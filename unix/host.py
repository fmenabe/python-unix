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
import unix

# Regular expression for matching IPv4 address.
IPV4 = re.compile('^[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}$')

# Regular expression for matching IPv6 address.
IPV6 = re.compile(
    '^[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:'
    '[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}$')

# Locale for all commands in order to have all outputs in english.
LOCALE = 'LC_ALL=en_US.utf-8'

# Extra arguments for 'scp' command as integer argument name raise syntax error
# when there are passed directly but not in kwargs.
SCP_EXTRA_ARGS = {
    'force_protocol1': '1',
    'force_protocol2': '2',
    'force_localhost': '3',
    'force_ipv4': '4',
    'force_ipv6': '6'
}

# Set some default value for SSH options of 'scp' command.
SCP_DEFAULT_OPTS = {
    'StrictHostKeyChecking': 'no',
    'ConnectTimeout': '2'
}



class ConnectError(Exception):
    """Exception raised by a **Remote** object when it is not possible to
    establish a connection."""
    pass





class Host(object):
    """Class that implement commands that are commons to local or remote
    host."""
    def __init__(self):
        self.path = _Path(weakref.ref(self)())
        self.remote = _Remote(weakref.ref(self)())


    def _format_command(self, command, args, options):
        interactive = options.pop('interactive', False)
        for option, value in options.iteritems():
            option = '-%s' % option if len(option) == 1 else '--%s' % option
            if type(value) is bool:
                command.append(option)
            elif type(value) in (list, tuple, set):
                command.extend('%s %s' % (option, val) for val in value)
            else:
                command.append('%s %s' % (option, value))
        command.extend(args)
        return interactive


    def execute(self):
        raise NotImplementedError("don't use 'Host' class directly, "
            "use 'Local' or 'Remote' class instead.")


    @property
    def type(self):
        """Property that return the type of the operating system by executing
        ``uname -s`` command."""
        return self.execute('uname -s')[1][0].lower()


    @property
    def arch(self):
        """Property that return the architecture of the operating system by
        executing ``uname -m`` command."""
        return self.execute('uname -m')[1][0]


    @property
    def hostname(self):
        return self.execute('hostname')[1][0]


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

        status, stdout, stderr = self.execute('ls %s' % path)
        if not status:
            raise OSError(stderr)

        return stdout


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
        return self.execute('which', command, **options)[1][0]


class Local(Host):
    """Implementing specifics functions of localhost."""
    def __init__(self):
        Host.__init__(self)


    def execute(self, command, *args, **options):
        """Function that execute a command using english utf8 locale. The output
        is a list of three elements: a boolean representing the status of the
        command (True if return code equal to 0), the standard output (stdout)
        and the error output (stderr). If **interactive**, the command is
        executed interactively (printing output in real time and waiting for
        inputs) and stdout and stderr are empty. The return code of the last
        command is put in *return_code* attribut."""
        command = [LOCALE, command]
        interactive = self._format_command(command, args, options)

        self.return_code = -1
        if interactive:
            try:
                self.return_code = subprocess.call(
                    ' '.join(command), shell=True, stderr=subprocess.STDOUT)
                return [True if self.return_code == 0 else False, '', '']
            except subprocess.CalledProcessError as err:
                return [False, '', err]
        else:
            try:
                obj = subprocess.Popen(' '.join(command),
                    shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = obj.communicate()
                self.return_code = obj.returncode
                return [True if self.return_code == 0 else False,
                    stdout.split('\n')[:-1], stderr.split('\n')[:-1]]
            except OSError as err:
                return [False, '', err]


class Remote(Host):
    def __init__(self):
        Host.__init__(self)
        self._connected = False


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
            return (socket.gethostbyaddr(self.ipv4)[0]
                if self.ipv4
                else (socket.gethostbyadd(self.ipv6)[0] if self.ipv6 else ''))
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
            self.fqdn = self.__fqdn()
            self.ipv4 = self.__ipv4()
        else:
            self.fqdn = host
            self.ipv4 = self.__ipv4()
            self.ipv6 = self.__ipv6()
            self.fqdn = self.__fqdn()

        if not self.ipv4 and not self.ipv6:
            raise ConnectError("unable to get an IPv4 or an IPv6 addresse.")

        self.ip = self.ipv6 if self.ipv6 and use_ipv6 else self.ipv4
        self._ssh = paramiko.SSHClient()
        try:
            self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            params = {'username': self.username, 'timeout': timeout}
            if self.password:
                params.update({
                    'password': self.password,
                    'allow_agent': kwargs.get('allow_agent', False),
                    'look_for_keys': kwargs.get('look_for_keys', False)})
            self._ssh.connect(self.ip, **params)
        except Exception as err:
            raise ConnectError(err)
        self._connected = True

        # Optimizations for file transfert
        # (see https://github.com/paramiko/paramiko/issues/175)
        # From 6Mb/s to 12Mb/s => still very slow (scp = 40Mb/s)!
        self._ssh.get_transport().window_size = 2147483647
        self._ssh.get_transport().packetizer.REKEY_BYTES = pow(2, 40)
        self._ssh.get_transport().packetizer.REKEY_PACKETS = pow(2, 40)


    def disconnect(self):
        self._ssh.close()


    def execute(self, command, *args, **options):
        if not self._connected:
            raise ConnectError(
                'you must be connected to a host before executing commands')

        command = [LOCALE, command]
        interactive = self._format_command(command, args, options)

        chan = self._ssh.get_transport().open_session()
        forward = None
        if self.forward_agent:
            forward = paramiko.agent.AgentRequestHandler(chan)

        self.return_code = -1
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
                # If no waiting, the process loop as he can, reading the
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
            return [True if self.return_code == 0 else False,
                chan.makefile('rb', -1).read().split('\n')[:-1],
                chan.makefile_stderr('rb', -1).read().split('\n')[:-1]]

        if forward:
            forward.close()
        chan.close()


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
        status, stdout = self._host.execute('file', path)[:-1]
        if not status:
            # For unexpected reasons, errors are in stdout!
            raise OSError(stdout)
        return stdout[0].split(':')[-1].strip()


    def size(self, filepath, **options):
        return self._host.execute('du', filepath, **options)



class _Remote(object):
    def __init__(self, host):
        self._host = host


    def _format_scp_arg(self, user, host, filepath):
        print user, host, filepath
        return (('%s@' % user if (user and host) else '')
            + ('%s:' % host if host else '')
            + (filepath))


    def scp(self, src_file, dst_file, **kwargs):
        # ssh_options (-o) can be passed many time so this must be a list.
        kwargs['o'] = kwargs.get('o', [])
        if type(kwargs['o']) not in (list, tuple):
            raise AttributeError("'o' argument of 'scp' function must be a list"
                " as there can be many SSH options passed to the command.")

        # Python don't like when argument name is an integer but passing them
        # with kwargs seems to work. So use extra argument for interger options
        # of scp command.
        for mapping, opt in SCP_EXTRA_ARGS.items():
            if kwargs.pop(mapping, False):
                kwargs.setdefault(opt, True)

        # Change default value of some SSH options (like host key checking and
        # connect timeout).
        cur_opts = [opt.split('=')[0] for opt in kwargs['o']]
        kwargs['o'].extend('%s=%s' % (opt, default)
            for opt, default in SCP_DEFAULT_OPTS.items() if opt not in cur_opts)

        # Format source and destination arguments.
        src = self._format_scp_arg(
            kwargs.pop('src_user', ''), kwargs.pop('src_host', ''), src_file)
        dst = self._format_scp_arg(
            kwargs.pop('dst_user', ''), kwargs.pop('dst_host', ''), dst_file)

        return self._host.execute('scp', src, dst, **kwargs)


    def get(self, rmthost, rmtpath, localpath, **kwargs):
        if unix.ishost(self._host, 'Remote') and rmthost == 'localhost':
            return Local().remote.put(rmtpath, self._host.ip, localpath, **kwargs)

        method = kwargs.pop('method', 'scp')
        rmtuser = kwargs.pop('rmtuser', 'root')

        return {
            'scp': lambda: self.scp(
                rmtpath, localpath, src_host=rmthost, src_user=rmtuser, **kwargs),
        }.get(method, lambda: [False, [], ["unknown copy method '%s'" % method]])()


    def put(self, localpath, rmthost, rmtpath, **kwargs):
        if unix.ishost(self._host, 'Remote') and rmthost == 'localhost':
            return Local().remote.get(self.host.ip, localpath, rmtpath, **kwargs)

        method = kwargs.pop('method', 'scp')
        rmtuser = kwargs.pop('rmtuser', 'root')

        return {
            'scp': lambda: self.scp(
                localpath, rmtpath, dst_host=rmthost, dst_user=rmtuser, **kwargs),
        }.get(method, lambda: [False, '', "unknown method '%s'" % method])()
