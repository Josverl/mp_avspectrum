# NeoPixel matrix rendering for the spectrum bars.

from machine import Pin
from neopixel import NeoPixel


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
        self.np = NeoPixel(Pin(pin, Pin.OUT), width * height)

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
