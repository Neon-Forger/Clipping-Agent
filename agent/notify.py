"""Phone link through ntfy (https://ntfy.sh).
- Agent -> phone: messages on <topic>
- Phone -> agent: commands on <topic>-cmd
Messages whose title starts with "__" carry JSON for the phone app (state, settings)."""
import json
import threading
import time

import requests


class Ntfy:
    def __init__(self, settings, log=None):
        self.settings = settings
        self.log = log or (lambda *a: None)
        self._stop = threading.Event()
        self._handled = set()

    @property
    def cfg(self):
        return self.settings["ntfy"]

    def _headers(self):
        h = {}
        if self.cfg.get("token"):
            h["Authorization"] = f"Bearer {self.cfg['token']}"
        return h

    def send(self, message, title=None, tags=None, priority=3, click=None, level="normal"):
        lvl = self.cfg.get("notify_level", "normal")
        if lvl == "quiet" and level not in ("important",):
            return
        if lvl == "normal" and level == "verbose":
            return
        body = {"topic": self.cfg["topic"], "message": message[:3900], "priority": priority}
        if title:
            body["title"] = title
        if tags:
            body["tags"] = tags
        if click:
            body["click"] = click
        try:
            requests.post(self.cfg["server"].rstrip("/"), json=body, headers=self._headers(), timeout=20)
        except Exception as e:
            self.log("warn", f"ntfy send failed: {e}")

    def send_data(self, kind, data):
        """Structured data for the phone app (not shown as a notification there)."""
        body = {"topic": self.cfg["topic"], "title": f"__{kind}__", "message": json.dumps(data, separators=(",", ":"))[:3950],
                "priority": 1, "tags": ["robot"]}
        try:
            requests.post(self.cfg["server"].rstrip("/"), json=body, headers=self._headers(), timeout=20)
        except Exception as e:
            self.log("warn", f"ntfy send failed: {e}")

    def listen(self, on_command, state_store):
        """Blocking loop: reads commands sent from the phone and calls on_command(text)."""
        while not self._stop.is_set():
            # resume after the last command we handled (unix time); with none, only new messages arrive
            last_t = state_store.get("last_cmd_time")
            url = f"{self.cfg['server'].rstrip('/')}/{self.cfg['topic']}-cmd/json"
            if last_t:
                url += f"?since={int(last_t) + 1}"
            try:
                with requests.get(url, headers=self._headers(), stream=True, timeout=(15, 90)) as r:
                    r.raise_for_status()
                    for line in r.iter_lines(decode_unicode=True):
                        if self._stop.is_set():
                            return
                        if not line:
                            continue
                        try:
                            msg = json.loads(line)
                        except Exception:
                            continue
                        if msg.get("event") != "message":
                            continue
                        if msg.get("id") in self._handled:
                            continue
                        self._handled.add(msg.get("id"))
                        state_store["last_cmd_time"] = msg.get("time") or time.time()
                        text = (msg.get("message") or "").strip()
                        if text:
                            try:
                                on_command(text)
                            except Exception as e:
                                self.send(f"Command failed: {e}", title="⚠️ Error", tags=["warning"])
            except requests.exceptions.ReadTimeout:
                continue
            except Exception as e:
                self.log("warn", f"ntfy listen error: {e}")
                time.sleep(10)

    def stop(self):
        self._stop.set()
