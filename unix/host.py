# -*- coding: utf-8 -*-

"""This module provide classes for managing Unix-like hosts. It is possible to
manage both localhost and remotes hosts in the same way. Execution of commands,
reading and writing files, copying files to a remote host have a different
implementations according to we are on a local or a remote host. **Local** and
**Remote** classes implemented theses distincts functions. Theses two classes
inherit from the **Host** class that implement some classic Unix commands (
*mkdir*, *rm*, ...).

Each classes **Local** and **Remote** contains a wrapper function *execute* for
executing commands. All commands are launched by specifying an **utf8** english
locale for having all outputs in english. By default, commands are run non
interactively, meaning the result is available only when the command has
finished his execution. When a command ask for inputs, the function hangs
indefinitely until the process is killed manually on the host. This is why the
function *execute* can take a boolean parameter for launching command
interactively, meaning output is in real time and it is possible to interact
with the command. In all case, the function return a list of three parameters:
    - the status (*True* if return code is equal to 0 else *False*)
    - the standard output (stdout)
    - the error output (stderr)
.. note:: When command is launched interactively, *stdout* and *stderr*
 are empty.
"""

import os
import sys
import socket
import subprocess
import pexpect
import paramiko
import time
import re
import select

# Regular expression for matching IPv4.
IPV4_REGEXP = re.compile('^[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}$')

# Regular expression for matching IPv6.
IPV6_REGEXP = re.compile(
    '^[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:'
    '[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}$'
)

# Locale for all commands in order to have all outputs in english.
LOCALE = 'LC_ALL=en_US.utf-8'


class ConnectError(Exception):
    """Exception raised by a **Remote** object when there is connection error."""
    pass


class Host(object):
    """Class that implement commands. It use specifics functions defining in
    **Local** and **Remote** classes."""
    @property
    def os_type(self):
        """Property that return the type of the operating system (*Linux*,
        *SunOS*, *OpenBSD*, ...)"""
        return self.execute('uname -s')[1].lower()


    @property
    def os_arch(self):
        """Property that return the architecture of the operating system."""
        return self.execute('uname -a')[1]


    def exists(self, path):
        """Return *True* if **path** exists."""
        return self.execute("test -e %s" % path)[0]


    def isfile(self, path):
        """Return *True* if **path** is a file."""
        return self.execute("test -f %s" % path)[0]


    def isdir(self, path):
        """Return *True* if **path** is a directory."""
        return self.execute("test -d %s" % path)[0]


    def islink(self, path):
        """Return *True* if **path** is symbolic link."""
        return self.execute("test -L %s" % path)[0]


    def filetype(self, path):
        """Return the type of **path**."""
        status, stdout = self.execute("file %s" % path)[:-1]
        if not status:
            # For unexpected reasons, errors are in stdout!
            raise OSError(stdout)
        return stdout.split(':')[-1].strip()


    def listdir(self, path):
        """Return a list containing the names of the entries in the directory
        **path**.

        .. note::
            As the exception raised is different when using local function
            *os.listdir(path)* or remote function *sftp.listdir(path)*,
            this method use *ls* command for listing directory and raise the
            **OSError** exception when **path** not exists or if there is an
            unexpected error.
        """
        if not self.isdir(path):
            raise OSError('%s is not a directory' % path)
        status, stdout, stderr = self.execute('ls %s' % path)
        if not status:
            raise OSError(stderr)
        return stdout.split('\n')


    def mkdir(self, path, parents=True):
        """Create directory **path**. The parameter **parent** indicate to
        create all intermediary directories."""
        command = ['mkdir', path]
        if parents:
            command.insert(1, '-p')
        return self.execute(' '.join(command))


    def cp(self, src, dst, recursive=False, preserve=False):
        """Copy **src** to **dst**. The parameter **recurive** indicate to
        operate on files and directories recursively and **preserve** parameter
        to keep originals permissions."""
        if not recursive and self.isdir(src):
            return (False, '', "'%s' is a directory" % src)

        command = ['cp', src, dst]
        if recursive:
            command.insert(1, '-R')
        if preserve:
            command.insert(1, '-p')
        return self.execute(' '.join(command))


    def mv(self, path, newpath):
        """Move **path** to **newpath**."""
        return self.execute('mv %s %s' % (path, newpath))


    def rm(self, path, recursive=False, safe=True):
        """Remove **path**. The parameter **recursive** indicate to operate on
        files and directories recursively and **safe** parameter prevent for
        removing a directory which is not empty."""
        command = [path]
        if not recursive:
            command.insert(0, 'rm')
        else:
            if not self.isdir(path):
                return [False, '', "'%s' is not a directory"]
            if safe:
                command.insert(0, 'rmdir')
            else:
                command.insert(0, 'rm')
                command.insert(1, '-r')
        return self.execute(' '.join(command))


    def chmod(self, path, rights, recursive=False):
        """Update permissions of **path**. **rights** take all formats that the
        *chmod* command take (ie: *[ugoa][[+-=][rwxS]*, *NNNN*) and **recurive**
        parameter indicate to operate on files and directories recursively."""
        command = ['chown', user, path]
        if recursive:
            command.insert(1, '-R')
        return self.execute(' '.join(command))


    def chown(self, path, user, recursive=False):
        """Update owner of **path**. **user** parameter take all formats that
        the *chown* command take (ie: *user*, *user:group* or *uid*) and
        **recurive** parameter indicate to operate on files and directories
        recursively."""
        command = ['chown', user, path]
        if recursive:
            command.insert(1, '-R')
        return self.execute(' '.join(command))


    def chgrp(self, path, group, recursive=False):
        """Update group of **path**. **group** take all formats that the *chgrp*
        command take (ie: *group*, *gid*) and **recurive** parameter indicate to
        operate on files and directories recursively."""
        command = ['chgrp', user, path]
        if recursive:
            command.insert(1, '-R')
        return self.execute(' '.join(command))


    def readlines(self, filepath):
        """Return the list of lines of **filepath**."""
        return self.read(filepath).split('\n')


    def replace(self, filepath, src_pattern, dst_pattern):
        """Replace in **filepath** the occurences of **src_pattern** by
        **dst_pattern**."""
        if not self.isfile(filepath):
            raise OSError("'%s' is not a file") % filepath

        return self.execute(
            "sed -i s/%s/%s/g %s"  % (src_pattern, dst_pattern, filepath)
        )


    def size(self, path):
        """Return the size in Kb of **path**."""
        if not self.exists(path):
            raise OSError("'%s' not exists" % path)

        return int(
            self.execute('du -ks %s' % path)[1].split()[0]
        )


    def rmt_copy(self, localpath, hostname, rmtpath, method='scp', user='root'):
        """Copy **localpath** from the current host (which can be localhost or
        a connection to a remote host) to **rmtpath** on an other host. **hostname**
        must contain SSH keys of the current host for user **user**. The **method**
        parameter indicate which method (*scp*, *tar*, *sftp*) to use. If method is
        not defined, the **AttributeError** exception is raised."""
        function = getattr(self, '_%s_copy' % method)
        return function(localpath, hostname, rmtpath, username)


    def _scp_copy(self, localpath, hostname, rmtpath, user):
        """Copy **localpath** from the current host to
        **user**\ @\ **hostname**\ :\ **rmt_path** using scp command."""
        return self.execute(' '.join((
            'scp -rp',
            '-o StrictHostKeyChecking=no',
            localpath,
            '%s@%s:%s' % (username, hostname, rmtpath)
        )))


    def _tar_copy(self, localpath, hostname, rmtpath, user):
        """Copy **localpath** from the current host to
        **user**\ @\ **hostname**\ :\ **rmt_path** using command::
            tar czf -C localpath | ssh user@hostname tar xzf - -C rmtpath
        """
        return self.execute(' '.join((
            'tar czf - -C',
            os.path.abspath(localpath),
            '|',
            'ssh', '-o StrictHostKeyChecking=no',
            '%s@%s' % (username, hostname),
            'tar xzf - -C', rmtpath
        )))


class Local(Host):
    """Implementing specifics functions for localhost."""

    def __init__(self):
        """Initialize object."""
        Host.__init__(self)


    @property
    def hostname(self):
        """Property that return the hostname."""
        return socket.gethostname()


    def execute(self, command, interactive=False):
        """Function that execute **command** using english utf8 locale. The output
        is a list of three elements ([*status*, *stdout*, *stderr*]). *status* is
        *True* only if return code is equal to 0. When **interactive**, output is
        in real time and interactions (ie: inputs) are possible. In this case
        *stdout* and *stderr* are empty. Return code is put in the *return_code*
        attribute of the object."""
        command = '%s %s' % (LOCALE, command)
        if interactive:
            try:
                self.return_code = subprocess.call(
                    command,
                    shell=True,
                    stderr=subprocess.STDOUT
                )
                return [
                    True if self.return_code == 0 else False,
                    '',
                    ''
                ]
            except subprocess.CalledProcessError as proc_err:
                return [False, '', '']
        else:
            try:
                obj = subprocess.Popen(
                    command,
                    shell=True,
                    stdout = subprocess.PIPE,
                    stderr = subprocess.PIPE
                )
                stdout, stderr = obj.communicate()
                self.return_code = obj.returncode
                return [
                    True if self.return_code == 0 else False,
                    '\n'.join(stdout.split('\n')[:-1]),
                    '\n'.join(stderr.split('\n')[:-1])
                ]
            except OSError as os_err:
                return [False, stdout, stderr]


    def expect(self, command, *patterns):
        """Use *expect* from executing **command**. **\*patterns** is a list
        of pair which contain the expected prompt and the value to pass.

        Exemple:
            >>> # Executing 'passwd' command as not root user
            >>> import unix
            >>> localhost = unix.Local()
            >>> localhost.expect(
            >>>     'passwd',
            >>>     ('pass', 'old_password'),   # Ask of the old password
            >>>     ('pass', 'new_password'),   # First ask of the new password
            >>>     ('pass', 'new_password')    # Second ask of the new password
            >>> )
        """
        child = pexpect.spawn(command)
        for (pattern, value) in patterns:
            child.expect(pattern)
            child.sendline(value)
            time.sleep(.1)
        output = "\n".join(
            [line.replace('\r\n', '') for line in child.readlines()[1:]]
        )

        child.close()
        return_code = child.exitstatus
        if return_code != 0:
            return [False, '', output]
        return [True, '', '']


    def get(self, *args, **kwargs):
        """Just an alias to *cp* method needed for the compatibility with
        **Remote** function *get*."""
        return self.cp(*args, **kwargs)


    def read(self, filepath, binary=False):
        """Return the content of a file. Use **binary** parameter for binary
        file."""
        mode = 'rb' if binary else 'r'
        with open(filepath, mode) as file_handler:
            return file_handler.read()


    def write(self, filepath, content, append=False, binary=False):
        """Write **content** in **filepath**. If **append**, file is not
        created or overwritted and **content** is writted at the end of the
        file. Use **binary** parameter for binary file."""
        mode = 'a' if 'append' in kwargs and kwargs['append'] else 'w'
        if 'binary' in kwargs and kwargs['binary']:
            mode += 'b'
        with open(filepath, mode) as file_handler:
            file_handler.write(content)


class Remote(Host):
    """Implementing specifics functions of a remote host."""

    def __get_ipv4(self):
        """Private function executed when *connect* is executed with hostname/fdqn
        as first parameter. It return the IPv4 address."""
        try:
            return socket.getaddrinfo(self.fqdn, 22, 2, 1, 6)[0][4][0]
        except socket.gaierror:
            return ''


    def __get_ipv6(self):
        """Private function executed when *connect* is executed with hostname/fdqn
        as first parameter. It return the IPv6 address."""
        try:
            return socket.getaddrinfo(self.fqdn, 22, 10, 1, 6)[0][4][0]
        except socket.gaierror:
            return ''


    def __get_fqdn(self):
        """Private function executed when *connect* is executed with an IPv4 or
        an IPv6 address. It return the hostname."""
        try:
            if self.ipv4:
                return socket.gethostbyaddr(self.ipv4)[0]
            elif self.ipv6:
                return socket.gethostbyaddr(self.ipv6)[0]
            else:
                return ''
        except socket.herror:
            return ''


    def __init__(self):
        """Initialize the object."""
        Host.__init__(self)
        self._connected = False


    def connect(self, host, **kwargs):
        """Connect to a remote host. The **host** parameter can a hostname, a fully
        qualified domain name (fqdn), an IPv4 or an IPv6 address. According to the
        value, FQDN, IPv4 and IPv6 are retrieved. **\*\*kwargs** parameter can contain:
            * **username**, the user for connecting (*root* by default).
            * **password**, the password for connecting (it use SSH keys by default).
            * **timeout**, timeout in seconds for the connection (default: 5)
            * **ipv6**, boolean that indicate if the connection must use the IPv6 address.
        """
        username = kwargs['username'] if 'username' in kwargs else 'root'
        password = kwargs['password'] if 'password' in kwargs else ''
        timeout = kwargs['timeout'] if 'timeout' in kwargs else 5
        use_ipv6 = True if 'ipv6' in kwargs and kwargs['ipv6'] else False

        if IPV4_REGEXP.match(host):
            # 'host' parameter is an IPv4 address.
            self.ipv4 = host
            self.fqdn = self.__get_fqdn()
            self.ipv6 = self.__get_ipv6()
        elif IPV6_REGEXP.match(host):
            # 'host' parameter is an IPv6 address.
            self.ipv6 = host
            self.fqdn = self.__get_fqdn()
            self.ipv4 = self.__get_ipv4()
        else:
            # 'host' parameter is an hostname.
            self.fqdn = host
            self.ipv4 = self.__get_ipv4()
            self.ipv6 = self.__get_ipv6()
            self.fqdn = self.__get_fqdn()

        if not self.ipv4 and not self.ipv6:
            raise ConnectError(
                "no IPv4 or IPv6 address declared for parameter '%s'" % host
            )

        self.__ip = self.ipv6 if self.ipv6 and use_ipv6 else self.ipv4

        self._ssh = paramiko.SSHClient()
        try:
            self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            params = {
                'username': username,
                'timeout': timeout,
            }
            # password = '' <=> no password
            if password:
                params.setdefault('password', password)
                params.setdefault('allow_agent', False)
                params.setdefault('look_for_keys', False)
            self._ssh.connect(self.__ip, **params)
        except Exception as exc:
            raise ConnectError(exc)
        self._sftp = self._ssh.open_sftp()
        self._connected = True


    @property
    def hostname(self):
        """Property that return the hostname."""
        return self.execute('hostname')[1].strip()


    def disconnect(self):
        """Disconnect from the remote host."""
        self._ssh.close()


    def execute(self, command, interactive=False):
        """Function that execute **command** using english utf8 locale. The output
        is a list of three elements ([*status*, *stdout*, *stderr*]). *status* is
        *True* only if return code is equal to 0. When **interactive**, output is
        in real time and interactions (ie: inputs) are possible. In this case
        *stdout* and *stderr* are empty. Return code is put in the *return_code*
        attribute of the object."""
        if not self._connected:
            raise ConnectError('no connection to an host')

        command = '%s %s' % (LOCALE, command)
        chan = self._ssh.get_transport().open_session()
        if interactive:
            chan.settimeout(0.0)
            chan.exec_command(command)
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
                print stderr
            return [
                True if self.return_code == 0 else False,
                '',
                ''
            ]
        else:
            # Execute a command and get status.
            chan.exec_command(command)
            self.return_code = chan.recv_exit_status()
            return [
                True if self.return_code == 0 else False,
                '\n'.join(chan.makefile('rb', -1).read().split('\n')[:-1]),
                '\n'.join(
                    chan.makefile_stderr('rb', -1).read().split('\n')[:-1]
                )
            ]


    def _sftp_get(self, localpath, rmtpath, recursive=False):
        """Get the file **localpath** on the localhost to *rmtpath*.
        ..todo:: implementing get for directory.
        """
        try:
            sftp = self.ssh.open_sftp()
            sftp.put(localpath, rmtpath)
            sftp.close()
            return [True, '', '']
        except IOError as ioerr:
            return [False, '', ioerr]


    def get(self, localpath, rmtpath, method='sftp'):
        """Get the file or directory **localpath** on the remote host to **rmtpath**
        using method **method**. Available methods are *sftp* and *scp*."""
        self._connected()
        if method == 'sftp':
            return self.sftp_get(local_path, rmt_path)
        else:
            return LocalHost().rmt_copy(
                local_path,
                self.__ip,
                rmt_path,
                method,
                username=self.username,
                password=self.password
            )


    def read(self, path, **kwargs):
        """Return the content of a file. Use **binary** parameter for binary
        file."""
        if not self.isfile(path):
            raise OSError("'%s' is not a file" % path)

        mode = 'rb' if 'binary' in kwargs and kwargs['binary'] else 'r'
        file_handler = self._sftp.open(path, mode)
        content = file_handler.read()
        file_handler.close()
        return content


    def write(self, path, content, **kwargs):
        """Write **content** in **filepath**. If **append**, file is not
        created or overwritted and **content** is writted at the end of the
        file. Use **binary** parameter for binary file."""
        mode = 'a' if 'append' in kwargs and kwargs['append'] else 'w'
        if 'binary' in kwargs and kwargs['binary']:
            mode += 'b'
        file_handler = self._sftp.open(path, mode)
        file_handler.write(content)
        file_handler.close()
