"""One voice layer for every video. Picks the voice (the normal AI voice, or the user's cloned voice for Shorts),
makes the audio smoother and clearer, and returns word timings for captions and for timing the visuals.

Smoothness/clarity here + the final mix in render._finish together fix rushed, clipped-sounding narration:
each line ends on a full stop with a short breath after it, tiny fades remove clicks, and the final mix adds a
gentle presence lift, de-rumble and level smoothing."""
import os
import re

from agent.tools import ffmpeg_path, media_duration, run

from . import tts


def _tidy(text):
    """Clean the line so the voice reads it fluently (full sentences, no odd spacing, a real ending)."""
    t = re.sub(r"\s+", " ", (text or "").strip())
    t = t.replace("--", ", ").replace(" - ", ", ")  # dashes make edge-tts clip the line
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)          # no space before punctuation
    t = re.sub(r"\s{2,}", " ", t).strip()            # tidy any doubled spaces left behind
    if t and t[-1] not in ".!?…":
        t += "."                                     # a terminal stop lets the voice finish the thought
    return t


def _use_clone(s, portrait):
    v = s.get("voice_clone") or {}
    if str(v.get("mode")) != "cloned":
        return False
    if not (v.get("sample") and os.path.exists(v.get("sample"))):
        return False
    return portrait or str(v.get("use_in") or "shorts") == "all"


def _smooth(src, out_mp3):
    """Re-encode with a tiny fade-in and a short breath of trailing silence (clean joins, no clipped tail)."""
    try:
        run([ffmpeg_path(), "-v", "error", "-y", "-i", src,
             "-af", "afade=t=in:st=0:d=0.03,apad=pad_dur=0.22,aresample=48000",
             "-ar", "48000", "-ac", "1", "-b:a", "192k", out_mp3])
        if os.path.exists(out_mp3) and os.path.getsize(out_mp3) > 500:
            return out_mp3
    except Exception:
        pass
    if src != out_mp3:
        os.replace(src, out_mp3)
    return out_mp3


def _edge(s, text, out_mp3, log=None):
    raw = out_mp3 + ".raw.mp3"
    words = tts.speak(text, s.get("voice") or "en-US-AndrewNeural", s.get("voice_rate", "+0%"), raw)
    _smooth(raw, out_mp3)
    try:
        os.remove(raw)
    except OSError:
        pass
    return words


def _whisper_words(s, wav, text, log=None):
    """Word timings for cloned audio (the model gives none), via the speech-to-text already in the app."""
    try:
        from agent import transcribe
        model = transcribe._get_model(s.get("transcribe", {}) or {})
        segments, _ = model.transcribe(wav, word_timestamps=True, vad_filter=False, beam_size=1,
                                       condition_on_previous_text=False)
        words = [{"s": round(w.start, 3), "e": round(w.end, 3), "w": w.word.strip()}
                 for seg in segments for w in (seg.words or []) if w.word.strip()]
        if words:
            return words
    except Exception as e:
        if log:
            log("warn", f"Couldn't time the cloned words ({e}); spacing captions evenly.")
    dur = media_duration(wav) or 1.0                  # even spacing as a fallback
    toks = text.split() or [text]
    step = dur / len(toks)
    return [{"s": round(i * step, 3), "e": round((i + 1) * step, 3), "w": w} for i, w in enumerate(toks)]


def _clone(s, text, out_mp3, log=None):
    from . import voice_engine
    wav = out_mp3 + ".clone.wav"
    voice_engine.synth(s, text, wav, log)             # raises if not set up / fails -> caller falls back
    raw = out_mp3 + ".raw.mp3"
    run([ffmpeg_path(), "-v", "error", "-y", "-i", wav, "-ar", "48000", "-ac", "1", "-b:a", "192k", raw])
    _smooth(raw, out_mp3)
    words = _whisper_words(s, wav, text, log)
    for f in (wav, raw):
        try:
            os.remove(f)
        except OSError:
            pass
    return words


def narrate(s, text, out_mp3, portrait=True, log=None):
    """Write out_mp3 and return word timings [{s, e, w}]. Uses the cloned voice when enabled, else the AI voice."""
    text = _tidy(text)
    if _use_clone(s, portrait):
        try:
            return _clone(s, text, out_mp3, log)
        except Exception as e:
            if log:
                log("warn", f"Using the AI voice this time — voice cloning couldn't run ({e}).")
    return _edge(s, text, out_mp3, log)
