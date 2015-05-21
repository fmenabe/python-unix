# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import sys
import subprocess

class ShellError(Exception):
    pass


class QuitOnError(Exception):
    pass


width = lambda: int(subprocess.check_output(['tput', 'cols']))
height = lambda: int(subprocess.check_output(['tput', 'lines']))

#
# Messages.
#
def flush(msg):
    """Flush a message in stdout."""
    sys.stdout.write(msg)
    sys.stdout.flush()


def msg(msg, start=76):
    """Return a shell string beggining at the **start** column."""
    return '\033[%sG%s' % (start, msg)


def ok(start=76):
    """Print the string 'OK' in green at the **start** column."""
    print('\033[%sG\033[32mOK\033[00m' % start)


def warn(msg, start=76):
    """Print the string 'WARN' in orange at the **start** column and the string
    **msg** in the next lines."""
    print('\033[%sG\033[33mWARN\n%s\033[00m' % (start, msg))


def fail(msg, quit=False, start=76):
    """Print the string 'FAIL' in red at the **start** column and the string
    **msg** in the next lines. If quit is *True*, the exception **QuitOnError**
    is raised.
    """
    print('\033[%sG\033[31mFAIL\n%s\033[00m' % (start, msg))
    if quit:
        raise QuitOnError(msg)


def status(result, quit=False, start=76):
    """Manage the result (status, stdout, stderr) of the execution of a command.
    """
    status, stdout, stderr = result
    if not status:
        fail(stderr, quit, start)
    elif stderr:
        warn(stderr, start)
    else:
        ok(start)


#
# Tables.
#
colorize = lambda color, value: '\033[%s%s\033[00m' % (color, value)


def table_border(columns, color=None):
    line = '+'
    for idx in range(0, len(columns)):
        size = columns[idx]
        for _ in range(0, size):
            line += '-'
        line += '+'
    if color:
        line = '\033[%s%s\033[00m' % (color, line)
    print(line)


def table_line(sizes, columns, colors=[], borders_color=None, indent=1):
    if len(sizes) != len(columns):
        raise ShellError('length of sizes is different from length of values')

    lines = []
    for index, value in enumerate(columns):
        size = sizes[index] - 2
        if not isinstance(value, str):
            value = str(value)

        line_number = 0
        column_lines = []

        # Split column value on new line.
        value_lines = value.split('\n')
        for line in value_lines:
            # Split line on word.
            line = line.split()
            cur_line = ' '
            while line:
                word = line.pop(0)
                new_line = cur_line + word + ' '
                if len(new_line) >= size + 2:
                    new_line += ' ' * (size + 2 - len(new_line))
                    column_lines.append(new_line)
                    cur_line = ' ' * indent + ' '
                else:
                    cur_line = new_line
            if cur_line.strip():
                cur_line += ' ' * (size + 2 - len(cur_line))
                column_lines.append(cur_line)

        # Add column lines.
        for line in column_lines:
            if line_number > len(lines) - 1:
                # Initialize a new line.
                new_line = []
                for __ in range(len(sizes)):
                   new_column = ' ' * sizes[__]
                   if colors and colors[__]:
                       new_column = colorize(colors[index], new_column)
                   new_line.append(new_column)
                lines.append(new_line)
            if colors and colors[index]:
                line = colorize(colors[index], line)
            lines[line_number][index] = line
            line_number += 1

    border = '|' if not borders_color else colorize(borders_color, '|')
    print('\n'.join(border + border.join(line) + border for line in lines))
