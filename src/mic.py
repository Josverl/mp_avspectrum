# I2S MEMS microphone capture.

from array import array
from machine import I2S, Pin


class Microphone:
    """Blocking block reads from an I2S microphone, scaled and DC corrected."""

    def __init__(
        self,
        i2s_id,
        sck,
        ws,
        sd,
        sample_rate,
        block_size,
        bits=32,
        ibuf=20000,
    ):
        if bits not in (16, 32):
            raise ValueError("bits must be 16 or 32")

        self.block_size = block_size
        self.bits = bits
        # Raw DMA target: one signed word per sample, native byte order.
        self._raw = array("i" if bits == 32 else "h", bytes((bits // 8) * block_size))
        self._view = memoryview(self._raw)
        self.samples = array("f", bytes(4 * block_size))

        self.i2s = I2S(
            i2s_id,
            sck=Pin(sck),
            ws=Pin(ws),
            sd=Pin(sd),
            mode=I2S.RX,
            bits=bits,
            format=I2S.MONO,
            rate=sample_rate,
            ibuf=ibuf,
        )

        for _ in range(16):
            self.i2s.readinto(self._view)

    def read(self):
        """Read one block and return it as floats with the DC offset removed."""
        read_bytes = self.i2s.readinto(self._view)
        count = read_bytes // (self.bits // 8)
        if count > self.block_size:
            count = self.block_size

        raw = self._raw
        samples = self.samples
        # 24 bit data arrives left justified in 32 bit words; bring it back to
        # roughly 16 bit full scale so the analysis numbers stay small.
        shift = 16 if self.bits == 32 else 0

        total = 0.0
        for i in range(count):
            value = float(raw[i] >> shift) if shift else float(raw[i])
            samples[i] = value
            total += value

        if count:
            offset = total / count
            for i in range(count):
                samples[i] -= offset

        return count

    def deinit(self):
        self.i2s.deinit()
