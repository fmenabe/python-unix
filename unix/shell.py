#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Shell display library."""

import sys
import time
import threading

class QuitOnError(Exception):
    """Exception raised in the formatting methods indicating to interrupt
    current execution."""
    pass


################################################################################
########                       Messages functions                       ########
################################################################################
def flush(msg):
    """Flush a message in stdout."""
    sys.stdout.write(msg)
    sys.stdout.flush()


def msg(msg, range=76):
    """Return a bash string begining at a given column."""
    return "\033[%sG%s" % (range, msg)


def ok(range=76):
    """Return 'OK' string in green at a given column."""
    print "\033[%sG\033[32mOK\033[00m" % range


def warn(msg, range=76):
    """Return 'WARN' string at a given column and a message in the next line,
    both in orange."""
    print "\033[%sG\033[33mWARN\n%s\033[00m" % (range, msg)


def fail(msg, quit=False, range=76):
    """Return 'FAIL' string in green at given column and a message next line.
    """
    print "\033[%sG\033[31mFAIL\n%s\033[00m" % (range, msg)
    if quit:
        raise QuitOnError(msg)


def status(cmd_output, quit=False, range=76):
    """In function of output of a command (status, stdout, stderr), print the
    good output."""
    status, stdout, stderr = cmd_output
    if not status:
        fail(stderr, quit, range)
    elif stderr:
        warn(stderr, range)
    else:
        ok()


def fstr(float_number):
    number, precision = str(float_number).split('.')
    return '%s.%s' % (number, precision[:2])



################################################################################
########                          Print table                           ########
################################################################################
def print_tab_line(columns, format):
    if format == 'text':
        line = '+'
        for i in xrange(0, len(columns)):
            size = columns[i]
            for i in xrange(0, size):
                line += '-'
            line += '+'
        print line



def print_line(columns, values, format):
    if format == 'text':
        line = '|'
        for i in xrange(0, len(columns)):
            size = columns[i]
            line += ' %s' % values[i]
            remain_size = size - len(str(values[i])) - 1
            for i in xrange(0, remain_size):
                line += ' '
            line += '|'
        print line
    elif format == 'csv':
        print ','.join(values)
    elif format == 'wiki':
        print '|'.joint(values)


class Copy(threading.Thread):
    def __init__(self, host, src_path, dst_path, method='scp'):
        threading.Thread.__init__(self)
        self.host = host
        self.src_path = src_path
        self.dst_path = dst_path
        self.method = method
        self.src_size = self.size(src_path)


    def run(self):
        self.status = self.host.get(
            self.src_path,
            self.dst_path,
            self.method,
        )


    def status(self):
        while self.isAlive():
            try:
                dest_size = float(
                    self.host.execute('du -s %s' % self.dst_path)[1].split()[0]
                )
            except IndexError:
                dst_size = 0
            completed = dst_size * 100 / self.src_size
            flush(msg('%.2f%%'))
            time.sleep(1)
        flush(msg('       '))
        return self.status


class LocalCopy(threading.Thread):
    def __init__(self, host, src_path, dst_path):
        threading.Thread.__init__(self)
        self.src_path = src_path
        self.dest_path = dest_path
        self.src_size = self.src_host.size(self.src_path)
        if self.host.exists(self.dst_path):
            self.host.rm(self.dst_path)


    def run(self):
        self.status = self.host.cp(
            self.src_path,
            self.dst_path,
        )


    def status(self):
        while self.isAlive():
            try:
                dst_size = self.dst_host.size(self.dst_path)
            except OSError:
                dest_size = 0
            completed = dest_size * 100 / self.src_size
            flush(msg('%.2f%%'))
            time.sleep(1)
        flush(msg('       '))
        return self.status


class RemoteCopy(threading.Thread):
    """Thread for monitoring status of a copy a file to a remote host.

        >>> copy_thread = shell.RemoteCopy(srchost, srcpath, dsthost, dstpath)
        >>> copy_thread.start()
        >>> shell.status(copy_thread.status())
    """
    def __init__(self, src_host, src_path, dst_host, dst_path):
        threading.Thread.__init__(self)
        self.src_host = src_host
        self.src_path = src_path
        self.dst_host = dst_host
        self.dst_path = dst_path
        self.src_size = self.src_host.size(self.src_path)
        if self.dst_host.exists(self.dst_path):
            self.dst_host.rm(self.dst_path)


    def run(self):
        self.status = self.src_host.rmt_copy(
            self.src_path,
            self.dst_host.hostname,
            self.dst_path,
            method='scp'
        )


    def status(self):
        while self.isAlive():
            try:
                dst_size = self.dst_host.size(self.dst_path)
            except OSError:
                dst_size = 0
            completed = float(dst_size) * 100 / float(self.src_size)
            flush(msg('%0.2f%%' % completed))
            time.sleep(1)
        flush(msg('       '))
        return self.status


