from kivy.logger import Logger as logger

from .app import MiniHomeTerm
from .config import load_config


def main():
    cfg = load_config()
    logger.setLevel(cfg.get("logging", "level", fallback="INFO").upper())

    MiniHomeTerm(cfg).run()


if __name__ == "__main__":
    main()
