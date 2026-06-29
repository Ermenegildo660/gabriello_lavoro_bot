import threading
import os

from bot import run_bot
from web import run_web


def main():
    """
    Avvia insieme:
    - Bot Telegram
    - Mini app web Ore Live

    Railway deve usare come Start Command:
    python main.py
    """

    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()

    run_bot()


if __name__ == "__main__":
    main()
