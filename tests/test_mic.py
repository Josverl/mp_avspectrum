import importlib.util
import os
import sys
import types
import unittest
from unittest.mock import patch


BLOCK_SIZE = 128


class FakeI2S:
    RX = 0
    MONO = 0
    blocks = []
    instance = None

    def __init__(self, *args, **kwargs):
        self.blocks = [list(block) for block in type(self).blocks]
        self.deinitialized = False
        type(self).instance = self

    def readinto(self, target):
        block = self.blocks.pop(0)
        for index, value in enumerate(block):
            target[index] = value
        return len(block) * target.itemsize

    def deinit(self):
        self.deinitialized = True


class FakePoll:
    def register(self, stream, event):
        self.stream = stream

    def poll(self, timeout):
        return [(self.stream, 1)] if self.stream.blocks else []


def load_microphone():
    machine = types.SimpleNamespace(I2S=FakeI2S, Pin=lambda pin: pin)
    select = types.SimpleNamespace(POLLIN=1, poll=FakePoll)
    path = os.path.join(os.path.dirname(__file__), "..", "src", "mic.py")
    spec = importlib.util.spec_from_file_location("mic", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"machine": machine, "select": select}):
        spec.loader.exec_module(module)
    return module.Microphone


class TestMicrophone(unittest.TestCase):
    def make(self, blocks, capture_blocks=4):
        FakeI2S.blocks = [[0] * BLOCK_SIZE for _ in range(64)] + blocks
        microphone = load_microphone()
        return microphone(0, 1, 2, 3, 16000, BLOCK_SIZE, bits=16,
                          ibuf=8192, capture_blocks=capture_blocks)

    def test_rejects_invalid_capture_window(self):
        with self.assertRaises(ValueError):
            self.make([], capture_blocks=0)

    def test_selects_strongest_low_frequency_block(self):
        high_frequency = [1000 if index % 2 else -1000 for index in range(BLOCK_SIZE)]
        bass_transient = [500] * 64 + [-500] * 64
        microphone = self.make([high_frequency, bass_transient])

        count = microphone.read()

        self.assertEqual(count, BLOCK_SIZE)
        self.assertAlmostEqual(microphone.samples[0], 500.0)
        self.assertAlmostEqual(microphone.samples[-1], -500.0)
        self.assertEqual(FakeI2S.instance.blocks, [])

    def test_stops_at_capture_block_limit(self):
        blocks = [[value] * BLOCK_SIZE for value in (1, 2, 3)]
        microphone = self.make(blocks, capture_blocks=2)

        microphone.read()

        self.assertEqual(len(FakeI2S.instance.blocks), 1)


if __name__ == "__main__":
    unittest.main()