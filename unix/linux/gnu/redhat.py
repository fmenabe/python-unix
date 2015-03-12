# -*- coding: utf-8 -*-

import re
import os
import unix
from .. import Linux, Chroot, LinuxError

DISTRIBS = ('RedHat', 'CentOS')

_CONFDIR =  '/etc/sysconfig'
_NETFILE = os.path.join(_CONFDIR, 'network')

def RedHat(host, force=False):
    unix.isvalid(host)

    root = host.__dict__.get('root', None)

    instances = unix.instances(host)
    if len(instances) >= 1:
        host = Linux(getattr(unix, instances[0]).clone(host))
    if root:
        host = Chroot(host, root)

    if host.distrib[0] not in DISTRIBS and not force:
        raise LinuxError('invalid distrib')

    class RedHatHost(host.__class__):
        def __init__(self):
            kwargs = {'root': root} if root else {}
            host.__class__.__init__(self, **kwargs)
            self.__dict__.update(host.__dict__)


        def list_packages(self):
            return self.execute('dpkg -l')


        @property
        def hostname(self):
            with self.open(_NETFILE) as fhandler:
                for line in fhandler.read().splitlines():
                    attr, value = line.split('=')
                    if attr == 'HOSTNAME':
                        return value


        @hostname.setter
        def hostname(self, value):
            contnet = ''
            with self.open(_NETFILE) as fhandler:
                content = re.sub('HOSTNAME=[^\n]*',
                                 'HOSTNAME=%s\n' % value,
                                 fhandler.read())
            with self.open(_NETFILE, 'w') as fhandler:
                fhandler.write(content)

    return RedHatHost()
