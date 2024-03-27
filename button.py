#!/usr/bin/env python
"""Entry point for button actuated limited-time operation"""
import logging
import os
import signal
import sys
import time
from multiprocessing import Process
from typing import Optional

import RPi.GPIO as GPIO
from dotenv import load_dotenv

load_dotenv()

from home_bkk_futar.matrix import run

# Set logging with a level acquired from environment variable
logging.basicConfig(level=os.environ["BKK_FUTAR_LOGGING_LEVEL"])
LOGGER = logging.getLogger(__name__)

# Configuration for button operation
ENABLE_FOR_SECONDS: Optional[int] = 600  # Switch off after this many seconds
BUTTON_CHANNEL: Optional[int] = 26  # Channel, enable on a rising input edge
TICK_SECONDS: float = 0.1  # Time between ticks (matrix and button checks)

# Global state variables
ENABLED_UNTIL: Optional[float] = None  # Epoch seconds when display should turn off
MATRIX: Optional[Process] = None  # Process holding the matrix loop


def set_enabled_time(*args) -> None:
    """Based on settings, determine a new value for `ENABLED_UNTIL` in the future"""
    global ENABLED_UNTIL
    LOGGER.debug("Setting enabled time for %d seconds from now", ENABLE_FOR_SECONDS)
    ENABLED_UNTIL = time.time() + ENABLE_FOR_SECONDS


def is_enabled_time() -> bool:
    """Based on settings, determine whether right now the matrix should be enabled"""
    return (time.time() < ENABLED_UNTIL) if ENABLED_UNTIL else False


def loop():
    """Button loop: handle the button press"""
    global MATRIX
    LOGGER.info("Starting button loop")
    while True:
        if not MATRIX and is_enabled_time():
            MATRIX = Process(target=run)
            MATRIX.start()
        elif MATRIX and not is_enabled_time():
            MATRIX.terminate()
            MATRIX = None
        time.sleep(TICK_SECONDS)


def cleanup(signum: int, frame):
    """Catch termination signal, send termination signal to matrix, and exit"""
    global MATRIX
    LOGGER.info("Exiting on %s", signal.Signals(signum))
    if MATRIX:
        MATRIX.terminate()
        MATRIX = None
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_CHANNEL, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.add_event_detect(BUTTON_CHANNEL, GPIO.RISING, callback=set_enabled_time)
    loop()
