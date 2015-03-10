# -*- coding: utf-8 -*-

import sys
import unix
from .. import Linux, Chroot, LinuxError

SELF = sys.modules[__name__]


def Arch(host, force=False):
    unix.isvalid(host)

    root = host.__dict__.get('root', None)

    instances = unix.instances(host)
    if len(instances) >= 1:
        host = Linux(getattr(unix, instances[0]).clone(host))
    if root:
        host = Chroot(host, root)

    if host.distrib[0] != 'Arch' and not force:
        raise LinuxError('invalid distrib')


    class ArchHost(host.__class__):
        def __init__(self, root):
            kwargs = {'root': root} if root else {}
            host.__class__.__init__(self, **kwargs)
            self.__dict__.update(host.__dict__)

    return ArchHost(root)
