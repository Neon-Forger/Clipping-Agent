"""NeonClip main window: a neon sidebar with two separate sections (Clipping, YouTube) and the phone link."""
import os
import sys
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

from . import theme

APP_PAGE = "https://neon-forger.github.io/NeonFuel/#neonclip"


class Shell:
    def __init__(self, clip_agent, yt_agent):
        self.agent, self.yt = clip_agent, yt_agent
        self.root = tk.Tk()
        self.root.title("NeonClip")
        self.root.geometry("1280x820")
        self.root.minsize(1100, 700)
        self.root.configure(bg=theme.BG)
        theme.load_fonts()
        theme.style(self.root)
        try:
            from agent.config import resource_path
            self.root.iconphoto(True, tk.PhotoImage(file=resource_path("assets", "icon.png")))
        except Exception:
            pass
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _build(self):
        side = tk.Frame(self.root, bg=theme.BG2, width=210)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        logo = tk.Canvas(side, bg=theme.BG2, height=90, width=210, highlightthickness=0)
        logo.pack(pady=(14, 4))
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            logo.create_text(105 + dx, 38 + dy, text="NEON", fill=theme.BLUE, font=(theme.DISPLAY, 24))
            logo.create_text(105 + dx, 70 + dy, text="CLIP", fill=theme.PINK, font=(theme.DISPLAY, 24))
        logo.create_text(105, 38, text="NEON", fill="#ffffff", font=(theme.DISPLAY, 24))
        logo.create_text(105, 70, text="CLIP", fill="#ffffff", font=(theme.DISPLAY, 24))
        tk.Frame(side, bg=theme.LINE, height=2).pack(fill="x", padx=18, pady=10)

        self.main = ttk.Frame(self.root)
        self.main.pack(side="left", fill="both", expand=True)

        from agent.gui import ClippingView
        from ytauto.gui import YouTubeView
        self.views = {"clip": ClippingView(self.agent, self.root, self.main).frame,
                      "yt": YouTubeView(self.yt, self.root, self.main).frame,
                      "phone": self._phone_page(self.main)}
        self.nav = {}
        for key, label, color in (("clip", "CLIPPING", theme.PINK), ("yt", "YOUTUBE", theme.BLUE), ("phone", "PHONE", theme.ICE)):
            b = tk.Label(side, text=label, bg=theme.BG2, fg=theme.MUTED, font=(theme.DISPLAY, 11), anchor="w",
                         padx=22, pady=12, cursor="hand2")
            b.pack(fill="x", padx=8, pady=3)
            b.bind("<Button-1>", lambda e, k=key: self.show(k))
            b.bind("<Enter>", lambda e, b=b, c=color: b.config(fg=c))
            b.bind("<Leave>", lambda e, b=b, k=key: b.config(fg=self._nav_color(k)))
            self.nav[key] = (b, color)
        tk.Label(side, text="Two separate sections:\nnothing is shared\nbetween them.", bg=theme.BG2, fg=theme.MUTED,
                 font=(theme.BODY, 9), justify="left").pack(side="bottom", anchor="w", padx=22, pady=16)
        self.current = None
        self.show("yt" if not self.yt.s["setup_done"] and not self.agent.db.clips(limit=1) else "clip")

    def _nav_color(self, k):
        return self.nav[k][1] if k == self.current else theme.MUTED

    def show(self, key):
        for k, v in self.views.items():
            v.pack_forget()
        self.views[key].pack(fill="both", expand=True)
        self.current = key
        for k, (b, c) in self.nav.items():
            b.config(fg=c if k == key else theme.MUTED, bg=theme.PANEL if k == key else theme.BG2)

    def _phone_page(self, parent):
        f = ttk.Frame(parent)
        head = ttk.Frame(f)
        head.pack(fill="x", padx=14, pady=(10, 0))
        theme.neon_title(head, "PHONE", accent=theme.ICE, size=18).pack(side="left")
        n = self.agent.settings["ntfy"]
        c = ttk.Frame(f, style="Card.TFrame", padding=18)
        c.pack(fill="x", padx=20, pady=14)
        ttk.Label(c, text="CONNECT THE NEONCLIP PHONE APP", style="Big.TLabel").pack(anchor="w")
        ttk.Label(c, text="Install the NeonClip app on your phone, then type these into its Connect screen. "
                          "The phone app shows both sections (Clipping and YouTube) and can control them.",
                  style="CardMuted.TLabel", wraplength=900).pack(anchor="w", pady=(4, 12))
        for label, value in (("Server", n["server"]), ("Topic", n["topic"]), ("Pairing code", n.get("pair_code", ""))):
            r = ttk.Frame(c, style="Card.TFrame")
            r.pack(anchor="w", pady=4)
            tk.Label(r, text=f"{label}:", bg=theme.PANEL, fg=theme.MUTED, font=(theme.BODY, 11), width=14, anchor="w").pack(side="left")
            e = tk.Entry(r, bg=theme.PANEL2, fg=theme.ICE, relief="flat", font=(theme.MONO, 16), width=34,
                         readonlybackground=theme.PANEL2)
            e.insert(0, value)
            e.config(state="readonly")
            e.pack(side="left")
            ttk.Button(r, text="Copy", command=lambda v=value: (self.root.clipboard_clear(), self.root.clipboard_append(v))).pack(side="left", padx=8)
        b = ttk.Frame(c, style="Card.TFrame")
        b.pack(anchor="w", pady=12)
        ttk.Button(b, text="Send test notification", style="Accent.TButton",
                   command=lambda: self.agent.ntfy.send("If you can read this, your phone is connected ✅", title="NeonClip test", tags=["tada"])).pack(side="left")
        ttk.Button(b, text="Get the phone app", command=lambda: webbrowser.open(APP_PAGE)).pack(side="left", padx=8)
        ttk.Button(b, text="Download latest PC version", command=lambda: webbrowser.open(
            "https://github.com/Neon-Forger/Clipping-Agent/releases/latest")).pack(side="left")
        ttk.Label(c, text="Anyone who knows the topic can read and control NeonClip. Keep it private.",
                  style="CardMuted.TLabel").pack(anchor="w")
        return f

    def _close(self):
        if messagebox.askyesno("Quit NeonClip?", "Quit NeonClip? Clipping and YouTube automation stop until you open it again.\n\n"
                                                 "Choose No to minimize it instead."):
            self.agent.stop()
            self.yt.stop()
            self.root.destroy()
        else:
            self.root.iconify()

    def run(self):
        self.root.mainloop()
