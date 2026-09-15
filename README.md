# mp_avspectrum

A MicroPython music/audio spectrum visualizer: an I2S MEMS microphone is
sampled, analysed with an FFT and rendered as eight bars on a WS2812B 8x8
NeoPixel matrix.

Target board: **Raspberry Pi Pico 2 W** (RP2350), but the code only relies on
`machine.I2S` and `neopixel`, so any port providing both will work.

## Hardware

| Part | Notes |
| --- | --- |
| Raspberry Pi Pico 2 W | RP2350, running a standard MicroPython build |
| I2S MEMS microphone | INMP441 or SPH0645LM4H, 3.3 V |
| WS2812B 8x8 matrix | 64 pixels |
| 5 V supply | share ground with the Pico; keep brightness low on USB power |

### Wiring (defaults from `config.py`)

Microphone:

| Mic | Pico 2 W |
| --- | --- |
| SCK | GP16 |
| WS | GP17 (**must be SCK + 1 on the rp2 port**) |
| SD | GP18 |
| L/R | GND (left channel) |
| VDD / GND | 3V3 / GND |

Matrix:

| Matrix | Pico 2 W |
| --- | --- |
| DIN | GP0 (300-500 Ohm series resistor recommended) |
| 5V | external 5 V supply |
| GND | supply GND **and** Pico GND |

A 74AHCT125 level shifter on the data line makes the 3.3 V to 5 V transition
reliable; many panels also work without one.

## Install

Copy the modules to the board, for example with `mpremote`:

```
mpremote connect auto fs cp config.py display.py levels.py main.py mic.py selftest.py spectrum.py :
```

Then run it:

```
mpremote connect auto run main.py
```

`main.py` starts the visualizer automatically when it is imported as the boot
script; while developing, use `import main; main.run()` from the REPL.

## Bring-up order

Test one stage at a time before running the full loop:

```python
import selftest
selftest.matrix()   # walks a white pixel: bottom left of column 0 first
selftest.mic()      # prints peak sample values, they should react to noise
selftest.bands()    # prints the eight band levels, whistle to sweep them
selftest.visualize()# full pipeline for a limited number of frames
```

If `selftest.matrix()` lights the pixels in the wrong order, change
`MATRIX_SERPENTINE` and/or `MATRIX_COLUMN_MAJOR` in `config.py`.

## Modules

| Module | Responsibility |
| --- | --- |
| `config.py` | pins, sample rate, FFT size, smoothing constants, palette |
| `mic.py` | I2S capture, 32 to 16 bit scaling, DC offset removal |
| `spectrum.py` | Hann window, radix-2 FFT, magnitudes, log spaced band grouping |
| `levels.py` | attack/decay envelopes, automatic gain control, peak hold |
| `display.py` | matrix coordinate mapping, brightness, bar rendering |
| `main.py` | wiring it together, plus `bench()` to measure the frame rate |
| `selftest.py` | hardware bring-up helpers |

## Tuning

* `FFT_SIZE` 128 at 16 kHz gives 125 Hz bins and ~8 ms of audio per frame.
  Lower it to 64 for a faster loop, raise it to 256 for finer low end detail.
* `ATTACK` / `DECAY` control how snappy the bars feel.
* `AGC_DECAY` controls how quickly the display re-normalises after a loud
  passage; `AGC_MIN_REFERENCE` sets the noise floor that stays dark.
* `BRIGHTNESS` scales every colour; 64 pixels at full white can draw several
  amps, so keep it modest unless you have the supply for it.

## Performance

`main.bench()` prints the achievable frame rate. The FFT is pure MicroPython
and is the dominant cost. If you need more frames per second:

1. reduce `FFT_SIZE`,
2. use a build with `ulab` and replace `Spectrum.compute` with `ulab.numpy.fft`,
3. or move rendering to the second core with `_thread`.

All buffers are preallocated so the analysis loop does not allocate and cannot
be interrupted by a garbage collection pause.

## Tests

The hardware independent parts (FFT, band mapping, level smoothing, matrix
coordinate mapping) have host tests that run on CPython:

```
python3 -m unittest discover tests
```
