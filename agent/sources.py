"""Finding new videos from the people/channels in settings, and downloading them."""
import os
import time

from .tools import ffmpeg_path


def _ydl(opts):
    import yt_dlp
    base = {"quiet": True, "no_warnings": True, "noprogress": True, "ffmpeg_location": ffmpeg_path()}
    from .config import data_dir
    cookies = os.path.join(data_dir(), "youtube_cookies.txt")
    if os.path.exists(cookies):
        base["cookiefile"] = cookies
    base.update(opts)
    return yt_dlp.YoutubeDL(base)


def video_info(url):
    with _ydl({"skip_download": True}) as y:
        return y.extract_info(url, download=False)


def find_new_videos(source, db, log):
    """Returns how many new videos were queued for this source."""
    added = 0
    name = source.get("name", "source")
    must = (source.get("title_must_contain") or "").lower()
    max_age = source.get("only_newer_than_days") or 0

    # fixed links first
    for url in source.get("video_urls") or []:
        try:
            info = video_info(url)
            if db.add_video(info["id"], name, info.get("webpage_url") or url, info.get("title", ""), info.get("duration")):
                added += 1
                log("info", f"Queued video: {info.get('title')}")
        except Exception as e:
            log("warn", f"Couldn't read {url}: {e}")

    ch = source.get("channel_url")
    if ch:
        try:
            with _ydl({"extract_flat": "in_playlist", "playlistend": 15, "skip_download": True}) as y:
                listing = y.extract_info(ch, download=False)
            for entry in listing.get("entries") or []:
                if not entry:
                    continue
                title = entry.get("title") or ""
                if must and must not in title.lower():
                    continue
                vid = entry.get("id")
                if not vid or db.video(vid):
                    continue
                url = entry.get("url") or f"https://www.youtube.com/watch?v={vid}"
                if not url.startswith("http"):
                    url = f"https://www.youtube.com/watch?v={vid}"
                if max_age:
                    try:
                        info = video_info(url)
                        ts = info.get("timestamp") or 0
                        if ts and time.time() - ts > max_age * 86400:
                            continue
                        if info.get("live_status") in ("is_upcoming", "is_live"):
                            continue
                        title = info.get("title", title)
                    except Exception:
                        continue
                if db.add_video(vid, name, url, title, entry.get("duration")):
                    added += 1
                    log("info", f"New video found: {title}")
        except Exception as e:
            log("warn", f"Couldn't check {ch}: {e}")
    return added


def download(video, folder, log):
    os.makedirs(folder, exist_ok=True)
    out = os.path.join(folder, f"{video['id']}.%(ext)s")
    opts = {
        "format": "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/bv*[height<=1080]+ba/b[height<=1080]/b",
        "merge_output_format": "mp4",
        "outtmpl": out,
        "retries": 5,
    }
    with _ydl(opts) as y:
        y.download([video["url"]])
    for ext in ("mp4", "mkv", "webm"):
        p = os.path.join(folder, f"{video['id']}.{ext}")
        if os.path.exists(p):
            return p
    raise RuntimeError("download finished but no file was found")
