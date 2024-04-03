"""Direct RGB Matrix manipulation, main event loop: request new info -> refresh matrix"""

import datetime as dt
import logging
import os
import signal
import sys
import time
from typing import Optional

from requests import Session
from rgbmatrix import RGBMatrix, RGBMatrixOptions, FrameCanvas, graphics

from home_bkk_futar.client import DisplayInfo
from home_bkk_futar.utils import get_rgb_color


# Set logging with a level acquired from environment variable
logging.basicConfig(level=os.environ["BKK_FUTAR_LOGGING_LEVEL"])
LOGGER = logging.getLogger(__name__)

# Also see rpi_rgb_led_matrix/fonts folder for many more available {W}x{H}{SUFFIX}.bdf files
FONT_WIDTH: int = 6
FONT_HEIGHT: int = 12
FONT_SUFFIX: str = "mono"
FONT_PATH: str = f"fonts/{FONT_WIDTH}x{FONT_HEIGHT}{FONT_SUFFIX}.bdf"

# Indention of text rows relative to origin at upper left
X_INDENT: int = 2  # Nice to have a left indent - won't harm at right because narrow minute sign: '
Y_INDENT: int = -2  # Helps center text for high fonts that have no pixels at the top such as 6x12

# Latency bars show the age of the display (meant for error mode when displayed info is getting old)
LATENCY_BAR_SECONDS: Optional[int] = 60  # For each this many seconds, draw one latency bar
LATENCY_BAR_Y_INDENT: int = 0  # Draw the latency bars at this pixel offset

# API request & canvas refresh timing
TICK_SECONDS: int = 10  # Time between ticks (canvas updates)
REQUEST_TICKS: int = 3  # In usual mode, make an API request to BKK after each this many ticks

# Error mode: when some error occurs while requesting BKK
ERROR_TICKS_SEQUENCE: list[int] = [1, 2, 4, 8, 16]  # Make API requests in these ticks (backoff)
ERROR_TICKS: int = 30  # After backoff, make API requests after each this many ticks

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

# Global matrix display state
STATE: Optional[tuple[RGBMatrix, FrameCanvas, graphics.Font]] = None


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


def draw(display_info: DisplayInfo, canvas: FrameCanvas, font: graphics.Font) -> None:
    """Draw the display info contents on the canvas using specified font"""

    def get_latency_bars() -> int:
        """Calculate the proper number of latency bars to draw"""
        latency_seconds = (dt.datetime.now(tz=dt.timezone.utc) - display_info.server_time).seconds
        return max(min(latency_seconds // LATENCY_BAR_SECONDS, chars), 0)

    color = graphics.Color(*get_rgb_color(display_info.server_time))
    lines = RGB_MATRIX_OPTIONS["rows"] // FONT_HEIGHT
    chars = RGB_MATRIX_OPTIONS["cols"] // FONT_WIDTH

    for i, line in enumerate(display_info.format(lines=lines, chars=chars)):
        if line:
            graphics.DrawText(canvas, font, X_INDENT, (i + 1) * FONT_HEIGHT + Y_INDENT, color, line)

    if LATENCY_BAR_SECONDS and (latency_bars := get_latency_bars()):
        graphics.DrawText(canvas, font, X_INDENT, LATENCY_BAR_Y_INDENT, color, "_" * latency_bars)


def init() -> tuple[RGBMatrix, FrameCanvas, graphics.Font]:
    """Initialize the matrix, canvas and font"""
    LOGGER.info("Initializing - using font path: %s", FONT_PATH)

    # Configuration for the matrix
    options = RGBMatrixOptions()
    for key, value in RGB_MATRIX_OPTIONS.items():
        setattr(options, key, value)

    # Load the font
    font = graphics.Font()
    font.LoadFont(FONT_PATH)

    # Start up the matrix
    matrix = RGBMatrix(options=options)
    canvas = matrix.CreateFrameCanvas()

    return matrix, canvas, font


def loop(matrix: RGBMatrix, canvas: FrameCanvas, font: graphics.Font) -> None:
    """Display loop: handle web requests and canvas refresh"""
    LOGGER.info("Starting display loop")
    display_info = None
    tick_counter = TickCounter()
    with Session() as session:
        while True:
            # Download data from BKK and populate a new `DisplayInfo` object
            if tick_counter.is_request_tick:
                try:
                    display_info = DisplayInfo.request(session=session)
                    LOGGER.debug(display_info)
                    tick_counter.set_normal_mode()
                except Exception as error:  # Errors should be specified (HTTP, Timeout, Validation)
                    LOGGER.warning(error)
                    tick_counter.set_error_mode()

            # Refresh the canvas and draw contents of the `DisplayInfo` object
            if display_info:
                canvas.Clear()
                draw(display_info, canvas, font)
                canvas = matrix.SwapOnVSync(canvas)

            tick_counter.do_tick()
            time.sleep(TICK_SECONDS)


def cleanup(signum: int, frame):
    """Catch termination signal, clear the matrix, and exit"""
    LOGGER.info("Exiting on %s", signal.Signals(signum))
    matrix, canvas, _ = STATE
    canvas.Clear()
    matrix.SwapOnVSync(canvas)

    sys.exit(0)


def run() -> None:
    """Initialize and run the loop"""
    global STATE
    STATE = init()
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    loop(*STATE)
