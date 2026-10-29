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

from . import scenes, visuals, voice

FPS = 30
POSES = ["neutral", "point_left", "point_right", "point_up", "point_down", "present_left", "present_right",
         "arms_up", "shrug", "thinking", "walking", "facepalm", "wave", "hands_hips", "cheer", "count"]
EXPRESSIONS = ["neutral", "happy", "shocked", "worried", "angry", "smug", "sad", "confused", "excited", "wink", "laughing"]
PLACEMENTS = ["center", "corner_bl", "corner_br", "corner_tl", "corner_tr", "edge_left", "edge_right"]
MOTIONS = ["hold", "cut", "fly_left", "fly_right", "fly_top", "fly_bottom", "pop", "slide", "spin"]
ZOOMS = ["none", "push", "punch"]
BGS = ["video", "photo", "scene", "prop", "black", "ui"]
TIER_COLORS = {"S": (230, 57, 70), "A": (247, 140, 44), "B": (246, 205, 58), "C": (76, 187, 96)}

_PACE = {"fast": (1.4, 2.2), "auto": (1.8, 4.0), "calm": (3.0, 5.5), "cinematic": (5.0, 8.0)}
_SCENE_FOCAL = {"city": (0.3, 0.46), "road": (0.5, 0.78), "hill": (0.3, 0.55), "house": (0.5, 0.55),
                "forest": (0.5, 0.5), "water": (0.45, 0.64), "space": (0.25, 0.3), "desert": (0.68, 0.72),
                "snow": (0.5, 0.6), "storm": (0.5, 0.4), "plain": (0.5, 0.4)}


def _pace_seconds(s, portrait):
    pace = str(s.get("pace") or "auto").lower()
    if str(s.get("stickman_backgrounds") or "") == "drawn" and pace == "auto":
        pace = "calm"                     # drawn doodle scenes read best held a little longer
    short_s, long_s = _PACE.get(pace, _PACE["auto"])
    return short_s if portrait else long_s


def _focal(beat, W, H):
    """A point on screen the character should point at this beat (a prop, a graphic or the subject of a drawn scene)."""
    if beat.get("bg") == "prop":
        from .props import layout
        L = layout(W, H)
        return (L["cx"], L["cy"])
    g = beat.get("graphic")
    if g:
        if g.get("type") == "panel":
            return (W * 0.5, H * 0.2)
        if g.get("type") in ("ring", "tier", "card"):
            return (W * 0.5, H * 0.42)
    if beat.get("bg") == "scene":
        fx, fy = _SCENE_FOCAL.get(beat.get("scene") or "", (0.4, 0.5))
        return (W * fx, H * fy)
    return None


def _mark_holds(out, seed=0):
    """Keep the character in the same spot across some beats (so he gestures in place instead of jumping around)."""
    rnd = random.Random(seed + 3)
    prev = None
    for beats in out:
        for b in beats:
            if prev is not None and b.get("character") is not False and rnd.random() < 0.5:
                b["placement"] = prev                 # stay put and keep gesturing
            b["_hold"] = (prev is not None and b.get("placement") == prev)
            prev = b.get("placement")


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
    "point_up": ((215, 500), (360, 110), (235, 840), (365, 840)),
    "point_down": ((215, 500), (430, 640), (235, 840), (365, 840)),
    "present_left": ((110, 420), (385, 500), (235, 840), (365, 840)),
    "present_right": ((215, 500), (490, 420), (235, 840), (365, 840)),
    "wave": ((215, 500), (470, 150), (235, 840), (365, 840)),
    "hands_hips": ((190, 430), (410, 430), (235, 840), (365, 840)),
    "cheer": ((150, 120), (450, 120), (225, 840), (375, 840)),
    "count": ((230, 470), (360, 230), (235, 840), (365, 840)),
}


_ARM = (122, 122)      # upper arm, forearm (canvas units)
_LEG = (150, 150)      # thigh, shin


def _ik(root, end, lengths, spine_x=300, prefer_low=False):
    """Two-bone IK: where the elbow/knee goes so the limb reaches `end` (bends away from the body)."""
    l1, l2 = lengths
    dx, dy = end[0] - root[0], end[1] - root[1]
    d = math.hypot(dx, dy) or 1.0
    reach = (l1 + l2) * 0.995
    if d >= reach:                                   # fully stretched: straight limb, clamp the hand
        ux, uy = dx / d, dy / d
        end = (root[0] + ux * reach, root[1] + uy * reach)
        return (root[0] + ux * l1, root[1] + uy * l1), end
    d = max(d, abs(l1 - l2) + 1)
    a = math.acos(max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
    base = math.atan2(dy, dx)
    cands = [(root[0] + l1 * math.cos(base + s * a), root[1] + l1 * math.sin(base + s * a)) for s in (1, -1)]
    if prefer_low:
        j = max(cands, key=lambda p: abs(p[0] - spine_x) * 0.6 + p[1] * 0.1)
    else:
        j = max(cands, key=lambda p: abs(p[0] - spine_x) + p[1] * 0.25)
    return j, end


def draw_stickman(pose="neutral", expression="neutral", seed=0, arms=None, legs=None, head_dy=0.0, mouth=0.0, blink=False,
                  boil=0, lean=0.0, hip_dx=0.0, eye_dx=0.0, eye_dy=0.0, point=None):
    """One frame of the character (600x900 RGBA).
    arms/legs: hand/foot positions (elbows and knees are worked out so the limbs bend naturally);
    head_dy bobs the head; lean tilts the upper body sideways; hip_dx shifts the weight (feet stay planted);
    mouth 0-1 opens the mouth; blink 0-1 closes the eyes (True = closed); eye_dx/dy make him look somewhere;
    point = 'l'/'r' adds a pointing finger on that hand; boil re-rolls the hand-drawn wobble (12 fps line boil)."""
    rnd = random.Random(f"{seed}-{boil}")
    im = Image.new("RGBA", (600, 900), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    W = 26
    pal, par, pll, plr = _POSE_PTS.get(pose, _POSE_PTS["neutral"])
    al, ar = (arms if arms else (pal, par))
    ll, lr = (legs if legs else (pll, plr))
    hip = (300 + hip_dx, 560)
    neck_x = 300 + lean + hip_dx * 0.5
    hb = head_dy
    sh = (neck_x, 330 + hb * 0.4)
    _marker(d, [(neck_x, 268 + hb), ((neck_x + hip[0]) / 2 + lean * 0.15, 420), hip], W, rnd)      # spine (slight curve)
    for hand, side in ((al, "l"), (ar, "r")):                                                      # arms with elbows
        el, hnd = _ik(sh, (hand[0] + lean * 0.6, hand[1]), _ARM, neck_x)
        _marker(d, [sh, el, hnd], W, rnd)
        if point == side:                                                                          # little pointing finger
            ux, uy = hnd[0] - el[0], hnd[1] - el[1]
            n = math.hypot(ux, uy) or 1
            _marker(d, [hnd, (hnd[0] + ux / n * 34, hnd[1] + uy / n * 34)], 15, rnd)
    for foot in (ll, lr):                                                                          # legs with knees
        kn, ft = _ik(hip, foot, _LEG, hip[0], prefer_low=True)
        _marker(d, [hip, kn, ft], W, rnd)
    # head: flat white circle, thick uneven outline
    cx, cy, r = neck_x, 175 + hb, 98
    pts = []
    for i in range(41):
        a = 2 * math.pi * i / 40
        rr = r + rnd.uniform(-3, 3)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=(255, 255, 255, 255))
    d.line(pts, fill=(0, 0, 0, 255), width=15, joint="curve")
    e = expression
    ex, ey = cx - 300, cy - 175
    edx, edy = max(-12, min(12, eye_dx)), max(-8, min(8, eye_dy))

    def P(x, y):
        return (x + ex, y + ey)

    def E(x, y):                                     # eye features also follow where he's looking
        return (x + ex + edx, y + ey + edy)
    bl = 1.0 if blink is True else (0.0 if blink is False else max(0.0, min(1.0, float(blink))))
    if bl > 0.75:
        _marker(d, [E(252, 158), E(278, 158)], 13, rnd)
        _marker(d, [E(322, 158), E(348, 158)], 13, rnd)
    elif e == "shocked":
        _marker(d, [E(262, 140 + 10 * bl), E(262, 168 - 6 * bl)], 16, rnd)
        _marker(d, [E(338, 140 + 10 * bl), E(338, 168 - 6 * bl)], 16, rnd)
    elif e == "excited":
        for x0 in (256, 320):
            a0, a1 = E(x0, 146 + 8 * bl), E(x0 + 24, 170 - 4 * bl)
            d.ellipse([a0[0], a0[1], a1[0], a1[1]], outline=(0, 0, 0, 255), width=10)
    elif e == "laughing":
        for x0 in (250, 310):
            a0, a1 = E(x0, 150), E(x0 + 40, 180)
            d.arc([a0[0], a0[1], a1[0], a1[1]], 180, 360, fill=(0, 0, 0, 255), width=12)
    elif e == "wink":
        _marker(d, [E(252, 160), E(278, 160)], 13, rnd)
        _marker(d, [E(335, 150 + 8 * bl), E(335, 168 - 4 * bl)], 16, rnd)
    else:
        _marker(d, [E(265, 150 + 8 * bl), E(265, 168 - 4 * bl)], 16, rnd)
        _marker(d, [E(335, 150 + 8 * bl), E(335, 168 - 4 * bl)], 16, rnd)
    if bl < 0.75:
        if e in ("worried", "sad"):
            _marker(d, [P(245, 144), P(284, 126)], 11, rnd)
            _marker(d, [P(355, 144), P(316, 126)], 11, rnd)
        elif e == "angry":
            _marker(d, [P(245, 128), P(285, 145)], 12, rnd)
            _marker(d, [P(355, 128), P(315, 145)], 12, rnd)
        elif e == "confused":
            _marker(d, [P(245, 140), P(285, 128)], 11, rnd)
            _marker(d, [P(320, 140), P(358, 142)], 11, rnd)
        elif e in ("shocked", "excited"):
            _marker(d, [P(248, 122), P(282, 118)], 10, rnd)
            _marker(d, [P(318, 118), P(352, 122)], 10, rnd)
    mo = max(0.0, min(1.0, mouth))
    if e == "laughing":
        h2 = 34 + mo * 20
        a0, a1 = P(276, 204), P(324, 204 + h2)
        d.ellipse([a0[0], a0[1], a1[0], a1[1]], fill=(0, 0, 0, 255))
    elif e in ("shocked", "excited") or mo > 0.45:
        h2 = 14 + mo * 34
        wdt = 16 + mo * 6
        a0, a1 = P(300 - wdt, 204), P(300 + wdt, 204 + h2)
        if e == "happy" or e == "excited":
            d.chord([a0[0], a0[1] - 6, a1[0], a1[1]], 0, 180, outline=(0, 0, 0, 255), fill=(0, 0, 0, 255), width=10)
        else:
            d.ellipse([a0[0], a0[1], a1[0], a1[1]], outline=(0, 0, 0, 255), width=12)
    elif e == "happy":
        a0, a1 = P(255, 175 + mo * 6), P(345, 240 + mo * 10)
        d.arc([a0[0], a0[1], a1[0], a1[1]], 20, 160, fill=(0, 0, 0, 255), width=13)
    elif e in ("smug", "wink"):
        _marker(d, [P(265, 222), P(330, 210 + mo * 8)], 13, rnd)
    elif e in ("worried", "sad"):
        a0, a1 = P(262, 212 - mo * 6), P(338, 262)
        d.arc([a0[0], a0[1], a1[0], a1[1]], 200, 340, fill=(0, 0, 0, 255), width=13)
    elif e == "angry":
        _marker(d, [P(270, 225), P(300, 222 + mo * 8), P(330, 225)], 13, rnd)
    elif e == "confused":
        _marker(d, [P(272, 222), P(298, 212 + mo * 6), P(318, 224), P(332, 214)], 11, rnd)
    else:
        if mo > 0.12:
            a0, a1 = P(282, 212), P(318, 214 + mo * 24)
            d.ellipse([a0[0], a0[1], a1[0], a1[1]], outline=(0, 0, 0, 255), width=11)
        else:
            _marker(d, [P(270, 220), P(330, 220)], 13, rnd)
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
  "black" (plain black, rarely), "ui" (a flat generic app/website screen), or
  "scene" (a hand-drawn doodle of the PLACE/OBJECT being described, in the character's own marker style; also give
  "scene": one of city, road, hill, house, forest, water, space, desert, snow, storm — pick the closest to the subject), or
  "prop" (a simple hand-drawn doodle of the specific THING being talked about, drawn big on a plain page while the character
  stands beside it and points at it — like an explainer video showing an example of each thing mentioned. Give "prop": the
  thing in 1-3 plain words (e.g. "lighthouse", "fingerprint", "money", "ai chatbot", "plane", "dna"), and optional "label":
  up to 3 words hand-written above/under it (use it for names, brands, places, dates, numbers so viewers know what it is,
  e.g. "Claude AI", "Flannan Isles", "1900"))
- pose: {poses}   (the character now ANIMATES in place: his arms move, he blinks and talks. point_*/present_* make him
  point straight at the background subject or the on-screen graphic, so choose those when he's calling something out)
- expression: {expressions}   (you may also add "expression2": a second expression he changes to partway through the beat)
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

The narration is split into segments; each needs exactly the given number of beats. Hold each beat — the character keeps
moving on his own (arm gestures, pointing, blinking, talking, changing expression), so you do NOT need a hard cut to keep it alive.
Prefer keeping the same placement across neighbouring beats and let him gesture in place; change placement only now and then.
{prop_rule}
Vary poses and expressions so he feels alive, and make them fit the words (point_* / present_* when calling something out,
shocked/excited on a reveal, thinking on a question, sad/worried on something grim). Backgrounds must match what is being said.
BACKGROUNDS: use "video" for most beats (moving footage keeps viewers watching), "photo" for the rest. Use "black" on at most
{black_pct}% of beats (only for a deliberate dramatic pause), even if the direction mentions black. Queries must be concrete things
a camera could film (places, objects, weather, crowds, vehicles), not abstract ideas: "abandoned hospital hallway", not "mystery".

SEGMENTS:
{segments}

Return JSON: {{"segments": [{{"beats": [{{"bg": "...", "query": "...", "scene": "...", "prop": "...", "label": "...", "pose": "...", "expression": "...", "expression2": "...", "placement": "...", "motion": "...", "zoom": "...", "character": true, "graphic": null}}]}}]}}"""


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
                                segments="\n".join(lines), black_pct=_black_pct(s), prop_rule=_prop_rule(s))
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
    mode = str(s.get("stickman_backgrounds") or "stock").lower()
    if str(s.get("props") or "some").lower() == "off":
        for beats in out:
            for b in beats:
                if b.get("bg") == "prop":
                    b["bg"] = "scene" if mode == "drawn" else "video"
                    b["query"] = b.get("prop") or b.get("query")
    if mode == "drawn":
        for i, beats in enumerate(out):
            for b in beats:
                if not b.get("graphic") and b.get("bg") != "prop":
                    b["bg"] = "scene"
                    b["scene"] = b.get("scene") or scenes.scene_for(b.get("query"), segs[i]["text"])
    else:
        _limit_black(out, segs, _black_pct(s), rnd)
        if mode == "mix":
            for i, beats in enumerate(out):
                for b in beats:
                    if b.get("bg") == "scene" and not b.get("scene"):
                        b["scene"] = scenes.scene_for(b.get("query"), segs[i]["text"])
    _mark_holds(out, len(segs))
    return out


_PROP_RULES = {
    "off": "PROPS: do not use \"prop\" backgrounds.",
    "some": "PROPS: whenever the narration names a specific thing, object, person-type, brand, place or number worth showing, "
            "use a \"prop\" beat for it (about 1 in 4 beats); keep the others as the usual backgrounds.",
    "lots": "PROPS: use \"prop\" beats a lot (about half the beats): every time the narration names a thing, object, brand, "
            "place, number or idea, show it as a prop he points at, like an explainer video.",
}


def _prop_rule(s):
    return _PROP_RULES.get(str(s.get("props") or "some").lower(), _PROP_RULES["some"])


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
        "scene": (str(b.get("scene")).strip().lower() if str(b.get("scene") or "").strip().lower() in scenes.SCENES else None),
        "prop": (str(b.get("prop") or "").strip()[:60] or None),
        "label": (str(b.get("label") or "").strip()[:28] or None),
        "pose": pick("pose", POSES, rnd.choice(POSES)),
        "expression": pick("expression", EXPRESSIONS, rnd.choice(EXPRESSIONS)),
        "expression2": pick("expression2", EXPRESSIONS, None),
        "placement": pick("placement", PLACEMENTS, rnd.choice(PLACEMENTS)),
        "motion": pick("motion", MOTIONS, "hold" if rnd.random() < 0.7 else rnd.choice(["pop", "fly_left", "fly_right", "slide"])),
        "zoom": pick("zoom", ZOOMS, "push"),
        "character": b.get("character", True) is not False,
        "graphic": g,
    }


# ------------------------------------------------------------------------------------------ rendering
def _ease(t):
    return 1 - (1 - max(0.0, min(1.0, t))) ** 3


def _target(placement, W, H, seed=0):
    """(center x, center y, figure height, rotation degrees) for a placement.
    Deterministic from the placement, so beats that keep the same placement line up exactly (no micro-jump)."""
    rnd = random.Random(placement)
    tilt = rnd.uniform(22, 36)
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

    def __init__(self, photos, footage, portrait, genre, drawn_bg="white", solid_color=(0, 0, 0)):
        self.photos, self.footage, self.portrait, self.genre = photos, footage, portrait, genre
        self.drawn_bg = drawn_bg if drawn_bg in ("white", "black") else "white"
        self.solid = solid_color
        self.recent = []         # recent good still backgrounds
        self.counts = {"video": 0, "photo": 0, "scene": 0, "prop": 0, "ui": 0, "reused": 0, "gradient": 0, "black": 0}
        self.s = None
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


# -------------------------------------------------------------------- animated character
_SHOULDER = (300, 330)
_REST = ((215, 500), (385, 500))
_GESTURE_FOR = {"point_left": "point_left", "point_right": "point_right", "point_up": "point_up", "point_down": "point_down",
                "present_left": "present_left", "present_right": "present_right", "arms_up": "raise", "cheer": "cheer",
                "shrug": "shrug", "thinking": "think", "facepalm": "facepalm", "wave": "wave", "hands_hips": "hands_hips",
                "count": "count", "walking": "explain", "neutral": "explain"}
_GEST_ARMS = {                      # None = keep the resting arm
    "point_left": ((70, 300), None), "point_right": (None, (530, 300)), "point_up": (None, (360, 110)),
    "point_down": (None, (430, 640)), "present_left": ((110, 420), None), "present_right": (None, (490, 420)),
    "raise": ((170, 130), (430, 130)), "cheer": ((150, 120), (450, 120)), "shrug": ((150, 270), (450, 270)),
    "think": (None, (330, 250)), "facepalm": (None, (300, 190)), "wave": (None, (470, 150)),
    "hands_hips": ((190, 430), (410, 430)), "count": (None, (360, 230)), "explain": ((250, 440), (350, 440)),
}
_POINTERS = ("point_left", "point_right", "point_up", "point_down", "present_left", "present_right")
_CHAR_FPS = 12                      # the character animates at 12 fps (limited-animation look, and cheap)


def _lerp(a, b, k):
    return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)


class _Spring:
    """Critically-ish damped spring (a little overshoot) used for hands, lean and head, so motion flows."""

    def __init__(self, x, k=170.0, zeta=0.45):
        self.x, self.v = list(x), [0.0] * len(x)
        self.k, self.c = k, 2 * zeta * math.sqrt(k)

    def step(self, target, dt):
        for i in range(len(self.x)):
            a = self.k * (target[i] - self.x[i]) - self.c * self.v[i]
            self.v[i] += a * dt
            self.x[i] += self.v[i] * dt


class _Actor:
    """Animates the character in place, at 12 fps, with flowing motion:
    springy hands that overshoot and settle, pose carried over from the previous shot, a wind-up before pointing,
    lean + weight shift with follow-through, eyes that track what he points at, natural blinks,
    a mouth that moves with the actual words being spoken, and little head nods on stressed words."""

    SUB = 4                                          # physics sub-steps per drawn frame

    def __init__(self, beat, fh, seed, pos, rot, size, point_target=None, words=None, t0=0.0, start=None, track=None):
        self.b, self.fh, self.seed = beat, fh, seed
        self.cx, self.cy, self.rot = pos[0], pos[1], rot
        self.W, self.H = size
        self.gname = _GESTURE_FOR.get(beat["pose"], "explain")
        self.gesture = _GEST_ARMS.get(self.gname, _GEST_ARMS["explain"])
        self.expr = beat["expression"]
        self.expr2 = beat.get("expression2") if beat.get("expression2") in EXPRESSIONS else None
        self.rnd = random.Random(seed * 101 + 7)
        self.ph = self.rnd.uniform(0, 6.28)
        self.talk_seed = seed * 31 + 5
        self.fixed_target = point_target
        self.track = track
        self.words = sorted((w["s"] - t0, w["e"] - t0) for w in (words or []) if w["e"] - t0 > -0.2)
        self.onsets = [s for s, _ in self.words]
        st = start or {}
        self.l = _Spring(st.get("l", _REST[0]))
        self.r = _Spring(st.get("r", _REST[1]))
        self.lean = _Spring([st.get("lean", 0.0)], k=60, zeta=0.6)
        self.head = _Spring([st.get("head", 0.0)], k=120, zeta=0.5)
        self.start_l, self.start_r = tuple(self.l.x), tuple(self.r.x)
        self.blinks = []
        tb = self.rnd.uniform(0.6, 2.2)
        while tb < 120:
            self.blinks.append(tb)
            tb += self.rnd.uniform(2.2, 4.2)
        self.glances = [(i * 1.9 + self.rnd.uniform(0, 0.6), self.rnd.uniform(-7, 7), self.rnd.uniform(-4, 3)) for i in range(64)]
        self.sim_f = 0
        self._cache = {}
        self._last = None

    # ------------------------------------------------------------------ helpers
    def _target_at(self, t):
        if self.track is not None:
            try:
                return self.track(t)
            except Exception:
                return None
        return self.fixed_target

    def _aim(self, target):
        """Hand position (canvas) for pointing straight at a screen point, and which arm does it."""
        k = self.fh / 900.0
        shx, shy = self.cx, self.cy - 120 * k
        dx, dy = target[0] - shx, target[1] - shy
        if self.rot:
            a = math.radians(-self.rot)
            dx, dy = dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)
        n = math.hypot(dx, dy) or 1
        dx, dy = dx / n, dy / n
        look = (dx, dy)
        if abs(dx) > 0.15:                       # keep a clear point: at most ~35 deg up (straight up beside the head
            ang = math.atan2(dy, abs(dx))        # reads as a raised hand, not a point)
            ang = max(math.radians(-35), min(math.radians(55), ang))
            dx, dy = math.copysign(math.cos(ang), dx), math.sin(ang)
        side = "l" if dx < 0 else "r"
        return side, (300 + dx * 236, 330 + dy * 236), look

    def _speech(self, t):
        """(mouth 0-1, nod 0-1) from the real word timings."""
        for i, (s, e) in enumerate(self.words):
            if s <= t < e:
                f = (t - s) / max(0.06, e - s)
                syl = max(1, int((e - s) / 0.18))                    # long words open/close more than once
                amp = 0.55 + 0.45 * random.Random(self.talk_seed + i).random()
                return amp * abs(math.sin(math.pi * f * syl)) ** 0.7, 0.0
        if not self.words:
            r = random.Random(self.talk_seed + int(t * _CHAR_FPS))
            return (0.0 if r.random() < 0.25 else r.uniform(0.2, 0.9)), 0.0
        return 0.0, 0.0

    def _nod(self, t):
        best = 0.0
        for s in self.onsets:
            if 0 <= t - s < 0.35:
                best = max(best, math.exp(-(t - s) * 9))
        return best

    def _targets(self, t, dur):
        gl, gr = self.gesture
        gl = gl or _REST[0]
        gr = gr or _REST[1]
        point_side, look = None, None
        target = self._target_at(t)
        if target is not None and (self.gname in _POINTERS or self.track is not None):
            point_side, hand, look = self._aim(target)
            if point_side == "l":
                gl, gr = hand, _REST[1]
            else:
                gl, gr = _REST[0], hand
        elif target is not None:
            _, _, look = self._aim(target)
        sway = math.sin(t * 1.6 + self.ph)
        gl = (gl[0] + sway * 9, gl[1] + math.sin(t * 2.1) * 7)
        gr = (gr[0] - sway * 9, gr[1] + math.cos(t * 1.9) * 7)
        g = self.gname
        talk = self._nod(t)
        if g == "wave":
            gr = (gr[0] + math.sin(t * 7) * 45, gr[1] - abs(math.sin(t * 7)) * 20)
        elif g == "cheer":
            pump = abs(math.sin(t * 5)) * 60
            gl, gr = (gl[0], gl[1] - pump), (gr[0], gr[1] - pump)
        elif g == "count":
            gr = (gr[0] + math.sin(t * 4) * 12, gr[1] + math.sin(t * 8) * 18)
        elif g == "think":
            gr = (gr[0], gr[1] + math.sin(t * 6) * 9)
        elif g == "explain" and point_side is None:                 # hands open with the rhythm of the words
            o = 18 + 40 * talk + math.sin(t * 2.6) * 12
            gl, gr = (gl[0] - o, gl[1] - 20 * talk), (gr[0] + o, gr[1] - 20 * talk)
        elif g in ("present_left", "present_right") and point_side is None:
            dd = math.sin(t * 3) * 14
            gl, gr = ((gl[0] - dd, gl[1] + dd), gr) if g.endswith("left") else (gl, (gr[0] + dd, gr[1] + dd))
        if point_side and t < 0.14 and not self.b.get("_hold"):  # wind-up: pull back a touch before pointing
            if point_side == "l":
                s0 = self.start_l
                gl = (s0[0] - (gl[0] - s0[0]) * 0.2, s0[1] - (gl[1] - s0[1]) * 0.2)
            else:
                s0 = self.start_r
                gr = (s0[0] - (gr[0] - s0[0]) * 0.2, s0[1] - (gr[1] - s0[1]) * 0.2)
        lean_t = (14 * (1 if look[0] > 0 else -1) * min(1, abs(look[0]) * 1.5)) if (look and point_side) else math.sin(t * 0.8 + self.ph) * 6
        return gl, gr, lean_t, point_side, look

    def _advance(self, fi, dur):
        if fi < self.sim_f:                                          # asked to go back: start over (rare)
            self.__init__(self.b, self.fh, self.seed, (self.cx, self.cy), self.rot, (self.W, self.H), self.fixed_target,
                          None, 0.0, {"l": self.start_l, "r": self.start_r}, self.track)
        dt = 1.0 / (_CHAR_FPS * self.SUB)
        while self.sim_f < fi:
            for k in range(self.SUB):
                t = (self.sim_f + k / self.SUB) / _CHAR_FPS
                gl, gr, lean_t, _, _ = self._targets(t, dur)
                self.l.step(gl, dt)
                self.r.step(gr, dt)
                self.lean.step([lean_t], dt)
                self.head.step([-10 * self._nod(t)], dt)
            self.sim_f += 1

    def _figure(self, t, dur):
        fi = int(t * _CHAR_FPS)
        if fi in self._cache:
            return self._cache[fi]
        self._advance(fi, dur)
        tt = fi / _CHAR_FPS
        gl, gr, lean_t, point_side, look = self._targets(tt, dur)
        mouth, _ = self._speech(tt)
        bounce = abs(math.sin(tt * 2.4)) * 5 if self.gname in ("cheer", "wave") else 0
        head_dy = math.sin(tt * 1.3 + self.ph) * 4 - bounce + self.head.x[0]
        blink = 0.0
        for tb in self.blinks:
            if 0 <= tt - tb < 3 / _CHAR_FPS:
                blink = (0.5, 1.0, 0.5)[int((tt - tb) * _CHAR_FPS)]
                break
        if look is not None:
            edx, edy = look[0] * 12, look[1] * 8
        else:
            edx, edy = 0.0, 0.0
            for g0, gx, gy in self.glances:
                if 0 <= tt - g0 < 0.7:
                    edx, edy = gx, gy
                    break
        expr = self.expr2 if (self.expr2 and tt > dur * 0.55) else self.expr
        hip = math.sin(tt * 0.9 + self.ph) * 9
        pointing = point_side if (point_side and (self.b.get("_hold") or tt > 0.25)) else None
        fig = draw_stickman(self.b["pose"], expr, self.seed % 7, arms=(tuple(self.l.x), tuple(self.r.x)), head_dy=head_dy,
                            mouth=mouth, blink=blink, boil=fi % 3, lean=self.lean.x[0], hip_dx=hip, eye_dx=edx, eye_dy=edy,
                            point=pointing)
        scale = self.fh / fig.height
        fig = fig.resize((max(1, int(fig.width * scale)), max(1, int(fig.height * scale))), Image.BILINEAR)
        if self.rot:
            fig = fig.rotate(self.rot, expand=True, resample=Image.BICUBIC)
        self._cache = {fi: fig}
        return fig

    def final_state(self):
        return {"l": tuple(self.l.x), "r": tuple(self.r.x), "lean": self.lean.x[0], "head": self.head.x[0]}

    def draw(self, im, t, dur):
        fig = self._figure(t, dur)
        m = self.b.get("motion", "hold")
        dx, dy, speed = 0.0, 0.0, None
        sc = 1.0
        if not self.b.get("_hold") and m.startswith("fly_") and t < 0.2:
            k = 1 - _ease(t / 0.2)
            off = {"fly_left": (-self.W, 0), "fly_right": (self.W, 0), "fly_top": (0, -self.H), "fly_bottom": (0, self.H)}[m]
            dx, dy, speed = off[0] * k, off[1] * k, off
        elif not self.b.get("_hold") and m == "pop" and t < 0.3:
            sc = 0.7 + 0.42 * _ease(t / 0.18) if t < 0.18 else 1.12 - 0.12 * ((t - 0.18) / 0.12)
        if sc != 1.0:
            fig = fig.resize((max(1, int(fig.width * sc)), max(1, int(fig.height * sc))), Image.BILINEAR)
        x = int(self.cx + dx - fig.width / 2)
        y = int(self.cy + dy - fig.height / 2)
        if speed:
            d = ImageDraw.Draw(im)
            ux = 1 if speed[0] < 0 else -1 if speed[0] > 0 else 0
            uy = 1 if speed[1] < 0 else -1 if speed[1] > 0 else 0
            for k in range(5):
                ox = (k - 2) * fig.height * 0.12
                sx = self.cx + dx - ux * fig.width * 0.5 + (ox if ux == 0 else 0)
                sy = self.cy + dy - uy * fig.height * 0.5 + (ox if uy == 0 else 0)
                d.line([(sx, sy), (sx - ux * self.W * 0.18, sy - uy * self.H * 0.12)], fill=(0, 0, 0), width=10)
        im.paste(fig, (x, y), fig)


class _Beat:
    def __init__(self, beat, dur, W, H, bgs, portrait, seed, keep=None, bgdir=None, words=None, t0=0.0, start=None,
                 prev_prop=None):
        """keep: what this beat used last time (re-edit of an unchanged beat). bgdir: where still backgrounds are saved.
        words/t0: the narration word timings and when this beat starts (for lip-sync). start: the character's pose at the
        end of the previous beat (so his motion carries on). prev_prop: the previous beat's prop (no redraw if the same)."""
        self.b, self.dur, self.W, self.H, self.seed = beat, dur, W, H, seed
        bg = beat["bg"]
        g = beat.get("graphic")
        if bg == "prop":
            g = None                                   # the prop is the graphic
        BW, BH = int(W * 1.06), int(H * 1.06)
        base, self.reader, self.scene, self.prop = None, None, None, None
        self.prop_key = None
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
        if base is None and keep and keep.get("kind") == "scene":
            from .scenes import SceneClip
            self.scene = SceneClip(keep.get("name") or "hill", BW, BH, bg=keep.get("bg") or bgs.drawn_bg, seed=seed)
            base = self.scene.frame(0.0)
            self.resolved = dict(keep)
            bgs.counts["scene"] += 1
        if base is None and (bg == "prop" or (keep and keep.get("kind") == "prop")):
            from .props import PropClip, resolve
            if keep and keep.get("kind") == "prop" and keep.get("src"):
                src = tuple(keep["src"])
            else:
                src = resolve(bgs.s or {}, beat.get("prop") or beat.get("query") or "", bgs.drawn_bg)
            self.prop_key = f"{src[0]}:{src[1]}"
            self.prop = PropClip(src, BW, BH, paper=bgs.drawn_bg, seed=seed, label=beat.get("label"),
                                 reveal=(prev_prop != self.prop_key), frame_size=(W, H))
            base = self.prop.frame(0.0)
            self.resolved = {"kind": "prop", "src": list(src), "label": beat.get("label")}
            bgs.counts["prop"] = bgs.counts.get("prop", 0) + 1
        if base is not None:
            pass
        elif bg == "scene":
            from .scenes import SceneClip, scene_for
            name = beat.get("scene") or scene_for(beat.get("query"), "")
            self.scene = SceneClip(name, BW, BH, bg=bgs.drawn_bg, seed=seed)
            base = self.scene.frame(0.0)
            self.resolved = {"kind": "scene", "name": name, "bg": bgs.drawn_bg}
            bgs.counts["scene"] += 1
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
            base = Image.new("RGB", (BW, BH), bgs.solid)
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
        self.actor = None
        if beat["character"]:
            ab = beat
            if self.prop is not None:                    # stands beside the prop and points at it
                from .props import layout
                cx, cy, fh = layout(W, H)["char"]
                rot = 0
                if beat.get("pose") not in _POINTERS:
                    ab = dict(beat, pose=("point_right", "present_right", "point_up")[seed % 3])
            else:
                cx, cy, fh, rot = _target(beat["placement"], W, H, seed)
                if beat["placement"] in ("corner_tl", "corner_tr") and g:
                    fh *= 0.8
                if g and (beat["placement"] == "center" or g["type"] == "tier"):     # keep graphics readable
                    cx, cy, fh, rot = W * 0.84, H * 0.9, H * 0.3, 25
            self.actor = _Actor(ab, fh, seed, (cx, cy), rot, (W, H), point_target=_focal(beat, W, H), words=words, t0=t0,
                                start=start)

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
            elif self.scene is not None and not self._first:
                self.base = self.scene.frame(t)
            elif self.prop is not None and not self._first:
                self.base = self.prop.frame(t)
            self._first = False
            bw, bh = self.base.size
            z = 1.0 + (0.05 * p if (b["zoom"] in ("push", "punch") and self.prop is None) else 0)
            cw, ch = bw / z, bh / z
            x0, y0 = (bw - cw) / 2, (bh - ch) / 2
            im = self.base.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.BILINEAR)
        if self.overlay is not None:
            im.paste(self.overlay, (0, 0), self.overlay)
        if b["character"]:
            self._draw_fig(im, t)
        if b["zoom"] == "punch" and self.prop is None:
            z = 1.18 if t > 0.08 else 1.0 + 0.18 * (t / 0.08)
            cw, ch = W / z, H / z
            im = im.crop((int((W - cw) / 2), int((H - ch) / 2), int((W + cw) / 2), int((H + ch) / 2))).resize((W, H), Image.BILINEAR)
        return im

    def _draw_fig(self, im, t):
        if self.actor is not None:
            self.actor.draw(im, t, self.dur)

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
        words = voice.narrate(s, sg["text"], mp3, portrait=portrait, log=log)
        dur = max(media_duration(mp3), 0.5) + 0.15
        wav = os.path.join(work, f"v{i:02d}.wav")
        run([ffmpeg_path(), "-v", "error", "-y", "-i", mp3, "-af", "apad", "-t", f"{dur:.3f}", "-ar", "48000", "-ac", "2", wav])
        wavs.append(wav)
        words_all += [{"s": w["s"] + t0, "e": w["e"] + t0, "w": w["w"]} for w in words]
        shot = _pace_seconds(s, portrait)
        segs.append({"text": sg["text"], "dur": dur, "beats": max(1, int(round(dur / shot))), "chapter": sg.get("chapter", ""), "start": t0})
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
    _mode = str(s.get("stickman_backgrounds") or "stock").lower()
    _drawn_bg = str(s.get("drawn_bg") or "white").lower()
    _solid = (8, 10, 16) if (_mode == "stock" or _drawn_bg == "black") else (250, 250, 248)
    bgs = _Bg(photos, footage, portrait, s.get("genre"), drawn_bg=_drawn_bg, solid_color=_solid)
    bgs.s = s
    bgdir = os.path.join(work, "bgs")
    os.makedirs(bgdir, exist_ok=True)

    if log:
        log("info", "Drawing frames")
    cmd = [ffmpeg_path(), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", "voice.wav", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "mux.mp4"]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE, cwd=work, **_popen_kwargs())
    frame_no, seed, n_beat, resolved = 0, 0, 0, []
    pose_state, prev_prop = None, None
    words = ed.get("words") or []
    try:
        for si, sg in enumerate(segs):
            n = len(beats[si])
            seg_frames = int(round((sg["start"] + sg["dur"]) * FPS)) - frame_no
            wts = [2.0 if b.get("bg") == "prop" else 1.0 for b in beats[si]]      # props get a 3-5 s look
            tot = sum(wts) or 1.0
            per = [int(seg_frames * w / tot) for w in wts]
            for k in range(seg_frames - sum(per)):
                per[k % n] += 1
            for bi, b in enumerate(beats[si]):
                seed += 1
                nf = per[bi]
                keep = None if redo(n_beat) else old[n_beat]
                n_beat += 1
                if nf <= 0:
                    resolved.append(keep or {"kind": "none"})
                    continue
                beat = _Beat(b, nf / FPS, W, H, bgs, portrait, seed, keep=keep, bgdir=bgdir, words=words,
                             t0=frame_no / FPS, start=pose_state, prev_prop=prev_prop)
                resolved.append(beat.resolved)
                try:
                    for k in range(nf):
                        proc.stdin.write(beat.frame(k / FPS).tobytes())
                        frame_no += 1
                finally:
                    if beat.reader is not None:
                        beat.reader.close()
                if beat.actor is not None:
                    pose_state = beat.actor.final_state()          # next shot carries his pose on
                prev_prop = beat.prop_key
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
        log("info", f"Backgrounds: {c['video']} moving, {c['scene']} drawn, {c['prop']} props, {c['photo']} photo, {c['ui']} screen, {c['reused']} reused, "
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
    parts, cap_words, ec = [os.path.join(work, "mux.mp4")], list(ed["words"]), None
    from . import endcard
    if endcard.enabled(s):
        ec = ed.get("endcard")
        if not (ec and os.path.exists(ec.get("path") or "")):
            try:
                ec = endcard.build(s, portrait, work, log)
            except Exception as e:
                ec = None
                if log:
                    log("warn", f"Couldn't add the like & subscribe ending ({e}).")
        if ec:
            off = media_duration(parts[0])
            parts.append(ec["path"])
            cap_words += [{"s": w["s"] + off, "e": w["e"] + off, "w": w["w"]} for w in ec.get("words") or []]
    _finish(_Override(s, captions=captions), parts, cap_words if captions else [], portrait, work, out_path)
    credits = list(dict.fromkeys(c for c in bgs.credits_used if c))
    ed = dict(ed, resolved=resolved, credits=credits, endcard=ec)
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
- bg: "video" (moving stock footage) / "photo" / "scene" (hand-drawn doodle) / "prop" (a doodle of a specific thing he points at;
  give "prop": the thing in 1-3 words and optional "label": up to 3 words written with it) / "ui" / "black"; query: 2-4 concrete visual words
- scene: city / road / hill / house / forest / water / space / desert / snow / storm (only when bg is "scene")
- new_footage: true  (same idea but different footage than before; use when the owner says a clip is bad/wrong/repetitive)
- pose: {poses}; expression: {expressions}; expression2 (optional); placement: {placements}; motion: {motions}; zoom: {zooms}; character: true/false
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
                         + (f" graphic={json.dumps(g)}" if g else "")
                         + (f" prop=\"{b.get('prop')}\" label=\"{b.get('label') or ''}\"" if b.get("bg") == "prop" else "")
                         + f" pose={b['pose']} character={b['character']}")
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
        for key in ("bg", "query", "scene", "prop", "label", "pose", "expression", "expression2", "placement", "motion", "zoom",
                    "character", "graphic"):
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
