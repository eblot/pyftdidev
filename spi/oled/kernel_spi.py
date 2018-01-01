from os import environ
from RPi import GPIO
from spidev import SpiDev
from time import sleep


class Ssd1306KernelPort:
    """
    """

    DC_PIN = 12  # lcd_data6
    RESET_PIN = 13  # lcd_data7

    def __init__(self, debug=False):
        self._debug = debug
        self._spi_port = None

    def open(self):
        """Open an SPI connection to a slave"""
        self._spi_port = SpiDev()
        self._spi_port.open(0, 0)
        self._spi_port.max_speed_hz = 5000
        self._spi_port.mode = 0b00
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.DC_PIN, GPIO.OUT)
        GPIO.setup(self.RESET_PIN, GPIO.OUT)

    def close(self):
        """Close the SPI connection"""
        self._spi_port.close()

    def reset(self):
        GPIO.output(self.RESET_PIN, True)
        sleep(0.001)
        GPIO.output(self.RESET_PIN, False)
        sleep(0.001)
        GPIO.output(self.RESET_PIN, True)
        sleep(0.001)

    def write_command(self, data):
        GPIO.output(self.DC_PIN, False)
        self._spi_port.writebytes(data)

    def write_data(self, data):
        GPIO.output(self.DC_PIN, True)
        self._spi_port.writebytes(data)


def get_port():
    port = Ssd1306KernelPort(False)
    return port
