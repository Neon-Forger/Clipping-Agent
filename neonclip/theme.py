"""NeonClip look: the synthwave neon style of the Neon Forger sites (NeonFuel / Neon Freeze)."""
import os
import sys
import tkinter as tk
from tkinter import ttk

BG = "#040915"
BG2 = "#071533"
PANEL = "#0A1630"
PANEL2 = "#0E1E40"
LINE = "#12305E"
FG = "#E6F4FF"
MUTED = "#8AA0C4"
BLUE = "#00B4FF"
ICE = "#7FE9FF"
PINK = "#FF2BD6"
GOLD = "#FFD34D"
RED = "#FF4D6D"
GREEN = "#3DDC84"

DISPLAY = "Orbitron"
MONO = "Share Tech Mono"
BODY = "Segoe UI"


def load_fonts():
    """Makes the bundled Orbitron / Share Tech Mono fonts usable in the window (Windows)."""
    global DISPLAY, MONO
    try:
        from agent.tools import fonts_dir
        if sys.platform == "win32":
            import ctypes
            for f in ("Orbitron-ExtraBold.ttf", "Orbitron-SemiBold.ttf", "ShareTechMono-Regular.ttf"):
                ctypes.windll.gdi32.AddFontResourceExW(os.path.join(fonts_dir(), f), 0x10, 0)
    except Exception:
        pass
    try:
        import tkinter.font as tkfont
        fams = set(tkfont.families())
        if "Orbitron ExtraBold" in fams:
            DISPLAY = "Orbitron ExtraBold"
        elif "Orbitron" not in fams:
            DISPLAY = "Segoe UI Black" if sys.platform == "win32" else "DejaVu Sans"
        if "Share Tech Mono" not in fams:
            MONO = "Consolas" if sys.platform == "win32" else "DejaVu Sans Mono"
        global BODY
        if sys.platform != "win32":
            BODY = "DejaVu Sans"
    except Exception:
        DISPLAY, MONO = "Segoe UI Black", "Consolas"


def style(root):
    st = ttk.Style(root)
    try:
        st.theme_use("clam")
    except Exception:
        pass
    st.configure(".", background=BG, foreground=FG, fieldbackground=PANEL2, font=(BODY, 10), bordercolor=LINE,
                 lightcolor=LINE, darkcolor=LINE, troughcolor=PANEL)
    st.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 4, 0, 0))
    st.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(16, 8), font=(DISPLAY, 9), borderwidth=0)
    st.map("TNotebook.Tab", background=[("selected", BG2)], foreground=[("selected", ICE)])
    st.configure("TFrame", background=BG)
    st.configure("Card.TFrame", background=PANEL)
    st.configure("TLabel", background=BG, foreground=FG)
    st.configure("Card.TLabel", background=PANEL, foreground=FG)
    st.configure("Muted.TLabel", background=BG, foreground=MUTED)
    st.configure("CardMuted.TLabel", background=PANEL, foreground=MUTED)
    st.configure("Big.TLabel", background=PANEL, foreground=FG, font=(DISPLAY, 15))
    st.configure("H.TLabel", background=BG, foreground=PINK, font=(DISPLAY, 12))
    st.configure("Num.TLabel", background=PANEL, foreground=ICE, font=(DISPLAY, 24))
    st.configure("TButton", background=PANEL2, foreground=FG, padding=(12, 7), borderwidth=1, focuscolor=BLUE)
    st.map("TButton", background=[("active", LINE)], foreground=[("active", ICE)])
    st.configure("Accent.TButton", background=BLUE, foreground="#021018", font=(DISPLAY, 9))
    st.map("Accent.TButton", background=[("active", ICE)])
    st.configure("Pink.TButton", background=PINK, foreground="#12001a", font=(DISPLAY, 9))
    st.map("Pink.TButton", background=[("active", "#ff7be6")])
    st.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=FG, rowheight=26, borderwidth=0)
    st.configure("Treeview.Heading", background=PANEL2, foreground=ICE, font=(DISPLAY, 8))
    st.map("Treeview", background=[("selected", LINE)], foreground=[("selected", ICE)])
    st.configure("TEntry", fieldbackground=PANEL2, foreground=FG, insertcolor=ICE)
    st.configure("TCheckbutton", background=BG, foreground=FG)
    st.map("TCheckbutton", background=[("active", BG)], foreground=[("active", ICE)])
    st.configure("Card.TCheckbutton", background=PANEL, foreground=FG)
    st.configure("TCombobox", fieldbackground=PANEL2, foreground=FG, arrowcolor=ICE)
    st.configure("TSpinbox", fieldbackground=PANEL2, foreground=FG, arrowcolor=ICE)
    st.configure("Vertical.TScrollbar", background=PANEL2, troughcolor=BG, arrowcolor=ICE)
    root.option_add("*TCombobox*Listbox.background", PANEL2)
    root.option_add("*TCombobox*Listbox.foreground", FG)


def neon_title(parent, text, accent=PINK, size=20, bg=BG):
    """A heading with a soft neon glow (drawn on a canvas)."""
    c = tk.Canvas(parent, bg=bg, height=size * 2 + 6, highlightthickness=0, width=size * len(text) + 40)
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        c.create_text(8 + dx, size + 3 + dy, text=text, anchor="w", fill=accent, font=(DISPLAY, size))
    c.create_text(8, size + 3, text=text, anchor="w", fill="#ffffff", font=(DISPLAY, size))
    return c
