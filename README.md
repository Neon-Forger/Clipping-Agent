# NeonClip V2

A Windows app with **two completely separate sections** and an Android phone app that watches and controls both.
Each section has its own settings, database, AI keys and browser sign-ins.

## ✂ Clipping (Content Rewards → TikTok)
1. Watches the YouTube channels or videos of campaigns you've joined.
2. Transcribes with word-level timing and asks your AI (Gemini, OpenRouter or any OpenAI-compatible API) for the most viral 30–60 s moments.
3. Edits vertical clips: zooms, word-by-word captions, hook title, and a flash + impact sound on the punchline.
4. Posts to TikTok, then submits the link to Content Rewards within its 30-minute window.

## ▶ YouTube automation
1. **Setup:** sign in with Google in a normal browser window, then pick an existing channel or create a new one. NeonClip can also make a neon profile picture and banner.
2. **Every day at your chosen time** (while the PC is on) it makes your long videos and Shorts for the genre you pick:
   - **Original:** the AI writes the script, a neural voice narrates it (Microsoft Edge voices, free), and it adds stock footage (Pexels, free key) or AI images, captions, chapters and an AI title, description and tags.
   - **Repurposed:** highlight/commentary edits of videos you're **allowed** to reuse: your own uploads, creators who gave permission, or videos YouTube marks **Creative Commons** (credited automatically).
3. **Thumbnails:** a neon style, made from the video or an AI image.
4. **Uploads** through YouTube Studio at your upload times (public, unlisted or private), with "made for kids" and altered-content answers set.

> NeonClip deliberately has no "ignore copyright" switch. Re-uploading other people's videos without permission gets copyright strikes (three strikes deletes the channel) and fails YouTube's reused-content monetization rules.

## 📱 Phone app
- Live status of both sections, plus activity and notifications.
- Pause or resume, make or upload now, post now, clip a link.
- Edit any setting, or type instructions in plain English.
- Sign in to TikTok and Content Rewards from the phone. Sign-ins are encrypted with your pairing code.

## Install
1. Download **NeonClip-Windows.zip** from [Releases](../../releases/latest), unzip it somewhere permanent, and open `NeonClip.exe`. If SmartScreen appears, choose *More info → Run anyway*.
2. **YOUTUBE → CHANNEL:** follow steps 1–4.
3. **CLIPPING → SETTINGS / ACCOUNTS:** add your AI key and sign in.
4. **PHONE:** install **NeonClip.apk** and enter the topic and pairing code.

## Editing the app
The source is in the `source` folder next to the .exe. Run it with `run_from_source.bat` (needs Python 3.11+).
Settings live in `%LOCALAPPDATA%\ClipCartelAgent\`: `settings.json` (Clipping) and `youtube.json` (YouTube).
Page selectors for TikTok, Content Rewards and YouTube Studio are editable there in case those sites change.

## Important
- Automated posting can break platform rules (TikTok especially). Keep posting volume human-like.
- Custom YouTube thumbnails need a phone-verified channel.
- Anyone who knows your ntfy topic can control NeonClip, so keep it private.
