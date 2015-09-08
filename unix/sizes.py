# -*- coding: utf-8 -*-

import sys
import math

def convert(value, power, si=False, toint=True):
    multiple = 1000 if not si else 1024
    value = (float(value) / multiple**-power
             if power < 0
             else float(value) * multiple**power)
    return int(math.ceil(value)) if toint else value

FUNCTIONS = {'b2kb': -1,
             'b2mb': -2,
             'b2gb': -3,
             'b2tb': -4,
             'b2pb': -5,
             'kb2b': 1,
             'kb2mb': -1,
             'kb2gb': -2,
             'kb2tb': -3,
             'kb2pb': -4,
             'mb2b': 2,
             'mb2kb': 1,
             'mb2gb': -1,
             'mb2tb': -2,
             'mb2pb': -3,
             'gb2b': 3,
             'gb2kb': 2,
             'gb2mb': 1,
             'gb2tb': -1,
             'gb2pb': -2,
             'tb2b': 4,
             'tb2kb': 3,
             'tb2mb': 2,
             'tb2gb': 1,
             'tb2pb': -1,
             'pb2b': 5,
             'pb2kb': 4,
             'pb2mb': 3,
             'pb2gb': 2,
             'pb2tb': 1}

for func, power in FUNCTIONS.items():
    setattr(sys.modules[__name__],
            func,
            lambda value, power=power, si=False, toint=True: convert(value, power, si, toint))

UNITS = ('b', 'kb', 'mb', 'gb', 'tb', 'pb')
def human(size, from_unit='kb', si=False, fmt='%.0f'):
    size = str(size)
    try:
        to_unit = UNITS[UNITS.index(from_unit) + (len(size) % 3 + 1)]
    except IndexError:
        to_unit = UNITS[-1]
    func = '%s2%s' % (from_unit, to_unit)
    new_size = getattr(sys.modules[__name__], func)(size, si=si, toint=False)
    fmt += '%s'
    return fmt % (new_size, to_unit[0].upper())
