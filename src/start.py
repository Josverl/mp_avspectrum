# Audio spectrum visualizer: I2S microphone -> FFT -> 8x8 NeoPixel matrix.

import gc
import time

import config
from display import BarsRenderer, Matrix, StripRenderer
from levels import Levels
from mic import Microphone
from spectrum import Spectrum


def build():
    microphone = Microphone(
        config.I2S_ID,
        config.PIN_SCK,
        config.PIN_WS,
        config.PIN_SD,
        config.SAMPLE_RATE,
        config.FFT_SIZE,
        bits=config.SAMPLE_BITS,
        ibuf=config.IBUF,
    )
    spectrum = Spectrum(
        config.FFT_SIZE,
        config.SAMPLE_RATE,
        config.BAND_COUNT,
        config.BAND_LOW_HZ,
        config.BAND_HIGH_HZ,
    )
    levels = Levels(
        config.BAND_COUNT,
        config.ATTACK,
        config.DECAY,
        config.AGC_DECAY,
        config.AGC_MIN_REFERENCE,
        config.PEAK_FALL,
    )
    matrix = Matrix(
        config.PIN_NEOPIXEL,
        config.MATRIX_WIDTH,
        config.MATRIX_HEIGHT,
        serpentine=config.MATRIX_SERPENTINE,
        column_major=config.MATRIX_COLUMN_MAJOR,
        brightness=config.BRIGHTNESS,
    )
    if config.DISPLAY_MODE == "strip":
        renderer = StripRenderer(matrix)
    elif config.DISPLAY_MODE == "matrix":
        renderer = BarsRenderer(
            matrix,
            config.PALETTE,
            config.PEAK_COLOR if config.PEAK_FALL > 0 else None,
        )
    else:
        raise ValueError("DISPLAY_MODE must be 'strip' or 'matrix'")
    return microphone, spectrum, levels, renderer


def run():
    microphone, spectrum, levels, renderer = build()
    # Collect once up front; the loop itself does not allocate.
    gc.collect()
    try:
        while True:
            count = microphone.read()
            bands = spectrum.compute(microphone.samples, count)
            values = levels.update(bands)
            renderer.render(values, levels.peaks)
    except KeyboardInterrupt:
        pass
    finally:
        renderer.matrix.clear()
        renderer.matrix.show()
        microphone.deinit()


def bench(frames=50):
    """Report the achievable frame rate for the current configuration."""
    microphone, spectrum, levels, renderer = build()
    gc.collect()
    try:
        start = time.ticks_ms()
        for _ in range(frames):
            count = microphone.read()
            bands = spectrum.compute(microphone.samples, count)
            renderer.render(levels.update(bands), levels.peaks)
        elapsed = time.ticks_diff(time.ticks_ms(), start)
    finally:
        microphone.deinit()
    print("{} frames in {} ms ({:.1f} fps)".format(frames, elapsed, 1000.0 * frames / elapsed))


if __name__ == "__main__":
    time.sleep(5)  # Small delay to allow for any setup before running
    run()

