# NeoPixel matrix rendering for the spectrum bars.

import time
from array import array
from machine import Pin
from neopixel import NeoPixel

try:
    import rp2
except ImportError:
    rp2 = None


if rp2 is not None:
    @rp2.asm_pio(
        sideset_init=rp2.PIO.OUT_LOW,
        out_shiftdir=rp2.PIO.SHIFT_LEFT,
        autopull=True,
        pull_thresh=24,
    )
    def _ws2812():
        t1 = 2
        t2 = 5
        t3 = 3
        label("bitloop")
        out(x, 1).side(0)[t3 - 1]
        jmp(not_x, "do_zero").side(1)[t1 - 1]
        jmp("bitloop").side(1)[t2 - 1]
        label("do_zero")
        nop().side(0)[t2 - 1]


    class _RP2NeoPixel:
        def __init__(self, pin, count):
            self._pixels = array("I", bytes(4 * count))
            self._sm = rp2.StateMachine(4, _ws2812, freq=8_000_000, sideset_base=pin)
            self._sm.active(1)

        def __setitem__(self, index, color):
            red, green, blue = color
            self._pixels[index] = (green << 16) | (red << 8) | blue

        def fill(self, color):
            red, green, blue = color
            packed = (green << 16) | (red << 8) | blue
            for index in range(len(self._pixels)):
                self._pixels[index] = packed

        def write(self):
            self._sm.put(self._pixels, 8)
            time.sleep_us(80)


class Matrix:
    """A small 2D wrapper around `neopixel.NeoPixel`.

    Pixel (0, 0) is the bottom left corner of the display.
    """

    def __init__(
        self,
        pin,
        width,
        height,
        serpentine=True,
        column_major=False,
        brightness=40,
    ):
        self.width = width
        self.height = height
        self.serpentine = serpentine
        self.column_major = column_major
        self.brightness = brightness
        output = Pin(pin, Pin.OUT)
        if rp2 is None:
            self.np = NeoPixel(output, width * height)
        else:
            self.np = _RP2NeoPixel(output, width * height)

    def index(self, x, y):
        """Map a bottom left based coordinate to a strip index."""
        # The strip starts at the bottom left corner of the panel.
        row = y
        if self.column_major:
            major, minor, length = x, row, self.height
        else:
            major, minor, length = row, x, self.width
        if self.serpentine and (major & 1):
            minor = length - 1 - minor
        return major * length + minor

    def set(self, x, y, color):
        scale = self.brightness
        self.np[self.index(x, y)] = (
            color[0] * scale // 255,
            color[1] * scale // 255,
            color[2] * scale // 255,
        )

    def clear(self):
        self.np.fill((0, 0, 0))

    def show(self):
        self.np.write()


class StripRenderer:
    """Render one frequency band per LED, green through red by level."""

    def __init__(self, matrix):
        if matrix.height != 1:
            raise ValueError("strip display height must be 1")
        self.matrix = matrix

    def render(self, values, peaks=None):
        matrix = self.matrix
        matrix.clear()

        for x in range(min(matrix.width, len(values))):
            level = values[x]
            if level < 0.0:
                level = 0.0
            elif level > 1.0:
                level = 1.0

            if level < 0.5:
                color = (int(level * 510), 255, 0)
            else:
                color = (255, int((1.0 - level) * 510), 0)
            intensity = level**0.5
            matrix.set(x, 0, tuple(int(component * intensity) for component in color))

        matrix.show()


class BarsRenderer:
    """Draw one vertical bar per band, with an optional peak dot."""

    def __init__(self, matrix, palette, peak_color=None):
        if len(palette) < matrix.height:
            raise ValueError("palette needs one colour per matrix row")
        self.matrix = matrix
        self.palette = palette
        self.peak_color = peak_color

    def render(self, values, peaks=None):
        matrix = self.matrix
        height = matrix.height
        matrix.clear()

        for x in range(min(matrix.width, len(values))):
            level = values[x]
            if level < 0.0:
                level = 0.0
            elif level > 1.0:
                level = 1.0
            lit = int(level * height + 0.5)
            for y in range(lit):
                matrix.set(x, y, self.palette[y])

            if self.peak_color is not None and peaks is not None:
                peak = peaks[x]
                if peak > 0.0:
                    y = int(peak * height + 0.5) - 1
                    if y >= height:
                        y = height - 1
                    if y >= lit and y >= 0:
                        matrix.set(x, y, self.peak_color)

        matrix.show()
