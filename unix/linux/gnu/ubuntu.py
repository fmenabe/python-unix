# -*- coding: utf-8 -*-

import unix
import weakref
from .. import Linux, Chroot, LinuxError
from .debian import Debian
from unix.linux._services import Initd, Upstart, Systemd

def Ubuntu(host, force=False):
    unix.isvalid(host)

    root = host.__dict__.get('root', None)

    instances = unix.instances(host)
    if len(instances) >= 1:
        host = Linux(getattr(unix, instances[0]).clone(host))
    if root:
        host = Chroot(host, root)
    host = Debian(host)

    if host.distrib[0] != 'Ubuntu' and not force:
        raise LinuxError('invalid distrib')

    class UbuntuHost(host.__class__):
        def __init__(self):
#            kwargs = {'root': root} if root else {}
            host.__class__.__init__(self)
            self.__dict__.update(host.__dict__)

        @property
        def services(self):
            version = float(self.distrib[1])
            if version <= 9.04:
                service_handler = Initd
            elif 9.10 <= version <= 14.10:
                service_handler = Upstart
            elif version >= 15.04:
                servivce_handler = Systemd
            return service_handler(weakref.ref(self)())

    return UbuntuHost()
