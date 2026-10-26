"""The AI part: talks to Gemini, OpenRouter or any OpenAI-compatible API.
Used to pick the best moments, write hook titles and captions, and answer
questions you send from the phone."""
import json
import re
import time

import requests


class NoAIKey(Exception):
    pass


class AIError(RuntimeError):
    """The AI service answered with an error (bad model, quota, outage). Worth retrying later."""


GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
_gemini_auto = {}


def pick_gemini_model(key):
    """Asks Google which models this key can use and picks the best general 'flash' model
    (Google retires model names over time, e.g. gemini-2.5-flash shut down on 16 Oct 2026)."""
    if key in _gemini_auto:
        return _gemini_auto[key]
    r = requests.get(f"{GEMINI_BASE}/models?pageSize=200", headers={"x-goog-api-key": key}, timeout=30)
    r.raise_for_status()
    names = []
    for m in r.json().get("models", []):
        if "generateContent" not in (m.get("supportedGenerationMethods") or []):
            continue
        n = m.get("name", "").split("/")[-1]
        if not n.startswith("gemini") or any(x in n for x in ("image", "tts", "audio", "live", "embedding", "thinking", "exp", "robotics", "computer")):
            continue
        names.append(n)

    def score(n):
        ver = re.findall(r"gemini-(\d+(?:\.\d+)?)", n)
        v = float(ver[0]) if ver else 0
        return (("flash" in n and "lite" not in n) * 4 + ("pro" in n) * 2 + ("lite" in n) * 1,
                v, "preview" not in n, -len(n))
    if not names:
        raise RuntimeError("this Gemini key can't use any text models")
    best = max(names, key=score)
    _gemini_auto[key] = best
    return best


def _alternates(key, current):
    """Other usable text models, best first (used when the main one is overloaded)."""
    try:
        r = requests.get(f"{GEMINI_BASE}/models?pageSize=200", headers={"x-goog-api-key": key}, timeout=30)
        names = [m["name"].split("/")[-1] for m in r.json().get("models", [])
                 if "generateContent" in (m.get("supportedGenerationMethods") or [])]
    except Exception:
        return []
    ok = [n for n in names if n.startswith("gemini") and n != current and "flash" in n
          and not any(x in n for x in ("image", "tts", "audio", "live", "embedding", "thinking", "exp", "robotics", "computer"))]

    def ver(n):
        v = re.findall(r"gemini-(\d+(?:\.\d+)?)", n)
        return float(v[0]) if v else 0
    ok.sort(key=lambda n: ("lite" in n, "preview" in n, -ver(n)))
    return ok[:3]


def _gemini_call(key, model, prompt, json_mode):
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.6}}
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"
    return requests.post(f"{GEMINI_BASE}/models/{model}:generateContent", json=body,
                         headers={"x-goog-api-key": key}, timeout=300)


def _gemini(cfg, prompt, json_mode):
    key = cfg.get("gemini_api_key")
    model = (cfg.get("gemini_model") or "").strip() or "auto"
    if model == "auto":
        model = pick_gemini_model(key)
    r = _gemini_call(key, model, prompt, json_mode)
    if r.status_code == 404:  # model retired / not available: pick one that exists
        model = pick_gemini_model(key)
        r = _gemini_call(key, model, prompt, json_mode)
    if r.status_code in (429, 500, 503):  # busy / rate limited: try the other flash models before giving up
        import time as _t
        for alt in _alternates(key, model):
            _t.sleep(2)
            r2 = _gemini_call(key, alt, prompt, json_mode)
            if r2.status_code < 400:
                r, model = r2, alt
                break
    if r.status_code >= 400:
        try:
            msg = r.json().get("error", {}).get("message", "")
        except Exception:
            msg = r.text[:200]
        raise RuntimeError(f"Gemini {r.status_code} ({model}): {msg[:300]}")
    data = r.json()
    cands = data.get("candidates") or []
    if not cands:
        raise RuntimeError(f"Gemini returned no answer: {str(data.get('promptFeedback', ''))[:200]}")
    return "".join(p.get("text", "") for p in cands[0].get("content", {}).get("parts", []))


def _openai_like(base_url, key, model, prompt, json_mode, extra_headers=None):
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    headers.update(extra_headers or {})
    body = {"model": model, "temperature": 0.6, "messages": [{"role": "user", "content": prompt}]}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    r = requests.post(base_url.rstrip("/") + "/chat/completions", headers=headers, json=body, timeout=300)
    if r.status_code == 400 and json_mode:
        body.pop("response_format", None)
        r = requests.post(base_url.rstrip("/") + "/chat/completions", headers=headers, json=body, timeout=300)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


PROVIDERS = ["gemini", "nvidia", "openrouter", "openai_compatible"]
KEY_FIELDS = ("gemini_api_key", "nvidia_api_key", "openrouter_api_key", "openai_compatible_api_key")
NVIDIA_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_PREFERRED = ["meta/llama-3.3-70b-instruct", "deepseek-ai/deepseek-v3.1", "moonshotai/kimi-k2-instruct",
                    "nvidia/llama-3.3-nemotron-super-49b-v1.5", "nvidia/llama-3.3-nemotron-super-49b-v1",
                    "qwen/qwen3-235b-a22b", "meta/llama-3.1-70b-instruct", "mistralai/mistral-large-2-instruct"]
_nvidia_model = {}


def has_key(cfg):
    return any(cfg.get(k) for k in KEY_FIELDS)


def nvidia_models(key):
    r = requests.get(NVIDIA_URL + "/models", headers={"Authorization": f"Bearer {key}"}, timeout=30)
    r.raise_for_status()
    return [m.get("id") for m in r.json().get("data", []) if m.get("id")]


def pick_nvidia_model(key):
    """A good chat model that this NVIDIA key can use (the catalog changes over time)."""
    ids = nvidia_models(key)
    for want in NVIDIA_PREFERRED:
        if want in ids:
            return want
    chat = [i for i in ids if "instruct" in i and not any(x in i for x in ("embed", "vision", "guard", "reward", "coder"))]
    return chat[0] if chat else (ids[0] if ids else NVIDIA_PREFERRED[0])


def _nvidia(cfg, prompt, json_mode):
    key = cfg["nvidia_api_key"].strip()
    model = (cfg.get("nvidia_model") or "auto").strip()
    if model in ("", "auto"):
        model = _nvidia_model.get(key) or pick_nvidia_model(key)
        _nvidia_model[key] = model
    for attempt in range(3):
        try:
            return _strip_think(_openai_like(NVIDIA_URL, key, model, prompt, json_mode))
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else 0
            if code == 429 and attempt < 2:          # 40 requests/min per model on the free tier
                time.sleep(min(30, float(e.response.headers.get("Retry-After") or 10)))
                continue
            if code in (404, 400, 410, 422) and attempt == 0 and "model" in (e.response.text or "").lower():
                model = pick_nvidia_model(key)       # model retired or misspelled -> pick one that exists
                _nvidia_model[key] = model
                continue
            raise
    raise AIError("NVIDIA kept refusing requests")


def _strip_think(text):
    """Reasoning models (DeepSeek R1, Nemotron) may prepend <think>...</think>."""
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()


def ask(cfg, prompt, json_mode=False):
    errors = []
    order = list(cfg.get("provider_order") or PROVIDERS)
    order += [p for p in PROVIDERS if p not in order]        # providers added in newer versions
    first = (cfg.get("first") or "").strip().lower()
    if first in PROVIDERS:
        order = [first] + [p for p in order if p != first]
    for prov in order:
        try:
            if prov == "nvidia" and cfg.get("nvidia_api_key"):
                return _nvidia(cfg, prompt, json_mode)
            if prov == "gemini" and cfg.get("gemini_api_key"):
                return _gemini(cfg, prompt, json_mode)
            if prov == "openrouter" and cfg.get("openrouter_api_key"):
                return _openai_like("https://openrouter.ai/api/v1", cfg["openrouter_api_key"],
                                    cfg.get("openrouter_model") or "openrouter/auto", prompt, json_mode,
                                    {"HTTP-Referer": "https://github.com/Neon-Forger/clipping-agent", "X-Title": "NeonClip"})
            if prov == "openai_compatible" and cfg.get("openai_compatible_api_key"):
                return _openai_like(cfg.get("openai_compatible_base_url") or "https://api.openai.com/v1",
                                    cfg["openai_compatible_api_key"], cfg.get("openai_compatible_model") or "gpt-4o-mini",
                                    prompt, json_mode)
        except Exception as e:
            errors.append(f"{prov}: {e}")
    if errors:
        msg = " | ".join(errors)
        for k in KEY_FIELDS:
            if cfg.get(k):
                msg = msg.replace(cfg[k], "***")
        raise AIError("All AI providers failed: " + msg)
    raise NoAIKey("No AI API key set. Add a Gemini, NVIDIA, OpenRouter or OpenAI-compatible key in Settings.")


def parse_json(text):
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    start = min([i for i in (text.find("{"), text.find("[")) if i >= 0] or [0])
    return json.loads(text[start:])


SELECT_PROMPT = """You are an expert short-form video editor who clips long podcasts and streams into viral TikToks.

Below is a timestamped transcript of "{title}" ({minutes} minutes long).
Pick the {n} BEST moments to turn into separate vertical clips.

Rules for every clip:
- Length between {min_s} and {max_s} seconds.
- It must make sense on its own with no context: a clear setup and a payoff (punchline, reveal, shocking line, big reaction).
- Start right where the setup begins (not mid-sentence) and end shortly after the payoff/laugh. Never cut off the payoff.
- Prefer funny, surprising, relatable or controversial-but-safe moments that make people comment and share.
- Skip ad reads/sponsor segments, intros/outros, and anything about death, violence, tragedy or real politics unless it's clearly comedic.
- Clips must not overlap.
{source_notes}{custom}{avoid}

For each clip return:
- "start" and "end": seconds from the start of the video (numbers, use the transcript timestamps).
- "punchline": the second where the biggest moment (punchline / reveal) lands. This gets a flash, zoom and impact sound.
- "title": a hook title shown on the video, max 50 characters, curiosity-driven, like a trending TikTok (e.g. "POV: a stranger Googles you mid-flight").
- "caption": the TikTok caption, 1 short punchy sentence with 1 emoji, no hashtags.
- "hashtags": 3-5 relevant hashtags (names of people involved, topic).
- "emphasis": 3-8 single words from the clip worth highlighting in yellow.
- "score": 1-100, how likely it is to go viral.
- "reason": one short sentence.

Return ONLY JSON in this form: {{"clips": [ {{...}}, ... ]}}

TRANSCRIPT:
{transcript}
"""


def select_moments(cfg_ai, cfg_edit, source, video, transcript_text, n, log=None, avoid=None):
    minutes = int((video.get("duration") or 0) // 60)
    notes = source.get("notes_for_ai") or ""
    prompt = SELECT_PROMPT.format(
        title=video.get("title", "video"), minutes=minutes, n=n,
        min_s=cfg_edit.get("min_seconds", 30), max_s=cfg_edit.get("max_seconds", 60),
        source_notes=f"- About this show: {notes}\n" if notes else "",
        custom=f"- Extra instructions from the owner: {cfg_ai.get('custom_instructions')}\n" if cfg_ai.get("custom_instructions") else "",
        avoid=("- Already clipped, do NOT pick these again: " + ", ".join(avoid) + "\n") if avoid else "",
        transcript=transcript_text)
    raw = ask(cfg_ai, prompt, json_mode=True)
    data = parse_json(raw)
    clips = data.get("clips", data) if isinstance(data, dict) else data
    out = []
    for c in clips:
        try:
            s, e = float(c["start"]), float(c["end"])
            if e <= s:
                continue
            out.append({
                "start": s, "end": e,
                "punch": float(c.get("punchline") or (s + (e - s) * 0.8)),
                "title": str(c.get("title", ""))[:60],
                "caption": str(c.get("caption", "")),
                "hashtags": [h if h.startswith("#") else "#" + h for h in (c.get("hashtags") or [])][:6],
                "emphasis": [str(w) for w in (c.get("emphasis") or [])][:10],
                "score": float(c.get("score") or 50),
                "reason": str(c.get("reason", "")),
            })
        except Exception:
            continue
    out.sort(key=lambda c: -c["score"])
    return out


def snap_to_words(clip, words, min_s, max_s):
    """Move clip edges onto real word boundaries so nothing starts or ends mid-word,
    and keep the length within limits."""
    if not words:
        return clip
    s, e = clip["start"], clip["end"]
    # start: first word that starts at/after s-0.5, but begin at a sentence start if one is close
    starts = [w for w in words if w["s"] >= s - 1.0]
    if starts:
        first = starts[0]
        for i, w in enumerate(words):
            if w is first:
                for j in range(i, min(i + 8, len(words))):
                    prev = words[j - 1]["w"] if j > 0 else "."
                    if prev.endswith((".", "?", "!")) and abs(words[j]["s"] - s) < 3:
                        first = words[j]
                        break
                break
        s = max(0.0, first["s"] - 0.15)
    ends = [w for w in words if w["e"] <= e + 1.5 and w["e"] > s]
    if ends:
        e = ends[-1]["e"] + 0.6  # leave a beat for the laugh
    if e - s > max_s:
        e = s + max_s
        inside = [w for w in words if s < w["e"] <= e]
        if inside:
            e = inside[-1]["e"] + 0.3
    if e - s < min_s:
        e = s + min_s
    clip["start"], clip["end"] = round(s, 2), round(e, 2)
    clip["punch"] = min(max(clip.get("punch", e - 3), s + 1), e - 0.5)
    return clip
