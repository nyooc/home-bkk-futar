#!/usr/bin/env python
"""Direct RGB Matrix manipulation, main event loop of home-bkk-futar"""
import logging
import os
import sys
import time
from requests import Session
from dotenv import load_dotenv

load_dotenv()

from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from home_bkk_futar.client import Display


# Set logging with a level acquired from environment variable
logging.basicConfig(level=os.environ["BKK_FUTAR_LOGGING_LEVEL"])
LOGGER = logging.getLogger(__name__)

# See rpi_rgb_led_matrix/fonts folder for available {W}x{H}{SUFFIX}.bdf files
FONT_WIDTH = 6
FONT_HEIGHT = 12
FONT_SUFFIX = ""

# Indention of text rows relative to origin at upper left
X_INDENT = 1  # This way a one-pixel column at left will be always blank - won't harm at right end
Y_INDENT = -1  # This helps center the text for high fonts such as 6x12

# API request & canvas refresh timing
REFRESH_SECONDS = 15  # Time between canvas updates
REQUEST_MULTIPLIER = 2  # Make an API request after this many canvas updates

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


def main():
    """Main event loop of home-bkk-futar"""

    # Configuration for the matrix
    options = RGBMatrixOptions()
    for key, value in RGB_MATRIX_OPTIONS.items():
        setattr(options, key, value)

    # Font and color loading
    font = graphics.Font()
    font.LoadFont(f"rpi_rgb_led_matrix/fonts/{FONT_WIDTH}x{FONT_HEIGHT}{FONT_SUFFIX}.bdf")
    color = graphics.Color(255, 0, 255)

    # Matrix initialization
    matrix = RGBMatrix(options=options)
    canvas = matrix.CreateFrameCanvas()

    i_request = 0
    with Session() as session:
        while True:
            if not i_request:
                display = Display.request_new(session=session)
                LOGGER.debug(display)
            i_request = (i_request + 1) % REQUEST_MULTIPLIER

            canvas.Clear()
            for i, line in enumerate(
                display.format(
                    lines=RGB_MATRIX_OPTIONS["rows"] // FONT_HEIGHT,
                    chars=RGB_MATRIX_OPTIONS["cols"] // FONT_WIDTH,
                )
            ):
                if line:
                    graphics.DrawText(
                        canvas, font, X_INDENT, (i + 1) * FONT_HEIGHT + Y_INDENT, color, line
                    )

            canvas = matrix.SwapOnVSync(canvas)
            time.sleep(REFRESH_SECONDS)


# Main function
if __name__ == "__main__":
    try:
        LOGGER.info("Home BKK Futar - Starting up (Press CTRL-C to exit)")
        main()
    except KeyboardInterrupt:
        LOGGER.info("Home BKK Futar- Exiting on KeyboardInterrupt")
        sys.exit(0)
