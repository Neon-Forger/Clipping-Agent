"""Optional on-device voice cloning engine (your own voice in the videos).

Real voice cloning needs a big model (Coqui XTTS v2) and PyTorch, which would bloat the app and slow every build,
so NeonClip does NOT bundle them. Instead, the first time you turn cloning on, it builds a small private Python
environment next to your settings and installs the engine there (a one-time ~2 GB download). Making a video then
runs that engine as a separate program, so the main app stays small and still starts instantly.

Everything here degrades gracefully: if the engine isn't set up, or anything fails, the caller falls back to the
normal AI voice and tells you why. Nothing here ever blocks a video from being made."""
import json
import os
import shutil
import subprocess
import sys

from agent.config import data_dir


def _dir():
    d = os.path.join(data_dir(), "voice")
    os.makedirs(d, exist_ok=True)
    return d


def sample_path(s=None):
    """The user's reference recording (what their voice sounds like)."""
    v = (s.get("voice_clone") if s else None) or {}
    p = (v.get("sample") or "").strip()
    return p if p and os.path.exists(p) else None


def _env_dir():
    return os.path.join(_dir(), "engine")


def _venv_python():
    env = _env_dir()
    exe = os.path.join(env, "Scripts", "python.exe") if os.name == "nt" else os.path.join(env, "bin", "python")
    return exe


def _marker():
    return os.path.join(_env_dir(), "ready.txt")


def ready():
    """True once the cloning engine is installed and usable."""
    return os.path.exists(_venv_python()) and os.path.exists(_marker())


def status_text(s=None):
    have_sample = bool(sample_path(s))
    if ready():
        return "Voice cloning is set up." + ("" if have_sample else " Add a voice sample to use it.")
    return "Voice cloning isn't set up yet (one-time ~2 GB download)." + (" Voice sample saved." if have_sample else "")


def _base_python():
    """A real Python interpreter to build the engine's environment with (the packaged app can't build it itself)."""
    cands = []
    exe = sys.executable or ""
    if exe and "python" in os.path.basename(exe).lower():       # running from source, not the frozen .exe
        cands.append(exe)
    for name in ("python3.11", "python3.10", "python3", "python", "py"):
        found = shutil.which(name)
        if found:
            cands.append(found + ("||-3.11" if name == "py" else ""))
    # de-dup preserving order
    seen, out = set(), []
    for c in cands:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _run(cmd, log=None, timeout=3600):
    kw = {"creationflags": 0x08000000} if os.name == "nt" else {}
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **kw)
    if p.returncode != 0 and log:
        log("warn", f"voice setup: {(p.stderr or p.stdout or '').strip()[-300:]}")
    return p.returncode == 0, (p.stderr or p.stdout or "")


def ensure(s=None, log=None, progress=None):
    """Build the engine environment and install Coqui XTTS. One-time, slow. Returns (ok, message)."""
    if ready():
        return True, "Voice cloning is already set up."
    pys = _base_python()
    if not pys:
        return False, ("Voice cloning needs Python on this PC to set itself up. Install Python 3.11 from python.org "
                       "(tick “Add to PATH”), then try again.")
    env = _env_dir()
    if progress:
        progress("Creating the voice engine environment…")
    ok = False
    for base in pys:
        base = base.split("||")[0]
        shutil.rmtree(env, ignore_errors=True)
        ok, _ = _run([base, "-m", "venv", env], log, timeout=300)
        if ok and os.path.exists(_venv_python()):
            break
    if not ok or not os.path.exists(_venv_python()):
        return False, "Couldn't create the voice engine environment. Is Python installed and on PATH?"
    vpy = _venv_python()
    if progress:
        progress("Upgrading pip…")
    _run([vpy, "-m", "pip", "install", "--upgrade", "pip", "wheel"], log, timeout=600)
    if progress:
        progress("Downloading the voice engine (~2 GB, one time)… this can take several minutes.")
    ok, out = _run([vpy, "-m", "pip", "install", "coqui-tts", "soundfile"], log, timeout=5400)
    if not ok:
        return False, "The voice engine download failed. Check the PC's internet connection and try again."
    with open(_marker(), "w", encoding="utf-8") as f:
        f.write("ok")
    return True, "Voice cloning is ready."


_WORKER = r'''
import sys, os, json
os.environ.setdefault("COQUI_TOS_AGREED", "1")
text, sample, out = json.load(sys.stdin)["text"], sys.argv[1], sys.argv[2]
from TTS.api import TTS
import torch
dev = "cuda" if torch.cuda.is_available() else "cpu"
m = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(dev)
m.tts_to_file(text=text, speaker_wav=sample, language="en", file_path=out)
print("OK")
'''


def synth(s, text, out_wav, log=None):
    """Clone the user's voice saying `text` into out_wav. Raises on any problem so the caller can fall back."""
    if not ready():
        raise RuntimeError("voice cloning isn't set up")
    sample = sample_path(s)
    if not sample:
        raise RuntimeError("no voice sample saved")
    worker = os.path.join(_dir(), "_worker.py")
    with open(worker, "w", encoding="utf-8") as f:
        f.write(_WORKER)
    kw = {"creationflags": 0x08000000} if os.name == "nt" else {}
    env = dict(os.environ, COQUI_TOS_AGREED="1")
    p = subprocess.run([_venv_python(), worker, sample, out_wav], input=json.dumps({"text": text}),
                       capture_output=True, text=True, timeout=1800, env=env, **kw)
    if p.returncode != 0 or not (os.path.exists(out_wav) and os.path.getsize(out_wav) > 2000):
        raise RuntimeError((p.stderr or p.stdout or "voice engine failed").strip()[-200:])
    return out_wav
