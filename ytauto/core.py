"""The YouTube section's agent: plans today's videos, makes them, uploads them on schedule.
Runs on its own threads, settings, database and browser profile, separate from Clipping."""
import datetime as dt
import json
import logging
import os
import random
import re
import shutil
import sqlite3
import threading
import time
import traceback

from agent import ai, editor, sources, transcribe
from agent.config import data_dir

from . import render, stickman, studio, thumbs, training, visuals, writer
from .config import YTSettings

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT, mode TEXT, day TEXT,
  title TEXT, description TEXT, tags TEXT, thumb_text TEXT,
  source_url TEXT, source_note TEXT,
  file TEXT, thumb TEXT,
  status TEXT,          -- planned, making, ready, uploading, uploaded, failed, skipped
  url TEXT, error TEXT, created REAL, uploaded_at REAL
);
CREATE TABLE IF NOT EXISTS used_sources (video_id TEXT PRIMARY KEY, used REAL);
CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, level TEXT, text TEXT);
"""

YT_HELP = """YouTube commands (send with "yt " in front, e.g. "yt status"):
status · pause · resume · make long [what it's about] · make short [what it's about] · make short original/repurpose
  e.g. "make short a Halloween special about the Dyatlov Pass" (the text after long/short is followed for that video)
style stickman / style stock (switch the visual style) · visual <direction> (set the visual direction)
train on / train off (training mode) · learn (learn from your best videos now) · stats (best videos by views)
upload (upload the next finished video now) · list · skip <id> · retry <id>
set <setting> <value> · get <setting> · settings · prompt <text> · ask <question>"""


class YTAgent:
    def __init__(self, notifier=None):
        self.s = YTSettings()
        self.conn = sqlite3.connect(os.path.join(data_dir(), "youtube.db"), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        with self.lock:
            self.conn.executescript(SCHEMA)
            cols = {r[1] for r in self.conn.execute("PRAGMA table_info(items)")}
            for col, typ in (("brief", "TEXT"), ("views", "INTEGER"), ("likes", "INTEGER"), ("comments", "INTEGER"),
                             ("stats_at", "REAL"), ("score", "REAL"), ("meta", "TEXT")):
                if col not in cols:
                    self.conn.execute(f"ALTER TABLE items ADD COLUMN {col} {typ}")
            # videos that were being made when NeonClip was closed start over
            self.conn.execute("UPDATE items SET status='planned' WHERE status='making'")
            self.conn.execute("UPDATE items SET status='ready' WHERE status='uploading'")
            self.conn.commit()
        self.state_path = os.path.join(data_dir(), "youtube_state.json")
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                self.state = json.load(f)
        except Exception:
            self.state = {}
        self.notifier = notifier          # app-level phone link (only used to send messages)
        self.listeners = []
        self.task = "idle"
        self.wake = threading.Event()
        self._stop = threading.Event()
        self.browser_lock = threading.Lock()
        self.upload_now = False

    # ------------------------------------------------------------ helpers
    def q(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.conn.execute(sql, args).fetchall()]

    def x(self, sql, args=()):
        with self.lock:
            c = self.conn.execute(sql, args)
            self.conn.commit()
            return c.lastrowid

    def save_state(self):
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f)

    def log(self, level, text, notify=False, title=None, priority=3):
        logging.info("[YT] " + text)
        self.x("INSERT INTO events (ts,level,text) VALUES (?,?,?)", (time.time(), level, text))
        for fn in list(self.listeners):
            try:
                fn(level, text)
            except Exception:
                pass
        if notify and self.notifier:
            self.notifier.send(text, title="▶ YT · " + (title or "YouTube"), priority=priority,
                               tags=["arrow_forward"], level="important" if priority >= 4 else "normal")

    def set_task(self, t):
        self.task = t
        for fn in list(self.listeners):
            try:
                fn("task", t)
            except Exception:
                pass

    def update(self, iid, **kw):
        cols = ",".join(f"{k}=?" for k in kw)
        self.x(f"UPDATE items SET {cols} WHERE id=?", (*kw.values(), iid))

    def item(self, iid):
        r = self.q("SELECT * FROM items WHERE id=?", (iid,))
        return r[0] if r else None

    @property
    def active(self):
        return self.s["enabled"] and self.s["setup_done"] and not self.s["paused"]

    def status(self):
        c = {r["status"]: r["n"] for r in self.q("SELECT status, COUNT(*) n FROM items GROUP BY status")}
        nxt = self.next_upload_time()
        return {"enabled": bool(self.s["enabled"]), "setup_done": bool(self.s["setup_done"]), "paused": bool(self.s["paused"]),
                "channel": self.s["channel"].get("name") or "", "genre": self.s["genre"], "task": self.task,
                "ready": c.get("ready", 0), "planned": c.get("planned", 0) + c.get("making", 0),
                "uploaded": c.get("uploaded", 0), "failed": c.get("failed", 0),
                "next_upload": nxt.strftime("%a %I:%M %p") if nxt else None,
                "training": bool((self.s.get("training") or {}).get("enabled")), "training_status": training.status_line(self.s),
                "updated": dt.datetime.now().strftime("%I:%M %p")}

    def status_text(self):
        st = self.status()
        if not st["setup_done"]:
            return "YouTube isn't set up yet. Open NeonClip on the PC → YouTube → Setup."
        return (f"{'⏸ Paused' if st['paused'] else '▶ Running'} · {st['channel']} ({st['genre']})\nNow: {st['task']}\n"
                f"Ready: {st['ready']} · in progress: {st['planned']} · uploaded: {st['uploaded']} · failed: {st['failed']}\n"
                f"Next upload: {st['next_upload'] or 'when a video is ready'}")

    def push_state(self):
        if self.notifier:
            self.notifier.send_data("ytstate", self.status())

    # ----------------------------------------------------------- lifecycle
    def start(self):
        threading.Thread(target=self._maker_loop, daemon=True, name="yt-maker").start()
        threading.Thread(target=self._upload_loop, daemon=True, name="yt-upload").start()
        threading.Thread(target=self._training_loop, daemon=True, name="yt-training").start()

    def _training_loop(self):
        self._stop.wait(90)
        while not self._stop.is_set():
            try:
                t = self.s.get("training") or {}
                if t.get("enabled") and self.s["setup_done"]:
                    if time.time() - self.state.get("stats_at", 0) > float(t.get("stats_every_hours", 4)) * 3600:
                        self.train(learn=False)
                    pb = t.get("playbook") or {}
                    if time.time() - (pb.get("learned_at") or 0) > float(t.get("relearn_every_hours", 24)) * 3600:
                        try:
                            training.learn(self, self.log)
                        except RuntimeError as e:
                            if "at least 4" not in str(e):
                                raise
            except Exception as e:
                self.log("warn", f"Training: {e}")
            self._stop.wait(900)

    def train(self, learn=True):
        """Reads the latest stats and (optionally) re-learns the playbook now."""
        self.set_task("training: reading video stats")
        try:
            training.refresh_stats(self, self.log)
            if learn:
                self.set_task("training: learning from the best videos")
                return training.learn(self, self.log)
        finally:
            self.set_task("idle")
            self.push_state()

    def stop(self):
        self._stop.set()

    # ------------------------------------------------------------- planning
    @staticmethod
    def _hm(s, default="08:00"):
        try:
            h, m = (int(x) for x in str(s or default).split(":")[:2])
            return h, m
        except Exception:
            return 8, 0

    def _plan_today_if_due(self):
        today = dt.date.today().isoformat()
        if self.state.get("planned_day") == today:
            return
        h, m = self._hm(self.s["daily"]["make_at"])
        if dt.datetime.now() < dt.datetime.now().replace(hour=h, minute=m, second=0, microsecond=0):
            return
        self.state["planned_day"] = today
        self.save_state()
        n_long, n_short = int(self.s["daily"]["long_videos"]), int(self.s["daily"]["shorts"])
        for _ in range(n_long):
            self.add_item("long")
        for _ in range(n_short):
            self.add_item("short")
        if n_long or n_short:
            self.log("info", f"Planned today: {n_long} long video(s) and {n_short} Short(s)", notify=True, title="🗓 Today's plan")

    def _choose_mode(self):
        mix = self.s["mix"]
        o, r = max(0, int(mix.get("original", 70))), max(0, int(mix.get("repurpose", 30)))
        if not self.s["sources"] and not self.s.get("find_creative_commons"):
            return "original"
        if o + r == 0:
            return "original"
        return "original" if random.random() < o / (o + r) else "repurpose"

    def add_item(self, kind, mode=None, brief=None):
        if brief and not mode:
            mode = "original"   # a specific request is written from scratch
        return self.x("INSERT INTO items (kind,mode,day,status,created,brief) VALUES (?,?,?,?,?,?)",
                      (kind, mode or self._choose_mode(), dt.date.today().isoformat(), "planned", time.time(), brief or None))

    # --------------------------------------------------------------- making
    def _maker_loop(self):
        while not self._stop.is_set():
            try:
                if self.active:
                    self._plan_today_if_due()
                    has_key = any(self.s["ai"].get(k) for k in ("gemini_api_key", "openrouter_api_key", "openai_compatible_api_key"))
                    nxt = self.q("SELECT * FROM items WHERE status='planned' ORDER BY id LIMIT 1") if has_key else []
                    if not has_key and not self.state.get("ai_warned"):
                        self.state["ai_warned"] = True
                        self.save_state()
                        self.log("warn", "Add an AI key in YouTube → Settings so I can write videos.", notify=True,
                                 title="🔑 AI key needed", priority=4)
                    if nxt:
                        self.make(nxt[0])
                    self._cleanup()
            except Exception as e:
                self.log("error", f"YouTube maker error: {e}")
                logging.error(traceback.format_exc())
            self.set_task("idle")
            self.wake.wait(60)
            self.wake.clear()

    def _out_dir(self):
        d = self.s["output_dir"]
        os.makedirs(d, exist_ok=True)
        return d

    def _work(self, iid):
        w = os.path.join(data_dir(), "yt-work", str(iid))
        os.makedirs(w, exist_ok=True)
        return w

    def past_titles(self):
        return [r["title"] for r in self.q("SELECT title FROM items WHERE title IS NOT NULL ORDER BY id")]

    def make(self, it):
        iid, mode = it["id"], it["mode"]
        self.update(iid, status="making")
        try:
            if mode == "repurpose":
                try:
                    done = self._make_repurposed(it)
                except NoSource as e:
                    self.log("warn", f"{e} Making an original video instead.")
                    self.update(iid, mode="original")
                    done = self._make_original(dict(it, mode="original"))
            else:
                done = self._make_original(it)
            self.update(iid, status="ready", **done)
            self.log("info", f"✅ Ready: {done.get('title')}", notify=True, title="🎬 Video ready")
        except ai.NoAIKey:
            self.update(iid, status="planned")
        except ai.AIError as e:
            self.update(iid, status="planned")
            self.log("error", f"AI error, will retry in a few minutes: {e}")
            self._stop.wait(600)
        except Exception as e:
            self.update(iid, status="failed", error=str(e)[:500])
            self.log("error", f"Making video #{iid} failed: {e}", notify=True, title="⚠️ Video failed")
            logging.error(traceback.format_exc())
        finally:
            self.push_state()

    def _make_original(self, it):
        iid, kind = it["id"], it["kind"]
        portrait = kind == "short"
        self.set_task(f"writing a {'Short' if portrait else 'video'}")
        brief = (it.get("brief") or "").strip()
        if not brief and (self.s.get("training") or {}).get("follow_topics", True):
            topic = training.next_topic(self.s)
            if topic:
                brief = f"(Picked by training mode because similar videos did best) Make it about: {topic}"
                self.update(iid, brief=brief)
        idea = writer.new_idea(self.s, kind, self.past_titles(), brief=brief)
        self.update(iid, title=idea.get("title"))
        sc = writer.script(self.s, kind, idea, brief=brief)
        self.set_task(f"making: {idea.get('title', '')[:40]}")
        work = self._work(iid)
        name = _safe(idea.get("title") or f"video {iid}")
        out = os.path.join(self._out_dir(), f"{iid} - {name}{' (Short)' if portrait else ''}.mp4")
        if (self.s.get("visual_style") or "stock") == "stickman":
            _, credits = stickman.build(self.s, sc["segments"], portrait, work, out, log=self.log)
        else:
            _, credits = render.build_original(self.s, sc["segments"], portrait, work, out, log=self.log)
        desc = (sc.get("description") or "").strip()
        if credits:
            desc += "\n\nPhotos: " + "; ".join(dict.fromkeys(credits))
        if not portrait and self.s["long"].get("chapters"):
            ch = _chapters(work)
            if ch:
                desc += "\n\n" + ch
        thumb = None
        if not portrait:
            thumb = self._thumbnail(idea.get("title", ""), sc.get("thumbnail_text") or idea.get("title", ""), out, work)
        title = idea.get("title", "")[:100]
        if portrait and "#shorts" not in title.lower():
            desc += "\n#shorts"
        meta = {"hook": idea.get("hook"), "angle": idea.get("angle"), "style": self.s.get("visual_style") or "stock",
                "segments": len(sc["segments"]), "duration": round(_dur(out), 1), "thumbnail_text": sc.get("thumbnail_text", ""),
                "training": bool((self.s.get("training") or {}).get("enabled"))}
        return {"title": title, "description": self._footer(desc), "tags": json.dumps(sc.get("tags") or []),
                "thumb_text": sc.get("thumbnail_text", ""), "file": out, "thumb": thumb, "meta": json.dumps(meta)}

    def _thumbnail(self, title, text, video, work):
        bg = None
        if self.s["thumbnails"].get("ai_images"):
            bg = visuals.ai_image(self.s["ai"], f"YouTube thumbnail background, dramatic cinematic lighting, about: {title}",
                                  os.path.join(work, "thumb_bg.png"), "16:9")
        if not bg:
            clean = os.path.join(work, "joined.mp4")   # same video before captions were added
            bg = thumbs.best_frame(clean if os.path.exists(clean) else video, os.path.join(work, "thumb_bg.png"))
        out = os.path.splitext(video)[0] + " - thumbnail.jpg"
        t = self.s["thumbnails"]
        return thumbs.thumbnail(bg, text, out, t.get("text_color", "#7FE9FF"), t.get("accent", "#FF2BD6"))

    def _footer(self, desc):
        f = (self.s["upload"].get("description_footer") or "").strip()
        return (desc + ("\n\n" + f if f else "")).strip()

    # ------------------------------------------------------------ repurpose
    def _candidate_sources(self):
        """Videos we're allowed to reuse: your own / permission / Creative Commons. Never anything else."""
        cands = []
        for src in self.s["sources"]:
            rights = (src.get("rights") or "").lower()
            if rights not in ("own", "permission", "creative_commons"):
                continue
            url = (src.get("url") or "").strip()
            # a channel link lists its tabs, not videos: point it at the Videos tab
            if re.search(r"youtube\.com/(@[^/]+|channel/[^/]+|c/[^/]+|user/[^/]+)/?$", url):
                url = url.rstrip("/") + "/videos"
            try:
                with sources._ydl({"extract_flat": "in_playlist", "playlistend": 25, "skip_download": True}) as y:
                    info = y.extract_info(url, download=False)
                entries = info.get("entries") or [info]
                for e in entries:
                    if e and e.get("id"):
                        cands.append({"id": e["id"], "url": e.get("url") or f"https://www.youtube.com/watch?v={e['id']}",
                                      "rights": rights, "note": src.get("note", "")})
            except Exception as e:
                self.log("warn", f"Couldn't read source {url}: {e}")
        if self.s.get("find_creative_commons") and self.s["genre"]:
            try:
                with sources._ydl({"extract_flat": True, "skip_download": True}) as y:
                    res = y.extract_info(f"ytsearch25:{self.s['genre']}", download=False)
                for e in res.get("entries") or []:
                    if e and e.get("id"):
                        cands.append({"id": e["id"], "url": f"https://www.youtube.com/watch?v={e['id']}",
                                      "rights": "creative_commons?", "note": ""})
            except Exception as e:
                self.log("warn", f"Creative Commons search failed: {e}")
        used = {r["video_id"] for r in self.q("SELECT video_id FROM used_sources")}
        return [c for c in cands if c["id"] not in used]

    def _pick_source(self, kind):
        need = 300 if kind == "long" else 60
        for c in self._candidate_sources():
            try:
                info = sources.video_info(c["url"])
            except Exception:
                continue
            dur = info.get("duration") or 0
            if dur < need or info.get("live_status") in ("is_live", "is_upcoming"):
                continue
            lic = (info.get("license") or "").lower()
            if c["rights"] == "creative_commons?" and "creative commons" not in lic:
                continue  # search results are only used when YouTube marks them Creative Commons
            if c["rights"] == "creative_commons" and lic and "creative commons" not in lic:
                continue
            c.update(info=info, title=info.get("title"), uploader=info.get("uploader"), license=info.get("license"))
            return c
        raise NoSource("No reusable source video found (add sources you own/have permission for, or turn on Creative Commons search).")

    def _make_repurposed(self, it):
        iid, kind = it["id"], it["kind"]
        self.set_task("finding a source video")
        c = self._pick_source(kind)
        info = c["info"]
        self.x("INSERT OR REPLACE INTO used_sources (video_id, used) VALUES (?,?)", (c["id"], time.time()))
        work = self._work(iid)
        self.set_task(f"downloading: {(c['title'] or '')[:40]}")
        path = sources.download({"id": c["id"], "url": c["url"]}, os.path.join(data_dir(), "yt-downloads"), self.log)
        self.set_task("transcribing")
        tr = transcribe.transcribe(path, os.path.join(work, "transcript.json"), self.s["transcribe"], self.log)
        words = transcribe.all_words(tr)
        credit = f"Source: \"{c['title']}\" by {c.get('uploader') or 'the original creator'} — {c['url']}"
        if "creative" in (c.get("license") or "").lower():
            credit += f" (licensed {c['license']})"
        try:
            if kind == "long":
                self.set_task("AI planning the edit")
                plan = writer.repurpose_plan(self.s, kind, {"title": c["title"], "uploader": c.get("uploader")},
                                             transcribe.transcript_for_ai(tr), self.s["long"]["minutes"])
                out = os.path.join(self._out_dir(), f"{iid} - {_safe(plan.get('title') or c['title'])}.mp4")
                self.set_task(f"editing: {(plan.get('title') or '')[:40]}")
                render.build_repurposed_long(self.s, path, plan, work, out, log=self.log)
                thumb = self._thumbnail(plan.get("title", ""), plan.get("thumbnail_text") or plan.get("title", ""), out, work)
                desc = (plan.get("description") or "") + "\n\n" + credit
                return {"title": (plan.get("title") or c["title"])[:100], "description": self._footer(desc),
                        "tags": json.dumps(plan.get("tags") or []), "thumb_text": plan.get("thumbnail_text", ""),
                        "file": out, "thumb": thumb, "source_url": c["url"], "source_note": c["rights"]}
            # Short: best single moment, vertical, dramatic edit
            self.set_task("AI picking the best moment")
            edit_cfg = {"min_seconds": 20, "max_seconds": min(59, int(self.s["shorts"]["seconds"]) + 10), "style": "dramatic",
                        "censor_swears": True}
            picks = ai.select_moments(self.s["ai"], edit_cfg, {"notes_for_ai": self.s.get("style_notes", "")},
                                      {"title": c["title"], "duration": info.get("duration")}, transcribe.transcript_for_ai(tr), 1)
            if not picks:
                raise RuntimeError("The AI didn't find a good moment")
            m = ai.snap_to_words(picks[0], words, edit_cfg["min_seconds"], edit_cfg["max_seconds"])
            out = os.path.join(self._out_dir(), f"{iid} - {_safe(m['title'])} (Short).mp4")
            self.set_task(f"editing Short: {m['title'][:40]}")
            editor.render_clip(path, m, words, edit_cfg, out, os.path.join(work, "short"))
            desc = (m.get("caption") or "") + "\n\n" + credit + "\n#shorts"
            return {"title": m["title"][:100], "description": self._footer(desc), "tags": json.dumps(m.get("hashtags") or []),
                    "file": out, "source_url": c["url"], "source_note": c["rights"]}
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    # ---------------------------------------------------------------- upload
    def next_upload_time(self):
        if not self.q("SELECT id FROM items WHERE status='ready' LIMIT 1"):
            return None
        today = dt.date.today()
        done = set(self.state.get("slots_done", {}).get(today.isoformat(), []))
        times = sorted(self.s["daily"]["upload_times"] or ["12:00"])
        for day_off in range(0, 3):
            d = today + dt.timedelta(days=day_off)
            for t in times:
                if day_off == 0 and t in done:
                    continue
                h, m = self._hm(t)
                cand = dt.datetime.combine(d, dt.time(h, m))
                if day_off == 0 and cand < dt.datetime.now() - dt.timedelta(hours=3):
                    continue  # missed by more than 3 hours (PC was off): skip that slot
                return cand
        return None

    def _upload_loop(self):
        while not self._stop.is_set():
            try:
                if self.active:
                    nxt = self.next_upload_time()
                    if self.upload_now or (nxt and dt.datetime.now() >= nxt):
                        forced = self.upload_now
                        self.upload_now = False
                        self.upload_next(slot=None if forced else nxt.strftime("%H:%M"))
            except Exception as e:
                self.log("error", f"YouTube upload error: {e}")
                logging.error(traceback.format_exc())
            self._stop.wait(45)

    def upload_next(self, iid=None, slot=None):
        it = self.item(iid) if iid else (self.q("SELECT * FROM items WHERE status='ready' ORDER BY id LIMIT 1") or [None])[0]
        if not it:
            return
        if slot:
            day = dt.date.today().isoformat()
            self.state.setdefault("slots_done", {}).setdefault(day, []).append(slot)
            self.state["slots_done"] = {k: v for k, v in self.state["slots_done"].items() if k >= (dt.date.today() - dt.timedelta(days=3)).isoformat()}
            self.save_state()
        if not it.get("file") or not os.path.exists(it["file"]):
            self.update(it["id"], status="planned", file=None)
            self.log("warn", f"Video #{it['id']}'s file is missing (NeonClip was probably closed while making it), so it will be made again.")
            self.wake.set()
            return
        with self.browser_lock:
            self.update(it["id"], status="uploading")
            self.set_task(f"uploading: {(it['title'] or '')[:40]}")
            try:
                tags = json.loads(it["tags"] or "[]") + list(self.s["upload"].get("default_tags") or [])
                url = studio.upload(self.s, it["file"], it["title"] or "New video", it["description"] or "",
                                    tags=[t.lstrip("#") for t in tags][:25], thumbnail=it["thumb"], log=self.log,
                                    short=it["kind"] == "short")
                self.update(it["id"], status="uploaded", url=url, uploaded_at=time.time())
                self.log("info", f"📺 Uploaded: {it['title']}\n{url}", notify=True, title="📺 Uploaded")
            except studio.NotSignedIn as e:
                self.update(it["id"], status="ready")
                self.s.set("paused", True)
                self.log("error", str(e), notify=True, title="🔒 YouTube sign-in needed", priority=5)
            except Exception as e:
                self.update(it["id"], status="failed", error=str(e)[:500])
                self.log("error", f"Upload failed: {e}", notify=True, title="⚠️ Upload failed", priority=4)
            finally:
                self.set_task("idle")
                self.push_state()

    def _cleanup(self):
        days = int(self.s.get("keep_finished_days") or 0)
        if not days:
            return
        cutoff = time.time() - days * 86400
        for it in self.q("SELECT * FROM items WHERE status='uploaded' AND uploaded_at < ? AND file IS NOT NULL", (cutoff,)):
            for f in (it["file"], it["thumb"]):
                if f and os.path.exists(f):
                    try:
                        os.remove(f)
                    except OSError:
                        pass
            shutil.rmtree(os.path.join(data_dir(), "yt-work", str(it["id"])), ignore_errors=True)
            self.update(it["id"], file=None)

    # -------------------------------------------------------------- commands
    def run_command(self, text):
        parts = text.strip().split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""
        arg = parts[1].strip() if len(parts) > 1 else ""
        s = self.s
        if cmd in ("help", "?"):
            return YT_HELP
        if cmd == "status":
            return self.status_text()
        if cmd == "state":
            return None
        if cmd == "pause":
            s.set("paused", True)
            return "⏸ YouTube paused."
        if cmd in ("resume", "start"):
            s.set("paused", False)
            self.state.pop("ai_warned", None)
            self.save_state()
            self.wake.set()
            return "▶ YouTube running."
        if cmd == "make":
            words = arg.split()
            kind = "long"
            if words and words[0].lower().startswith(("short", "long", "video")):
                kind = "short" if words[0].lower().startswith("short") else "long"
                words = words[1:]
            mode = None
            if words and words[0].lower() in ("original", "repurpose", "repurposed"):
                mode = "repurpose" if words[0].lower().startswith("repurpose") else "original"
                words = words[1:]
            brief = " ".join(words).strip(" :-")
            iid = self.add_item(kind, mode, brief or None)
            self.wake.set()
            return (f"🎬 Making a {'Short' if kind == 'short' else 'long video'} now (#{iid})"
                    + (f" about: {brief[:120]}" if brief else "") + ".")
        if cmd == "train":
            a = arg.strip().lower()
            if a in ("on", "off"):
                s.set("training.enabled", a == "on")
                if a == "on":
                    threading.Thread(target=lambda: self._safe_train(), daemon=True).start()
                return "🧠 Training " + ("ON: reading your video stats and learning now." if a == "on" else "OFF.")
            return training.status_line(s)
        if cmd in ("learn", "train_now"):
            threading.Thread(target=self._safe_train, daemon=True).start()
            return "🧠 Reading stats and learning from your best videos..."
        if cmd in ("stats", "best", "leaderboard"):
            rows = training.leaderboard(self, 10)
            if not rows:
                return "No stats yet. Send 'yt learn' to read them."
            return "\n".join(f"{i}. {r['views']} views · {r['title'][:60]}" for i, r in enumerate(rows, 1))
        if cmd == "style":
            st = arg.strip().lower()
            if st not in ("stickman", "stock"):
                return "Use: style stickman  or  style stock"
            s.set("visual_style", st)
            return f"✔ Visual style: {st}"
        if cmd == "visual":
            s.set("visual_instructions", "" if arg.lower() == "clear" else arg, raw=True)
            return "✔ Visual direction " + ("cleared." if arg.lower() == "clear" else "saved. New videos will follow it.")
        if cmd == "upload":
            self.upload_now = True
            return "📺 Uploading the next finished video now."
        if cmd == "list":
            rows = self.q("SELECT id,kind,status,title FROM items ORDER BY id DESC LIMIT 15")
            return "\n".join(f"#{r['id']} {r['kind']} · {r['status']} · {r['title'] or '(writing)'}" for r in rows) or "Nothing yet."
        if cmd == "skip" and arg.isdigit():
            self.update(int(arg), status="skipped")
            return f"Skipped #{arg}."
        if cmd == "retry" and arg.isdigit():
            it = self.item(int(arg))
            if not it:
                return "No such video."
            st = "ready" if it.get("file") and os.path.exists(it["file"]) else "planned"
            self.update(int(arg), status=st, error=None)
            self.wake.set()
            return f"🔁 #{arg} is back in the queue ({st})."
        if cmd == "set":
            k, _, v = arg.partition(" ")
            val = s.set(k, v.strip())
            self.wake.set()
            return f"✔ YouTube {k} = {'(saved)' if 'key' in k else json.dumps(val)[:300]}"
        if cmd == "get":
            v = s.get(arg)
            return f"{arg} = {json.dumps(v)[:1500]}" if v is not None else f"No YouTube setting named {arg}"
        if cmd == "settings":
            if self.notifier:
                self.notifier.send_data("ytsettings", s.masked())
            return None
        if cmd == "settings_json":
            s.replace_all(json.loads(arg))
            return "✔ YouTube settings saved."
        if cmd == "prompt":
            s.set("ai.custom_instructions", "" if arg.lower() == "clear" else arg, raw=True)
            return "✔ YouTube AI instructions updated."
        if cmd == "ask":
            ctx = {"status": self.status(), "recent": [e["text"] for e in self.q("SELECT text FROM events ORDER BY id DESC LIMIT 20")]}
            return ai.ask(s["ai"], "You are the assistant in NeonClip's YouTube section. Answer briefly.\n"
                          f"Info: {json.dumps(ctx)[:8000]}\nQuestion: {arg}")
        return self._natural(text)

    def _safe_train(self):
        try:
            pb = self.train(learn=True)
            if self.notifier and pb:
                tips = "\n".join("• " + d for d in (pb.get("do") or [])[:5])
                self.notifier.send(f"{pb.get('summary') or ''}\n{tips}", title="▶ YT · 🧠 Playbook", tags=["brain"])
        except Exception as e:
            self.log("warn", f"Training: {e}", notify=True, title="🧠 Training")

    def _natural(self, text):
        prompt = (YT_HELP + "\n\nYouTube settings (dotted paths for 'set'): " + json.dumps(self.s.masked())[:7000] +
                  "\n\nThe owner sent this from their phone: \"" + text[:6000] + "\"\nTurn it into commands from the list above "
                  "(WITHOUT the 'yt ' prefix). If it's a question, use 'ask'. If they ask for a video, use 'make short <brief>' or "
                  "'make long <brief>' and put EVERYTHING they asked for about that video (topic, theme, tone, details) in the brief. "
                  "If they describe how videos should LOOK (art style, animation, backgrounds, editing), use 'visual <their full "
                  "description>' (and 'style stickman' if they want a stickman/cutout style). If they describe how scripts should be "
                  "written, use 'prompt <their full text>'. Return JSON: {\"commands\": [\"...\"], \"reply\": \"short confirmation\"}")
        try:
            data = ai.parse_json(ai.ask(self.s["ai"], prompt, json_mode=True))
        except ai.NoAIKey:
            return "Unknown YouTube command. Send 'yt help' (or add an AI key in YouTube settings so I understand plain English)."
        outs = []
        for c in (data.get("commands") or [])[:8]:
            c = c[3:] if c.lower().startswith("yt ") else c
            if c.split(" ")[0].lower() in ("help", "status", "pause", "resume", "start", "make", "upload", "list", "skip", "retry",
                                           "set", "get", "settings", "prompt", "ask", "style", "visual", "train", "learn", "stats"):
                r = self.run_command(c)
                if r:
                    outs.append(r)
        return ((data.get("reply") or "") + ("\n" + "\n".join(outs) if outs else "")).strip()

    def handle_command(self, text):
        self.log("info", f"📱 YT command: {text[:100]}")
        reply = self.run_command(text)
        if reply and self.notifier:
            self.notifier.send(reply, title="▶ YT · Agent", tags=["robot"])
        self.push_state()


class NoSource(Exception):
    pass


def _dur(path):
    try:
        from agent.tools import media_duration
        return media_duration(path)
    except Exception:
        return 0


def _safe(name):
    return re.sub(r'[<>:"/\\|?*\n\r\t]', "", name or "").strip()[:80] or "video"


def _chapters(work):
    """YouTube chapters from the script's chapter titles (YouTube needs 3+, first at 0:00, each 10s+)."""
    try:
        with open(os.path.join(work, "segments.json"), "r", encoding="utf-8") as f:
            segs = json.load(f)
    except Exception:
        return ""
    marks = [x for x in segs if x.get("chapter")]
    if not marks:
        return ""
    lines, last = [], -999
    for i, m in enumerate(marks):
        st = 0 if i == 0 else m["start"]
        if st - last < 10:
            continue
        last = st
        lines.append(f"{int(st // 60)}:{int(st % 60):02d} {m['chapter']}")
    return "Chapters\n" + "\n".join(lines) if len(lines) >= 3 else ""
