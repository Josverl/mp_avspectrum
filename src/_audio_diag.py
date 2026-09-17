import gc
import selftest

microphone = selftest._microphone()
minimum = 1 << 30
maximum = 0
total = 0
frames = 500

try:
    for _ in range(frames):
        count = microphone.read()
        peak = 0
        for index in range(count):
            value = microphone.samples[index]
            if value < 0:
                value = -value
            if value > peak:
                peak = value
        if peak < minimum:
            minimum = peak
        if peak > maximum:
            maximum = peak
        total += peak
finally:
    microphone.deinit()

print("PEAK min={} avg={} max={} free={}".format(
    minimum, total // frames, maximum, gc.mem_free()
))
