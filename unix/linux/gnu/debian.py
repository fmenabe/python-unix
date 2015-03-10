# -*- coding: utf-8 -*-

import unix
import unix.linux as linux
from .. import Linux, Chroot, LinuxError

DISTRIBS = ('Debian', 'Ubuntu')

def Debian(host, force=False):
    unix.isvalid(host)

    root = host.__dict__.get('root', None)

    instances = unix.instances(host)
    if len(instances) >= 1:
        host = Linux(getattr(unix, instances[0]).clone(host))
    if root:
        host = Chroot(host, root)

    if host.distrib[0] not in DISTRIBS and not force:
        raise LinuxError('invalid distrib')

    class DebianHost(host.__class__):
        def __init__(self, root=''):
            kwargs = {'root': root} if root else {}
            host.__class__.__init__(self, **kwargs)
            self.__dict__.update(host.__dict__)


        def list_packages(self):
            return self.execute('dpkg -l')


        def set_hostname(self, hostname):
            try:
                with self.open('/etc/hostname', 'w') as fhandler:
                    fhandler.write(hostname)
            except Exception as err:
                return [False, '', err]
            return [True, '', '']

    return DebianHost(root)
