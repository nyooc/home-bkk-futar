# home-bkk-futar
Your own Budapest transit display using a Raspberry Pi + a LED matrix.

![Home BKK Futar display in work, the button on the right serves to enable it for some time period](
/assets/device.jpg)

Those LED matrix displays showing bus departure times are so cool out there right? What's more, if
you know up front when your bus will be leaving, you can make an informed decision whether you have
those extra minutes to take out the trash. This project unifies the beauty and usefulness of 
Budapest's BKK Futar displays. You can use it to just display the departure times on your computer,
or configure a Raspberry Pi with a real LED Matrix display using the excellent
[rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix/) library.

## Features

**Modular.** Uses [pydantic](https://github.com/pydantic/pydantic) to structure responses from
BKK's API as well as internal structures. You can use only the structured departure time for a given
stop to build something else on top of it.

**Highly configurable.** You have a myriad of options to operate the display, or just simply use the
BKK Futar client to implement your own. You can create your own font and display format.

**Privacy first.** Not just the API key but also your bus stops are treated as secret. This is
important since it doesn't expose your location even if you fork and update this project.

**Handles errors.** The matrix won't die on any networking or other error, and will show an
error bar per minute of latency, so you'll know how outdated is the data you are staring at. 

**Saves energy.** If you choose button-actuated operation, the display will completely stop after
going blank, so your Pi's CPU can have a rest (or do some other stuff).

## Known Issues

**Bus stops too deeply burned.** It's very effective when running the matrix that the environment
variable containing your bus stops is read up and subsequent variables are compiled just once,
but it's complicated to try out different bus stops at runtime, e.g. when experimenting. 

**Fonts, fonts, fonts.** I tweaked the 6x12 font for my use case, but it may need further
improvement, especially when wanting a fully monospaced font. This font mostly uses 6x8 characters
so if someone wants a lot of lines on the display, it may make sense to use a 6x8 font - this is the
original one used at BKK.

## Try It Out Right Now!

No Raspberry Pi or matrix display required. We use [bdfparser](https://github.com/tomchen/bdfparser)
and [pillow](https://github.com/python-pillow/Pillow) to render an image output.

**Make your environment.** Clone this repo to your machine, you can omit the git submodule for now. 
Create a Python environment and install packages from `requirements-dev.txt`. If you plan to carry
on to a Pi, use the Python version you have there (Python 3.9 is preinstalled on Pi images as of
this writing).

**Set environment variables.** Copy the `.env.example` file into `.env`, and set the variables
therein.
- `BKK_FUTAR_API_KEY` should contain your API key at BKK. You can ask for one at 
  [opendata.bkk.hu/keys](https://opendata.bkk.hu/keys). Be respectful of this key, never expose it
  and never overuse it.
- `BKK_FUTAR_LOGGING_LEVEL` shows the logging level and is set to `INFO` by default. You can change
  it to `DEBUG` to see more granular logs, or to `WARNING` to only see problems.
- `BKK_FUTAR_SIGN_BY_STOP` is a list of Budapest transit stops we want to display, each paired with
  a character that will display on the screen. This is treated as a secret variable because it can
  bind someone to his home. The stop IDs can be browsed on the [futar.bkk.hu](https://futar.bkk.hu/)
  interactive map: instead of the `#F01234` format you find there, just write `BKK_F01234`. For the
  sign, you may use unicode characters as long as your font has an implementation for that.
  The space character is also OK. My example stops are situated at Zivatar utca, Rózsadomb hill, 
  where buses are going
  [upwards the hill](https://futar.bkk.hu/stop/BKK_F00230) and
  [downwards to the city](https://futar.bkk.hu/stop/BKK_F00231). This justifies the use of `↑` and
  `↓` characters on the display.

Be sure to read these up before playing. For example, you can use python-dotenv like the code does:

```python
from dotenv import load_dotenv
load_dotenv()
```

**Play around.** I included a jupyter notebook dependency for easy experimenting. You can fire it
up or just stay at the Python terminal. First, let's download some departure times for our stops.

```python
from home_bkk_futar.client import DisplayInfo

display_info = DisplayInfo.request()
print(display_info)
```

```text
Machine: 2024-04-03 15:14:04 (UTC+0200)
Server: 2024-04-03 15:14:05 (UTC+0200)
===================================================================
↑  | 91   | Széll Kálmán tér M                  |  6:53 | LIVE     
↓  | 291  | Nyugati pályaudvar M                |  8:57 | LIVE     
↑  | 291  | Zugliget, Libegő                    | 14:55 | SCHEDULED
↓  | 91   | Nyugati pályaudvar M                | 17:08 | LIVE     
↓  | 191  | Nyugati pályaudvar M                | 17:55 | SCHEDULED
↓  | 291  | Nyugati pályaudvar M                | 25:55 | LIVE     
↑  | 91   | Széll Kálmán tér M                  | 25:55 | SCHEDULED
```

Now, using your font and your imaginary display size, you can calculate how many lines and how many
characters per line you can fit. Since I am using a 6x12 font on a 48x96 matrix, I can put 4 lines
in there with 16 characters each.

```python
formatted = display_info.format(lines=4, chars=16)
[print(line) for line in formatted]
```

```text
↑ 91  Széll   7'
↑ 291 Zuglig 15'
↓ 291 Nyugat  9'
↓ 91  Nyugat 17'
```

How will this look in reality? Let's use bdfparser to find out. You can play with fonts for a
lifetime. See some more at the [fonts](/fonts/README.md) folder.

```python
from bdfparser import Font
font = Font('fonts/6x12mono.bdf')
print(font.draw(formatted[0], mode=0))
```

```text
................................................................................................
................................................................................................
...................................................#........................................#...
..#..........###....#................###..........#....##....##.....................#####...#...
.###........#...#..##...............#...#...............#.....#.........................#...#...
#.#.#.......#...#.#.#...............#.....#####..###....#.....#........................#........
..#..........####...#................###.....#..#...#...#.....#........................#........
..#.............#...#...................#...#...####....#.....#.......................#.........
..#............#....#...............#...#..#....#.......#.....#.......................#.........
..#..........##...#####..............###..#####..###...###...###......................#.........
................................................................................................
................................................................................................
```

But what if we want some real image with some real color? The color supplier function works
something like an IKEA lamp, it cycles colors and has some pseudo-randomness in it, but it also
respects local time of day (in the night it gets darker).

```python
# Concatenate all lines into a bitmap
from bdfparser import Bitmap

full_bitmap = Bitmap.concatall([
    font.draw(line, mode=0) if line else Bitmap([6 * 16 * '0' for _ in range(12)])
    for line in formatted
], direction=0)

# Show using pillow
from home_bkk_futar.utils import get_rgb_color
from PIL import Image

bytesdict = {0: b'\x00\x00\x00', 1: bytes(get_rgb_color(display_info.server_time))}
large_bitmap = full_bitmap * 6
Image.frombytes(
  'RGB',
  (large_bitmap.width(), large_bitmap.height()), 
  large_bitmap.tobytes('RGB', bytesdict=bytesdict)
)
```

![A true view of how it will look on the matrix](/assets/display.png)

## Set It Up with a Real Matrix Display

I used the following hardware setup:
- [Raspberry Pi 3B+](https://www.raspberrypi.com/products/raspberry-pi-3-model-b-plus/)
  with its official 5V/2.5A DC adapter.
- WaveShare flexible RGB full-color LED matrix panel, 2.5mm Pitch, 96x48 pixels, see listing 
  [here](https://www.waveshare.com/rgb-matrix-p2.5-96x48-f.htm) and wiki page
  [here](https://www.waveshare.com/wiki/RGB-Matrix-P2.5-96x48-F). This panel has all needed wires
  included, but you must separately buy a strong enough power supply, 5V/4A will do.
- A button actuator is not strictly needed but quite recommended (running the display 24/7 seems
  quite like overkill...). I bought a fancy-looking but alas all-too-sensitive 
  [capacitive touch button](https://www.hestore.hu/prod_10041531.html#) and some female-female
  wiring to connect it.

The wiring (and a lot else!) is thoroughly explained at the 
[rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix/) site and the WaveShare doc also
points here. For the button, you will need to connect three wires to the free-remaining pins on
the Pi: one GND, one VCC 3.3V, and one free GPIO pin (I happened to use GPIO26).

It is strongly recommended to use the Pi in a headless mode which means it has no 
peripherals connected, and you log into it via ssh. Clone this repo onto the Pi, and also clone the
[rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix/) submodule. At this point you
should be able to step into the submodule's folder, and follow its documentation's instructions
(see e.g. [here](https://github.com/hzeller/rpi-rgb-led-matrix/?tab=readme-ov-file#lets-do-it)) to 
set up some C-based demos on your matrix.

The next step is to achieve that the Python-based demos also work. Again, follow the 
rpi-rgb-led-matrix library's Python
[instructions](https://github.com/hzeller/rpi-rgb-led-matrix/tree/master/bindings/python)
to set up and build the package on Pi (alas, you cannot pip-install it). When done, you should
be able to run the Python-based demos (like `runtext.py`) described in the doc.

When everything works, you may connect the dots: set up the environment variables for the project
as described above, and you may fire up a Python console in the project root and try out whether you
can do a `DisplayInfo.request()` call.

The project has two entry points: one for an infinite operation ([main.py](/main.py)) and one for 
the button-actuated operation ([button.py](/button.py)).

### Infinite Operation

```shell
sudo python -m main
```

This will infinitely download departure data every some seconds, and refresh the display somewhat 
more often (see configuration in [matrix.py](/home_bkk_futar/matrix.py)). Exit on a keyboard 
interrupt `Ctrl+C` or send a termination signal.

### Button Actuated Operation

```shell
sudo python -m button
```

You'll need the [RPi.GPIO](https://sourceforge.net/projects/raspberry-gpio-python/) library which
is probably pre-installed with the Python on your Pi. There are several peculiarities when operating
using a button:

**Separate process.** Once you initialize the matrix, you cannot deallocate it, and the 
rpi-rgb-led-matrix library will never stop refreshing - even if you keep it blank. This has quite
an effect on the CPU usage. In a typical use-case you want to look at the display probably 3-5 times
a day, for maybe ten minutes each. So what we can do is to use a fully separate process for button 
handling, which will spawn the matrix when needed, and fully terminate it a bit later.

**Different button types.** Buttons can operate in a variety of ways. My one is like a flip-flop
(on a push it turns on and keeps being on until I press it again), other buttons are only up while
they are pressed. What's more, my button is so sensitive that sometimes it just randomly turns on 
and off, so I needed to require the user to push it twice inside a second to treat it as a press.
Unless you choose exactly the button I bought, It's almost sure that you'll need to do some code 
tweaking here. See config and code in [button.py](/button.py).

### Services

When operating long-term, it is best to ensure that home-bkk-futar is always running. This is very 
flexibly achieved using a service unit file. See some more at the [services](/services/README.md)
folder.
