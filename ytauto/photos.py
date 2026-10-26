"""Stock photos for backgrounds, from several services so one being down doesn't matter.

Order tried for each search (each service is skipped for the rest of the video once it keeps failing):
  Pexels (free key) → Pixabay (free key) → Unsplash (free key) → Openverse (no key, Creative Commons)
  → Wikimedia Commons (no key, free licenses) → AI image (Gemini, if your key can make images)
Photos that need credit (Creative Commons / Unsplash) are listed in the video description automatically."""
import hashlib
import os
import random
import re
import time

from PIL import Image

from . import visuals

UA = "NeonClip/2.0 (https://github.com/Neon-Forger/Clipping-Agent; YouTube video maker)"


def _get(url, **kw):
    import requests
    h = kw.pop("headers", {})
    h.setdefault("User-Agent", UA)
    return requests.get(url, headers=h, timeout=kw.pop("timeout", 30), **kw)


class PhotoSource:
    MAX_SEARCHES = 14   # per video, keeps keyless services under their rate limits; later beats reuse results

    def __init__(self, s, folder, log=None):
        self.s, self.folder, self.log = s, folder, log
        os.makedirs(folder, exist_ok=True)
        self.pools = {}            # query -> list of candidate dicts (not yet used)
        self.used = set()
        self.credits = []
        self.searches = 0
        self.fail = {}             # provider -> consecutive failures
        self.why = {}              # provider -> last error
        self.got = {}              # provider -> photos used
        self._warned = False
        self.last_key, self.last_credit = None, None

    # ------------------------------------------------------------------ public
    def get(self, query, portrait):
        self.last_key, self.last_credit = None, None
        q = re.sub(r"\s+", " ", (query or self.s.get("genre") or "city")).strip()[:60]
        img = self._next_from_pool(q)
        if img is None and self.searches < self.MAX_SEARCHES and q not in self.pools:
            self.searches += 1
            self.pools[q] = self._search(q, portrait)
            img = self._next_from_pool(q)
        if img is None:
            img = self._closest_pool(q)        # reuse photos from a similar search instead of going black
        if img is None:
            img = self._ai(q, portrait)
        if img is None and not self._warned and self.log:
            self._warned = True
            self.log("warn", "Couldn't get photos for some backgrounds (using video or other backgrounds instead). " + self.status_text())
        return img

    def status_text(self):
        parts = [f"{k}: {v}" for k, v in self.why.items()]
        return ("Photo services: " + "; ".join(parts)) if parts else "No photo service answered."

    def summary(self):
        return ", ".join(f"{n} from {k}" for k, n in self.got.items()) or "none"

    # ---------------------------------------------------------------- pooling
    def _next_from_pool(self, q):
        pool = self.pools.get(q) or []
        while pool:
            c = pool.pop(0)
            if c["key"] in self.used:
                continue
            img = self._load(c)
            if img is not None:
                return img
        return None

    def _closest_pool(self, q):
        words = set(q.lower().split())
        ranked = sorted(self.pools.items(), key=lambda kv: -len(words & set(kv[0].lower().split())))
        for k, pool in ranked:
            img = self._next_from_pool(k)
            if img is not None:
                return img
        return None

    def _load(self, c):
        try:
            name = hashlib.md5(c["url"].encode()).hexdigest()[:16] + ".img"
            path = os.path.join(self.folder, name)
            if not os.path.exists(path):
                r = _get(c["url"], timeout=60)
                r.raise_for_status()
                with open(path + ".part", "wb") as f:
                    f.write(r.content)
                os.replace(path + ".part", path)
            im = Image.open(path)
            im.load()
            im = im.convert("RGB")
            if min(im.size) < 400:
                return None
            self.used.add(c["key"])
            self.last_key, self.last_credit = c["key"], c.get("credit")
            self.got[c["provider"]] = self.got.get(c["provider"], 0) + 1
            if c.get("credit"):
                self.credits.append(c["credit"])
            if c.get("ping"):
                try:
                    _get(c["ping"][0], headers=c["ping"][1], timeout=10)   # Unsplash asks apps to report downloads
                except Exception:
                    pass
            return im
        except Exception:
            return None

    # --------------------------------------------------------------- searching
    def _search(self, q, portrait):
        for name, fn in (("Pexels", self._pexels), ("Pixabay", self._pixabay), ("Unsplash", self._unsplash),
                         ("Openverse", self._openverse), ("Wikimedia", self._wikimedia)):
            if self.fail.get(name, 0) >= 2:
                continue
            try:
                res = fn(q, portrait)
            except _Skip:
                continue
            except Exception as e:
                self.fail[name] = self.fail.get(name, 0) + 1
                self.why[name] = _short(e)
                continue
            self.fail[name] = 0
            if res:
                random.shuffle(res)
                return res
        return []

    def _pexels(self, q, portrait):
        key = self.s.get("pexels_api_key")
        if not key:
            raise _Skip()
        r = _get("https://api.pexels.com/v1/search", headers={"Authorization": key},
                 params={"query": q, "per_page": 15, "orientation": "portrait" if portrait else "landscape"})
        r.raise_for_status()
        return [{"provider": "Pexels", "key": f"px{p['id']}", "url": p["src"]["large2x"]} for p in r.json().get("photos", [])]

    def _pixabay(self, q, portrait):
        key = self.s.get("pixabay_api_key")
        if not key:
            raise _Skip()
        r = _get("https://pixabay.com/api/", params={"key": key, "q": q[:100], "image_type": "photo", "per_page": 20,
                                                      "safesearch": "true", "orientation": "vertical" if portrait else "horizontal"})
        r.raise_for_status()
        return [{"provider": "Pixabay", "key": f"pb{h['id']}", "url": h.get("largeImageURL") or h.get("webformatURL")}
                for h in r.json().get("hits", [])]

    def _unsplash(self, q, portrait):
        key = self.s.get("unsplash_access_key")
        if not key:
            raise _Skip()
        hdr = {"Authorization": f"Client-ID {key}", "Accept-Version": "v1"}
        r = _get("https://api.unsplash.com/search/photos", headers=hdr,
                 params={"query": q, "per_page": 20, "orientation": "portrait" if portrait else "landscape", "content_filter": "high"})
        r.raise_for_status()
        out = []
        for p in r.json().get("results", []):
            u = p.get("user") or {}
            out.append({"provider": "Unsplash", "key": f"us{p['id']}", "url": p["urls"]["regular"].replace("w=1080", "w=1920"),
                        "credit": f"Photo by {u.get('name') or 'unknown'} on Unsplash",
                        "ping": (p.get("links", {}).get("download_location"), hdr) if p.get("links", {}).get("download_location") else None})
        return out

    def _openverse(self, q, portrait):
        r = _get("https://api.openverse.org/v1/images/",
                 params={"q": q, "page_size": 20, "mature": "false", "license_type": "commercial,modification",
                         "aspect_ratio": "tall" if portrait else "wide"})
        if r.status_code == 429:
            self.fail["Openverse"] = 99     # out of free searches for now
            self.why["Openverse"] = "hit its free limit (20 searches/min, 200/day)"
            return []
        r.raise_for_status()
        out = []
        for x in r.json().get("results", []):
            if x.get("width") and x["width"] < 700:
                continue
            lic = (x.get("license") or "").upper()
            lic_txt = lic if lic in ("CC0", "PDM") else f"CC {lic} {x.get('license_version') or ''}".strip()
            out.append({"provider": "Openverse", "key": f"ov{x['id']}", "url": x["url"],
                        "credit": f"\"{x.get('title') or 'photo'}\" by {x.get('creator') or 'unknown'} ({lic_txt}) {x.get('foreign_landing_url') or ''}".strip()})
        return out

    def _wikimedia(self, q, portrait):
        r = _get("https://commons.wikimedia.org/w/api.php",
                 params={"action": "query", "format": "json", "generator": "search", "gsrsearch": f"{q} filetype:bitmap",
                         "gsrnamespace": 6, "gsrlimit": 20, "prop": "imageinfo", "iiprop": "url|extmetadata|size|mime",
                         "iiurlwidth": 1920, "iiextmetadatafilter": "LicenseShortName|Artist|ObjectName"})
        r.raise_for_status()
        out = []
        for pg in (r.json().get("query", {}).get("pages", {}) or {}).values():
            ii = (pg.get("imageinfo") or [{}])[0]
            if ii.get("mime") not in ("image/jpeg", "image/png", "image/webp") or (ii.get("width") or 0) < 800:
                continue
            md = ii.get("extmetadata") or {}
            artist = re.sub(r"<[^>]+>", "", (md.get("Artist") or {}).get("value", "")).strip()[:60] or "unknown"
            lic = (md.get("LicenseShortName") or {}).get("value", "free license")
            title = (md.get("ObjectName") or {}).get("value") or pg.get("title", "").replace("File:", "")
            out.append({"provider": "Wikimedia", "key": f"wm{pg.get('pageid')}", "url": ii.get("thumburl") or ii.get("url"),
                        "credit": f"\"{re.sub(r'<[^>]+>', '', str(title))[:80]}\" by {artist} ({lic}) {ii.get('descriptionshorturl') or ''}".strip()})
        return out

    def _ai(self, q, portrait):
        if not self.s.get("thumbnails", {}).get("ai_images"):
            return None
        p = os.path.join(self.folder, f"ai-{hashlib.md5(q.encode()).hexdigest()[:10]}.png")
        got = visuals.ai_image(self.s["ai"], f"Realistic stock photo: {q}. No people's faces", p, "9:16" if portrait else "16:9")
        if got:
            try:
                self.got["AI"] = self.got.get("AI", 0) + 1
                return Image.open(got).convert("RGB")
            except Exception:
                return None
        return None


class _Skip(Exception):
    """Service not set up (no key)."""


def _short(e):
    t = str(e)
    m = re.search(r"(\d{3}) (Client|Server) Error", t)
    if m:
        return f"error {m.group(1)}"
    if "timed out" in t.lower():
        return "timed out"
    if "Failed to resolve" in t or "getaddrinfo" in t or "Name or service" in t:
        return "can't be reached (site down or blocked)"
    return t[:80]


def test_sources(s, folder, log=None):
    """Tries every photo service once and returns a readable report (for the Settings 'Test' button)."""
    ps = PhotoSource(s, folder)
    lines = []
    for name, fn in (("Pexels", ps._pexels), ("Pixabay", ps._pixabay), ("Unsplash", ps._unsplash),
                     ("Openverse", ps._openverse), ("Wikimedia", ps._wikimedia)):
        t = time.time()
        try:
            res = fn("lighthouse", True)
            if not res and name in ps.why:
                lines.append(f"⚠️ {name}: {ps.why[name]}")
            else:
                lines.append(f"✅ {name}: {len(res)} photos ({time.time() - t:.1f}s)")
        except _Skip:
            lines.append(f"➖ {name}: no key set")
        except Exception as e:
            lines.append(f"❌ {name}: {_short(e)}")
    return "\n".join(lines)


def pixabay_video(query, key, portrait, folder, used=None):
    """Stock video clip from Pixabay (free key). Returns a file path or None."""
    if not key:
        return None
    used = used if used is not None else set()
    try:
        r = _get("https://pixabay.com/api/videos/", params={"key": key, "q": query[:100], "per_page": 15, "safesearch": "true"})
        r.raise_for_status()
        hits = r.json().get("hits", [])
    except Exception:
        return None
    random.shuffle(hits)
    for h in hits:
        if h.get("id") in used:
            continue
        v = h.get("videos", {})
        best = v.get("large") if (v.get("large") or {}).get("url") else v.get("medium")
        if not best or not best.get("url"):
            continue
        w, hh = best.get("width") or 0, best.get("height") or 0
        if portrait and w > hh * 1.9:
            continue
        path = os.path.join(folder, f"pixabay-{h['id']}.mp4")
        if not os.path.exists(path):
            try:
                os.makedirs(folder, exist_ok=True)
                with _get(best["url"], stream=True, timeout=120) as resp:
                    resp.raise_for_status()
                    with open(path + ".part", "wb") as fh:
                        for chunk in resp.iter_content(1 << 20):
                            fh.write(chunk)
                os.replace(path + ".part", path)
            except Exception:
                continue
        used.add(h.get("id"))
        return path
    return None
