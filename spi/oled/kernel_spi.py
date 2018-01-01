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
        self._spi = SpiDev()
        self._spi_port = None
        self._io_dc_port = None
        self._io_reset_port = None

    def open(self):
        """Open an SPI connection to a slave"""
        self._spi_port = self._spi.open(0, 0)
        self._spi_port.max_speed_hz = int(3E6)
        self._spi_port.mode = 0b00
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.DC_PIN, GPIO.OUT)
        GPIO.setup(self.RESET_PIN, GPIO.OUT)

    def close(self):
        """Close the SPI connection"""
        self._spi_port.close()

    def reset(self):
        self._io = self.RESET_PIN
        GPIO.output(self._io_reset_port, True)
        sleep(0.001)
        GPIO.output(self._io_reset_port, False)
        sleep(0.001)
        GPIO.output(self._io_reset_port, True)
        sleep(0.001)

    def write_command(self, data):
        GPIO.output(self._io_dc_port, False)
        self._spi_port.writebytes(data)

    def write_data(self, data):
        GPIO.output(self._io_dc_port, True)
        self._spi_port.writebytes(data)


def get_port():
    port = Ssd1306KernelPort(False)
    return port
