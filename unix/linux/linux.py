# -*- coding: utf-8 -*-

import os
import crypt
import random
import string
from datetime import datetime
import unix

HOSTS_CONTENT= """127.0.0.1    localhost
$(IP)   $(HOSTNAME).$(DOMAIN)   $(HOSTNAME)

# The following lines are desirable for IPv6 capable hosts
::1     localhost ip6-localhost ip6-loopback
fe00::0 ip6-localnet
ff00::0 ip6-mcastprefix
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
"""

def Linux(host, root=''):
    # Check it a valid host (ie: *Local* or *Remote*)
    unix.isvalid(host)

    if unix.ishost(host, 'LinuxHost'):
        if unix.ishost(host, 'Local'):
            new_host = unix.Local()
        else:
            new_host = unix.Remote()
        new_host.__dict__.update(host.__dict__)
        return Linux(new_host, root)

    class LinuxHost(host.__class__):
        """Inherit class from *host* and deepcopy object."""
        def __init__(self, root=''):
            host.__class__.__init__(self)
            self.__dict__.update(host.__dict__)
            # If *root*, check that the directory contain
            # a valid Linux environment.
            self.root = root


        @property
        def distrib(self):
            if not self.which('lsb_release'):
                # Use alternative way for finding OS.
                raise NotImplementedError(
                    'search linux distribution without using lsb_release')
            else:
                return self.execute(
                    'lsb_release -i')[1].split(':')[1].strip().lower()


        def __chroot(self):
            """Mount specials filesystems for having a  "valid" chrooted
            environment. This may be needed when install a package in a
            chrooted environment for example."""
            # Use parent (ie: Local or Remote) *execute* function.
            super(LinuxHost, self).execute(
                'mount -t proc proc %s/proc/' % self.root
            )
            super(LinuxHost, self).execute(
                'mount -t sysfs sys %s/sys/' % self.root
            )
            super(LinuxHost, self).execute(
                'mount -o bind /dev %s/dev/' % self.root
            )


        def __unchroot(self):
            """Umount specials filesystems on the chrooted environment."""
            # Use parent (ie: Local or Remote) *execute* function.
            super(LinuxHost, self).execute('umount %s/proc/' % self.root)
            super(LinuxHost, self).execute('umount %s/sys/' % self.root)
            super(LinuxHost, self).execute('umount %s/dev/' % self.root)


        def execute(self, command, interactive=False, chroot=False):
            """Refine the *execute* wrapper function, taking into account if
            it must be executed in a chrooted environment. if *chroot* is
            given, specials filesystems (*proc*, *sys* and *dev*) are mounted
            before execution of the command and unmounted after.
            """
            if chroot and self.root:
                self.__chroot()
            command = 'chroot %s %s' % (self.root, command) \
                if self.root \
                else command
            result = super(LinuxHost, self).execute(command, interactive)
            if chroot and self.root:
                self.__unchroot()
            return result


        def read(self, path, **kwargs):
            """Refine the *read* function, taking into account if it must be
            executed in a chroot environment."""
            if self.root:
                if not os.path.isabs(path):
                    raise IOError("'%s' is not an absolute path")
                path = os.path.join(self.root, path[1:])
            return super(LinuxHost, self).read(path, **kwargs)


        def write(self, path, content, **kwargs):
            """Refine the *write* function, taking into account if it must be
            executed in a chroot environment."""
            if self.root:
                if not os.path.isabs(path):
                    raise IOError("'%s' is not an absolute path")
                path = os.path.join(self.root, path[1:])
            super(LinuxHost, self).write(path, content, **kwargs)


        def isloaded(self, module):
            status, stdout, stderr = self.execute('lsmod')
            if not status:
                return False

            for line in stdout.split('\n')[1:-1]:
                if line.split()[0] == module:
                    return True
            return False


        def load(self, module, options=()):
            return self.execute('modprobe %s %s' % (module, ' '.join(options)))


        def unload(self, module):
            return self.execute('modprobe -r %s' % module)


        def service(self, name, action, type='upstart'):
            return self.execute(
                {
                    'upstart': lambda: "service %s %s" % (name, action),
                    'init': lambda: "/etc/init.d/%s %s" % (name, action)
                }.get(type)()
            )


        def set_password(self, username, password):
            shadow_file = '/etc/shadow'
            hashed_password = crypt.crypt(password, '$6$%s$' % ''.join(
                [random.choice(string.letters + string.digits) for i in xrange(0,8)]
            ))
            shadow_line = '%s:%s:%s:0:99999:7:::' % (
                username,
                hashed_password,
                (datetime.today() - datetime(1970, 1, 1)).days
            )

            new_content = []
            in_file = False
            for line in self.readlines(shadow_file):
                if line.find(username) != -1:
                    new_content.append(shadow_line)
                    in_file = True
                else:
                    new_content.append(line)
            if not in_file:
                new_content.append(shadow_line)
            try:
                self.write(shadow_file, '\n'.join(new_content))
                return [True, '', '']
            except IOError:
                return [False, '', ioerr]


        def set_hosts(self, ip, hostname, domain):
            try:
                self.write(
                    '/etc/hosts',
                    HOSTS_CONTENT \
                        .replace("$(IP)", ip) \
                        .replace("$(HOSTNAME)", hostname) \
                        .replace("$(DOMAIN)", domain)
                )
                return [True, '', '']
            except IOError as ioerr:
                return [False, '', ioerr]


        def set_sshkeys(self, algos=['rsa', 'dsa']):
            sshd_dir = '/etc/ssh'
            keys = [
                os.path.join(sshd_dir, filename) \
                for filename in self.listdir(sshd_dir) if 'ssh_host_' in filename
            ]
            for key in keys:
                output = self.execute("rm %s" % key)
                if not output[0]:
                    output[2] = "Unable to remove old keys: %s" % output[2]
                    return output

            for algo in algos:
                output = self.execute(
                    'ssh-keygen -N "" -t %s -f %s/ssh_host_%s_key' % (
                        algo, sshd_dir, algo
                    )
                )
                if not output[0]:
                    output[2] = "Unable to generate %s keys: %s" % (
                        algo.upper(), output[2]
                    )
                    return output
            return [True, '', '']

    return LinuxHost(root)
