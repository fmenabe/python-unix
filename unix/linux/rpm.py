# -*- coding: utf-8 -*-

import os.path as path
import unix

def Rpm(host, root=''):
    unix.isvalid(host)

    if unix.ishost(host, 'RpmHost'):
        if unix.ishost(host, 'Local'):
            new_host = unix.Local()
        else:
            new_host = unix.Remote()
        new_host.__dict__.update(host.__dict__)
        return Rpm(new_host, root)

    host = unix.linux.Linux(host, root)


    class RpmHost(host.__class__):
        def __init__(self, root=''):
            host.__class__.__init__(self, root)
            self.__dict__.update(host.__dict__)


        def set_hostname(self, hostname):
            try:
                self.write(
                    '/etc/sysconfig/network',
                    '\n'.join((
                        'NETWORKING=yes',
                        'NETWORKING_IPV6=no',
                        'HOSTNAME=%s' % hostname
                    ))
                )
                return [True, '', '']
            except IOError as ioerr:
                return [False, '', ioerr]


        def set_network(self, interfaces):
            network_root = '/etc/sysconfig/network-scripts'
            self.rm(path.join(network_root, 'ifcfg-ext'))
            for index, interface in enumerate(interfaces):
                interface_conf = [
                    'DEVICE=eth%s' % index,
                    'BOOTPROTO=none',
                    'ONBOOT=yes',
                    'NETMASK=%s' % interface['netmask'],
                    'IPADDR=%s' % interface['address'],
                    'TYPE=Ethernet',
                    'USERCTL=no',
                    'IPV6INIT=no',
                    'PEERDNS=yes'
                ]

                if 'gateway' in interface:
                    interface_conf.insert(5, 'GATEWAY=%s' % interface['gateway'])

                try:
                    self.write(
                        path.join(network_root, 'ifcfg-eth%s' % index),
                        '\n'.join(interface_conf)
                    )
                except IOError as ioerr:
                    return [False, '', ioerr]

            return [True, '', '']


        def check_pkg(self, package):
            status, stdout = self.execute('rpm -qa')[:2]
            if status and stdout.find(package) != -1:
                return True
            return False


        def add_repository(self, filepath):
            return self.get(filepath, os.path.join(
                '/etc/yum.repos.d',
                os.path.basename(filepath))
            )


        def yum_install(self, packages, interative=True,repository=''):
            yum_cmd = '-y' if not repository else '-y --enablerepo=%s' % repository
            return self.execute(
                'yum install %s %s' % (yum_cmd, ' '.join(packages)),
                interactive
            )


        def yum_remove(self, packages):
            return self.execute('yum erase -y %s' % ' '.join(packages))


        def rpm_install(self, filepath):
            return self.execute('rpm -U %s' % filepath)

    return RpmHost(root)
