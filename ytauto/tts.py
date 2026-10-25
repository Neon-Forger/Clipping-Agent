"""Voiceover with Microsoft Edge's free neural voices (edge-tts), with word timings for captions."""
import asyncio

TICKS = 10_000_000  # edge-tts reports time in 100-nanosecond units


async def _speak(text, voice, rate, out_path):
    import edge_tts
    try:
        com = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    except TypeError:  # older edge-tts
        com = edge_tts.Communicate(text, voice, rate=rate)
    words = []
    with open(out_path, "wb") as f:
        async for chunk in com.stream():
            t = chunk.get("type")
            if t == "audio":
                f.write(chunk["data"])
            elif t == "WordBoundary":
                s = chunk["offset"] / TICKS
                words.append({"s": round(s, 3), "e": round(s + chunk["duration"] / TICKS, 3), "w": chunk["text"]})
    return words


def speak(text, voice, rate, out_path):
    """Writes an mp3 and returns word timings [{s, e, w}] in seconds."""
    for attempt in range(3):
        try:
            return asyncio.run(_speak(text, voice, rate, out_path))
        except Exception:
            if attempt == 2:
                raise
    return []


def list_voices(lang_prefix="en-"):
    import edge_tts

    async def go():
        return await edge_tts.list_voices()
    return sorted(v["ShortName"] for v in asyncio.run(go()) if v["ShortName"].startswith(lang_prefix))
