"""The PC window for Clip Cartel Agent."""
import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

from . import poster
from .config import data_dir

BG = "#0B0B0C"
PANEL = "#16161A"
FG = "#F2F2F2"
MUTED = "#9A9AA5"
RED = "#E5252A"
YEL = "#FFD400"

APK_URL = "https://neon-forger.github.io/NeonFuel/#clipcartel"


def open_path(p):
    if sys.platform == "win32":
        os.startfile(p)  # noqa
    elif sys.platform == "darwin":
        subprocess.Popen(["open", p])
    else:
        subprocess.Popen(["xdg-open", p])


class App:
    def __init__(self, agent):
        self.agent = agent
        self.q = queue.Queue()
        agent.listeners.append(lambda lvl, txt: self.q.put((lvl, txt)))
        self.root = tk.Tk()
        self.root.title("Clip Cartel Agent")
        self.root.geometry("1100x760")
        self.root.configure(bg=BG)
        try:
            from .config import resource_path
            self.root.iconphoto(True, tk.PhotoImage(file=resource_path("assets", "icon.png")))
        except Exception:
            pass
        self._style()
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(300, self._pump)
        self.root.after(1000, self._refresh)

    # ------------------------------------------------------------- styling
    def _style(self):
        st = ttk.Style(self.root)
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure(".", background=BG, foreground=FG, fieldbackground=PANEL, font=("Segoe UI", 10))
        st.configure("TNotebook", background=BG, borderwidth=0)
        st.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(16, 8), font=("Segoe UI Semibold", 10))
        st.map("TNotebook.Tab", background=[("selected", RED)], foreground=[("selected", "#fff")])
        st.configure("TFrame", background=BG)
        st.configure("Card.TFrame", background=PANEL)
        st.configure("TLabel", background=BG, foreground=FG)
        st.configure("Card.TLabel", background=PANEL, foreground=FG)
        st.configure("Muted.TLabel", background=BG, foreground=MUTED)
        st.configure("Big.TLabel", background=PANEL, foreground=FG, font=("Segoe UI Black", 20))
        st.configure("Num.TLabel", background=PANEL, foreground=YEL, font=("Segoe UI Black", 26))
        st.configure("TButton", background=PANEL, foreground=FG, padding=(12, 7), borderwidth=0)
        st.map("TButton", background=[("active", "#2A2A31")])
        st.configure("Accent.TButton", background=RED, foreground="#fff", font=("Segoe UI Semibold", 10))
        st.map("Accent.TButton", background=[("active", "#C71F23")])
        st.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=FG, rowheight=26, borderwidth=0)
        st.configure("Treeview.Heading", background="#202026", foreground=MUTED)
        st.map("Treeview", background=[("selected", "#3A1416")])
        st.configure("TEntry", fieldbackground="#202026", foreground=FG, insertcolor=FG)
        st.configure("TCheckbutton", background=BG, foreground=FG)
        st.configure("TCombobox", fieldbackground="#202026", foreground=FG)

    # --------------------------------------------------------------- layout
    def _build(self):
        head = tk.Frame(self.root, bg=BG)
        head.pack(fill="x", padx=18, pady=(14, 6))
        tk.Label(head, text="CLIP", bg=BG, fg=FG, font=("Segoe UI Black", 22)).pack(side="left")
        tk.Label(head, text=" CARTEL", bg=BG, fg=RED, font=("Segoe UI Black", 22)).pack(side="left")
        tk.Label(head, text="  agent", bg=BG, fg=MUTED, font=("Segoe UI", 14)).pack(side="left", pady=(8, 0))
        self.pause_btn = ttk.Button(head, text="Pause", command=self._toggle_pause, style="Accent.TButton")
        self.pause_btn.pack(side="right")

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=14, pady=8)
        self.nb = nb
        for name, fn in (("Dashboard", self._tab_dash), ("Clips", self._tab_clips), ("Sources", self._tab_sources),
                         ("Settings", self._tab_settings), ("Accounts & Phone", self._tab_accounts)):
            f = ttk.Frame(nb)
            nb.add(f, text=name)
            fn(f)

    # ---- dashboard
    def _tab_dash(self, f):
        top = ttk.Frame(f)
        top.pack(fill="x", pady=10)
        self.stat_labels = {}
        for key, label in (("ready", "Clips ready"), ("posted", "Posted"), ("submitted", "Submitted"), ("failed", "Failed")):
            card = ttk.Frame(top, style="Card.TFrame", padding=14)
            card.pack(side="left", fill="x", expand=True, padx=6)
            n = ttk.Label(card, text="0", style="Num.TLabel")
            n.pack(anchor="w")
            ttk.Label(card, text=label, style="Card.TLabel").pack(anchor="w")
            self.stat_labels[key] = n
        info = ttk.Frame(f, style="Card.TFrame", padding=14)
        info.pack(fill="x", padx=6, pady=4)
        self.task_lbl = ttk.Label(info, text="Starting...", style="Big.TLabel")
        self.task_lbl.pack(anchor="w")
        self.next_lbl = ttk.Label(info, text="", style="Card.TLabel")
        self.next_lbl.pack(anchor="w", pady=(4, 0))
        btns = ttk.Frame(f)
        btns.pack(fill="x", pady=8, padx=6)
        ttk.Button(btns, text="Check for new videos", command=lambda: self._cmd("run")).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="Post next clip now", command=lambda: self._cmd("post")).pack(side="left", padx=6)
        ttk.Button(btns, text="Clip a video link...", command=self._clip_link).pack(side="left", padx=6)
        ttk.Button(btns, text="Open clips folder", command=lambda: open_path(self._outdir())).pack(side="left", padx=6)
        ttk.Label(f, text="Activity", style="Muted.TLabel").pack(anchor="w", padx=8)
        self.logbox = tk.Text(f, bg=PANEL, fg=FG, insertbackground=FG, relief="flat", font=("Consolas", 10), wrap="word")
        self.logbox.pack(fill="both", expand=True, padx=6, pady=(2, 6))
        self.logbox.tag_config("error", foreground="#FF6B6B")
        self.logbox.tag_config("warn", foreground=YEL)
        for e in reversed(self.agent.db.events(120)):
            self._append(e["level"], e["text"])

    # ---- clips
    def _tab_clips(self, f):
        cols = ("id", "status", "score", "title", "link")
        tv = ttk.Treeview(f, columns=cols, show="headings")
        for c, w in zip(cols, (60, 100, 60, 520, 300)):
            tv.heading(c, text=c.title())
            tv.column(c, width=w, anchor="w")
        tv.pack(fill="both", expand=True, padx=6, pady=8)
        self.clips_tv = tv
        b = ttk.Frame(f)
        b.pack(fill="x", padx=6, pady=(0, 8))
        ttk.Button(b, text="Play", command=self._play).pack(side="left", padx=(0, 6))
        ttk.Button(b, text="Post this now", command=self._post_sel, style="Accent.TButton").pack(side="left", padx=6)
        ttk.Button(b, text="Skip", command=lambda: self._sel_cmd("skip")).pack(side="left", padx=6)
        ttk.Button(b, text="Retry", command=lambda: self._sel_cmd("retry")).pack(side="left", padx=6)
        ttk.Button(b, text="Open TikTok link", command=self._open_link).pack(side="left", padx=6)
        ttk.Button(b, text="Refresh", command=self._fill_clips).pack(side="right")
        self._fill_clips()

    def _fill_clips(self):
        tv = self.clips_tv
        tv.delete(*tv.get_children())
        for c in self.agent.db.clips(limit=500):
            tv.insert("", "end", iid=str(c["id"]), values=(c["id"], c["status"], int(c["score"] or 0), c["title"], c["tiktok_url"] or ""))

    def _sel(self):
        s = self.clips_tv.selection()
        return int(s[0]) if s else None

    def _play(self):
        c = self.agent.db.clip(self._sel() or -1)
        if c and c.get("file") and os.path.exists(c["file"]):
            open_path(c["file"])

    def _post_sel(self):
        cid = self._sel()
        if cid and messagebox.askyesno("Post now", f"Post clip #{cid} to TikTok now?"):
            threading.Thread(target=self.agent.post_next, args=(cid,), daemon=True).start()

    def _sel_cmd(self, cmd):
        cid = self._sel()
        if cid:
            self._cmd(f"{cmd} {cid}")
            self._fill_clips()

    def _open_link(self):
        c = self.agent.db.clip(self._sel() or -1)
        if c and c.get("tiktok_url"):
            webbrowser.open(c["tiktok_url"])

    # ---- sources
    SRC_FIELDS = [("name", "Name"), ("channel_url", "YouTube channel / playlist to watch"),
                  ("video_urls", "Specific video links (comma separated)"), ("title_must_contain", "Only videos whose title contains"),
                  ("only_newer_than_days", "Only videos newer than (days)"), ("campaign_url", "Content Rewards campaign link"),
                  ("required_hashtags", "Required hashtags (space separated)"), ("extra_hashtags", "Extra hashtags"),
                  ("clips_per_video", "Clips per video"), ("notes_for_ai", "Notes for the AI")]

    def _tab_sources(self, f):
        left = ttk.Frame(f)
        left.pack(side="left", fill="y", padx=6, pady=8)
        self.src_list = tk.Listbox(left, bg=PANEL, fg=FG, selectbackground=RED, relief="flat", width=28, font=("Segoe UI", 11))
        self.src_list.pack(fill="y", expand=True)
        self.src_list.bind("<<ListboxSelect>>", lambda e: self._load_src())
        ttk.Button(left, text="+ New source", command=self._new_src).pack(fill="x", pady=(6, 0))
        ttk.Button(left, text="Remove", command=self._del_src).pack(fill="x", pady=(6, 0))
        right = ttk.Frame(f)
        right.pack(side="left", fill="both", expand=True, padx=12, pady=8)
        self.src_vars = {}
        for key, label in self.SRC_FIELDS:
            ttk.Label(right, text=label, style="Muted.TLabel").pack(anchor="w", pady=(6, 0))
            v = tk.StringVar()
            ttk.Entry(right, textvariable=v).pack(fill="x")
            self.src_vars[key] = v
        self.src_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(right, text="Enabled", variable=self.src_enabled).pack(anchor="w", pady=8)
        ttk.Button(right, text="Save source", command=self._save_src, style="Accent.TButton").pack(anchor="w")
        ttk.Label(right, text="Only clip creators whose Content Rewards campaign you've joined; that's what gives you permission.",
                  style="Muted.TLabel").pack(anchor="w", pady=10)
        self._fill_src()

    def _fill_src(self):
        self.src_list.delete(0, "end")
        for s in self.agent.settings["sources"]:
            self.src_list.insert("end", ("✓ " if s.get("enabled", True) else "  ") + s.get("name", "?"))

    def _load_src(self):
        sel = self.src_list.curselection()
        if not sel:
            return
        s = self.agent.settings["sources"][sel[0]]
        for k, v in self.src_vars.items():
            val = s.get(k, "")
            if isinstance(val, list):
                val = (", " if k == "video_urls" else " ").join(val)
            v.set(str(val))
        self.src_enabled.set(s.get("enabled", True))

    def _new_src(self):
        for v in self.src_vars.values():
            v.set("")
        self.src_vars["clips_per_video"].set("5")
        self.src_vars["only_newer_than_days"].set("7")
        self.src_list.selection_clear(0, "end")

    def _save_src(self):
        d = {k: v.get().strip() for k, v in self.src_vars.items()}
        src = {
            "name": d["name"] or "Untitled", "enabled": self.src_enabled.get(), "channel_url": d["channel_url"],
            "video_urls": [u.strip() for u in d["video_urls"].split(",") if u.strip()],
            "title_must_contain": d["title_must_contain"],
            "only_newer_than_days": int(d["only_newer_than_days"] or 0),
            "campaign_url": d["campaign_url"], "required_hashtags": d["required_hashtags"].split(),
            "extra_hashtags": d["extra_hashtags"].split(), "clips_per_video": int(d["clips_per_video"] or 5),
            "notes_for_ai": d["notes_for_ai"],
        }
        lst = self.agent.settings["sources"]
        sel = self.src_list.curselection()
        if sel:
            lst[sel[0]] = src
        else:
            lst.append(src)
        self.agent.settings.set("sources", lst)
        self._fill_src()
        messagebox.showinfo("Saved", "Source saved.")

    def _del_src(self):
        sel = self.src_list.curselection()
        if sel and messagebox.askyesno("Remove", "Remove this source?"):
            lst = self.agent.settings["sources"]
            lst.pop(sel[0])
            self.agent.settings.set("sources", lst)
            self._fill_src()

    # ---- settings
    FIELDS = [
        ("AI", [("ai.gemini_api_key", "Gemini API key", "secret"), ("ai.gemini_model", "Gemini model", ""),
                ("ai.openrouter_api_key", "OpenRouter API key", "secret"), ("ai.openrouter_model", "OpenRouter model", ""),
                ("ai.openai_compatible_base_url", "Other OpenAI-compatible API URL", ""),
                ("ai.openai_compatible_api_key", "Other API key", "secret"), ("ai.openai_compatible_model", "Other model", ""),
                ("ai.custom_instructions", "Extra instructions for the AI editor", "")]),
        ("Editing", [("edit.style", "Style (dramatic / clean)", ""), ("edit.min_seconds", "Min clip length (s)", "int"),
                     ("edit.max_seconds", "Max clip length (s)", "int"), ("edit.censor_swears", "Censor swear words in captions", "bool"),
                     ("edit.sound_effects", "Impact sound effects", "bool"), ("edit.progress_bar", "Progress bar", "bool"),
                     ("transcribe.model", "Speech-to-text model (base.en / small.en / medium.en)", ""),
                     ("output_dir", "Save clips to", "dir")]),
        ("Posting", [("posting.auto_post", "Post automatically", "bool"),
                     ("posting.submit_to_content_rewards", "Submit to Content Rewards after posting", "bool"),
                     ("posting.min_minutes_between_posts", "Minutes between posts", "int"),
                     ("posting.max_posts_per_day", "Max posts per day", "int"),
                     ("posting.quiet_hours_start", "No posting from (hour 0-23)", "int"),
                     ("posting.quiet_hours_end", "...until (hour 0-23)", "int"),
                     ("posting.browser", "Browser for sign-in & posting (opera_gx / edge / chrome / path to .exe)", ""),
                     ("posting.headless", "Hide the browser while posting", "bool"),
                     ("check_sources_every_minutes", "Check for new videos every (minutes)", "int"),
                     ("start_with_windows", "Start with Windows", "bool"), ("keep_pc_awake", "Keep the PC awake", "bool")]),
    ]

    def _tab_settings(self, f):
        canvas = tk.Canvas(f, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(f, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw", width=1040)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))
        self.set_vars = {}
        for section, fields in self.FIELDS:
            tk.Label(inner, text=section, bg=BG, fg=RED, font=("Segoe UI Black", 13)).pack(anchor="w", pady=(14, 2), padx=8)
            for key, label, kind in fields:
                row = ttk.Frame(inner)
                row.pack(fill="x", padx=8, pady=3)
                val = self.agent.settings.get(key)
                if kind == "bool":
                    v = tk.BooleanVar(value=bool(val))
                    ttk.Checkbutton(row, text=label, variable=v).pack(anchor="w")
                else:
                    ttk.Label(row, text=label, width=46).pack(side="left")
                    v = tk.StringVar(value="" if val is None else str(val))
                    e = ttk.Entry(row, textvariable=v, show="•" if kind == "secret" else "")
                    e.pack(side="left", fill="x", expand=True)
                    if kind == "dir":
                        ttk.Button(row, text="...", width=3,
                                   command=lambda v=v: v.set(filedialog.askdirectory() or v.get())).pack(side="left", padx=4)
                self.set_vars[key] = (v, kind)
        b = ttk.Frame(inner)
        b.pack(fill="x", padx=8, pady=16)
        ttk.Button(b, text="Save settings", command=self._save_settings, style="Accent.TButton").pack(side="left")
        ttk.Button(b, text="Edit all settings (settings.json)", command=lambda: open_path(self.agent.settings.path)).pack(side="left", padx=8)
        ttk.Button(b, text="Reload settings.json", command=self._reload).pack(side="left")
        ttk.Button(b, text="Open app source folder", command=lambda: open_path(os.path.join(os.path.dirname(sys.executable), "source") if getattr(sys, "frozen", False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))).pack(side="left", padx=8)

    def _save_settings(self):
        for key, (v, kind) in self.set_vars.items():
            val = v.get()
            if kind == "int":
                try:
                    val = int(val)
                except ValueError:
                    continue
            self.agent.settings.set(key, val)
        self._apply_startup()
        self.agent.wake.set()
        messagebox.showinfo("Saved", "Settings saved.")

    def _reload(self):
        self.agent.settings.load()
        for key, (v, kind) in self.set_vars.items():
            val = self.agent.settings.get(key)
            v.set(bool(val) if kind == "bool" else ("" if val is None else str(val)))
        self._fill_src()

    def _apply_startup(self):
        if sys.platform != "win32":
            return
        startup = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
        target = os.path.join(startup, "ClipCartelAgent.cmd")
        try:
            if self.agent.settings["start_with_windows"]:
                if getattr(sys, "frozen", False):
                    cwd, launch = os.path.dirname(sys.executable), f'start "" "{sys.executable}"'
                else:
                    cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    pyw = sys.executable.replace("python.exe", "pythonw.exe")
                    launch = f'start "" "{pyw}" -m agent'
                with open(target, "w") as fh:
                    fh.write(f'@echo off\ncd /d "{cwd}"\n{launch}\n')
            elif os.path.exists(target):
                os.remove(target)
        except Exception as e:
            self.agent.log("warn", f"Couldn't update Start with Windows: {e}")

    # ---- accounts & phone
    def _tab_accounts(self, f):
        c1 = ttk.Frame(f, style="Card.TFrame", padding=16)
        c1.pack(fill="x", padx=6, pady=10)
        ttk.Label(c1, text="1. Sign in (once): easiest from the phone app → Accounts", style="Big.TLabel").pack(anchor="w")
        ttk.Label(c1, text="Opens the agent's own Opera GX window (separate from your normal Opera profile) with TikTok and Content Rewards. Sign in to both, then close the window.\n"
                           "Use the same TikTok account you linked on Content Rewards (@clipping_cartel_1).",
                  style="Card.TLabel").pack(anchor="w", pady=6)
        ttk.Button(c1, text="Sign in to TikTok + Content Rewards", style="Accent.TButton", command=self._login).pack(anchor="w")

        c2 = ttk.Frame(f, style="Card.TFrame", padding=16)
        c2.pack(fill="x", padx=6, pady=10)
        ttk.Label(c2, text="2. Connect your phone", style="Big.TLabel").pack(anchor="w")
        n = self.agent.settings["ntfy"]
        ttk.Label(c2, text="Install the Clip Cartel phone app, then enter this server and topic in its Connect screen:",
                  style="Card.TLabel").pack(anchor="w", pady=6)
        self.topic_var = tk.StringVar(value=n["topic"])
        row = ttk.Frame(c2, style="Card.TFrame")
        row.pack(anchor="w", fill="x")
        tk.Label(row, text=n["server"] + "  ·  ", bg=PANEL, fg=MUTED, font=("Consolas", 13)).pack(side="left")
        tk.Entry(row, textvariable=self.topic_var, bg="#202026", fg=YEL, relief="flat", font=("Consolas", 16), width=30,
                 readonlybackground="#202026", state="readonly").pack(side="left")
        ttk.Button(row, text="Copy", command=lambda: (self.root.clipboard_clear(), self.root.clipboard_append(n["topic"]))).pack(side="left", padx=8)
        row2 = ttk.Frame(c2, style="Card.TFrame")
        row2.pack(anchor="w", fill="x", pady=(8, 0))
        tk.Label(row2, text="Pairing code (for signing in from your phone):  ", bg=PANEL, fg=MUTED, font=("Segoe UI", 11)).pack(side="left")
        tk.Label(row2, text=n.get("pair_code", ""), bg=PANEL, fg=YEL, font=("Consolas", 18, "bold")).pack(side="left")
        b = ttk.Frame(c2, style="Card.TFrame")
        b.pack(anchor="w", pady=8)
        ttk.Button(b, text="Send test notification", command=lambda: self.agent.ntfy.send("If you can read this, your phone is connected ✅",
                                                                                          title="🤖 Test from Clip Cartel Agent", tags=["tada"])).pack(side="left")
        ttk.Button(b, text="Get the phone app", command=lambda: webbrowser.open(APK_URL)).pack(side="left", padx=8)
        ttk.Button(b, text="Download latest PC version", command=lambda: webbrowser.open(
            "https://github.com/Neon-Forger/Clipping-Agent/releases/latest")).pack(side="left")
        ttk.Label(c2, text="Anyone who knows the topic can read and control the agent, so keep it private.",
                  style="Card.TLabel").pack(anchor="w")

    def _login(self):
        if not self.agent.browser_lock.acquire(blocking=False):
            messagebox.showwarning("Busy", "The agent is using the browser right now (posting). Try again in a few minutes.")
            return

        def go():
            try:
                poster.open_for_login(self.agent.settings["posting"], ["https://www.tiktok.com/login", "https://contentrewards.com/c/home"])
                self.agent.state.pop("signin_needed", None)
                self.agent.save_state()
                self.agent.log("info", "Sign-in window closed")
            except Exception as e:
                self.agent.log("error", f"Couldn't open the browser: {e}. Check the browser setting in Settings → Posting.")
            finally:
                self.agent.browser_lock.release()
        threading.Thread(target=go, daemon=True).start()

    # ------------------------------------------------------------- helpers
    def _outdir(self):
        d = self.agent.settings["output_dir"]
        os.makedirs(d, exist_ok=True)
        return d

    def _cmd(self, text):
        def go():
            r = self.agent.run_command(text, allow_ai=False)
            if r:
                self.q.put(("info", r))
            self.agent.push_state()
        threading.Thread(target=go, daemon=True).start()

    def _clip_link(self):
        top = tk.Toplevel(self.root, bg=BG)
        top.title("Clip a video")
        ttk.Label(top, text="Video link (YouTube, Twitch VOD, Kick, etc.)").pack(padx=14, pady=(14, 4), anchor="w")
        v = tk.StringVar()
        ttk.Entry(top, textvariable=v, width=70).pack(padx=14)
        ttk.Label(top, text="How many clips").pack(padx=14, pady=(10, 4), anchor="w")
        n = tk.StringVar(value="5")
        ttk.Entry(top, textvariable=n, width=6).pack(padx=14, anchor="w")
        ttk.Button(top, text="Start", style="Accent.TButton",
                   command=lambda: (self._cmd(f"clip {v.get().strip()} {n.get().strip()}"), top.destroy())).pack(padx=14, pady=14, anchor="w")

    def _toggle_pause(self):
        self._cmd("resume" if self.agent.paused else "pause")
        self.root.after(400, self._refresh_once)

    def _append(self, lvl, txt):
        self.logbox.insert("end", txt + "\n", lvl if lvl in ("error", "warn") else None)
        self.logbox.see("end")

    def _pump(self):
        try:
            while True:
                lvl, txt = self.q.get_nowait()
                if lvl == "task":
                    self.task_lbl.config(text=("⏸ Paused · " if self.agent.paused else "") + txt.capitalize())
                else:
                    self._append(lvl, txt)
        except queue.Empty:
            pass
        self.root.after(300, self._pump)

    def _refresh_once(self):
        s = self.agent.status()
        for k, lbl in self.stat_labels.items():
            lbl.config(text=str(s.get(k, 0)))
        self.task_lbl.config(text=("⏸ Paused · " if s["paused"] else "▶ ") + s["task"].capitalize())
        self.next_lbl.config(text=f"Next post: {s['next_post'] or 'when a clip is ready'}")
        self.pause_btn.config(text="Resume" if s["paused"] else "Pause")

    def _refresh(self):
        try:
            self._refresh_once()
        except Exception:
            pass
        self.root.after(5000, self._refresh)

    def _on_close(self):
        if messagebox.askyesno("Quit Clip Cartel Agent?", "Quit the agent? It will stop clipping and posting.\n\nChoose No to minimize it instead."):
            self.agent.stop()
            self.root.destroy()
        else:
            self.root.iconify()

    def run(self):
        self.root.mainloop()
