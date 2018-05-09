#!/usr/bin/env python3

import sys
sys.path.append('/Users/eblot/Sources/Git/github.com/pyftdi')
from os import pardir
from os.path import dirname, isfile, join as joinpath
from PIL import Image, ImageDraw, ImageFont
from epd2in9 import Epd


def main():
    textheight = 14
    epd = Epd(orientation=90)
    epd.fini()
    partial = True
    epd.init(partial)
    # print("Init as %s" % (full and 'full' or 'partial'))
    epd.clear(True)
    epd.refresh()
    epd.clear(False)
    epd.refresh()
    w = 30
    for wd in (1, ):
        x = 5
        for l in range(10, 20):
            epd.hline(x, l, w, wd)
            x += w
            epd.refresh()
    w = 25
    for wd in (1, 3):
        y = 0
        for x in range(0, 12):
            # print('Line', x, y)
            epd.vline(x, y, 11, wd)
            y+=11
            epd.refresh()
    epd.rectangle(10, 10, 90, 40)
    epd.refresh()
    fontname = 'DejaVuSansMono.ttf'
    fontpath = joinpath(dirname(__file__), pardir, pardir, fontname)
    epd.set_fontpath(fontpath)
    epd.text('Test', 97, 61, 20)
    epd.refresh()
    epd.fini()
    print('Ok')

if __name__ == '__main__':
    main()
