# RP2040: repeated NeoPixel writes stop while I2S RX is active

## Summary

On an RP2040 running MicroPython 1.29.0, repeated writes through the built-in
`neopixel.NeoPixel` API stop updating a WS2812 matrix after the first frame when
an I2S RX peripheral is active. The same NeoPixel animation works when I2S is
not initialized.

A WS2812 driver using a dedicated `rp2.StateMachine` on PIO1 state machine 4
continues to update correctly while the same I2S input is active. This suggests
a resource or state interaction between RP2 I2S and the transport used by
`machine.bitstream`/`neopixel`, but the owning component has not yet been
confirmed.

## Environment

- Board: Pimoroni Pico LiPo 16MB with RP2040
- Firmware: MicroPython `v1.29.0`, built 2026-08-24
- Build: `PIMORONI_PICOLIPO-FLASH_16M`
- Host: Windows, device on USB serial `COM62`
- Microphone: INMP441, I2S RX mono, 32 bits, 16 kHz
- I2S pins: SCK GP6, WS GP7, SD GP5
- WS2812 data pin: GP1
- WS2812 count: 64

Firmware identification:

```text
(sysname='rp2', nodename='rp2', release='1.29.0',
 version='v1.29.0 on 2026-08-24 (GNU 16.1.0 MinSizeRel)',
 machine='Pimoroni Pico LiPo 16MB with RP2040')
```

## Minimal reproduction

```python
import time
from array import array
from machine import I2S, Pin
from neopixel import NeoPixel

audio = I2S(
    0,
    sck=Pin(6),
    ws=Pin(7),
    sd=Pin(5),
    mode=I2S.RX,
    bits=32,
    format=I2S.MONO,
    rate=16000,
    ibuf=20000,
)
samples = array("i", bytes(4 * 128))
pixels = NeoPixel(Pin(1, Pin.OUT), 64)

try:
    for column in range(8):
        audio.readinto(samples)
        pixels.fill((0, 0, 0))
        for row in range(8):
            index = column * 8 + (7 - row if column & 1 else row)
            pixels[index] = (40, 40, 40)
        pixels.write()
        time.sleep(1)
finally:
    audio.deinit()
```

## Actual behavior

Only the first column is displayed. Subsequent columns do not appear and the
script does not complete normally. When invoked through `mpremote exec`, the
host can later report a serial failure such as:

```text
serial.serialutil.SerialException: ClearCommError failed
(PermissionError(13, 'The device does not recognize the command.', None, 22))
```

The serial exception appears secondary to the device-side stall and is included
only as an additional observation.

## Expected behavior

All eight columns should be displayed in sequence and the script should print or
return normally after the final frame.

## Control experiments

1. Running the same moving-column animation without creating the I2S object
   updates all eight columns and completes normally.
2. Reading I2S without writing NeoPixels completes normally.
3. Replacing `NeoPixel.write()` with a standard WS2812 PIO program running on
   `rp2.StateMachine(4, ...)` updates all eight columns while I2S remains active.
4. The full audio visualizer computes changing FFT and normalized band values
   when rendering is disabled, but displays only its first rendered frame when
   the built-in NeoPixel transport is used.

## Workaround

Drive the WS2812 matrix with a persistent state machine explicitly allocated on
PIO1, for example state machine 4, rather than the built-in NeoPixel transport.
This workaround was validated with I2S RX active and reading on every frame.

## Additional investigation

- Reproduce with the official generic RP2040 firmware to separate an upstream
  MicroPython issue from the Pimoroni build.
- Determine which PIO block/state machine and DMA resources RP2 I2S and
  `machine.bitstream` claim in this firmware.
- Check whether the issue depends on I2S direction, DMA channel allocation,
  NeoPixel pin, or initialization order.
- Capture a device-side stack or state-machine/DMA status if an instrumented
  firmware build is available.