#!/usr/bin/env python
"""Direct RGB Matrix manipulation, main event loop of home-bkk-futar"""
import sys
import time

from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

# See rpi_rgb_led_matrix/fonts folder for available {W}x{H}{SUFFIX}.bdf files
FONT_WIDTH = 9
FONT_HEIGHT = 18
FONT_SUFFIX = "B"

# Time between canvas updates
TICK_SECONDS = 0.2

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

    while True:
        canvas.Clear()
        graphics.DrawText(canvas, font, 10, 24, color, time.strftime("%H:%M:%S", time.localtime()))

        time.sleep(TICK_SECONDS)
        canvas = matrix.SwapOnVSync(canvas)


# Main function
if __name__ == "__main__":
    try:
        print("Press CTRL-C to exit")
        main()
    except KeyboardInterrupt:
        print("Exiting\n")
        sys.exit(0)
