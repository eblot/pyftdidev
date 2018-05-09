#!/usr/bin/env python3

from PIL import Image, ImageDraw, ImageFont
from atexit import register
from collections import deque, namedtuple
from epd2in9 import Epd
from knob import RotaryEncoder
from os import isatty, pipe2, pardir, read, uname, write, O_NONBLOCK
from os.path import dirname, isfile, join as joinpath
from subprocess import check_output, TimeoutExpired
from select import select
from sys import stdin
from termios import (tcgetattr, tcsetattr,
                     ECHO, ICANON, TCSAFLUSH, TCSANOW, VMIN, VTIME)
from time import localtime, strftime, sleep, time as now


class Screen:

    FontDesc = namedtuple('FontDesc', 'point, height')

    def __init__(self):
        self._epd = Epd()
        self._frame = Image.new('1', (self._epd.width, self._epd.height),
                                Epd.WHITE)
        self._font_heights = {}
        self._line_offsets = {}

    def close(self):
        self._epd.fini()

    def initialize(self):
        self._epd.fini()
        self._epd.init(True)
        self.set_titlebar('Internet Radio')

    def set_font(self, fontname):
        self._epd.set_fontpath(fontname)
        self._font_heights['titlebar'] = self._get_font_desc(16)
        self._font_heights['fullscreen'] = self._get_font_desc(72)
        self._font_heights['firstline'] = self._get_font_desc(30)
        self._line_offsets['firstline'] = self._font_heights['titlebar'].height

    def _get_font_desc(self, point):
        return self.FontDesc(point, self._epd.get_font_height(point))

    def test_chrono(self):
        self.test_clock(False)

    def test_wallclock(self):
        self.test_clock(True)

    def test_clock(self, big):
        point = 72 if big else 24
        font_height = self._epd.get_font_height(point)
        yoff = (self._epd.height+font_height//2)//2
        self._epd.clear()
        self._epd.refresh()
        while True:
            ts = now()
            if not big:
                ms = (1000*ts) % 1000
                timestr = '%s.%03d' % (strftime('%H:%M:%S', localtime(ts)), ms)
            else:
                timestr = strftime('%H:%M', localtime(ts))
            print(timestr)
            self._epd.text(timestr, 45, yoff, point)
            self._epd.refresh()
            if big:
                break

    def set_titlebar(self, text, align=''):
        point, height = self._font_heights['titlebar']
        self._epd.rectangle(0, 0, self._epd.width, height)
        xpos = self._get_text_xoffset(text, point, align)
        self._epd.text(text, xpos, height, point)
        self._epd.refresh()

    def set_radio_name(self, text, clear_all=False, align=''):
        point, textheight = self._font_heights['firstline']
        ypos = self._line_offsets['firstline']
        if clear_all:
            self._epd.rectangle(0, ypos,
                                self._epd.width, self._epd.height)
        else:
            self._epd.rectangle(0, ypos, self._epd.width, ypos+textheight)
        xpos = self._get_text_xoffset(text, point, align)
        ypos = ypos + 2*textheight
        print('set_radio_name', text, clear_all, xpos, ypos)
        self._epd.text(text, xpos, ypos, point)
        self._epd.refresh()

    def set_radio_names(self, radios, align=''):
        point, textheight = self._font_heights['firstline']
        ypos = self._line_offsets['firstline']
        self._epd.rectangle(0, ypos,
                            self._epd.width, self._epd.height)
        for rpos, radio in enumerate(radios):
            ypos += textheight
            textwidth = radio and self._epd.get_font_width(point, radio) or 0
            xpos = self._get_text_xoffset(radio, point, align)
            invert = rpos == 1
            if radio:
                if invert:
                    fg = False
                    #self._epd.rectangle(0, ypos,
                    #                    self._epd.width, ypos+textheight,
                    #                    black=True)
                else:
                    fg = True
                print("> %s %dx%d" % (radio, xpos, ypos))
                self._epd.text(radio, xpos, ypos, point, black=fg)
            if rpos == 2:
                break
        self._epd.refresh()

    def _get_text_xoffset(self, text, point, align=''):
        width = self._epd.width
        textwidth = self._epd.get_font_width(point, text)
        if not align:
            align = 'left'
        if align == 'center':
            return max(0, (width - textwidth)//2)
        elif align == 'right':
            return min(width, width - textwidth)
        else:
            return 0


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
        self.execute('mpc load iradio'.split())
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

    def __init__(self, fontname):
        self._screen = Screen()
        self._screen.set_font(fontname)
        self._mpc = Mpc()
        self._term_config = None
        self._knob_pipe = pipe2(O_NONBLOCK)
        self._knob = RotaryEncoder(23, 24, 17, self._knob_event)

    def initialize(self):
        self._mpc.initialize()
        self._screen.initialize()

    def _knob_event(self, event):
        print("KNOB", event)
        if event:
            write(self._knob_pipe[1], bytes([0x40 + event]))
        #['NO_EVENT', 'CLOCKWISE', 'ANTICLOCKWISE', 'BUTTON_DOWN', 'BUTTON UP']

    def _show_radio(self, position, clear=False):
        radio = self._mpc.radios[position]
        self._screen.set_radio_name(radio, clear, align='center')

    def _select_radio(self, rpos):
        radionames = (
            rpos > 1 and self._mpc.radios[rpos - 1] or '',
            self._mpc.radios[rpos],
            rpos < len(self._mpc.radios) and
                        self._mpc.radios[rpos + 1] or '')
        self._screen.set_radio_names(radionames, align='center')

    def run(self):
        #self._screen.test_wallclock()
        #self._screen.test_chrono()
        sinfd = stdin.fileno()
        knobfd = self._knob_pipe[0]
        if isatty(sinfd):
            self._init_term()
        rpos = self._mpc.current
        print("rpos", rpos)
        self._show_radio(rpos, False)
        radios = deque(sorted(self._mpc.radios.keys()))
        edit = False
        clear = False
        last = 0
        infds = [knobfd]
        if isatty(sinfd):
            infds.append(sinfd)
        while True:
            ready = select(list(infds), [], [], 0.25)[0]
            if not ready:
                ts = now()
                if not edit and ((ts-last) > 1.0):
                    tstr = strftime('%X ', localtime(now()))
                    self._screen.set_titlebar(tstr, align='right')
                    last = ts
                continue
            action = ''
            if sinfd in ready:
                print("KEY")
                code = read(sinfd, 1)
                if code == b'q':
                    action = 'S'  # stop
                elif code == b'a':
                    action = 'C'  # cancel
                elif code == b'\n':
                    action = 'E'  # edit on/off
                elif code == b'z':
                    action = 'N'  # next
                elif code == b'x':
                    action = 'P'  # previous
                else:
                    print('?')
                    continue
            elif knobfd in ready:
                print('KNOB')
                code = read(knobfd, 1)
                if code == b'A':
                    print('Next')
                    action = 'N'
                elif code == b'B':
                    print('Prev')
                    action = 'P'
                elif code == b'C':
                    print('Edit')
                    action = 'E'
                else:
                    print('?', code)
                    continue
            if action == 'S':
                self._mpc.stop()
                break
            if action == 'C':
                rpos = self._mpc.current
                continue
            if action == 'E':
                edit = not edit
                if not edit:
                    if rpos != self._mpc.current:
                        self._mpc.select(rpos)
                    #ts = strftime('%X ', localtime(now()))
                    #self._screen.set_titlebar(ts, align='right')
                    self._show_radio(rpos, clear)
                    continue
                # fallback on edit
                clear = True
            if edit:
                if action == 'P':
                    radios.rotate(1)
                elif action == 'N':
                    radios.rotate(-1)
                rpos = radios[0]
                self._select_radio(rpos)

    def _init_term(self):
        """Internal terminal initialization function"""
        fd = stdin.fileno()
        old = tcgetattr(fd)
        self._term_config = (fd, old)
        new = tcgetattr(fd)
        new[3] = new[3] & ~ICANON & ~ECHO
        new[6][VMIN] = 1
        new[6][VTIME] = 0
        tcsetattr(fd, TCSANOW, new)
        # terminal modes have to be restored on exit...
        register(self._cleanup_term)

    def _cleanup_term(self):
        if self._term_config:
            fd, old = self._term_config
            tcsetattr(fd, TCSAFLUSH, old)
            self._term_config = None


if __name__ == '__main__':
    machine = uname().machine
    # quick and unreliable way to detect RPi for now
    if machine.startswith('armv'):
        from RPi import GPIO
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
    fontname = 'DejaVuSansMono.ttf'
    fontpath = joinpath(dirname(__file__), pardir, pardir, fontname)
    engine = Engine(fontpath)
    engine.initialize()
    engine.run()
