import os

from agent.config import Settings, data_dir

DEFAULTS = {
    "enabled": False,               # turned on by the setup wizard
    "paused": False,
    "setup_done": False,
    # ---- channel ----
    "channel": {
        "mode": "",                 # "new" or "existing"
        "name": "",
        "handle": "",
        "channel_id": "",           # UC... (filled in after you pick the channel)
        "description": "",
        "avatar_file": "",
        "banner_file": "",
    },
    # ---- what to make ----
    "genre": "",                    # e.g. "true crime stories", "space facts", "motivational stories"
    "audience": "adults in the US",
    "language": "English",
    "style_notes": "",              # anything the AI should always do or avoid
    "daily": {
        "long_videos": 1,
        "shorts": 2,
        "make_at": "08:00",         # when the PC starts making today's videos (24h)
        "upload_times": ["12:00", "15:00", "18:00"],   # when finished videos go live (24h, local time)
    },
    "long": {"minutes": 8, "chapters": True},
    "shorts": {"seconds": 45},
    # Where content comes from. "original" = AI writes and narrates new videos for the genre.
    # "repurpose" = re-edit videos you have the rights to use (see sources below).
    "mix": {"original": 70, "repurpose": 30},
    "sources": [
        # {"url": "https://www.youtube.com/@yourotherchannel", "rights": "own", "note": ""}
        # rights: "own" (your content) | "permission" (creator allowed it / campaign) | "creative_commons"
    ],
    "find_creative_commons": True,  # search YouTube for Creative Commons videos in your genre to repurpose
    # ---- voice & visuals ----
    "voice": "en-US-AndrewNeural",  # Microsoft Edge neural voices (free)
    "voice_rate": "+5%",
    "pexels_api_key": "",           # free key from pexels.com/api, used for stock footage
    "music_folder": "",             # optional: folder of music you have the rights to
    "music_volume": 0.12,
    "visual_style": "stock",        # stock = stock footage/photos + captions | stickman = stickman cutout meme edit
    "visual_instructions": "",      # how videos should LOOK (followed beat by beat by the AI editor)
    "stickman_captions": False,     # burn word captions in the stickman style
    "captions": True,
    "caption_style": "neon",        # neon | clean
    # ---- thumbnails ----
    "thumbnails": {"ai_images": True, "text_color": "#7FE9FF", "accent": "#FF2BD6"},
    # ---- upload ----
    "upload": {
        "visibility": "public",     # public | unlisted | private
        "made_for_kids": False,
        "altered_content": False,   # YouTube's "altered or synthetic content" disclosure (realistic fakes)
        "default_tags": [],
        "description_footer": "",
        "browser": "opera_gx",      # browser used for YouTube Studio
        "headless": False,
    },
    # ---- AI (separate keys from the Clipping section) ----
    "ai": {
        "provider_order": ["gemini", "openrouter", "openai_compatible"],
        "gemini_api_key": "", "gemini_model": "auto",
        "openrouter_api_key": "", "openrouter_model": "openrouter/auto",
        "openai_compatible_base_url": "https://api.openai.com/v1",
        "openai_compatible_api_key": "", "openai_compatible_model": "gpt-4o-mini",
        "custom_instructions": "",
    },
    "transcribe": {"model": "small.en", "device": "auto", "compute_type": "int8"},
    "output_dir": os.path.join(os.path.expanduser("~"), "Videos", "NeonClip YouTube"),
    "keep_finished_days": 14,
    # Advanced: YouTube Studio page selectors (editable if YouTube changes its pages)
    "selectors": {
        "upload_url": "https://www.youtube.com/upload",
        "file_input": "input[type=file]",
        "title_box": "#title-textarea #textbox",
        "description_box": "#description-textarea #textbox",
        "thumbnail_input": "#file-loader, input[type=file][accept*='image']",
        "not_for_kids": "tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT_MFK']",
        "for_kids": "tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_MFK']",
        "altered_no": "tp-yt-paper-radio-button[name='VIDEO_HAS_ALTERED_CONTENT_NO']",
        "altered_yes": "tp-yt-paper-radio-button[name='VIDEO_HAS_ALTERED_CONTENT_YES']",
        "show_more": "#toggle-button",
        "tags_input": "#tags-container input, input[aria-label='Tags']",
        "next_button": "#next-button",
        "done_button": "#done-button",
        "visibility_radio": "tp-yt-paper-radio-button[name='{VIS}']",
        "video_link": "a.ytcp-video-info, .video-url-fadeable a",
    },
}


class YTSettings(Settings):
    def __init__(self):
        super().__init__(path=os.path.join(data_dir(), "youtube.json"), defaults=DEFAULTS)

    def after_load(self):
        changed = super().after_load()
        ci = (self.data.get("ai", {}).get("custom_instructions") or "")
        visual_words = ("ANIMATION", "BACKGROUND", "CAMERA", "9:16", "stickman", "cutout", "PLACEMENT")
        if ci and not self.data.get("visual_instructions") and sum(w.lower() in ci.lower() for w in visual_words) >= 2:
            # a visual direction was saved as script instructions (older versions only had that box)
            self.data["visual_instructions"] = ci
            self.data["ai"]["custom_instructions"] = ""   # moved (the script writer still sees it as the look of the video)
            if "stickman" in ci.lower():
                self.data["visual_style"] = "stickman"
            changed = True
        return changed
