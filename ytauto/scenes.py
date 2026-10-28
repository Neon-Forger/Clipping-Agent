"""Hand-drawn doodle backgrounds in the same marker style as the stickman character.

Instead of stock footage, a beat can show a simple drawing of what's being talked about — a city skyline,
a hilltop, a car on a road, a house, a forest, the ocean, outer space — on a plain white or black "paper".
Everything is drawn with the same wobbly marker strokes as the character and animated lightly (clouds drift,
stars twinkle, a car drives across, waves bob), so the character can stand in front of it and point at things.

No text, no real logos, nothing copyrighted: these are generic doodles generated from code."""
import math
import random

from PIL import Image, ImageDraw, ImageFilter

FPS = 30
_SCENE_FPS = 12          # the doodle redraws 12 times a second (limited-animation look, and cheap)

# which scene a subject maps to (first keyword that appears in the query/narration wins)
SCENE_WORDS = [
    ("city", ("city", "town", "street", "building", "skyline", "urban", "downtown", "office", "apartment", "skyscraper")),
    ("road", ("road", "car", "truck", "drive", "driving", "vehicle", "highway", "traffic", "bus", "motorway", "route")),
    ("hill", ("hill", "mountain", "cliff", "peak", "valley", "countryside", "field", "meadow", "trail", "summit", "ridge")),
    ("house", ("house", "home", "cabin", "cottage", "farm", "barn", "village", "neighbou")),
    ("forest", ("forest", "tree", "woods", "jungle", "wood", "park", "pine")),
    ("water", ("ocean", "sea", "water", "wave", "beach", "lake", "river", "boat", "ship", "coast", "island", "harbor", "harbour")),
    ("space", ("space", "star", "planet", "galaxy", "moon", "night sky", "universe", "cosmos", "rocket", "orbit", "astronaut", "nebula")),
    ("desert", ("desert", "dune", "sand", "cactus", "canyon", "wasteland")),
    ("snow", ("snow", "winter", "ice", "arctic", "blizzard", "frozen", "glacier")),
    ("storm", ("storm", "rain", "thunder", "lightning", "cloud", "hurricane", "tornado")),
]
SCENES = [name for name, _ in SCENE_WORDS] + ["plain"]


def scene_for(query, text=""):
    """Pick a doodle scene for what's being talked about."""
    hay = f"{query or ''} {text or ''}".lower()
    for name, words in SCENE_WORDS:
        if any(w in hay for w in words):
            return name
    return "hill"          # a calm landscape reads better than a blank page


# ----------------------------------------------------------------------------- marker drawing helpers
def _marker(d, pts, width, rnd, color):
    """A wobbly hand-drawn stroke (same feel as the character's lines)."""
    if len(pts) < 2:
        return
    jig = []
    for x, y in pts:
        jig.append((x + rnd.uniform(-width * 0.12, width * 0.12), y + rnd.uniform(-width * 0.12, width * 0.12)))
    d.line(jig, fill=color, width=width, joint="curve")
    for x, y in (jig[0], jig[-1]):
        d.ellipse([x - width / 2, y - width / 2, x + width / 2, y + width / 2], fill=color)


def _poly(d, pts, width, rnd, color):
    pts = pts + [pts[0]]
    _marker(d, pts, width, rnd, color)


class SceneClip:
    """Renders an animated doodle scene frame by frame (cached at _SCENE_FPS). Deterministic from (name, bg, seed)."""

    def __init__(self, name, W, H, bg="white", seed=0):
        self.name = name if name in SCENES else "hill"
        self.W, self.H, self.bg, self.seed = W, H, bg, seed
        self.sw, self.sh = max(360, W // 2), max(640, H // 2)       # draw at half size, then upscale (cheaper, still marker-like)
        self.paper = (250, 250, 248) if bg == "white" else (8, 10, 16)
        self.ink = (18, 18, 22) if bg == "white" else (238, 242, 250)
        self.accent = (255, 120, 40) if bg == "white" else (120, 220, 255)
        self._cache = {}
        self._static = None       # pre-rendered still parts (ground, buildings…) so only moving parts redraw

    def frame(self, t):
        fi = int(t * _SCENE_FPS)
        if fi in self._cache:
            return self._cache[fi]
        im = self._render(fi / _SCENE_FPS)
        self._cache = {fi: im}     # only ever need the current frame
        return im

    # ------------------------------------------------------------------ rendering
    def _base(self):
        if self._static is None:
            im = Image.new("RGB", (self.sw, self.sh), self.paper)
            self._static = im
        return self._static.copy()

    def _render(self, t):
        im = Image.new("RGB", (self.sw, self.sh), self.paper)
        d = ImageDraw.Draw(im)
        rnd = random.Random(self.seed)       # same wobble every frame so lines don't buzz
        getattr(self, f"_{self.name}", self._hill)(d, rnd, t)
        if self.sw != self.W:
            im = im.resize((self.W, self.H), Image.BILINEAR)
        return im

    # ------------------------------------------------------------------ shared bits
    def _sky_clouds(self, d, rnd, t, n=3, y0=0.12):
        w, h = self.sw, self.sh
        for i in range(n):
            r = random.Random(self.seed * 7 + i)
            speed = 0.004 + r.random() * 0.01
            cx = (r.random() + speed * t * 60) % 1.25 * w - w * 0.1
            cy = (y0 + r.random() * 0.18) * h
            s = (0.5 + r.random()) * w * 0.07
            for dx, dy, rr in [(-s, 0, s * 0.8), (0, -s * 0.4, s), (s, 0, s * 0.8), (0, s * 0.1, s * 0.7)]:
                d.ellipse([cx + dx - rr, cy + dy - rr, cx + dx + rr, cy + dy + rr], outline=self.ink, width=5)

    def _sun(self, d, rnd, t, cx=0.8, cy=0.16, moon=False):
        w, h = self.sw, self.sh
        x, y, r = cx * w, cy * h, w * 0.08
        d.ellipse([x - r, y - r, x + r, y + r], outline=self.accent, width=7)
        if not moon:
            pulse = 1 + 0.12 * math.sin(t * 2)
            for a in range(0, 360, 45):
                a2 = math.radians(a + t * 20)
                x1, y1 = x + math.cos(a2) * r * 1.4, y + math.sin(a2) * r * 1.4
                x2, y2 = x + math.cos(a2) * r * 1.9 * pulse, y + math.sin(a2) * r * 1.9 * pulse
                d.line([(x1, y1), (x2, y2)], fill=self.accent, width=6)

    def _ground(self, d, rnd, t, y=0.8):
        w, h = self.sw, self.sh
        pts = [(x, y * h + math.sin(x * 0.01 + self.seed) * 6) for x in range(0, w + 1, w // 12)]
        _marker(d, [(0, y * h)] + pts + [(w, y * h)], 7, rnd, self.ink)

    # ------------------------------------------------------------------ scenes
    def _hill(self, d, rnd, t):
        w, h = self.sw, self.sh
        self._sky_clouds(d, rnd, t)
        self._sun(d, rnd, t)
        for layer, (yb, amp, step) in enumerate([(0.86, 0.1, 0.9), (0.78, 0.16, 1.3), (0.7, 0.2, 1.7)]):
            pts = []
            for i in range(0, 13):
                x = i / 12 * w
                y = (yb - amp * (0.5 + 0.5 * math.sin(i * step + self.seed + layer))) * h
                pts.append((x, y))
            _marker(d, [(0, h)] + pts + [(w, h)], 6, rnd, self.ink)
        # a little tree on a hill
        tx, ty = w * 0.3, h * 0.62
        _marker(d, [(tx, ty), (tx, ty - h * 0.08)], 6, rnd, self.ink)
        d.ellipse([tx - w * 0.05, ty - h * 0.16, tx + w * 0.05, ty - h * 0.06], outline=self.ink, width=6)

    def _city(self, d, rnd, t):
        w, h = self.sw, self.sh
        self._sky_clouds(d, rnd, t, n=2, y0=0.08)
        self._sun(d, rnd, t, cx=0.82, cy=0.14, moon=(self.bg == "black"))
        base = h * 0.82
        x = 0
        i = 0
        while x < w:
            r = random.Random(self.seed * 13 + i)
            bw = w * (0.08 + r.random() * 0.06)
            bh = h * (0.18 + r.random() * 0.4)
            _poly(d, [(x, base), (x, base - bh), (x + bw, base - bh), (x + bw, base)], 6, rnd, self.ink)
            for wy in range(1, int(bh / (h * 0.05))):
                for wx in range(1, 3):
                    lit = (r.random() > 0.35)
                    wxp, wyp = x + bw * wx / 3, base - bh + wy * h * 0.05
                    col = self.accent if (lit and ((wx + wy + int(t * 2)) % 4 == 0)) else self.ink
                    d.rectangle([wxp - 4, wyp - 4, wxp + 4, wyp + 4], outline=col, width=3)
            x += bw + w * 0.015
            i += 1
        self._ground(d, rnd, t, y=0.82)

    def _road(self, d, rnd, t):
        w, h = self.sw, self.sh
        self._sky_clouds(d, rnd, t, n=2)
        self._sun(d, rnd, t, cx=0.2, cy=0.16)
        horizon = h * 0.6
        _marker(d, [(0, horizon), (w, horizon)], 5, rnd, self.ink)
        # road widening toward viewer
        _marker(d, [(w * 0.46, horizon), (w * 0.1, h)], 6, rnd, self.ink)
        _marker(d, [(w * 0.54, horizon), (w * 0.9, h)], 6, rnd, self.ink)
        for k in range(6):                       # dashed centre line scrolling toward viewer
            f = ((k / 6) + (t * 0.5) % (1 / 6)) % 1
            y = horizon + f * (h - horizon)
            seg = 6 + f * 26
            d.line([(w * 0.5, y), (w * 0.5, y + seg)], fill=self.accent, width=int(3 + f * 6))
        # a little car driving across
        car_x = (t * 0.18 % 1.3 - 0.15) * w
        cy = h * 0.8
        cw, ch = w * 0.16, h * 0.07
        _poly(d, [(car_x, cy), (car_x + cw, cy), (car_x + cw, cy - ch), (car_x + cw * 0.7, cy - ch),
                  (car_x + cw * 0.55, cy - ch * 1.7), (car_x + cw * 0.25, cy - ch * 1.7), (car_x + cw * 0.12, cy - ch)], 6, rnd, self.ink)
        for wx in (0.25, 0.75):
            d.ellipse([car_x + cw * wx - 10, cy - 6, car_x + cw * wx + 10, cy + 14], outline=self.ink, width=6)

    def _house(self, d, rnd, t):
        w, h = self.sw, self.sh
        self._sky_clouds(d, rnd, t)
        self._sun(d, rnd, t)
        bx, by, bw, bh = w * 0.32, h * 0.52, w * 0.36, h * 0.26
        _poly(d, [(bx, by + bh), (bx, by), (bx + bw, by), (bx + bw, by + bh)], 6, rnd, self.ink)      # walls
        _marker(d, [(bx - w * 0.03, by), (bx + bw * 0.5, by - h * 0.12), (bx + bw + w * 0.03, by)], 6, rnd, self.ink)  # roof
        _poly(d, [(bx + bw * 0.4, by + bh), (bx + bw * 0.4, by + bh * 0.45), (bx + bw * 0.6, by + bh * 0.45), (bx + bw * 0.6, by + bh)], 5, rnd, self.ink)  # door
        d.rectangle([bx + bw * 0.1, by + bh * 0.2, bx + bw * 0.28, by + bh * 0.45], outline=self.ink, width=5)  # window
        # chimney smoke drifting up
        smx, smy = bx + bw * 0.75, by - h * 0.06
        d.rectangle([smx - 8, smy, smx + 8, by], outline=self.ink, width=5)
        for k in range(4):
            ph = (t * 0.3 + k / 4) % 1
            sy = smy - ph * h * 0.18
            sr = 8 + ph * 22
            d.ellipse([smx - sr + math.sin(ph * 6) * 10, sy - sr, smx + sr + math.sin(ph * 6) * 10, sy + sr],
                      outline=self.ink, width=3)
        self._ground(d, rnd, t, y=0.78)

    def _forest(self, d, rnd, t):
        w, h = self.sw, self.sh
        self._sky_clouds(d, rnd, t, n=2, y0=0.08)
        self._ground(d, rnd, t, y=0.8)
        for i in range(6):
            r = random.Random(self.seed * 3 + i)
            tx = (i + 0.5) / 6 * w + r.uniform(-20, 20)
            sway = math.sin(t * 1.2 + i) * w * 0.01
            th = h * (0.22 + r.random() * 0.14)
            ty = h * 0.8
            _marker(d, [(tx, ty), (tx + sway, ty - th)], 6, rnd, self.ink)
            for lvl in range(3):
                lw = w * (0.11 - lvl * 0.025)
                ly = ty - th * (0.5 + lvl * 0.22)
                _poly(d, [(tx + sway * (0.5 + lvl * 0.2) - lw, ly), (tx + sway * (0.5 + lvl * 0.2), ly - h * 0.09),
                          (tx + sway * (0.5 + lvl * 0.2) + lw, ly)], 5, rnd, self.ink)
        for k in range(6):                       # drifting leaves
            r = random.Random(self.seed + 50 + k)
            lx = (r.random() + t * 0.05) % 1 * w
            ly = ((r.random() + t * 0.12) % 1) * h * 0.7
            d.ellipse([lx - 5, ly - 3, lx + 5, ly + 3], outline=self.accent, width=3)

    def _water(self, d, rnd, t):
        w, h = self.sw, self.sh
        self._sky_clouds(d, rnd, t)
        self._sun(d, rnd, t, cx=0.75, cy=0.2)
        horizon = h * 0.52
        _marker(d, [(0, horizon), (w, horizon)], 5, rnd, self.ink)
        for row in range(6):
            y = horizon + (row + 1) / 6 * (h - horizon)
            pts = []
            for x in range(0, w + 1, w // 16):
                pts.append((x, y + math.sin(x * 0.03 + t * 2 + row) * (6 + row * 2)))
            _marker(d, pts, 4, rnd, self.ink)
        # little boat bobbing
        bx = w * 0.4 + math.sin(t * 0.6) * w * 0.04
        by = horizon + h * 0.12 + math.sin(t * 2) * 6
        bw = w * 0.14
        _marker(d, [(bx, by), (bx + bw, by), (bx + bw * 0.82, by + h * 0.05), (bx + bw * 0.18, by + h * 0.05), (bx, by)], 6, rnd, self.ink)
        _marker(d, [(bx + bw * 0.5, by), (bx + bw * 0.5, by - h * 0.1)], 5, rnd, self.ink)
        _poly(d, [(bx + bw * 0.5, by - h * 0.1), (bx + bw * 0.5, by - h * 0.02), (bx + bw * 0.85, by - h * 0.04)], 5, rnd, self.accent)

    def _space(self, d, rnd, t):
        w, h = self.sw, self.sh
        for k in range(60):
            r = random.Random(self.seed * 9 + k)
            sx, sy = r.random() * w, r.random() * h
            tw = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(t * 3 + k))
            rr = (1.5 + r.random() * 2.5) * tw
            col = self.accent if k % 7 == 0 else self.ink
            d.ellipse([sx - rr, sy - rr, sx + rr, sy + rr], fill=col)
        self._sun(d, rnd, t, cx=0.78, cy=0.2, moon=True)
        # a drifting planet with a ring
        px, py = w * 0.25 + math.sin(t * 0.3) * w * 0.02, h * 0.3
        pr = w * 0.1
        d.ellipse([px - pr, py - pr, px + pr, py + pr], outline=self.ink, width=6)
        d.ellipse([px - pr * 1.6, py - pr * 0.4, px + pr * 1.6, py + pr * 0.4], outline=self.accent, width=5)

    def _desert(self, d, rnd, t):
        w, h = self.sw, self.sh
        self._sun(d, rnd, t, cx=0.8, cy=0.18)
        for layer, yb in enumerate([0.88, 0.8, 0.72]):
            pts = []
            for i in range(0, 13):
                x = i / 12 * w
                y = (yb - 0.05 * math.sin(i * 0.9 + self.seed + layer)) * h
                pts.append((x, y))
            _marker(d, [(0, h)] + pts + [(w, h)], 6, rnd, self.ink)
        # cactus
        cx, cy = w * 0.68, h * 0.72
        _marker(d, [(cx, cy), (cx, cy - h * 0.16)], 8, rnd, self.ink)
        _marker(d, [(cx, cy - h * 0.1), (cx - w * 0.05, cy - h * 0.1), (cx - w * 0.05, cy - h * 0.15)], 7, rnd, self.ink)
        _marker(d, [(cx, cy - h * 0.13), (cx + w * 0.05, cy - h * 0.13), (cx + w * 0.05, cy - h * 0.19)], 7, rnd, self.ink)

    def _snow(self, d, rnd, t):
        w, h = self.sw, self.sh
        for layer, yb in enumerate([0.86, 0.78]):
            pts = [(i / 12 * w, (yb - 0.06 * math.sin(i + self.seed + layer)) * h) for i in range(13)]
            _marker(d, [(0, h)] + pts + [(w, h)], 6, rnd, self.ink)
        for k in range(50):                      # falling snow
            r = random.Random(self.seed + k)
            sx = (r.random() + math.sin(t + k) * 0.02) % 1 * w
            sy = ((r.random() + t * 0.08) % 1) * h
            d.ellipse([sx - 3, sy - 3, sx + 3, sy + 3], fill=self.ink)

    def _storm(self, d, rnd, t):
        w, h = self.sw, self.sh
        self._sky_clouds(d, rnd, t, n=4, y0=0.1)
        flash = (math.sin(t * 9) > 0.9)
        if flash:
            bx = w * (0.3 + 0.4 * random.Random(int(t * 3)).random())
            _marker(d, [(bx, h * 0.3), (bx - w * 0.04, h * 0.45), (bx + w * 0.03, h * 0.45), (bx - w * 0.03, h * 0.62)], 6, rnd, self.accent)
        for k in range(40):                      # rain streaks
            r = random.Random(self.seed + k)
            rx = (r.random() + t * 0.3) % 1 * w
            ry = ((r.random() + t * 0.9) % 1) * h
            d.line([(rx, ry), (rx - 8, ry + 26)], fill=self.ink, width=3)
        self._ground(d, rnd, t, y=0.85)

    def _plain(self, d, rnd, t):
        # just the paper, with a couple of drifting doodles so it isn't dead
        self._sky_clouds(d, rnd, t, n=2, y0=0.2)


def draw_scene_still(name, W, H, bg="white", seed=0):
    """A single frame (for thumbnails / tests)."""
    return SceneClip(name, W, H, bg, seed).frame(0.0)


def soften(im):
    return im.filter(ImageFilter.SMOOTH_MORE)
