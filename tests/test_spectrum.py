# Host side tests for the parts that do not need hardware.
#
#   cd mp_avspectrum && python3 -m unittest discover tests

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from levels import Levels  # noqa: E402
from spectrum import Spectrum  # noqa: E402

SAMPLE_RATE = 16000
SIZE = 128
BANDS = 8


def tone(frequency, size=SIZE, rate=SAMPLE_RATE, amplitude=10000.0):
    return [amplitude * math.sin(2.0 * math.pi * frequency * i / rate) for i in range(size)]


class TestSpectrum(unittest.TestCase):
    def setUp(self):
        self.spectrum = Spectrum(SIZE, SAMPLE_RATE, BANDS, 80, 6000)

    def test_rejects_non_power_of_two(self):
        with self.assertRaises(ValueError):
            Spectrum(100, SAMPLE_RATE, BANDS, 80, 6000)

    def test_rejects_wrong_number_of_band_gains(self):
        with self.assertRaises(ValueError):
            Spectrum(SIZE, SAMPLE_RATE, BANDS, 80, 6000, [1.0])

    def test_band_edges_are_increasing(self):
        edges = self.spectrum._band_edges
        self.assertEqual(len(edges), BANDS + 1)
        for i in range(BANDS):
            self.assertLess(edges[i], edges[i + 1])

    def test_matches_naive_dft(self):
        samples = tone(1000)
        self.spectrum.compute(samples)
        windowed = [samples[i] * self.spectrum._window[i] for i in range(SIZE)]
        for bin_index in (1, 5, 8, 17, 40):
            real = sum(
                windowed[n] * math.cos(-2.0 * math.pi * bin_index * n / SIZE) for n in range(SIZE)
            )
            imag = sum(
                windowed[n] * math.sin(-2.0 * math.pi * bin_index * n / SIZE) for n in range(SIZE)
            )
            expected = math.sqrt(real * real + imag * imag)
            self.assertAlmostEqual(
                self.spectrum.magnitude[bin_index], expected, delta=max(1.0, expected * 1e-3)
            )

    def test_peak_bin_follows_tone_frequency(self):
        for frequency in (250, 1000, 3000):
            self.spectrum.compute(tone(frequency))
            magnitude = self.spectrum.magnitude
            peak = max(range(1, len(magnitude)), key=lambda i: magnitude[i])
            self.assertAlmostEqual(peak * SAMPLE_RATE / SIZE, frequency, delta=SAMPLE_RATE / SIZE)

    def test_low_tone_lights_low_band(self):
        low = list(self.spectrum.compute(tone(150)))
        high = list(self.spectrum.compute(tone(4000)))
        self.assertEqual(max(range(BANDS), key=lambda i: low[i]), 0)
        self.assertGreater(max(range(BANDS), key=lambda i: high[i]), 4)

    def test_silence_produces_no_energy(self):
        bands = self.spectrum.compute([0.0] * SIZE)
        for value in bands:
            self.assertAlmostEqual(value, 0.0)

    def test_applies_band_gains(self):
        plain = list(self.spectrum.compute(tone(1000)))
        weighted = Spectrum(SIZE, SAMPLE_RATE, BANDS, 80, 6000, [2.0] * BANDS)
        gained = weighted.compute(tone(1000))
        for band in range(BANDS):
            self.assertAlmostEqual(gained[band], plain[band] * 2.0, delta=1.0)

    def test_short_block_is_zero_padded(self):
        bands = self.spectrum.compute(tone(1000, size=SIZE), count=SIZE // 2)
        self.assertGreater(max(bands), 0.0)


class TestLevels(unittest.TestCase):
    def make(self):
        return Levels(BANDS, 0.7, 0.25, 0.995, 2000.0, 0.12)

    def test_levels_stay_normalised(self):
        levels = self.make()
        for _ in range(50):
            values = levels.update([1e6] * BANDS)
        for value in values:
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)

    def test_quiet_input_stays_near_zero(self):
        levels = self.make()
        for _ in range(20):
            values = levels.update([1.0] * BANDS)
        self.assertLess(max(values), 0.01)

    def test_decay_after_loud_burst(self):
        levels = self.make()
        for _ in range(10):
            levels.update([1e5] * BANDS)
        loud = levels.values[0]
        for _ in range(20):
            levels.update([0.0] * BANDS)
        self.assertLess(levels.values[0], loud)

    def test_peaks_never_below_level(self):
        levels = self.make()
        for value in (1e5, 0.0, 5e4, 0.0):
            levels.update([value] * BANDS)
            for i in range(BANDS):
                self.assertGreaterEqual(levels.peaks[i], levels.values[i] - 1e-6)

    def test_transient_peak_precedes_smoothed_level(self):
        levels = Levels(BANDS, 0.5, 0.25, 0.995, 2000.0, 0.04)
        levels.update([1e5] + [0.0] * (BANDS - 1))
        self.assertEqual(levels.peaks[0], 1.0)
        self.assertEqual(levels.values[0], 0.5)

    def test_dynamics_are_independent_of_frame_rate(self):
        slow = self.make()
        fast = self.make()
        for _ in range(10):
            slow.update([1e5] * BANDS, 100.0)
        for _ in range(20):
            fast.update([1e5] * BANDS, 50.0)
        for band in range(BANDS):
            self.assertAlmostEqual(slow.values[band], fast.values[band], places=5)
            self.assertAlmostEqual(slow.peaks[band], fast.peaks[band], places=5)
        self.assertAlmostEqual(slow.reference, fast.reference, places=5)

    def test_reset(self):
        levels = self.make()
        levels.update([1e5] * BANDS)
        levels.reset()
        self.assertEqual(max(levels.values), 0.0)
        self.assertEqual(max(levels.peaks), 0.0)


if __name__ == "__main__":
    unittest.main()
