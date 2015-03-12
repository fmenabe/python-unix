# -*- coding: utf-8 -*-

import unix
from .. import Linux, Chroot, LinuxError
from .redhat import RedHat

def CentOS(host, root='', force=False):
    unix.isvalid(host)

    root = host.__dict__.get('root', None)

    instances = unix.instances(host)
    if len(instances) >= 1:
        host = Linux(getattr(unix, instances[0]).clone(host))
    if root:
        host = Chroot(host, root)
    host = RedHat(host)

    if host.distrib[0] != 'CentOS' and not force:
        raise LinuxError('invalid distrib')


    class CentOSHost(host.__class__):
        def __init__(self):
            host.__class__.__init__(self)
            self.__dict__.update(host.__dict__)

    return CentOSHost()
