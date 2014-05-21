# -*- coding: utf-8 -*-


def table_border(columns):
        line = '+'
        for idx in range(0, len(columns)):
            size = columns[idx]
            for _ in range(0, size):
                line += '-'
            line += '+'
        print(line)


def table_line(columns, values):
        line = '|'
        for i in xrange(0, len(columns)):
            size = columns[i]
            line += ' %s' % str(values[i])
            remain_size = size - len(str(values[i])) - 1
            for i in xrange(0, remain_size):
                line += ' '
            line += '|'
        print(line)
