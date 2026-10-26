"""NeonClip → YouTube section (fully separate from Clipping)."""
import json
import os
import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

from agent.config import data_dir
from agent.gui import open_path
from neonclip import theme
from neonclip.theme import BG, FG, ICE, MUTED, PANEL, PINK

from . import studio, thumbs, visuals


class YouTubeView:
    def __init__(self, yt, root, container):
        self.yt = yt
        self.root = root
        self.q = queue.Queue()
        yt.listeners.append(lambda lvl, txt: self.q.put((lvl, txt)))
        self.frame = ttk.Frame(container)
        head = ttk.Frame(self.frame)
        head.pack(fill="x", padx=14, pady=(10, 0))
        theme.neon_title(head, "YOUTUBE", accent=theme.BLUE, size=18).pack(side="left")
        self.head_lbl = ttk.Label(head, text="", style="Muted.TLabel")
        self.head_lbl.pack(side="left", padx=10, pady=(10, 0))
        self.pause_btn = ttk.Button(head, text="Pause", command=self._toggle, style="Accent.TButton")
        self.pause_btn.pack(side="right")
        nb = ttk.Notebook(self.frame)
        nb.pack(fill="both", expand=True, padx=14, pady=8)
        self.nb = nb
        self.tabs = {}
        for name, fn in (("DASHBOARD", self._dash), ("VIDEOS", self._videos), ("CHANNEL", self._channel),
                         ("CONTENT", self._content), ("SETTINGS", self._settings)):
            f = ttk.Frame(nb)
            nb.add(f, text=name)
            self.tabs[name] = f
            fn(f)
        if not yt.s["setup_done"]:
            nb.select(self.tabs["CHANNEL"])
        self.root.after(400, self._pump)
        self.root.after(1200, self._refresh)

    # --------------------------------------------------------------- utils
    def _bg(self, fn, *a, done=None):
        def go():
            try:
                r = fn(*a)
                if done:
                    self.root.after(0, lambda: done(r))
            except Exception as e:
                msg = str(e)
                self.yt.log("error", msg)
                self.root.after(0, lambda: messagebox.showerror("NeonClip", msg))
        threading.Thread(target=go, daemon=True).start()

    def _cmd(self, text):
        def go():
            r = self.yt.run_command(text)
            if r:
                self.q.put(("info", r))
            self.yt.push_state()
        threading.Thread(target=go, daemon=True).start()

    def _card(self, parent, title, sub=None):
        c = ttk.Frame(parent, style="Card.TFrame", padding=16)
        c.pack(fill="x", padx=6, pady=8)
        ttk.Label(c, text=title, style="Big.TLabel").pack(anchor="w")
        if sub:
            ttk.Label(c, text=sub, style="CardMuted.TLabel", wraplength=980, justify="left").pack(anchor="w", pady=(4, 8))
        return c

    def _scroll(self, f):
        canvas = tk.Canvas(f, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(f, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        win = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win, width=e.width))
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", lambda ev: canvas.yview_scroll(int(-ev.delta / 120), "units")))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        return inner

    # ----------------------------------------------------------- dashboard
    def _dash(self, f):
        top = ttk.Frame(f)
        top.pack(fill="x", pady=10)
        self.stats = {}
        for key, label in (("ready", "Ready to upload"), ("planned", "Being made"), ("uploaded", "Uploaded"), ("failed", "Failed")):
            card = ttk.Frame(top, style="Card.TFrame", padding=14)
            card.pack(side="left", fill="x", expand=True, padx=6)
            n = ttk.Label(card, text="0", style="Num.TLabel")
            n.pack(anchor="w")
            ttk.Label(card, text=label, style="CardMuted.TLabel").pack(anchor="w")
            self.stats[key] = n
        info = ttk.Frame(f, style="Card.TFrame", padding=14)
        info.pack(fill="x", padx=6, pady=4)
        self.task_lbl = ttk.Label(info, text="", style="Big.TLabel")
        self.task_lbl.pack(anchor="w")
        self.next_lbl = ttk.Label(info, text="", style="CardMuted.TLabel")
        self.next_lbl.pack(anchor="w", pady=(4, 0))
        br = ttk.Frame(f)
        br.pack(fill="x", pady=(8, 0), padx=6)
        ttk.Label(br, text="Next video is about (optional, followed exactly):", style="Muted.TLabel").pack(side="left")
        self.brief_var = tk.StringVar()
        ttk.Entry(br, textvariable=self.brief_var).pack(side="left", fill="x", expand=True, padx=8)
        b = ttk.Frame(f)
        b.pack(fill="x", pady=8, padx=6)
        ttk.Button(b, text="Make a long video now", style="Accent.TButton", command=lambda: self._make("long")).pack(side="left", padx=(0, 6))
        ttk.Button(b, text="Make a Short now", command=lambda: self._make("short")).pack(side="left", padx=6)
        ttk.Button(b, text="Upload next now", command=lambda: self._cmd("upload")).pack(side="left", padx=6)
        ttk.Button(b, text="Open videos folder", command=lambda: open_path(self._outdir())).pack(side="left", padx=6)
        tr = ttk.Frame(f, style="Card.TFrame", padding=12)
        tr.pack(fill="x", padx=6, pady=4)
        row = ttk.Frame(tr, style="Card.TFrame")
        row.pack(fill="x")
        ttk.Label(row, text="🧠 TRAINING MODE", style="Big.TLabel").pack(side="left")
        self.train_var = tk.BooleanVar(value=bool((self.yt.s.get("training") or {}).get("enabled")))
        ttk.Checkbutton(row, text="Learn from my best videos and make more like them", variable=self.train_var,
                        style="Card.TCheckbutton", command=lambda: self._cmd("train " + ("on" if self.train_var.get() else "off"))).pack(side="left", padx=14)
        ttk.Button(row, text="Learn now", command=lambda: self._cmd("learn")).pack(side="right")
        ttk.Button(row, text="Best videos", command=self._show_best).pack(side="right", padx=6)
        self.train_lbl = ttk.Label(tr, text="", style="CardMuted.TLabel", wraplength=1000, justify="left")
        self.train_lbl.pack(anchor="w", pady=(6, 0))
        ttk.Label(f, text="Activity", style="Muted.TLabel").pack(anchor="w", padx=8)
        self.logbox = tk.Text(f, bg=PANEL, fg=FG, insertbackground=FG, relief="flat", font=(theme.MONO, 10), wrap="word", height=8)
        self.logbox.pack(fill="both", expand=True, padx=6, pady=(2, 6))
        self.logbox.tag_config("error", foreground=theme.RED)
        self.logbox.tag_config("warn", foreground=theme.GOLD)
        for e in reversed(self.yt.q("SELECT level, text FROM events ORDER BY id DESC LIMIT 120")):
            self._append(e["level"], e["text"])

    def _train_text(self):
        from . import training
        t = self.yt.s.get("training") or {}
        pb = t.get("playbook") or {}
        lines = [training.status_line(self.yt.s)]
        if pb.get("summary"):
            lines.append(pb["summary"])
        if pb.get("do"):
            lines.append("Doing more of: " + "; ".join(pb["do"][:4]))
        if pb.get("topics") and t.get("enabled"):
            used = set(t.get("topics_used") or [])
            nxt = [x for x in pb["topics"] if x not in used][:3]
            if nxt:
                lines.append("Next topics: " + " · ".join(nxt))
        return "\n".join(lines)

    def _show_best(self):
        from . import training
        top = tk.Toplevel(self.root, bg=BG)
        top.title("Best videos")
        top.geometry("820x480")
        cols = ("views", "likes", "comments", "kind", "title")
        tv = ttk.Treeview(top, columns=cols, show="headings")
        for c, w in zip(cols, (90, 70, 90, 60, 480)):
            tv.heading(c, text=c.upper())
            tv.column(c, width=w, anchor="w")
        tv.pack(fill="both", expand=True, padx=10, pady=10)
        rows = training.leaderboard(self.yt, 50)
        for r in rows:
            tv.insert("", "end", values=(r["views"], r["likes"] if r["likes"] is not None else "", r["comments"] if r["comments"] is not None else "",
                                         r["kind"], r["title"]))
        if not rows:
            ttk.Label(top, text="No stats yet. Click \"Learn now\" on the dashboard.", style="Muted.TLabel").pack(pady=8)

    def _make(self, kind):
        brief = " ".join(self.brief_var.get().split())
        self._cmd(f"make {kind} {brief}".strip())
        self.brief_var.set("")

    def _outdir(self):
        d = self.yt.s["output_dir"]
        os.makedirs(d, exist_ok=True)
        return d

    # -------------------------------------------------------------- videos
    def _videos(self, f):
        cols = ("id", "kind", "mode", "status", "views", "title", "link")
        tv = ttk.Treeview(f, columns=cols, show="headings")
        for c, w in zip(cols, (50, 60, 90, 90, 70, 460, 240)):
            tv.heading(c, text=c.upper())
            tv.column(c, width=w, anchor="w")
        tv.pack(fill="both", expand=True, padx=6, pady=8)
        self.tv = tv
        b = ttk.Frame(f)
        b.pack(fill="x", padx=6, pady=(0, 8))
        ttk.Button(b, text="Play", command=lambda: self._open_sel("file")).pack(side="left", padx=(0, 6))
        ttk.Button(b, text="Thumbnail", command=lambda: self._open_sel("thumb")).pack(side="left", padx=6)
        ttk.Button(b, text="Upload this now", style="Accent.TButton", command=self._upload_sel).pack(side="left", padx=6)
        ttk.Button(b, text="Skip", command=lambda: self._sel_cmd("skip")).pack(side="left", padx=6)
        ttk.Button(b, text="Retry", command=lambda: self._sel_cmd("retry")).pack(side="left", padx=6)
        ttk.Button(b, text="Open on YouTube", command=lambda: self._open_sel("url")).pack(side="left", padx=6)
        ttk.Button(b, text="Refresh", command=self._fill).pack(side="right")
        self._fill()

    def _fill(self):
        self.tv.delete(*self.tv.get_children())
        for r in self.yt.q("SELECT * FROM items ORDER BY id DESC LIMIT 300"):
            self.tv.insert("", "end", iid=str(r["id"]), values=(r["id"], r["kind"], r["mode"], r["status"],
                                                               "" if r.get("views") is None else r["views"], r["title"] or "(writing)", r["url"] or ""))

    def _selid(self):
        s = self.tv.selection()
        return int(s[0]) if s else None

    def _open_sel(self, field):
        it = self.yt.item(self._selid() or -1)
        if not it or not it.get(field):
            return
        if field == "url":
            webbrowser.open(it["url"])
        elif os.path.exists(it[field]):
            open_path(it[field])

    def _upload_sel(self):
        iid = self._selid()
        if iid and messagebox.askyesno("Upload", f"Upload video #{iid} to YouTube now?"):
            threading.Thread(target=self.yt.upload_next, args=(iid,), daemon=True).start()

    def _sel_cmd(self, cmd):
        iid = self._selid()
        if iid:
            self._cmd(f"{cmd} {iid}")
            self.root.after(500, self._fill)

    # ------------------------------------------------------------- channel
    def _channel(self, f):
        inner = self._scroll(f)
        s = self.yt.s
        c1 = self._card(inner, "1 · SIGN IN WITH GOOGLE",
                        "Opens a normal browser window (its own profile, separate from Clipping and from your everyday browser). "
                        "Sign in to the Google account that owns (or will own) the channel. You can leave that window open.")
        ttk.Button(c1, text="Sign in to YouTube", style="Accent.TButton",
                   command=lambda: self._bg(studio.sign_in, s, self.yt.log, False)).pack(anchor="w")

        c2 = self._card(inner, "2 · PICK OR CREATE THE CHANNEL",
                        "Use an existing channel: click \"Choose channel\", click the channel in the window that opens, "
                        "then click \"Use the open channel\".  New channel: click \"Create new channel\", follow YouTube's steps, "
                        "then click \"Use the open channel\".")
        row = ttk.Frame(c2, style="Card.TFrame")
        row.pack(anchor="w")
        ttk.Button(row, text="Choose channel", command=lambda: self._bg(studio.open_page, s, "https://www.youtube.com/channel_switcher", self.yt.log)).pack(side="left")
        ttk.Button(row, text="Create new channel", command=lambda: self._bg(studio.sign_in, s, self.yt.log, True)).pack(side="left", padx=8)
        ttk.Button(row, text="Use the open channel", style="Accent.TButton", command=self._detect).pack(side="left")
        self.ch_lbl = tk.Label(c2, text=self._ch_text(), bg=PANEL, fg=ICE, font=(theme.MONO, 13), anchor="w", justify="left")
        self.ch_lbl.pack(anchor="w", pady=(10, 0))

        c3 = self._card(inner, "3 · LOOK (PROFILE PICTURE + BANNER)",
                        "Make a neon profile picture and banner from your channel name and genre, then put them on the channel. "
                        "(Skip this for an old channel you want to keep as it looks.)")
        r3 = ttk.Frame(c3, style="Card.TFrame")
        r3.pack(anchor="w")
        ttk.Label(r3, text="Channel name", style="Card.TLabel").pack(side="left")
        self.name_var = tk.StringVar(value=s["channel"].get("name") or "")
        ttk.Entry(r3, textvariable=self.name_var, width=30).pack(side="left", padx=8)
        ttk.Label(r3, text="Tagline", style="Card.TLabel").pack(side="left")
        self.tag_var = tk.StringVar(value=s["channel"].get("description")[:60] if s["channel"].get("description") else "")
        ttk.Entry(r3, textvariable=self.tag_var, width=36).pack(side="left", padx=8)
        r4 = ttk.Frame(c3, style="Card.TFrame")
        r4.pack(anchor="w", pady=8)
        ttk.Button(r4, text="Make profile picture + banner", command=self._make_brand).pack(side="left")
        ttk.Button(r4, text="Put them on my channel", style="Accent.TButton", command=self._apply_brand).pack(side="left", padx=8)
        ttk.Button(r4, text="Open branding page", command=lambda: self._bg(
            studio.open_page, s, f"https://studio.youtube.com/channel/{s['channel'].get('channel_id', '')}/editing/images", self.yt.log)).pack(side="left")
        self.preview = tk.Label(c3, bg=PANEL)
        self.preview.pack(anchor="w")
        self._show_brand()

        c4 = self._card(inner, "4 · TURN IT ON",
                        "Set your genre and daily plan in CONTENT, add an AI key in SETTINGS, then switch it on. "
                        "Each day at the \"make at\" time it makes your videos and uploads them at your upload times while the PC is on.")
        self.on_var = tk.BooleanVar(value=bool(s["enabled"] and s["setup_done"]))
        ttk.Checkbutton(c4, text="YouTube automation ON", variable=self.on_var, style="Card.TCheckbutton", command=self._toggle_on).pack(anchor="w")

    def _ch_text(self):
        ch = self.yt.s["channel"]
        return f"Channel: {ch.get('name') or '(none yet)'}   {ch.get('channel_id') or ''}"

    def _detect(self):
        def done(info):
            s = self.yt.s
            s.set("channel.channel_id", info["id"])
            if info.get("name"):
                s.set("channel.name", info["name"])
                self.name_var.set(info["name"])
            self.ch_lbl.config(text=self._ch_text())
            self.yt.log("info", f"Using channel {info.get('name') or info['id']}", notify=True, title="📺 Channel selected")
        with_lock = lambda: self._locked(studio.current_channel, self.yt.s, self.yt.log)
        self._bg(with_lock, done=done)

    def _locked(self, fn, *a):
        if not self.yt.browser_lock.acquire(timeout=5):
            raise RuntimeError("The YouTube browser is busy (uploading). Try again in a few minutes.")
        try:
            return fn(*a)
        finally:
            self.yt.browser_lock.release()

    def _brand_paths(self):
        d = os.path.join(data_dir(), "yt-brand")
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, "profile.png"), os.path.join(d, "banner.png")

    def _make_brand(self):
        name = self.name_var.get().strip() or self.yt.s["channel"].get("name") or "NeonClip"
        tag = self.tag_var.get().strip()
        self.yt.s.set("channel.name", name)
        self.yt.s.set("channel.description", tag)
        av, bn = self._brand_paths()

        def go():
            art = None
            if self.yt.s["thumbnails"].get("ai_images"):
                art = visuals.ai_image(self.yt.s["ai"], f"Abstract neon synthwave artwork for a YouTube channel about {self.yt.s['genre'] or name}",
                                       os.path.join(os.path.dirname(av), "art.png"), "16:9")
            thumbs.avatar(name, av, art)
            thumbs.banner(name, tag, bn, art)
            self.yt.s.set("channel.avatar_file", av)
            self.yt.s.set("channel.banner_file", bn)
            return True
        self._bg(go, done=lambda _: self._show_brand())

    def _show_brand(self):
        av, bn = self.yt.s["channel"].get("avatar_file"), self.yt.s["channel"].get("banner_file")
        if not (av and bn and os.path.exists(av) and os.path.exists(bn)):
            return
        try:
            from PIL import Image, ImageTk
            a = Image.open(av).resize((140, 140))
            b = Image.open(bn).resize((420, 236))
            g = Image.new("RGB", (580, 236), BG)
            g.paste(a, (0, 48))
            g.paste(b, (160, 0))
            self._ph = ImageTk.PhotoImage(g)
            self.preview.config(image=self._ph)
        except Exception:
            pass

    def _apply_brand(self):
        ch = self.yt.s["channel"]
        if not ch.get("channel_id"):
            messagebox.showwarning("NeonClip", "Pick your channel first (step 2).")
            return
        if not ch.get("avatar_file"):
            messagebox.showwarning("NeonClip", "Make the profile picture + banner first.")
            return

        def done(ok):
            messagebox.showinfo("NeonClip", "Done ✅ (YouTube can take a few minutes to show it)." if ok else
                                "Couldn't finish automatically. Use \"Open branding page\" and upload the files from:\n" + os.path.dirname(ch["avatar_file"]))
        self._bg(lambda: self._locked(studio.set_branding, self.yt.s, ch["avatar_file"], ch["banner_file"], self.yt.log), done=done)

    def _toggle_on(self):
        s = self.yt.s
        if self.on_var.get():
            missing = []
            if not s["channel"].get("channel_id"):
                missing.append("pick a channel (step 2)")
            if not s["genre"]:
                missing.append("set a genre (CONTENT tab)")
            if not any(s["ai"].get(k) for k in ("gemini_api_key", "openrouter_api_key", "openai_compatible_api_key")):
                missing.append("add an AI key (SETTINGS tab)")
            if missing:
                self.on_var.set(False)
                messagebox.showwarning("NeonClip", "Before turning it on:\n• " + "\n• ".join(missing))
                return
            s.set("setup_done", True)
            s.set("enabled", True)
            s.set("paused", False)
            self.yt.log("info", "YouTube automation is ON", notify=True, title="▶ YouTube on")
        else:
            s.set("enabled", False)
        self.yt.wake.set()

    # ------------------------------------------------------------- content
    def _content(self, f):
        inner = self._scroll(f)
        s = self.yt.s
        self.cvars = {}
        c = self._card(inner, "WHAT THE CHANNEL MAKES")
        for key, label in (("genre", "Genre / niche (e.g. unsolved mysteries, space facts, motivational stories)"),
                           ("audience", "Audience"), ("language", "Language"), ("style_notes", "Always do / never do (notes for the AI)")):
            self._row(c, key, label)
        ttk.Label(c, text="Script instructions (how the narration is written: tone, structure, hooks, length...)",
                  style="Card.TLabel").pack(anchor="w", pady=(8, 2))
        self.script_text = self._text(c, s["ai"].get("custom_instructions") or "", 5)

        c = self._card(inner, "HOW VIDEOS LOOK",
                       "stock = stock footage / real photos with word captions.  stickman = a crude stickman cutout pasted over real "
                       "photos, flat app screens or black, with hard cuts, fly-ins, punch-in zooms and meme graphics (tier board, "
                       "progress ring, photo card, text panel). The AI plans every shot from your visual direction.")
        r = ttk.Frame(c, style="Card.TFrame")
        r.pack(fill="x", pady=3)
        ttk.Label(r, text="Visual style", style="Card.TLabel", width=58).pack(side="left")
        self.style_var = tk.StringVar(value=s.get("visual_style") or "stock")
        ttk.Combobox(r, textvariable=self.style_var, values=["stock", "stickman"], state="readonly", width=14).pack(side="left")
        ttk.Label(c, text="Visual direction (art style, placement, backgrounds, camera, graphics, things to never do)",
                  style="Card.TLabel").pack(anchor="w", pady=(8, 2))
        self.visual_text = self._text(c, s.get("visual_instructions") or "", 9)
        self.stick_caps = tk.BooleanVar(value=bool(s.get("stickman_captions")))
        ttk.Checkbutton(c, text="Word captions in the stickman style", variable=self.stick_caps,
                        style="Card.TCheckbutton").pack(anchor="w", pady=6)
        c = self._card(inner, "DAILY PLAN", "Runs while the PC is on and NeonClip is open. Times are 24h, your local time.")
        for key, label in (("daily.long_videos", "Long videos per day"), ("daily.shorts", "Shorts per day"),
                           ("daily.make_at", "Start making at (HH:MM)"), ("daily.upload_times", "Upload times (comma separated, e.g. 12:00, 15:00, 18:00)"),
                           ("long.minutes", "Long video length (minutes)"), ("shorts.seconds", "Short length (seconds)"),
                           ("mix.original", "% original AI videos"), ("mix.repurpose", "% repurposed videos")):
            self._row(c, key, label)
        c = self._card(inner, "REPURPOSE SOURCES",
                       "Only videos you're allowed to reuse: your own uploads, creators who gave you permission (e.g. a Content Rewards "
                       "campaign), or videos YouTube marks as Creative Commons. One per line: link | rights (own / permission / creative_commons)")
        self.src_text = tk.Text(c, height=6, bg=theme.PANEL2, fg=FG, insertbackground=ICE, relief="flat", font=(theme.MONO, 10))
        self.src_text.pack(fill="x")
        self.src_text.insert("1.0", "\n".join(f"{x.get('url', '')} | {x.get('rights', 'own')}" for x in s["sources"]))
        self.cc_var = tk.BooleanVar(value=bool(s["find_creative_commons"]))
        ttk.Checkbutton(c, text="Also search YouTube for Creative Commons videos in my genre (credited in the description)",
                        variable=self.cc_var, style="Card.TCheckbutton").pack(anchor="w", pady=6)
        ttk.Button(inner, text="Save content settings", style="Accent.TButton", command=self._save_content).pack(anchor="w", padx=8, pady=12)

    def _text(self, parent, value, height):
        t = tk.Text(parent, height=height, bg=theme.PANEL2, fg=FG, insertbackground=ICE, relief="flat", font=(theme.MONO, 10), wrap="word")
        t.pack(fill="x")
        t.insert("1.0", value)
        return t

    def _row(self, parent, key, label, secret=False):
        r = ttk.Frame(parent, style="Card.TFrame")
        r.pack(fill="x", pady=3)
        ttk.Label(r, text=label, style="Card.TLabel", width=58).pack(side="left")
        val = self.yt.s.get(key)
        if isinstance(val, list):
            val = ", ".join(str(v) for v in val)
        v = tk.StringVar(value="" if val is None else str(val))
        ttk.Entry(r, textvariable=v, show="•" if secret else "").pack(side="left", fill="x", expand=True)
        self.cvars[key] = v
        return v

    def _save_content(self):
        s = self.yt.s
        for key, v in self.cvars.items():
            if key.startswith(("ai.gemini", "ai.openrouter", "ai.openai")) or key in self._settings_keys():
                continue
            raw = v.get().strip()
            if key == "daily.upload_times":
                s.set(key, [t.strip() for t in raw.split(",") if t.strip()])
            elif key in ("daily.long_videos", "daily.shorts", "long.minutes", "shorts.seconds", "mix.original", "mix.repurpose"):
                try:
                    s.set(key, int(float(raw)))
                except ValueError:
                    pass
            else:
                s.set(key, raw)
        srcs = []
        for line in self.src_text.get("1.0", "end").splitlines():
            if not line.strip():
                continue
            url, _, rights = line.partition("|")
            rights = (rights.strip().lower() or "own").replace(" ", "_")
            if rights not in ("own", "permission", "creative_commons"):
                messagebox.showwarning("NeonClip", f"\"{rights}\" isn't a valid right. Use own, permission or creative_commons.")
                return
            srcs.append({"url": url.strip(), "rights": rights, "note": ""})
        s.set("sources", srcs)
        s.set("find_creative_commons", bool(self.cc_var.get()))
        s.set("ai.custom_instructions", self.script_text.get("1.0", "end").strip(), raw=True)
        s.set("visual_style", self.style_var.get() or "stock")
        s.set("visual_instructions", self.visual_text.get("1.0", "end").strip(), raw=True)
        s.set("stickman_captions", bool(self.stick_caps.get()))
        self.yt.wake.set()
        messagebox.showinfo("NeonClip", "Saved.")

    # ------------------------------------------------------------ settings
    SETTINGS = [
        ("AI (YouTube only)", [("ai.gemini_api_key", "Gemini API key", "secret"), ("ai.gemini_model", "Gemini model (auto = newest)", ""),
                               ("ai.openrouter_api_key", "OpenRouter API key", "secret"), ("ai.openrouter_model", "OpenRouter model", ""),
                               ("ai.openai_compatible_base_url", "Other OpenAI-compatible URL", ""),
                               ("ai.openai_compatible_api_key", "Other API key", "secret"), ("ai.openai_compatible_model", "Other model", "")]),
        ("Voice & footage", [("voice", "Voice (e.g. en-US-AndrewNeural, en-US-AriaNeural, en-GB-RyanNeural)", ""),
                             ("voice_rate", "Voice speed (e.g. +5% or -5%)", ""),
                             ("pexels_api_key", "Pexels API key (optional: pexels.com/api)", "secret"),
                             ("pixabay_api_key", "Pixabay API key (free photos + stock video: pixabay.com/api/docs)", "secret"),
                             ("unsplash_access_key", "Unsplash Access Key (free photos: unsplash.com/developers)", "secret"),
                             ("stock_video", "Search the web's free stock-video libraries for moving backgrounds "
                                             "(Wikimedia Commons, Internet Archive, NASA + Pexels/Pixabay with keys)", "bool"),
                             ("max_black_percent", "Most beats allowed to be plain black (%)", "int"),
                             ("music_folder", "Background music folder (only music you have rights to)", "dir"),
                             ("music_volume", "Music volume (0-1)", "float"), ("captions", "Burn in captions", "bool"),
                             ("thumbnails.ai_images", "Use AI images (thumbnails / visuals when no footage)", "bool")]),
        ("Upload", [("upload.visibility", "Visibility (public / unlisted / private)", ""),
                    ("upload.made_for_kids", "Made for kids", "bool"),
                    ("upload.altered_content", "Mark as altered/synthetic (realistic AI people or events)", "bool"),
                    ("upload.description_footer", "Text added to every description", ""),
                    ("upload.browser", "Browser (opera_gx / edge / chrome / path to .exe)", ""),
                    ("upload.headless", "Hide the browser while uploading", "bool"),
                    ("output_dir", "Save videos to", "dir"), ("keep_finished_days", "Delete uploaded files after (days, 0 = keep)", "int")]),
    ]

    def _settings_keys(self):
        return {k for _, fields in self.SETTINGS for k, _, _ in fields}

    def _settings(self, f):
        inner = self._scroll(f)
        self.svars = {}
        for section, fields in self.SETTINGS:
            ttk.Label(inner, text=section.upper(), style="H.TLabel").pack(anchor="w", padx=8, pady=(14, 2))
            for key, label, kind in fields:
                r = ttk.Frame(inner)
                r.pack(fill="x", padx=8, pady=3)
                val = self.yt.s.get(key)
                if kind == "bool":
                    v = tk.BooleanVar(value=bool(val))
                    ttk.Checkbutton(r, text=label, variable=v).pack(anchor="w")
                else:
                    ttk.Label(r, text=label, width=62).pack(side="left")
                    v = tk.StringVar(value="" if val is None else str(val))
                    ttk.Entry(r, textvariable=v, show="•" if kind == "secret" else "").pack(side="left", fill="x", expand=True)
                    if kind == "dir":
                        ttk.Button(r, text="...", width=3, command=lambda v=v: v.set(filedialog.askdirectory() or v.get())).pack(side="left", padx=4)
                self.svars[key] = (v, kind)
        b = ttk.Frame(inner)
        b.pack(fill="x", padx=8, pady=14)
        ttk.Button(b, text="Save settings", style="Accent.TButton", command=self._save_settings).pack(side="left")
        ttk.Button(b, text="Edit all settings (youtube.json)", command=lambda: open_path(self.yt.s.path)).pack(side="left", padx=8)
        ttk.Button(b, text="Test photo + video sources", command=self._test_photos).pack(side="left")

    def _test_photos(self):
        from agent.config import data_dir as _dd
        from . import photos

        from . import footage

        def go():
            return ("PHOTOS\n" + photos.test_sources(self.yt.s, os.path.join(_dd(), "yt-work", "_photos"))
                    + "\n\nSTOCK VIDEO\n" + footage.test_sources(self.yt.s, os.path.join(_dd(), "yt-work", "_footage")))
        self._bg(go, done=lambda rep: messagebox.showinfo("Photo + video sources", rep + "\n\nOpenverse, Wikimedia, Internet Archive "
                                                          "and NASA need no key. Pexels/Pixabay keys add a lot more stock footage."))

    def _save_settings(self):
        for key, (v, kind) in self.svars.items():
            val = v.get()
            if kind == "int":
                try:
                    val = int(val)
                except ValueError:
                    continue
            elif kind == "float":
                try:
                    val = float(val)
                except ValueError:
                    continue
            self.yt.s.set(key, val)
        if self.yt.s["paused"] and any(self.yt.s["ai"].get(k) for k in ("gemini_api_key", "openrouter_api_key", "openai_compatible_api_key")):
            self.yt.state.pop("ai_warned", None)
        self.yt.wake.set()
        messagebox.showinfo("NeonClip", "Saved.")

    # ------------------------------------------------------------- refresh
    def _toggle(self):
        self._cmd("resume" if self.yt.s["paused"] else "pause")
        self.root.after(400, self._refresh_once)

    def _append(self, lvl, txt):
        self.logbox.insert("end", txt + "\n", lvl if lvl in ("error", "warn") else None)
        self.logbox.see("end")

    def _pump(self):
        try:
            while True:
                lvl, txt = self.q.get_nowait()
                if lvl == "task":
                    self.task_lbl.config(text=txt.capitalize())
                else:
                    self._append(lvl, txt)
        except queue.Empty:
            pass
        self.root.after(300, self._pump)

    def _refresh_once(self):
        st = self.yt.status()
        for k, l in self.stats.items():
            l.config(text=str(st.get(k, 0)))
        if not st["setup_done"]:
            self.task_lbl.config(text="Not set up yet → CHANNEL tab")
        elif not st["enabled"]:
            self.task_lbl.config(text="Off → CHANNEL tab → step 4")
        else:
            self.task_lbl.config(text=("⏸ Paused · " if st["paused"] else "▶ ") + st["task"].capitalize())
        self.next_lbl.config(text=f"Next upload: {st['next_upload'] or 'when a video is ready'}")
        self.head_lbl.config(text=f"{st['channel'] or 'no channel yet'} · {st['genre'] or 'no genre yet'}")
        self.pause_btn.config(text="Resume" if st["paused"] else "Pause")
        self.train_lbl.config(text=self._train_text())
        self.train_var.set(bool(st.get("training")))

    def _refresh(self):
        try:
            self._refresh_once()
            if self.nb.index(self.nb.select()) == 1:
                pass
        except Exception:
            pass
        self.root.after(5000, self._refresh)
