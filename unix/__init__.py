# -*- coding: utf-8 -*-

import os
import sys
import re
import time
import socket
import select
import subprocess
import paramiko
import weakref
from six import iteritems
from contextlib import contextmanager

#
# Logs.
#
import logging
logger = logging.getLogger('unix')


#
# Constants
#
# Available controls with their defaults values.
CONTROLS = {'options_place': 'before',
            'locale': 'en_US.utf-8',
            'decode': 'utf-8'}

# Regular expression for matching IPv4 address.
IPV4 = re.compile('^[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}$')

# Regular expression for matching IPv6 address.
IPV6 = re.compile('^[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:'
                  '[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:'
                  '[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}$')

# Extra arguments for 'scp' command as integer argument name raise syntax error
# when there are passed directly but not in kwargs.
SCP_EXTRA_ARGS = {'force_protocol1': '1',
                  'force_protocol2': '2',
                  'force_localhost': '3',
                  'force_ipv4': '4',
                  'force_ipv6': '6'}

# Set some default value for SSH options of 'scp' command.
SCP_DEFAULT_OPTS = {'StrictHostKeyChecking': 'no',
                    'ConnectTimeout': '2'}

# /etc/passwd fields.
PASSWD_FIELDS = ('login', 'password', 'uid', 'gid', 'name', 'home', 'shell')
# /etc/group fields.
GROUP_FIELDS = ('name', 'password', 'gid', 'users')


#
# Utils functions.
#
def instances(host):
    return [elt.__name__ for elt in host.__class__.mro()]


def ishost(host, value):
    return True if value in instances(host) else False




#
# Exceptions.
#
class UnixError(Exception):
    pass


#
# Abstract class for managing a host.
#
class Host(object):
    """Class that implement commands that are commons to local or remote
    host."""
    def __init__(self):
        self.return_code = -1
        for control, value in iteritems(CONTROLS):
            setattr(self, '_%s' % control, value)


    @property
    def path(self):
        return _Path(weakref.ref(self)())


    @property
    def remote(self):
        return _Remote(weakref.ref(self)())


    @property
    def users(self):
        return _Users(weakref.ref(self)())


    @property
    def groups(self):
        return _Groups(weakref.ref(self)())


    @property
    def processes(self):
        return _Processes(weakref.ref(self)())


    @property
    def controls(self):
        return {control: getattr(self, '_%s' % control) for control in CONTROLS}


    def get_control(self, control):
        if control not in CONTROLS:
            raise UnixError("invalid control '%s'" % control)
        return getattr(self, '_%s' % control)


    def set_control(self, control, value):
        setattr(self, '_%s' % control, value)


    @contextmanager
    def set_controls(self, **controls):
        cur_controls = dict(self.controls)

        try:
            for control, value in iteritems(controls):
                self.set_control(control, value)
            yield None
        finally:
            for control, value in iteritems(cur_controls):
                self.set_control(control, value)


    def _format_command(self, command, args, options):
        command = ['LC_ALL=%s' % self._locale, command]
        interactive = options.pop('interactive', False)
        if self._options_place == 'after':
            command.extend([str(arg) for arg in args])

        for option, value in iteritems(options):
            option = ('-%s' % option
                      if len(option) == 1
                      else '--%s' % option.replace('_', '-'))
            if type(value) is bool:
                if not value:
                    continue
                command.append(option)
            elif type(value) in (list, tuple, set):
                command.extend('%s %s' % (option, val) for val in value)
            else:
                command.append('%s %s' % (option, value))

        if self._options_place == 'before':
            command.extend(args)
        logger.debug('[execute] %s' % ' '.join(map(str, command)))
        return command, interactive


    def execute(self):
        raise NotImplementedError("don't use 'Host' class directly, "
                                  "use 'Local' or 'Remote' class instead.")


    @property
    def type(self):
        """Property that return the type of the operating system by executing
        ``uname -s`` command."""
        return self.execute('uname', s=True)[1].splitlines()[0].lower()


    @property
    def arch(self):
        """Property that return the architecture of the operating system by
        executing ``uname -m`` command."""
        return self.execute('uname', m=True)[1].splitlines()[0]


    @property
    def hostname(self):
        return self.execute('hostname')[1].splitlines()[0]


    def listdir(self, path):
        """List files in a directory.

        .. note::
            As the exception raised is different when using local function
            ``os.listdir(path)`` or remote function ``sftp.listdir(path)``, this
            method use ``ls`` command for listing directory and raise the
            **OSError** exception if **path** not exists or if there is another
            unexpected error.
        """
        if not self.path.exists(path):
            raise OSError("'%s' not exists" % path)
        if not self.path.isdir(path):
            raise OSError("'%s' is not a directory" % path)

        status, stdout, stderr = self.execute('ls', path)
        if not status:
            raise OSError(stderr)

        return stdout.splitlines()


    def touch(self, *paths, **options):
        return self.execute('touch', *paths, **options)


    def mkdir(self, *paths, **options):
        """Create a directory. *args and **options contains options that can be
        passed to the command. **options can contain an additionnal key
        *interactive* that will be pass to ``execute`` function."""
        return self.execute('mkdir', *paths, **options)


    def copy(self, *paths, **options):
        """Copy **src** file or directory to **dst**. *args and **options
        contains options that can be passed to the command. **options can
        contain an additionnal key *interactive* that will be pass to
        ``execute`` function."""
        return self.execute('cp', *paths, **options)


    def move(self, *paths, **options):
        return self.execute('mv', *paths, **options)


    def remove(self, *paths, **options):
        return self.execute('rm', *paths, **options)


    def chmod(self, permissions, *paths, **options):
        return self.execute('chmod', permissions, *paths, **options)


    def chown(self, owner, *paths, **options):
        return self.execute('chown', owner, *paths, **options)


    def chgrp(self, group, *paths, **options):
        return self.execute('chgrp', group, *path, **options)


    def which(self, command, **options):
        return self.execute('which', command, **options)[1].splitlines()[0]


#
# Class for managing localhost (subprocess).
#
class Local(Host):
    """Implementing specifics functions of localhost."""
    def __init__(self):
        Host.__init__(self)

    @property
    def username(self):
        return self.users.username(os.getuid())


    def execute(self, command, *args, **options):
        """Function that execute a command using english utf8 locale. The output
        is a list of three elements: a boolean representing the status of the
        command (True if return code equal to 0), the standard output (stdout)
        and the error output (stderr). If **interactive**, the command is
        executed interactively (printing output in real time and waiting for
        inputs) and stdout and stderr are empty. The return code of the last
        command is put in *return_code* attribut."""
        command, interactive = self._format_command(command, args, options)

        if interactive:
            try:
                self.return_code = subprocess.call(' '.join(command),
                                                   shell=True,
                                                   stderr=subprocess.STDOUT)
                return [True if self.return_code == 0 else False, '', '']
            except subprocess.CalledProcessError as err:
                return [False, '', err]
        else:
            try:
                obj = subprocess.Popen(' '.join(map(str, command)),
                                       shell=True,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
                stdout, stderr = obj.communicate()
                self.return_code = obj.returncode
                return [True if self.return_code == 0 else False,
                        stdout.decode(self._decode) if self._decode else stdout,
                        stderr.decode(self._decode) if self._decode else stderr]
            except OSError as err:
                return [False, '', err]


    def open(self, filepath, mode='r'):
        return open(filepath, mode)


#
# Context Manager for connecting to a remote host.
#
class connect(object):
    def __init__(self, host, **kwargs):
        self.hostname = host
        self.options = kwargs


    def __enter__(self):
        self._host = Remote()
        self._host.connect(self.hostname, **self.options)
        return self._host


    def __exit__(self, type, value, traceback):
        self._host.disconnect()
        del self._host


#
# Class for managing a remote host with SSH (paramiko).
#
class Remote(Host):
    def __init__(self):
        Host.__init__(self)
        self._connected = False
        self.ipv4 = None
        self.ipv6 = None
        self.fqdn = None


    def __ipv4(self):
        try:
            return socket.getaddrinfo(self.fqdn, 22, 2, 1, 6)[0][4][0]
        except socket.gaierror:
            return ''


    def __ipv6(self):
        try:
            return socket.getaddrinfo(self.fqdn, 22, 10, 1, 6)[0][4][0]
        except socket.gaierror:
            return ''


    def __fqdn(self):
        try:
            if self.ipv4:
                return socket.gethostbyaddr(self.ipv4)[0]
            elif self.ipv6:
                return socket.gethostbyadd(self.ipv6)[0]
            else:
                return ''
        except socket.herror:
            return ''


    def connect(self, host, **kwargs):
        self.username = kwargs.get('username', 'root')
        self.password = kwargs.get('password', '')
        self.forward_agent = kwargs.get('forwardagent', True)
        timeout = kwargs.get('timeout', 10)
        use_ipv6 = kwargs.get('ipv6', False)

        if IPV4.match(host):
            self.ipv4 = host
            self.fqdn = self.__fqdn()
            self.ipv6 = self.__ipv6()
        elif IPV6.match(host):
            self.ipv6 = host
            self.ipv4 = self.__ipv4()
            self.fqdn = self.__fqdn()
        else:
            self.fqdn = host
            self.ipv4 = self.__ipv4()
            self.ipv6 = self.__ipv6()
            self.fqdn = self.__fqdn()

        if not self.ipv4 and not self.ipv6:
            raise UnixError("unable to get an IPv4 or an IPv6 addresse.")

        self.ip = self.ipv6 if self.ipv6 and use_ipv6 else self.ipv4
        self._ssh = paramiko.SSHClient()
        try:
            self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            params = {'username': self.username, 'timeout': timeout}
            if self.password:
                params.update({'password': self.password,
                               'allow_agent': kwargs.get('allow_agent', False),
                               'look_for_keys': kwargs.get('look_for_keys',
                                                           False)})
            self._ssh.connect(self.ip, **params)
        except Exception as err:
            raise UnixError(err)
        self._connected = True
        self.sftp = None
        self.localhost = Local()

        # Optimizations for file transfert
        # (see https://github.com/paramiko/paramiko/issues/175)
        # From 6Mb/s to 12Mb/s => still very slow (scp = 40Mb/s)!
        self._ssh.get_transport().window_size = 2147483647
        self._ssh.get_transport().packetizer.REKEY_BYTES = pow(2, 40)
        self._ssh.get_transport().packetizer.REKEY_PACKETS = pow(2, 40)


    def disconnect(self):
        self._ssh.close()


    def execute(self, command, *args, **options):
        if not hasattr(self, '_ssh') or not self._ssh._transport:
            raise UnixError('you must be connected to a host before '
                            'executing any commands')

        command, interactive = self._format_command(command, args, options)

        chan = self._ssh.get_transport().open_session()
        forward = None
        if self.forward_agent:
            forward = paramiko.agent.AgentRequestHandler(chan)

        if interactive:
            chan.settimeout(0.0)
            chan.exec_command(' '.join(command))
            while True:
                rlist = select.select([chan, sys.stdin], [], [])[0]
                if chan in rlist:
                    try:
                        stdout = chan.recv(1024)
                        if len(stdout) == 0:
                            break
                        sys.stdout.write(stdout)
                        sys.stdout.flush()
                    except socket.timeout:
                        pass
                if sys.stdin in rlist:
                    stdin = ''
                    while True:
                        char = sys.stdin.read(1)
                        stdin += char
                        if len(char) == 0 or char == '\n':
                            break
                    chan.send(stdin)
                # If no wait, the process loop as he can, reading the
                # channel! Waiting 0.1 seconds avoids using a processor at
                # 100% for nothing.
                time.sleep(0.1)

            self.return_code = chan.recv_exit_status()
            stderr = chan.makefile_stderr('rb', -1).read()
            if stderr:
                print(stderr)
            return [True if self.return_code == 0 else False, '', '']
        else:
            chan.exec_command(' '.join(command))
            self.return_code = chan.recv_exit_status()
            stdout = chan.makefile('rb', -1).read()
            stderr = chan.makefile_stderr('rb', -1).read()
            return [True if self.return_code == 0 else False,
                    stdout.decode(self._decode) if self._decode else stdout,
                    stderr.decode(self._decode) if self._decode else stderr]

        if forward:
            forward.close()
        chan.close()


    def open(self, filepath, mode='r'):
        sftp = paramiko.SFTPClient.from_transport(self._ssh.get_transport())
        return sftp.open(filepath, mode)

#
# Class for managing filesystem paths.
#
class _Path(object):
    def __init__(self, host):
        self._host = host


    def exists(self, path):
        """Return the status of ``test -e`` command."""
        return self._host.execute('test', path, e=True)[0]


    def isfile(self, path):
        """Return the status of ``test -f`` command."""
        return self._host.execute('test', path, f=True)[0]


    def isdir(self, path):
        """Return the status of ``test -d`` command."""
        return self._host.execute('test', path, d=True)[0]


    def islink(self, path):
        """Return the status of ``test -L`` command."""
        return self._host.execute('test', path, L=True)[0]


    def type(self, path):
        """Use ``file`` command for retrieving the type of the **path**."""
        with self._host.set_controls(decode='utf-8'):
            status, stdout = self._host.execute('file', path)[:-1]
        if not status:
            # For unexpected reasons, errors are in stdout!
            raise OSError(stdout)
        return stdout.split(':')[-1].strip()


    def size(self, filepath, **options):
        with self._host.set_controls(decode='utf-8'):
            options.update(s=True)
            status, stdout, stderr = self._host.execute('du', filepath, **options)
        if not status:
            raise OSError(stderr)
        return stdout.split('\t')[0]


#
# Class for managing remote file copy.
#
class _Remote(object):
    def __init__(self, host):
        self._host = host


    def _format_ssh_arg(self, user, host, filepath):
        return (('%s@' % user if (user and host) else '')
                + (host or '')
                + (('%s%s' % (':' if host else '', filepath))
                   if filepath
                   else ''))


    def scp(self, src_file, dst_file, **kwargs):
        # ssh_options (-o) can be passed many time so this must be a list.
        kwargs['o'] = kwargs.get('o', [])
        if type(kwargs['o']) not in (list, tuple):
            raise AttributeError("'o' argument of 'scp' function must be a list"
                                 " as there can be many SSH options passed to "
                                 "the command.")

        # Python don't like when argument name is an integer but passing them
        # with kwargs seems to work. So use extra arguments for interger options
        # of the scp command.
        for mapping, opt in iteritems(SCP_EXTRA_ARGS):
            if kwargs.pop(mapping, False):
                kwargs.setdefault(opt, True)

        # Change default value of some SSH options (like host key checking and
        # connect timeout).
        cur_opts = [opt.split('=')[0] for opt in kwargs['o']]
        kwargs['o'].extend('%s=%s' % (opt, default)
                           for opt, default in iteritems(SCP_DEFAULT_OPTS)
                           if opt not in cur_opts)

        # Format source and destination arguments.
        src = self._format_ssh_arg(kwargs.pop('src_user', ''),
                                   kwargs.pop('src_host', ''),
                                   src_file)
        dst = self._format_ssh_arg(kwargs.pop('dst_user', ''),
                                   kwargs.pop('dst_host', ''),
                                   dst_file)

        return self._host.execute('scp', src, dst, **kwargs)


    def rsync(self, src_file, dst_file, **kwargs):
        src = self._format_ssh_arg(kwargs.pop('src_user', ''),
                                   kwargs.pop('src_host', ''),
                                   src_file)
        dst = self._format_ssh_arg(kwargs.pop('dst_user', ''),
                                   kwargs.pop('dst_host', ''),
                                   dst_file)

        return self._host.execute('rsync', src, dst, **kwargs)


    def tar(self, src_file, dst_file, src_opts={}, dst_opts={}, **kwargs):
        src_ssh = '%s' % self._format_ssh_arg(kwargs.pop('src_user', ''),
                                              kwargs.pop('src_host', ''),
                                              '')
        dst_ssh = '%s' % self._format_ssh_arg(kwargs.pop('dst_user', ''),
                                              kwargs.pop('dst_host', ''),
                                              '')

        interactive = kwargs.pop('interactive', False)

        src_cmd = ['tar cf -']
        src_opts.update(kwargs)
        src_opts.setdefault('C', os.path.dirname(src_file))
        self._format_command(src_cmd, [os.path.basename(src_file)], src_opts)

        dst_cmd = ['tar xf -']
        dst_opts.update(kwargs)
        dst_opts.setdefault('C', dst_file)
        self._format_command(dst_cmd, [], dst_opts)

        cmd = ['ssh %s' % src_ssh if src_ssh else '']
        cmd.extend(src_cmd)
        cmd.append('|')
        cmd.append('ssh %s' % dst_ssh if dst_ssh else '')
        cmd.extend(dst_cmd)
        return self._host.execute(*cmd, interactive=interactive)


    def get(self, rmthost, rmtpath, localpath, **kwargs):
        if ishost(self._host, 'Remote') and rmthost == 'localhost':
            return Local().remote.put(rmtpath,
                                      self._host.ip,
                                      localpath,
                                      **kwargs)

        method = kwargs.pop('method', 'scp')
        rmtuser = kwargs.pop('rmtuser', 'root')

        return {
            'scp': lambda: self.scp(rmtpath,
                                    localpath,
                                    src_host=rmthost,
                                    src_user=rmtuser,
                                    **kwargs),
            'rsync': lambda: self.rsync(rmtpath,
                                        localpath,
                                        src_host=rmthost,
                                        src_user=rmtuser,
                                        **kwargs),
            'tar': lambda: self.tar(rmtpath,
                                    localpath,
                                    src_host=rmthost,
                                    src_user=rmtuser,
                                    **kwargs),
        }.get(method, lambda: [False, [], ["unknown copy method '%s'" % method]])()


    def put(self, localpath, rmthost, rmtpath, **kwargs):
        if ishost(self._host, 'Remote') and rmthost == 'localhost':
            return Local().remote.get(self.host.ip,
                                      localpath,
                                      rmtpath,
                                      **kwargs)

        method = kwargs.pop('method', 'scp')
        rmtuser = kwargs.pop('rmtuser', 'root')

        return {
            'scp': lambda: self.scp(localpath,
                                    rmtpath,
                                    dst_host=rmthost,
                                    dst_user=rmtuser,
                                    **kwargs),
            'rsync': lambda: self.rsync(localpath,
                                        rmtpath,
                                        dst_host=rmthost,
                                        dst_user=rmtuser,
                                        **kwargs),
            'tar': lambda: self.tar(localpath,
                                    rmtpath,
                                    dst_host=rmthost,
                                    dst_user=rmtuser,
                                    **kwargs),
        }.get(method, lambda: [False, '', "unknown method '%s'" % method])()


#
# Class for managing users.
#
class _Users(object):
    def __init__(self, host):
        self._host = host


    def details(self):
        status, stdout, stderr = self._host.execute('getent', 'passwd')
        if not status:
            raise UserError(stderr)
        return [dict(zip(PASSWD_FIELDS, user.split(':'))) for user in stdout]


    def list(self):
        return [user['login'] for user in self.details()]


    def uid(self, username):
        status, stdout, stderr = self._host.execute('id', u=username)
        if not status:
            raise UserError(stderr)
        return int(stdout[0])


    def username(self, uid):
        status, stdout, stderr = self._host.execute('getent', 'passwd', uid)
        if not status:
            raise UserError(stderr)
        return stdout[0].split(':')[0]


    def groups(self, username):
        status, stdout, stderr = self._host.execute('id', G=username)


    def detail(self, uid):
        status, stdout, stderr = self._host.execute('getent', 'passwd', uid)
        if not status:
            raise UserError(stderr)
        return dict(zip(PASSWD_FIELDS, stdout[0].split('')))


    def add(self, user, **kwargs):
        self._host.asroot('useradd')
        return self._host.execute('useradd', user, **kwargs)


    def delete(self, user, **kwargs):
        self._host.asroot('userdel')
        return self._host.execute('userdel', user, **kwargs)


    def update(self, user, **kwargs):
        self._host.asroot('usermod')
        return self._host.execute('usermod', user, **kwargs)


#
# Class for managing groups.
#
class _Groups(object):
    def __init__(self, host):
        self._host = host


    def list(self):
        status, stdout, stderr = self._host.execute('getent', 'group')
        if not status:
            raise UserError(stderr)
        groups = []
        for line in stdout:
            group = dict(zip(GROUP_FIELDS, line.split(':')))
            group['users'] = group['users'].split(',') if group['users'] else []
        return groups


    def gid(self, groupname):
        status, stdout, stderr = self._host.execute('id', g=username)
        if not status:
            raise UserError(stderr)
        return int(stdout[0])


    def groupname(self, gid):
        status, stdout, stderr = self._host.execute('getent', 'group', gid)
        if not status:
            raise UserError(stderr)
        return stdout[0].split(':')[0]


    def add(self, group, **kwargs):
        self._host.asroot('groupadd')
        return self._host.execute('groupadd', group, **kwargs)


    def delete(self, group):
        self._host.asroot('groupdel')
        return self._host.execute('groupdel', group)


    def update(self, group, **kwargs):
        self._host.asroot('groupmod')
        return self._host.execute('groupmod', group, **kwargs)


    def users(self, groupname):
        for group in self.list():
            if group['name'] == groupname:
                return group['users']


#
# Class for managing process.
#
class _Processes(object):
    def __init__(self, host):
        self._host = host


    def kill(self, pid, **options):
        return self._host.execute('kill', pid, **options)
