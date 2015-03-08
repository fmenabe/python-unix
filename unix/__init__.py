import os
import re
import sys
import time
import socket
import select
import subprocess
import paramiko
import weakref
from contextlib import contextmanager
from unix._processes import Processes
from unix._path import Path
from unix._remote import Remote
from unix._users import Users
from unix._groups import Groups

#
# Logs.
#
import logging
logger = logging.getLogger('unix')


#
# Utils functions.
#
def instances(host):
    return list(reversed([elt.__name__.replace('Host', '')
                          for elt in host.__class__.mro()[:-2]]))


def ishost(host, value):
    return True if value in instances(host) else False


def isvalid(host):
    if instances(host)[0] not in ('Local', 'Remote'):
        raise ValueError("this is not a 'Local' or a 'Remote' host")


#
# Constants
#
# Available controls with their defaults values.
_CONTROLS = {'options_place': 'before',
             'locale': 'en_US.utf-8',
             'decode': 'utf-8'}

# Errors.
_HOST_CLASS_ERR = ("don't use 'Host' class directly, use 'Local' or "
                   "'Remote' class instead.")
_NOT_CONNECTED_ERR = 'you are not connected'
_IP_ERR = 'unable to get an IPv4 or an IPv6 addresse.'

# Regular expression for matching IPv4 address.
_IPV4 = re.compile(r'^[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}$')

# Regular expression for matching IPv6 address.
_IPV6 = re.compile(r'^[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:'
                    '[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:'
                    '[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}$')

# Extra arguments for 'scp' command as integer argument name raise syntax error
# when there are passed directly but not in kwargs.
_SCP_EXTRA_ARGS = {'force_protocol1': '1',
                   'force_protocol2': '2',
                   'force_localhost': '3',
                   'force_ipv4': '4',
                   'force_ipv6': '6'}

# Set some default value for SSH options of 'scp' command.
_SCP_DEFAULT_OPTS = {'StrictHostKeyChecking': 'no', 'ConnectTimeout': '2'}

# /etc/passwd fields.
_PASSWD_FIELDS = ('login', 'password', 'uid', 'gid', 'name', 'home', 'shell')
# /etc/group fields.
_GROUP_FIELDS = ('name', 'password', 'gid', 'users')


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
        for control, value in _CONTROLS.items():
            setattr(self, '_%s' % control, value)


    @property
    def path(self):
        return Path(weakref.ref(self)())


    @property
    def remote(self):
        return Remote(weakref.ref(self)())


    @property
    def users(self):
        return Users(weakref.ref(self)())


    @property
    def groups(self):
        return Groups(weakref.ref(self)())


    @property
    def processes(self):
        return Processes(weakref.ref(self)())


    @property
    def controls(self):
        return {control: getattr(self, '_%s' % control) for control in _CONTROLS}


    def get_control(self, control):
        if control not in _CONTROLS:
            raise UnixError("invalid control '%s'" % control)
        return getattr(self, '_%s' % control)


    def set_control(self, control, value):
        setattr(self, '_%s' % control, value)


    @contextmanager
    def set_controls(self, **controls):
        cur_controls = dict(self.controls)

        try:
            for control, value in controls.items():
                self.set_control(control, value)
            yield None
        finally:
            for control, value in cur_controls.items():
                self.set_control(control, value)


    def _format_command(self, command, args, options):
        command = ['LC_ALL=%s' % self._locale, command]
        interactive = options.pop('interactive', False)
        if self._options_place == 'after':
            command.extend([str(arg) for arg in args])

        for option, value in options.items():
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
        raise NotImplementedError(_HOST_CLASS_ERR)


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
        try:
            return self.execute('which', command, **options)[1].splitlines()[0]
        except IndexError:
            raise UnixError("which: unable to find command '%s'" % command)


    def mount(self, device, mount_point, **options):
        return self.execute('mount', device, mount_point, **options)


    def umount(self, mount_point, **options):
        return self.execute('umount', mount_point, **options)


#
# Class for managing localhost (subprocess).
#
class Local(Host):
    """Implementing specifics functions of localhost."""
    def __init__(self):
        Host.__init__(self)


    @staticmethod
    def clone(host):
        new_host = Local()
        new_host.__dict__.update(return_code=host.return_code)
        new_host.__dict__.update(host.controls)
        return new_host


    @property
    def username(self):
        return self.users.username(os.getuid())


    def is_connected(self):
        pass


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
                return [True if self.return_code == 0 else False, u'', u'']
            except subprocess.CalledProcessError as err:
                return [False, u'', err]
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
                return [False, u'', err]


    def open(self, filepath, mode='r'):
        return open(filepath, mode)


    def tail(self, filepath, delta=1):
        prev_size = os.stat(filepath).st_size
        while 1:
            cur_size = os.stat(filepath).st_size
            # File has been rotate.
            if cur_size < prev_size:
                with self.open(filepath) as fhandler:
                    for line in fhandler.read().splitlines():
                        yield line
            else:
                with self.open(filepath) as fhandler:
                    fhandler.seek(prev_size, 0)
                    for line in fhandler.read().splitlines():
                        yield line
            prev_size = cur_size
            time.sleep(delta)


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
        self.forward_agent = True
        self.ipv4 = None
        self.ipv6 = None
        self.fqdn = None
        self.username = None
        self._conn = None


    @staticmethod
    def clone(host):
        new_host = Remote()
        new_host.__dict__.update(return_code=host.return_code)
        new_host.__dict__.update(host.controls)
        attrs = ('ipv4', 'ipv6', 'fqdn', 'username')
        new_host.__dict__.update({attr: getattr(host, attr) for attr in attrs})
        if hasattr(host, '_conn'):
            new_host.__dict__.update(_conn=host._conn)
        return new_host


    def __ipv4(self):
        try:
            return socket.getaddrinfo(self.fqdn, 22, 2, 1, 6)[0][4][0]
        except socket.gaierror:
            return None


    def __ipv6(self):
        try:
            return socket.getaddrinfo(self.fqdn, 22, 10, 1, 6)[0][4][0]
        except socket.gaierror:
            return None


    def __fqdn(self):
        try:
            if self.ipv4:
                return socket.gethostbyaddr(self.ipv4)[0]
            elif self.ipv6:
                return socket.gethostbyadd(self.ipv6)[0]
            else:
                return None
        except socket.herror:
            return None


    def connect(self, host, **kwargs):
        self.forward_agent = kwargs.pop('forward_agent', True)
        self.username = kwargs.pop('username', 'root')

        if _IPV4.match(host):
            self.ipv4 = host
            self.fqdn = self.__fqdn()
            self.ipv6 = self.__ipv6()
        elif _IPV6.match(host):
            self.ipv6 = host
            self.ipv4 = self.__ipv4()
            self.fqdn = self.__fqdn()
        else:
            self.fqdn = host
            self.ipv4 = self.__ipv4()
            self.ipv6 = self.__ipv6()
            self.fqdn = self.__fqdn()

        if not self.ipv4 and not self.ipv6:
            raise UnixError(_IP_ERR)
        self.ip = (self.ipv6 if self.ipv6 and kwargs.pop('ipv6', False)
                             else self.ipv4)

        params = {'username': self.username}
        for param, value in kwargs.items():
            params[param] = value
        self._conn = paramiko.SSHClient()
        try:
            self._conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._conn.connect(self.ip, **params)
        except Exception as err:
            raise UnixError(err)

        # Optimizations for file transfert
        # (see https://github.com/paramiko/paramiko/issues/175)
        # From 6Mb/s to 12Mb/s => still very slow (scp = 40Mb/s)!
        self._conn.get_transport().window_size = 2147483647
        self._conn.get_transport().packetizer.REKEY_BYTES = pow(2, 40)
        self._conn.get_transport().packetizer.REKEY_PACKETS = pow(2, 40)


    def disconnect(self):
        self._conn.close()


    def is_connected(self):
        if self._conn is None or not self._conn.get_transport():
            raise UnixError(_NOT_CONNECTED_ERR)


    def execute(self, command, *args, **options):
        self.is_connected()

        command, interactive = self._format_command(command, args, options)

        chan = self._conn.get_transport().open_session()
        forward = (paramiko.agent.AgentRequestHandler(chan)
                   if self.forward_agent
                   else None)

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
                        sys.stdout.write(stdout.decode())
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
                print(stderr.decode())
            return [True if self.return_code == 0 else False, u'', u'']
        else:
            chan.exec_command(' '.join(map(str, command)))
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
        self.is_connected()
        sftp = paramiko.SFTPClient.from_transport(self._conn.get_transport())
        return sftp.open(filepath, mode)


    def tail(self, filepath, delta=1):
        sftp = paramiko.SFTPClient.from_transport(self._conn.get_transport())

        prev_size = sftp.stat(filepath).st_size
        while 1:
            cur_size = sftp.stat(filepath).st_size
            # File has been rotate.
            if cur_size < prev_size:
                with self.open(filepath) as fhandler:
                    for line in fhandler.read().splitlines():
                        yield line.decode()
            else:
                with self.open(filepath) as fhandler:
                    fhandler.seek(prev_size, 0)
                    for line in fhandler.read().splitlines():
                        yield line.decode()
            prev_size = cur_size
            time.sleep(delta)

