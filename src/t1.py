
import gc
import time

import config
from display import BarsRenderer, Matrix
from levels import Levels
from mic import Microphone
from spectrum import Spectrum

from start import build

microphone, spectrum, levels, renderer = build()
# Collect once up front; the loop itself does not allocate.
gc.collect()



# Test matrix 
