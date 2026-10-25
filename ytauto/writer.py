"""AI writing for the YouTube section: video ideas, scripts, titles, descriptions, tags, thumbnail text."""
import json

from agent import ai


def _ask_json(cfg_ai, prompt):
    return ai.parse_json(ai.ask(cfg_ai, prompt, json_mode=True))


def _channel_context(s):
    ch = s["channel"]
    bits = [f'Channel: "{ch.get("name") or "a new channel"}"', f'Genre: {s["genre"] or "general interest"}',
            f'Audience: {s["audience"]}', f'Language: {s["language"]}']
    if s.get("style_notes"):
        bits.append(f"Always follow: {s['style_notes']}")
    if s["ai"].get("custom_instructions"):
        bits.append(f"Owner's extra instructions: {s['ai']['custom_instructions']}")
    return "\n".join(bits)


def new_idea(s, kind, past_titles):
    """kind: 'long' or 'short'. Returns {title, hook, angle}."""
    past = "\n".join(f"- {t}" for t in past_titles[-60:]) or "(none yet)"
    prompt = f"""You run a faceless YouTube channel.
{_channel_context(s)}

Come up with ONE new {'long-form video (about %d minutes)' % s['long']['minutes'] if kind == 'long' else 'YouTube Short (under 60 seconds)'} idea
that fits the genre, has a strong curiosity hook, and is NOT a repeat of these past videos:
{past}

Rules: factual and accurate (no made-up facts presented as true, no fake news, no misleading claims), no hate,
no sexual content, no dangerous advice, nothing about real private people.
Return JSON: {{"title": "max 70 chars, curiosity-driven, no clickbait lies", "hook": "first sentence that grabs attention", "angle": "1-2 sentences on what the video covers"}}"""
    return _ask_json(s["ai"], prompt)


def script(s, kind, idea):
    """Returns {"segments": [{"text", "visual"}], "description", "tags", "thumbnail_text"}."""
    if kind == "long":
        words = int(s["long"]["minutes"] * 150)
        shape = (f"about {words} words split into 14-24 segments of 2-5 sentences. Segment 1 is the hook; "
                 "end with a short outro asking viewers to subscribe.")
    else:
        words = int(s["shorts"]["seconds"] * 2.6)
        shape = f"about {words} words split into 5-8 short segments. Hook in the first 2 seconds, no intro, punchy ending."
    chap_note = ('For long videos, put a "chapter" (2-5 word chapter title) on the first segment and on 4-7 later '
                 'segments where a new part begins.') if kind == "long" else ""
    prompt = f"""Write the narration for a faceless YouTube {'video' if kind == 'long' else 'Short'}.
{_channel_context(s)}
Title: {idea.get('title')}
Hook: {idea.get('hook')}
Angle: {idea.get('angle')}

Length: {shape}
Write how a great YouTube narrator talks: simple words, short sentences, curiosity loops, no filler, no stage directions,
no emojis, no "[music]" notes. Facts must be accurate; say "reportedly" when unsure.
For each segment also give "visual": 2-4 plain English words describing stock footage to show (e.g. "city at night", "old letters desk").
{chap_note}

Return JSON: {{
 "segments": [{{"text": "...", "visual": "...", "chapter": "optional"}}],
 "description": "YouTube description: 2 short paragraphs, natural keywords, no hashtags spam",
 "tags": ["10-15 search tags"],
 "thumbnail_text": "2-4 WORDS, ALL CAPS, emotional, not the same as the title"
}}"""
    out = _ask_json(s["ai"], prompt)
    segs = [x for x in out.get("segments", []) if str(x.get("text", "")).strip()]
    if not segs:
        raise ai.AIError("The AI returned an empty script")
    out["segments"] = segs
    return out


def repurpose_plan(s, kind, video, transcript_text, minutes):
    """For long-form repurposing: pick excerpts and write short narrated bridges (adds original commentary)."""
    prompt = f"""You edit a YouTube channel that makes highlight/commentary videos from source footage it has rights to use.
{_channel_context(s)}
Source video: "{video.get('title')}" by {video.get('uploader') or 'unknown'}.
Make a ~{minutes}-minute video: choose 4-8 of the strongest excerpts (30-120 s each, in order, no overlaps) and write
original narration between them that adds context and commentary (this is what makes the video yours).

Return JSON: {{
 "title": "max 70 chars",
 "intro": "narrated hook, 2-4 sentences",
 "parts": [{{"start": seconds, "end": seconds, "bridge": "1-3 sentences of narration said BEFORE this excerpt"}}],
 "outro": "1-2 sentences + subscribe ask",
 "description": "2 short paragraphs",
 "tags": ["10-15 tags"],
 "thumbnail_text": "2-4 WORDS, ALL CAPS"
}}

TRANSCRIPT:
{transcript_text}"""
    return _ask_json(s["ai"], prompt)


def short_meta(s, title, caption):
    return {"title": (title or caption or "")[:90], "description": caption or ""}
