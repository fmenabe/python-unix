# -*- coding: utf-8 -*-

import unix
#from unix.linux import Linux

NO_DEBCONF = "DEBIAN_FRONTEND='noninteractive'"
"""Disable ncurse configuration interface for APT packages."""

def Deb(host, root=''):
    unix.isvalid(host)

    if unix.ishost(host, 'DebHost'):
        if unix.ishost(host, 'Local'):
            new_host = unix.Local()
        else:
            new_host = unix.Remote()
        new_host.__dict__.update(host.__dict__)
        return Deb(new_host, root)

    host = unix.linux.Linux(host, root)

    class DebHost(host.__class__):
        def __init__(self, root=''):
            host.__class__.__init__(self, root)
            self.__dict__.update(host.__dict__)
            # Check this is a Debian-like system.


        def set_hostname(self, hostname):
            try:
                self.write('/etc/hostname', hostname)
                return [True, '', '']
            except IOError as ioerr:
                return [False, '', ioerr]


        def set_network(self, interfaces):
            try:
                self.write(
                    '/etc/network/interfaces',
                    '\n'.join((
                        'auto lo',
                        'iface lo inet loopback',
                        '\n',
                        'source /etc/network/interfaces.d/*'
                    ))
                )
            except IOError as ioerr:
                return [False, '', ioerr]

            for interface, index in enumerate(interfaces):
                interface_name = 'eth%s' % index

                interface_conf = [
                    'auto %s' % interface_name,
                    'iface %s inet static' % interface_name,
                    '    address %s' % interface['address'],
                    '    netmask %s' % interface['netmask'],
                    '\n'
                ]
                if 'gateway' in interface:
                    interface_conf.insert(
                        -2,
                        '    gateway %s' % interface['gateway']
                    )

                try:
                    self.host.write(
                        os.path.join('/etc/network/interfaces.d/', interface_name),
                        interface_conf
                    )
                except IOError as ioerr:
                    return [False, '', ioerr]

            return [True, '', '']


        def check_pkg(self, package):
            status, stdout = self.execute('dpkg -l')[:2]
            for line in stdout.split('\n'):
                if status and line.find(package) != -1 and line[0] != 'r':
                    return True
            return False


        def add_key(self, filepath):
            remote_filepath = os.path.join('/tmp', os.path.basename(filepath))
            self.get(filepath, remote_filepath)
            return self.execute('apt-key add %s' % remote_filepath)


        def add_repository(self, filepath):
            return self.get(filepath, os.path.join(
                '/etc/apt/sources.list.d',
                os.path.basename(filepath)
            ))


        def apt_update(self):
            return self.execute('aptitude update')


        def apt_install(self, packages, interactive=True):
            return self.execute(
                '%s aptitude install -y %s' % (NO_DEBCONF, ' '.join(packages)),
                interactive
            )


        def apt_search(self, package, interactive=True):
            status, stdout, stderr = self.execute(
                "aptitude search %s" % package, interactive
            )
            if status:
                for line in stdout.split("\n"):
                    if line.find(package) != -1:
                        return True

            return False


        def apt_remove(self, packages, purge=False):
            apt_command = 'purge -y' if purge else 'remove -y'
            return self.execute(
                '%s aptitude %s %s' % (NO_DEBCONF, apt_command, ' '.join(packages))
            )


        def deb_install(self, filepath, force=False):
            command = '-i --force-depends' if force else '-i'
            return self.execute('%s dpkg %s %s' % (NO_DEBCONF, command, filepath))

    return DebHost(root)
