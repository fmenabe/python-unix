#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Shell display library."""

import sys
import time
import threading


################################################################################
########                       Messages functions                       ########
################################################################################
def flush(msg):
    """Flush a message in stdout.

    @type msg: str
    @param str: Message to print.
    """
    sys.stdout.write(msg)
    sys.stdout.flush()


def msg(msg, range=76):
    """Return a bash string begining at a given column.

    @type msg: str
    @param msg: Message to print.
    @type range: int
    @param range: Column number.
    """
    return "\033[%sG%s" % (range, msg)


def ok(range=76):
    """Return 'OK' string in green at a given column.

    @type range: int
    @param range: Column to start printing (default: 76).
    """
    return "\033[%sG\033[32mOK\033[00m" % range


def warn(msg, range=76):
    """Return 'WARN' string at a given column and a message in the next line,
    both in orange.

    @type range: int
    @param range: Column number.
    @type msg: str
    @param msg: Warning message.
    """
    return "\033[%sG\033[33mWARN\n%s\033[00m" % (range, msg)


def fail(msg, range=76):
    """Return 'FAIL' string in green at given column and a message next line.

    @type range: int
    @param range: Column number.
    @type msg: str
    @param msg: Fail message.
    """
    return "\033[%sG\033[31mFAIL\n%s\033[00m" % (range, msg)


def status(cmd_output, exit=False, range=76):
    """In function of output of a command (status, stdout, stderr), print the
    good output.

    @type cmd_output: list
    @param cmd_output: List with the three parameters of an output (ie: status,
                       stdout and stderr.)
    @type exit: bool
    @param exit: Quit program if the status of the command is False.
    @type range: int
    @param range: Column number.
    """
    status, stdout, stderr = cmd_output
    if not status:
        print(fail(stderr, range))
        if exit:
            sys.exit(1)
    elif stderr:
        print(warn(stderr, range))
    else:
        print(ok())


def fstr(float_number):
    number, precision = str(float_number).split('.')
    return '%s.%s' % (number, precision[:2])




################################################################################
########                          Print table                           ########
################################################################################
def print_tab_line(columns, format):
    if format is 'text':
        line = '+'
        for i in xrange(0, len(columns)):
            size = columns[i]
            for i in xrange(0, size):
                line += '-'
            line += '+'
        print line



def print_line(columns, values, format):
    if format is 'text':
        line = '|'
        for i in xrange(0, len(columns)):
            size = columns[i]
            line += ' %s' % values[i]
            remain_size = size - len(str(values[i])) - 1
            for i in xrange(0, remain_size):
                line += ' '
            line += '|'
        print line
    elif format is 'csv':
        line = ''
        for value in values:
            line += value.strip()
        pass
    elif format is 'wiki':
        pass


class Copy(threading.Thread):
    def __init__(self, host, src_path, dest_path, method='scp'):
        threading.Thread.__init__(self)
        self.host = host
        self.src_path = src_path
        self.dest_path = dest_path
        self.method = method
        command = (
            'du',
            '-s',
            self.src_path
        )
        status, stdout, stderr = cmd(command)

        self.src_size = float(
            cmd(command)[1].split()[0]
        )


    def run(self):
        self.status = self.host.get(
            self.src_path,
            self.dest_path,
            self.method,
        )


    def status(self):
        while self.isAlive():
            try:
                dest_size = float(
                    self.host.execute('du -s %s' % self.dest_path)[1].split()[0]
                )
            except IndexError:
                dest_size = 0
            completed = dest_size * 100 / self.src_size
            flush(msg('%.2f%%'))
            time.sleep(1)
        flush(msg('       '))
        return self.status


class LocalCopy(threading.Thread):
    def __init__(self, host, src_path, dest_path):
        threading.Thread.__init__(self)
        self.src_path = src_path
        self.dest_path = dest_path
        self.src_size = float(
            self.host.execute('du -s %s' % self.src_path)[1].split()[0]
        )


    def run(self):
        self.status = self.host.cp(
            self.src_path,
            self.dest_path,
        )


    def status(self):
        while self.isAlive():
            try:
                dest_size = float(
                    self.host.execute('du -s %s' % self.dest_path)[1].split()[0]
                )
            except IndexError:
                dest_size = 0
            completed = dest_size * 100 / self.src_size
            flush(msg('%.2f%%'))
            time.sleep(1)
        flush(msg('       '))
        return self.status


class RemoteCopy(threading.Thread):
    def __init__(self, src_host, src_path, dest_path, dest_host):
        threading.Thread.__init__(self)
        self.src_host = src_host
        self.src_path = src_path
        self.dest_path = dest_path
        self.dest_host = dest_host
        self.src_size = float(
            self.src_host.execute('du -s %s' % self.src_path)[1].split()[0]
        )


    def run(self):
        self.status = self.src_host.copy(
            self.src_path,
            self.dest_path,
            self.dest_host.hostname,
            method='scp'
        )


    def status(self):
        while self.isAlive():
            try:
                dest_size = float(
                    self.dest_host.execute('du -s %s' % self.dest_path)[1].split()[0]
                )
            except IndexError:
                dest_size = 0
            completed = dest_size * 100 / self.src_size
            flush(msg('%0.2f%%'))
            time.sleep(1)
        flush(msg('       '))
        return self.status


