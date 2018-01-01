from os import environ
from pyftdi import FtdiLogger
from pyftdi.spi import SpiController
from sys import stdout
from time import sleep


class Ssd1306FtdiPort:
    """
    """

    DC_PIN = 1 << 4
    RESET_PIN = 1 << 5
    IO_PINS = DC_PIN | RESET_PIN

    def __init__(self, debug=False):
        self._debug = debug
        self._spi = SpiController(cs_count=1)
        self._spi_port = None
        self._io_port = None
        self._io = 0

    def open(self):
        """Open an SPI connection to a slave"""
        url = environ.get('FTDI_DEVICE', 'ftdi:///1')
        self._spi.configure(url, debug=self._debug)
        self._spi_port = self._spi.get_port(0, freq=3E6, mode=0)
        self._io_port = self._spi.get_gpio()
        self._io_port.set_direction(self.IO_PINS, self.IO_PINS)

    def close(self):
        """Close the SPI connection"""
        self._spi.terminate()

    def reset(self):
        self._io = self.RESET_PIN
        self._io_port.write(self._io)
        sleep(0.001)
        self._io = 0
        self._io_port.write(self._io)
        sleep(0.001)
        self._io = self.RESET_PIN
        self._io_port.write(self._io)
        sleep(0.001)

    def write_command(self, data):
        self._io &= ~self.DC_PIN
        self._io_port.write(self._io)
        self._spi_port.write(data)

    def write_data(self, data):
        self._io |= self.DC_PIN
        self._io_port.write(self._io)
        self._spi_port.write(data)


def get_port():
    import logging
    level = environ.get('FTDI_LOGLEVEL', 'info').upper()
    try:
        loglevel = getattr(logging, level)
    except AttributeError:
        raise ValueError('Invalid log level: %s', level)
    FtdiLogger.log.addHandler(logging.StreamHandler(stdout))
    FtdiLogger.set_level(loglevel)
    port = Ssd1306FtdiPort(False)
    return port
