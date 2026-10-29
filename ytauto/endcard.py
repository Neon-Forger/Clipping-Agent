"""Like & subscribe end card, added automatically to the end of every original video (Shorts and long videos).

What happens (about 4 seconds, on a plain white or black page):
- a big hand-drawn SUBSCRIBE button, a thumbs-up and a bell draw themselves on,
- the character says a like-and-subscribe line (in the chosen voice) and points at the button,
- a cartoon cursor clicks it ("pop"), it turns into SUBSCRIBED and the bell rings ("ding"),
- an arrow draws itself down ("whoosh") to where YouTube's real subscribe button is (bottom-left on Shorts, below the
  video on long videos), a ring pulses there, and the character points at it.

The button is a generic red SUBSCRIBE button, not YouTube's logo (that's a trademark). The sound effects are
synthesized from scratch, so there's nothing copyrighted in it."""
import hashlib
import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw

from agent.tools import ffmpeg_path, media_duration, run

from . import voice
from .props import PropArt
from .sketch import PAPER, Pen, hand_font

FPS = 30
LINES = [
    "If you enjoyed this, hit like and subscribe!",
    "Like and subscribe for more stories like this!",
    "Subscribe so you don't miss the next one!",
    "Don't forget to like and subscribe!",
    "Want more? Hit that subscribe button!",
    "Thanks for watching! Like and subscribe!",
]


def _popen_kwargs():
    return {"creationflags": 0x08000000} if sys.platform == "win32" else {}


# ---------------------------------------------------------------------------------------- sound effects
_SFX = {
    "ding": ["-f", "lavfi", "-i",
             "aevalsrc=exprs='0.30*(sin(2*PI*1318.5*t)+0.55*sin(2*PI*2637*t)+0.22*sin(2*PI*3951*t))*exp(-3.2*t)':s=48000:d=1.6"],
    "pop": ["-f", "lavfi", "-i", "aevalsrc=exprs='0.75*sin(2*PI*(1400-1000*t/0.12)*t)*exp(-28*t)':s=48000:d=0.16"],
    "whoosh": ["-f", "lavfi", "-i", "anoisesrc=d=0.6:c=pink:r=48000:a=0.55",
               "-af", "highpass=f=350,lowpass=f=3200,afade=t=in:d=0.28,afade=t=out:st=0.28:d=0.32"],
}


def sfx(name):
    """Path to a synthesized sound effect (made once, then cached)."""
    from agent.config import data_dir
    d = os.path.join(data_dir(), "sfx")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{name}.wav")
    if not os.path.exists(path):
        run([ffmpeg_path(), "-v", "error", "-y"] + _SFX[name] + ["-ac", "2", "-ar", "48000", path])
    return path


# ---------------------------------------------------------------------------------------- layout
def _layout(W, H):
    if H > W:   # Shorts: the real subscribe button sits bottom-left, next to the channel name
        return {"btn": (W * 0.46, H * 0.33, W * 0.68, H * 0.1), "like": (W * 0.24, H * 0.17, W * 0.26),
                "bell": (W * 0.68, H * 0.17, W * 0.24), "char": (W * 0.78, H * 0.68, H * 0.4),
                "arrow": [(W * 0.36, H * 0.4), (W * 0.24, H * 0.6), (W * 0.33, H * 0.86)], "spot": (W * 0.36, H * 0.905)}
    return {"btn": (W * 0.42, H * 0.42, W * 0.36, H * 0.16), "like": (W * 0.15, H * 0.42, H * 0.26),
            "bell": (W * 0.66, H * 0.16, H * 0.22), "char": (W * 0.83, H * 0.6, H * 0.62),
            "arrow": [(W * 0.36, H * 0.52), (W * 0.27, H * 0.72), (W * 0.24, H * 0.95)], "spot": (W * 0.24, H * 1.02)}


def _bez(pts, k):
    (x0, y0), (x1, y1), (x2, y2) = pts
    return ((1 - k) ** 2 * x0 + 2 * (1 - k) * k * x1 + k * k * x2, (1 - k) ** 2 * y0 + 2 * (1 - k) * k * y1 + k * k * y2)


def _ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


class _Card:
    def __init__(self, W, H, paper, seed, dur, voice_dur):
        self.W, self.H, self.paper, self.seed = W, H, paper, seed
        self.L = _layout(W, H)
        self.dur = dur
        self.click = max(1.0, min(voice_dur * 0.55, dur - 2.4))
        self.arrow_t = self.click + 0.5
        lx, ly, ls = self.L["like"]
        bx, by, bs = self.L["bell"]
        self.like = PropArt("thumbs_up", int(ls), paper, seed)
        self.bell = PropArt("bell", int(bs), paper, seed + 1)
        self.ink = (20, 20, 24) if paper == "white" else (240, 243, 250)

    def target(self, t):
        """Where the character points: the button, then the real subscribe spot once the arrow is drawn."""
        if t < self.arrow_t + 0.25:
            bx, by, _, _ = self.L["btn"]
            return (bx, by)
        return self.L["arrow"][-1]

    def frame(self, t):
        W, H = self.W, self.H
        im = Image.new("RGB", (W, H), PAPER[self.paper])
        d = ImageDraw.Draw(im)
        fi = int(t * 12)
        tt = fi / 12.0
        # thumbs up + bell (the bell starts ringing on the click)
        lx, ly, ls = self.L["like"]
        bump = 1 + 0.12 * max(0, math.sin((tt - 0.2) * 6)) * (1 if tt < 1.4 else 0)
        art = self.like.render(tt)
        if bump != 1:
            art = art.resize((int(art.width * bump), int(art.height * bump)), Image.BILINEAR)
        im.paste(art, (int(lx - art.width / 2), int(ly - art.height / 2)), art)
        bx, by, bs = self.L["bell"]
        bell_t = tt if tt < self.click else 0.6 + (tt - self.click)      # its swing kicks in on the click
        art = self.bell.render(bell_t if tt >= self.click else min(tt, 0.59))
        im.paste(art, (int(bx - art.width / 2), int(by - art.height / 2)), art)
        # the button
        cx, cy, bw, bh = self.L["btn"]
        reveal = _ease(tt / 0.5)
        press = 1.0
        if self.click <= tt < self.click + 0.18:
            press = 0.9
        elif self.click + 0.18 <= tt < self.click + 0.36:
            press = 1.05
        done = tt >= self.click + 0.1
        w2, h2 = bw * press * (0.6 + 0.4 * reveal) / 2, bh * press * (0.6 + 0.4 * reveal) / 2
        size = max(w2, h2) * 2
        pen = Pen(d, cx - size / 2, cy - size / 2, size, "white", self.seed, fi % 3)
        u = 100 / size
        pen.rrect(50 - w2 * u, 50 - h2 * u, 50 + w2 * u, 50 + h2 * u, r=h2 * u * 0.5, w=2.2 * (300 / size) + 1.4,
                  fill="gray" if done else "red")
        label = "SUBSCRIBED" if done else "SUBSCRIBE"
        f = hand_font(bh * press * 0.46 * (0.6 + 0.4 * reveal))
        d.text((cx, cy + 2), label, font=f, fill=(255, 255, 255), anchor="mm")
        if done:
            tick_x = cx + d.textlength(label, font=f) / 2 + bh * 0.25
            tp = Pen(d, tick_x - bh * 0.2, cy - bh * 0.2, bh * 0.4, "white", self.seed + 3, fi % 3)
            tp.stroke([(15, 55), (40, 80), (90, 20)], w=12, color="white")
            if tt < self.click + 0.8:                                           # little burst of sparkles
                sp = Pen(d, cx - bw / 2, cy - bw / 2, bw, "white", self.seed, fi % 3, t=tt * 3)
                for k, (ox, oy) in enumerate(((10, 30), (90, 34), (6, 66), (94, 70), (50, 18))):
                    sp.sparkle(ox, oy, r=5, w=1.4, color="yellow", phase=k)
        # cartoon cursor sliding in and clicking
        if self.click - 0.55 <= tt < self.click + 0.45:
            k = _ease((tt - (self.click - 0.55)) / 0.5)
            px = cx + bw * 0.2 + (1 - k) * W * 0.35
            py = cy + bh * 0.15 + (1 - k) * H * 0.12
            cs = bh * 0.9
            cp = Pen(d, px, py, cs, "white", self.seed + 7, fi % 3)
            cp.poly([(0, 0), (0, 74), (18, 58), (30, 86), (42, 80), (30, 54), (54, 54)], w=6, fill="white", color="black")
            if self.click <= tt < self.click + 0.25:
                for a in (200, 240, 280, 320):
                    r = math.radians(a)
                    d.line([(px + math.cos(r) * cs * 0.25, py + math.sin(r) * cs * 0.25),
                            (px + math.cos(r) * cs * 0.5, py + math.sin(r) * cs * 0.5)], fill=self.ink, width=max(3, int(cs * 0.05)))
        # arrow down to the real subscribe button, then a pulsing ring there
        if tt >= self.arrow_t:
            k = _ease((tt - self.arrow_t) / 0.55)
            pts = [_bez(self.L["arrow"], i / 24 * k) for i in range(25)]
            ap = Pen(d, 0, 0, 100, "white", self.seed + 9, fi % 3)
            ap.k = 1.0
            col = "red" if self.paper == "white" else "yellow"
            ap.stroke(pts, w=max(8, W * 0.014), color=col)
            if k > 0.95:
                (x1, y1), (x2, y2) = pts[-3], pts[-1]
                a = math.atan2(y2 - y1, x2 - x1)
                hl = W * 0.05
                ap.stroke([(x2 - hl * math.cos(a - 0.5), y2 - hl * math.sin(a - 0.5)), (x2, y2),
                           (x2 - hl * math.cos(a + 0.5), y2 - hl * math.sin(a + 0.5))], w=max(8, W * 0.014), color=col)
                sx, sy = self.L["spot"]
                pr = (W * 0.06) * (1 + 0.25 * math.sin((tt - self.arrow_t) * 8))
                ap.ellipse(sx, sy, pr * 1.4, pr * 0.7, w=max(5, W * 0.008), color=col)
        return im


def build(s, portrait, work, log=None):
    """Make endcard.mp4 in `work`. Returns {"path", "words", "dur"} (words are relative to the card's start)."""
    W, H = (1080, 1920) if portrait else (1920, 1080)
    cfg = s.get("end_card") or {}
    seed = int(hashlib.md5(work.encode("utf-8", "replace")).hexdigest()[:6], 16)
    line = (cfg.get("text") or "").strip() or LINES[seed % len(LINES)]
    paper = str(s.get("drawn_bg") or "white").lower()
    paper = paper if paper in PAPER else "white"
    if log:
        log("info", "Adding the like & subscribe ending")
    mp3 = os.path.join(work, "endcard_voice.mp3")
    words = voice.narrate(s, line, mp3, portrait=portrait, log=log)
    vdur = max(0.8, media_duration(mp3))
    dur = max(3.8, vdur + 1.6)
    card = _Card(W, H, paper, seed, dur, vdur)
    from .stickman import _Actor
    cx, cy, fh = card.L["char"]
    beat = {"pose": "point_left", "expression": "happy", "expression2": "excited", "placement": "center", "character": True,
            "motion": "pop"}
    actor = _Actor(beat, fh, seed % 997, (cx, cy), 0, (W, H), words=words, t0=0.0, track=card.target)
    # audio: voice + pop on the click + ding as the bell rings + whoosh with the arrow
    wav = os.path.join(work, "endcard_audio.wav")
    ms = lambda x: str(int(max(0, x) * 1000))          # noqa: E731
    run([ffmpeg_path(), "-v", "error", "-y", "-i", mp3, "-i", sfx("pop"), "-i", sfx("ding"), "-i", sfx("whoosh"),
         "-filter_complex",
         f"[0:a]aformat=sample_rates=48000:channel_layouts=stereo[v];"
         f"[1:a]adelay={ms(card.click)}|{ms(card.click)},volume=0.8[p];"
         f"[2:a]adelay={ms(card.click + 0.12)}|{ms(card.click + 0.12)},volume=0.55[d];"
         f"[3:a]adelay={ms(card.arrow_t)}|{ms(card.arrow_t)},volume=0.6[w];"
         f"[v][p][d][w]amix=inputs=4:duration=longest:normalize=0,apad[a]",
         "-map", "[a]", "-t", f"{dur:.3f}", "-ar", "48000", "-ac", "2", wav])
    out = os.path.join(work, "endcard.mp4")
    cmd = [ffmpeg_path(), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE, **_popen_kwargs())
    try:
        nf = int(round(dur * FPS))
        for k in range(nf):
            t = k / FPS
            im = card.frame(t)
            actor.draw(im, t, dur)
            proc.stdin.write(im.tobytes())
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "replace")
        if proc.wait() != 0:
            raise RuntimeError(f"end card encode failed: {err[-400:]}")
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
        raise
    return {"path": out, "words": words, "dur": media_duration(out) or dur}


def enabled(s):
    return bool((s.get("end_card") or {}).get("enabled", True))
