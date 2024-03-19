# Fonts

This is a folder for custom `.bdf` fonts, there are many more to use or tweak within the 
[rpi_rgb_led_matrix](https://github.com/hzeller/rpi-rgb-led-matrix/tree/master/fonts) library.
Some instructions on how to create these bitmap fonts from OpenType or TrueType format using 
[otf2bdf](https://github.com/jirutka/otf2bdf) can also be found there. Tweaking an already existing 
font can be done via a GUI font editor such as [FontForge](https://fontforge.org/).

`6x12mono.bdf` is a modified version of the original `6x12.bdf`: some narrower letters were 
converted to monospaced because RGBMatrix will draw them using a fixed spacing.
