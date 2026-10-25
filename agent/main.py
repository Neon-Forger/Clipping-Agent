"""Starts the agent and opens its window.
  --no-gui    run without a window
  --selftest  check that everything the agent needs can be loaded, then exit"""
import os
import sys


def _fix_streams():
    # A windowed .exe has no console; some libraries expect stdout/stderr to exist.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")


def selftest():
    import faster_whisper  # noqa
    import playwright.sync_api  # noqa
    import requests  # noqa
    import yt_dlp  # noqa
    from .tools import ffmpeg_path, fonts_dir, run
    ff = ffmpeg_path()
    run([ff, "-version"])
    assert os.path.exists(os.path.join(fonts_dir(), "Poppins-Bold.ttf")), "font missing"
    from . import core, editor, gui  # noqa
    print("selftest ok:", ff)


def main():
    _fix_streams()
    if "--selftest" in sys.argv:
        selftest()
        return
    from .core import Agent
    agent = Agent()
    agent.start()
    if "--no-gui" in sys.argv:
        import time
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            agent.stop()
        return
    from .gui import App
    App(agent).run()


if __name__ == "__main__":
    main()
