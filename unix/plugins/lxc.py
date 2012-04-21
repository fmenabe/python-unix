import os
import time
#from hosts import Host, ConnectError, CommandError
from unix.remote import Host, ConnectError, CommandError


class LXC(Host):
    def __init__(self, path, templates, host=None):
        Host.__init__(self)
        if host:
            self.__dict__.update(host.__dict__)
        self.root = path
        self.templates_dir = templates


    def lxc_cmd(self, cmd, options):
        pass


    def list(self):
        pass


    def exist(self, container):
        status, stdout, stderr = self.execute('lxc-ls')
        if not status:
            raise CommandError(stderr)

        return True if container in stdout.split('\n')[0].split() else False


class ContainerNotExist(Exception):
    pass


class LXCContainer(Host):
    def __init__(self, name, lxc_host):
        self.parent = lxc_host
        self.name = name
        self.root = os.path.join(self.parent.root, name)
        self.rootfs = os.path.join(self.root, 'rootfs')
        self.config_file = os.path.join(self.root, 'config')
        self.fstab_file = os.path.join(self.root, 'fstab')


    def replace(self, tmpl_path, params):
        with open(tmpl_path, 'r') as tmpl_file:
            content = tmpl_file.read()

        for key, value in params.iteritems():
            content = content.replace('$%s' % key, value)

        return content


    ############################################################################
    ########                       LXC commands                         ########
    ############################################################################
    def _exist(self):
        if not self.parent.exist(self.name):
            raise ContainerNotExist


    def started(self):
        self._exist()
        status, stdout, stderr = self.parent.execute('lxc-info -n %s' % self.name)
        return True if self.name in lxc_containers else False


    def start(self):
        self._exist()
        status, stdout, stderr = self.parent.execute("lxc-start -n %s -d" % self.name)
        time.sleep(1)
        if status and not self.started():
            return (False, '', 'Unknow Error! Container is not started.')
        return (status, stdout,stderr)


    def stop(self):
        self._exist()
        return self.parent.execute("lxc-stop -n %s" % self.name)


    def destroy(self):
        self._exist()
#        return self.parent.execute("lxc-destroy -n %s" % self.name)
        return self.parent.execute("rm -r %s" % self.root)


    def chroot(self, command):
        self._exist()
        return self.parent.execute("chroot %s %s" % (
            self.rootfs,
            " ".join(command)
        ))


    ############################################################################
    ########             Create/Configure container system              ########
    ############################################################################
    def copy_system(self, src):
#        self.parent.execute('mkdir -p %s' % self.root)
        transform_expr = 's/%s//g' % os.path.basename(src)
        return self.parent.tar_copy(src, self.rootfs, transform=transform_expr)


    def debootstrap(self, release, packages, arch='amd64'):
        debootstrap_cmd = ' '.join((
            'debootstrap',
            '--variant=minbase',
            '--components=main,universe',
            '--arch=%s' % arch,
            '--include=%s' % ','.join(packages),
            release,
            self.rootfs
        ))
        return self.parent.execute(debootstrap_cmd)


    def set_network(self, ip, netmask, gateway, network):
        return self.parent.write(
            os.path.join(self.rootfs, 'etc', 'network', 'interfaces'),
            self.replace(
                os.path.join(self.tmpls, 'interfaces.tmpl'),
                {
                    'IP': ip,
                    'NETMASK': netmask,
                    'NETWORK': network,
                    'GATEWAY': gateway
                }
            )
        )


    def set_dns(self, nameserver, search):
        filepath = os.path.join(self.rootfs, 'etc', 'resolv.conf')
        # Deleting symlink to LXC host configuration.
        self.parent.execute("rm %s" % filepath)
        return self.parent.write(
            filepath,
            self.replace(
                os.path.join(self.tmpls, 'resolv.conf.tmpl'),
                {
                    'IP': nameserver,
                    'DOMAIN': search
                }
            )
        )

    def set_hostname(self):
        return self.parent.write(
            os.path.join(self.rootfs, 'etc', 'hostname'),
            self.name
        )


    def set_hosts(self, domain):
        return self.parent.write(
            os.path.join(self.rootfs, 'etc', 'hosts'),
            self.replace(
                os.path.join(self.tmpls, 'hosts.tmpl'),
                {
                    'NAME': self.name,
                    'DOMAIN': domain
                }
            )
        )


    def fix_udev(self):
        return self.parent.execute(
            'sed -i "s/=\"err\"/=0/" %s/etc/udev/udev.conf' % self.rootfs
        )


    def set_lxc_guest_conf(self):
        return self.parent.copy(
            os.path.join(self.tmpls, 'lxc.conf'),
            os.path.join(self.rootfs, 'etc', 'init', 'lxc.conf')
        )


    def fix_ssh(self):
        return self.parent.copy(
            os.path.join(self.tmpls, 'ssh.conf'),
            os.path.join(self.rootfs, 'etc', 'init', 'ssh.conf')
        )


    def clean_fstab(self):
        return self.parent.write(
            os.path.join(self.rootfs, 'lib', 'init', 'fstab'),
            '# /lib/init/fstab: cleared out for bare-bones lxc'
        )


    def fix_network_upstart(self):
        return self.parent.execute(" ".join(
            'sed -i',
            "s/^.*emission handled.*$/echo Emitting lo/",
            os.path.join(self.rootfs, 'etc', 'network', 'if-up.d', 'upstart')
        ))


    def set_password(self, username):
        return self.lxc_host.set_password(
            username,
            password,
            os.path.join(self.rootfs, 'etc', 'shadow')
        )


    def set_locale(self, locale):
        # Generating locale.
        output = self.chroot(('locale-gen', locale))
        if not output[0]:
            return (
                False,
                '',
                "Unable to generating locale '%s':\n%s" % (locale, output[2])
            )

        # Setting locale.
        output = self.chroot(('update-locale', 'LANG=%s' % locale))
        if not output[0]:
            return (
                False,
                '',
                "Unable to set locale '%s':\n%s" % (locale, output[2])
            )
        return output


    def del_service(self, service):
        return self.chroot((
            '/usr/sbin/update-rd.d',
            '-f',
            service,
            'remove'
        ))


    def clean_init_conf(self):
        output = self.chroot((
            '/bin/bash',
            '-c',
            "'cd /etc/init; for f in $(ls u*.conf); do mv $f $f.orig; done'"
        ))
        self.chroot((
            '/bin/bash',
            '-c',
            "'cd /etc/init; for f in $(ls tty[2-9].conf); do mv $f $f.orig; done'"
        ))
        self.chroot((
            '/bin/bash',
            '-c',
            "'cd /etc/init; for f in $(ls plymouth*.conf); do mv $f $f.orig; done'"
        ))
        self.chroot((
            '/bin/bash',
            '-c',
            "'cd /etc/init; for f in $(ls hwclock*.conf); do mv $f $f.orig; done'"
        ))
        self.chroot((
            '/bin/bash',
            '-c',
            "'cd /etc/init; for f in $(ls module*.conf); do mv $f $f.orig; done'"
        ))

    ############################################################################
    ########                       Configure LXC                        ########
    ############################################################################
    def create_root(self):
        return self.parent.execute('mkdir -p %s' % self.rootfs)


    def set_lxc_config(self):
        return self.parent.write(
            os.path.join(self.root, 'config'),
            self.replace(
                os.path.join(self.tmpls, 'config.tmpl'),
                {
                    'NAME': self.name,
                    'ROOTFS': self.rootfs,
                    'PATH': self.root
                }
            )
        )


    def set_lxc_fstab(self):
        self.parent.execute("mkdir -p %s" % os.path.join(
            '/nfs',
            'www',
            self.name,
        ))
        return self.parent.write(
            os.path.join(self.root, 'fstab'),
            self.replace(
                os.path.join(self.tmpls, 'fstab.tmpl'),
                {
                    'NAME': self.name,
                    'ROOTFS': self.rootfs
                }
            )
        )



class DjangoContainer(LXCContainer):
    def __init__(self, packages):
        LXCContainer.__init__(self)


