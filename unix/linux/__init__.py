import os
import re
import unix
import weakref
from contextlib import contextmanager
from unix.linux._conf import Conf as _Conf
from unix.linux._memory import Memory as _Memory
from unix.linux._stat import Stat as _Stat
from unix.linux._modules import Modules as _Modules


#
# Constants.
#
_FILESYSTEMS = (('proc', {'t': 'proc'}),
                ('sys', {'t': 'sysfs'}),
                ('/dev', {'o': 'bind'}))

_RELEASE_FILENAME_RE = re.compile(r'(\w+)[-_](release|version)')
_LSB_RELEASE_VERSION_RE = re.compile(r'(.+)'
                                      ' release '
                                      '([\d.]+)'
                                      '[^(]*(?:\((.+)\))?')
_RELEASE_VERSION_RE = re.compile(r'([^0-9]+)'
                                  '(?: release )?'
                                  '([\d.]+)'
                                  '[^(]*(?:\((.+)\))?')
_DISTRIBUTOR_ID_FILE_RE = re.compile(r'(?:DISTRIB_ID\s*=)\s*(.*)', re.I)
_RELEASE_FILE_RE = re.compile(r'(?:DISTRIB_RELEASE\s*=)\s*(.*)', re.I)
_CODENAME_FILE_RE = re.compile(r'(?:DISTRIB_CODENAME\s*=)\s*(.*)', re.I)

_SUPPORTED_DISTS = ('SuSE', 'debian', 'fedora', 'redhat', 'centos', 'mandrake',
                    'mandriva', 'rocks', 'slackware', 'yellowdog', 'gentoo',
                    'UnitedLinux', 'turbolinux', 'arch', 'mageia')


#
# Exceptions.
#
class LinuxError(Exception):
    pass

class ChrootError(Exception):
    pass


#
# Utils functions.
#
def distribution(host):
    distname, version, name = u'', u'', u''

    # Check for the Debian/Ubuntu /etc/lsb-release file first, needed
    # so that the distribution doesn't get identified as Debian.
    if host.path.exists('/etc/lsb-release'):
        with host.open('/etc/lsb-release') as fhandler:
            _u_distname, _u_version = u'', u''
            for line in fhandler.read().splitlines():
                regex = _DISTRIBUTOR_ID_FILE_RE.search(line.decode())
                if regex is not None:
                    _u_distname = regex.group(1).strip()
                regex = _RELEASE_FILE_RE.search(line.decode())
                if regex is not None:
                    _u_version = regex.group(1).strip()
                regex = _CODENAME_FILE_RE.search(line.decode())
                if regex is not None:
                    _u_name = regex.group(1).strip()
            if _u_distname and _u_version:
                return (_u_distname, _u_version, _u_name)

    # Get etc file of the distribution.
    for filename in sorted(host.listdir('/etc')):
        regex = _RELEASE_FILENAME_RE.match(filename)
        if regex is not None:
            _distname, _ = regex.groups()
            if _distname in _SUPPORTED_DISTS:
                distname = _distname
                break
    else:
        return host._dist_try_harder()

    # Read the first line.
    with host.open(os.path.join('/etc', filename)) as fhandler:
        firstline = fhandler.readline().decode()
    _distname, _version, _name = _parse_release_file(firstline)

    distname = _distname or distname
    if 'Red Hat' in distname:
        distname = 'RedHat'
    distname = list(distname.split()[0])
    distname = u''.join([distname[0].upper()] + distname[1:])
    return (distname, _version or version, _name or name)


def _dist_try_harder(host):
    if host.path.exists('/var/adm/inst-log/info'):
        # SuSE Linux stores distribution information in that file
        distname = 'SuSE'
        for line in host.open('/var/adm/inst-log/info'):
            line = line.decode().split()
            if len(line) != 2:
                continue
            tag, value = line
            if tag == 'MIN_DIST_VERSION':
                version = value.strip()
            elif tag == 'DIST_IDENT':
                name = value.split('-')[2]
        return distname, version, name

    if host.path.exists('/etc/.installed'):
        # Caldera OpenLinux has some infos in that file
        # (thanks to Colin Kong)
        for line in open('/etc/.installed'):
            pkg = line.decode().split('-')
            if len(pkg) >= 2 and pkg[0] == 'OpenLinux':
                # XXX does Caldera support non Intel platforms ? If yes,
                #     where can we find the needed name ?
                return 'OpenLinux', pkg[1], u''

    if host.path.isdir('/usr/lib/setup'):
        # Check for slackware version tag file (thanks to Greg Andruk)
        verfiles = host.listdir('/usr/lib/setup')
        for n in range(len(verfiles)-1, -1, -1):
            if verfiles[n][:14] != 'slack-version-':
                del verfiles[n]
        if verfiles:
            verfiles.sort()
            distname = 'slackware'
            version = verfiles[-1][14:]
            return distname, version, id


def _parse_release_file(firstline):
    version, name = u'', u''

    # LSB format: "distro release x.x (codename)"
    regex = _LSB_RELEASE_VERSION_RE.match(firstline)
    if regex is not None:
        return tuple(regex.groups())

    # Pre-LSB format: "distro x.x (codename)"
    regex = _RELEASE_VERSION_RE.match(firstline)
    if regex is not None:
        return tuple(regex.groups())

    # Unknown format... take the first two words
    line = firstline.strip().split()
    if line:
        version = line[0]
        if len(line) > 1:
            name = line[1]
    return u'', version, name


#
# Base class for managing linux hosts.
#
def Linux(host):
    unix.isvalid(host)
    host.is_connected()

    instances = unix.instances(host)
    if len(instances) > 1:
        host = getattr(unix, instances[0]).clone(host)

    host_type = host.type
    if host_type != 'linux':
        raise LinuxError('this is not a Linux host (%s)' % host_type)

    class LinuxHost(host.__class__):
        def __init__(self):
            host.__class__.__init__(self)
            self.__dict__.update(host.__dict__)


        @property
        def distrib(self):
            return distribution(self)


        @property
        def chrooted(self):
            return False


        @property
        def conf(self):
            return _Conf(weakref.ref(self)())


        @property
        def memory(self):
            return _Memory(weakref.ref(self)())


        def stat(self, filepath):
            return _Stat(weakref.ref(self)(), filepath)


        @property
        def modules(self):
            return _Modules(weakref.ref(self)())


        def fstab(self, filepath='/etc/fstab'):
            filesystems = {}
            with self.open(filepath) as fhandler:
                return {elts[1]: {'fs': elts[0],
                                  'type': elts[2],
                                  'options': elts[3],
                                  'dump': elts[4],
                                  'pass': elts[5]}
                        for line in fhandler.read().splitlines()
                        if line and not line.decode().startswith('#')
                        for elts in [line.decode().split()]}


    return LinuxHost()


def Chroot(host, root):
    unix.isvalid(host)
    host.is_connected()

    if root and host.username != 'root':
        raise ChrootError('you need to be root for chroot')

    instances = unix.instances(host)
    if len(instances) > 1:
        host = getattr(unix, instances[0]).clone(host)
    host = Linux(host)

    class ChrootHost(host.__class__):
        def __init__(self, root):
            host.__class__.__init__(self)
            self.__dict__.update(host.__dict__)
            self.root = root


        @property
        def chrooted(self):
            return True


        def execute(self, cmd, *args, **kwargs):
            if self.root:
                cmd = 'chroot %s %s' % (self.root, cmd)
            result = host.execute(cmd, *args, **kwargs)
            # Set return code of the parent. If not set some functions (like
            # Path) does not work correctly on chrooted objects.
            self.return_code = host.return_code
            return result


        def open(self, filepath, mode='r'):
            if self.root:
                filepath = filepath[1:] if filepath.startswith('/') else filepath
                filepath = os.path.join(self.root, filepath)
            return host.open(filepath, mode)


        @contextmanager
        def set_controls(self, **controls):
            cur_controls = dict(host.controls)

            try:
                for control, value in controls.items():
                    host.set_control(control, value)
                yield None
            finally:
                for control, value in cur_controls.items():
                    host.set_control(control, value)


        def chroot(self):
            for (fs, opts) in _FILESYSTEMS:
                status, _, stderr = host.mount(fs, os.path.join(root, fs), **opts)
                if not status:
                    raise ChrootError("unable to mount '%s': %s" % (fs, stderr))


        def unchroot(self):
            for fs in _FILESYSTEMS:
                status, _, stderr = host.umount(os.path.join(root, fs[0]))
                if not status:
                    raise ChrootError("unable to umount '%s': %s" % (fs, stderr))


    return ChrootHost(root)


#
# Context Manager for connecting to a remote host.
#
class connect(object):
    def __init__(self, host, **kwargs):
        self.hostname = host
        self.options = kwargs

    def __enter__(self):
        self._host = unix.Remote()
        self._host.connect(self.hostname, **self.options)
        self._host = Linux(self._host)
        try:
            from . import gnu
            self._host = getattr(gnu, self._host.distrib[0])(self._host)
        except AttributeError:
            pass
        return self._host

    def __exit__(self, type, value, traceback):
        self._host.disconnect()
        del self._host


#
# Context Manager for chroot.
#
class chroot(object):
    def __init__(self, parent, root, distrib=None, force=False):
        self.host = Chroot(Linux(parent), root)

        try:
            from . import gnu
            if distrib is None:
                self.host = getattr(gnu, self.host.distrib[0])(self.host, root)
            else:
                self.host = getattr(gnu, distrib)(self.host, root, force)
        except AttributeError:
            pass

    def __enter__(self):
        self.host.chroot()
        return self.host

    def __exit__(self, type, value, traceback):
        self.host.unchroot()
        del self.host
