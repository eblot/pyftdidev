#!/usr/bin/env python3

from os import environ
from pyftdi import FtdiLogger
from pyftdi.spi import SpiController
from sys import argv, stdout
from time import sleep, time as now


class Ssd1306Port(object):
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


class GfxBuffer(object):
    """
    """

    def __init__(self, display, width, height):
        self.display = display
        self.width = width
        self.height = height
        self.buffer = bytearray(width*height//8)
        self._tl = [0, 0]
        self._br = [self.width, self.height]

    def __len__(self):
        return len(self.buffer)

    def copy_bitmap(self, img, x=0, y=0):
        width, height = img.size
        buf = img.getdata(0)
        for pos, pixel in enumerate(buf):
            row = pos % width
            col = pos // width
            xoff = row + x
            if xoff >= self.width:
                continue
            yoff = col + y
            if yoff >= self.height:
                break
            if pixel:
                self.buffer[xoff + (yoff >> 3)*self.width] |= 1 << (yoff & 7)

    def invalidate(self, tl=None, br=None):
        if not tl:
            self._tl = [0, 0]
        else:
            if tl[0] < self._tl[0]:
                self._tl[0] = tl[0]
            if tl[1] < self._tl[1]:
                self._tl[1] = tl[1]
        if not br:
            self._br = [self.width, self.height]
        else:
            if br[0] > self._br[0]:
                self._br[0] = br[0]
            if br[1] > self._br[1]:
                self._br[1] = br[1]

    def paint(self):
        x, y = self._tl[0], self._tl[1] & ~0x7
        last_y = (self._br[1]+7) & ~0x7
        width = self._br[0]-self._tl[0] + 1
        count = 0
        while y < last_y:
            self.display.set_cursor(y//8, x)
            start = x + y*self.width//8
            end = start + width
            self.display.write_buffer(self.buffer[start:end])
            count += (end-start)
            y += 8
        self._tl = [self.width, self.height]
        self._br = [0, 0]


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
    ADDRESS_SET_LOW_COL_CMD = 0x00
    ADDRESS_SET_HIGH_COL_CMD = 0x10
    ADDRESS_SET_MODE_CMD = 0x20
    ADDRESS_SET_COL_CMD = 0x21
    ADDRESS_SET_PAGE_CMD = 0x22
    ADDRESS_SET_PAGES_CMD = 0xB0

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

    WIDTH = 128
    HEIGHT = 64

    def __init__(self, interface):
        self._if = interface
        # self._gddram = bytearray(self.WIDTH*self.HEIGHT//8)
        self.gfxbuf = GfxBuffer(self, self.WIDTH, self.HEIGHT)

    def initialize(self):
        init_sequence = bytes((
            self.DISPLAY_OFF_CMD,
            self.CLOCK_DISPLAY_CMD, 0x80,
            self.MULTIPLEX_RATIO_CMD, 0x3f,
            self.DISPLAY_OFFSET_CMD, 0x00,
            self.CHARGE_PUMP_CMD, self.CHARGE_PUMP_ENABLE,
            self.START_LINE_BASE_CMD,
            self.DISPLAY_REG_CMD,
            self.DISPLAY_RESTORE_CMD,
            self.SEGMENT_REMAP_HIGH_CMD,
            self.SCAN_DIR_REVERSE_CMD,
            self.COMM_PINS_CFG_CMD, self.COMM_PINS_CFG_DEFAULT,
            self.DISPLAY_CONTRAST_CMD, 0x70,
            self.PRECHARGE_PEDIOD_CMD, 0xf1,
            self.VCOMM_DESELECT_LEVEL_CMD, 0x40,
            self.DISPLAY_ON_CMD))
        self._if.reset()
        self._if.write_command(init_sequence)

    def invert(self, mode=True):
        self._if.write_command(bytes([mode and self.DISPLAY_INV_CMD or
                                      self.DISPLAY_REG_CMD]))

    def set_page_address(self, address):
        command = self.ADDRESS_SET_PAGES_CMD + address
        self._if.write_command([command])

    def set_column_address(self, address):
        command = [self.ADDRESS_SET_HIGH_COL_CMD | (address >> 4),
                   self.ADDRESS_SET_LOW_COL_CMD | (address & ((1 << 4) - 1))]
        self._if.write_command(bytes(command))

    def set_cursor(self, line, column):
        # print("cursor L:%d C:%d" % (line, column))
        command = [self.ADDRESS_SET_PAGES_CMD | line,
                   self.ADDRESS_SET_HIGH_COL_CMD | (column >> 4),
                   self.ADDRESS_SET_LOW_COL_CMD | (column & ((1 << 4) - 1))]
        self._if.write_command(bytes(command))

    def write_buffer(self, buf):
        self._if.write_data(buf)

    def qrcode(self, msg):
        try:
            from qrcode import QRCode
        except ImportError as ex:
            self.log.critical('PIL and QRCode modules are required')
        qr = QRCode(box_size=2, border=2)
        qr.add_data(msg)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        self.gfxbuf.copy_bitmap(img)
        self.gfxbuf.paint()

    def text(self, msg, x=0, y=0, **kwargs):
        from adafruit.bitmapfont import BitmapFont
        font = 'font%dx%d.bin' % (int(argv[1]), int(argv[2]))
        with BitmapFont(self.gfxbuf, font) as bf:
            bf.text(msg, x, y, **kwargs)
        self.gfxbuf.paint()


def main():
    port = Ssd1306Port(False)
    port.open()
    disp = Ssd1306(port)
    disp.initialize()
    disp.invert(True)
    if len(argv) > 1:
        disp.qrcode(argv[1])
    disp.invert(True)
    disp.text("ABCD", 20, 27, bold=True)
    # disp.text("next", 5, 21)
    # prevent SPI glitches as screen does not support a /CS line
    sleep(0.1)
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