# I2S MEMS microphone capture.

from array import array
from machine import I2S, Pin
import select


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
        capture_blocks=1,
    ):
        if bits not in (16, 32):
            raise ValueError("bits must be 16 or 32")
        if capture_blocks < 1:
            raise ValueError("capture_blocks must be positive")

        self.block_size = block_size
        self.bits = bits
        self.capture_blocks = capture_blocks
        # Raw DMA target: one signed word per sample, native byte order.
        self._raw = array("i" if bits == 32 else "h", bytes((bits // 8) * block_size))
        self._best_raw = array("i" if bits == 32 else "h", bytes((bits // 8) * block_size))
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
        self._poll = select.poll()
        self._poll.register(self.i2s, select.POLLIN)

        for _ in range(64):
            self.i2s.readinto(self._view)

    def read(self):
        """Drain a capture window and retain its strongest DC-corrected block."""
        raw = self._raw
        best_raw = self._best_raw
        samples = self.samples
        best_score = -1
        best_count = 0

        for block in range(self.capture_blocks):
            if block and not self._poll.poll(0):
                break
            read_bytes = self.i2s.readinto(self._view)
            count = read_bytes // (self.bits // 8)
            if count > self.block_size:
                count = self.block_size

            if count:
                # Ranges of 16-sample sums attenuate high-frequency percussion
                # while preserving the kick/bass energy used to select a block.
                minimum = None
                maximum = None
                for start in range(0, count, 16):
                    group_total = 0
                    stop = min(start + 16, count)
                    for i in range(start, stop):
                        group_total += raw[i]
                    if minimum is None or group_total < minimum:
                        minimum = group_total
                    if maximum is None or group_total > maximum:
                        maximum = group_total
                score = maximum - minimum
            else:
                score = 0

            if score > best_score:
                best_score = score
                best_count = count
                for i in range(count):
                    best_raw[i] = raw[i]

        # RP2 I2S capture leaves seven padding bits below the INMP441 payload.
        # Preserve that payload while retaining the existing 16-bit-like scale.
        shift = 7 if self.bits == 32 else 0
        scale = 1.0 / 512.0 if self.bits == 32 else 1.0
        total = 0.0
        for i in range(best_count):
            value = float(best_raw[i] >> shift) * scale if shift else float(best_raw[i])
            samples[i] = value
            total += value

        if best_count:
            offset = total / best_count
            for i in range(best_count):
                samples[i] -= offset

        return best_count

    def deinit(self):
        self.i2s.deinit()
