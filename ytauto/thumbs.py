"""Thumbnails (1280x720), channel profile picture (800x800) and banner (2560x1440) in a neon style."""
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageStat

from agent.tools import ffmpeg_path, fonts_dir, run

CYAN = (127, 233, 255)
BLUE = (0, 180, 255)
PINK = (255, 43, 214)
NAVY = (4, 9, 21)


def _font(size, kind="display"):
    name = {"display": "Orbitron-ExtraBold.ttf", "bold": "Poppins-Bold.ttf"}.get(kind, "Poppins-Bold.ttf")
    try:
        return ImageFont.truetype(os.path.join(fonts_dir(), name), size)
    except Exception:
        return ImageFont.load_default()


def _hex(c):
    if isinstance(c, str) and c.startswith("#") and len(c) == 7:
        return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
    return c


def best_frame(video, out_png, at=(0.25, 0.45, 0.65)):
    """Grabs a few frames and keeps the sharpest, brightest one."""
    from agent.tools import media_duration
    dur = max(media_duration(video), 1)
    best, best_score = None, -1
    for i, f in enumerate(at):
        p = out_png + f".{i}.png"
        try:
            run([ffmpeg_path(), "-v", "error", "-y", "-ss", f"{dur * f:.2f}", "-i", video, "-frames:v", "1", p])
            im = Image.open(p).convert("L")
            edges = im.filter(ImageFilter.FIND_EDGES)
            sc = ImageStat.Stat(edges).var[0] + ImageStat.Stat(im).mean[0] * 2
            if sc > best_score:
                best, best_score = p, sc
        except Exception:
            continue
    if not best:
        return None
    os.replace(best, out_png)
    return out_png


def _glow_text(base, xy, text, font, fill, glow, stroke=10, anchor="la"):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text(xy, text, font=font, fill=glow + (255,), stroke_width=stroke + 8, stroke_fill=glow + (255,), anchor=anchor)
    layer = layer.filter(ImageFilter.GaussianBlur(18))
    base.alpha_composite(layer)
    d = ImageDraw.Draw(base)
    d.text(xy, text, font=font, fill=fill + (255,), stroke_width=stroke, stroke_fill=(0, 0, 0, 255), anchor=anchor)


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def thumbnail(background, text, out_path, color="#7FE9FF", accent="#FF2BD6"):
    """background: image path (frame or AI image) or None. text: 2-4 words."""
    W, H = 1280, 720
    color, accent = _hex(color), _hex(accent)
    if background and os.path.exists(background):
        bg = ImageOps.fit(Image.open(background).convert("RGB"), (W, H), Image.LANCZOS)
    else:
        bg = Image.new("RGB", (W, H), NAVY)
    im = bg.convert("RGBA")
    # darken the left side for the text and add a neon vignette
    shade = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(shade)
    for x in range(W):
        sd.line([(x, 0), (x, H)], fill=int(190 * max(0, 1 - x / (W * 0.75))))
    im = Image.composite(Image.new("RGBA", (W, H), NAVY + (255,)), im, shade)
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(frame)
    fd.rectangle([10, 10, W - 11, H - 11], outline=accent + (255,), width=10)
    frame = frame.filter(ImageFilter.GaussianBlur(6))
    im.alpha_composite(frame)
    ImageDraw.Draw(im).rectangle([14, 14, W - 15, H - 15], outline=color + (255,), width=4)

    text = (text or "").upper().strip()
    d = ImageDraw.Draw(im)
    size = 150
    while size > 60:
        f = _font(size, "bold")
        lines = _wrap(d, text, f, W * 0.62)
        if len(lines) <= 3 and all(d.textlength(l, font=f) <= W * 0.66 for l in lines):
            break
        size -= 8
    f = _font(size, "bold")
    lines = _wrap(d, text, f, W * 0.62)
    total = len(lines) * size * 1.05
    y = (H - total) / 2
    for i, ln in enumerate(lines):
        fill = accent if (i == len(lines) - 1 and len(lines) > 1) else (255, 255, 255)
        _glow_text(im, (60, y), ln, f, fill, color if fill == (255, 255, 255) else accent, stroke=9)
        y += size * 1.05
    im.convert("RGB").save(out_path, "JPEG", quality=92)
    return out_path


def avatar(name, out_path, art=None):
    S = 800
    im = Image.new("RGBA", (S, S), NAVY + (255,))
    if art and os.path.exists(art):
        a = ImageOps.fit(Image.open(art).convert("RGBA"), (S, S), Image.LANCZOS)
        im.alpha_composite(a)
        im.alpha_composite(Image.new("RGBA", (S, S), NAVY + (120,)))
    ring = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    rd.ellipse([40, 40, S - 40, S - 40], outline=PINK + (255,), width=26)
    ring = ring.filter(ImageFilter.GaussianBlur(10))
    im.alpha_composite(ring)
    ImageDraw.Draw(im).ellipse([52, 52, S - 52, S - 52], outline=CYAN + (255,), width=10)
    initials = "".join(w[0] for w in (name or "N C").split()[:2]).upper() or "NC"
    f = _font(300 if len(initials) == 1 else 250, "display")
    _glow_text(im, (S / 2, S / 2), initials, f, (255, 255, 255), BLUE, stroke=6, anchor="mm")
    im.convert("RGB").save(out_path, "PNG")
    return out_path


def banner(name, tagline, out_path, art=None):
    """2560x1440; everything important stays inside YouTube's 1546x423 safe area in the middle."""
    W, H = 2560, 1440
    im = Image.new("RGBA", (W, H), NAVY + (255,))
    if art and os.path.exists(art):
        a = ImageOps.fit(Image.open(art).convert("RGBA"), (W, H), Image.LANCZOS)
        im.alpha_composite(a)
        im.alpha_composite(Image.new("RGBA", (W, H), NAVY + (150,)))
    # synthwave grid
    grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid)
    horizon = 860
    for i in range(-30, 31):
        gd.line([(W / 2 + i * 40, horizon), (W / 2 + i * 260, H)], fill=BLUE + (110,), width=3)
    y, step = horizon, 12
    while y < H:
        gd.line([(0, y), (W, y)], fill=BLUE + (110,), width=3)
        step *= 1.25
        y += step
    im.alpha_composite(grid)
    f = _font(150, "display")
    d = ImageDraw.Draw(im)
    while d.textlength(name.upper(), font=f) > 1450 and f.size > 60:
        f = _font(f.size - 10, "display")
    _glow_text(im, (W / 2, H / 2 - 40), (name or "NEONCLIP").upper(), f, (255, 255, 255), PINK, stroke=6, anchor="mm")
    if tagline:
        t = _font(56, "bold")
        _glow_text(im, (W / 2, H / 2 + 95), tagline, t, CYAN, BLUE, stroke=3, anchor="mm")
    im.convert("RGB").save(out_path, "PNG")
    return out_path
