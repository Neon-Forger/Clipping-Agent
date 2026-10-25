"""The agent itself: finds videos, makes clips, posts them, submits them,
and keeps your phone updated. Runs in background threads; the PC window
(gui.py) and the phone (ntfy) both talk to this."""
import datetime as dt
import json
import logging
import os
import re
import shutil
import sys
import threading
import time
import traceback

from . import ai, editor, poster, sources, transcribe
from .config import Settings, data_dir
from .db import DB
from .notify import Ntfy

HELP = """Commands you can send from the phone:
status · pause · resume · run (check for new videos now) · post (post the next clip now)
list (clips waiting) · skip <id> · retry <id> · retry videos
clip <video url> [how many] (clip a specific video)
set <setting> <value> · get <setting> · settings
prompt <text> (extra instructions for the AI editor) · prompt clear
addsource <name> | <youtube channel url> | <campaign url> | <#hashtag>
removesource <number> · sources
ask <question> (ask the AI about the agent)
Anything else is read by the AI and turned into commands."""


class Agent:
    def __init__(self):
        self.settings = Settings()
        self.db = DB()
        self.state_path = os.path.join(data_dir(), "state.json")
        self.state = self._load_state()
        self.listeners = []          # GUI callbacks: fn(level, text)
        self.current_task = "idle"
        self.browser_lock = threading.Lock()
        self.wake = threading.Event()
        self._stop = threading.Event()
        self.post_now_requested = False
        self.update_url = None
        logging.basicConfig(filename=os.path.join(data_dir(), "agent.log"), level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(message)s")
        self.ntfy = Ntfy(self.settings, self.log)

    # ------------------------------------------------------------------ utils
    def _load_state(self):
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_state(self):
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f)

    def log(self, level, text, notify=False, title=None, tags=None, priority=3):
        getattr(logging, "warning" if level == "warn" else ("error" if level == "error" else "info"))(text)
        try:
            self.db.log(level, text)
        except Exception:
            pass
        for fn in list(self.listeners):
            try:
                fn(level, text)
            except Exception:
                pass
        if notify:
            self.ntfy.send(text, title=title, tags=tags, priority=priority,
                           level="important" if priority >= 4 else "normal")

    def set_task(self, t):
        self.current_task = t
        for fn in list(self.listeners):
            try:
                fn("task", t)
            except Exception:
                pass

    @property
    def paused(self):
        return bool(self.settings["paused"])

    def status(self):
        c = self.db.counts()
        nxt = self.next_post_time()
        return {
            "paused": self.paused,
            "task": self.current_task,
            "ready": c.get("rendered", 0),
            "posted": c.get("posted", 0) + c.get("submitted", 0),
            "submitted": c.get("submitted", 0),
            "failed": c.get("failed", 0),
            "next_post": nxt.strftime("%a %I:%M %p") if nxt else None,
            "videos": len(self.db.q("SELECT id FROM videos")),
            "updated": dt.datetime.now().strftime("%I:%M %p"),
            "signin_needed": bool(self.state.get("signin_needed")),
        }

    def status_text(self):
        s = self.status()
        return (f"{'⏸ Paused' if s['paused'] else '▶ Running'} · now: {s['task']}\n"
                f"Clips ready: {s['ready']} · posted: {s['posted']} · submitted: {s['submitted']} · failed: {s['failed']}\n"
                f"Next post: {s['next_post'] or 'when a clip is ready'}"
                + ("\n🔒 Posting is waiting for a TikTok / Content Rewards sign-in." if s["signin_needed"] else ""))

    def push_state(self):
        self.ntfy.send_data("state", self.status())

    # --------------------------------------------------------------- lifecycle
    def start(self):
        self._keep_awake()
        threading.Thread(target=self._producer_loop, daemon=True, name="producer").start()
        threading.Thread(target=self._poster_loop, daemon=True, name="poster").start()
        threading.Thread(target=self.ntfy.listen, args=(self.handle_command, self._cmd_state()), daemon=True,
                         name="ntfy").start()
        threading.Thread(target=self._heartbeat, daemon=True, name="heartbeat").start()
        threading.Thread(target=self._check_update, daemon=True, name="update").start()
        self.log("info", "NeonClip started", notify=True, title="🤖 NeonClip online", tags=["robot"])
        self.push_state()

    def stop(self):
        self._stop.set()
        self.ntfy.stop()

    def _cmd_state(self):
        agent = self

        class Store(dict):
            def __setitem__(self, k, v):
                agent.state[k] = v
                agent.save_state()

            def get(self, k, d=None):
                return agent.state.get(k, d)
        return Store()

    def _keep_awake(self):
        if sys.platform == "win32" and self.settings["keep_pc_awake"]:
            try:
                import ctypes
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
            except Exception:
                pass

    def _check_update(self):
        try:
            from ._build import BUILD
        except Exception:
            return  # running from source
        try:
            import requests
            r = requests.get("https://api.github.com/repos/Neon-Forger/Clipping-Agent/releases/latest", timeout=20).json()
            latest = int(str(r.get("tag_name", "v0.0.0")).rsplit(".", 1)[-1])
            if latest > int(BUILD):
                self.update_url = r.get("html_url")
                self.log("warn", f"A new version (v1.0.{latest}) is out. Download it from the Accounts & Phone tab.",
                         notify=True, title="⬆️ Agent update available", tags=["arrow_up"])
        except Exception:
            pass

    def _heartbeat(self):
        while not self._stop.wait(1800):
            self.push_state()
            if getattr(self, "yt", None):
                self.yt.push_state()

    # ---------------------------------------------------------------- producer
    def _producer_loop(self):
        while not self._stop.is_set():
            try:
                if not self.paused:
                    self._check_sources_if_due()
                    self._process_next_video()
            except Exception as e:
                self.log("error", f"Producer error: {e}")
                logging.error(traceback.format_exc())
            self.set_task("idle")
            self.wake.wait(30)
            self.wake.clear()

    def _check_sources_if_due(self, force=False):
        every = self.settings["check_sources_every_minutes"] * 60
        if not force and time.time() - self.state.get("last_source_check", 0) < every:
            return
        self.state["last_source_check"] = time.time()
        self.save_state()
        self.set_task("checking for new videos")
        total = 0
        for src in self.settings["sources"]:
            if src.get("enabled", True):
                total += sources.find_new_videos(src, self.db, self.log)
        if total:
            self.log("info", f"Found {total} new video(s) to clip", notify=True, title="🎬 New video", tags=["clapper"])
        else:
            self.log("info", f"No new videos yet. Next check in {self.settings['check_sources_every_minutes']} min "
                             "(or use 'Clip a video link...' to clip one now).")

    def source_by_name(self, name):
        for s in self.settings["sources"]:
            if s.get("name") == name:
                return s
        return {"name": name, "required_hashtags": [], "extra_hashtags": [], "clips_per_video": 5}

    def _process_next_video(self):
        statuses = "'new','downloaded'" if time.time() < self.state.get("ai_retry_at", 0) else "'new','downloaded','transcribed'"
        pending = self.db.q(f"SELECT * FROM videos WHERE status IN ({statuses}) ORDER BY created LIMIT 1")
        if not pending:
            return
        v = pending[0]
        src = self.source_by_name(v["source"])
        work = os.path.join(data_dir(), "work", v["id"])
        os.makedirs(work, exist_ok=True)
        try:
            if v["status"] == "new":
                self.set_task(f"downloading: {v['title'][:40]}")
                self.log("info", f"Downloading {v['title']}")
                path = sources.download(v, os.path.join(data_dir(), "downloads"), self.log)
                self.db.update_video(v["id"], status="downloaded", path=path)
                v = self.db.video(v["id"])
            if v["status"] == "downloaded":
                self.set_task(f"transcribing: {v['title'][:40]}")
                self.log("info", "Transcribing (this can take a while)...")
                tr = transcribe.transcribe(v["path"], os.path.join(work, "transcript.json"), self.settings["transcribe"], self.log)
                self.db.update_video(v["id"], status="transcribed", transcript=os.path.join(work, "transcript.json"),
                                     duration=v["duration"] or (tr[-1]["end"] if tr else 0))
                v = self.db.video(v["id"])
            if v["status"] == "transcribed":
                self._select_and_render(v, src, work)
        except ai.NoAIKey as e:
            # keep the video waiting (downloaded + transcribed); tell the owner once
            if not self.state.get("ai_key_warned"):
                self.state["ai_key_warned"] = True
                self.save_state()
                self.log("warn", str(e), notify=True, title="🔑 AI key needed", tags=["key"], priority=4)
        except ai.AIError as e:
            # the AI service failed (retired model, quota, outage): keep the video and try again in 20 min
            self.state["ai_retry_at"] = time.time() + 1200
            self.save_state()
            self.log("error", f"AI step failed on {v['title']}, will retry in 20 min: {e}", notify=True,
                     title="⚠️ AI error", tags=["warning"])
        except Exception as e:
            self.db.update_video(v["id"], status="failed", error=str(e)[:500])
            self.log("error", f"Failed on {v['title']}: {e}\nSend 'retry videos' (or Dashboard → Retry failed videos) to try again.",
                     notify=True, title="⚠️ Video failed", tags=["warning"])
            logging.error(traceback.format_exc())

    def _select_and_render(self, v, src, work, n=None):
        with open(v["transcript"], "r", encoding="utf-8") as f:
            tr = json.load(f)
        words = transcribe.all_words(tr)
        n = n or self.state.get("clip_counts", {}).get(v["id"]) or src.get("clips_per_video", 5)
        edit = self.settings["edit"]
        self.set_task(f"AI picking moments: {v['title'][:35]}")
        done = [f"{int(c['start'] // 60)}:{int(c['start'] % 60):02d}-{int(c['end'] // 60)}:{int(c['end'] % 60):02d}"
                for c in self.db.q("SELECT start, end FROM clips WHERE video_id=?", (v["id"],))]
        picks = ai.select_moments(self.settings["ai"], edit, src, v, transcribe.transcript_for_ai(tr), n, avoid=done)
        if self.state.pop("ai_key_warned", None):
            self.save_state()
        prev = [(c["start"], c["end"]) for c in self.db.q("SELECT start, end FROM clips WHERE video_id=?", (v["id"],))]
        picks = [c for c in picks if all(c["end"] <= a or c["start"] >= b for a, b in prev)]
        # drop overlaps
        chosen = []
        for c in picks:
            c = ai.snap_to_words(c, words, edit["min_seconds"], edit["max_seconds"])
            if all(c["end"] <= o["start"] or c["start"] >= o["end"] for o in chosen):
                chosen.append(c)
            if len(chosen) >= n:
                break
        self.log("info", f"AI picked {len(chosen)} moments from {v['title']}")
        out_dir = os.path.join(self.settings["output_dir"], _safe(src.get("name", "clips")))
        os.makedirs(out_dir, exist_ok=True)
        made = 0
        for i, c in enumerate(chosen, 1):
            if self._stop.is_set():
                return
            caption = self.build_caption(c, src)
            cid = self.db.add_clip(video_id=v["id"], source=src.get("name"), start=c["start"], end=c["end"],
                                   punch=c["punch"], title=c["title"], caption=caption, emphasis=c["emphasis"],
                                   score=c["score"], reason=c["reason"])
            self.set_task(f"editing clip {i}/{len(chosen)}")
            out = os.path.join(out_dir, f"{cid} - {_safe(c['title'])}.mp4")
            try:
                editor.render_clip(v["path"], c, words, edit, out, os.path.join(work, f"clip{cid}"))
                self.db.update_clip(cid, file=out, status="rendered")
                made += 1
            except Exception as e:
                self.db.update_clip(cid, status="failed", error=str(e)[:500])
                self.log("error", f"Editing clip {cid} failed: {e}")
        self.db.update_video(v["id"], status="done")
        self.log("info", f"✂️ {made} clips ready from \"{v['title']}\"", notify=True, title="✂️ Clips ready", tags=["scissors"])
        if self.settings.get("delete_source_after_render", True) and v.get("path") and os.path.exists(v["path"]):
            try:
                os.remove(v["path"])
            except OSError:
                pass
        self.push_state()

    def build_caption(self, c, src):
        tags = []
        for h in (src.get("required_hashtags") or []) + (c.get("hashtags") or []) + (src.get("extra_hashtags") or []):
            h = h.strip()
            if h and h.lower() not in [t.lower() for t in tags]:
                tags.append(h if h.startswith("#") else "#" + h)
        cap = (c.get("caption") or c.get("title") or "").strip()
        extra = (src.get("caption_extra") or "").strip()
        if extra:
            cap += "\n" + extra
        # required hashtags are always kept; others fill up to 8 total
        req = len([h for h in (src.get("required_hashtags") or []) if h.strip()])
        return cap + "\n" + " ".join(tags[:max(8, req)])

    # ------------------------------------------------------------------ poster
    def next_post_time(self):
        p = self.settings["posting"]
        if not p.get("auto_post", True):
            return None
        if not self.db.clips("rendered", 1):
            return None
        t = max(time.time(), self.db.last_post_time() + p["min_minutes_between_posts"] * 60)
        day_posts = self.db.posts_since(time.time() - 86400)
        if len(day_posts) >= p["max_posts_per_day"]:
            oldest = min(c["posted_at"] for c in day_posts)
            t = max(t, oldest + 86400)
        d = dt.datetime.fromtimestamp(t)
        qs, qe = p["quiet_hours_start"], p["quiet_hours_end"]
        for _ in range(48):
            h = d.hour
            quiet = (qs <= h < qe) if qs < qe else (h >= qs or h < qe)
            if not quiet:
                break
            d = (d + dt.timedelta(hours=1)).replace(minute=7, second=0)
        return d

    def _poster_loop(self):
        while not self._stop.is_set():
            try:
                if not self.paused and not self.state.get("signin_needed"):
                    nxt = self.next_post_time()
                    if self.post_now_requested or (nxt and dt.datetime.now() >= nxt):
                        self.post_now_requested = False
                        self.post_next()
            except Exception as e:
                self.log("error", f"Poster error: {e}")
                logging.error(traceback.format_exc())
            self._stop.wait(30)

    def post_next(self, cid=None):
        try:
            self._post_next(cid)
        finally:
            self.set_task("idle")

    def _post_next(self, cid=None):
        clip = self.db.clip(cid) if cid else (self.db.clips("rendered", 1) or [None])[0]
        if not clip:
            self.log("info", "No clips ready to post", notify=True, title="📭 Nothing to post")
            return
        src = self.source_by_name(clip["source"])
        p = self.settings["posting"]
        sel = self.settings["selectors"]
        with self.browser_lock:
            self.db.update_clip(clip["id"], status="posting")
            self.set_task(f"posting clip {clip['id']}")
            try:
                url = poster.post_to_tiktok(clip["file"], clip["caption"], p, sel, self.log)
            except poster.NotLoggedIn as e:
                self.db.update_clip(clip["id"], status="rendered")
                self.state["signin_needed"] = True
                self.save_state()
                self.log("error", str(e) + " Sign in from the phone app (Settings → Accounts).",
                         notify=True, title="🔒 Sign-in needed", tags=["lock"], priority=5)
                return
            except Exception as e:
                self.db.update_clip(clip["id"], status="failed", error=str(e)[:500])
                self.log("error", f"Posting clip {clip['id']} failed: {e}", notify=True, title="⚠️ Post failed", tags=["warning"], priority=4)
                return
            posted_at = time.time()
            self.db.update_clip(clip["id"], status="posted", tiktok_url=url, posted_at=posted_at)
            self.log("info", f"📤 Posted: {clip['title']}\n{url}", notify=True, title="📤 Posted to TikTok", tags=["outbox_tray"])

            if p.get("submit_to_content_rewards", True) and src.get("campaign_url"):
                self.set_task(f"submitting clip {clip['id']}")
                for attempt in range(3):
                    if time.time() - posted_at > p.get("submit_within_minutes", 25) * 60:
                        self.log("error", "Too late to submit (Content Rewards needs it within 30 min of posting)",
                                 notify=True, title="⏰ Missed the submit window", priority=4)
                        break
                    try:
                        res = poster.submit_to_content_rewards(src["campaign_url"], url, p, sel, self.log)
                        self.db.update_clip(clip["id"], status="submitted", submitted_at=time.time(), submit_result=res)
                        self.log("info", f"✅ Submitted to Content Rewards ({res})\n{url}", notify=True,
                                 title="✅ Submitted for payout", tags=["white_check_mark", "moneybag"])
                        break
                    except poster.NotLoggedIn as e:
                        self.state["signin_needed"] = True
                        self.save_state()
                        self.log("error", str(e) + f" Submit this link by hand within 30 min: {url}",
                                 notify=True, title="🔒 Content Rewards sign-in needed", tags=["lock"], priority=5)
                        break
                    except Exception as e:
                        self.log("warn", f"Submit attempt {attempt + 1} failed: {e}")
                        if attempt == 2:
                            self.db.update_clip(clip["id"], submit_result=f"failed: {e}"[:500])
                            self.log("error", f"Couldn't submit clip {clip['id']}: {e}\nSubmit it by hand quickly: {url}",
                                     notify=True, title="⚠️ Submit failed", tags=["warning"], priority=5, )
                        time.sleep(30)
            self.set_task("idle")
            self.push_state()

    # ---------------------------------------------------------------- commands
    def handle_command(self, text):
        yt = getattr(self, "yt", None)
        if yt and text.lower().startswith(("yt ", "youtube ")):
            yt.handle_command(text.split(maxsplit=1)[1] if len(text.split(maxsplit=1)) > 1 else "status")
            return
        if yt and text.strip().lower() == "state":
            yt.push_state()
        shown = "login (sign-in from phone)" if text.lower().startswith("login ") else (text if len(text) < 120 else text[:117] + "...")
        if text.lower().startswith("set ") and any(k in text for k in ("api_key", "token", "pair_code")):
            shown = text.split(" ")[0] + " " + text.split(" ")[1] + " (hidden)"
        self.log("info", f"📱 Command: {shown}")
        reply = self.run_command(text)
        if reply:
            self.ntfy.send(reply, title="🤖 Agent", tags=["robot"])
        self.push_state()

    def run_command(self, text, allow_ai=True):
        parts = text.strip().split(maxsplit=1)
        cmd = parts[0].lower().lstrip("/") if parts else ""
        arg = parts[1].strip() if len(parts) > 1 else ""
        s = self.settings
        if cmd in ("help", "?"):
            return HELP
        if cmd == "status":
            return self.status_text()
        if cmd == "state":
            return None
        if cmd == "pause":
            s.set("paused", True)
            return "⏸ Paused. Send 'resume' to continue."
        if cmd in ("resume", "start", "unpause"):
            s.set("paused", False)
            self.wake.set()
            return "▶ Running."
        if cmd in ("run", "check"):
            self.state["last_source_check"] = 0
            self.wake.set()
            return "🔎 Checking for new videos now."
        if cmd == "post":
            if arg.isdigit():
                threading.Thread(target=self.post_next, args=(int(arg),), daemon=True).start()
            else:
                self.state.pop("signin_needed", None)
                self.post_now_requested = True
            return "📤 Posting the next clip now."
        if cmd == "list":
            rows = self.db.clips("rendered", 15)
            if not rows:
                return "No clips waiting."
            return "\n".join(f"#{r['id']} ({int(r['score'] or 0)}) {r['title']}" for r in rows)
        if cmd == "skip" and arg.isdigit():
            self.db.update_clip(int(arg), status="skipped")
            return f"Skipped clip #{arg}."
        if cmd == "retry" and arg.lower() in ("videos", "video", "failed", "all"):
            return self.retry_failed_videos()
        if cmd == "retry" and arg.isdigit():
            c = self.db.clip(int(arg))
            if c and c.get("file") and os.path.exists(c["file"]):
                self.db.update_clip(int(arg), status="rendered", error=None)
                return f"Clip #{arg} is back in the queue."
            return f"Clip #{arg} has no video file to retry."
        if cmd == "clip":
            bits = arg.split()
            if not bits:
                return "Usage: clip <video url> [how many]"
            url, n = bits[0], int(bits[1]) if len(bits) > 1 and bits[1].isdigit() else None
            threading.Thread(target=self._clip_url, args=(url, n), daemon=True).start()
            return f"🎬 Clipping {url}"
        if cmd == "set":
            k, _, v = arg.partition(" ")
            if not k:
                return "Usage: set <setting> <value>"
            val = s.set(k, v.strip())
            self.wake.set()
            return f"✔ {k} = {json.dumps(val) if k.split('.')[-1] not in ('gemini_api_key','openrouter_api_key','openai_compatible_api_key','token') else '(saved)'}"
        if cmd == "get":
            v = s.get(arg)
            return f"{arg} = {json.dumps(v)[:1500]}" if v is not None else f"No setting named {arg}"
        if cmd == "settings":
            self.ntfy.send_data("settings", s.masked())
            return None
        if cmd == "settings_json":
            s.replace_all(json.loads(arg))
            self.wake.set()
            return "✔ Settings saved."
        if cmd == "prompt":
            s.set("ai.custom_instructions", "" if arg.lower() == "clear" else arg)
            return "✔ AI instructions " + ("cleared." if arg.lower() == "clear" else "updated.")
        if cmd == "sources":
            return "\n".join(f"{i}. {'✅' if x.get('enabled', True) else '⏸'} {x.get('name')} — {x.get('channel_url') or ', '.join(x.get('video_urls') or [])}"
                             for i, x in enumerate(s["sources"])) or "No sources."
        if cmd == "addsource":
            f = [x.strip() for x in arg.split("|")]
            if len(f) < 3:
                return "Usage: addsource <name> | <youtube channel url> | <campaign url> | <#hashtag>"
            src = {"name": f[0], "enabled": True, "channel_url": f[1], "video_urls": [], "title_must_contain": "",
                   "only_newer_than_days": 7, "campaign_url": f[2],
                   "required_hashtags": [h for h in f[3].split()] if len(f) > 3 else [],
                   "extra_hashtags": ["#fyp"], "notes_for_ai": "", "clips_per_video": 5}
            lst = s["sources"]
            lst.append(src)
            s.set("sources", lst)
            return f"✔ Added source {f[0]}."
        if cmd == "removesource" and arg.isdigit():
            lst = s["sources"]
            gone = lst.pop(int(arg))
            s.set("sources", lst)
            return f"✔ Removed {gone.get('name')}."
        if cmd == "ask":
            return self._ask_ai(arg)
        if cmd == "login":
            threading.Thread(target=self._phone_login, args=(arg,), daemon=True).start()
            return None
        if allow_ai:
            return self._natural_language(text)
        return f"Unknown command: {cmd}. Send 'help'."

    def _phone_login(self, blob):
        from . import crypto
        try:
            data = crypto.decrypt(blob, self.settings["ntfy"]["pair_code"])
        except Exception:
            self.log("error", "A sign-in from the phone couldn't be read. Check the pairing code in the phone app matches "
                              "the one in Accounts & Phone on the PC.", notify=True, title="🔒 Sign-in failed", priority=4)
            return
        service = data.get("service", "")
        name = {"tiktok": "TikTok", "contentrewards": "Content Rewards", "youtube": "YouTube"}.get(service, service)
        if data.get("ua"):
            self.settings.set("posting.user_agent", data["ua"])
        try:
            if service == "youtube":
                from .poster import write_netscape_cookies
                write_netscape_cookies(data.get("cookies", ""), ".youtube.com", os.path.join(data_dir(), "youtube_cookies.txt"))
                res = "saved ✅ (used for downloading)"
            else:
                with self.browser_lock:
                    self.set_task(f"saving {name} sign-in")
                    res = poster.import_cookies(service, data.get("cookies", ""), self.settings["posting"], self.log)
            ok = "✅" in res
            self.log("info" if ok else "warn", f"{name} sign-in from phone: {res}", notify=True,
                     title=("✅ " if ok else "⚠️ ") + f"{name} sign-in", priority=3 if ok else 4)
            if ok and service in ("tiktok", "contentrewards") and self.state.pop("signin_needed", None):
                self.save_state()
                self.log("info", "Posting is back on.", notify=True, title="🤖 Agent")
        except Exception as e:
            self.log("error", f"Couldn't save the {name} sign-in: {e}", notify=True, title="⚠️ Sign-in failed", priority=4)
        finally:
            self.set_task("idle")

    def _clip_url(self, url, n):
        try:
            info = sources.video_info(url)
            src = self._source_for(info) or (self.settings["sources"][0] if self.settings["sources"] else {"name": "manual"})
            if not self.db.add_video(info["id"], src.get("name", "manual"), info.get("webpage_url") or url, info.get("title", ""), info.get("duration")):
                old = self.db.video(info["id"])
                tr = os.path.join(data_dir(), "work", info["id"], "transcript.json")
                has_file = old.get("path") and os.path.exists(old["path"])
                st = "transcribed" if (has_file and os.path.exists(tr)) else ("downloaded" if has_file else "new")
                self.db.update_video(info["id"], status=st, error=None, source=src.get("name", "manual"),
                                     transcript=tr if st == "transcribed" else old.get("transcript"))
                self.state.pop("ai_retry_at", None)
            if n:
                self.state.setdefault("clip_counts", {})[info["id"]] = n
            self.wake.set()
        except Exception as e:
            self.log("error", f"Couldn't clip {url}: {e}", notify=True, title="⚠️ Clip failed")

    def retry_failed_videos(self):
        n = 0
        for v in self.db.q("SELECT * FROM videos WHERE status='failed'"):
            tr = os.path.join(data_dir(), "work", v["id"], "transcript.json")
            if os.path.exists(tr) and v.get("path") and os.path.exists(v["path"]):
                st = "transcribed"
            elif v.get("path") and os.path.exists(v["path"]):
                st = "downloaded"
            else:
                st = "new"  # re-download; a saved transcript is reused
            self.db.update_video(v["id"], status=st, error=None,
                                 transcript=tr if st == "transcribed" else v.get("transcript"))
            n += 1
        self.state.pop("ai_retry_at", None)
        self.save_state()
        self.wake.set()
        return f"🔁 Retrying {n} failed video(s)." if n else "No failed videos."

    def _source_for(self, info):
        """The source a video belongs to: listed in its video links, or from the channel it watches."""
        vid = info.get("id", "")
        chan = [(info.get(k) or "").lower().rstrip("/") for k in ("channel_url", "uploader_url")]
        for s in self.settings["sources"]:
            if any(vid and vid in u for u in (s.get("video_urls") or [])):
                return s
        for s in self.settings["sources"]:
            c = (s.get("channel_url") or "").lower().rstrip("/")
            for suffix in ("/videos", "/streams", "/featured"):
                if c.endswith(suffix):
                    c = c[: -len(suffix)]
            if c and any(x and (x == c or x.endswith(c.split("youtube.com")[-1])) for x in chan):
                return s
        return None

    def _ask_ai(self, question):
        ctx = {"status": self.status(), "recent_log": [e["text"] for e in self.db.events(25)],
               "settings": self.settings.masked()}
        return ai.ask(self.settings["ai"], "You are the assistant inside 'NeonClip', an app whose Clipping section clips long videos into "
                      "TikToks, posts them and submits them to Content Rewards. Answer the owner briefly (max 5 sentences).\n"
                      f"Agent info: {json.dumps(ctx)[:12000]}\n\nQuestion: {question}")

    def _natural_language(self, text):
        prompt = (HELP + "\n\nSettings (JSON, dotted paths usable with 'set'): " + json.dumps(self.settings.masked())[:8000] +
                  "\n\nThe owner sent this message from their phone: \"" + text + "\"\n"
                  "Turn it into a list of the commands above that carry it out. If it's just a question, use 'ask'. "
                  'Return JSON: {"commands": ["..."], "reply": "short confirmation"}')
        try:
            data = ai.parse_json(ai.ask(self.settings["ai"], prompt, json_mode=True))
        except ai.NoAIKey:
            return "Unknown command. Send 'help' (or add an AI key so I can understand plain English)."
        outs = []
        for c in (data.get("commands") or [])[:8]:
            r = self.run_command(c, allow_ai=False)
            if r:
                outs.append(r)
        return ((data.get("reply") or "") + ("\n" + "\n".join(outs) if outs else "")).strip()


def random_minute():
    import random
    return random.randint(3, 40)


def _safe(name):
    return re.sub(r'[<>:"/\\|?*\n\r\t]', "", name).strip()[:80] or "clip"
