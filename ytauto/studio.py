"""YouTube Studio automation in the YouTube section's own browser profile (separate from Clipping).
The browser runs as a normal browser (Google allows sign-in there); NeonClip drives it through a local
debugging port and only touches the tabs it opens itself."""
import re
import time

from agent import poster

PREFIX = "yt-profile"   # browser profile kept apart from the Clipping section


class NotSignedIn(Exception):
    pass


def browser_cfg(s):
    up = s["upload"]
    return {"browser": up.get("browser", "opera_gx"), "headless": up.get("headless", False)}


def _open_tabs(s, urls, log=None):
    """Opens tabs in the YouTube section's browser (a normal browser window you can use)."""
    from playwright.sync_api import sync_playwright
    port = poster.ensure_cdp_browser(browser_cfg(s), PREFIX, log)
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        ctx = b.contexts[0] if b.contexts else b.new_context()
        for u in urls:
            pg = ctx.new_page()
            try:
                pg.goto(u, wait_until="commit", timeout=30000)
            except Exception:
                pass
            try:
                pg.bring_to_front()
            except Exception:
                pass
    if log:
        log("info", "Browser open. Sign in / pick your channel there, then click \"Use the open channel\" (you can leave the window open).")
    return True


def sign_in(s, log=None, also_create=False):
    """Opens the YouTube section's browser on Google sign-in (and the channel picker / creator)."""
    urls = ["https://accounts.google.com/ServiceLogin?service=youtube&continue=https://www.youtube.com/"]
    urls.append("https://www.youtube.com/create_channel" if also_create else "https://www.youtube.com/channel_switcher")
    return _open_tabs(s, urls, log)


def open_page(s, url, log=None):
    return _open_tabs(s, [url], log)


def _ctx(p, s, log=None, headless=None):
    return poster.connect(p, browser_cfg(s), PREFIX, log)


def _wait_signed_in(page, timeout=40):
    """Google bounces through accounts.google.com even when you ARE signed in, and Studio may only redirect
    to sign-in after a moment. Signed in = Studio settles on a /channel/ page (or any non-Google page) for
    a few seconds; signed out = a Google sign-in / account-chooser page that stays put."""
    start = time.time()
    on_google_since = None
    while time.time() - start < timeout:
        page.wait_for_timeout(1000)   # also lets Playwright see the page's latest URL
        u = page.url
        if "accounts.google.com" in u:
            on_google_since = on_google_since or time.time()
            try:
                if page.locator("input[type=email], #identifierId").count():
                    return False
            except Exception:
                pass
            if time.time() - on_google_since > 15:   # account chooser etc.
                return False
            continue
        on_google_since = None
        if time.time() - start >= 4 and ("/channel/" in u or "studio.youtube.com" not in u):
            return True
    return "accounts.google.com" not in page.url


def current_channel(s, log=None):
    """Returns {"id", "name"} of the channel Studio opens on, or raises NotSignedIn."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        ctx = _ctx(p, s, log)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto("https://studio.youtube.com/", wait_until="domcontentloaded", timeout=90000)
            if not _wait_signed_in(page):
                raise NotSignedIn("Not signed in to YouTube in NeonClip's browser yet. Click \"Sign in to YouTube\", sign in, then try again.")
            for _ in range(30):
                m = re.search(r"/channel/(UC[\w-]{20,})", page.url)
                if m:
                    break
                page.wait_for_timeout(1 * 1000)
            else:
                raise RuntimeError("YouTube Studio didn't open a channel (does this Google account have a channel?)")
            page.wait_for_timeout(3 * 1000)
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
            page.wait_for_timeout(6 * 1000)
            if not _wait_signed_in(page):
                raise NotSignedIn("YouTube is signed out. Open NeonClip → YouTube → Channel → Sign in.")
            if "/channel/" not in page.url and ch:
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(5 * 1000)
            if ch and ch not in page.url:
                log("warn", "Studio opened a different channel than the one selected; uploading to the selected one may fail.")
            page.locator(sel["file_input"]).first.set_input_files(video_path)
            log("info", "Uploading to YouTube...")
            page.locator(sel["title_box"]).first.wait_for(state="visible", timeout=180000)
            page.wait_for_timeout(2 * 1000)
            _type_box(page, sel["title_box"], title[:100])
            page.wait_for_timeout(1 * 1000)
            _type_box(page, sel["description_box"], description[:4900])
            if thumbnail and not short:
                try:
                    page.locator(sel["thumbnail_input"]).first.set_input_files(thumbnail)
                    page.wait_for_timeout(3 * 1000)
                except Exception as e:
                    log("warn", f"Couldn't set the thumbnail (custom thumbnails need a phone-verified channel): {e}")
            _click_if(page, sel["for_kids"] if up.get("made_for_kids") else sel["not_for_kids"])
            if _click_if(page, sel["show_more"]):
                page.wait_for_timeout(1 * 1000)
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
                page.wait_for_timeout(2 * 1000)
            vis = {"public": "PUBLIC", "unlisted": "UNLISTED", "private": "PRIVATE"}.get(up.get("visibility", "public"), "PUBLIC")
            page.locator(sel["visibility_radio"].replace("{VIS}", vis)).first.click()
            page.wait_for_timeout(1 * 1000)
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
                page.wait_for_timeout(5 * 1000)
            link = ""
            for q in (sel["video_link"], "a[href*='youtu.be/']", "a[href*='/shorts/']"):
                loc = page.locator(q)
                if loc.count():
                    link = loc.first.get_attribute("href") or ""
                    if link:
                        break
            page.locator(sel["done_button"]).first.click()
            page.wait_for_timeout(6 * 1000)
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
            page.wait_for_timeout(8 * 1000)
            inputs = page.locator("input[type=file]")
            done_any = False
            for i, f in ((0, avatar), (1, banner)):
                if not f or inputs.count() <= i:
                    continue
                inputs.nth(i).set_input_files(f)
                page.wait_for_timeout(5 * 1000)
                _click_if(page, "#done-button, ytcp-button#done-button")
                page.wait_for_timeout(3 * 1000)
                done_any = True
            if done_any:
                if not _click_if(page, "#publish-button, ytcp-button#publish-button"):
                    raise RuntimeError("Couldn't find Publish on the branding page")
                page.wait_for_timeout(5 * 1000)
            return done_any
        finally:
            ctx.close()
