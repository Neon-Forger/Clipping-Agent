"""Turns a moment of a long video into a vertical TikTok clip:
blurred background, zooms, word-by-word captions with highlighted words,
a hook title, and (in "dramatic" style) flashes, shake and impact sounds
on the punchline."""
import os
import re
import shutil

from .tools import ffmpeg_path, fonts_dir, run

YELLOW = "&H0000E5FF&"
RED = "&H003030FF&"
WHITE = "&H00FFFFFF&"

SWEARS = {
    "fuck": "f*ck", "fucking": "f*cking", "fucked": "f*cked", "fucker": "f*cker", "motherfucker": "motherf*cker",
    "shit": "sh*t", "bullshit": "bullsh*t", "bitch": "b*tch", "cunt": "c*nt", "dick": "d*ck", "pussy": "p*ssy",
    "asshole": "a**hole", "whore": "wh*re", "slut": "sl*t",
}


def _censor(word):
    m = re.match(r"^(\W*)([\w']+)(\W*)$", word)
    if not m:
        return word
    pre, core, post = m.groups()
    rep = SWEARS.get(core.lower())
    if not rep:
        return word
    if core.isupper():
        rep = rep.upper()
    elif core[0].isupper():
        rep = rep[0].upper() + rep[1:]
    return pre + rep + post


def _clean(w):
    return re.sub(r"[^\w']", "", w).lower()


def _ass_time(t):
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def _ass_escape(s):
    return s.replace("\\", "").replace("{", "(").replace("}", ")")


def _wrap(text, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


def chunk_words(words, max_words=3, max_chars=18, gap=0.4):
    chunks, cur = [], []
    for i, w in enumerate(words):
        if cur:
            prev = cur[-1]
            text = " ".join(x["w"] for x in cur)
            if (len(cur) >= max_words or len(text) + len(w["w"]) > max_chars
                    or w["s"] - prev["e"] > gap or prev["w"].endswith((".", "?", "!", ","))):
                chunks.append(cur)
                cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)
    return chunks


def build_ass(clip, words, cfg, dramatic, path):
    dur = clip["end"] - clip["start"]
    P = clip["punch"] - clip["start"]
    emph = {_clean(w) for w in clip.get("emphasis") or []}
    censor = cfg.get("censor_swears", True)
    cap_size = cfg.get("caption_font_size", 82)
    hook_size = cfg.get("hook_font_size", 80)

    rel = [{"s": w["s"] - clip["start"], "e": w["e"] - clip["start"], "w": w["w"]} for w in words
           if w["e"] > clip["start"] and w["s"] < clip["end"]]
    for w in rel:
        if censor:
            w["w"] = _censor(w["w"])

    big_win = (P - 0.05, P + 1.9) if dramatic else (None, None)
    big_words = []
    if dramatic:
        for w in rel:
            if w["s"] < P - 0.25:
                continue
            if big_words and (w["s"] - big_words[-1]["e"] > 0.35 or w["s"] > P + 1.5):
                break
            big_words.append(w)
            if len(big_words) >= 4 or w["w"].endswith((".", "?", "!")):
                break

    ev = []
    chunks = chunk_words(rel)
    for i, ch in enumerate(chunks):
        a = ch[0]["s"]
        b = chunks[i + 1][0]["s"] if i + 1 < len(chunks) else min(ch[-1]["e"] + 0.4, dur)
        b = min(b, ch[-1]["e"] + 0.9, a + 2.5)
        if big_words and any(w in big_words for w in ch):
            continue
        y = 1440
        if dramatic and big_words and a < big_win[1] and b > big_win[0]:
            y = 1650
        parts = []
        for w in ch:
            col = YELLOW if (_clean(w["w"]) in emph or (w["w"].isupper() and len(_clean(w["w"])) > 1)) else WHITE
            parts.append("{\\c" + col + "}" + _ass_escape(w["w"].upper()))
        pop = "\\fscx75\\fscy75\\t(0,80,\\fscx108\\fscy108)\\t(80,140,\\fscx100\\fscy100)"
        ev.append(f"Dialogue: 0,{_ass_time(a)},{_ass_time(b)},Cap,,0,0,0,,{{\\pos(540,{y}){pop}}}{' '.join(parts)}")

    if big_words:
        first = _ass_escape(big_words[0]["w"].upper())
        rest = _ass_escape(" ".join(w["w"] for w in big_words[1:]).upper())
        t1 = big_words[1]["s"] if len(big_words) > 1 else P + 0.5
        size = lambda txt: 128 if len(txt) <= 13 else (104 if len(txt) <= 20 else 86)
        ev.append(f"Dialogue: 2,{_ass_time(P)},{_ass_time(t1 if rest else big_win[1])},Big,,0,0,0,,"
                  f"{{\\pos(540,1430)\\fs{size(first)}\\fscx220\\fscy220\\t(0,120,\\fscx100\\fscy100)\\frz-5}}{first}")
        if rest:
            lines = _wrap(rest, 14)
            txt = "\\N".join(lines)
            fs = size(max(lines, key=len))
            ev.append(f"Dialogue: 2,{_ass_time(t1)},{_ass_time(big_win[1])},Big,,0,0,0,,"
                      f"{{\\pos(540,1430)\\fs{fs}\\fscx240\\fscy240\\t(0,110,\\fscx100\\fscy100)\\frz4\\c{RED}}}{txt}")
            for k, (dx, dy) in enumerate([(-14, 6), (12, -8), (-9, 5), (8, -4), (-5, 3)]):
                t = t1 + k * 0.06
                ev.append(f"Dialogue: 3,{_ass_time(t)},{_ass_time(t + 0.06)},Big,,0,0,0,,"
                          f"{{\\pos({540 + dx},{1430 + dy})\\fs{fs}\\frz4\\c{RED}}}{txt}")
        clip["_t1"] = t1

    title = _ass_escape(clip.get("title") or "")
    if title:
        lines = _wrap(title, 26)[:3]
        colored = []
        for ln in lines:
            colored.append(" ".join(("{\\c" + RED + "}" + w + "{\\c&H00000000&}") if (w.isupper() and len(_clean(w)) > 1) else w
                                    for w in ln.split()))
        txt = "\\N".join(colored)
        pop = "\\fscx40\\fscy40\\t(0,180,\\fscx106\\fscy106)\\t(180,260,\\fscx100\\fscy100)" if dramatic else ""
        ev.append(f"Dialogue: 1,{_ass_time(0)},{_ass_time(dur)},Hook,,0,0,0,,{{\\pos(540,380){pop}}}{txt}")

    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Poppins,{cap_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,8,4,5,40,40,0,1
Style: Big,Poppins,128,&H00FFFFFF,&H00FFFFFF,&H00000000,&HA0000000,-1,0,0,0,100,100,2,0,1,11,6,5,30,30,0,1
Style: Hook,Poppins,{hook_size},&H00000000,&H00000000,&H00FFFFFF,&H00FFFFFF,-1,0,0,0,100,100,0,0,3,20,0,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(hdr + "\n".join(ev) + "\n")
    return bool(big_words)


def render_clip(src, clip, words, cfg, out_path, work_dir):
    """Render one clip. `clip` has start, end, punch (seconds in the source video), title, emphasis."""
    os.makedirs(work_dir, exist_ok=True)
    fdir = os.path.join(work_dir, "fonts")
    if not os.path.isdir(fdir):
        shutil.copytree(fonts_dir(), fdir)
    dramatic = (cfg.get("style", "dramatic") == "dramatic")
    dur = round(clip["end"] - clip["start"], 2)
    has_big = build_ass(clip, words, cfg, dramatic, os.path.join(work_dir, "subs.ass"))
    P = round(clip["punch"] - clip["start"], 2)
    T1 = round(clip.get("_t1", P + 0.5), 2)
    fy = cfg.get("zoom_focus_y", 0.44)

    if dramatic:
        z = (f"if(lt(it,{P}),1+0.12*it/{max(P, 0.1)},"
             f"if(lt(it,{P}+0.9),1.40-0.15*(it-{P})/0.9,"
             f"if(lt(it,{P}+4),1.25,max(1.08,1.25-0.05*(it-{P}-4)))))")
        sx = f"if(between(it,{P},{P}+0.5),18*sin(it*95),0)"
        sy = f"if(between(it,{P},{P}+0.5),12*cos(it*120),0)"
    else:
        z = f"1+0.08*it/{max(dur, 1)}"
        sx = sy = "0"

    v = ("[0:v]fps=30,split[x][y];"
         "[x]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,boxblur=10:2,eq=brightness=-0.15,scale=1080:1920[bg];"
         f"[y]scale=1620:1080:force_original_aspect_ratio=increase,crop=1620:1080,zoompan=z='{z}':x='iw/2-(iw/zoom/2)+{sx}':y='ih*{fy}-(ih/zoom/2)+{sy}':d=1:s=1080x720:fps=30[fg];"
         "[bg][fg]overlay=0:560[o0];[o0]")
    boxes = []
    if dramatic:
        boxes += ["drawbox=x=0:y=0:w=iw:h=ih:color=white@0.5:t=fill:enable='between(t,0,0.06)'"]
        if has_big:
            boxes += [f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.85:t=fill:enable='between(t,{P},{P}+0.07)'",
                      f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.45:t=fill:enable='between(t,{P}+0.07,{P}+0.14)'",
                      f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.6:t=fill:enable='between(t,{T1},{T1}+0.06)'",
                      f"drawbox=x=0:y=1280:w=iw:h=8:color=0xE52E2E@1:t=fill:enable='gte(t,{P})'",
                      f"drawbox=x=0:y=552:w=iw:h=8:color=0xE52E2E@1:t=fill:enable='gte(t,{P})'"]
    if not boxes:
        boxes = ["null"]
    v += ",".join(boxes) + "[o1];"
    if cfg.get("progress_bar", True):
        v += f"color=c=0xFFD400:s=1080x14:r=30[bar];[o1][bar]overlay=x='-W+W*t/{dur}':y=1906:shortest=1[o2];[o2]"
    else:
        v += "[o1]"
    v += "ass=subs.ass:fontsdir=fonts[v];"

    a = "[0:a]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[va];"
    if dramatic and has_big and cfg.get("sound_effects", True):
        d0 = int(max(P - 0.8, 0) * 1000)
        a += (f"anoisesrc=d=0.8:c=pink:a=0.5:r=48000,highpass=f=800,lowpass=f=6000,afade=t=in:d=0.7,afade=t=out:st=0.7:d=0.1,volume=0.35,adelay={d0}|{d0}[wh];"
              f"aevalsrc='0.9*sin(2*PI*(55-35*t)*t)*exp(-3.5*t)':d=1.6:s=48000,adelay={int(P * 1000)}|{int(P * 1000)}[bm];"
              f"aevalsrc='0.6*sin(2*PI*(70-40*t)*t)*exp(-5*t)':d=0.8:s=48000,volume=0.7,adelay={int(T1 * 1000)}|{int(T1 * 1000)}[bm2];"
              "[va][wh][bm][bm2]amix=inputs=4:duration=first:normalize=0,alimiter=limit=0.95[a]")
    else:
        a += "[va]anull[a]"

    cmd = [ffmpeg_path(), "-v", "error", "-y", "-ss", str(clip["start"]), "-t", str(dur), "-i", os.path.abspath(src),
           "-filter_complex", v + a, "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", str(cfg.get("video_crf", 19)), "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
    max_mb = cfg.get("max_upload_mb") or 0
    if max_mb:
        kbps = int((max_mb * 8 * 1000 * 0.93) / max(dur, 1) - 192)
        cmd += ["-maxrate", f"{kbps}k", "-bufsize", f"{kbps * 2}k"]
    cmd.append(os.path.abspath(out_path))
    run(cmd, cwd=work_dir, timeout=1800)
    return out_path
