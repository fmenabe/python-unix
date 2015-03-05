# -*- coding: utf-8 -*-

import os
import re
import unix

_RELEASE_FILENAME_RE = re.compile(r'(\w+)[-_](release|version)')
_LSB_RELEASE_VERSION_RE = re.compile(r'(.+)'
                                     ' release '
                                     '([\d.]+)'
                                     '[^(]*(?:\((.+)\))?', re.ASCII)
_RELEASE_VERSION_RE = re.compile(r'([^0-9]+)'
                                 '(?: release )?'
                                 '([\d.]+)'
                                 '[^(]*(?:\((.+)\))?', re.ASCII)
_DISTRIBUTOR_ID_FILE_RE = re.compile("(?:DISTRIB_ID\s*=)\s*(.*)", re.I)
_RELEASE_FILE_RE = re.compile("(?:DISTRIB_RELEASE\s*=)\s*(.*)", re.I)
_CODENAME_FILE_RE = re.compile("(?:DISTRIB_CODENAME\s*=)\s*(.*)", re.I)

_SUPPORTED_DISTS = ('SuSE', 'debian', 'fedora', 'redhat', 'centos', 'mandrake',
                    'mandriva', 'rocks', 'slackware', 'yellowdog', 'gentoo',
                    'UnitedLinux', 'turbolinux', 'arch', 'mageia')

#
# Exceptions.
#
class LinuxError(Exception):
    pass

#
# Utils functions.
#
def distribution(host):
    distname, version, name = '', '', ''

    # check for the Debian/Ubuntu /etc/lsb-release file first, needed
    # so that the distribution doesn't get identified as Debian.
    if host.path.exists('/etc/lsb-release'):
        with host.open('/etc/lsb-release') as fhandler:
            _u_distname, _u_version = '', ''
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
        firstline = fhandler.readline()
    _distname, _version, _name = _parse_release_file(firstline)

    distname = _distname or distname
    if 'Red Hat' in distname:
        distname = 'RedHat'
    distname = list(distname.split()[0])
    distname = ''.join([distname[0].upper()] + distname[1:])
    return (distname, _version or version, _name or name)


def _dist_try_harder(host):
    if host.path.exists('/var/adm/inst-log/info'):
        # SuSE Linux stores distribution information in that file
        distname = 'SuSE'
        for line in host.open('/var/adm/inst-log/info'):
            line = line.split()
            if len(line) != 2:
                continue
            tag, value = line.split()
            if tag == 'MIN_DIST_VERSION':
                version = value.strip()
            elif tag == 'DIST_IDENT':
                name = value.split('-')[2]
        return distname, version, name

    if host.path.exists('/etc/.installed'):
        # Caldera OpenLinux has some infos in that file
        # (thanks to Colin Kong)
        for line in open('/etc/.installed'):
            pkg = line.split('-')
            if len(pkg) >= 2 and pkg[0] == 'OpenLinux':
                # XXX does Caldera support non Intel platforms ? If yes,
                #     where can we find the needed name ?
                return 'OpenLinux', pkg[1], ''

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
    version, name = '', ''

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
    return '', version, name


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

    return LinuxHost(root)
