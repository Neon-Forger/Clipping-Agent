# Clip Cartel Agent

An app for your Windows PC that runs [Content Rewards](https://contentrewards.com) clipping on its own:

1. **Finds videos.** It watches the YouTube channels (or specific videos) you pick in **Sources**.
2. **Picks the best moments.** It transcribes on your PC with word-level timing and asks your AI (Gemini, OpenRouter or any OpenAI-compatible API) for the most viral 30–60 second moments, with hook titles and captions.
3. **Edits.** It renders vertical 1080×1920 clips: blurred background, slow zoom, word-by-word captions with highlighted words, and a hook title. In *dramatic* style the punchline also gets a flash, punch-in zoom, shake and impact sound. There's a progress bar too.
4. **Posts to TikTok.** It uses its own Microsoft Edge window, spaced out and never during quiet hours.
5. **Submits the link to Content Rewards** within the 30-minute window and checks it shows up in Submissions.
6. **Keeps your phone updated** over [ntfy](https://ntfy.sh). Use the **Clip Cartel** Android app to see progress, pause/resume, post now, change any setting, or type instructions in plain English.

## Install (Windows)
1. Download **ClipCartelAgent-Windows.zip** from [Releases](../../releases/latest), unzip it somewhere permanent (e.g. `Documents\ClipCartelAgent`).
2. Open `ClipCartelAgent.exe`. If Windows SmartScreen appears, click *More info → Run anyway*.
3. **Settings tab:** paste your Gemini and/or OpenRouter API key, then click Save.
4. **Accounts & Phone tab:** click *Sign in to TikTok + Content Rewards*, sign in to both in the window that opens, then close it.
5. **Sources tab:** check the channel and campaign link.
6. Install **ClipCartel.apk** on your phone and enter the topic shown in *Accounts & Phone*.

The first transcription downloads a speech model (~500 MB) once.

## Phone commands
`status` `pause` `resume` `run` `post` `list` `skip <id>` `retry <id>` `clip <url> [n]`
`set <setting> <value>` `get <setting>` `settings` `prompt <text>` `sources` `ask <question>`
Anything else is turned into commands by the AI, e.g. *"only post 3 a day and skip anything political"*.

## Editing the app
The full source is in the `source` folder next to the .exe (and in this repo). Edit it and start it with `run_from_source.bat` (needs Python 3.11+). Every setting is also in `%LOCALAPPDATA%\ClipCartelAgent\settings.json`. If TikTok or Content Rewards change their pages, the page selectors are under `selectors` in that file.

## Important
* Automated posting is against TikTok's terms; accounts that post like bots can be limited or banned. Keep the volume human-like (the defaults: ≥3 h apart, ≤5/day, nothing 00:00–05:00).
* Only clip creators whose Content Rewards campaign you've joined. That's what gives you permission to use their footage. Read each campaign's rules (required hashtags, which episodes are allowed).
* Content Rewards only accepts links submitted within 30 minutes of posting, so keep the agent running while it posts.
* Anyone who knows your ntfy topic can read and control the agent. Keep it private.
