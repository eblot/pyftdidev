from os import environ
from RPi import GPIO
from spidev import SpiDev
from time import sleep, time as now


class EpdKernelPort:
    """
    """

    DC_PIN = 5  # Pin 29
    RESET_PIN = 6  # Pin 31
    BUSY_PIN = 12  # Pin 32

    def __init__(self, debug=False):
        self._debug = debug
        self._spi_port = None

    def open(self):
        """Open an SPI connection to a slave"""
        self._spi_port = SpiDev()
        self._spi_port.open(0, 0)
        self._spi_port.max_speed_hz = int(3E6)
        self._spi_port.mode = 0b00
        GPIO.setup(self.DC_PIN, GPIO.OUT)
        GPIO.setup(self.RESET_PIN, GPIO.OUT)
        GPIO.setup(self.BUSY_PIN, GPIO.IN)

    def close(self):
        """Close the SPI connection"""
        if self._spi_port:
            self._spi_port.close()

    def reset(self):
        GPIO.output(self.RESET_PIN, True)
        sleep(0.02)
        GPIO.output(self.RESET_PIN, False)
        sleep(0.02)
        GPIO.output(self.RESET_PIN, True)
        sleep(0.02)

    def write_command(self, data):
        GPIO.output(self.DC_PIN, False)
        if isinstance(data, int):
            data = bytes([data])
        from binascii import hexlify
        self._spi_port.writebytes(data)

    def write_data(self, data):
        GPIO.output(self.DC_PIN, True)
        if isinstance(data, int):
            data = bytes([data])
        while data:
            buf, data = data[:4096], data[4096:]
            self._spi_port.writebytes(buf)

    def wait_ready(self):
        start = now()
        while GPIO.input(self.BUSY_PIN):
            sleep(0.05)
        return now()-start

def get_port():
    port = EpdKernelPort(False)
    return port
