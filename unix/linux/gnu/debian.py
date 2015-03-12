# -*- coding: utf-8 -*-

import os
import weakref
import unix
import unix.linux as linux
from .. import Linux, Chroot, LinuxError

DISTRIBS = ('Debian', 'Ubuntu')

_HOSTNAMEFILE = '/etc/hostname'
_NETFILE = '/etc/network/interfaces'
_NETDIR = '/etc/network/interfaces.d'
_LOINT = """auto lo
iface lo inet loopback"""

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
        def __init__(self):
            kwargs = {'root': root} if root else {}
            host.__class__.__init__(self, **kwargs)
            self.__dict__.update(host.__dict__)


        def list_packages(self):
            return self.execute('dpkg -l')


        @property
        def hostname(self):
            with self.open(_HOSTNAMEFILE) as fhandler:
                return fhandler.read().decode().strip()


        @hostname.setter
        def hostname(self, value):
            with self.open(_HOSTNAMEFILE, 'w') as fhandler:
                fhandler.write(value)


        @property
        def network(self):
            return _Network(weakref.ref(self)())


    return DebianHost()


class _Network:
    def __init__(self, host):
        self._host = host


    def configure(self, interfaces):
        distrib, version = self._host.distrib[0:2]
        split_files = distrib == 'Ubuntu' and float(version) > 11.04

        try:
            with self._host.open(_NETFILE, 'w') as fhandler_main:
                fhandler_main.write(_LOINT)

                if split_files:
                    fhandler_main.write('\nsource %s/*' % _NETDIR)
                    if self._host.path.exists(_NETDIR):
                        self._host.mkdir(_NETDIR)

                for index, interface in enumerate(interfaces):
                    name = interface.pop('name', 'eth%s' % index)
                    inet = interface.pop('inet', 'dhcp')

                    conf = ['auto %s' % name, 'iface %s inet %s' % (name, inet)]
                    if inet == 'static':
                        address = interface.pop('address')
                        netmask = interface.pop('netmask')
                        conf.extend(('    address %s' % address,
                                     '    netmask %s' % netmask))
                    else:
                        for param in ('address', 'netmask', 'gateway'):
                            interface.pop(param, None)
                    conf.extend('    %s %s' % (attr, value)
                                for attr, value in interface.items()
                                if value)

                    if split_files:
                        int_file = os.path.join(_NETDIR, name)
                        with self._host.open(int_file, 'w') as fhandler_int:
                            fhandler_int.write('\n'.join(conf))
                    else:
                        conf.insert(0, '\n')
                        fhandler_main.write('\n'.join(conf))
        except OSError as err:
            return [False, u'', err]
        return [True, u'', u'']
