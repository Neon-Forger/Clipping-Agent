"""Browser automation for TikTok posting and Content Rewards submission.
Uses its own persistent browser profile (Opera GX by default): you sign in
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


def profile_dir(name="browser-profile"):
    d = os.path.join(data_dir(), name)
    os.makedirs(d, exist_ok=True)
    return d


def find_opera_gx():
    """Path to Opera GX's real browser exe (the versioned one, not the launcher)."""
    roots = [os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Opera GX"),
             os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Opera GX"),
             os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Opera GX")]
    for root in roots:
        if not os.path.isdir(root):
            continue
        versions = []
        for d in os.listdir(root):
            exe = os.path.join(root, d, "opera.exe")
            if os.path.isfile(exe) and d[:1].isdigit():
                try:
                    versions.append((tuple(int(x) for x in d.split(".")), exe))
                except ValueError:
                    pass
        if versions:
            return max(versions)[1]
        if os.path.isfile(os.path.join(root, "opera.exe")):
            return os.path.join(root, "opera.exe")
    return None


def _exe_for_channel(ch):
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    la = os.environ.get("LOCALAPPDATA", "")
    cands = {"msedge": [os.path.join(pf86, r"Microsoft\Edge\Application\msedge.exe"), os.path.join(pf, r"Microsoft\Edge\Application\msedge.exe")],
             "chrome": [os.path.join(pf, r"Google\Chrome\Application\chrome.exe"), os.path.join(pf86, r"Google\Chrome\Application\chrome.exe"),
                        os.path.join(la, r"Google\Chrome\Application\chrome.exe")]}.get(ch, [])
    for c in cands:
        if os.path.isfile(c):
            return c
    return None


def browser_targets(posting_cfg, prefix="browser-profile"):
    """Browsers to try, in order: (display name, launch kwargs for Playwright, plain .exe path or None).
    `prefix` keeps separate sign-ins per section (clipping vs YouTube)."""
    want = (posting_cfg.get("browser") or "opera_gx").strip()
    out = []
    if want.lower() in ("opera_gx", "opera", "operagx"):
        exe = find_opera_gx()
        if exe:
            out.append(("Opera GX", dict(executable_path=exe, user_data_dir=profile_dir(prefix + "-operagx")), exe))
    elif want.lower().endswith(".exe"):
        out.append((os.path.basename(want), dict(executable_path=want, user_data_dir=profile_dir(prefix + "-custom")), want))
    elif want.lower() == "chrome":
        out.append(("Chrome", dict(channel="chrome", user_data_dir=profile_dir(prefix + "-chrome")), _exe_for_channel("chrome")))
    out += [("Edge", dict(channel="msedge", user_data_dir=profile_dir(prefix if prefix != "browser-profile" else "browser-profile")), _exe_for_channel("msedge")),
            ("Chrome", dict(channel="chrome", user_data_dir=profile_dir(prefix + "-chrome")), _exe_for_channel("chrome"))]
    return out


def _launch(p, posting_cfg, headless=None, log=None, prefix="browser-profile"):
    """Opens the agent's browser for automation. Setting `posting.browser`: opera_gx (default), edge,
    chrome, or a full path to a Chromium-based browser .exe."""
    base = dict(headless=posting_cfg.get("headless", False) if headless is None else headless,
                viewport={"width": 1366, "height": 900},
                user_agent=posting_cfg.get("user_agent") or None,
                args=["--disable-blink-features=AutomationControlled", "--mute-audio"])
    attempts = browser_targets(posting_cfg, prefix)
    errors = []
    for name, kw, _exe in attempts:
        try:
            ctx = p.chromium.launch_persistent_context(**kw, **base)
            if errors and log:
                log("warn", f"Couldn't open {attempts[0][0]} ({errors[0]}); using {name} instead.")
            return ctx
        except Exception as e:
            errors.append(str(e).splitlines()[0][:200])
    raise RuntimeError("Couldn't open any browser: " + " | ".join(errors))


def open_plain(posting_cfg, urls, prefix="browser-profile", max_minutes=30, log=None):
    """Opens the agent's browser profile as a NORMAL browser window (not remote-controlled), so sites
    like Google allow signing in. Returns when you close the window. Falls back to the controlled
    browser if no browser .exe is found."""
    import subprocess
    for name, kw, exe in browser_targets(posting_cfg, prefix):
        if not exe or not os.path.isfile(exe):
            continue
        cmd = [exe, f"--user-data-dir={kw['user_data_dir']}", "--no-first-run", "--no-default-browser-check", "--new-window"] + list(urls)
        try:
            proc = subprocess.Popen(cmd)
        except Exception as e:
            if log:
                log("warn", f"Couldn't start {name}: {e}")
            continue
        if log:
            log("info", f"Opened {name}. Sign in, then close that window.")
        try:
            proc.wait(timeout=max_minutes * 60)
        except Exception:
            proc.kill()
        time.sleep(2)
        return name
    open_for_login(posting_cfg, urls, max_minutes=max_minutes, prefix=prefix)
    return "automation browser"


def _human_pause(a=0.6, b=1.6):
    time.sleep(random.uniform(a, b))


def open_for_login(posting_cfg, urls, max_minutes=20, prefix="browser-profile"):
    """Opens the agent's browser so you can sign in. Returns when you close the window
    (or after `max_minutes`, so the browser is never blocked forever)."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        ctx = _launch(p, posting_cfg, headless=False, prefix=prefix)
        closed = {"v": False}
        ctx.on("close", lambda *_: closed.update(v=True))
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(urls[0])
        for u in urls[1:]:
            ctx.new_page().goto(u)
        end = time.time() + max_minutes * 60
        while time.time() < end and not closed["v"]:
            try:
                if not [pg for pg in ctx.pages if not pg.is_closed()]:
                    break
                time.sleep(1)
            except Exception:
                break
        try:
            ctx.close()
        except Exception:
            pass


def tiktok_qr_login(posting_cfg, on_qr, should_stop, log=None, max_minutes=5):
    """Signs in to TikTok by QR code: the agent opens TikTok's QR login page out of sight,
    hands screenshots of the QR to `on_qr(png_bytes)`, and you scan it with the TikTok app
    (Profile -> ☰ or the scan icon). Returns True once TikTok is signed in."""
    from playwright.sync_api import sync_playwright
    cfg = dict(posting_cfg)
    cfg["headless"] = False
    with sync_playwright() as p:
        ctx = _launch(p, cfg, headless=False, log=log)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            try:
                page.evaluate("() => { window.moveTo(-3000, -3000); }")
            except Exception:
                pass
            page.goto("https://www.tiktok.com/login/qrcode", wait_until="domcontentloaded", timeout=60000)
            end = time.time() + max_minutes * 60
            last_shot = 0
            while time.time() < end and not should_stop():
                if any(c["name"] == "sessionid" and c["value"] for c in ctx.cookies("https://www.tiktok.com")):
                    time.sleep(3)
                    return True
                if time.time() - last_shot > 4:
                    last_shot = time.time()
                    shot = None
                    for sel in ("canvas", "img[src*='qr' i]", "[data-e2e*='qr' i] img", "[class*='qrcode' i] img",
                                "[class*='QRcode' i] img", "[class*='qr' i] canvas"):
                        loc = page.locator(sel)
                        for i in range(min(loc.count(), 5)):
                            el = loc.nth(i)
                            try:
                                box = el.bounding_box()
                                if el.is_visible() and box and box["width"] >= 100 and box["height"] >= 100:
                                    shot = el.screenshot()
                                    break
                            except Exception:
                                continue
                        if shot:
                            break
                    if not shot:
                        shot = page.screenshot()
                    on_qr(shot)
                time.sleep(1)
            return False
        finally:
            try:
                ctx.close()
            except Exception:
                pass


COOKIE_DOMAINS = {
    "tiktok": [".tiktok.com"],
    "contentrewards": [".contentrewards.com"],
    "youtube": [".youtube.com"],
    "google": [".google.com"],
}
CHECK_URLS = {
    "tiktok": ("https://www.tiktok.com/tiktokstudio/content", "login"),
    "contentrewards": ("https://contentrewards.com/c/home", "login"),
}


def _parse_cookie_header(header, domain):
    out = []
    for part in header.split(";"):
        if "=" not in part:
            continue
        name, _, value = part.strip().partition("=")
        if not name:
            continue
        out.append({"name": name, "value": value, "domain": domain, "path": "/", "secure": True,
                    "httpOnly": False, "sameSite": "Lax", "expires": time.time() + 60 * 86400})
    return out


def import_cookies(service, cookie_header, posting_cfg, log):
    """Puts cookies captured on the phone into the agent's browser profile and checks the sign-in worked.
    Returns a short status string."""
    from playwright.sync_api import sync_playwright
    domains = COOKIE_DOMAINS.get(service, [])
    cookies = [c for d in domains for c in _parse_cookie_header(cookie_header, d)]
    if not cookies:
        raise RuntimeError("No cookies were received. Make sure you finished signing in before tapping Send.")
    with sync_playwright() as p:
        ctx = _launch(p, posting_cfg, headless=True, log=log)
        try:
            ctx.add_cookies(cookies)
            if service in CHECK_URLS:
                url, bad = CHECK_URLS[service]
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                time.sleep(5)
                if bad in page.url:
                    return f"cookies saved, but {service} still shows the sign-in page"
                return "signed in ✅"
            return "saved ✅"
        finally:
            ctx.close()


def write_netscape_cookies(cookie_header, domain, path):
    lines = ["# Netscape HTTP Cookie File"]
    exp = int(time.time() + 60 * 86400)
    for c in _parse_cookie_header(cookie_header, domain):
        lines.append("\t".join([domain, "TRUE", "/", "TRUE", str(exp), c["name"], c["value"]]))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _dismiss_popups(page):
    """Closes TikTok's 'new feature' / tips pop-ups that can block clicks."""
    for label in ("Got it", "Not now", "Skip", "Close", "OK"):
        try:
            b = page.get_by_role("button", name=label, exact=True)
            for i in range(min(b.count(), 3)):
                if b.nth(i).is_visible():
                    b.nth(i).click(timeout=2000)
                    time.sleep(0.5)
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
        ctx = _launch(p, posting_cfg, log=log)
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

            _dismiss_popups(page)
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

            _dismiss_popups(page)
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
        ctx = _launch(p, posting_cfg, log=log)
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
