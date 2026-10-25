"""'Stickman' visual style: a crude hand-drawn stickman cutout pasted over real photos, flat UI screens or black,
with hard cuts every 1-2 s, fly-ins with speed lines, scale pops, punch-in zooms and simple meme graphics
(tier board, progress ring, photo card, bright text panel). Frames are drawn with Pillow and piped to ffmpeg.

The AI plans every beat from the owner's visual direction (YouTube → CONTENT → Visual direction)."""
import json
import math
import os
import random
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from agent import ai
from agent.tools import ffmpeg_path, fonts_dir, media_duration, run

from . import tts, visuals

FPS = 30
POSES = ["neutral", "point_left", "point_right", "arms_up", "shrug", "thinking", "walking", "facepalm"]
EXPRESSIONS = ["neutral", "happy", "shocked", "worried", "angry", "smug"]
PLACEMENTS = ["center", "corner_bl", "corner_br", "corner_tl", "corner_tr", "edge_left", "edge_right"]
MOTIONS = ["cut", "fly_left", "fly_right", "fly_top", "fly_bottom", "pop", "slide", "spin"]
ZOOMS = ["none", "push", "punch"]
BGS = ["photo", "black", "ui"]
TIER_COLORS = {"S": (230, 57, 70), "A": (247, 140, 44), "B": (246, 205, 58), "C": (76, 187, 96)}


# --------------------------------------------------------------------------------------------- drawing
def _font(size, bold=True):
    try:
        return ImageFont.truetype(os.path.join(fonts_dir(), "Poppins-Bold.ttf"), size)
    except Exception:
        return ImageFont.load_default()


def _marker(d, pts, width, rnd):
    """A thick, slightly wobbly marker stroke through pts (2+ points)."""
    path = []
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        n = max(2, int(math.hypot(x2 - x1, y2 - y1) / 40))
        for i in range(n):
            t = i / n
            path.append((x1 + (x2 - x1) * t + rnd.uniform(-3, 3), y1 + (y2 - y1) * t + rnd.uniform(-3, 3)))
    path.append(pts[-1])
    for k in range(2):  # two passes = uneven fat marker
        off = rnd.uniform(-2.5, 2.5)
        w = int(width * rnd.uniform(0.82, 1.08))
        d.line([(x + off, y + off) for x, y in path], fill=(0, 0, 0, 255), width=w, joint="curve")
        for x, y in (path[0], path[-1]):
            d.ellipse([x - w / 2 + off, y - w / 2 + off, x + w / 2 + off, y + w / 2 + off], fill=(0, 0, 0, 255))


_POSE_PTS = {   # shoulder (300,330), hip (300,560): arm ends L/R, leg ends L/R  (canvas 600x900)
    "neutral": ((215, 500), (385, 500), (235, 840), (365, 840)),
    "point_left": ((70, 300), (385, 500), (235, 840), (365, 840)),
    "point_right": ((215, 500), (530, 300), (235, 840), (365, 840)),
    "arms_up": ((170, 130), (430, 130), (225, 840), (375, 840)),
    "shrug": ((150, 270), (450, 270), (235, 840), (365, 840)),
    "thinking": ((215, 500), (330, 245), (240, 840), (360, 840)),
    "walking": ((210, 470), (400, 440), (200, 820), (420, 800)),
    "facepalm": ((215, 500), (300, 185), (240, 840), (360, 840)),
}


def draw_stickman(pose="neutral", expression="neutral", seed=0):
    rnd = random.Random(f"{pose}-{expression}-{seed}")
    im = Image.new("RGBA", (600, 900), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    W = 26
    al, ar, ll, lr = _POSE_PTS.get(pose, _POSE_PTS["neutral"])
    sh, hip = (300, 330), (300, 560)
    _marker(d, [(300, 268), hip], W, rnd)          # body
    _marker(d, [sh, al], W, rnd)                    # arms
    _marker(d, [sh, ar], W, rnd)
    _marker(d, [hip, ll], W, rnd)                   # legs
    _marker(d, [hip, lr], W, rnd)
    # head: flat white circle, thick uneven outline
    cx, cy, r = 300, 175, 98
    pts = []
    for i in range(41):
        a = 2 * math.pi * i / 40
        rr = r + rnd.uniform(-3, 3)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=(255, 255, 255, 255))
    d.line(pts, fill=(0, 0, 0, 255), width=15, joint="curve")
    # face: 3-4 thick strokes
    e = expression
    if e == "shocked":
        _marker(d, [(262, 140), (262, 168)], 16, rnd)
        _marker(d, [(338, 140), (338, 168)], 16, rnd)
        d.ellipse([280, 200, 320, 245], outline=(0, 0, 0, 255), width=12)
    else:
        _marker(d, [(265, 150), (265, 168)], 16, rnd)
        _marker(d, [(335, 150), (335, 168)], 16, rnd)
        if e == "happy":
            d.arc([255, 175, 345, 240], 20, 160, fill=(0, 0, 0, 255), width=13)
        elif e == "smug":
            _marker(d, [(265, 222), (330, 210)], 13, rnd)
        elif e == "worried":
            d.arc([262, 212, 338, 262], 200, 340, fill=(0, 0, 0, 255), width=13)
            _marker(d, [(245, 128), (282, 138)], 11, rnd)
            _marker(d, [(355, 128), (318, 138)], 11, rnd)
        elif e == "angry":
            _marker(d, [(270, 225), (330, 225)], 13, rnd)
            _marker(d, [(245, 128), (285, 145)], 12, rnd)
            _marker(d, [(355, 128), (315, 145)], 12, rnd)
        else:
            _marker(d, [(270, 220), (330, 220)], 13, rnd)
    # thin white cutout edge, like a sticker cut out with scissors (keeps the black lines visible on black/dark photos)
    a = im.split()[3]
    edge = a.filter(ImageFilter.MaxFilter(11)).filter(ImageFilter.MaxFilter(5))
    out = Image.new("RGBA", im.size, (255, 255, 255, 0))
    out.putalpha(edge)
    out.alpha_composite(im)
    return out


# ------------------------------------------------------------------------------------------ graphics
def _cover(img, w, h):
    return ImageOps.fit(img.convert("RGB"), (w, h), Image.LANCZOS)


def ui_screen(w, h, seed=0):
    """A flat, generic app/website screen (no brands)."""
    rnd = random.Random(seed)
    accent = rnd.choice([(29, 155, 240), (255, 69, 0), (88, 101, 242), (37, 211, 102), (255, 45, 85)])
    im = Image.new("RGB", (w, h), (245, 246, 248))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w, int(h * 0.07)], fill=accent)
    d.rounded_rectangle([int(w * 0.05), int(h * 0.015), int(w * 0.5), int(h * 0.05)], radius=20, fill=(255, 255, 255))
    y = int(h * 0.1)
    while y < h * 0.95:
        ch = rnd.randint(int(h * 0.12), int(h * 0.2))
        d.rounded_rectangle([int(w * 0.05), y, int(w * 0.95), y + ch], radius=28, fill=(255, 255, 255), outline=(225, 228, 232), width=3)
        d.ellipse([int(w * 0.09), y + 30, int(w * 0.09) + 90, y + 120], fill=(210, 214, 220))
        for k in range(3):
            lw = rnd.uniform(0.35, 0.7)
            d.rounded_rectangle([int(w * 0.25), y + 40 + k * 45, int(w * (0.25 + lw * 0.65)), y + 62 + k * 45], radius=10,
                                fill=(200, 204, 210) if k else (150, 155, 165))
        y += ch + 30
    return im


def g_panel(w, h, text, color):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    try:
        col = tuple(int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        col = (255, 59, 48)
    ph = int(h * 0.26)
    y0 = int(h * 0.37)
    d.rectangle([0, y0, w, y0 + ph], fill=col + (255,))
    size = int(w * 0.11)
    words = (text or "").upper().split()
    while size > 30:
        f = _font(size)
        lines, cur = [], ""
        for wd in words:
            t = (cur + " " + wd).strip()
            if d.textlength(t, font=f) < w * 0.88 or not cur:
                cur = t
            else:
                lines.append(cur)
                cur = wd
        if cur:
            lines.append(cur)
        if len(lines) * size * 1.1 < ph * 0.85:
            break
        size -= 6
    f = _font(size)
    yy = y0 + (ph - len(lines) * size * 1.1) / 2
    for ln in lines:
        d.text((w / 2, yy), ln, font=f, fill=(255, 255, 255, 255), anchor="ma")
        yy += size * 1.1
    return im


def g_ring(w, h, value, label, progress):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    d = ImageDraw.Draw(im)
    r = int(min(w, h) * 0.32)
    cx, cy = w // 2, int(h * 0.45)
    box = [cx - r, cy - r, cx + r, cy + r]
    d.ellipse(box, outline=(40, 40, 48, 255), width=int(r * 0.16))
    end = -90 + 360 * max(0.0, min(1.0, value / 100.0)) * progress
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(glow).arc(box, -90, end, fill=(0, 230, 255, 255), width=int(r * 0.2))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(18)))
    d.arc(box, -90, end, fill=(0, 230, 255, 255), width=int(r * 0.16))
    shown = label or f"{int(round(value * progress))}%"
    f = _font(int(r * 0.55))
    d.text((cx, cy), shown, font=f, anchor="mm", fill=(0, 0, 0, 255), stroke_width=10, stroke_fill=(255, 255, 255, 255))
    return im


def g_tier(w, h, rows):
    im = Image.new("RGBA", (w, h), (24, 24, 28, 255))
    d = ImageDraw.Draw(im)
    keys = ["S", "A", "B", "C"]
    top = int(h * 0.18)
    rh = int(h * 0.15)
    lab = int(rh * 0.95)
    f_lab = _font(int(lab * 0.55))
    f_item = _font(int(rh * 0.2))
    for i, k in enumerate(keys):
        y = top + i * (rh + 10)
        d.rectangle([20, y, w - 20, y + rh], fill=(52, 52, 58))
        d.rectangle([20, y, 20 + lab, y + rh], fill=TIER_COLORS[k])
        d.text((20 + lab / 2, y + rh / 2), k, font=f_lab, anchor="mm", fill=(0, 0, 0))
        x = 40 + lab
        for item in (rows or {}).get(k, [])[:3]:
            t = str(item)[:18]
            tw = d.textlength(t, font=f_item) + 30
            if x + tw > w - 30:
                break
            d.rounded_rectangle([x, y + rh * 0.3, x + tw, y + rh * 0.7], radius=12, fill=(235, 235, 240))
            d.text((x + tw / 2, y + rh / 2), t, font=f_item, anchor="mm", fill=(20, 20, 24))
            x += tw + 14
    return im


def g_card(w, h, photo):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    cw, chh = int(w * 0.82), int(h * 0.42)
    x0, y0 = (w - cw) // 2, int(h * 0.26)
    card = Image.new("RGBA", (cw, chh), (255, 255, 255, 255))
    if photo:
        inner = _cover(photo, cw - 36, chh - 36)
        card.paste(inner, (18, 18))
    m = Image.new("L", (cw, chh), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, cw - 1, chh - 1], radius=40, fill=255)
    im.paste(card, (x0, y0), m)
    return im


# -------------------------------------------------------------------------------------------- photos
class PhotoSource:
    """Real photos for backgrounds: Pexels (free key) → Openverse (no key, CC licensed, credited) → AI image."""

    def __init__(self, s, folder, log=None):
        self.s, self.folder, self.log = s, folder, log
        self.cache, self.credits, self._warned = {}, [], False
        os.makedirs(folder, exist_ok=True)

    def get(self, query, portrait):
        q = (query or self.s.get("genre") or "city").strip()[:60]
        if q in self.cache:
            return self.cache[q]
        img = self._pexels(q, portrait) or self._openverse(q) or self._ai(q, portrait)
        if img is None and not self._warned and self.log:
            self._warned = True
            self.log("warn", "Couldn't get photos for some backgrounds (using black). A free Pexels key "
                             "(YouTube → SETTINGS) gives the best photos.")
        self.cache[q] = img
        return img

    def _download(self, url, name):
        import requests
        path = os.path.join(self.folder, name)
        if not os.path.exists(path):
            r = requests.get(url, timeout=40, headers={"User-Agent": "NeonClip/2.0"})
            r.raise_for_status()
            with open(path, "wb") as f:
                f.write(r.content)
        im = Image.open(path)
        im.load()
        return im.convert("RGB")

    def _pexels(self, q, portrait):
        key = self.s.get("pexels_api_key")
        if not key:
            return None
        import requests
        try:
            r = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": key}, timeout=30,
                             params={"query": q, "per_page": 10, "orientation": "portrait" if portrait else "landscape"})
            r.raise_for_status()
            photos = r.json().get("photos", [])
            random.shuffle(photos)
            for p in photos[:3]:
                try:
                    return self._download(p["src"]["large2x"], f"px-{p['id']}.jpg")
                except Exception:
                    continue
        except Exception:
            return None
        return None

    def _openverse(self, q):
        import requests
        try:
            r = requests.get("https://api.openverse.org/v1/images/", timeout=30, headers={"User-Agent": "NeonClip/2.0"},
                             params={"q": q, "page_size": 12, "mature": "false", "license_type": "commercial,modification"})
            r.raise_for_status()
            res = [x for x in r.json().get("results", []) if (x.get("width") or 0) >= 800]
            random.shuffle(res)
            for x in res[:4]:
                try:
                    im = self._download(x["url"], f"ov-{x['id']}.img")
                    lic = (x.get("license") or "").upper()
                    self.credits.append(f"\"{x.get('title') or 'photo'}\" by {x.get('creator') or 'unknown'} ({'CC ' + lic if lic not in ('CC0', 'PDM') else lic}) {x.get('foreign_landing_url') or ''}".strip())
                    return im
                except Exception:
                    continue
        except Exception:
            return None
        return None

    def _ai(self, q, portrait):
        if not self.s.get("thumbnails", {}).get("ai_images"):
            return None
        p = os.path.join(self.folder, f"ai-{abs(hash(q)) % 10 ** 8}.png")
        got = visuals.ai_image(self.s["ai"], f"Realistic stock photo: {q}. No people's faces", p, "9:16" if portrait else "16:9")
        if got:
            try:
                return Image.open(got).convert("RGB")
            except Exception:
                return None
        return None


# ------------------------------------------------------------------------------------------- planning
PLAN_PROMPT = """You are the editor of a short-form video. Plan the visuals beat by beat, following the owner's VISUAL DIRECTION exactly.

VISUAL DIRECTION FROM THE OWNER (follow it over any default):
{direction}

What the editor can do (use ONLY these values):
- bg: "photo" (a real stock photo; give "query": 2-5 plain words to search, never a real person's name or face), "black", or "ui" (a flat generic app/website screen)
- pose: {poses}
- expression: {expressions}
- placement: {placements}   (corner_*/edge_* = tilted and partly cropped off the frame like a webcam overlay; center = full body in the lower middle third)
- motion: {motions}   (fly_* = fast fly-in from that edge with speed lines; pop = scale-pop bounce; slide = slow drift; cut = static)
- zoom: {zooms}   (push = slow 5% push-in on the photo; punch = sudden 110-130% punch-in, use on reveals)
- character: true/false (show the stickman this beat)
- graphic (optional, only when it helps or the direction asks): null, or one of
  {{"type": "panel", "text": "max 6 words", "color": "#RRGGBB"}}   full-width bright solid panel with big white text
  {{"type": "ring", "value": 0-100, "label": "short big number/text"}}   neon progress ring on black filling clockwise
  {{"type": "tier", "rows": {{"S": ["..."], "A": ["..."], "B": ["..."], "C": ["..."]}}}}   tier board
  {{"type": "card", "query": "stock photo search words"}}   a photo inside a white rounded card on black
Text only appears inside graphics. Only add graphics with text if the direction allows text.

The narration is split into segments; each needs exactly the given number of beats (hard cuts every 1-2 s).
Vary poses, placements and motions so consecutive beats never look the same. Backgrounds must match what is being said.

SEGMENTS:
{segments}

Return JSON: {{"segments": [{{"beats": [{{"bg": "...", "query": "...", "pose": "...", "expression": "...", "placement": "...", "motion": "...", "zoom": "...", "character": true, "graphic": null}}]}}]}}"""


def plan(s, segs, log=None):
    direction = (s.get("visual_instructions") or "").strip() or "Crude stickman cutout over real stock photos, hard cuts, punch-in zooms on reveals."
    lines = []
    for i, sg in enumerate(segs):
        lines.append(f"{i + 1}. ({sg['beats']} beats, {sg['dur']:.1f}s) {sg['text']}")
    prompt = PLAN_PROMPT.format(direction=direction, poses=", ".join(POSES), expressions=", ".join(EXPRESSIONS),
                                placements=", ".join(PLACEMENTS), motions=", ".join(MOTIONS), zooms=", ".join(ZOOMS),
                                segments="\n".join(lines))
    try:
        data = ai.parse_json(ai.ask(s["ai"], prompt, json_mode=True))
        planned = data.get("segments") or []
    except (ai.NoAIKey, ai.AIError):
        raise
    except Exception as e:
        if log:
            log("warn", f"The AI's visual plan couldn't be read ({e}); using a default plan.")
        planned = []
    rnd = random.Random(len(segs))
    out = []
    for i, sg in enumerate(segs):
        beats = (planned[i].get("beats") if i < len(planned) and isinstance(planned[i], dict) else None) or []
        fixed = []
        for k in range(sg["beats"]):
            b = beats[k] if k < len(beats) and isinstance(beats[k], dict) else {}
            fixed.append(_clean_beat(b, rnd, sg["text"]))
        out.append(fixed)
    return out


def _clean_beat(b, rnd, text):
    def pick(key, allowed, default):
        v = str(b.get(key, "")).strip().lower()
        return v if v in allowed else default
    g = b.get("graphic")
    if not (isinstance(g, dict) and g.get("type") in ("panel", "ring", "tier", "card")):
        g = None
    return {
        "bg": pick("bg", BGS, "photo"),
        "query": str(b.get("query") or " ".join(text.split()[:4]))[:60],
        "pose": pick("pose", POSES, rnd.choice(POSES)),
        "expression": pick("expression", EXPRESSIONS, rnd.choice(EXPRESSIONS)),
        "placement": pick("placement", PLACEMENTS, rnd.choice(PLACEMENTS)),
        "motion": pick("motion", MOTIONS, rnd.choice(MOTIONS)),
        "zoom": pick("zoom", ZOOMS, "push"),
        "character": b.get("character", True) is not False,
        "graphic": g,
    }


# ------------------------------------------------------------------------------------------ rendering
def _ease(t):
    return 1 - (1 - max(0.0, min(1.0, t))) ** 3


def _target(placement, W, H, seed):
    """(center x, center y, figure height, rotation degrees) for a placement."""
    rnd = random.Random(seed)
    tilt = rnd.uniform(20, 40)
    return {
        "center": (W * 0.5, H * 0.66, H * 0.5, 0),
        "corner_bl": (W * 0.16, H * 0.86, H * 0.55, -tilt),
        "corner_br": (W * 0.84, H * 0.86, H * 0.55, tilt),
        "corner_tl": (W * 0.16, H * 0.14, H * 0.42, 180 + tilt),     # head pointing down-right, body cropped off the corner
        "corner_tr": (W * 0.84, H * 0.14, H * 0.42, 180 - tilt),
        "edge_left": (W * 0.06, H * 0.55, H * 0.5, -tilt),
        "edge_right": (W * 0.94, H * 0.55, H * 0.5, tilt),
    }.get(placement, (W * 0.5, H * 0.66, H * 0.5, 0))


class _Beat:
    def __init__(self, beat, dur, W, H, photos, portrait, seed):
        self.b, self.dur, self.W, self.H, self.seed = beat, dur, W, H, seed
        bg = beat["bg"]
        g = beat.get("graphic")
        base = None
        if g and g["type"] in ("ring", "tier"):
            base = None
        elif g and g["type"] == "card":
            base = g_card(W, H, photos.get(g.get("query") or beat["query"], portrait)).convert("RGB")
        elif bg == "photo":
            ph = photos.get(beat["query"], portrait)
            base = _cover(ph, int(W * 1.06), int(H * 1.06)) if ph else None
        elif bg == "ui":
            base = ui_screen(int(W * 1.06), int(H * 1.06), seed)
        self.base = base if base is not None else Image.new("RGB", (int(W * 1.06), int(H * 1.06)), (0, 0, 0))
        self.overlay = g_panel(W, H, g.get("text", ""), g.get("color", "#FF3B30")) if g and g["type"] == "panel" else None
        self.tier = g_tier(W, H, g.get("rows")).convert("RGB") if g and g["type"] == "tier" else None
        self.ring = g if g and g["type"] == "ring" else None
        self.fig = None
        if beat["character"]:
            fig = draw_stickman(beat["pose"], beat["expression"], seed % 3)
            cx, cy, fh, rot = _target(beat["placement"], W, H, seed)
            if beat["placement"] in ("corner_tl", "corner_tr") and g:
                fh *= 0.8
            if g and (beat["placement"] == "center" or g["type"] == "tier"):     # keep graphics readable
                cx, cy, fh, rot = W * 0.84, H * 0.9, H * 0.3, 25
            scale = fh / fig.height
            fig = fig.resize((max(1, int(fig.width * scale)), max(1, int(fig.height * scale))), Image.LANCZOS)
            self.fig_base, self.target = fig, (cx, cy, rot)

    def frame(self, t):
        W, H, b = self.W, self.H, self.b
        p = t / max(self.dur, 0.01)
        if self.tier is not None:
            im = self.tier.copy()
        elif self.ring is not None:
            im = g_ring(W, H, float(self.ring.get("value") or 0), str(self.ring.get("label") or ""), _ease(min(1, p * 1.4))).convert("RGB")
        else:
            bw, bh = self.base.size
            z = 1.0 + (0.05 * p if b["zoom"] in ("push", "punch") else 0)
            cw, ch = bw / z, bh / z
            x0, y0 = (bw - cw) / 2, (bh - ch) / 2
            im = self.base.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.BILINEAR)
        if self.overlay is not None:
            im.paste(self.overlay, (0, 0), self.overlay)
        if b["character"]:
            self._draw_fig(im, t)
        if b["zoom"] == "punch":
            z = 1.18 if t > 0.08 else 1.0 + 0.18 * (t / 0.08)
            cw, ch = W / z, H / z
            im = im.crop((int((W - cw) / 2), int((H - ch) / 2), int((W + cw) / 2), int((H + ch) / 2))).resize((W, H), Image.BILINEAR)
        return im

    def _draw_fig(self, im, t):
        W, H = self.W, self.H
        cx, cy, rot = self.target
        m = self.b["motion"]
        fig = self.fig_base
        sc, dx, dy, drot = 1.0, 0.0, 0.0, 0.0
        fly = 0.18
        speed = None
        if m.startswith("fly_") and t < fly:
            k = 1 - _ease(t / fly)
            off = {"fly_left": (-W, 0), "fly_right": (W, 0), "fly_top": (0, -H), "fly_bottom": (0, H)}[m]
            dx, dy = off[0] * k, off[1] * k
            speed = off
        elif m == "pop":
            if t < 0.12:
                sc = 0.6 + 0.55 * (t / 0.12)
            elif t < 0.26:
                sc = 1.15 - 0.15 * ((t - 0.12) / 0.14)
        elif m == "slide":
            dx = W * 0.05 * (t / max(self.dur, 0.01)) * (1 if cx < W / 2 else -1)
        elif m == "spin" and t < 0.2:
            drot = 90 * (1 - _ease(t / 0.2))
            sc = 0.7 + 0.3 * _ease(t / 0.2)
        if sc != 1.0:
            fig = fig.resize((max(1, int(fig.width * sc)), max(1, int(fig.height * sc))), Image.BILINEAR)
        r = rot + drot
        if r:
            fig = fig.rotate(r, expand=True, resample=Image.BICUBIC)
        x, y = int(cx + dx - fig.width / 2), int(cy + dy - fig.height / 2)
        if speed:
            d = ImageDraw.Draw(im)
            ux, uy = (1 if speed[0] < 0 else -1 if speed[0] > 0 else 0), (1 if speed[1] < 0 else -1 if speed[1] > 0 else 0)
            for k in range(5):
                ox = (k - 2) * fig.height * 0.12
                sx = cx + dx - ux * fig.width * 0.5 + (ox if ux == 0 else 0)
                sy = cy + dy - uy * fig.height * 0.5 + (ox if uy == 0 else 0)
                d.line([(sx, sy), (sx - ux * W * 0.18, sy - uy * H * 0.12)], fill=(0, 0, 0), width=10)
        im.paste(fig, (x, y), fig)


class _Override:
    """Settings with a few values replaced (YTSettings isn't a plain dict)."""

    def __init__(self, s, **over):
        self.s, self.over = s, over

    def get(self, k, d=None):
        return self.over[k] if k in self.over else self.s.get(k, d)

    def __getitem__(self, k):
        return self.over[k] if k in self.over else self.s[k]


def _popen_kwargs():
    return {"creationflags": 0x08000000} if sys.platform == "win32" else {}


def build(s, segments, portrait, work, out_path, log=None):
    """Narrates each segment, asks the AI for a beat-by-beat visual plan, draws every frame, and returns
    (out_path, credits) where credits lists photos that need attribution in the description."""
    from .render import _finish   # captions / music / loudness / final encode
    os.makedirs(work, exist_ok=True)
    W, H = (1080, 1920) if portrait else (1920, 1080)
    segs, words_all, wavs, t0 = [], [], [], 0.0
    for i, sg in enumerate(segments):
        if log:
            log("info", f"Voice {i + 1}/{len(segments)}")
        mp3 = os.path.join(work, f"v{i:02d}.mp3")
        words = tts.speak(sg["text"], s["voice"], s.get("voice_rate", "+0%"), mp3)
        dur = max(media_duration(mp3), 0.5) + 0.15
        wav = os.path.join(work, f"v{i:02d}.wav")
        run([ffmpeg_path(), "-v", "error", "-y", "-i", mp3, "-af", "apad", "-t", f"{dur:.3f}", "-ar", "48000", "-ac", "2", wav])
        wavs.append(wav)
        words_all += [{"s": w["s"] + t0, "e": w["e"] + t0, "w": w["w"]} for w in words]
        segs.append({"text": sg["text"], "dur": dur, "beats": max(1, int(round(dur / 1.5))), "chapter": sg.get("chapter", ""), "start": t0})
        t0 += dur
    with open(os.path.join(work, "segments.json"), "w", encoding="utf-8") as f:
        json.dump([{"start": round(x["start"], 2), "chapter": (x["chapter"] or "").strip()} for x in segs], f)
    lst = os.path.join(work, "voice.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for w in wavs:
            f.write(f"file '{os.path.basename(w)}'\n")
    run([ffmpeg_path(), "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "voice.txt", "-c", "copy", "voice.wav"], cwd=work)

    if log:
        log("info", "AI planning the visuals")
    beats = plan(s, segs, log)
    photos = PhotoSource(s, os.path.join(os.path.dirname(work), "_photos"), log)

    if log:
        log("info", "Drawing frames")
    mux = os.path.join(work, "mux.mp4")
    cmd = [ffmpeg_path(), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", "voice.wav", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "mux.mp4"]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE, cwd=work, **_popen_kwargs())
    frame_no, seed = 0, 0
    try:
        for si, sg in enumerate(segs):
            n = len(beats[si])
            seg_frames = int(round((sg["start"] + sg["dur"]) * FPS)) - frame_no
            per = [seg_frames // n + (1 if k < seg_frames % n else 0) for k in range(n)]
            for bi, b in enumerate(beats[si]):
                seed += 1
                nf = per[bi]
                if nf <= 0:
                    continue
                beat = _Beat(b, nf / FPS, W, H, photos, portrait, seed)
                for k in range(nf):
                    proc.stdin.write(beat.frame(k / FPS).tobytes())
                    frame_no += 1
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "replace")
        if proc.wait() != 0:
            raise RuntimeError(f"ffmpeg failed: {err[-800:]}")
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
        raise
    captions = bool(s.get("stickman_captions", False))
    if captions and not os.path.isdir(os.path.join(work, "fonts")):
        import shutil
        shutil.copytree(fonts_dir(), os.path.join(work, "fonts"))
    _finish(_Override(s, captions=captions), [mux], words_all if captions else [], portrait, work, out_path)
    return out_path, photos.credits
