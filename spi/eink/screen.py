#!/usr/bin/env python3

from PIL import Image, ImageDraw, ImageFont
from epd2in9 import Epd
from os.path import isfile
from time import localtime, strftime, time as now


class Screen:

    def __init__(self):
        self._epd = Epd()
        self._frame = Image.new('1', (self._epd.width, self._epd.height),
                                Epd.WHITE)

    def close(self):
        self._epd.fini()

    def initialize(self, full):
        if full == self._epd.is_partial_refresh:
            return
        self._epd.fini()
        self._epd.init(full)
        print("Init as %s" % (full and 'full' or 'partial'))
        self._epd.clear_frame_memory()
        self._epd.display_frame()
        if not full:
            self._epd.clear_frame_memory()
            self._epd.display_frame()

    def test(self, fontname):
        big = False
        height = big and 72 or 24
        time_image = Image.new('1', (260, height), Epd.WHITE)
        draw = ImageDraw.Draw(time_image)
        font = ImageFont.truetype(fontname, height)
        image_width, image_height = time_image.size
        while (True):
            draw.rectangle((0, 0, image_width, image_height), fill=Epd.WHITE)
            ts = now()
            if not big:
                ms = (1000*ts) % 1000
                timestr = '%s.%03d' % (strftime('%H:%M:%S', localtime(ts)), ms)
            else:
                timestr = strftime('%H:%M', localtime(ts))
            print(timestr)
            draw.text((0, 0), timestr, font=font, fill=0x00)
            self._epd.set_frame_memory(time_image.rotate(-90, expand=True), 45, 20)
            self._epd.display_frame()
            self._epd.wait_until_idle()


if __name__ == '__main__':
    fontname = 'DejaVuSansMono.ttf'
    if not isfile(fontname):
        raise RuntimeError('Missing font file: %s' % fontname)
    screen = Screen()
    screen.initialize(True)
    screen.initialize(False)
    screen.test(fontname)
