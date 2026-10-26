"""Settings: stored as JSON in the app data folder. Every field can be edited
from the PC app, by hand in settings.json, or from the phone with `set <key> <value>`."""
import copy
import json
import os
import secrets
import sys
import threading

APP_NAME = "ClipCartelAgent"


def data_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share")
    d = os.path.join(base, APP_NAME)
    os.makedirs(d, exist_ok=True)
    return d


def default_output_dir():
    return os.path.join(os.path.expanduser("~"), "Videos", "ClipCartel")


DEFAULTS = {
    "paused": False,
    # ---- where clips come from ----
    "sources": [
        {
            "name": "2 Bears 1 Cave",
            "enabled": True,
            # A YouTube channel/playlist to watch for NEW videos, and/or fixed video links.
            "channel_url": "https://www.youtube.com/@YMHStudios/videos",
            "video_urls": [],
            "title_must_contain": "2 Bears, 1 Cave",
            "only_newer_than_days": 4,
            # The Content Rewards campaign the clips are submitted to.
            "campaign_url": "https://contentrewards.com/c/campaigns/295e9879-4464-4a31-975d-1c7b3a80d359",
            "required_hashtags": ["#2BearsWeekly"],
            "extra_hashtags": ["#bertkreischer", "#tomsegura", "#2bears1cave", "#comedy", "#fyp"],
            "notes_for_ai": "Comedy podcast. Skip sad, violent or political segments and ad reads.",
            "caption_extra": "",
            "clips_per_video": 6,
        }
    ],
    "check_sources_every_minutes": 60,
    # ---- AI ----
    "ai": {
        "provider_order": ["gemini", "nvidia", "openrouter", "openai_compatible"],
        "first": "",                  # provider to try first (blank = provider_order)
        "gemini_api_key": "",
        "gemini_model": "auto",       # "auto" picks the newest available flash model
        "nvidia_api_key": "",         # free key from build.nvidia.com (starts with nvapi-)
        "nvidia_model": "auto",       # "auto" picks a good chat model the key can use
        "openrouter_api_key": "",
        "openrouter_model": "openrouter/auto",
        "openai_compatible_base_url": "https://api.openai.com/v1",
        "openai_compatible_api_key": "",
        "openai_compatible_model": "gpt-4o-mini",
        "custom_instructions": "",
    },
    "transcribe": {"model": "small.en", "device": "auto", "compute_type": "int8"},
    # ---- editing ----
    "edit": {
        "min_seconds": 30,
        "max_seconds": 60,
        "style": "dramatic",          # "dramatic" (flashes, zooms, impact sounds) or "clean"
        "censor_swears": True,
        "caption_font_size": 82,
        "hook_font_size": 80,
        "progress_bar": True,
        "sound_effects": True,
        "zoom_focus_y": 0.44,
        "video_crf": 19,
        "max_upload_mb": 0,           # 0 = no limit; otherwise re-encode down to this size
    },
    "output_dir": default_output_dir(),
    "delete_source_after_render": True,   # delete the downloaded full episode once its clips are made
    # ---- posting ----
    "posting": {
        "auto_post": True,
        "min_minutes_between_posts": 180,
        "max_posts_per_day": 5,
        "quiet_hours_start": 0,       # no posting from 00:00 ...
        "quiet_hours_end": 5,         # ... until 05:00 (local time)
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "browser": "opera_gx",        # opera_gx | edge | chrome | full path to a Chromium-based browser .exe
        "headless": False,
        "submit_to_content_rewards": True,
        "submit_within_minutes": 25,  # Content Rewards only accepts links < 30 min old
    },
    # ---- phone (ntfy) ----
    "ntfy": {
        "server": "https://ntfy.sh",
        "topic": "",                  # generated on first run; the phone app uses the same topic
        "pair_code": "",              # generated on first run; encrypts sign-ins sent from the phone (never sent over ntfy)
        "token": "",                  # optional access token for a protected / self-hosted server
        "notify_level": "normal",     # "quiet" | "normal" | "verbose"
    },
    "start_with_windows": False,
    "keep_pc_awake": True,
    # Advanced: page selectors, editable if TikTok / Content Rewards change their sites.
    "selectors": {
        "tiktok_upload_url": "https://www.tiktok.com/tiktokstudio/upload",
        "tiktok_content_url": "https://www.tiktok.com/tiktokstudio/content",
        "tiktok_file_input": "input[type=file][accept='video/*']",
        "tiktok_caption_editor": ".public-DraftEditor-content",
        "tiktok_uploaded_text": "Uploaded",
        "tiktok_post_button": "[data-e2e=post_video_button]",
        "tiktok_video_link": "a[href*='/video/']",
        "cr_submit_button_text": "Submit clip",
        "cr_dialog": "[role=dialog][aria-label='Submit clip']",
        "cr_link_input": "input[type=url]",
        "cr_submissions_url": "https://contentrewards.com/c/submissions",
    },
}

SECRET_KEYS = {"gemini_api_key", "nvidia_api_key", "openrouter_api_key", "openai_compatible_api_key", "token", "pair_code",
               "pexels_api_key", "pixabay_api_key", "unsplash_access_key"}

_lock = threading.RLock()


def _merge(base, extra):
    out = copy.deepcopy(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


class Settings:
    def __init__(self, path=None, defaults=None):
        self.defaults = defaults if defaults is not None else DEFAULTS
        self.path = path or os.path.join(data_dir(), "settings.json")
        self.data = copy.deepcopy(self.defaults)
        self.load()

    def load(self):
        with _lock:
            if os.path.exists(self.path):
                try:
                    with open(self.path, "r", encoding="utf-8") as f:
                        self.data = _merge(self.defaults, json.load(f))
                except Exception:
                    pass
            if self.after_load():
                self.save()

    def after_load(self):
        """Fix-ups after loading; returns True if something changed and should be saved."""
        changed = self._fix_ai_boxes()
        if "ai" in self.data:
            if self.data["ai"].get("gemini_model") in ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"):
                self.data["ai"]["gemini_model"] = "auto"
                changed = True
            if self.data["ai"].get("openrouter_model") == "google/gemini-2.5-flash":
                self.data["ai"]["openrouter_model"] = "openrouter/auto"
                changed = True
        if "ntfy" in self.data:
            if not self.data["ntfy"].get("topic"):
                self.data["ntfy"]["topic"] = "clipcartel-" + secrets.token_hex(6)
                changed = True
            if not self.data["ntfy"].get("pair_code"):
                alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
                code = "".join(secrets.choice(alphabet) for _ in range(8))
                self.data["ntfy"]["pair_code"] = code[:4] + "-" + code[4:]
                changed = True
        return changed

    def save(self):
        with _lock:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            os.replace(tmp, self.path)

    def __getitem__(self, k):
        return self.data[k]

    def get(self, dotted, default=None):
        cur = self.data
        for part in dotted.split("."):
            if isinstance(cur, list):
                try:
                    cur = cur[int(part)]
                    continue
                except Exception:
                    return default
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

    def set(self, dotted, value, raw=False):
        """Set a value by dotted path, e.g. `posting.max_posts_per_day` or `sources.0.enabled`.
        Strings are parsed as JSON when possible (numbers, true/false, lists)."""
        if isinstance(value, str) and not raw:
            try:
                value = json.loads(value)
            except Exception:
                pass
        with _lock:
            parts = dotted.split(".")
            cur = self.data
            for p in parts[:-1]:
                if isinstance(cur, list):
                    cur = cur[int(p)]
                else:
                    cur = cur.setdefault(p, {})
            last = parts[-1]
            if isinstance(cur, list):
                cur[int(last)] = value
            else:
                cur[last] = value
            if parts[0] == "ai":
                self._fix_ai_boxes()
            self.save()
        return value

    def _fix_ai_boxes(self):
        """Moves API keys pasted into the wrong box to the right one (returns True if anything moved)."""
        a = self.data.get("ai")
        if not isinstance(a, dict):
            return False
        changed = False
        first = str(a.get("first") or "").strip()
        if first and first.lower() not in ("gemini", "nvidia", "openrouter", "openai_compatible"):
            if first.startswith("nvapi-") and not a.get("nvidia_api_key"):
                a["nvidia_api_key"] = first
            a["first"] = "nvidia" if first.startswith("nvapi-") else ""
            changed = True
        other = str(a.get("openai_compatible_api_key") or "").strip()
        default_url = str(a.get("openai_compatible_base_url") or "https://api.openai.com/v1").rstrip("/") == "https://api.openai.com/v1"
        for prefix, field in (("nvapi-", "nvidia_api_key"), ("sk-or-", "openrouter_api_key")):
            if other.startswith(prefix) and default_url:
                if not a.get(field):
                    a[field] = other
                a["openai_compatible_api_key"] = ""
                changed = True
        for k in ("gemini_api_key", "nvidia_api_key", "openrouter_api_key", "openai_compatible_api_key"):
            if isinstance(a.get(k), str) and a[k] != a[k].strip():
                a[k] = a[k].strip()
                changed = True
        return changed

    def replace_all(self, new_data):
        with _lock:
            # keep secrets the phone never saw (they arrive masked)
            merged = _merge(self.defaults, new_data)
            _restore_secrets(merged, self.data)
            self.data = merged
            self.save()

    def masked(self):
        return _mask(copy.deepcopy(self.data))


def _mask(d):
    if isinstance(d, dict):
        for k, v in d.items():
            if k in SECRET_KEYS and isinstance(v, str) and v:
                d[k] = "••••" + v[-4:]
            else:
                _mask(v)
    elif isinstance(d, list):
        for v in d:
            _mask(v)
    return d


def _restore_secrets(new, old):
    if isinstance(new, dict) and isinstance(old, dict):
        for k, v in new.items():
            if k in SECRET_KEYS and isinstance(v, str) and v.startswith("••••"):
                new[k] = old.get(k, "")
            else:
                _restore_secrets(v, old.get(k))


def resource_path(*parts):
    """Path to bundled files (works both from source and from the packaged .exe)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, *parts)
