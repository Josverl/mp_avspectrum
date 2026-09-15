# Host side tests for the matrix mapping, using stubs for machine/neopixel.

import os
import sys
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class _FakePin:
    OUT = 1

    def __init__(self, number, mode=None):
        self.number = number
        self.mode = mode


class _FakeNeoPixel:
    def __init__(self, pin, count):
        self.pin = pin
        self.buffer = [(0, 0, 0)] * count
        self.writes = 0

    def __len__(self):
        return len(self.buffer)

    def __setitem__(self, index, value):
        self.buffer[index] = value

    def __getitem__(self, index):
        return self.buffer[index]

    def fill(self, color):
        self.buffer = [color] * len(self.buffer)

    def write(self):
        self.writes += 1


machine = types.ModuleType("machine")
machine.Pin = _FakePin
sys.modules.setdefault("machine", machine)

neopixel = types.ModuleType("neopixel")
neopixel.NeoPixel = _FakeNeoPixel
sys.modules.setdefault("neopixel", neopixel)

from display import BarsRenderer, Matrix, StripRenderer  # noqa: E402

PALETTE = tuple((32 * i, 255, 0) for i in range(8))


class TestMatrixMapping(unittest.TestCase):
    def matrix(self, **kwargs):
        kwargs.setdefault("brightness", 255)
        return Matrix(0, 8, 8, **kwargs)

    def test_every_pixel_has_a_unique_index(self):
        for serpentine in (False, True):
            for column_major in (False, True):
                panel = self.matrix(serpentine=serpentine, column_major=column_major)
                seen = {panel.index(x, y) for x in range(8) for y in range(8)}
                self.assertEqual(len(seen), 64)
                self.assertEqual(min(seen), 0)
                self.assertEqual(max(seen), 63)

    def test_progressive_row_major_origin(self):
        panel = self.matrix(serpentine=False, column_major=False)
        # Strip starts top left, so (0, 7) is pixel 0 and (0, 0) starts the last row.
        self.assertEqual(panel.index(0, 7), 0)
        self.assertEqual(panel.index(7, 7), 7)
        self.assertEqual(panel.index(0, 0), 56)

    def test_serpentine_reverses_alternate_rows(self):
        panel = self.matrix(serpentine=True, column_major=False)
        self.assertEqual(panel.index(0, 7), 0)
        # Second row from the top runs right to left.
        self.assertEqual(panel.index(7, 6), 8)
        self.assertEqual(panel.index(0, 6), 15)

    def test_brightness_scales_colour(self):
        panel = self.matrix(brightness=128)
        panel.set(0, 0, (255, 255, 255))
        self.assertEqual(panel.np[panel.index(0, 0)], (128, 128, 128))


class TestBarsRenderer(unittest.TestCase):
    def renderer(self, peak_color=(255, 255, 255)):
        return BarsRenderer(Matrix(0, 8, 8, brightness=255), PALETTE, peak_color)

    def test_palette_must_cover_the_matrix(self):
        with self.assertRaises(ValueError):
            BarsRenderer(Matrix(0, 8, 8), PALETTE[:4])

    def test_full_level_lights_whole_column(self):
        renderer = self.renderer(peak_color=None)
        renderer.render([1.0] + [0.0] * 7)
        panel = renderer.matrix
        for y in range(8):
            self.assertEqual(panel.np[panel.index(0, y)], PALETTE[y])
        for y in range(8):
            self.assertEqual(panel.np[panel.index(1, y)], (0, 0, 0))

    def test_levels_are_clamped(self):
        renderer = self.renderer(peak_color=None)
        renderer.render([5.0, -5.0] + [0.0] * 6)
        panel = renderer.matrix
        self.assertEqual(panel.np[panel.index(0, 7)], PALETTE[7])
        self.assertEqual(panel.np[panel.index(1, 0)], (0, 0, 0))

    def test_peak_dot_sits_above_the_bar(self):
        renderer = self.renderer()
        renderer.render([0.25] + [0.0] * 7, [1.0] + [0.0] * 7)
        panel = renderer.matrix
        self.assertEqual(panel.np[panel.index(0, 7)], (255, 255, 255))
        self.assertEqual(panel.np[panel.index(0, 1)], PALETTE[1])

    def test_render_writes_once_per_frame(self):
        renderer = self.renderer()
        renderer.render([0.5] * 8, [0.5] * 8)
        self.assertEqual(renderer.matrix.np.writes, 1)


class TestStripRenderer(unittest.TestCase):
    def test_uses_one_pixel_per_band(self):
        renderer = StripRenderer(Matrix(0, 18, 1, brightness=255))
        renderer.render([0.0] * 7 + [1.0])

        self.assertEqual(renderer.matrix.np[0], (0, 0, 0))
        self.assertEqual(renderer.matrix.np[7], (255, 0, 0))
        self.assertEqual(renderer.matrix.np[8], (0, 0, 0))
        self.assertEqual(renderer.matrix.np[17], (0, 0, 0))
        self.assertEqual(renderer.matrix.np.writes, 1)

    def test_shifts_color_and_brightness_by_level(self):
        renderer = StripRenderer(Matrix(0, 18, 1, brightness=255))
        renderer.render([0.25, 0.5, 1.0])

        self.assertEqual(renderer.matrix.np[0], (63, 127, 0))
        self.assertEqual(renderer.matrix.np[1], (180, 180, 0))
        self.assertEqual(renderer.matrix.np[2], (255, 0, 0))


if __name__ == "__main__":
    unittest.main()
