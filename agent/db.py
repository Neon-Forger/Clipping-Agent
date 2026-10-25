"""Small SQLite store so the agent can stop/restart without losing track of anything."""
import json
import os
import sqlite3
import threading
import time

from .config import data_dir

_SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
  id TEXT PRIMARY KEY,          -- e.g. youtube video id
  source TEXT, url TEXT, title TEXT, duration REAL,
  status TEXT,                  -- new, downloaded, transcribed, selected, done, failed, skipped
  path TEXT, transcript TEXT, error TEXT,
  created REAL, updated REAL
);
CREATE TABLE IF NOT EXISTS clips (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id TEXT, source TEXT, start REAL, end REAL, punch REAL,
  title TEXT, caption TEXT, emphasis TEXT, score REAL, reason TEXT,
  file TEXT,
  status TEXT,                  -- planned, rendered, posting, posted, submitted, failed, skipped
  tiktok_url TEXT, posted_at REAL, submitted_at REAL, submit_result TEXT, error TEXT,
  created REAL, updated REAL
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, level TEXT, text TEXT
);
"""


class DB:
    def __init__(self, path=None):
        self.path = path or os.path.join(data_dir(), "agent.db")
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        with self._lock:
            self.conn.executescript(_SCHEMA)
            self.conn.commit()

    def q(self, sql, args=()):
        with self._lock:
            return [dict(r) for r in self.conn.execute(sql, args).fetchall()]

    def x(self, sql, args=()):
        with self._lock:
            cur = self.conn.execute(sql, args)
            self.conn.commit()
            return cur.lastrowid

    # ---- videos ----
    def add_video(self, vid, source, url, title, duration=None):
        if self.q("SELECT 1 FROM videos WHERE id=?", (vid,)):
            return False
        now = time.time()
        self.x("INSERT INTO videos (id,source,url,title,duration,status,created,updated) VALUES (?,?,?,?,?,?,?,?)",
               (vid, source, url, title, duration, "new", now, now))
        return True

    def video(self, vid):
        r = self.q("SELECT * FROM videos WHERE id=?", (vid,))
        return r[0] if r else None

    def update_video(self, vid, **kw):
        kw["updated"] = time.time()
        cols = ",".join(f"{k}=?" for k in kw)
        self.x(f"UPDATE videos SET {cols} WHERE id=?", (*kw.values(), vid))

    # ---- clips ----
    def add_clip(self, **kw):
        now = time.time()
        kw.setdefault("status", "planned")
        if isinstance(kw.get("emphasis"), (list, tuple)):
            kw["emphasis"] = json.dumps(kw["emphasis"])
        kw["created"] = kw["updated"] = now
        cols = ",".join(kw)
        return self.x(f"INSERT INTO clips ({cols}) VALUES ({','.join('?' * len(kw))})", tuple(kw.values()))

    def clip(self, cid):
        r = self.q("SELECT * FROM clips WHERE id=?", (cid,))
        return r[0] if r else None

    def update_clip(self, cid, **kw):
        kw["updated"] = time.time()
        cols = ",".join(f"{k}=?" for k in kw)
        self.x(f"UPDATE clips SET {cols} WHERE id=?", (*kw.values(), cid))

    def clips(self, status=None, limit=200):
        if status:
            return self.q("SELECT * FROM clips WHERE status=? ORDER BY score DESC, id LIMIT ?", (status, limit))
        return self.q("SELECT * FROM clips ORDER BY id DESC LIMIT ?", (limit,))

    def posts_since(self, ts):
        return self.q("SELECT * FROM clips WHERE posted_at IS NOT NULL AND posted_at>=?", (ts,))

    def last_post_time(self):
        r = self.q("SELECT MAX(posted_at) AS t FROM clips")
        return r[0]["t"] or 0

    # ---- events ----
    def log(self, level, text):
        self.x("INSERT INTO events (ts,level,text) VALUES (?,?,?)", (time.time(), level, text))

    def events(self, limit=200):
        return self.q("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))

    def counts(self):
        out = {}
        for r in self.q("SELECT status, COUNT(*) AS n FROM clips GROUP BY status"):
            out[r["status"]] = r["n"]
        return out
