# ===== shared/logger.py =====

import logging
import logging.handlers
import os
import sys


class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[90m",
        "INFO": "\033[97m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "CRITICAL": "\033[1;91m",
    }
    RESET = "\033[0m"

    def format(self, record):
        log_fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        base = formatter.format(record)
        color = self.COLORS.get(record.levelname, self.RESET)
        return f"{color}{base}{self.RESET}"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    logs_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"
    )
    os.makedirs(logs_dir, exist_ok=True)

    log_path = os.path.join(logs_dir, "render-agent.log")
    file_handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)

    return logger