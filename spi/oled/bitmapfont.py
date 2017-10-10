# Based on MicroPython basic bitmap font renderer.
# Original author: Tony DiCola
# License: MIT License (https://opensource.org/licenses/MIT)

from os.path import dirname, join as joinpath


class BitmapFont(object):

    def __init__(self, gfxbuf, font_name='font5x8.bin'):
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
        self._gfxbuf = gfxbuf

    def init(self):
        # Open the font file and grab the character width and height values.
        # Note that only fonts up to 8 pixels tall are currently supported.
        font_file = joinpath(dirname(__file__), 'fonts', self._font_name)
        print(font_file)
        self._font = open(font_file, 'rb')
        self._font_width, self._font_height = self._font.read(2)
        print('Font W:%d x H:%d' % (self._font_width, self._font_height))

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

    def _draw_char(self, ch, x, y, bold=False):
        # print("char @ %dx%d" % (x, y))
        # Don't draw the character if it will be clipped off the visible area.
        if x < -self._font_width or x >= self._gfxbuf.width or \
           y < -self._font_height or y >= self._gfxbuf.height:
            return None, None
        # Go through each column of the character.
        bpc = self.byte_count_for_height(self._font_height)
        first_pos = 0
        last_pos = len(self._gfxbuf)-1
        for char_x in range(self._font_width):
            # Grab the byte for the current column of font data.
            self._font.seek(2 + bpc*(ord(ch)*self._font_width+char_x))
            bytes_ = self._font.read(bpc)
            bits = sum([bv << (8*bp) for bp, bv in enumerate(bytes_)])
            pos = self._gfxbuf.width * (y >> 3)
            yoff = y & 7
            pos += x + char_x
            if not first_pos:
                first_pos = pos
            if pos >= last_pos:
                break
            l_col = (x + char_x) >= self._gfxbuf.width
            lbo_col = (x + char_x) >= (self._gfxbuf.width-1)
            dbg = []
            if yoff == 0:
                for col in range(bpc):
                    if not l_col:
                        self._gfxbuf.buffer[pos] |= bits & 0xff
                        dbg.append('{0:08b}'.format(bits & 0xff).replace('0',
                                   ' ').replace('1', chr(0x2589)))
                    if bold and not lbo_col:
                        self._gfxbuf.buffer[pos+1] |= bits & 0xff
                    bits >>= 8
                    pos += self._gfxbuf.width
                    if pos >= last_pos:
                        break
            else:
                bits <<= yoff
                for col in range(bpc+1):
                    if not l_col:
                        self._gfxbuf.buffer[pos] |= bits & 0xff
                        dbg.append('{0:08b}'.format(bits & 0xff).replace('0',
                                   ' ').replace('1', chr(0x2589)))
                    if bold and not lbo_col:
                        self._gfxbuf.buffer[pos+1] |= bits & 0xff
                    bits >>= 8
                    pos += self._gfxbuf.width
                    if pos >= last_pos:
                        break
            # print(''.join(reversed(dbg)))
        return first_pos, min(pos + 1 + int(bool(bold)), last_pos)

    def erase(self, x, y, w, h):
        if (x + w) > self._gfxbuf.width:
            w = self._gfxbuf.width-x
            if w < 0:
                return
        if (y + h) > self._gfxbuf.height:
            h = self._gfxbuf.height - y
            if y < 0:
                return
        ebuf = bytes([0]*w)
        yoff = y & 7
        last_y = y+h
        if yoff:
            imask = (1 << yoff) - 1
            line = y >> 3
            pos = line*self._gfxbuf.width + x
            for xix in range(pos, pos+w):
                self._gfxbuf.buffer[xix] &= imask
            y += 8 - yoff
        while (y + 8) <= last_y:
            line = y >> 3
            pos = line*self._gfxbuf.width + x
            self._gfxbuf.buffer[pos:pos+w] = ebuf
            y += 8
        yoff = last_y & 7
        if yoff:
            mask = 0xff & ~((1 << yoff) - 1)
            line = last_y >> 3
            pos = line*self._gfxbuf.width + x
            for xix in range(pos, pos+w):
                self._gfxbuf.buffer[xix] &= mask

    def text(self, text, x, y, bold=False):
        # Draw the specified text at the specified location.
        self._erase_text(text, x, y, bold)
        fpos = len(self._gfxbuf)-1
        lpos = 0
        for i in range(len(text)):
            first, last = self._draw_char(
                text[i], x + (i * (self._font_width + 1)), y, bold)
            if first is not None:
                if fpos > first:
                    fpos = first
            if last is not None:
                if lpos < last:
                    lpos = last
        lpos = min(lpos, len(self._gfxbuf)-1)
        tl = (fpos % self._gfxbuf.width, (8*fpos // self._gfxbuf.width))
        br = (lpos % self._gfxbuf.width, (8*lpos // self._gfxbuf.width))
        self._gfxbuf.invalidate(tl, br)

    def text_width(self, text, bold=False):
        # Return the pixel width of the specified text message.
        return len(text) * (self._font_width + 1) + int(bool(bold))

    def height(self):
        if not self._font_height:
            raise ValueError('Not initialized')
        return self._font_height

    def _erase_text(self, text, x, y, bold):
        xe = x + self.text_width(text, bold)
        if x > 0:
            x -= 1
        if xe < self._gfxbuf.width:
            xe += 1
        w = xe - x
        self.erase(x, y, w, self._font_height)
