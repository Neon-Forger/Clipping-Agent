"""Props: simple hand-drawn doodles of whatever the narration is about, shown big on a plain white or black
page with the character beside it pointing at it ("this is the lighthouse...", "they found a fingerprint...").

Where a prop comes from (first that works):
1. YOUR OWN IMAGE: put a picture in the props folder named after the thing (e.g. "claude ai.png") and it's used
   whenever that thing comes up. Use this for logos and brands you have the rights to show.
2. THE BUILT-IN LIBRARY: 170+ doodles in the character's marker style, each drawn on live and lightly animated.
3. AN AI IMAGE (optional, uses your Gemini key): asked for a simple marker line drawing, then converted to the same
   ink colour so it matches the rest of the video.
4. A FALLBACK doodle (a lightbulb / question mark) so the shot never comes out empty.

Brand logos are not drawn from memory: famous logos are trademarks. When the narration names a brand or product, the
prop shows a matching generic doodle (e.g. a chat bubble with a spark for an AI assistant) with the name hand-lettered
underneath, unless you drop the real logo into your props folder yourself."""
import math
import os
import random
import re

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from .sketch import PAPER, Pen, hand_font

PROPS = {}          # name -> (draw_fn, [keyword phrases], category)
_CHAR_FPS = 12


def prop(name, keywords="", cat="misc"):
    """Register a prop. keywords: comma-separated words/phrases that should bring this prop up."""
    def deco(fn):
        kws = [name.replace("_", " ")] + [k.strip().lower() for k in keywords.split(",") if k.strip()]
        PROPS[name] = (fn, kws, cat)
        return fn
    return deco


# ---- small geometry helpers for the drawings -------------------------------------------------------
def rot(pts, cx, cy, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return [(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c) for x, y in pts]


def scale(pts, cx, cy, k):
    return [(cx + (x - cx) * k, cy + (y - cy) * k) for x, y in pts]


def wave(t, speed=1.0, amp=1.0, phase=0.0):
    return math.sin(t * speed + phase) * amp


# the library registers itself on import (kept in separate files to stay readable)
from . import props_lib1, props_lib2, props_lib3   # noqa: E402,F401


# ---- finding the right prop ------------------------------------------------------------------------
def _norm(text):
    return re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower()).strip()


def _tokens(text):
    out = set()
    for w in _norm(text).split():
        out.add(w)
        if len(w) > 3 and w.endswith("s"):
            out.add(w[:-1])
        if len(w) > 4 and w.endswith("es"):
            out.add(w[:-2])
    return out


def find_prop(text):
    """Best library prop for a phrase like 'claude ai' or 'a stack of cash' (None if nothing fits)."""
    t = _norm(text)
    if not t:
        return None
    toks = _tokens(t)
    best, best_score = None, 0
    for name, (_, kws, _) in PROPS.items():
        hits = []
        for k in kws:
            if " " in k:
                if re.search(r"\b" + re.escape(k) + r"\b", t):
                    hits.append(6 + len(k.split()))
            elif k in toks:
                hits.append(3)
        if not hits:
            continue
        hits.sort(reverse=True)
        score = hits[0] + 0.25 * (len(hits) - 1)              # several matching words beat one
        nm = name.replace("_", " ")
        if nm == t:
            score = 20
        elif re.search(r"\b" + re.escape(nm) + r"\b", t):
            score += 3                                        # the prop's own name is in the phrase
        if score > best_score:
            best, best_score = name, score
    return best if best_score >= 3 else None


def user_props_dir():
    from agent.config import data_dir
    d = os.path.join(data_dir(), "props")
    os.makedirs(d, exist_ok=True)
    return d


def find_user_image(text):
    """An image the user dropped into the props folder whose file name matches (e.g. 'claude ai.png')."""
    t = _norm(text)
    if not t:
        return None
    try:
        files = os.listdir(user_props_dir())
    except OSError:
        return None
    toks = _tokens(t)
    best, best_score = None, 0
    for f in files:
        if not f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            continue
        stem = _norm(os.path.splitext(f)[0].replace("_", " ").replace("-", " "))
        if not stem:
            continue
        if stem == t:
            return os.path.join(user_props_dir(), f)
        words = set(stem.split())
        hit = len(words & toks)
        if hit and hit == len(words) and hit > best_score:
            best, best_score = os.path.join(user_props_dir(), f), hit
    return best


# ---- AI image -> same ink style ---------------------------------------------------------------------
def sticker(im, px):
    """White cut-out edge around a drawing (like the character), so black ink reads on a black page."""
    if px < 1:
        return im
    a = im.split()[3]
    k = max(3, int(px) | 1)
    edge = a.filter(ImageFilter.MaxFilter(k)).filter(ImageFilter.MaxFilter(3))
    out = Image.new("RGBA", im.size, (255, 255, 255, 0))
    out.putalpha(edge)
    out.alpha_composite(im)
    return out


def sketchify(img, paper="white"):
    """Turn a line drawing (or any picture) into black ink strokes on a transparent background."""
    g = ImageOps.autocontrast(img.convert("L"))
    if g.getpixel((2, 2)) < 128:              # dark background: invert so lines are dark
        g = ImageOps.invert(g)
    mask = g.point(lambda v: 255 if v < 140 else 0).filter(ImageFilter.MaxFilter(3))
    bbox = mask.getbbox()
    if bbox:
        mask = mask.crop(bbox)
    out = Image.new("RGBA", mask.size, (20, 20, 24, 0))
    out.putalpha(mask)
    return out


def ai_prop_image(s, text, paper="white", log=None):
    """Ask the AI image model for a simple marker doodle of `text`; cached. Returns the image path or None."""
    if not text or not (s.get("props_ai", True)):
        return None
    from agent.config import data_dir
    cache = os.path.join(data_dir(), "props_ai")
    os.makedirs(cache, exist_ok=True)
    key = re.sub(r"[^a-z0-9]+", "_", _norm(text))[:60] or "prop"
    path = os.path.join(cache, key + ".png")
    if not os.path.exists(path):
        from . import visuals
        prompt = (f"A very simple doodle icon of {text}, drawn with a thick black marker on a plain white background, "
                  f"bold outlines only, cartoon style, no shading, no background, centered, like a hand-drawn sticker")
        got = visuals.ai_image(s.get("ai", {}) if hasattr(s, "get") else {}, prompt, path, "1:1")
        if not got:
            return None
    return path if os.path.exists(path) else None


# ---- rendering ---------------------------------------------------------------------------------------
def _ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


class PropArt:
    """One library doodle rendered at a given size; draw-on reveal + boiling lines, cached per 12 fps frame."""

    REVEAL_S = 0.75

    def __init__(self, name, size, paper="white", seed=0, reveal=True):
        self.fn = PROPS[name][0] if name in PROPS else PROPS["lightbulb"][0]
        self.name = name
        self.size, self.paper, self.seed, self.reveal = int(size), paper, seed, reveal
        m = Pen(None, 0, 0, self.size, paper, seed, 0, measure=True)
        try:
            self.fn(m)
        except Exception:
            pass
        self.total = max(1.0, m.total)
        self._cache = {}

    def render(self, t):
        fi = int(t * _CHAR_FPS)
        if fi in self._cache:
            return self._cache[fi]
        tt = fi / _CHAR_FPS
        im = Image.new("RGBA", (self.size, self.size), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        p = _ease(tt / self.REVEAL_S) if self.reveal else 1.0
        pen = Pen(d, self.size * 0.06, self.size * 0.06, self.size * 0.88, "white", self.seed, fi % 3,
                  reveal=(self.total * p if p < 0.999 else None), t=tt)
        try:
            self.fn(pen)
        except Exception:
            pass
        if self.paper == "black":
            im = sticker(im, self.size * 0.018)
        self._cache = {fi: im}
        return im


class ImageArt:
    """A user / AI image used as a prop: pops in instead of drawing on, then gently wobbles like the doodles."""

    def __init__(self, img, size, seed=0, paper="white"):
        img = img.convert("RGBA")
        if paper == "black":
            img = sticker(img, max(img.width, img.height) * 0.02)
        k = (size * 0.86) / max(img.width, img.height)
        self.img = img.resize((max(1, int(img.width * k)), max(1, int(img.height * k))), Image.LANCZOS)
        self.size, self.seed = int(size), seed
        self._cache = {}

    def render(self, t):
        fi = int(t * _CHAR_FPS)
        if fi in self._cache:
            return self._cache[fi]
        tt = fi / _CHAR_FPS
        im = Image.new("RGBA", (self.size, self.size), (0, 0, 0, 0))
        k = 1.0
        if tt < 0.3:
            k = 0.6 + 0.5 * _ease(tt / 0.3)
        elif tt < 0.45:
            k = 1.1 - 0.1 * ((tt - 0.3) / 0.15)
        a = math.sin(fi * 2.1 + self.seed) * 0.8          # tiny hand-held wobble per frame
        src = self.img.resize((max(1, int(self.img.width * k)), max(1, int(self.img.height * k))), Image.BILINEAR)
        src = src.rotate(a, expand=True, resample=Image.BICUBIC)
        im.alpha_composite(src, ((self.size - src.width) // 2, (self.size - src.height) // 2))
        self._cache = {fi: im}
        return im


def layout(W, H):
    """Where the prop, its label and the character go. Returns dict with prop centre/size and character spot."""
    if H > W:          # Shorts (portrait): prop up-right, character big at the left pointing across at it
        return {"cx": W * 0.6, "cy": H * 0.36, "size": W * 0.66, "label_y": H * 0.36 - W * 0.4,
                "char": (W * 0.21, H * 0.70, H * 0.42)}
    return {"cx": W * 0.63, "cy": H * 0.43, "size": H * 0.66, "label_y": H * 0.43 + H * 0.39,
            "char": (W * 0.2, H * 0.62, H * 0.62)}


def resolve(s, text, paper="white", log=None):
    """('user', path) / ('lib', name) / ('ai', path) / ('lib', fallback name) for a prop description."""
    up = find_user_image(text)
    if up:
        return ("user", up)
    name = find_prop(text)
    if name:
        return ("lib", name)
    img = ai_prop_image(s, text, paper, log)
    if img:
        return ("ai", img)
    return ("lib", "question" if "?" in (text or "") else "lightbulb")


class PropClip:
    """A full frame: plain page + the prop (drawn on, bobbing, with twinkles) + optional hand-lettered label.
    Rendered at (W, H); the character is drawn on top by the caller."""

    def __init__(self, source, W, H, paper="white", seed=0, label=None, reveal=True, frame_size=None):
        self.W, self.H = W, H
        self.paper = paper if paper in PAPER else "white"
        self.seed, self.label = seed, (label or "").strip()[:28]
        lw, lh = frame_size or (W, H)                 # layout is based on the real video size
        L = layout(lw, lh)
        sx, sy = W / lw, H / lh
        self.cx, self.cy, self.S = L["cx"] * sx, L["cy"] * sy, int(L["size"] * min(sx, sy))
        self.label_y = L["label_y"] * sy
        kind, val = source
        if kind == "lib":
            self.art = PropArt(val, self.S, self.paper, seed, reveal)
        else:
            try:
                img = Image.open(val) if kind == "user" else sketchify(Image.open(val))
                self.art = ImageArt(img, self.S, seed, self.paper)
            except Exception:
                self.art = PropArt("lightbulb", self.S, self.paper, seed, reveal)
        self.reveal = reveal
        self._cache = {}
        self.rnd = random.Random(seed)
        self.spark = [(self.rnd.uniform(-0.5, 0.5), self.rnd.uniform(-0.5, 0.4), self.rnd.uniform(0, 6)) for _ in range(3)]

    def focal(self):
        return (self.cx, self.cy)

    def frame(self, t):
        fi = int(t * _CHAR_FPS)
        if fi in self._cache:
            return self._cache[fi]
        tt = fi / _CHAR_FPS
        im = Image.new("RGB", (self.W, self.H), PAPER[self.paper])
        art = self.art.render(tt)
        bob = math.sin(tt * 2.2 + self.seed) * self.S * 0.012
        tilt = math.sin(tt * 1.4 + self.seed) * 1.6
        if tilt:
            art = art.rotate(tilt, expand=False, resample=Image.BICUBIC)
        im.paste(art, (int(self.cx - art.width / 2), int(self.cy - art.height / 2 + bob)), art)
        d = ImageDraw.Draw(im)
        if tt > 0.6:                                   # twinkles around it once it's drawn
            pen = Pen(d, self.cx - self.S / 2, self.cy - self.S / 2, self.S, self.paper, self.seed, fi % 3, t=tt)
            for (ox, oy, ph) in self.spark:
                pen.sparkle(50 + ox * 100 * 0.98, 50 + oy * 100 * 0.98, r=4.5, w=1.6, color="yellow", phase=ph)
        if self.label and tt > (0.55 if self.reveal else 0.1):
            txt = self.label.upper()
            size = self.S * 0.1
            maxw = self.W * (0.84 if self.H > self.W else 0.42)          # never wider than the free space
            while size > 14 and d.textlength(txt, font=hand_font(size)) > maxw:
                size *= 0.9
            f = hand_font(size)
            tw = d.textlength(txt, font=f)
            k = min(1.0, (tt - 0.55) / 0.2) if self.reveal else 1.0
            col = (20, 20, 24) if self.paper == "white" else (240, 243, 250)
            left_limit = self.W * (0.08 if self.H > self.W else 0.36)       # keep clear of the character
            x = max(self.cx, left_limit + tw / 2) + math.sin(fi * 1.7) * 1.2
            x = min(x, self.W * 0.97 - tw / 2)
            y = self.label_y + bob * 0.5 + (1 - k) * 18
            d.text((x, y), txt, font=f, fill=col, anchor="mm")
            ul = Pen(d, x - tw / 2, y + self.S * 0.05, max(10, tw), self.paper, self.seed + 5, fi % 3)
            ul.stroke([(0, 0), (100, 1.5)], w=max(1.2, 140 / max(10, tw)), color="red" if self.paper == "white" else "yellow")
        self._cache = {fi: im}
        return im


def contact_sheet(paper="white", cols=12, cell=180, t=2.0, names=None):
    """All props on one sheet (for previews / the gallery)."""
    names = names or sorted(PROPS)
    rows = (len(names) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 26)), PAPER[paper])
    d = ImageDraw.Draw(sheet)
    f = hand_font(15)
    ink = (20, 20, 24) if paper == "white" else (240, 243, 250)
    for i, n in enumerate(names):
        art = PropArt(n, cell, paper, seed=i).render(t)
        x, y = (i % cols) * cell, (i // cols) * (cell + 26)
        sheet.paste(art, (x, y), art)
        d.text((x + cell / 2, y + cell + 10), n.replace("_", " "), font=f, fill=ink, anchor="mm")
    return sheet
