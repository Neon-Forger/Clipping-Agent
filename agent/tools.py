"""Helpers for finding ffmpeg and running it without popping up console windows."""
import os
import shutil
import subprocess
import sys

_FFMPEG = None


def ffmpeg_path():
    global _FFMPEG
    if _FFMPEG:
        return _FFMPEG
    found = shutil.which("ffmpeg")
    if not found:
        try:
            import imageio_ffmpeg
            found = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            found = "ffmpeg"
    _FFMPEG = found
    return found


def run(cmd, timeout=None, check=True, cwd=None):
    kw = {"cwd": cwd}
    if sys.platform == "win32":
        kw["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, **kw)
    if check and p.returncode != 0:
        raise RuntimeError(f"{os.path.basename(str(cmd[0]))} failed: {p.stderr.decode('utf-8', 'replace')[-1500:]}")
    return p


def media_duration(path):
    """Duration in seconds, read from ffmpeg's own output (no ffprobe needed)."""
    p = run([ffmpeg_path(), "-hide_banner", "-i", path], check=False)
    txt = p.stderr.decode("utf-8", "replace")
    import re
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.?\d*)", txt)
    if not m:
        return 0.0
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def fonts_dir():
    from .config import resource_path
    return resource_path("assets", "fonts")
