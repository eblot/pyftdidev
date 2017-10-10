#!/usr/bin/env python3

from io import BytesIO
from os.path import dirname, join as joinpath
from sys import stdin


def show_bits(bits):
    for c in bits:
        print('  %s' % ''.join([str(b) for b in c]))
    print('')


def show_dots(bits):
    dot = chr(0x2589)
    # dot = '*'
    for c in bits:
        print('  %s .' % ''.join([b and dot or ' ' for b in c]))
    print('')


def encode(value, width):
    return bytes([(value >> (8*b) & 0xff) for b in range(width)])


def group(lst, count):
    return list(zip(*[lst[i::count] for i in range(count)]))


def rotate(line, w, h):
    byc = (w+7)//8
    bic = 8*byc
    fmt = '{0:0%db}' % bic
    if byc > 1:
        line = [sum([val << (8*off) for off, val in enumerate(vals)])
                for vals in group(line, byc)]
    pts = [[int(b) for b in fmt.format(c)] for c in line]
    rpts = list(reversed(list(zip(*pts[::-1]))))[:w]
    # show_bits(pts)
    # show_dots(rpts)
    width = (max([len(bits) for bits in rpts]))
    bw = (width+7)//8
    bytes_ = [encode(int(''.join([str(b) for b in t]), 2), bw) for t in rpts]
    return b''.join(bytes_)


def main(fp):
    infont = False
    font_name = ''
    font_ids = set()
    try:
        for pos, line in enumerate(fp, start=1):
            line = line.strip()
            if line.startswith('#ifdef '):
                font_name = line.split(' ', 1)[1].split('_')[-1].lower()
                w, h = [int(x) for x in font_name.split('x')]
                font_id = (w, h)
                if font_id not in font_ids:
                    print('Font', font_name)
                    font_ids.add(font_id)
                    continue
                break
            if font_name:
                if line.startswith('__UG_FONT_DATA'):
                    infont = True
                    size = 0
                    io = BytesIO()
                    code = -1
                    continue
            if infont:
                code += 1
                if w != 12 or h != 20:
                    continue
                if line.startswith('{'):
                    end = line.index('}')
                    line = line[1:end]
                    data = bytes([int(b, 16) for b in line.split(',')])
                    data = rotate(data, w, h)
                    if not size:
                        size = len(data)
                    elif size != len(data):
                        raise RuntimeError('Incoherent size')
                    io.write(data)
            if line.startswith('#endif'):
                infont = False
                if not io:
                    font_name = ''
                    continue
                pos = io.tell()
                if pos:
                    with open('font%dx%d.bin' % (w, h), 'wb') as fp:
                        fp.write(bytes([w, h]))
                        fp.write(io.getvalue())
                # print('Size: %d' % io.tell())
                io = None
                font_name = ''
    except Exception as ex:
        # from traceback import print_exc
        # print_exc(chain=False)
        print(ex)
        exit(0)


if __name__ == '__main__':
    with open(joinpath(dirname(__file__), 'ugui.c'), 'rt') as fp:
        main(fp)

