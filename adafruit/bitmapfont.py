# MicroPython basic bitmap font renderer.
# Author: Tony DiCola
# License: MIT License (https://opensource.org/licenses/MIT)
# Modified for regular PY3

from struct import unpack as sunpack
from os.path import dirname, join as joinpath


class BitmapFont(object):

    def __init__(self, buf, width, height, font_name='font5x8.bin'):
        # Specify the drawing area width and height, and the pixel function to
        # call when drawing pixels (should take an x and y param at least).
        # Optionally specify font_name to override the font file to use
        # (default is font5x8.bin).  The font format is a binary file with the
        # following format:
        # - 1 unsigned byte: font character width in pixels
        # - 1 unsigned byte: font character height in pixels
        # - x bytes: font data, in ASCII order covering all 255 characters.
        #            Each character should have a byte for each pixel column of
        #            data (i.e. a 5x8 font has 5 bytes per character).
        self._font_width = 0
        self._font_height = 0
        self._font_name = font_name
        self._font = None
        self._buffer = buf
        self._width = width
        self._height = height

    def init(self):
        # Open the font file and grab the character width and height values.
        # Note that only fonts up to 8 pixels tall are currently supported.
        font_file = joinpath(dirname(__file__), self._font_name)
        self._font = open(font_file, 'rb')
        self._font_width, self._font_height = sunpack('BB', self._font.read(2))

    def deinit(self):
        # Close the font file as cleanup.
        self._font.close()

    def __enter__(self):
        self.init()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.deinit()

    @classmethod
    def byte_count_for_height(cls, font_height):
        return (font_height+7)//8

    def _draw_char(self, ch, x, y):
        # print("char @ %dx%d" % (x, y))
        # Don't draw the character if it will be clipped off the visible area.
        if x < -self._font_width or x >= self._width or \
           y < -self._font_height or y >= self._height:
            return
        # Go through each column of the character.
        bpc = self.byte_count_for_height(self._font_height)
        sbpc, fmt = {1: (1, 'B'),
                     2: (2, '<H'),
                     3: (4, '<I'),
                     4: (4, '<I')}[bpc]
        first_pos = 0
        last_pos = 0
        for char_x in range(self._font_width):
            # Grab the byte for the current column of font data.
            self._font.seek(2 + (ord(ch) * self._font_width) + char_x)
            bytes_ = self._font.read(bpc)
            if len(bytes_) < sbpc:
                bytes_ = b''.join(bytes_, b'\x00'*(sbpc-bpc))
            bits, = sunpack(fmt, bytes_)
            pos = self._width * (y >> 3)
            yoff = y & 7
            pos += x + char_x
            if not first_pos:
                first_pos = pos
            last_pos = len(self._buffer)
            if yoff == 0:
                for col in range(bpc):
                    self._buffer[pos] = bits & 0xff
                    bits >>= 8
                    pos += self._width
            else:
                bits <<= yoff
                mask = ((1 << self._font_height)-1) << yoff
                for col in range(bpc+1):
                    self._buffer[pos] &= ~(mask & 0xff)
                    self._buffer[pos] |= bits & 0xff
                    bits >>= 8
                    mask >>= 8
                    pos += self._width
                    if pos >= last_pos:
                        break
        return first_pos, pos

    def text(self, text, x, y):
        # Draw the specified text at the specified location.
        fpos = len(self._buffer)
        lpos = 0
        for i in range(len(text)):
            first, last = self._draw_char(text[i],
                                          x + (i * (self._font_width + 1)), y)
            if fpos > first:
                fpos = first
            if lpos < last:
                lpos = last
        # print("fpos %d %d, lpos %d %d" % (fpos, fpos%128, lpos, lpos%128))
        tl = (fpos % self._width, 8*(fpos // self._width))
        br = (lpos % self._width, 8*(lpos // self._width))
        # print("rect %d,%d" % tl,  "x %d,%d" % br)
        return tl, br

    def text_width(self, text):
        # Return the pixel width of the specified text message.
        return len(text) * (self._font_width + 1)

    def height(self):
        if not self._font_height:
            raise ValueError('Not initialized')
        return self._font_height
