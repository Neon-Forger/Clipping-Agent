"""Speech-to-text on the PC with word-level timing (faster-whisper).
The model downloads once (a few hundred MB) the first time it runs."""
import json
import os

from .tools import ffmpeg_path, run

_model = None
_model_key = None


def _get_model(cfg):
    global _model, _model_key
    key = (cfg.get("model", "small.en"), cfg.get("device", "auto"), cfg.get("compute_type", "int8"))
    if _model is None or _model_key != key:
        from faster_whisper import WhisperModel
        _model = WhisperModel(key[0], device=key[1], compute_type=key[2])
        _model_key = key
    return _model


def transcribe(video_path, cache_path, cfg, log=None):
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    wav = os.path.splitext(cache_path)[0] + ".wav"
    run([ffmpeg_path(), "-v", "error", "-y", "-i", video_path, "-vn", "-ac", "1", "-ar", "16000", wav])
    model = _get_model(cfg)
    segments, info = model.transcribe(wav, word_timestamps=True, vad_filter=True, beam_size=1,
                                      condition_on_previous_text=False)
    out = []
    last_report = 0
    for seg in segments:
        words = [{"s": round(w.start, 2), "e": round(w.end, 2), "w": w.word.strip()} for w in (seg.words or []) if w.word.strip()]
        out.append({"start": round(seg.start, 2), "end": round(seg.end, 2), "text": seg.text.strip(), "words": words})
        if log and seg.end - last_report > 600:
            last_report = seg.end
            log("info", f"Transcribing... {int(seg.end // 60)} min done")
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(out, f)
    try:
        os.remove(wav)
    except OSError:
        pass
    return out


def all_words(transcript):
    return [w for seg in transcript for w in seg["words"]]


def transcript_for_ai(transcript, max_chars=180000):
    """Compact '[mm:ss] text' lines for the language model."""
    lines = []
    for seg in transcript:
        t = int(seg["start"])
        lines.append(f"[{t // 60}:{t % 60:02d}] {seg['text']}")
    text = "\n".join(lines)
    return text[:max_chars]
