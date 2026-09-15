# Fixed-size real FFT and log spaced band grouping.
#
# Everything is preallocated at construction time so that the analysis loop
# does not allocate and therefore cannot trigger a garbage collection pause.

import math
from array import array


def _is_power_of_two(n):
    return n > 1 and (n & (n - 1)) == 0


class Spectrum:
    """Compute `band_count` log spaced band magnitudes from a block of samples."""

    def __init__(
        self,
        size,
        sample_rate,
        band_count,
        low_hz,
        high_hz,
    ):
        if not _is_power_of_two(size):
            raise ValueError("FFT size must be a power of two")

        self.size = size
        self.sample_rate = sample_rate
        self.band_count = band_count

        self._re = array("f", bytes(4 * size))
        self._im = array("f", bytes(4 * size))
        self.magnitude = array("f", bytes(4 * (size // 2)))
        self.bands = array("f", bytes(4 * band_count))

        # Hann window, applied to reduce spectral leakage.
        self._window = array("f", bytes(4 * size))
        for i in range(size):
            self._window[i] = 0.5 - 0.5 * math.cos(2.0 * math.pi * i / size)

        # Twiddle factors for the decimation in time butterflies.
        half = size // 2
        self._cos = array("f", bytes(4 * half))
        self._sin = array("f", bytes(4 * half))
        for i in range(half):
            angle = -2.0 * math.pi * i / size
            self._cos[i] = math.cos(angle)
            self._sin[i] = math.sin(angle)

        self._reverse = array("H", bytes(2 * size))
        bits = 0
        while (1 << bits) < size:
            bits += 1
        for i in range(size):
            j = 0
            value = i
            for _ in range(bits):
                j = (j << 1) | (value & 1)
                value >>= 1
            self._reverse[i] = j

        self._band_edges = self._make_band_edges(band_count, low_hz, high_hz)

    def _make_band_edges(self, band_count, low_hz, high_hz):
        """Return band_count + 1 FFT bin indices spaced logarithmically."""
        bin_width = self.sample_rate / self.size
        max_bin = self.size // 2
        low = max(1, int(low_hz / bin_width))
        high = min(max_bin, max(low + band_count, int(high_hz / bin_width)))

        edges = array("H", bytes(2 * (band_count + 1)))
        ratio = math.log(high / low) / band_count
        previous = low
        edges[0] = low
        for i in range(1, band_count + 1):
            edge = int(low * math.exp(ratio * i) + 0.5)
            # Guarantee that every band owns at least one bin.
            if edge <= previous:
                edge = previous + 1
            if edge > high:
                edge = high
            edges[i] = edge
            previous = edge
        return edges

    def compute(self, samples, count=None):
        """Analyse `samples` (a sequence of numbers) and return the band array."""
        size = self.size
        re = self._re
        im = self._im
        window = self._window

        if count is None:
            count = len(samples)
        if count > size:
            count = size

        for i in range(count):
            re[i] = samples[i] * window[i]
        for i in range(count, size):
            re[i] = 0.0
        for i in range(size):
            im[i] = 0.0

        self._fft()
        self._magnitudes()
        self._group()
        return self.bands

    def _fft(self):
        size = self.size
        re = self._re
        im = self._im
        reverse = self._reverse

        for i in range(size):
            j = reverse[i]
            if j > i:
                re[i], re[j] = re[j], re[i]
                im[i], im[j] = im[j], im[i]

        span = 2
        while span <= size:
            half = span >> 1
            step = size // span
            for start in range(0, size, span):
                index = 0
                for offset in range(start, start + half):
                    wr = self._cos[index]
                    wi = self._sin[index]
                    index += step
                    pair = offset + half
                    tr = wr * re[pair] - wi * im[pair]
                    ti = wr * im[pair] + wi * re[pair]
                    re[pair] = re[offset] - tr
                    im[pair] = im[offset] - ti
                    re[offset] += tr
                    im[offset] += ti
            span <<= 1

    def _magnitudes(self):
        re = self._re
        im = self._im
        magnitude = self.magnitude
        for i in range(len(magnitude)):
            r = re[i]
            m = im[i]
            magnitude[i] = math.sqrt(r * r + m * m)

    def _group(self):
        magnitude = self.magnitude
        edges = self._band_edges
        bands = self.bands
        for band in range(self.band_count):
            start = edges[band]
            stop = edges[band + 1]
            if stop <= start:
                stop = start + 1
            total = 0.0
            for i in range(start, stop):
                total += magnitude[i]
            bands[band] = total / (stop - start)
        return bands
