#!/usr/bin/env python3

from PIL import Image, ImageDraw, ImageFont
from collections import deque, namedtuple
from epd2in9 import Epd
from os.path import isfile
from subprocess import check_output, TimeoutExpired
from time import localtime, strftime, sleep, time as now
from tools import getkey, is_term


class Screen:

    FontDesc = namedtuple('FontDesc', 'font, height')

    def __init__(self):
        self._epd = Epd()
        self._frame = Image.new('1', (self._epd.width, self._epd.height),
                                Epd.WHITE)
        self._fonts = {}
        self._line_offsets = {}

    def close(self):
        self._epd.fini()

    def initialize(self, full):
        if full == self._epd.is_partial_refresh:
            return
        self._epd.fini()
        self._epd.init(full)
        # print("Init as %s" % (full and 'full' or 'partial'))
        self._epd.clear_frame_memory()
        self._epd.display_frame()
        if not full:
            self._epd.clear_frame_memory()
            self._epd.display_frame()

    def set_font(self, fontname):
        if not isfile(fontname):
            raise RuntimeError('Missing font file: %s' % fontname)
        font = ImageFont.truetype(fontname, 16)
        self._fonts['titlebar'] = Screen.FontDesc(font, font.getsize('Ij')[1])
        font = ImageFont.truetype(fontname, 72)
        self._fonts['fullscreen'] = Screen.FontDesc(font, font.getsize('Ij')[1])
        font = ImageFont.truetype(fontname, 30)
        self._fonts['firstline'] = Screen.FontDesc(font, font.getsize('Ij')[1])
        self._line_offsets['firstline'] = self._fonts['titlebar'].height

    def test_chrono(self):
        self.test_clock(False)

    def test_wallclock(self):
        self.test_clock(True)

    def test_clock(self, big):
        height = big and 72 or 24
        time_image = Image.new('1', (260, height), Epd.WHITE)
        draw = ImageDraw.Draw(time_image)
        font = big and self._fonts['fullscreen'].font or \
                    self._fonts['firstline'].font
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
            draw.text((0, 0), timestr, font=font, fill=Epd.BLACK)
            self._epd.set_frame_memory(time_image.rotate(-90, expand=True),
                                       45, 20)
            self._epd.display_frame()
            if big:
                break

    def set_titlebar(self, text, align=''):
        font, textheight = self._fonts['titlebar']
        image = Image.new('1', (Epd.HEIGHT, textheight), Epd.WHITE)
        width, height = image.size
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, width, height), fill=Epd.WHITE)
        draw.line((0, height-2, width, height-2), fill = 0)
        textsize = font.getsize(text)
        if not align:
            align = 'left'
        if align == 'center':
            xpos = max(0, (width - textsize[0])//2)
        elif align == 'right':
            xpos = min(Epd.HEIGHT, Epd.HEIGHT-textsize[0])
        else:
            xpos = 0
        draw.text((xpos, 0), text, font=font, fill=Epd.BLACK)
        image = image.rotate(-90, expand=True)
        self._epd.set_frame_memory(image, Epd.WIDTH-height, 0)
        self._epd.display_frame()
        self._epd.set_frame_memory(image, Epd.WIDTH-height, 0)

    def set_radio_name(self, text, clear_all=False, align=''):
        font, textheight = self._fonts['firstline']
        ypos = self._line_offsets['firstline']
        height = clear_all and (Epd.WIDTH - ypos) or textheight
        image = Image.new('1', (Epd.HEIGHT, height), Epd.WHITE)
        width, height = image.size
        draw = ImageDraw.Draw(image)
        textsize = font.getsize(text)
        if not align:
            align = 'center'
        if align == 'center':
            xpos = max(0, (width - textsize[0])//2)
        elif align == 'right':
            xoff = min(Epd.HEIGHT, Epd.HEIGHT-textsize[0])
        else:
            xpos = 0
        yoff = clear_all and 10 or 0
        draw.rectangle((0, 0, width, height), fill=Epd.WHITE)
        draw.text((xpos, yoff), text, font=font, fill=Epd.BLACK)
        image = image.rotate(-90, expand=True)
        if not clear_all:
            ypos += 10
        self._epd.set_frame_memory(image, Epd.WIDTH-height-ypos, 0)
        self._epd.display_frame()
        self._epd.set_frame_memory(image, Epd.WIDTH-height-ypos, 0)

    def set_radio_names(self, radios, align=''):
        print('---')
        font, textheight = self._fonts['firstline']
        image = Image.new('1', (Epd.HEIGHT, 3*textheight), Epd.WHITE)
        width, height = image.size
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, width, height), fill=Epd.WHITE)
        ypos = 0
        for rpos, radio in enumerate(radios):
            textwidth = radio and font.getsize(radio)[0] or 0
            if not align:
                align = 'center'
            if align == 'center':
                xpos = max(0, (width - textwidth)//2)
            elif align == 'right':
                xoff = min(Epd.HEIGHT, Epd.HEIGHT-textwidth)
            else:
                xpos = 0
            invert = rpos == 1
            if radio:
                if invert:
                    fg = Epd.WHITE
                    draw.rectangle((0, ypos, width, ypos+textheight),
                                   fill=Epd.BLACK)
                else:
                    fg = Epd.BLACK
                print("> %s %dx%d" % (radio, xpos, ypos))
                draw.text((xpos, ypos), radio, font=font, fill=fg)
            ypos += textheight
            if rpos == 2:
                break
        image = image.rotate(-90, expand=True)
        print("Image %dx%d" % image.size, "@ %d" % (Epd.WIDTH-height))
        ypos = self._line_offsets['firstline']
        self._epd.set_frame_memory(image, Epd.WIDTH-height-ypos, 0)
        self._epd.display_frame()
        self._epd.set_frame_memory(image, Epd.WIDTH-height-ypos, 0)


class Mpc:

    def __init__(self):
        self._radios = {}
        self._current = 0

    def execute(self, args):
        while True:
            try:
                return check_output(args,
                                    timeout=2.0, universal_newlines=True)
            except TimeoutExpired:
                print("Time out, retrying: %s" % ' '.join(args))
                continue

    def initialize(self):
        self.execute('mpc stop'.split())
        self.execute('mpc clear'.split())
        self.execute('mpc load playlist'.split())
        playlist = self.execute(('mpc', 'playlist',
                                 '-f', r'%position%: %name%'))
        for radio in playlist.split('\n'):
            if not radio:
                break
            spos, name = radio.split(':', 1)
            pos = int(spos)
            sname = name.split('-', 1)[0].strip()
            print("%2d: '%s'" % (pos, sname))
            self._radios[pos] = sname
        self.execute('mpc play'.split())
        self._load_current()

    def select(self, position):
        self.execute(('mpc', 'play', '%d' % position))
        self._load_current()

    def stop(self):
        self.execute('mpc stop'.split())

    def _load_current(self):
        current = self.execute(('mpc', '-f', r'%position%: %title%'))
        spos, title = current.split(':', 1)
        pos = int(spos)
        self._current = pos
        print("Current %s %s %s" % (pos, self._radios[pos], title))

    @property
    def current(self):
        return self._current

    @property
    def radios(self):
        return self._radios


class Engine:

    def __init__(self):
        fontname = 'DejaVuSansMono.ttf'
        self._screen = Screen()
        self._screen.set_font(fontname)
        self._mpc = Mpc()

    def initialize(self):
        self._mpc.initialize()
        self._screen.initialize(True)
        self._screen.initialize(False)
        self._screen.set_titlebar('Internet Radio')

    def _show_radio(self, position, clear=False):
        radio = self._mpc.radios[position]
        self._screen.set_radio_name(radio, clear)

    def _select_radio(self, rpos):
        radionames = (
            rpos > 1 and self._mpc.radios[rpos - 1] or '',
            self._mpc.radios[rpos],
            rpos < len(self._mpc.radios) and
                        self._mpc.radios[rpos + 1] or '')
        self._screen.set_radio_names(radionames)

    def run(self):
        rpos = self._mpc.current
        print("rpos", rpos)
        self._show_radio(rpos, False)
        radios = deque(sorted(self._mpc.radios.keys()))
        edit = False
        clear = False
        while True:
            code = getkey()
            if code == b'q':
                self._mpc.stop()
                break
            if code == b'a':
                rpos = self._mpc.current
                continue
            if code == b'\n':
                edit = not edit
                if not edit:
                    if rpos != self._mpc.current:
                        self._mpc.select(rpos)
                    ts = strftime('%X ', localtime(now()))
                    self._screen.set_titlebar(ts, align='right')
                    self._show_radio(rpos, clear)
                    continue
                # fallback on edit
                clear = True
            if edit:
                if code == b'z':
                    radios.rotate(1)
                elif code == b'x':
                    radios.rotate(-1)
                rpos = radios[0]
                self._select_radio(rpos)


if __name__ == '__main__':
    engine = Engine()
    engine.initialize()
    engine.run()

    #screen.test_wallclock()
    #screen.test_chrono()

