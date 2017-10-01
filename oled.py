#!/usr/bin/env python3

from os import environ
from pyftdi import FtdiLogger
from pyftdi.spi import SpiController
from sys import stdout
from time import sleep


class Ssd1306Port(object):
    """
    """

    DC_PIN = 1 << 4
    RESET_PIN = 1 << 5
    IO_PINS = DC_PIN | RESET_PIN

    def __init__(self):
        self._spi = SpiController(cs_count=1)
        self._spi_port = None
        self._io_port = None
        self._io = 0

    def open(self):
        """Open an SPI connection to a slave"""
        url = environ.get('FTDI_DEVICE', 'ftdi:///1')
        self._spi.configure(url, debug=True)
        self._spi_port = self._spi.get_port(0, freq=1E6, mode=0)
        self._io_port = self._spi.get_gpio()
        self._io_port.set_direction(self.IO_PINS, self.IO_PINS)

    def close(self):
        """Close the SPI connection"""
        self._spi.terminate()

    def reset(self):
        self._io = self.RESET_PIN
        self._io_port.write(self._io)
        sleep(0.005)
        self._io = 0
        self._io_port.write(self._io)
        sleep(0.005)
        self._io = self.RESET_PIN
        self._io_port.write(self._io)
        sleep(0.005)

    def write_command(self, data):
        self._io &= ~self.DC_PIN
        self._io_port.write(self._io)
        self._spi_port.write(data)

    def write_data(self, data):
        self._io |= self.DC_PIN
        self._io_port.write(self._io)
        self._io.write(data)


class Ssd1306(object):
    """
    """

    # Scrolling
    SCROLL_CFG_H_RIGHT_CMD = 0x26
    SCROLL_CFG_H_LEFT_CMD = 0x27
    SCROLL_CFG_V_RIGHT_CMD = 0x29
    SCROLL_CFG_V_LEFT_CMD = 0x2A
    SCROLL_OFF_CMD = 0x2E
    SCROLL_START_CMD = 0x2F
    SCROLL_CFG_V_AREA_CMD = 0xA3

    # Display
    DISPLAY_CONTRAST_CMD = 0x81
    DISPLAY_RESTORE_CMD = 0xA4
    DISPLAY_IGNORE_CMD = 0xA5
    DISPLAY_REG_CMD = 0xA6
    DISPLAY_INV_CMD = 0xA7
    DISPLAY_OFF_CMD = 0xAE
    DISPLAY_ON_CMD = 0xAF

    # Addressing
    ADDRESS_SET_HIGH_COL_CMD = 0x10
    ADDRESS_SET_MODE_CMD = 0x20
    ADDRESS_SET_COL_CMD = 0x21
    ADDRESS_SET_PAGE_CMD = 0x22
    ADDRESS_SET_PAGES_CMD = 0XB0

    # Hardware configuration
    START_LINE_BASE_CMD = 0x40
    SEGMENT_REMAP_LOW_CMD = 0XA0
    SEGMENT_REMAP_HIGH_CMD = 0XA1
    MULTIPLEX_RATIO_CMD = 0xA8
    SCAN_DIR_NORMAL_CMD = 0xC0
    SCAN_DIR_REVERSE_CMD = 0xC8
    DISPLAY_OFFSET_CMD = 0xD3
    COMM_PINS_CFG_CMD = 0xDA
    COMM_PINS_CFG_DEFAULT = 0x12

    # Timing
    CLOCK_DISPLAY_CMD = 0xD5
    PRECHARGE_PEDIOD_CMD = 0xD9
    VCOMM_DESELECT_LEVEL_CMD = 0xDB
    NO_OP_CMD = 0XE3
    CHARGE_PUMP_CMD = 0x8D
    CHARGE_PUMP_ENABLE = 0x14
    CHARGE_PUMP_DISABLE = 0x10

    # Advanced graphics
    FADE_OUT_BLINK_CMD = 0X23
    ZOOM_IN_CMD = 0xD6

    def __init__(self, interface):
        self._if = interface

    def initialize(self):
        init_sequence = bytes((
            self.DISPLAY_OFF_CMD,
            self.CLOCK_DISPLAY_CMD, 0x80,
            self.MULTIPLEX_RATIO_CMD, 0x3f,
            self.DISPLAY_OFFSET_CMD, 0x00,
            self.CHARGE_PUMP_CMD, self.CHARGE_PUMP_ENABLE,
            self.START_LINE_BASE_CMD,
            self.DISPLAY_INV_CMD,  # self.DISPLAY_REG_CMD,
            self.DISPLAY_RESTORE_CMD,
            self.SEGMENT_REMAP_HIGH_CMD,
            self.SCAN_DIR_REVERSE_CMD,
            self.COMM_PINS_CFG_CMD, self.COMM_PINS_CFG_DEFAULT,
            self.DISPLAY_CONTRAST_CMD, 0xf0,
            self.PRECHARGE_PEDIOD_CMD, 0xf1,
            self.VCOMM_DESELECT_LEVEL_CMD, 0x40,
            self.DISPLAY_ON_CMD))
        self._if.reset()
        self._if.write_command(init_sequence)


def main():
    port = Ssd1306Port()
    port.open()
    disp = Ssd1306(port)
    disp.initialize()
    port.close()


if __name__ == '__main__':
    import logging
    level = environ.get('FTDI_LOGLEVEL', 'info').upper()
    try:
        loglevel = getattr(logging, level)
    except AttributeError:
        raise ValueError('Invalid log level: %s', level)
    FtdiLogger.log.addHandler(logging.StreamHandler(stdout))
    FtdiLogger.set_level(loglevel)
    main()
