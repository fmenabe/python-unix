# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from six.moves import range

class ShellError(Exception):
    pass


def colorize(colors, index, value):
    try:
        return ('\033[%sm%s\033[00m' % (colors[index], value)
                if colors[index]
                else value)
    except IndexError:
        return value


def table_border(columns):
    line = '+'
    for idx in range(0, len(columns)):
        size = columns[idx]
        for _ in range(0, size):
            line += '-'
        line += '+'
    print(line)


def table_line(columns_sizes, columns_values, columns_colors=[]):
    if len(columns_sizes) != len(columns_values):
        raise ShellError("print error: len of columns is different of len of "
                         "columns values")

    lines = [[' ' * columns_sizes[__] for __ in range(len(columns_sizes))]]
    # Parse columns
    for column_index, column_value in enumerate(columns_values):
        column_size = columns_sizes[column_index] - 2

        if not isinstance(column_value, (str)):
            column_value = str(column_value)

        line_number = 0
        # Split column on new line.
        values = column_value.split('\n')
        for value in values:
            # Split on column len.
            line_value = ' %s ' % value[:column_size]
            if len(line_value) - 1 <= column_size:
                line_value += ' ' * (column_size - len(value))
            value_lines = [colorize(columns_colors, column_index, line_value)]

            value = value[column_size:]
            while value:
                line_value = '  %s ' % value
                if len(line_value) - 2 <= column_size :
                    line_value += ' ' * (column_size - (len(line_value) - 2))
                value_lines.append(colorize(columns_colors,
                                             column_index,
                                             line_value))
                value = value[(column_size - 1):]

            for line in value_lines:
                if line_number > len(lines) - 1:
                    lines.append([' ' * columns_sizes[__]
                                  for __ in range(len(columns_sizes))])
                lines[line_number][column_index] = line
                line_number += 1

    print('\n'.join('|%s|' % '|'.join(line) for line in lines))
