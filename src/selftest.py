# Bring up helpers: run each step on its own before starting main.run().
#
#   import selftest
#   selftest.matrix()   # check pixel order, orientation and brightness
#   selftest.mic()      # check that the microphone produces sane levels
#   selftest.bands()    # check the FFT and band mapping

from array import array
import time

import config
from display import BarsRenderer, Matrix, StripRenderer
from levels import Levels
from machine import I2S, Pin, freq
from mic import Microphone
from spectrum import Spectrum


def _matrix():
    return Matrix(
        config.PIN_NEOPIXEL,
        config.MATRIX_WIDTH,
        config.MATRIX_HEIGHT,
        serpentine=config.MATRIX_SERPENTINE,
        column_major=config.MATRIX_COLUMN_MAJOR,
        brightness=config.BRIGHTNESS,
    )


def _microphone():
    freq(config.CPU_FREQ)
    return Microphone(
        config.I2S_ID,
        config.PIN_SCK,
        config.PIN_WS,
        config.PIN_SD,
        config.SAMPLE_RATE,
        config.FFT_SIZE,
        bits=config.SAMPLE_BITS,
        ibuf=config.IBUF,
        capture_blocks=config.CAPTURE_BLOCKS,
    )


def _renderer():
    panel = _matrix()
    if config.DISPLAY_MODE == "strip":
        return StripRenderer(panel)
    return BarsRenderer(panel, config.PALETTE, config.PEAK_COLOR)


def matrix(delay_ms=120):
    """Walk one pixel through the panel: bottom left first, column by column."""
    panel = _matrix()
    for x in range(panel.width):
        for y in range(panel.height):
            panel.clear()
            panel.set(x, y, (255, 255, 255))
            panel.show()
            time.sleep_ms(delay_ms)
    panel.clear()
    panel.show()


def mic(frames=2000):
    """Print peak sample values; they should rise when you make a noise."""
    microphone = _microphone()
    try:
        for _ in range(frames):
            count = microphone.read()
            peak = 0.0
            for i in range(count):
                value = microphone.samples[i]
                if value < 0:
                    value = -value
                if value > peak:
                    peak = value
            print(f"samples={count} peak={peak:.0f}")
    finally:
        microphone.deinit()


def mic_channels(frames=20):
    """Print raw left/right I2S activity to diagnose wiring and channel selection."""
    frame_count = config.FFT_SIZE
    raw = array("i", bytes(8 * frame_count))
    audio = I2S(
        config.I2S_ID,
        sck=Pin(config.PIN_SCK),
        ws=Pin(config.PIN_WS),
        sd=Pin(config.PIN_SD),
        mode=I2S.RX,
        bits=32,
        format=I2S.STEREO,
        rate=config.SAMPLE_RATE,
        ibuf=config.IBUF,
    )
    try:
        for _ in range(frames):
            words = audio.readinto(raw) // 4
            if words < 2:
                print("no complete stereo frame")
                continue

            left_min = left_max = raw[0]
            right_min = right_max = raw[1]
            left_nonzero = 0
            right_nonzero = 0
            for i in range(0, words - 1, 2):
                left_value = raw[i]
                right_value = raw[i + 1]
                left_min = min(left_min, left_value)
                left_max = max(left_max, left_value)
                right_min = min(right_min, right_value)
                right_max = max(right_max, right_value)
                if left_value != 0:
                    left_nonzero += 1
                if right_value != 0:
                    right_nonzero += 1
            print(
                "left=({},{}) nz={} right=({},{}) nz={}".format(
                    left_min,
                    left_max,
                    left_nonzero,
                    right_min,
                    right_max,
                    right_nonzero,
                )
            )
    finally:
        audio.deinit()


def bands(frames=200):
    """Print band levels; whistling should move the energy between columns."""
    microphone = _microphone()
    spectrum = Spectrum(
        config.FFT_SIZE,
        config.SAMPLE_RATE,
        config.BAND_COUNT,
        config.BAND_LOW_HZ,
        config.BAND_HIGH_HZ,
        config.BAND_GAINS,
    )
    levels = Levels(
        config.BAND_COUNT,
        config.ATTACK,
        config.DECAY,
        config.AGC_DECAY,
        config.AGC_MIN_REFERENCE,
        config.PEAK_FALL,
    )
    try:
        for _ in range(frames):
            count = microphone.read()
            values = levels.update(spectrum.compute(microphone.samples, count))
            print(" ".join("{:4.2f}".format(v) for v in values))
    finally:
        microphone.deinit()


def visualize(frames=200, verbose=True):
    """Run the full pipeline and optionally print each rendered frame."""
    microphone = _microphone()
    spectrum = Spectrum(
        config.FFT_SIZE,
        config.SAMPLE_RATE,
        config.BAND_COUNT,
        config.BAND_LOW_HZ,
        config.BAND_HIGH_HZ,
        config.BAND_GAINS,
    )
    levels = Levels(
        config.BAND_COUNT,
        config.ATTACK,
        config.DECAY,
        config.AGC_DECAY,
        config.AGC_MIN_REFERENCE,
        config.PEAK_FALL,
    )
    renderer = _renderer()
    try:
        for _ in range(frames):
            count = microphone.read()
            values = levels.update(spectrum.compute(microphone.samples, count))
            renderer.render(values, levels.peaks)
            if verbose:
                if config.DISPLAY_MODE == "strip":
                    shades = " .:-=+*#%@"
                    preview = ""
                    for x in range(min(renderer.matrix.width, len(values))):
                        shade = int(values[x] * (len(shades) - 1) + 0.5)
                        preview += shades[shade]
                    print(
                        "{}  {}".format(
                            preview,
                            " ".join("{:.2f}".format(value) for value in values),
                        )
                    )
                else:
                    print(" ".join("{:.2f}".format(value) for value in values))
    finally:
        renderer.matrix.clear()
        renderer.matrix.show()
        microphone.deinit()
