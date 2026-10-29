"""Hand-drawn marker toolkit shared by the props, the end card and the doodle scenes.

Everything is drawn in a 0-100 box that is mapped onto a pixel box, with:
- wobbly marker strokes (two slightly offset passes, like a fat felt-tip),
- "boil": the wobble is re-rolled on every 12 fps frame (cycling through 3 versions), the classic
  hand-drawn animation look where lines shimmer slightly,
- draw-on reveal: give `reveal` (0-1) and strokes appear in the order they're drawn, like someone sketching it live,
- spot-colour fills that sit a little off the outline (misregistered), like coloured in quickly with a marker."""
import math
import os
import random

from PIL import ImageFont

COLORS = {
    "red": (235, 64, 52), "orange": (255, 140, 40), "yellow": (255, 205, 40), "green": (70, 190, 90),
    "teal": (40, 190, 180), "blue": (60, 140, 240), "lightblue": (140, 200, 255), "purple": (150, 90, 220),
    "pink": (255, 110, 170), "brown": (160, 105, 60), "gray": (150, 150, 160), "lightgray": (215, 215, 222),
    "skin": (255, 210, 170), "gold": (245, 185, 30), "silver": (190, 195, 205), "white": (255, 255, 255),
    "black": (22, 22, 26), "darkgreen": (40, 130, 70), "cream": (250, 240, 215),
}
PAPER = {"white": (250, 250, 248), "black": (10, 12, 18)}
INK = {"white": (20, 20, 24), "black": (240, 243, 250)}
FONT_FILE = "PermanentMarker-Regular.ttf"
_fonts = {}


def hand_font(px):
    px = max(8, int(px))
    if px not in _fonts:
        try:
            from agent.tools import fonts_dir
            _fonts[px] = ImageFont.truetype(os.path.join(fonts_dir(), FONT_FILE), px)
        except Exception:
            try:
                from agent.tools import fonts_dir
                _fonts[px] = ImageFont.truetype(os.path.join(fonts_dir(), "Poppins-Bold.ttf"), px)
            except Exception:
                _fonts[px] = ImageFont.load_default()
    return _fonts[px]


def _catmull(pts, steps=6):
    """Smooth curve through points."""
    if len(pts) < 3:
        return pts
    out = []
    p = [pts[0]] + list(pts) + [pts[-1]]
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for s in range(steps):
            t = s / steps
            t2, t3 = t * t, t * t * t
            out.append((0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                               + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
                        0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                               + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)))
    out.append(pts[-1])
    return out


class Pen:
    """Draws in a 0-100 unit box placed at (x0, y0) with side `size` pixels."""

    def __init__(self, d, x0, y0, size, paper="white", seed=0, boil=0, reveal=None, measure=False, wobble=1.0, t=0.0):
        self.d, self.x0, self.y0, self.k = d, x0, y0, size / 100.0
        self.paper_name = paper if paper in PAPER else "white"
        self.ink = INK[self.paper_name]
        self.paper = PAPER[self.paper_name]
        self.rnd = random.Random(seed * 1009 + boil * 7919 + 13)
        self.measure, self.total = measure, 0.0
        self.budget = None if (reveal is None or measure) else float(reveal)
        self.wob = wobble
        self.t = t                       # seconds since the drawing appeared (for per-prop animation)

    # -------------------------------------------------------------- basics
    def P(self, x, y):
        return (self.x0 + x * self.k, self.y0 + y * self.k)

    def col(self, c):
        if c is None or c == "ink":
            return self.ink
        if c == "paper":
            return self.paper
        if isinstance(c, tuple):
            return c
        return COLORS.get(c, self.ink)

    def _len(self, pts):
        return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))

    def _trim(self, pts):
        """Respect the draw-on budget: returns the visible part of a path (and spends the budget)."""
        L = self._len(pts)
        if self.measure:
            self.total += L
            return []
        if self.budget is None:
            return pts
        if self.budget <= 0:
            return []
        if self.budget >= L:
            self.budget -= L
            return pts
        out, left = [pts[0]], self.budget
        for a, b in zip(pts, pts[1:]):
            seg = math.hypot(b[0] - a[0], b[1] - a[1])
            if seg >= left:
                f = left / seg if seg else 0
                out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
                break
            out.append(b)
            left -= seg
        self.budget = 0
        return out

    def _wobble(self, pts, w):
        """Hand-drawn jitter, resampled along the path."""
        res, amp = [], max(0.6, w * 0.16) * self.wob
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            n = max(1, int(math.hypot(x2 - x1, y2 - y1) / max(14.0, 30 * self.k)))
            for i in range(n):
                f = i / n
                res.append((x1 + (x2 - x1) * f + self.rnd.uniform(-amp, amp), y1 + (y2 - y1) * f + self.rnd.uniform(-amp, amp)))
        res.append((pts[-1][0] + self.rnd.uniform(-amp, amp) * 0.5, pts[-1][1] + self.rnd.uniform(-amp, amp) * 0.5))
        return res

    # -------------------------------------------------------------- strokes
    def stroke(self, pts, w=3.0, color=None, closed=False, smooth=False):
        """A marker stroke through unit-space points."""
        if len(pts) < 2:
            return
        px = [self.P(x, y) for x, y in pts]
        if closed:
            px = px + [px[0]]
        if smooth:
            px = _catmull(px)
        vis = self._trim(px)
        if self.measure or len(vis) < 2:
            return
        wpx = max(1.5, w * self.k)
        c = self.col(color)
        path = self._wobble(vis, wpx)
        for k in range(2):
            off = self.rnd.uniform(-0.18, 0.18) * wpx
            ww = int(max(1, wpx * self.rnd.uniform(0.82, 1.06)))
            self.d.line([(x + off, y + off) for x, y in path], fill=c, width=ww, joint="curve")
            for x, y in (path[0], path[-1]):
                self.d.ellipse([x - ww / 2 + off, y - ww / 2 + off, x + ww / 2 + off, y + ww / 2 + off], fill=c)

    def line(self, x1, y1, x2, y2, w=3.0, color=None):
        self.stroke([(x1, y1), (x2, y2)], w, color)

    def _fill(self, pts_px, fill, outline_len):
        """Spot colour under an outline, nudged off it a little like quick colouring-in."""
        if fill is None or self.measure:
            return
        if self.budget is not None and self.budget < outline_len * 0.5:
            return
        c = self.col(fill)
        o = 1.1 * self.k
        self.d.polygon([(x + o, y + o) for x, y in pts_px], fill=c)

    def poly(self, pts, w=3.0, fill=None, color=None, smooth=False):
        px = [self.P(x, y) for x, y in pts]
        if smooth:
            px = _catmull(px + [px[0]])
        self._fill(px, fill, self._len(px + [px[0]]))
        self.stroke(pts, w, color, closed=True, smooth=smooth)

    def _ell_pts(self, cx, cy, rx, ry, a0=0, a1=360, n=None, rot=0):
        n = n or max(16, int((abs(a1 - a0) / 360) * 40))
        out = []
        cr, sr = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        for i in range(n + 1):
            a = math.radians(a0 + (a1 - a0) * i / n)
            x, y = rx * math.cos(a), ry * math.sin(a)
            out.append((cx + x * cr - y * sr, cy + x * sr + y * cr))
        return out

    def ellipse(self, cx, cy, rx, ry, w=3.0, fill=None, color=None, rot=0):
        pts = self._ell_pts(cx, cy, rx, ry, rot=rot)
        px = [self.P(x, y) for x, y in pts]
        self._fill(px, fill, self._len(px))
        self.stroke(pts, w, color)

    def circle(self, cx, cy, r, w=3.0, fill=None, color=None):
        self.ellipse(cx, cy, r, r, w, fill, color)

    def arc(self, cx, cy, rx, ry, a0, a1, w=3.0, color=None):
        self.stroke(self._ell_pts(cx, cy, rx, ry, a0, a1), w, color)

    def rect(self, x0, y0, x1, y1, w=3.0, fill=None, color=None):
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], w, fill, color)

    def rrect(self, x0, y0, x1, y1, r=6, w=3.0, fill=None, color=None):
        r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
        pts = []
        for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
            pts += self._ell_pts(cx, cy, r, r, a0, a0 + 90, n=6)
        self.poly(pts, w, fill, color)

    def star(self, cx, cy, r1, r2=None, n=5, w=3.0, fill=None, color=None, rot=-90):
        r2 = r2 if r2 is not None else r1 * 0.45
        pts = []
        for i in range(n * 2):
            a = math.radians(rot + i * 180 / n)
            r = r1 if i % 2 == 0 else r2
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        self.poly(pts, w, fill, color)

    def dot(self, x, y, r=1.6, color=None):
        if self.measure:
            self.total += r * self.k * 3
            return
        if self.budget is not None:
            if self.budget <= 0:
                return
            self.budget -= r * self.k * 3
        cx, cy = self.P(x, y)
        rr = r * self.k
        self.d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=self.col(color))

    def arrow(self, x1, y1, x2, y2, w=3.0, head=8, color=None):
        self.stroke([(x1, y1), (x2, y2)], w, color)
        a = math.atan2(y2 - y1, x2 - x1)
        for s in (-1, 1):
            self.stroke([(x2 - head * math.cos(a + s * 0.5), y2 - head * math.sin(a + s * 0.5)), (x2, y2)], w, color)

    def curve(self, pts, w=3.0, color=None):
        self.stroke(pts, w, color, smooth=True)

    def blob(self, pts, w=3.0, fill=None, color=None):
        """Smooth closed shape through points (clouds, leaves, puddles)."""
        self.poly(pts, w, fill, color, smooth=True)

    def text(self, x, y, s, size=10, color=None, anchor="mm"):
        """Hand lettering (Permanent Marker). Counts toward the draw-on reveal as a whole word."""
        cost = size * self.k * max(1, len(s)) * 0.6
        if self.measure:
            self.total += cost
            return
        if self.budget is not None:
            if self.budget <= 0:
                return
            self.budget -= cost
        f = hand_font(size * self.k)
        cx, cy = self.P(x, y)
        self.d.text((cx, cy), s, font=f, fill=self.col(color), anchor=anchor)

    def sparkle(self, x, y, r=4, w=2.2, color="yellow", phase=0.0):
        """A little twinkle (4 ticks) that grows and shrinks over time."""
        k = 0.55 + 0.45 * math.sin(self.t * 5 + phase)
        for a in range(0, 360, 90):
            ra = math.radians(a + 45 * (phase % 2))
            self.stroke([(x + math.cos(ra) * r * 0.35 * k, y + math.sin(ra) * r * 0.35 * k),
                         (x + math.cos(ra) * r * k, y + math.sin(ra) * r * k)], w, color)
