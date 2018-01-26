#!/usr/bin/env python3

from PIL import Image, ImageDraw, ImageFont
from epd2in9 import Epd
from os.path import isfile
from time import localtime, strftime, time as now


def main(fontname):
    epd = Epd()

    # use full update to ensure proper start up
    epd.init(epd.LUT_FULL_UPDATE)
    image = Image.new('1', (epd.width, epd.height), 0xff)
    epd.clear_frame_memory(0xFF)
    epd.set_frame_memory(image, 0, 0)
    epd.display_frame()
    epd.fini()

    # use partial update to speed up refresh
    epd.init(epd.LUT_PARTIAL_UPDATE)
    epd.set_frame_memory(image, 0, 0)
    epd.display_frame()
    epd.set_frame_memory(image, 0, 0)
    epd.display_frame()

    big = False
    height = big and 72 or 24
    time_image = Image.new('1', (260, height), 0xff)
    draw = ImageDraw.Draw(time_image)
    font = ImageFont.truetype(fontname, height)
    image_width, image_height = time_image.size
    while (True):
        draw.rectangle((0, 0, image_width, image_height), fill=0xff)
        ts = now()
        if not big:
            ms = (1000*ts) % 1000
            timestr = '%s.%03d' % (strftime('%H:%M:%S', localtime(ts)), ms)
        else:
            timestr = strftime('%H:%M', localtime(ts))
        print(timestr)
        draw.text((0, 0), timestr, font=font, fill=0x00)
        epd.set_frame_memory(time_image.rotate(-90, expand=True), 45, 20)
        epd.display_frame()
        epd.wait_until_idle()


if __name__ == '__main__':
    fontname = 'DejaVuSansMono.ttf'
    if not isfile(fontname):
        raise RuntimeError('Missing font file: %s' % fontname)
    main(fontname)
