#!/usr/bin/env python
"""Direct RGB Matrix manipulation, main event loop of home-bkk-futar"""
import logging
import os
import sys
import time
from typing import Optional
from requests import Session
from dotenv import load_dotenv

load_dotenv()

from rgbmatrix import RGBMatrix, RGBMatrixOptions, FrameCanvas, graphics
from home_bkk_futar.client import Display
from home_bkk_futar.utils import get_rgb_color


# Set logging with a level acquired from environment variable
logging.basicConfig(level=os.environ["BKK_FUTAR_LOGGING_LEVEL"])
LOGGER = logging.getLogger(__name__)

# See rpi_rgb_led_matrix/fonts folder for available {W}x{H}{SUFFIX}.bdf files
FONT_WIDTH: int = 6
FONT_HEIGHT: int = 12
FONT_SUFFIX: str = ""

# Indention of text rows relative to origin at upper left
X_INDENT: int = 2  # Nice to have a left indent - won't harm at right because narrow minute sign: '
Y_INDENT: int = -2  # Helps center text for high fonts that have no pixels at the top such as 6x12

# API request & canvas refresh timing
TICK_SECONDS: int = 10  # Time between ticks (canvas updates)
REQUEST_TICKS: int = 3  # In usual mode, make an API request to BKK after each this many ticks

# Error mode: when some error occurs while requesting BKK
ERROR_TICKS_SEQUENCE: list[int] = [1, 2, 4, 8, 16]  # Make API requests in these ticks (backoff)
ERROR_TICKS: int = 30  # After backoff, make API requests after each this many ticks

# When should the matrix be enabled and request and show information
ENABLE_FOR_SECONDS: Optional[int] = 600  # Switch off after this many seconds (when None, never)
ENABLE_UNTIL: Optional[float] = None  # Switch off at this epoch seconds (when None, never)

# RGBMatrixOptions elements to pass, for clarity here we include params with default values, too
RGB_MATRIX_OPTIONS = {
    "rows": 48,  # led-rows
    "cols": 96,  # led-cols
    "chain_length": 1,  # led-chain (DEFAULT)
    "parallel": 1,  # led-parallel (DEFAULT)
    "hardware_mapping": "regular",  # led-gpio-mapping (DEFAULT)
    "row_address_type": 0,  # led-row-addr-type (DEFAULT)
    "multiplexing": 0,  # led-multiplexing (DEFAULT)
    "pwm_bits": 11,  # led-pwm-bits (DEFAULT)
    "brightness": 100,  # led-brightness (DEFAULT)
    "pwm_lsb_nanoseconds": 130,  # led-pwm-lsb-nanoseconds
    "led_rgb_sequence": "RGB",  # led-rgb-sequence (DEFAULT)
    "pixel_mapper_config": "",  # led-pixel-mapper (DEFAULT)
    "show_refresh_rate": 0,  # led-show-refresh (DEFAULT)
    "gpio_slowdown": 4,  # led-slowdown-gpio
    "disable_hardware_pulsing": True,  # led-no-hardware-pulse
    "drop_privileges": True,  # led-no-drop-privs (DEFAULT)
}


class TickCounter:
    """Facility that keeps track of tick count and normal vs error mode"""

    error_mode: bool = False
    tick: int = 0

    @property
    def is_request_tick(self) -> bool:
        """Return True when an API request should be made"""
        if self.error_mode:
            return (self.tick in ERROR_TICKS_SEQUENCE) or (self.tick % ERROR_TICKS == 0)
        return self.tick % REQUEST_TICKS == 0

    def set_normal_mode(self) -> None:
        """When entering normal mode, reset counter"""
        if self.error_mode:
            self.error_mode = False
            self.tick = 0

    def set_error_mode(self) -> None:
        """When entering error mode, reset counter"""
        if not self.error_mode:
            self.error_mode = True
            self.tick = 0

    def do_tick(self) -> None:
        """Increase counter"""
        self.tick += 1


def set_enabled_time() -> None:
    """Based on settings, determine a new value for `ENABLE_UNTIL`"""
    global ENABLE_UNTIL
    if ENABLE_FOR_SECONDS:
        ENABLE_UNTIL = time.time() + ENABLE_FOR_SECONDS
    elif not ENABLE_UNTIL:
        ENABLE_UNTIL = float("inf")


def is_enabled_time() -> bool:
    """Based on settings, determine whether right now the display should be enabled"""
    if ENABLE_UNTIL:
        return time.time() < ENABLE_UNTIL
    return False


def draw(display: Display, canvas: FrameCanvas, font: graphics.Font) -> None:
    """Draw the display contents on the canvas using specified font"""
    color = graphics.Color(*get_rgb_color(display.server_time))
    lines = RGB_MATRIX_OPTIONS["rows"] // FONT_HEIGHT
    chars = RGB_MATRIX_OPTIONS["cols"] // FONT_WIDTH

    for i, line in enumerate(display.format(lines=lines, chars=chars)):
        if line:
            graphics.DrawText(canvas, font, X_INDENT, (i + 1) * FONT_HEIGHT + Y_INDENT, color, line)


def init() -> tuple[RGBMatrix, FrameCanvas, graphics.Font]:
    """Initialize the matrix, canvas and font"""

    LOGGER.info("Home BKK Futar - Initializing")

    # Configuration for the matrix
    options = RGBMatrixOptions()
    for key, value in RGB_MATRIX_OPTIONS.items():
        setattr(options, key, value)

    # Load the font
    font = graphics.Font()
    font.LoadFont(f"rpi_rgb_led_matrix/fonts/{FONT_WIDTH}x{FONT_HEIGHT}{FONT_SUFFIX}.bdf")

    # Start up the matrix
    matrix = RGBMatrix(options=options)
    canvas = matrix.CreateFrameCanvas()

    return matrix, canvas, font


def loop(matrix: RGBMatrix, canvas: FrameCanvas, font: graphics.Font) -> None:
    """Main event loop of home-bkk-futar"""

    LOGGER.info("Home BKK Futar - Starting event loop (Press CTRL-C to exit)")
    display = None
    set_enabled_time()
    tick_counter = TickCounter()
    with Session() as session:
        while is_enabled_time():
            # Download data from BKK and populate a new Display object
            if tick_counter.is_request_tick:
                try:
                    display = Display.request_new(session=session)
                    LOGGER.debug(display)
                    tick_counter.set_normal_mode()
                except Exception as error:  # Errors should be specified (HTTP, Timeout, Validation)
                    LOGGER.warning(error)
                    tick_counter.set_error_mode()

            # Refresh the canvas and draw contents of the Display object
            if display:
                canvas.Clear()
                draw(display, canvas, font)
                canvas = matrix.SwapOnVSync(canvas)

            tick_counter.do_tick()
            time.sleep(TICK_SECONDS)

    # End-of-loop cleanup
    LOGGER.info("Home BKK Futar - Finishing event loop")
    canvas.Clear()
    matrix.SwapOnVSync(canvas)


# Main function
if __name__ == "__main__":
    try:
        loop(*init())
    except KeyboardInterrupt:
        LOGGER.info("Home BKK Futar- Exiting on KeyboardInterrupt")
        sys.exit(0)
