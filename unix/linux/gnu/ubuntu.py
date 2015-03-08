# -*- coding: utf-8 -*-

import unix
from .. import Linux, LinuxError
from .debian import Debian

def Ubuntu(host, root='', force=False):
    unix.isvalid(host)

    instances = unix.instances(host)
    if len(instances) >= 1:
        host = Debian(getattr(unix, instances[0]).clone(host), root, force)

    if host.distrib[0] != 'Ubuntu' and not force:
        raise LinuxError('invalid distrib')


    class UbuntuHost(host.__class__):
        def __init__(self, root=''):
            host.__class__.__init__(self, root)
            self.__dict__.update(host.__dict__)

    return UbuntuHost(root)
