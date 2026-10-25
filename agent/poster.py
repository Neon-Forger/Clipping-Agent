"""Browser automation for TikTok posting and Content Rewards submission.
Uses a separate, persistent Microsoft Edge profile owned by the agent: you sign in
to TikTok and Content Rewards once (Accounts tab -> "Sign in"), and it stays signed in.

Warning: automated posting is against TikTok's terms and can get an account
limited. Keep posting volume human-like (see posting settings)."""
import os
import random
import re
import time

from .config import data_dir


class NotLoggedIn(Exception):
    pass


def profile_dir():
    d = os.path.join(data_dir(), "browser-profile")
    os.makedirs(d, exist_ok=True)
    return d


def _launch(p, posting_cfg, headless=None):
    channel = posting_cfg.get("browser_channel") or None
    kw = dict(user_data_dir=profile_dir(), headless=posting_cfg.get("headless", False) if headless is None else headless,
              viewport={"width": 1366, "height": 900},
              args=["--disable-blink-features=AutomationControlled", "--mute-audio"])
    try:
        return p.chromium.launch_persistent_context(channel=channel, **kw)
    except Exception:
        # Edge not found: fall back to Chrome, then to Playwright's own Chromium
        for ch in ("chrome", None):
            try:
                return p.chromium.launch_persistent_context(channel=ch, **kw) if ch else p.chromium.launch_persistent_context(**kw)
            except Exception:
                continue
        raise


def _human_pause(a=0.6, b=1.6):
    time.sleep(random.uniform(a, b))


def open_for_login(posting_cfg, urls):
    """Opens the agent's browser so you can sign in. Returns when you close the window."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        ctx = _launch(p, posting_cfg, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(urls[0])
        for u in urls[1:]:
            ctx.new_page().goto(u)
        while True:
            try:
                if not ctx.pages:
                    break
                time.sleep(1)
            except Exception:
                break
        try:
            ctx.close()
        except Exception:
            pass


def _video_links(page, sel):
    hrefs = page.eval_on_selector_all(sel, "els => els.map(e => e.href)")
    out = []
    for h in hrefs:
        if "/video/" in h and h not in out:
            out.append(h.split("?")[0])
    return out


def post_to_tiktok(video_path, caption, posting_cfg, sel, log):
    """Uploads and posts a video. Returns the new video's URL."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        ctx = _launch(p, posting_cfg)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_default_timeout(60000)
        try:
            page.goto(sel["tiktok_content_url"], wait_until="domcontentloaded")
            _human_pause(3, 5)
            if "login" in page.url:
                raise NotLoggedIn("TikTok is signed out in the agent's browser. Open the agent on the PC and use Accounts -> Sign in.")
            known = set(_video_links(page, sel["tiktok_video_link"]))

            page.goto(sel["tiktok_upload_url"], wait_until="domcontentloaded")
            _human_pause(3, 5)
            if "login" in page.url:
                raise NotLoggedIn("TikTok is signed out in the agent's browser.")
            page.locator(sel["tiktok_file_input"]).first.set_input_files(os.path.abspath(video_path))
            log("info", "Uploading video to TikTok...")

            # wait for the upload to finish
            deadline = time.time() + 900
            while time.time() < deadline:
                txt = page.locator("[data-e2e=upload_status_container]").first.inner_text(timeout=5000) \
                    if page.locator("[data-e2e=upload_status_container]").count() else ""
                if sel.get("tiktok_uploaded_text", "Uploaded") in txt:
                    break
                time.sleep(2)
            else:
                raise RuntimeError("TikTok upload did not finish within 15 minutes")
            _human_pause(1.5, 3)

            # caption
            ed = page.locator(sel["tiktok_caption_editor"]).first
            ed.click()
            page.keyboard.press("Control+A")
            page.keyboard.press("Delete")
            _human_pause(0.3, 0.8)
            for token in re.split(r"(\s+)", caption):
                if not token:
                    continue
                if token.startswith("#"):
                    page.keyboard.type(token, delay=random.randint(40, 90))
                    _human_pause(1.2, 1.8)  # let the hashtag suggestion box settle
                    page.keyboard.press("Space")
                    _human_pause(0.3, 0.6)
                elif token.isspace():
                    if "\n" in token:
                        page.keyboard.press("Shift+Enter")
                    else:
                        page.keyboard.type(" ")
                else:
                    page.keyboard.type(token, delay=random.randint(25, 60))
            page.keyboard.press("Escape")
            _human_pause(2, 4)

            # wait for the post button to be usable, then post
            btn = page.locator(sel["tiktok_post_button"]).first
            for _ in range(60):
                dis = btn.get_attribute("aria-disabled") == "true" or btn.is_disabled()
                if not dis:
                    break
                time.sleep(2)
            btn.scroll_into_view_if_needed()
            _human_pause(1, 2)
            btn.click()
            log("info", "Clicked Post")
            # some accounts get an extra "Post now" confirmation (e.g. while checks are still running)
            for _ in range(8):
                time.sleep(2)
                for label in ("Post now", "Post anyway", "Continue"):
                    b = page.get_by_role("button", name=label)
                    if b.count() and b.first.is_visible():
                        b.first.click()
                        log("info", f"Confirmed: {label}")
                        break
                if "content" in page.url and "upload" not in page.url:
                    break

            # find the new video's link
            deadline = time.time() + 420
            while time.time() < deadline:
                page.goto(sel["tiktok_content_url"], wait_until="domcontentloaded")
                time.sleep(6)
                links = _video_links(page, sel["tiktok_video_link"])
                new = [l for l in links if l not in known]
                if new:
                    return new[0]
                time.sleep(15)
            raise RuntimeError("Posted, but couldn't find the new video's link on TikTok Studio")
        finally:
            try:
                ctx.close()
            except Exception:
                pass


def submit_to_content_rewards(campaign_url, tiktok_url, posting_cfg, sel, log):
    """Submits the link to a campaign and checks it appears in Submissions. Returns a status string."""
    from playwright.sync_api import sync_playwright
    vid = tiktok_url.rstrip("/").split("/")[-1]
    with sync_playwright() as p:
        ctx = _launch(p, posting_cfg)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_default_timeout(45000)
        try:
            page.goto(campaign_url, wait_until="domcontentloaded")
            _human_pause(4, 6)
            if "login" in page.url or "sign" in page.url:
                raise NotLoggedIn("Content Rewards is signed out in the agent's browser. Use Accounts -> Sign in on the PC.")
            btns = page.get_by_role("button", name=sel.get("cr_submit_button_text", "Submit clip"))
            clicked = False
            for i in range(btns.count()):
                if btns.nth(i).is_visible():
                    btns.nth(i).click()
                    clicked = True
                    break
            if not clicked:
                raise RuntimeError("Couldn't find the 'Submit clip' button (have you joined this campaign?)")
            dlg = page.locator(sel["cr_dialog"]).first
            dlg.wait_for(state="visible")
            _human_pause()
            inp = dlg.locator(sel["cr_link_input"]).first
            inp.click()
            inp.fill(tiktok_url)
            _human_pause(2, 3)
            box = dlg.locator("input[type=checkbox]")
            if box.count() and not box.first.is_checked():
                try:
                    box.first.check(force=True)
                except Exception:
                    dlg.locator("label:has(input[type=checkbox])").first.click()
            _human_pause(1, 2)
            submit = dlg.get_by_role("button", name=sel.get("cr_submit_button_text", "Submit clip")).last
            for _ in range(20):
                if submit.get_attribute("aria-disabled") != "true":
                    break
                time.sleep(1)
            problems = dlg.inner_text()
            if submit.get_attribute("aria-disabled") == "true":
                raise RuntimeError("Content Rewards wouldn't accept the link: " + " ".join(problems.split())[:300])
            submit.click()
            log("info", "Submitted link on Content Rewards")
            time.sleep(6)
            msg = ""
            if dlg.is_visible():
                msg = " ".join(dlg.inner_text().split())[:300]
            # verify
            page.goto(sel["cr_submissions_url"], wait_until="domcontentloaded")
            for _ in range(6):
                time.sleep(5)
                html = page.content()
                if vid in html:
                    return "verified"
                page.reload(wait_until="domcontentloaded")
            return "submitted (not visible in Submissions yet)" + (f": {msg}" if msg else "")
        finally:
            try:
                ctx.close()
            except Exception:
                pass
