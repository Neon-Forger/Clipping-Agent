"""Footage and images for original videos: Pexels stock video (free, licensed for reuse),
AI-generated images (Gemini image models), or a generated neon motion background as a fallback."""
import base64
import hashlib
import os
import random

import requests

from agent.ai import GEMINI_BASE
from agent.tools import ffmpeg_path, run


def _cache_path(folder, key, ext):
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, hashlib.md5(key.encode()).hexdigest()[:16] + ext)


def pexels_video(query, api_key, portrait, folder, used=None):
    """Downloads a fitting stock clip. Returns a file path or None."""
    if not api_key:
        return None
    try:
        r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": api_key}, timeout=30,
                         params={"query": query, "orientation": "portrait" if portrait else "landscape",
                                 "per_page": 12, "size": "medium"})
        r.raise_for_status()
        vids = r.json().get("videos", [])
    except Exception:
        return None
    random.shuffle(vids)
    used = used if used is not None else set()
    for v in vids:
        if v.get("id") in used:
            continue
        files = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("width") and f.get("height")]
        if not files:
            continue
        target = 1080 if portrait else 1920

        def fit(f):
            side = f["height"] if portrait else f["width"]
            return (abs(side - target), f["width"] * f["height"])
        best = min(files, key=fit)
        path = _cache_path(folder, f"pexels-{v['id']}-{best['width']}", ".mp4")
        if not os.path.exists(path):
            try:
                with requests.get(best["link"], stream=True, timeout=120) as resp:
                    resp.raise_for_status()
                    with open(path + ".part", "wb") as fh:
                        for chunk in resp.iter_content(1 << 20):
                            fh.write(chunk)
                os.replace(path + ".part", path)
            except Exception:
                continue
        used.add(v.get("id"))
        return path
    return None


def pick_image_model(key):
    r = requests.get(f"{GEMINI_BASE}/models?pageSize=200", headers={"x-goog-api-key": key}, timeout=30)
    r.raise_for_status()
    names = [m["name"].split("/")[-1] for m in r.json().get("models", [])
             if "generateContent" in (m.get("supportedGenerationMethods") or []) and "image" in m.get("name", "")
             and "gemini" in m.get("name", "")]
    if not names:
        return None
    return sorted(names, key=lambda n: ("preview" not in n, n))[-1]


_img_model = {}


def ai_image(cfg_ai, prompt, out_path, aspect="16:9"):
    """Makes an image with a Gemini image model. Returns the path, or None if not available."""
    key = cfg_ai.get("gemini_api_key")
    if not key:
        return None
    try:
        if key not in _img_model:
            _img_model[key] = pick_image_model(key)
        model = _img_model[key]
        if not model:
            return None
        body = {"contents": [{"role": "user", "parts": [{"text": f"{prompt}. Aspect ratio {aspect}. No text, no letters, no watermark."}]}],
                "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}}
        r = requests.post(f"{GEMINI_BASE}/models/{model}:generateContent", json=body,
                          headers={"x-goog-api-key": key}, timeout=180)
        r.raise_for_status()
        for cand in r.json().get("candidates", []):
            for part in cand.get("content", {}).get("parts", []):
                data = (part.get("inlineData") or part.get("inline_data") or {}).get("data")
                if data:
                    with open(out_path, "wb") as f:
                        f.write(base64.b64decode(data))
                    return out_path
    except Exception:
        return None
    return None


def neon_background(out_path, seconds, portrait, seed=0):
    """A moving neon gradient used when no footage is available."""
    w, h = (1080, 1920) if portrait else (1920, 1080)
    sw, sh = w // 4, h // 4
    hue = (seed * 23) % 60 - 30  # small hue shifts so backgrounds vary but stay neon
    # dark navy base with drifting cyan and magenta glows (Neon look)
    cy = f"pow(max(0,sin(2*PI*(X/{sw}*0.8+T/14))*sin(2*PI*(Y/{sh}*0.6+T/17))),2)"
    mg = f"pow(max(0,cos(2*PI*(X/{sw}*0.6-T/19))*sin(2*PI*(Y/{sh}*0.9+T/23))),2)"
    vf = (f"geq=r='clip(4+200*{mg},0,255)':g='clip(9+150*{cy}+20*{mg},0,255)':b='clip(21+230*{cy}+150*{mg},0,255)',"
          f"hue=h={hue - 180 if hue > 180 else hue}:s=1,gblur=sigma=6,scale={w}:{h},noise=alls=4:allf=t,setsar=1,format=yuv420p")
    run([ffmpeg_path(), "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s={sw}x{sh}:r=30:d={seconds:.2f}",
         "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", out_path], timeout=900)
    return out_path
