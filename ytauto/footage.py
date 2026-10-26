"""Moving backgrounds (stock video + animation) searched across free-to-use libraries on the web.

Searched for each topic, in this order (a site that keeps failing is skipped for the rest of the video):
  Pexels video (free key) → Pixabay video (free key) → Wikimedia Commons video (no key, free licenses)
  → Internet Archive (no key; public-domain + Creative Commons films, cartoons and animation, e.g. the Prelinger archive)
  → NASA video library (no key, public domain; only for space/science-looking topics)
Only licenses that allow commercial use and editing are used (no NC / ND), so it's safe on a monetized channel.
Clips are trimmed straight from the web (only the seconds needed are downloaded) and credited in the description.

Websites in general (Google results, GIPHY, TikTok, random pages) are NOT used: almost everything there is copyrighted,
and using it gets videos claimed or the channel struck."""
import hashlib
import math
import os
import random
import re
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor

from agent.tools import ffmpeg_path

from .photos import UA, _get, _short, _Skip

SPACEY = re.compile(r"\b(space|planet|galax|star|nasa|moon|mars|rocket|orbit|astronaut|earth from|nebula|sun|solar|"
                    r"comet|asteroid|satellite|universe|cosmos|black hole|launch|telescope|aurora|hurricane|storm)", re.I)
BAD_LICENSE = re.compile(r"(-nc|/nc|by-nc|noncommercial|-nd|/nd|by-nd|noderiv)", re.I)
FPS = 30


def _ok_license(lic):
    return not BAD_LICENSE.search(lic or "")


def _popen_kwargs():
    if os.name == "nt":
        return {"creationflags": 0x08000000}   # no console window
    return {}


class FootageSource:
    MAX_SEARCHES = 12      # per video
    MAX_CLIPS = 12         # clips downloaded per video; each clip is reused for up to 3 beats at different moments
    CLIP_SECONDS = 6.5

    def __init__(self, s, folder, log=None, size=(1080, 1920)):
        self.s, self.folder, self.log = s, folder, log
        self.W, self.H = size
        os.makedirs(folder, exist_ok=True)
        self.lock = threading.Lock()
        self.cands = {}        # query -> candidate list
        self.slices = {}       # query -> [(clip_path, offset)]
        self.all_clips = []
        self.used = set()          # source keys already used (a re-edit pre-fills this to get different footage)
        self.key_of = {}           # clip path -> source key
        self.credit_of = {}        # clip path -> credit line
        self.credits = []
        self.searches = 0
        self.clips = 0
        self.fail, self.why, self.got = {}, {}, {}
        self.reuse_i = 0

    # ------------------------------------------------------------------ public
    def prefetch(self, queries, portrait):
        """queries: list in beat order (repeats = more beats need that query). Fetches clips in parallel."""
        need = {}
        for q in queries:
            q = self._norm(q)
            need[q] = need.get(q, 0) + 1
        jobs = [(q, max(1, math.ceil(n / 3))) for q, n in need.items()]
        if not jobs:
            return
        with ThreadPoolExecutor(max_workers=4) as ex:
            list(ex.map(lambda j: self._fill(j[0], j[1], portrait), jobs))
        if self.log:
            self.log("info", f"Stock video: {len(self.all_clips)} clip(s) from {self.summary()}")

    def get(self, query, portrait=True):
        """Returns (clip_path, start_seconds) for a beat, or None if no clip at all could be found."""
        q = self._norm(query)
        with self.lock:
            sl = self.slices.get(q)
        if not sl and q not in self.cands:
            self._fill(q, 1, portrait)          # wasn't prefetched (e.g. a fallback for a missing photo)
        with self.lock:
            sl = self.slices.get(q) or self._closest(q)
            if sl:
                return sl.pop(0)
            if self.all_clips:                   # reuse something rather than show a black screen
                self.reuse_i += 1
                p = self.all_clips[self.reuse_i % len(self.all_clips)]
                return p, (self.reuse_i * 1.7) % 4.0
        return None

    def summary(self):
        return ", ".join(f"{n} from {k}" for k, n in self.got.items()) or "none"

    def status_text(self):
        parts = [f"{k}: {v}" for k, v in self.why.items()]
        return ("Video sites: " + "; ".join(parts)) if parts else "No video site had matching clips."

    # ---------------------------------------------------------------- internals
    def _norm(self, q):
        return re.sub(r"\s+", " ", (q or self.s.get("genre") or "city")).strip().lower()[:60]

    def _closest(self, q):
        words = set(q.split())
        ranked = sorted(((k, v) for k, v in self.slices.items() if v), key=lambda kv: -len(words & set(kv[0].split())))
        return ranked[0][1] if ranked and len(words & set(ranked[0][0].split())) > 0 else None

    def _fill(self, q, n_clips, portrait):
        with self.lock:
            if q in self.cands or self.searches >= self.MAX_SEARCHES:
                return
            self.searches += 1
            self.cands[q] = []
        cands = self._search(q, portrait)
        if not cands and len(q.split()) > 2:            # broaden: first two words
            cands = self._search(" ".join(q.split()[:2]), portrait)
        with self.lock:
            self.cands[q] = cands
        got = 0
        for c in cands:
            if got >= n_clips:
                break
            with self.lock:
                if self.clips >= self.MAX_CLIPS or c["key"] in self.used:
                    if self.clips >= self.MAX_CLIPS:
                        break
                    continue
                self.used.add(c["key"])
                self.clips += 1
            path = self._trim(c)
            if not path:
                with self.lock:
                    self.clips -= 1
                continue
            got += 1
            with self.lock:
                self.all_clips.append(path)
                self.key_of[path] = c["key"]
                if c.get("credit"):
                    self.credit_of[path] = c["credit"]
                self.slices.setdefault(q, []).extend([(path, 0.0), (path, 2.1), (path, 4.2)])
                self.got[c["provider"]] = self.got.get(c["provider"], 0) + 1
                if c.get("credit"):
                    self.credits.append(c["credit"])

    def _trim(self, c):
        """Downloads only CLIP_SECONDS of the video, scaled/cropped to the frame size, no audio."""
        start = c.get("start") or 0.0
        dur = c.get("duration") or 0
        if dur and dur > self.CLIP_SECONDS + 2 and not c.get("start"):
            start = random.uniform(min(3.0, dur * 0.1), max(min(3.0, dur * 0.1), dur - self.CLIP_SECONDS - 1))
        name = hashlib.md5(f"{c['url']}|{start:.1f}|{self.W}x{self.H}".encode()).hexdigest()[:16] + ".mp4"
        out = os.path.join(self.folder, name)
        if os.path.exists(out) and os.path.getsize(out) > 10000:
            return out
        vf = (f"scale={self.W}:{self.H}:force_original_aspect_ratio=increase,crop={self.W}:{self.H},fps={FPS},format=yuv420p")
        cmd = [ffmpeg_path(), "-v", "error", "-y", "-user_agent", UA, "-rw_timeout", "30000000",
               "-ss", f"{start:.2f}", "-i", c["url"], "-t", f"{self.CLIP_SECONDS}", "-an", "-vf", vf,
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", out + ".part.mp4"]
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=150, **_popen_kwargs())
            part = out + ".part.mp4"
            if r.returncode == 0 and os.path.exists(part) and os.path.getsize(part) > 10000:
                os.replace(part, out)
                return out
            if os.path.exists(part):
                os.remove(part)
            with self.lock:
                self.why[c["provider"]] = "a clip couldn't be read: " + r.stderr.decode("utf-8", "replace").strip()[-90:]
        except Exception as e:
            with self.lock:
                self.why[c["provider"]] = _short(e)
        return None

    def _search(self, q, portrait):
        out = []
        order = [("Pexels", self._pexels), ("Pixabay", self._pixabay), ("Wikimedia", self._wikimedia),
                 ("Internet Archive", self._archive)]
        if SPACEY.search(q):
            order.insert(2, ("NASA", self._nasa))
        for name, fn in order:
            with self.lock:
                if self.fail.get(name, 0) >= 2:
                    continue
            try:
                res = fn(q, portrait)
            except _Skip:
                continue
            except Exception as e:
                with self.lock:
                    self.fail[name] = self.fail.get(name, 0) + 1
                    self.why[name] = _short(e)
                continue
            with self.lock:
                self.fail[name] = 0
            random.shuffle(res)
            out += res
            if len(out) >= 6:          # enough choices; don't hammer the other sites
                break
        return out

    # ---------------------------------------------------------------- sites
    def _pexels(self, q, portrait):
        key = self.s.get("pexels_api_key")
        if not key:
            raise _Skip()
        r = _get("https://api.pexels.com/videos/search", headers={"Authorization": key},
                 params={"query": q, "per_page": 15, "orientation": "portrait" if portrait else "landscape"})
        r.raise_for_status()
        out = []
        for v in r.json().get("videos", []):
            files = [f for f in v.get("video_files", []) if f.get("link") and (f.get("file_type") or "").endswith("mp4")]
            files.sort(key=lambda f: abs((f.get("height") or 0) - (1920 if portrait else 1080)))
            if files:
                out.append({"provider": "Pexels", "key": f"pxv{v['id']}", "url": files[0]["link"], "duration": v.get("duration")})
        return out

    def _pixabay(self, q, portrait):
        key = self.s.get("pixabay_api_key")
        if not key:
            raise _Skip()
        r = _get("https://pixabay.com/api/videos/", params={"key": key, "q": q[:100], "per_page": 15, "safesearch": "true"})
        r.raise_for_status()
        out = []
        for h in r.json().get("hits", []):
            v = h.get("videos", {})
            best = v.get("large") if (v.get("large") or {}).get("url") else v.get("medium")
            if best and best.get("url"):
                out.append({"provider": "Pixabay", "key": f"pbv{h['id']}", "url": best["url"], "duration": h.get("duration")})
        return out

    def _wikimedia(self, q, portrait):
        r = _get("https://commons.wikimedia.org/w/api.php",
                 params={"action": "query", "format": "json", "generator": "search", "gsrsearch": f"{q} filetype:video",
                         "gsrnamespace": 6, "gsrlimit": 15, "prop": "videoinfo", "viprop": "url|size|mime|extmetadata|derivatives",
                         "viextmetadatafilter": "LicenseShortName|Artist|ObjectName|LicenseUrl"})
        r.raise_for_status()
        out = []
        for pg in (r.json().get("query", {}).get("pages", {}) or {}).values():
            vi = (pg.get("videoinfo") or [{}])[0]
            if (vi.get("height") or 0) < 360 or (vi.get("duration") or 0) < 3:
                continue
            md = vi.get("extmetadata") or {}
            lic = (md.get("LicenseShortName") or {}).get("value", "")
            if not _ok_license(lic + " " + (md.get("LicenseUrl") or {}).get("value", "")):
                continue
            ders = [d for d in vi.get("derivatives") or [] if (d.get("transcodekey") or "").endswith(".webm")]
            ders.sort(key=lambda d: abs((d.get("height") or 0) - 1080))
            url = ders[0]["src"] if ders else (vi.get("url") or "").split("?")[0]
            if not url:
                continue
            artist = re.sub(r"<[^>]+>", "", (md.get("Artist") or {}).get("value", "")).strip()[:60] or "unknown"
            title = re.sub(r"<[^>]+>", "", str((md.get("ObjectName") or {}).get("value") or pg.get("title", "").replace("File:", "")))[:80]
            out.append({"provider": "Wikimedia", "key": f"wmv{pg.get('pageid')}", "url": url, "duration": vi.get("duration"),
                        "credit": f"Video \"{title}\" by {artist} ({lic or 'free license'}) {vi.get('descriptionshorturl') or ''}".strip()})
        return out

    def _archive(self, q, portrait):
        words = " ".join(re.findall(r"[\w']+", q)[:4]) or "city"
        lic = "(licenseurl:*publicdomain* OR licenseurl:*creativecommons.org/licenses/by/* OR licenseurl:*creativecommons.org/licenses/by-sa/*)"
        query = f"(title:({words}) OR subject:({words}) OR description:({words})) AND mediatype:movies AND {lic}"
        r = _get("https://archive.org/advancedsearch.php",
                 params={"q": query, "fl[]": ["identifier", "title", "licenseurl", "creator"], "rows": 12,
                         "sort[]": "downloads desc", "output": "json"})
        r.raise_for_status()
        docs = [d for d in r.json().get("response", {}).get("docs", []) if _ok_license(d.get("licenseurl"))]
        random.shuffle(docs)
        out = []
        for d in docs[:4]:                       # metadata lookups are one request each; keep it small
            try:
                m = _get(f"https://archive.org/metadata/{d['identifier']}", timeout=20).json()
            except Exception:
                continue
            files = []
            for f in m.get("files", []):
                nm, fmt = f.get("name", ""), (f.get("format") or "").lower()
                if nm.lower().endswith(".mp4") and ("mpeg4" in fmt or "h.264" in fmt or "512kb" in fmt or fmt == ""):
                    files.append(f)
            if not files:
                continue
            files.sort(key=lambda f: -int(f.get("size") or 0))
            f = files[0]
            length = _seconds(f.get("length"))
            if length and length < 4:
                continue
            title = (d.get("title") or d["identifier"])
            title = title if isinstance(title, str) else str(title[0])
            lic_url = d.get("licenseurl") or ""
            lic_txt = "public domain" if "publicdomain" in lic_url else lic_url
            from urllib.parse import quote
            out.append({"provider": "Internet Archive", "key": f"ia{d['identifier']}",
                        "url": f"https://archive.org/download/{d['identifier']}/{quote(f['name'])}", "duration": length,
                        "credit": f"Video \"{title[:80]}\" ({lic_txt}) https://archive.org/details/{d['identifier']}"})
        return out

    def _nasa(self, q, portrait):
        r = _get("https://images-api.nasa.gov/search", params={"q": q, "media_type": "video", "page_size": 10})
        r.raise_for_status()
        out = []
        items = r.json().get("collection", {}).get("items", [])
        random.shuffle(items)
        for it in items[:4]:
            try:
                files = _get(it["href"], timeout=20).json()
            except Exception:
                continue
            pick = None
            for want in ("~large.mp4", "~orig.mp4", "~medium.mp4", "~mobile.mp4"):
                pick = next((u for u in files if u.endswith(want)), None)
                if pick:
                    break
            if not pick:
                continue
            d = (it.get("data") or [{}])[0]
            out.append({"provider": "NASA", "key": f"nasa{d.get('nasa_id')}", "url": pick.replace("http://", "https://"),
                        "start": 4.0, "credit": f"Video \"{(d.get('title') or 'NASA')[:80]}\" courtesy of NASA"})
        return out


def _seconds(v):
    if v is None:
        return None
    try:
        if ":" in str(v):
            p = [float(x) for x in str(v).split(":")]
            return sum(x * 60 ** i for i, x in enumerate(reversed(p)))
        return float(v)
    except ValueError:
        return None


class ClipReader:
    """Streams frames (PIL images) of a local clip from a start time, looping if it runs out."""

    def __init__(self, path, start, w, h):
        from PIL import Image
        self.Image, self.w, self.h = Image, w, h
        self.last = None
        cmd = [ffmpeg_path(), "-v", "error", "-stream_loop", "-1", "-ss", f"{start:.2f}", "-i", path, "-an",
               "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={FPS}",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        try:
            self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, **_popen_kwargs())
        except Exception:
            self.p = None

    def next(self):
        n = self.w * self.h * 3
        if self.p:
            buf = b""
            while len(buf) < n:
                chunk = self.p.stdout.read(n - len(buf))
                if not chunk:
                    break
                buf += chunk
            if len(buf) == n:
                self.last = self.Image.frombytes("RGB", (self.w, self.h), buf)
        return self.last

    def close(self):
        if self.p:
            try:
                self.p.kill()
                self.p.stdout.close()
                self.p.wait(timeout=5)
            except Exception:
                pass
            self.p = None


def test_sources(s, folder):
    """Tries every video site once (for the Settings 'Test' button)."""
    fs = FootageSource(s, folder)
    lines = []
    for name, fn, q in (("Pexels video", fs._pexels, "ocean waves"), ("Pixabay video", fs._pixabay, "ocean waves"),
                        ("Wikimedia video", fs._wikimedia, "ocean waves"), ("Internet Archive", fs._archive, "city"),
                        ("NASA video", fs._nasa, "galaxy")):
        try:
            res = fn(q, True)
            lines.append(f"✅ {name}: {len(res)} clips" if res else f"⚠️ {name}: no results")
        except _Skip:
            lines.append(f"➖ {name}: no key set")
        except Exception as e:
            lines.append(f"❌ {name}: {_short(e)}")
    return "\n".join(lines)
