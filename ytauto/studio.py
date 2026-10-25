"""YouTube Studio automation in the YouTube section's own browser profile (separate from Clipping).
Sign-in happens in a normal browser window so Google allows it; uploads reuse that signed-in profile."""
import re
import time

from agent import poster

PREFIX = "yt-profile"   # browser profile kept apart from the Clipping section


class NotSignedIn(Exception):
    pass


def browser_cfg(s):
    up = s["upload"]
    return {"browser": up.get("browser", "opera_gx"), "headless": up.get("headless", False)}


def sign_in(s, log=None, also_create=False):
    """Opens a normal browser window on YouTube so you can sign in with Google (and create/pick a channel)."""
    urls = ["https://accounts.google.com/ServiceLogin?service=youtube&continue=https://www.youtube.com/"]
    if also_create:
        urls.append("https://www.youtube.com/create_channel")
    else:
        urls.append("https://www.youtube.com/channel_switcher")
    return poster.open_plain(browser_cfg(s), urls, prefix=PREFIX, log=log)


def open_page(s, url, log=None):
    return poster.open_plain(browser_cfg(s), [url], prefix=PREFIX, log=log)


def _ctx(p, s, log=None, headless=None):
    return poster._launch(p, browser_cfg(s), headless=headless, log=log, prefix=PREFIX)


def current_channel(s, log=None):
    """Returns {"id", "name"} of the channel Studio opens on, or raises NotSignedIn."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        ctx = _ctx(p, s, log)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto("https://studio.youtube.com/", wait_until="domcontentloaded", timeout=90000)
            for _ in range(30):
                if "accounts.google.com" in page.url:
                    raise NotSignedIn("Not signed in to YouTube yet.")
                m = re.search(r"/channel/(UC[\w-]{20,})", page.url)
                if m:
                    break
                time.sleep(1)
            else:
                raise RuntimeError("YouTube Studio didn't open a channel (does this Google account have a channel?)")
            time.sleep(3)
            name = ""
            for sel in ("#entity-name", "ytcp-navigation-drawer #entity-name", "#channel-title"):
                loc = page.locator(sel)
                if loc.count():
                    name = loc.first.inner_text().strip()
                    if name:
                        break
            return {"id": m.group(1), "name": name}
        finally:
            ctx.close()


def _click_if(page, selector, timeout=4000):
    loc = page.locator(selector)
    try:
        if loc.count():
            loc.first.click(timeout=timeout)
            return True
    except Exception:
        pass
    return False


def _type_box(page, selector, text):
    box = page.locator(selector).first
    box.click()
    page.keyboard.press("Control+A")
    page.keyboard.press("Delete")
    page.keyboard.insert_text(text)


def upload(s, video_path, title, description, tags=None, thumbnail=None, log=None, short=False):
    """Uploads and publishes a video. Returns its URL."""
    from playwright.sync_api import sync_playwright
    sel = s["selectors"]
    up = s["upload"]
    ch = s["channel"].get("channel_id")
    log = log or (lambda *a: None)
    with sync_playwright() as p:
        ctx = _ctx(p, s, log)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.set_default_timeout(60000)
            url = f"https://studio.youtube.com/channel/{ch}/videos/upload?d=ud" if ch else sel["upload_url"]
            page.goto(url, wait_until="domcontentloaded")
            time.sleep(6)
            if "accounts.google.com" in page.url:
                raise NotSignedIn("YouTube is signed out. Open NeonClip → YouTube → Channel → Sign in.")
            if ch and ch not in page.url:
                log("warn", "Studio opened a different channel than the one selected; uploading to the selected one may fail.")
            page.locator(sel["file_input"]).first.set_input_files(video_path)
            log("info", "Uploading to YouTube...")
            page.locator(sel["title_box"]).first.wait_for(state="visible", timeout=180000)
            time.sleep(2)
            _type_box(page, sel["title_box"], title[:100])
            time.sleep(1)
            _type_box(page, sel["description_box"], description[:4900])
            if thumbnail and not short:
                try:
                    page.locator(sel["thumbnail_input"]).first.set_input_files(thumbnail)
                    time.sleep(3)
                except Exception as e:
                    log("warn", f"Couldn't set the thumbnail (custom thumbnails need a phone-verified channel): {e}")
            _click_if(page, sel["for_kids"] if up.get("made_for_kids") else sel["not_for_kids"])
            if _click_if(page, sel["show_more"]):
                time.sleep(1)
            _click_if(page, sel["altered_yes"] if up.get("altered_content") else sel["altered_no"])
            if tags:
                try:
                    tin = page.locator(sel["tags_input"]).first
                    tin.click(timeout=5000)
                    tin.type(",".join(t.replace(",", " ") for t in tags)[:480] + ",", delay=10)
                except Exception:
                    pass
            for _ in range(3):
                page.locator(sel["next_button"]).first.click()
                time.sleep(2)
            vis = {"public": "PUBLIC", "unlisted": "UNLISTED", "private": "PRIVATE"}.get(up.get("visibility", "public"), "PUBLIC")
            page.locator(sel["visibility_radio"].replace("{VIS}", vis)).first.click()
            time.sleep(1)
            # wait for the upload itself to finish before publishing
            started = time.time()
            deadline = started + 3600
            while time.time() < deadline:
                txt = ""
                for q in ("ytcp-video-upload-progress", ".progress-label", "#dialog .footer"):
                    loc = page.locator(q)
                    if loc.count():
                        try:
                            txt += " " + loc.first.inner_text(timeout=2000)
                        except Exception:
                            pass
                low = txt.lower()
                if any(k in low for k in ("upload complete", "processing", "checks complete", "finished processing")):
                    break
                if not low.strip() and time.time() - started > 60:
                    break  # no progress bar found; Studio usually lets you publish anyway
                if "%" not in low and "upload" not in low and time.time() - started > 60:
                    break
                time.sleep(5)
            link = ""
            for q in (sel["video_link"], "a[href*='youtu.be/']", "a[href*='/shorts/']"):
                loc = page.locator(q)
                if loc.count():
                    link = loc.first.get_attribute("href") or ""
                    if link:
                        break
            page.locator(sel["done_button"]).first.click()
            time.sleep(6)
            for q in ("a#share-url", "a[href*='youtu.be/']"):
                loc = page.locator(q)
                if loc.count():
                    link = loc.first.get_attribute("href") or link
                    break
            _click_if(page, "#close-button, ytcp-button#close-button")
            if not link:
                raise RuntimeError("Published, but couldn't read the video link")
            return link
        finally:
            try:
                ctx.close()
            except Exception:
                pass


def set_branding(s, avatar=None, banner=None, log=None):
    """Best effort: uploads the profile picture and banner on Studio → Customization → Branding."""
    from playwright.sync_api import sync_playwright
    ch = s["channel"].get("channel_id")
    if not ch:
        raise RuntimeError("Pick your channel first")
    log = log or (lambda *a: None)
    with sync_playwright() as p:
        ctx = _ctx(p, s, log)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(f"https://studio.youtube.com/channel/{ch}/editing/images", wait_until="domcontentloaded", timeout=90000)
            time.sleep(8)
            inputs = page.locator("input[type=file]")
            done_any = False
            for i, f in ((0, avatar), (1, banner)):
                if not f or inputs.count() <= i:
                    continue
                inputs.nth(i).set_input_files(f)
                time.sleep(5)
                _click_if(page, "#done-button, ytcp-button#done-button")
                time.sleep(3)
                done_any = True
            if done_any:
                if not _click_if(page, "#publish-button, ytcp-button#publish-button"):
                    raise RuntimeError("Couldn't find Publish on the branding page")
                time.sleep(5)
            return done_any
        finally:
            ctx.close()
