# Per band envelope following, automatic gain control and peak hold.

from array import array


class Levels:
    """Convert raw band magnitudes into normalised 0..1 levels."""

    def __init__(
        self,
        band_count,
        attack,
        decay,
        agc_decay,
        agc_min_reference,
        peak_fall,
        nominal_frame_ms=100.0,
    ):
        self.band_count = band_count
        self.attack = attack
        self.decay = decay
        self.agc_decay = agc_decay
        self.agc_min_reference = agc_min_reference
        self.peak_fall = peak_fall
        self.nominal_frame_ms = nominal_frame_ms
        self.reference = agc_min_reference

        self.values = array("f", bytes(4 * band_count))
        self.peaks = array("f", bytes(4 * band_count))

    def update(self, bands, elapsed_ms=None):
        """Feed one frame of band magnitudes, return normalised levels."""
        frame_scale = 1.0 if elapsed_ms is None else elapsed_ms / self.nominal_frame_ms
        if frame_scale < 0.0:
            frame_scale = 0.0

        loudest = 0.0
        for value in bands:
            if value > loudest:
                loudest = value

        # The reference tracks the loudest band instantly when it grows and
        # slowly relaxes back down, which keeps quiet passages visible.
        reference = self.reference * self.agc_decay**frame_scale
        if loudest > reference:
            reference = loudest
        if reference < self.agc_min_reference:
            reference = self.agc_min_reference
        self.reference = reference

        values = self.values
        peaks = self.peaks
        attack = 1.0 - (1.0 - self.attack) ** frame_scale
        decay = 1.0 - (1.0 - self.decay) ** frame_scale
        fall = self.peak_fall * frame_scale

        for i in range(self.band_count):
            target = bands[i] / reference
            if target > 1.0:
                target = 1.0
            current = values[i]
            rate = attack if target > current else decay
            current += (target - current) * rate
            values[i] = current

            peak = peaks[i] - fall
            if target > peak:
                peak = target
            if current > peak:
                peak = current
            elif peak < 0.0:
                peak = 0.0
            peaks[i] = peak

        return values

    def reset(self):
        for i in range(self.band_count):
            self.values[i] = 0.0
            self.peaks[i] = 0.0
        self.reference = self.agc_min_reference
