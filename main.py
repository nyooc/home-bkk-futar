#!/usr/bin/env python
"""Entry point for infinite operation"""
import logging
import os
import signal
import sys
from dotenv import load_dotenv

load_dotenv()

from home_bkk_futar.matrix import run


# Set logging with a level acquired from environment variable
logging.basicConfig(level=os.environ["BKK_FUTAR_LOGGING_LEVEL"])
LOGGER = logging.getLogger(__name__)


def cleanup(signum: int, frame):
    """Catch termination signal and do the exit"""
    LOGGER.info("Exiting on %s", signal.Signals(signum))
    sys.exit(0)


if __name__ == "__main__":
    LOGGER.info("Starting up")
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    run()
