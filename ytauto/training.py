"""Training mode: learns which of your videos do best and steers new videos toward what works.

How it works
1. Every few hours it reads the public numbers (views, likes, comments) of every video on your channel,
   including ones NeonClip didn't make, using yt-dlp (no extra sign-in needed).
2. Each video gets a score: views adjusted for age (a 2-day-old video isn't compared with a 2-month-old one on raw
   views), with a small bonus for likes and comments.
3. The AI compares your best and worst videos (titles, topics, hooks, length, style, the brief and visual plan
   NeonClip used) and writes a playbook: what to do more, what to avoid, topics to make next.
4. With training ON, every new idea, script and visual plan follows that playbook, and leans toward topics like your winners.
YouTube's private stats (watch time, retention, click-through) need Google's Analytics API and aren't used."""
import datetime as dt
import json
import math
import time

from agent import ai, sources


def score(views, likes, comments, uploaded_ts, now=None):
    now = now or time.time()
    age_h = max(6.0, (now - (uploaded_ts or now)) / 3600.0)
    engaged = (views or 0) + 20 * (likes or 0) + 40 * (comments or 0)
    return round(engaged / math.sqrt(age_h / 24.0), 1)


def _channel_videos(channel_id, limit=60):
    """Public list of the channel's uploads (videos + Shorts) with view counts."""
    out = {}
    for tab in ("videos", "shorts"):
        url = f"https://www.youtube.com/channel/{channel_id}/{tab}"
        try:
            with sources._ydl({"extract_flat": "in_playlist", "playlistend": limit, "skip_download": True}) as y:
                info = y.extract_info(url, download=False)
        except Exception:
            continue
        for e in info.get("entries") or []:
            if e and e.get("id"):
                out[e["id"]] = {"id": e["id"], "title": e.get("title") or "", "views": e.get("view_count"),
                                "kind": "short" if tab == "shorts" else "long", "url": e.get("url") or ""}
    return out


def _video_id(url):
    import re
    m = re.search(r"(?:shorts/|v=|youtu\.be/)([\w-]{11})", url or "")
    return m.group(1) if m else None


def refresh_stats(yt, log=None):
    """Updates views/likes/comments for NeonClip's uploads and the rest of the channel. Returns how many were read."""
    n = 0
    ch = yt.s["channel"].get("channel_id")
    listed = _channel_videos(ch) if ch else {}
    mine = {}
    for it in yt.q("SELECT * FROM items WHERE status='uploaded' AND url IS NOT NULL"):
        vid = _video_id(it["url"])
        if vid:
            mine[vid] = it
    for vid, it in mine.items():
        try:
            info = sources.video_info(f"https://www.youtube.com/watch?v={vid}")
        except Exception:
            info = {}
        views = info.get("view_count", (listed.get(vid) or {}).get("views"))
        if views is None:
            continue
        sc = score(views, info.get("like_count"), info.get("comment_count"), it.get("uploaded_at"))
        yt.update(it["id"], views=views, likes=info.get("like_count"), comments=info.get("comment_count"),
                  stats_at=time.time(), score=sc)
        n += 1
    # videos on the channel that NeonClip didn't make (or made before training existed)
    others = []
    for vid, v in list(listed.items())[:40]:
        if vid in mine:
            continue
        try:   # full info gives upload time + likes/comments, so old and new videos are compared fairly
            info = sources.video_info(f"https://www.youtube.com/watch?v={vid}")
            v.update(views=info.get("view_count", v.get("views")), likes=info.get("like_count"),
                     comments=info.get("comment_count"), uploaded=info.get("timestamp"))
        except Exception:
            pass
        if v.get("views") is None:
            continue
        v["score"] = score(v["views"], v.get("likes"), v.get("comments"), v.get("uploaded") or (time.time() - 30 * 86400))
        others.append(v)
    yt.state["channel_videos"] = others[:80]
    yt.state["stats_at"] = time.time()
    yt.save_state()
    if log:
        log("info", f"Training: read stats for {n} NeonClip video(s) and {len(others)} other channel video(s).")
    return n + len(others)


def leaderboard(yt, limit=10):
    rows = []
    for it in yt.q("SELECT * FROM items WHERE status='uploaded' AND views IS NOT NULL"):
        meta = {}
        try:
            meta = json.loads(it.get("meta") or "{}")
        except Exception:
            pass
        rows.append({"id": it["id"], "title": it["title"], "kind": it["kind"], "views": it["views"], "likes": it["likes"],
                     "comments": it["comments"], "score": it.get("score") or 0, "url": it["url"], "brief": it.get("brief"),
                     "meta": meta, "age_h": round((time.time() - (it.get("uploaded_at") or time.time())) / 3600, 1)})
    for v in yt.state.get("channel_videos") or []:
        age = round((time.time() - v["uploaded"]) / 3600, 1) if v.get("uploaded") else None
        rows.append({"id": None, "title": v["title"], "kind": v["kind"], "views": v["views"], "likes": v.get("likes"),
                     "comments": v.get("comments"), "score": v.get("score") or 0, "url": f"https://youtu.be/{v['id']}",
                     "brief": None, "meta": {}, "age_h": age})
    rows.sort(key=lambda r: -(r["score"] or 0))
    return rows[:limit] if limit else rows


LEARN_PROMPT = """You are a YouTube growth analyst for a faceless channel.
Channel genre: {genre}. Audience: {audience}.

Here are the channel's videos, best first, with a score (views adjusted for age, plus likes/comments) and what was used to make them.
{rows}

Compare the top third with the bottom third. Find what the winners have in common (topics, title wording, hook style,
length, Short vs long, tone, visual style) and what the losers share. Be concrete and specific to THESE videos;
don't give generic YouTube advice. If there's too little data, say so and keep advice modest.

Return JSON: {{
 "summary": "2-3 sentences on what's working and what isn't",
 "do": ["5-8 concrete things new videos should do"],
 "avoid": ["3-6 concrete things to stop doing"],
 "topics": ["6-10 specific new video topics similar to the winners (not repeats)"],
 "title_patterns": ["3-5 title templates modeled on the best titles"],
 "visual_notes": ["2-4 notes for the visual editor, only if the data supports them"],
 "confidence": "low | medium | high"
}}"""


def learn(yt, log=None):
    rows = leaderboard(yt, limit=0)
    if len([r for r in rows if r["views"] is not None]) < 4:
        raise RuntimeError("Training needs at least 4 videos with view counts. Upload a few more first.")
    lines = []
    for i, r in enumerate(rows[:40], 1):
        m = r["meta"] or {}
        bits = [f"{i}. score {r['score']:.0f} · {r['views']} views", r["kind"], f"\"{r['title']}\""]
        if r["age_h"] is not None:
            bits.append(f"{r['age_h']:.0f}h old")
        for k in ("hook", "angle", "style", "duration", "segments"):
            if m.get(k):
                bits.append(f"{k}: {str(m[k])[:120]}")
        if r.get("brief"):
            bits.append(f"brief: {r['brief'][:120]}")
        lines.append(" · ".join(str(b) for b in bits))
    s = yt.s
    data = ai.parse_json(ai.ask(s["ai"], LEARN_PROMPT.format(genre=s["genre"], audience=s["audience"], rows="\n".join(lines)),
                                json_mode=True))
    pb = {k: data.get(k) for k in ("summary", "do", "avoid", "topics", "title_patterns", "visual_notes", "confidence")}
    pb["learned_at"] = time.time()
    pb["videos"] = len(rows)
    pb["best"] = [{"title": r["title"], "views": r["views"]} for r in rows[:5]]
    s.set("training.playbook", pb)
    s.set("training.topics_used", [])
    if log:
        log("info", f"🧠 Training: learned from {len(rows)} videos. {pb.get('summary') or ''}", notify=True, title="🧠 Learned from your videos")
    return pb


def playbook_text(s, for_visuals=False):
    """The part of the playbook that goes into the AI prompts (empty when training is off)."""
    t = s.get("training") or {}
    pb = t.get("playbook") or {}
    if not t.get("enabled") or not pb:
        return ""
    if for_visuals:
        notes = pb.get("visual_notes") or []
        return ("What has worked on this channel (from its own stats): " + "; ".join(notes)) if notes else ""
    parts = ["LEARNED FROM THIS CHANNEL'S OWN STATS (follow unless the owner's request says otherwise):"]
    if pb.get("summary"):
        parts.append(pb["summary"])
    if pb.get("do"):
        parts.append("Do: " + "; ".join(pb["do"]))
    if pb.get("avoid"):
        parts.append("Avoid: " + "; ".join(pb["avoid"]))
    if pb.get("title_patterns"):
        parts.append("Title patterns that work: " + "; ".join(pb["title_patterns"]))
    if pb.get("best"):
        parts.append("Best videos so far: " + "; ".join(f"\"{b['title']}\" ({b['views']} views)" for b in pb["best"]))
    return "\n".join(parts)


def next_topic(s):
    """A suggested topic from the playbook that hasn't been used yet (training 'make more like the winners')."""
    t = s.get("training") or {}
    pb = t.get("playbook") or {}
    if not t.get("enabled"):
        return None
    used = set(t.get("topics_used") or [])
    for topic in pb.get("topics") or []:
        if topic not in used:
            s.set("training.topics_used", list(used | {topic}))
            return topic
    return None


def status_line(s):
    t = s.get("training") or {}
    pb = t.get("playbook") or {}
    if not t.get("enabled"):
        return "Training is off."
    if not pb:
        return "Training is on, waiting for enough video stats (needs 4+ uploaded videos)."
    when = dt.datetime.fromtimestamp(pb.get("learned_at", 0)).strftime("%b %d %I:%M %p")
    return f"Training is on · learned from {pb.get('videos', 0)} videos on {when} · confidence: {pb.get('confidence') or '?'}"
