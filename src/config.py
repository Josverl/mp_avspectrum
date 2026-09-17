# Configuration for the audio spectrum visualizer.
#
# Default wiring targets a Raspberry Pi Pico 2 W with an INMP441/SPH0645 I2S
# MEMS microphone and a WS2812B NeoPixel display.

# --- I2S microphone ---------------------------------------------------------
I2S_ID = 0
PIN_SCK = 6  # bit clock
PIN_WS = 7   # word select; on rp2 this must be PIN_SCK + 1
PIN_SD = 5   # serial data out of the microphone

SAMPLE_RATE = 16000
SAMPLE_BITS = 32  # INMP441/SPH0645 send 24 bits left justified in 32 bit words
IBUF = 20000

# --- Analysis ---------------------------------------------------------------
FFT_SIZE = 128  # power of two; 128 @ 16 kHz gives 125 Hz per bin
BAND_COUNT = 8  # one per matrix column
BAND_LOW_HZ = 80
BAND_HIGH_HZ = 6000
# Fixed spectral tilt measured against quiet, music and acoustic test tones.
BAND_GAINS = (1.0, 1.1, 1.4, 1.8, 2.5, 5.0, 9.0, 14.0)

# Envelope follower (0..1 per frame); attack is fast, decay is slow.
ATTACK = 0.9
DECAY = 0.25
NOMINAL_FRAME_MS = 100.0

# Automatic gain control: the reference level decays towards the loudest band
# seen recently, so the display stays usable at any volume.
AGC_DECAY = 0.97
AGC_MIN_REFERENCE = 1000.0

# Peak dots fall this many rows per frame (0 disables them).
PEAK_FALL = 0.04

# --- Display ----------------------------------------------------------------
PIN_NEOPIXEL = 1

# DISPLAY_MODE = "strip"  # "strip" for a linear strip, "matrix" for vertical bars
# MATRIX_WIDTH = 18
# MATRIX_HEIGHT = 1

DISPLAY_MODE = "matrix"  # "strip" for a linear strip, "matrix" for vertical bars
MATRIX_WIDTH = 8
MATRIX_HEIGHT = 8

# True when the matrix is wired boustrophedon (every other row/column reversed).
MATRIX_SERPENTINE = True
# True when pixel 0 walks along a column, False when it walks along a row.
MATRIX_COLUMN_MAJOR = True
# 0..255, keep low unless the LEDs have a suitable external power supply.
BRIGHTNESS = 40

# Low to high frequency colour ramp, with one entry per analysis band.
PALETTE = (
    (0, 255, 0),
    (0, 255, 0),
    (64, 255, 0),
    (128, 255, 0),
    (200, 255, 0),
    (255, 200, 0),
    (255, 96, 0),
    (255, 0, 0),
)
PEAK_COLOR = (255, 255, 255)
