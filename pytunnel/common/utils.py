"""Common utility functions."""

import logging
import secrets
import string
from typing import Optional
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Set up a logger with colored output."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)

        class ColoredFormatter(logging.Formatter):
            """Custom formatter with colors."""

            COLORS = {
                'DEBUG': Fore.CYAN,
                'INFO': Fore.GREEN,
                'WARNING': Fore.YELLOW,
                'ERROR': Fore.RED,
                'CRITICAL': Fore.RED + Style.BRIGHT,
            }

            def format(self, record):
                levelname = record.levelname
                if levelname in self.COLORS:
                    record.levelname = f"{self.COLORS[levelname]}{levelname}{Style.RESET_ALL}"
                return super().format(record)

        formatter = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def generate_client_id(length: int = 8) -> str:
    """Generate a random client ID."""
    alphabet = string.ascii_lowercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_request_id(length: int = 16) -> str:
    """Generate a random request ID."""
    return secrets.token_hex(length // 2)
