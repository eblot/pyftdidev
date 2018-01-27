
"""Console helper routines
"""

import os
import atexit
from sys import stdin, stdout

if os.name == 'nt':
    import msvcrt
elif os.name == 'posix':
    import select
    import termios
else:
    import time


class EasyDict(dict):
    """Dictionary whose members can be accessed as instance members
    """

    def __init__(self, dictionary=None, **kwargs):
        if dictionary is not None:
            self.update(dictionary)
        self.update(kwargs)

    def __getattr__(self, name):
        try:
            return self.__getitem__(name)
        except KeyError:
            raise AttributeError("'%s' object has no attribute '%s'" %
                                 (self.__class__.__name__, name))

    def __setattr__(self, name, value):
        self.__setitem__(name, value)

    @classmethod
    def copy(cls, dictionary):

        def _deep_copy(x):
            if isinstance(x, list):
                return [_deep_copy(v) for v in x]
            elif isinstance(x, dict):
                return EasyDict({k: _deep_copy(x[k]) for k in x})
            else:
                return deepcopy(x)
        return cls(_deep_copy(dictionary))


_static_vars = EasyDict(init=False, term=stdout.isatty())


def cleanup_console():
    global _static_vars
    if 'term_config' in _static_vars:
        fd, old = _static_vars['term_config']
        termios.tcsetattr(fd, termios.TCSAFLUSH, old)
        _static_vars.init = False


def _init_term(fullterm):
    """Internal terminal initialization function"""
    if os.name == 'nt':
        return True
    elif os.name == 'posix':
        global _static_vars
        fd = stdin.fileno()
        old = termios.tcgetattr(fd)
        _static_vars.term_config = (fd, old)
        new = termios.tcgetattr(fd)
        new[3] = new[3] & ~termios.ICANON & ~termios.ECHO
        new[6][termios.VMIN] = 1
        new[6][termios.VTIME] = 0
        if fullterm:
            new[6][termios.VINTR] = 0
            new[6][termios.VSUSP] = 0
        termios.tcsetattr(fd, termios.TCSANOW, new)
        # terminal modes have to be restored on exit...
        atexit.register(cleanup_console)
        return True
    else:
        return True


def getkey(fullterm=False):
    """Return a key from the current console, in a platform independent way"""
    # there's probably a better way to initialize the module without
    # relying onto a singleton pattern. To be fixed
    global _static_vars
    if not _static_vars.init:
        _static_vars.init = _init_term(fullterm)
    if os.name == 'nt':
        # w/ py2exe, it seems the importation fails to define the global
        # symbol 'msvcrt', to be fixed
        while 1:
            z = msvcrt.getch()
            if z == b'\3':
                raise KeyboardInterrupt('Ctrl-C break')
            if z == b'\0':
                msvcrt.getch()
            else:
                if z == '\r':
                    return '\n'
                return z
    elif os.name == 'posix':
        sinfd = stdin.fileno()
        while True:
            ready = select.select([sinfd], [], [], 0.25)[0]
            if ready:
                c = os.read(sinfd, 1)
                return c
    else:
        time.sleep(1)
        return None


def is_term():
    """Tells whether the current stdout/stderr stream are connected to a
    terminal (vs. a regular file or pipe)"""
    global _static_vars
    return _static_vars.term


def is_colorterm():
    """Tells whether the current terminal (if any) support colors escape
    sequences"""
    global _static_vars
    if 'colorterm' not in _static_vars:
        terms = ['ansi', 'xterm-color', 'xterm-256color']
        _static_vars.colorterm = _static_vars.term and \
            os.environ.get('TERM') in terms
    return _static_vars.colorterm


def get_term_colors():
    """Reports the number of colors supported with the current terminal"""
    term = os.environ.get('TERM')
    if not is_term() or not term:
        return 1
    if term in ('xterm-color', 'ansi'):
        return 16
    if term in ('xterm-256color'):
        return 256
    return 1


def charset():
    """Reports the current terminal charset"""
    global _static_vars
    if 'charset' not in _static_vars:
        lang = os.environ.get('LC_ALL')
        if not lang:
            lang = os.environ.get('LANG')
        if lang:
            _static_vars.charset = \
                lang.rsplit('.', 1)[-1].replace('-', '').lower()
        else:
            _static_vars.charset = ''
    return _static_vars.charset


CSI = '\x1b['
END = 'm'
BACKGROUND_COLOR = 9
RV_FORMAT = '%s%%2d%%2d%s' % (CSI, END)
FG_FORMAT = '%s38;5;%%d%s' % (CSI, END)
BG_FORMAT = '%s48;5;%%d%s' % (CSI, END)
DF_FORMAT = '%s%02d%s' % (CSI, 40 + BACKGROUND_COLOR, END)


def _make_term_color(fg, bg, bold=False, reverse=False):
    """Emit the ANSI escape string to change the current color"""
    return '%s%02d;%02d;%02d;%02d%s' % \
        (CSI, bold and 1 or 22, reverse and 7 or 27, 30 + fg, 40 + bg, END)


def make_term_color(fg, bg, bold=False, reverse=False):
    """Emit the ANSI escape string to change the current color"""
    rev = RV_FORMAT % (bold and 1 or 22, reverse and 7 or 27)
    fore = FG_FORMAT % fg
    if bg == BACKGROUND_COLOR:
        back = DF_FORMAT
    else:
        back = BG_FORMAT % bg
    return(''.join((rev, fore, back)))


def print_progressbar(fmt, current, last, start=0, dot=None, lastfmt=None,
                      maxwidth=0, **kwargs):
    """Give user some feedback with a poor man dotgraph"""
    global _static_vars
    if not _static_vars.term:
        return
    if last == start:
        return
    WIDTH = maxwidth or 80
    EMPTYBLOCK = ord(' ')
    width = WIDTH-1-len("%06x:   00%%" % last)
    if start == current:
        level = 0
    else:
        level = width*8*(current-start)
    distance = last-start
    progress = current-start
    if charset() != 'utf8':
        fullblock = ord('.')
        if not dot:
            lastchar = EMPTYBLOCK
        else:
            lastchar = dot == 'E' and 0x2718 or ord(dot)
        if not lastfmt:
            lastfmt = fmt
        level //= distance
    else:
        fullblock = 0x2588  # unicode char
        level //= distance
        sublevel = level % 8
        if not dot:
            lastchar = sublevel and (fullblock+8-sublevel) or EMPTYBLOCK
        else:
            lastchar = dot == 'E' and 0x2718 or ord(dot)
        if not lastfmt:
            lastfmt = '%s \u2714' % fmt
    completion = (100*progress)//distance
    barcount = min(width, level//8)  # deal with rounding
    if current < last:
        barg = u''.join((chr(fullblock)*barcount,
                         chr(lastchar),
                         chr(EMPTYBLOCK)*(width-barcount+1)))
        format_ = u'\r%s\r' % fmt
    else:
        barg = chr(fullblock)*(2+barcount)
        format_ = u'\r%s\r' % lastfmt
    arguments = dict(kwargs)
    arguments.update({'pos': current,
                      'bargraph': barg,
                      'percent': completion})
    output = format_ % arguments
    stdout.write(output)
    stdout.flush()
