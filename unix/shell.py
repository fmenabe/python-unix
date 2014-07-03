# -*- coding: utf-8 -*-

class ShellError(Exception):
    pass

def table_border(columns):
    line = '+'
    for idx in range(0, len(columns)):
        size = columns[idx]
        for _ in range(0, size):
            line += '-'
        line += '+'
    print(line)


def table_line(columns_sizes, columns_values):
    if len(columns_sizes) != len(columns_values):
        raise ShellError("print error: len of columns is different of len of "
                         "columns values")

    lines = [[' ' * columns_sizes[__] for __ in xrange(len(columns_sizes))]]
    # Parse columns
    for column_index, column_value in enumerate(columns_values):
        column_size = columns_sizes[column_index]

        if not isinstance(column_value, (str, unicode)):
            column_value = str(column_value)
        column_value = column_value.encode('utf-8')

        line_number = 0
        # Split column on new line.
        values = column_value.split('\n')
        for value in values:
            # Split on column len.
            value_lines = []
            cur_value = ' '
            for char in value:
                if len(cur_value) == (column_size - 1):
                    cur_value += ' '
                    value_lines.append(cur_value)
                    cur_value = '  '
                cur_value += char
            value_lines.append(cur_value + ' ' * (column_size - len(cur_value)))

            for line in value_lines:
                if line_number > len(lines) - 1:
                    lines.append([' ' * columns_sizes[__]
                                  for __ in xrange(len(columns_sizes))])
                lines[line_number][column_index] = line
                line_number += 1

    print('\n'.join('|%s|' % '|'.join(line) for line in lines))
