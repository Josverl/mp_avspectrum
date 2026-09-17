import config
from neopixel import NeoPixel
from machine import Pin 

# Clear the matrix
np = NeoPixel( Pin(config.PIN_NEOPIXEL, Pin.OUT), config.MATRIX_HEIGHT * (config.MATRIX_WIDTH+1))
np.fill((0,0,0))
np.write()

