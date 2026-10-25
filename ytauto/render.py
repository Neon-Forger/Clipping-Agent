"""Builds finished YouTube videos (16:9 long-form or 9:16 Shorts) from narration + footage."""
import os
import random
import shutil

from agent.tools import ffmpeg_path, fonts_dir, media_duration, run

from . import tts, visuals

FPS = 30


def _ass_time(t):
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def captions_ass(words, path, portrait, style="neon"):
    """Word-by-word captions: 1-3 words at a time, current word highlighted."""
    W, H = (1080, 1920) if portrait else (1920, 1080)
    size = 112 if portrait else 84
    y = int(H * (0.70 if portrait else 0.86))
    hi = "&H00FFE97F&" if style == "neon" else "&H0000E5FF&"   # cyan (BGR) for neon, yellow for clean
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Poppins,{size},&H00FFFFFF,&H00FFFFFF,&H00180904,&H80000000,-1,0,0,0,100,100,1,0,1,7,3,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev, cur = [], []
    groups = []
    for w in words:
        if cur and (len(cur) >= 3 or w["s"] - cur[-1]["e"] > 0.45 or cur[-1]["w"].endswith((".", "?", "!", ","))):
            groups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    for gi, g in enumerate(groups):
        g_end = groups[gi + 1][0]["s"] if gi + 1 < len(groups) else g[-1]["e"] + 0.3
        for i, w in enumerate(g):
            a = w["s"]
            b = g[i + 1]["s"] if i + 1 < len(g) else g_end
            parts = []
            for j, x in enumerate(g):
                txt = x["w"].upper().replace("{", "(").replace("}", ")")
                parts.append(("{\\c" + hi + "}" if j == i else "{\\c&H00FFFFFF&}") + txt)
            pop = "\\fscx92\\fscy92\\t(0,70,\\fscx100\\fscy100)" if i == 0 else ""
            ev.append(f"Dialogue: 0,{_ass_time(a)},{_ass_time(b)},Cap,,0,0,0,,{{\\pos({W // 2},{y}){pop}}}{' '.join(parts)}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(hdr + "\n".join(ev) + "\n")


def _fit_clip(src, dur, out, portrait, still=False, zoom_seed=0, start=0.0):
    """Makes a `dur`-second clip from footage (looped if short) or a still image (slow zoom)."""
    W, H = (1080, 1920) if portrait else (1920, 1080)
    if still:
        z = "1+0.0009*on" if zoom_seed % 2 == 0 else "1.12-0.0009*on"
        frames = int(dur * FPS) + 2
        vf = (f"scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,crop={W * 2}:{H * 2},"
              f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},setsar=1,format=yuv420p")
        cmd = [ffmpeg_path(), "-v", "error", "-y", "-loop", "1", "-i", src, "-t", f"{dur:.3f}", "-vf", vf]
    else:
        vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1"
        cmd = [ffmpeg_path(), "-v", "error", "-y", "-stream_loop", "-1", "-ss", f"{start:.2f}", "-i", src, "-t", f"{dur:.3f}", "-an", "-vf", vf]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", out]
    run(cmd, timeout=1800)
    return out


def _music(folder):
    if not folder or not os.path.isdir(folder):
        return None
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith((".mp3", ".wav", ".m4a", ".ogg"))]
    return random.choice(files) if files else None


def build_original(s, segments, portrait, work, out_path, log=None):
    """segments: [{"text", "visual"}]. Narrates, finds footage per segment, adds captions, renders."""
    os.makedirs(work, exist_ok=True)
    fdir = os.path.join(work, "fonts")
    if not os.path.isdir(fdir):
        shutil.copytree(fonts_dir(), fdir)
    used = set()
    parts, all_words, t0, chapters = [], [], 0.0, []
    stock = os.path.join(os.path.dirname(work), "_stock")
    from .photos import PhotoSource, pixabay_video
    photos = PhotoSource(s, os.path.join(os.path.dirname(work), "_photos"), None)
    warned = False
    for i, seg in enumerate(segments):
        if log:
            log("info", f"Voice + footage {i + 1}/{len(segments)}")
        mp3 = os.path.join(work, f"v{i:02d}.mp3")
        words = tts.speak(seg["text"], s["voice"], s.get("voice_rate", "+0%"), mp3)
        dur = max(media_duration(mp3), 0.5) + 0.15
        clip = os.path.join(work, f"c{i:02d}.mp4")
        q = seg.get("visual") or s["genre"]
        src = visuals.pexels_video(q, s.get("pexels_api_key"), portrait, stock, used) \
            or pixabay_video(q, s.get("pixabay_api_key"), portrait, stock, used)
        if src:
            _fit_clip(src, dur, clip, portrait)
        else:
            img = visuals.ai_image(s["ai"], f"Cinematic, moody, high-detail scene: {seg.get('visual') or s['genre']}",
                                   os.path.join(work, f"i{i:02d}.png"), "9:16" if portrait else "16:9") \
                if s.get("thumbnails", {}).get("ai_images") else None
            if not img:
                ph = photos.get(seg.get("visual") or s["genre"], portrait)
                if ph is not None:
                    img = os.path.join(work, f"p{i:02d}.jpg")
                    ph.save(img, "JPEG", quality=92)
            if img:
                _fit_clip(img, dur, clip, portrait, still=True, zoom_seed=i)
            else:
                if log and not warned:
                    warned = True
                    log("warn", "No footage or photo found for some parts, so they use the neon background. "
                                + photos.status_text() + " A free Pixabay key (YouTube → SETTINGS) adds stock video and photos.")
                loop = os.path.join(stock, f"neon_loop_{'p' if portrait else 'l'}.mp4")
                if not os.path.exists(loop):
                    os.makedirs(stock, exist_ok=True)
                    visuals.neon_background(loop, 20, portrait, seed=3)
                _fit_clip(loop, dur, clip, portrait, start=(i * 7.3) % 15)
        # pair this segment's picture with its voice
        seg_mp4 = os.path.join(work, f"s{i:02d}.mp4")
        run([ffmpeg_path(), "-v", "error", "-y", "-i", clip, "-i", mp3, "-map", "0:v", "-map", "1:a",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-t", f"{dur:.3f}", seg_mp4], timeout=600)
        parts.append(seg_mp4)
        all_words += [{"s": w["s"] + t0, "e": w["e"] + t0, "w": w["w"]} for w in words]
        chapters.append({"start": round(t0, 2), "chapter": (seg.get("chapter") or "").strip()})
        t0 += media_duration(seg_mp4) or dur
    with open(os.path.join(work, "segments.json"), "w", encoding="utf-8") as f:
        import json
        json.dump(chapters, f)
    _finish(s, parts, all_words, portrait, work, out_path)
    return out_path, photos.credits


def _finish(s, parts, words, portrait, work, out_path):
    lst = os.path.join(work, "list.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for p in parts:
            f.write(f"file '{os.path.basename(p)}'\n")
    joined = os.path.join(work, "joined.mp4")
    run([ffmpeg_path(), "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "joined.mp4"],
        cwd=work, timeout=1800)
    total = media_duration(joined)
    vf = "null"
    if s.get("captions", True) and words:
        captions_ass(words, os.path.join(work, "caps.ass"), portrait, s.get("caption_style", "neon"))
        vf = "ass=caps.ass:fontsdir=fonts"
    music = _music(s.get("music_folder"))
    cmd = [ffmpeg_path(), "-v", "error", "-y", "-i", "joined.mp4"]
    if music:
        cmd += ["-stream_loop", "-1", "-i", music]
        af = (f"[0:a]loudnorm=I=-14:TP=-1.5:LRA=11[v];[1:a]volume={s.get('music_volume', 0.12)},"
              f"afade=t=out:st={max(total - 3, 0):.2f}:d=3[m];[v][m]amix=inputs=2:duration=first:normalize=0[a]")
    else:
        af = "[0:a]loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    cmd += ["-filter_complex", f"[0:v]{vf}[v];{af}", "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", os.path.abspath(out_path)]
    run(cmd, cwd=work, timeout=3600)
    return out_path


def build_repurposed_long(s, src_video, plan, work, out_path, log=None):
    """Long-form highlights video: narrated intro, then each excerpt with a narrated bridge before it, then outro.
    Bridges play over a blurred still from the next excerpt."""
    os.makedirs(work, exist_ok=True)
    fdir = os.path.join(work, "fonts")
    if not os.path.isdir(fdir):
        shutil.copytree(fonts_dir(), fdir)
    W, H = 1920, 1080
    parts, words_all, t0 = [], [], 0.0

    def narrated(text, still_at, idx):
        nonlocal t0
        mp3 = os.path.join(work, f"n{idx:02d}.mp3")
        words = tts.speak(text, s["voice"], s.get("voice_rate", "+0%"), mp3)
        dur = max(media_duration(mp3), 0.5) + 0.2
        still = os.path.join(work, f"st{idx:02d}.png")
        run([ffmpeg_path(), "-v", "error", "-y", "-ss", f"{max(still_at, 0):.2f}", "-i", src_video, "-frames:v", "1", still])
        out = os.path.join(work, f"p{idx:02d}.mp4")
        run([ffmpeg_path(), "-v", "error", "-y", "-loop", "1", "-i", still, "-i", mp3, "-t", f"{dur:.3f}",
             "-filter_complex", f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=20:2,"
                                f"eq=brightness=-0.25,fps={FPS},setsar=1,format=yuv420p[v]",
             "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", out], timeout=600)
        parts.append(out)
        words_all.extend({"s": w["s"] + t0, "e": w["e"] + t0, "w": w["w"]} for w in words)
        t0 += media_duration(out) or dur

    def excerpt(a, b, idx):
        nonlocal t0
        out = os.path.join(work, f"x{idx:02d}.mp4")
        run([ffmpeg_path(), "-v", "error", "-y", "-ss", f"{a:.2f}", "-t", f"{b - a:.2f}", "-i", src_video,
             "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps={FPS},setsar=1,format=yuv420p",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", out],
            timeout=1800)
        parts.append(out)
        t0 += media_duration(out) or (b - a)

    items = plan.get("parts") or []
    if not items:
        raise RuntimeError("The AI didn't choose any excerpts")
    narrated(plan.get("intro") or plan.get("title", ""), items[0]["start"], 0)
    for i, p in enumerate(items, 1):
        if log:
            log("info", f"Excerpt {i}/{len(items)}")
        if p.get("bridge"):
            narrated(p["bridge"], p["start"], i * 2)
        excerpt(float(p["start"]), float(p["end"]), i * 2 + 1)
    if plan.get("outro"):
        narrated(plan["outro"], items[-1]["end"] - 1, 99)
    # only the narration gets captions (excerpts keep their own audio)
    return _finish(s, parts, words_all, False, work, out_path)
