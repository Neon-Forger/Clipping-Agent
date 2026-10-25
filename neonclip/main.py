"""Starts NeonClip: the Clipping agent and the YouTube agent (separate), plus the window.
  --no-gui    run without a window
  --selftest  check that everything can be loaded, then exit"""
import os
import sys


def _fix_streams():
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")


def selftest():
    from agent.main import selftest as clip_selftest
    clip_selftest()
    import edge_tts  # noqa
    import PIL  # noqa
    from ytauto import core, gui, render, studio, thumbs, visuals, writer  # noqa
    from neonclip import app, theme  # noqa
    print("neonclip selftest ok")


def main():
    _fix_streams()
    if "--selftest" in sys.argv:
        selftest()
        return
    from agent.core import Agent
    from ytauto.core import YTAgent
    clip = Agent()
    yt = YTAgent(notifier=clip.ntfy)
    clip.yt = yt                     # only used to pass "yt ..." phone commands along
    yt.start()
    clip.start()
    if "--no-gui" in sys.argv:
        import time
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            clip.stop()
            yt.stop()
        return
    from neonclip.app import Shell
    Shell(clip, yt).run()


if __name__ == "__main__":
    main()
