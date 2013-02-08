# -*- coding: utf-8 -*-

import math

def kb2mb(value):
    """Convert **value** size in Kb to Mb."""
    return int(math.ceil(float(value) / 1024))


def kb2gb(value):
    """Convert **value** size in Kb to Gb."""
    return int(math.ceil(float(value) / 1024**2))


def kb2tb(value):
    """Convert **value** size in Kb to Tb."""
    return int(math.ceil(float(value) / 1024**3))


def mb2kb(value):
    """Convert **value** size in Mb to Kb."""
    return int(math.ceil(float(value) * 1024))


def mb2gb(value):
    """Convert **value** size in Mb to Gb."""
    return int(math.ceil(float(value) / 1024))


def mb2tb(value):
    """Convert **value** size in Kb to Mb."""
    return int(math.ceil(float(value) / 1024**2))


def gb2kb(value):
    """Convert **value** size in Gb to Kb."""
    return int(math.ceil(float(value) * 1024**2))


def gb2mb(value):
    """Convert **value** size in Gb to Mb."""
    return int(math.ceil(float(value) * 1024))


def gb2tb(value):
    """Convert **value** size in Gb to Tb."""
    return int(math.ceil(float(value) / 1024))
