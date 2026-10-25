"""Starts the agent and opens its window. Use --no-gui to run without a window."""
import sys


def main():
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
