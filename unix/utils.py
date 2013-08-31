# -*- coding: utf-8 -*-

import math

def kb2mb(value, toint=True):
    """Convert **value** size in Kb to Mb."""
    value = float(value) / 1024
    return int(math.ceil(value)) if toint else value


def kb2gb(value, toint=True):
    """Convert **value** size in Kb to Gb."""
    value = float(value) / 1024**2
    return int(math.ceil(value)) if toint else value


def kb2tb(value, toint=True):
    """Convert **value** size in Kb to Tb."""
    value = float(value) / 1024**3
    return int(math.ceil(value)) if toint else value


def mb2kb(value, toint=True):
    """Convert **value** size in Mb to Kb."""
    value = float(value) * 1024
    return int(math.ceil(value)) if toint else value


def mb2gb(value, toint=True):
    """Convert **value** size in Mb to Gb."""
    value = float(value) / 1024
    return int(math.ceil(value)) if toint else value


def mb2tb(value, toint=True):
    """Convert **value** size in Kb to Mb."""
    value = float(value) / 1024**2
    return int(math.ceil(value)) if toint else value


def gb2kb(value, toint=True):
    """Convert **value** size in Gb to Kb."""
    value = float(value) * 1024**2
    return int(math.ceil(value)) if toint else value


def gb2mb(value, toint=True):
    """Convert **value** size in Gb to Mb."""
    value = float(value) * 1024
    return int(math.ceil(value)) if toint else value


def gb2tb(value, toint=True):
    """Convert **value** size in Gb to Tb."""
    value = float(value) / 1024
    return int(math.ceil(value)) if toint else value
