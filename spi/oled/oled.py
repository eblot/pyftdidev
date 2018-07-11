#!/usr/bin/env python3

from os import environ, uname
from sys import argv, stdout
from time import sleep, time as now


class GfxBuffer:
    """
    """

    def __init__(self, display, width, height):
        self.width = width
        self.height = height
        self._display = display
        self._tl = [0, 0]
        self._br = [self.width-1, self.height-1]
        self._buffer = self.get_empty_buffer()

    def __len__(self):
        return len(self._buffer)

    def get_buffer(self):
        return self._buffer

    def erase(self):
        self._buffer = self.get_empty_buffer()
        self.invalidate()
        self.paint()

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
                self._buffer[xoff + (yoff >> 3)*self.width] |= 1 << (yoff & 7)

    def invalidate(self, tl=None, br=None):
        if not tl:
            self._tl = [0, 0]
        else:
            if tl[0] < self._tl[0]:
                self._tl[0] = tl[0]
            if tl[1] < self._tl[1]:
                self._tl[1] = tl[1]
        if not br:
            self._br = [self.width-1, self.height-1]
        else:
            if br[0] > self._br[0]:
                self._br[0] = br[0]
            if br[1] > self._br[1]:
                self._br[1] = br[1]
        #print('Invalidated area: X:%d..%d Y:%d..%d' %
        #      (self._tl[0], self._br[0], self._tl[1], self._br[1]))

    def paint(self):
        x, y = self._tl[0], self._tl[1] & ~0x7
        last_y = self._br[1] & ~0x7
        width = self._br[0]-self._tl[0]
        count = 0
        # print("Refresh X:%d..%d Y: %d..%d" % (x, x+width, y, last_y))
        while y <= last_y:
            # could optimize this command w/ advancer OLED commands,
            # using a proper stride.
            self._display.set_cursor(x, y)
            start = x + y*self.width//8
            end = start + width + 1
            self._display.write_buffer(self._buffer[start:end])
            count += (end-start)
            y += 8
        self._tl = [self.width, self.height]
        self._br = [0, 0]

    def get_empty_buffer(self, inverted=False):
        if inverted:
            return bytearray([0xFF for _ in range(self.width*self.height//8)])
        else:
            return bytearray(self.width*self.height//8)

    def qrcode(self, msg):
        try:
            from qrcode import QRCode
        except ImportError as ex:
            self.log.critical('PIL and QRCode modules are required')
        qr = QRCode(box_size=2, border=2)
        qr.add_data(msg)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        self.copy_bitmap(img)
        self.paint()

    def text(self, msg, x=0, y=0, **kwargs):
        from bitmapfont import BitmapFont
        font = 'font%dx%d.bin' % (int(argv[1]), int(argv[2]))
        with BitmapFont(self, font) as bf:
            bf.text(msg, x, y, **kwargs)
        self.paint()

    def draw_v_line(self, x, y1, y2, negative=False, paint=False):
        if not 0 <= x < self.width:
            return
        if y1 > y2:
            y1, y2 = y2, y1
        if y1 < 0:
            y1 = 0
        if y1 >= self.height:
            y1 = self.height-1
        if y2 < 0:
            y2 = 0
        if y2 >= self.height:
            y2 = self.height-1
        self.invalidate((x, y1), (x, y2))
        py1 = y1 & 0x7
        if py1:
            offset = x + (y1//8)*self.width
            mask = 0xff & ~((1 << py1) - 1)
            if negative:
                self._buffer[offset] &= ~mask
            else:
                self._buffer[offset] |= mask
            y1 += 8-py1
        py2 = (y2 + 1) & 0x7
        if py2:
            offset = x + (y2//8)*self.width
            mask = (1 << py2) - 1
            if negative:
                self._buffer[offset] &= ~mask
            else:
                self._buffer[offset] |= mask
            y2 -= py2
        offset = x + (y1//8)*self.width
        mask = 0x00 if negative else 0xff
        while y1 <= y2:
            self._buffer[offset] = mask
            offset += self.width
            y1 += 8
        if paint:
            self.paint()

    def draw_h_line(self, x1, x2, y, negative=False, paint=False):
        if not 0 <= y < self.height:
            return
        if x1 > x2:
            x1, x2 = x2, x1
        if x1 < 0:
            x1 = 0
        if x1 >= self.width:
            x1 = self.width-1
        if x2 < 0:
            x2 = 0
        if x2 >= self.width:
            x2 = self.width-1
        mask = 1 << (y & 0x7)
        offset = (y//8)*self.width
        start = offset+x1
        end = offset+x2+1
        if negative:
            mask = ~mask
            while start < end:
                self._buffer[start] &= mask
                start += 1
        else:
            while start < end:
                self._buffer[start] |= mask
                start += 1
        self.invalidate((x1, y), (x2, y))
        if paint:
            self.paint()


class Ssd1306:
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

    # Address mode
    MODE_ADDR_HORIZONTAL = 0
    MODE_ADDR_VERTICAL = 1
    MODE_ADDR_PAGE = 2

    # Physical dimensions
    WIDTH = 128
    HEIGHT = 64

    def __init__(self, interface):
        self._if = interface
        self.gfxbuf = GfxBuffer(self, self.WIDTH, self.HEIGHT)
        self._xoffset = 0

    @property
    def gfx(self):
        return self.gfxbuf

    def initialize(self, xoffset=0):
        self._xoffset = xoffset
        init_sequence = bytes((
            # switch off display
            self.DISPLAY_OFF_CMD,
            # set clock and divider
            self.CLOCK_DISPLAY_CMD, 0x80,
            # set height stride
            self.MULTIPLEX_RATIO_CMD, self.HEIGHT-1,
            # enable charge pump
            self.CHARGE_PUMP_CMD, self.CHARGE_PUMP_ENABLE,
            # precharge period (magical value)
            self.PRECHARGE_PEDIOD_CMD, 0xf1,
            # voltage level (magical value)
            self.VCOMM_DESELECT_LEVEL_CMD, 0x40,
            # no vertical shift
            self.DISPLAY_OFFSET_CMD, 0x00,  # cause issue on small oled?
            # set display start line
            self.START_LINE_BASE_CMD | 0x00,
            # set page address mode addressing
            self.ADDRESS_SET_MODE_CMD, self.MODE_ADDR_PAGE,
            # invert display (for debug)
            self.DISPLAY_REG_CMD,
            # use RAM to populate display content
            self.DISPLAY_RESTORE_CMD,
            # horizontal mirror (LOW to disable)
            self.SEGMENT_REMAP_HIGH_CMD,
            # vertical mirror (NORMAL to disable)
            self.SCAN_DIR_REVERSE_CMD,
            # controller to display matrix config (use default)
            self.COMM_PINS_CFG_CMD, self.COMM_PINS_CFG_DEFAULT,
            # set contrast
            self.DISPLAY_CONTRAST_CMD, 0x70,
            # switch on display
            self.DISPLAY_ON_CMD))
        self._if.reset()
        self._if.write_command(init_sequence)
        sleep(0.1)

    def invert(self, mode=True):
        self._if.write_command(bytes([mode and self.DISPLAY_INV_CMD or
                                      self.DISPLAY_REG_CMD]))

    def set_page_address(self, page):
        if page > (self.HEIGHT//8):
            raise ValueError('Invalid page')
        command = self.ADDRESS_SET_PAGES_CMD + page
        self._if.write_command([command])

    def set_column_address(self, column):
        if column > self.WIDTH:
            raise ValueError('Invalid column')
        column += self._xoffset
        command = [self.ADDRESS_SET_HIGH_COL_CMD | (column >> 4),
                   self.ADDRESS_SET_LOW_COL_CMD | (column & ((1 << 4) - 1))]
        self._if.write_command(bytes(command))

    def set_cursor(self, column, line):
        if line >= self.HEIGHT:
            raise ValueError('Invalid line: %d' % line)
        if column > self.WIDTH:
            raise ValueError('Invalid column: %d' % column)
        page = line // 8
        # print("cursor L:%d C:%d P:%d" % (line, column, page))
        column += self._xoffset
        command = [self.ADDRESS_SET_PAGES_CMD | page,
                   self.ADDRESS_SET_HIGH_COL_CMD | (column >> 4),
                   self.ADDRESS_SET_LOW_COL_CMD | (column & ((1 << 4) - 1))]
        self._if.write_command(bytes(command))

    def write_buffer(self, buf):
        self._if.write_data(buf)


def main():
    machine = uname().machine
    # quick and unreliable way to detect RPi for now
    if machine == 'armv7l':
        from kernel_spi import get_port
    else:
        from ftdi_spi import get_port
    port = get_port()
    port.open()
    disp = Ssd1306(port)
    disp.initialize(2)
    gfx = disp.gfx
    gfx.erase()
    # disp.invert(False)
    # disp.qrcode(argv[3])
    # disp.invert(True)
    for l in range(0, 64):
        gfx.draw_h_line(int(argv[1])+l, int(argv[2])+l, l, paint=True)
        #sleep(0.05)
    for c in range(0, 25):
        line = int(argv[2])
        gfx.draw_v_line(int(argv[1])+c, line+c, line+33+c, paint=True)
        #sleep(0.1)
    for argc in range(3, len(argv)):
        gfx.text(argv[argc], 10, 30+(argc-3)*int(int(argv[2])*1.2), bold=True)
    # prevent SPI glitches for screen that does not support a /CS line
    sleep(0.1)
    port.close()


if __name__ == '__main__':
    # oled.py <width> <height> <text> [text...]
    main()

