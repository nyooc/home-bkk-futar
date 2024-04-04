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
BUTTON_CHANNEL: Optional[int] = 26  # Broadcom GPIO channel of the button
TICK_SECONDS: float = 0.1  # Time between ticks (matrix and button checks)
BUTTON_MAX_SECONDS: float = 1.0  # Max time between two consecutive presses that we accept as real

# Global state variables
ENABLED_UNTIL: Optional[float] = None  # Epoch seconds when display should turn off
BUTTON_LAST_PRESSED_AT: Optional[float] = None  # Epoch seconds when button was last pressed
MATRIX: Optional[Process] = None  # Process holding the matrix loop


def on_button_press(_: int) -> None:
    """Only set enabled time if button experienced two consecutive presses"""
    global BUTTON_LAST_PRESSED_AT
    button_last_pressed_at = BUTTON_LAST_PRESSED_AT
    BUTTON_LAST_PRESSED_AT = time.time()
    if button_last_pressed_at:
        diff_seconds = BUTTON_LAST_PRESSED_AT - button_last_pressed_at
        LOGGER.debug("Button press, last pressed %.3f seconds ago", diff_seconds)
        if diff_seconds <= BUTTON_MAX_SECONDS:
            set_enabled_time()
    else:
        LOGGER.debug("Button press, never pressed before")


def set_enabled_time() -> None:
    """Based on settings, determine a new value for `ENABLED_UNTIL` in the future"""
    global ENABLED_UNTIL
    LOGGER.debug("Setting enabled time for %d seconds from now", ENABLE_FOR_SECONDS)
    ENABLED_UNTIL = BUTTON_LAST_PRESSED_AT + ENABLE_FOR_SECONDS


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
    GPIO.add_event_detect(BUTTON_CHANNEL, GPIO.BOTH, callback=on_button_press)
    loop()
