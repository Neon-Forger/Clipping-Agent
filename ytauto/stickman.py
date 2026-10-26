"""'Stickman' visual style: a crude hand-drawn stickman cutout pasted over real photos, flat UI screens or black,
with hard cuts every 1-2 s, fly-ins with speed lines, scale pops, punch-in zooms and simple meme graphics
(tier board, progress ring, photo card, bright text panel). Frames are drawn with Pillow and piped to ffmpeg.

The AI plans every beat from the owner's visual direction (YouTube → CONTENT → Visual direction)."""
import json
import math
import os
import random
import re
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
BGS = ["video", "photo", "black", "ui"]
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


# photos come from ytauto/photos.py (several services)
from .photos import PhotoSource  # noqa: E402


# ------------------------------------------------------------------------------------------- planning
PLAN_PROMPT = """You are the editor of a short-form video. Plan the visuals beat by beat, following the owner's VISUAL DIRECTION exactly.

VISUAL DIRECTION FROM THE OWNER (follow it over any default):
{direction}

What the editor can do (use ONLY these values):
- bg: "video" (moving stock footage or animation; give "query": 2-4 plain visual words to search, e.g. "foggy forest night",
  "old film reel", "police car lights", never a real person's name), "photo" (a real stock photo; same kind of "query"),
  "black" (plain black, rarely), or "ui" (a flat generic app/website screen)
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
BACKGROUNDS: use "video" for most beats (moving footage keeps viewers watching), "photo" for the rest. Use "black" on at most
{black_pct}% of beats (only for a deliberate dramatic pause), even if the direction mentions black. Queries must be concrete things
a camera could film (places, objects, weather, crowds, vehicles), not abstract ideas: "abandoned hospital hallway", not "mystery".

SEGMENTS:
{segments}

Return JSON: {{"segments": [{{"beats": [{{"bg": "...", "query": "...", "pose": "...", "expression": "...", "placement": "...", "motion": "...", "zoom": "...", "character": true, "graphic": null}}]}}]}}"""


def plan(s, segs, log=None):
    direction = (s.get("visual_instructions") or "").strip() or "Crude stickman cutout over real stock photos, hard cuts, punch-in zooms on reveals."
    from .training import playbook_text
    vnotes = playbook_text(s, for_visuals=True)
    if vnotes:
        direction += "\n" + vnotes
    lines = []
    for i, sg in enumerate(segs):
        lines.append(f"{i + 1}. ({sg['beats']} beats, {sg['dur']:.1f}s) {sg['text']}")
    prompt = PLAN_PROMPT.format(direction=direction, poses=", ".join(POSES), expressions=", ".join(EXPRESSIONS),
                                placements=", ".join(PLACEMENTS), motions=", ".join(MOTIONS), zooms=", ".join(ZOOMS),
                                segments="\n".join(lines), black_pct=_black_pct(s))
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
    _limit_black(out, segs, _black_pct(s), rnd)
    return out


def _black_pct(s):
    try:
        return max(0, min(100, int(s.get("max_black_percent", 5))))
    except (TypeError, ValueError):
        return 5


_STOP = set("the a an and or but of to in on at for with is are was were be been it its this that these those he she they "
            "we you i his her their our your my me him them who what when where why how not no so as by from into just "
            "than then there here very can could would should will about".split())


def _query_from(text, genre):
    words = [w for w in re.findall(r"[A-Za-z']+", text.lower()) if w not in _STOP and len(w) > 2]
    return " ".join(words[:3]) or (genre or "city night")


def _limit_black(out, segs, pct, rnd):
    """Turns black beats beyond the allowed share into video/photo beats about what's being said."""
    flat = [(i, b) for i, beats in enumerate(out) for b in beats]
    allowed = int(len(flat) * pct / 100)
    blacks = [(i, b) for i, b in flat if b["bg"] == "black" and not (b.get("graphic") or {}).get("type") in ("ring", "tier")]
    rnd.shuffle(blacks)
    for n, (i, b) in enumerate(blacks):
        if n < allowed:
            continue
        b["bg"] = "video" if n % 3 else "photo"
        if not b.get("query_given"):
            b["query"] = _query_from(segs[i]["text"], None)


def _clean_beat(b, rnd, text):
    def pick(key, allowed, default):
        v = str(b.get(key, "")).strip().lower()
        return v if v in allowed else default
    g = b.get("graphic")
    if not (isinstance(g, dict) and g.get("type") in ("panel", "ring", "tier", "card")):
        g = None
    return {
        "bg": pick("bg", BGS, "video" if rnd.random() < 0.6 else "photo"),
        "query": str(b.get("query") or _query_from(text, None))[:60],
        "query_given": bool(b.get("query")),
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


class _Bg:
    """Everything a beat can pull a background from, plus memory of recent good backgrounds (so a miss isn't black)."""

    def __init__(self, photos, footage, portrait, genre):
        self.photos, self.footage, self.portrait, self.genre = photos, footage, portrait, genre
        self.recent = []         # recent good still backgrounds
        self.counts = {"video": 0, "photo": 0, "ui": 0, "reused": 0, "gradient": 0, "black": 0}
        self.credits_used = []

    def remember(self, img):
        self.recent.append(img)
        del self.recent[:-6]

    def reuse(self, seed):
        if not self.recent:
            return None
        img = self.recent[seed % len(self.recent)]
        if seed % 2:
            img = ImageOps.mirror(img)       # flipped + different crop so it doesn't look repeated
        self.counts["reused"] += 1
        return img


def _gradient(w, h, seed):
    rnd = random.Random(seed)
    hue = rnd.choice([(20, 40, 90), (60, 20, 80), (10, 70, 80), (90, 30, 30), (30, 60, 40)])
    top = Image.new("RGB", (1, 2))
    top.putpixel((0, 0), tuple(min(255, c + 40) for c in hue))
    top.putpixel((0, 1), tuple(c // 4 for c in hue))
    return top.resize((w, h), Image.BICUBIC)


class _Beat:
    def __init__(self, beat, dur, W, H, bgs, portrait, seed, keep=None, bgdir=None):
        """keep: what this beat used last time (re-edit of an unchanged beat). bgdir: where still backgrounds are saved."""
        self.b, self.dur, self.W, self.H, self.seed = beat, dur, W, H, seed
        bg = beat["bg"]
        g = beat.get("graphic")
        BW, BH = int(W * 1.06), int(H * 1.06)
        base, self.reader = None, None
        self.resolved = {"kind": "none"}
        if keep and keep.get("kind") == "video" and os.path.exists(keep.get("clip") or ""):
            from .footage import ClipReader
            self.reader = ClipReader(keep["clip"], keep.get("start") or 0, BW, BH)
            base = self.reader.next()
            if base is not None:
                self.resolved = dict(keep)
                bgs.counts["video"] += 1
                bgs.credits_used += [keep["credit"]] if keep.get("credit") else []
            else:
                self.reader.close()
                self.reader = None
        elif keep and keep.get("kind") in ("still", "card") and os.path.exists(keep.get("path") or ""):
            try:
                ph = Image.open(keep["path"]).convert("RGB")
                base = g_card(W, H, ph).convert("RGB") if keep["kind"] == "card" else ph
                self.resolved = dict(keep)
                bgs.counts["photo"] += 1
                bgs.credits_used += [keep["credit"]] if keep.get("credit") else []
                if keep["kind"] == "still":
                    bgs.remember(base)
            except Exception:
                base = None
        if base is not None:
            pass
        elif g and g["type"] in ("ring", "tier"):
            base = None
        elif g and g["type"] == "card":
            ph = bgs.photos.get(g.get("query") or beat["query"], portrait)
            base = g_card(W, H, ph).convert("RGB")
            if ph is not None and bgdir:
                path = os.path.join(bgdir, f"b{seed:03d}.jpg")
                ph.save(path, "JPEG", quality=90)
                self.resolved = {"kind": "card", "path": path, "key": bgs.photos.last_key, "credit": bgs.photos.last_credit}
                bgs.credits_used += [bgs.photos.last_credit] if bgs.photos.last_credit else []
        elif bg == "black":
            base = Image.new("RGB", (BW, BH), (0, 0, 0))
            bgs.counts["black"] += 1
        elif bg == "ui":
            base = ui_screen(BW, BH, seed)
            bgs.counts["ui"] += 1
        else:
            order = ["video", "photo"] if bg == "video" else ["photo", "video"]
            for kind in order:
                if kind == "video" and bgs.footage is not None:
                    got = bgs.footage.get(beat["query"], portrait)
                    if got:
                        from .footage import ClipReader
                        self.reader = ClipReader(got[0], got[1], BW, BH)
                        first = self.reader.next()
                        if first is not None:
                            base = first
                            bgs.counts["video"] += 1
                            cr = bgs.footage.credit_of.get(got[0])
                            self.resolved = {"kind": "video", "clip": got[0], "start": got[1],
                                             "key": bgs.footage.key_of.get(got[0]), "credit": cr}
                            bgs.credits_used += [cr] if cr else []
                            break
                        self.reader.close()
                        self.reader = None
                elif kind == "photo":
                    ph = bgs.photos.get(beat["query"], portrait)
                    if ph is not None:
                        base = _cover(ph, BW, BH)
                        bgs.remember(base)
                        bgs.counts["photo"] += 1
                        self.resolved = {"kind": "still", "key": bgs.photos.last_key, "credit": bgs.photos.last_credit}
                        bgs.credits_used += [bgs.photos.last_credit] if bgs.photos.last_credit else []
                        break
            if base is None:
                base = bgs.reuse(seed)
                if base is not None:
                    self.resolved = {"kind": "still", "key": None, "credit": None}
            if base is None:
                base = _gradient(BW, BH, seed)
                bgs.counts["gradient"] += 1
            if self.resolved.get("kind") == "still" and bgdir:
                path = os.path.join(bgdir, f"b{seed:03d}.jpg")
                base.save(path, "JPEG", quality=90)
                self.resolved["path"] = path
        self.base = base if base is not None else Image.new("RGB", (BW, BH), (0, 0, 0))
        self._first = True
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
            if self.reader is not None and not self._first:
                nxt = self.reader.next()
                if nxt is not None:
                    self.base = nxt
            self._first = False
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
    return render_visuals(s, {"style": "stickman", "portrait": portrait, "segs": segs, "beats": beats,
                              "words": words_all, "resolved": None}, work, out_path, log)


def render_visuals(s, ed, work, out_path, log=None, changed=None, avoid_keys=()):
    """Draws the frames over the saved voice and finishes the video. ed = what edit.json holds.
    On a re-edit, `changed` is the set of beat numbers to redo; every other beat keeps exactly the background it had."""
    from .render import _finish
    portrait, segs, beats = ed["portrait"], ed["segs"], ed["beats"]
    W, H = (1080, 1920) if portrait else (1920, 1080)
    old = ed.get("resolved") or []
    redo = lambda n: changed is None or n in changed or n >= len(old)     # noqa: E731
    flat = [b for bl in beats for b in bl]
    photos = PhotoSource(s, os.path.join(os.path.dirname(work), "_photos"), log)
    photos.used |= set(avoid_keys)
    footage = None
    vq = [b["query"] for n, b in enumerate(flat) if redo(n) and b["bg"] in ("video", "photo") and not b.get("graphic")]
    vq_video = [b["query"] for n, b in enumerate(flat) if redo(n) and b["bg"] == "video" and not b.get("graphic")]
    if s.get("stock_video", True) and vq:
        from .footage import FootageSource
        if log:
            log("info", "Searching free stock-video libraries for moving backgrounds")
        footage = FootageSource(s, os.path.join(os.path.dirname(work), "_footage"), log, (int(W * 1.06), int(H * 1.06)))
        footage.used |= set(avoid_keys)
        try:
            footage.prefetch(vq_video or vq[:6], portrait)
        except Exception as e:
            if log:
                log("warn", f"Stock video search failed ({e}); using photos.")
    bgs = _Bg(photos, footage, portrait, s.get("genre"))
    bgdir = os.path.join(work, "bgs")
    os.makedirs(bgdir, exist_ok=True)

    if log:
        log("info", "Drawing frames")
    cmd = [ffmpeg_path(), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", "voice.wav", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "mux.mp4"]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE, cwd=work, **_popen_kwargs())
    frame_no, seed, n_beat, resolved = 0, 0, 0, []
    try:
        for si, sg in enumerate(segs):
            n = len(beats[si])
            seg_frames = int(round((sg["start"] + sg["dur"]) * FPS)) - frame_no
            per = [seg_frames // n + (1 if k < seg_frames % n else 0) for k in range(n)]
            for bi, b in enumerate(beats[si]):
                seed += 1
                nf = per[bi]
                keep = None if redo(n_beat) else old[n_beat]
                n_beat += 1
                if nf <= 0:
                    resolved.append(keep or {"kind": "none"})
                    continue
                beat = _Beat(b, nf / FPS, W, H, bgs, portrait, seed, keep=keep, bgdir=bgdir)
                resolved.append(beat.resolved)
                try:
                    for k in range(nf):
                        proc.stdin.write(beat.frame(k / FPS).tobytes())
                        frame_no += 1
                finally:
                    if beat.reader is not None:
                        beat.reader.close()
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
    if log:
        c = bgs.counts
        log("info", f"Backgrounds: {c['video']} moving, {c['photo']} photo, {c['ui']} screen, {c['reused']} reused, "
                    f"{c['gradient']} color, {c['black']} black. Photos: {photos.summary()}"
                    + (f". Video: {footage.summary()}" if footage else ""))
        if c["gradient"] + c["reused"] > max(3, (c["video"] + c["photo"]) // 2):
            log("warn", "Many backgrounds couldn't be found. " + photos.status_text()
                + (" " + footage.status_text() if footage else "")
                + " Free Pexels/Pixabay keys (YouTube → SETTINGS) add a lot more stock footage.")
    captions = bool(s.get("stickman_captions", False))
    if captions and not os.path.isdir(os.path.join(work, "fonts")):
        import shutil
        shutil.copytree(fonts_dir(), os.path.join(work, "fonts"))
    _finish(_Override(s, captions=captions), [os.path.join(work, "mux.mp4")], ed["words"] if captions else [], portrait, work, out_path)
    credits = list(dict.fromkeys(c for c in bgs.credits_used if c))
    ed = dict(ed, resolved=resolved, credits=credits)
    save_edit(work, ed)
    return out_path, credits


def save_edit(work, ed):
    with open(os.path.join(work, "edit.json"), "w", encoding="utf-8") as f:
        json.dump(ed, f)


def load_edit(work):
    try:
        with open(os.path.join(work, "edit.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


REEDIT_PROMPT = """You are re-editing the VISUALS of a finished short-form video. The voiceover stays exactly the same.
The owner watched it and wants these changes:
\"\"\"{instructions}\"\"\"

Current visual plan, one beat per line (#number, time in the video, what the voice is saying, current background):
{beats}

Change ONLY the beats the owner's request is about (if they name a time, change the beats around that time; if they describe
footage, find the beats that use it; if they ask for something across the whole video, change all the beats it applies to).
Leave every other beat out of your answer so it stays exactly as it is.

For each beat you change you may set any of:
- bg: "video" (moving stock footage) / "photo" / "ui" / "black"; query: 2-4 concrete visual search words (things a camera can film)
- new_footage: true  (same idea but different footage than before; use when the owner says a clip is bad/wrong/repetitive)
- pose: {poses}; expression: {expressions}; placement: {placements}; motion: {motions}; zoom: {zooms}; character: true/false
- graphic: null, or {{"type": "panel", "text": "...", "color": "#RRGGBB"}} / {{"type": "ring", "value": 0-100, "label": "..."}} /
  {{"type": "tier", "rows": {{"S": [...], "A": [...], "B": [...], "C": [...]}}}} / {{"type": "card", "query": "..."}}

Return JSON: {{"changes": [{{"beat": 12, "bg": "video", "query": "...", "new_footage": true}}], "summary": "one sentence on what you changed"}}"""


def _fmt_t(sec):
    return f"{int(sec // 60)}:{int(sec % 60):02d}"


def reedit(s, work, out_path, instructions, log=None):
    """Re-does only the visuals the owner asked about, keeping the voiceover and every other beat. Returns (path, credits, summary)."""
    ed = load_edit(work)
    if not ed or ed.get("style") != "stickman":
        raise RuntimeError("This video was made before re-editing existed (or its work files were cleaned up), so it can't be re-edited.")
    if not os.path.exists(os.path.join(work, "voice.wav")):
        raise RuntimeError("The voiceover file for this video is gone, so it can't be re-edited.")
    lines, n, old = [], 0, ed.get("resolved") or []
    for si, sg in enumerate(ed["segs"]):
        k = len(ed["beats"][si])
        for bi, b in enumerate(ed["beats"][si]):
            t0 = sg["start"] + sg["dur"] * bi / k
            t1 = sg["start"] + sg["dur"] * (bi + 1) / k
            used = (old[n] if n < len(old) else {}).get("kind", "?")
            g = b.get("graphic")
            lines.append(f"#{n} {_fmt_t(t0)}-{_fmt_t(t1)} | \"{sg['text'][:90]}\" | bg={b['bg']} query=\"{b['query']}\" (shown: {used})"
                         + (f" graphic={json.dumps(g)}" if g else "") + f" pose={b['pose']} character={b['character']}")
            n += 1
    prompt = REEDIT_PROMPT.format(instructions=instructions.strip()[:2000], beats="\n".join(lines), poses=", ".join(POSES),
                                  expressions=", ".join(EXPRESSIONS), placements=", ".join(PLACEMENTS),
                                  motions=", ".join(MOTIONS), zooms=", ".join(ZOOMS))
    data = ai.parse_json(ai.ask(s["ai"], prompt, json_mode=True))
    flat = [(si, bi) for si, bl in enumerate(ed["beats"]) for bi in range(len(bl))]
    changed, avoid = set(), set()
    rnd = random.Random(7)
    for ch in data.get("changes") or []:
        try:
            num = int(str(ch.get("beat", ch.get("index", -1))).lstrip("#"))
        except (TypeError, ValueError):
            continue
        if not 0 <= num < len(flat):
            continue
        si, bi = flat[num]
        b = dict(ed["beats"][si][bi])
        for key in ("bg", "query", "pose", "expression", "placement", "motion", "zoom", "character", "graphic"):
            if key in ch:
                b[key] = ch[key]
        fixed = _clean_beat(b, rnd, ed["segs"][si]["text"])
        if "query" in ch:
            fixed["query_given"] = True
        ed["beats"][si][bi] = fixed
        changed.add(num)
        if num < len(old) and old[num].get("key"):
            avoid.add(old[num]["key"])        # never put the same footage back
    if not changed:
        raise RuntimeError("The AI couldn't tell which part of the video to change. Try naming the time (e.g. 'at 0:12') "
                           "or describing the footage (e.g. 'the clip of the empty road').")
    summary = str(data.get("summary") or f"changed {len(changed)} beat(s)")[:300]
    if log:
        log("info", f"Re-editing {len(changed)} of {len(flat)} beats (voiceover kept): {summary}")
    path, credits = render_visuals(s, ed, work, out_path, log, changed=changed, avoid_keys=avoid)
    return path, credits, summary
