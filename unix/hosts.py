import os
import socket
import subprocess
import pexpect
import paramiko
import crypt
import random
import string
import re
import time
from datetime import datetime


IPV4_REGEXP = re.compile('^[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}$')
"""Regular expression for checking format of an IPv4 address."""

IPV6_REGEXP = re.compile(
    '^[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:'
    '[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}$'
)
"""Regular expression for checking format of an IPv6 address."""



class ConnectError(Exception):
    """Exception raised when there is an error when connecting to a
    remote host."""
    pass


class UnknownMethod(Exception):
    """Exception raised when there is an attempt to execute a function
    that the object not have."""
    pass


class LocalHost(object):
    """Class that execute commands on localhost.

    @sort: __init__, execute, expect, copy, scp_copy, tar_copy
    """
    def __init__(self):
        """Initialize the object. This method only get hostname of the
        localhost.
        """
        self.hostname = socket.gethostname()


    def execute(self, *commands):
        """Execute commands. If there are many commands, command are piped. Only
        the stderr of the last command is returned so, if there are errors
        before the last command, status is set to False but stderr is empty!

        @type *command: list
        @param *command: Commands to execute.

        @rtype: list
        @return: status, stdout, stderr
        """
        previous = None
        for command in commands:
            if previous:
                obj = subprocess.Popen(
                    command,
                    stdin = previous.stdout,
                    stdout = subprocess.PIPE,
                    stderr = subprocess.PIPE,
                )
                previous.stdout.close()
            else:
                obj = subprocess.Popen(
                    command,
                    stdout = subprocess.PIPE,
                    stderr = subprocess.PIPE
                )
            previous = obj

        try:
            stdout, stderr = obj.communicate()
            if obj.returncode != 0:
                return (False, stdout, stderr)
            return (True, stdout, stderr)
        except OSError as os_err:
            return (False, '', os_err)


    def expect(self, command, *patterns):
        """Execute command on the local host that need inputs.

        Exemple:
        >>> # Executing as not root user
        >>> localhost.expect(
        >>>     'passwd',
        >>>     ('pass', 'old_password'),   # Ask of the old password
        >>>     ('pass', 'new_password'),   # First ask of the new password
        >>>     ('pass', 'new_password')    # Second ask of the new password
        >>> )

        @type command: str
        @param command: Command with parameters to execute.
        @type *pattern: list
        @param *pattern: List of couple pattern/value to send

        @rtype: list
        @return: status, stdout, stderr
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
            return (False, '', output)
        return (True, '', '')


    def rmt_copy(self, path, hostname, rmt_path, method='scp', **ids):
        """Wrapper for copy methods.

        @type path: str
        @param path: Path of the file/directory on localhost.
        @type hostname: str
        @param hostname: Hostname/IP of the remote host.
        @type rmt_path: str
        @param rmt_path: Remote path.
        @type method: str
        @param method: Method ('scp', 'tar', ...) for copyign files.
        @type ids: dict
        @param rmt_user: ids (username and password) for the connexion.

        @rtype: list
        @return: status, stdout, stderr
        """
        username = 'root' \
            if not 'username' in ids or ids['username'] == '' \
            else ids['username']
        pwd = '' \
            if not 'password' in ids or ids['password'] == '' \
            else ids['password']

        try:
            function = getattr(self, '%s_copy' % method)
        except AttributeError:
            raise UnknownMethod("Invalid copy method '%s'" % method)
        return function(path, hostname, rmt_path, username, pwd)


    def scp_copy(self, path, hostname, rmt_path, username, password):
        """Copy a file or a directory from the local host to a remote host with
        SCP command.

        @type path: str
        @param path: Path of the file/directory on the local host.
        @type hostname: str
        @param hostname: Hosrname of the remote host.
        @type rmt_path: str
        @param rmt_path: Path of the file/directory on the remote host.
        @type username: str
        @param username: Username of the remote host.
        @type password: str
        @param password: Remote password (optionaly).

        @rtype: list
        @return: status, stdout, stderr
        """
        command = [
            'scp', '-rp',
            '-o', 'StrictHostKeyChecking=no',
            path,
            '%s@%s:%s' % (username, hostname, rmt_path)
        ]
        if password:
            command.insert(2, '-o PubkeyAuthentication=no')

        return \
            self.execute(command) if not password \
            else self.expect(' '.join(command), ("assword", password))


    def tar_copy(self, path, hostname, rmt_path, username, password, transform=''):
        """Copy a file or a directory from the local host to a remote host with
        SCP command.

        @type path: str
        @param path: Path of the file/directory on the local host.
        @type hostname: str
        @param hostname: Hosrname of the remote host.
        @type rmt_path: str
        @param rmt_path: Path of the file/directory on the remote host.
        @type username: str
        @param username: Username of the remote host.
        @type password: str
        @param password: Remote password (optionaly).
        @type transform: str
        @param transform: pattern for transforming file names.

        @rtype: list
        @return: status, stdout, stderr
        """
        compress_cmd = (
            'tar', 'czf', '-', '-C',
            os.path.abspath(os.path.dirname(path)),
            os.path.basename(path)
        )
        uncompress_cmd = [
            'ssh', '-o StrictHostKeyChecking=no',
            '%s@%s' % (username, hostname),
            'tar', 'xzf', '-', '-C', rmt_path
        ]
        if password:
            uncompress_cmd.insert(2, '-o PubkeyAuthentication=no')
        if transform:
            uncompress_cmd.append('--transform %s' % transform)

        return \
            self.execute(compress_cmd, uncompress_cmd) if not password \
            else self.expect(
                '/bin/sh -c "%s | %s"' % (
                    ' '.join(compress_cmd),
                    ' '.join(uncompress_cmd)
                ),
                ('assword', password)
            )


class RemoteHost(object):
    """Class that connect to a host and execute commands and actions on it.

    @sort: __init__, _get_*, connect, _connected, disconnect, execute, exists,
    filetype, isfile, isdir, listdir, mkdir, cp, mv, rm, rmdir, ch*, read,
    readlines, write, replace, get, sftp_get, copy, scp_copy, tar_copy, get_*,
    load, loaded, unload, manage_service, start, stop, restart, reload,
    set_password
    """
    def __init__(self, host=None):
        """Initialize host.

        If an host object is pass, attributes of the given object are copied.

        @type host: Host
        @param host: Host object that it inherits the properties.
        """
        if host:
            self.__dict__.update(host.__dict__)


    def _get_ipv4(self):
        """Get IPv4 address of the host.

        @rtype: str
        @return: IPv4 address or empty string if not exists.
        """
        try:
            return socket.getaddrinfo(self.fqdn, 22, 2, 1, 6)[0][4][0]
        except socket.gaierror:
            return ''


    def _get_ipv6(self):
        """Get IPv6 of the host.

        @rtype: str
        @return: IPv6 address or empty string if not exists.
        """
        try:
            return socket.getaddrinfo(self.fqdn, 22, 10, 1, 6)[0][4][0]
        except socket.gaierror:
            return ''


    def _get_fqdn(self):
        """Get FQDN of the host.

        @rtype: str
        @return: Hostname if has one
        """
        try:
            if self.ipv4:
                return socket.gethostbyaddr(self.ipv4)[0]
            elif self.ipv6:
                return socket.gethostbyaddr(self.ipv6)[0]
            else:
                return ''
        except socket.herror:
            return ''


    def connect(self, ip, username='root', password='', timeout=4, ipv6=False):
        """Connect to the host.

        This method must be executed just after initialization of the object.
        The only exception is if an host which has already executed this method
        is passed at the initialization.

        The first parameter is the IPv4/IPv6 address or the FQDN (Fully Qualified
        Domain Name)/hostname (localhost must resolv him) of the host. According
        to given parameter it get the others datas. At the end of method, object
        has theses attributes:
            - ipv4
            - ipv6
            - fqdn
            - hostname
        Attributes are empty strings if not exists except the hostname that is
        retrieve by executing the command I{hostname} if connection succeed.
        If it is not possible to get an IPv4 or an IPv6 address, the method raise
        the exception B{ConnectError}.

        The second and thid parameters are ids (username/password) for the
        connection. Password is optionaly and if not given, the SSH keys
        of the user executing the script are used or password is asked in
        console.

        @type ip: str
        @param ip: IPv4/IPv6/fqdn/hostname of the host.
        @type username: str
        @param username: User for the connection.
        @type password: str
        @param password: Password for the connection.
        @type timeout: int
        @param timeout: Timeout for the connection.
        @type ipv6: boolean
        @param ipv6: Use the ipv6 address if exists (not by default).
        """
        self.username = username
        self.password = password

        if IPV4_REGEXP.match(ip):
            self.ipv4 = ip
            self.fqdn = self._get_fqdn()
            self.ipv6 = self._get_ipv6()
        elif IPV6_REGEXP.match(ip):
            self.ipv6 = ip
            self.fqdn = self._get_fqdn()
            self.ipv4 = self._get_ipv4()
        else:
            self.fqdn = ip
            self.ipv4 = self._get_ipv4()
            self.ipv6 = self._get_ipv6()
            self.fqdn = self._get_fqdn()

        if not self.ipv4 and not self.ipv6:
            raise ConnectError("no IPv4 or IPv6 address")

        self.ip = self.ipv6 if self.ipv6 and ipv6 else self.ipv4

        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if password:
                self.ssh.connect(
                    self.ip,
                    username=username,
                    password=password,
                    allow_agent=False,
                    look_for_keys=False,
                    timeout=timeout
                )
            else:
                self.ssh.connect(
                    self.ip,
                    username=username,
                    timeout=timeout
                )
            self.hostname = self.execute('hostname')[1].strip()
        except Exception as exc:
            raise ConnectError(exc)


    def _connected(self):
        """Check that a connection is opened and raise exception B{ConnectError}
        if not.
        """
        if not 'ssh' in self.__dict__:
            raise ConnectError("no connection to the host")


    def disconnect(self):
        """Close the SSH connection."""
        self.ssh.close()


    def execute(self, command):
        """Execute a command in the remote host.

        @type command: str
        @param command: Command to execute.

        @rtype: list
        @return: status, stdout, stderr
        """
        self._connected()

        # Execute a command and get status.
        stdin, stdout, stderr = self.ssh.exec_command('%s; echo $?' % command)
        stdout = stdout.readlines()
        return_code = int(stdout[-1].strip())
        stdout = ''.join(stdout[:-1])

        # Deleting blank line on stderr.
        stderr = ''.join(
            [line if line != '\n' else '' for line in stderr.readlines()]
        )

        if return_code != 0:
            return (False, stdout, stderr)
        return (True, stdout, stderr)


    def exists(self, path):
        """Check that a file or a directory exists on remote filesystem.

        It manage the exception raised by I{filetype} function.

        @type path: str
        @param path: Path of the file/directory to check.

        @rtype: list
        @return: status, stdout, stderr
        """
        self._connected()
        try:
            self.filetype(path)
            return True
        except OSError:
            return False


    def filetype(self, path):
        """Get the type of the given file/directory.

        It use I{file} command. For managing language of the output in method
        using this one, the command set I{LC_ALL} environment variable to
        I{en_US.utf8} but I am not sure it really work in all case (en_US.utf-8
        must be generated in remote host and, is setting LC_ALL really work on all
        UNIX like systems?)! TODO: manage this :-)

        @type path: str
        @param path: Path of the file/directory on remote filesystem.

        @rtype: str
        @return: Second part (after ':') of the I{file} command.
        """
        self._connected()
        # TODO: manage LANG of output or set all output in english.
        locale = 'LC_ALL=en_US.utf8'
        status, stdout, stderr = self.execute('%s file %s' % (locale, path))
        if not status:
            # For unexpected reason, errors are in stdout!
            raise OSError(stdout)

        return stdout.split(':')[-1].strip()


    def isfile(self, path):
        """Check that given path is a file.

        It check that the type of the file don't match:
            - 'block device'
            - 'character device'
            - 'directory'
            - 'link'
        Maybe it miss some others matchs!!

        @type path: str
        @param path: Path to check.

        @rtype: boolean
        @return: I{True} if it is a file, I{False} otherwise.
        """
        self._connected()
        filetype = self.filetype(path)
        no_file_list = ('block special', 'character special', 'directory', 'link')
        for current_type in no_file_list:
            if filetype.find(current_type) != -1:
                return False
        return True


    def isdir(self, path):
        """Check that given path is a directory.

        It check that the type of the file is 'directory'.

        @type path: str
        @param path: Path to check.

        @rtype: boolean
        @return: I{True} if it is a directory, I{False} otherwise.
        """
        self._connected()
        return True if self.filetype(path) == 'directory' else False


    def listdir(self, dirpath):
        """List files on a directory.

        @type dirpath: str
        @param dirpath: Directory to list files.

        @rtype: list
        @return: List of files and directories.
        """
        self._connected()
        if not self.isdir(dirpath):
            raise OSError('%s is not a directory' % dirpath)
        status, stdout, stderr = self.execute('ls %s' % dirpath)
        if not status:
            raise OSError(stderr)
        return stdout.split('\n')[:-1]


    def mkdir(self, dirpath, parents=True):
        """Create a directory and parents by default.

        It use the I{mkdir} command with '-p' option by default for creating
        parents. If I{parents} parameter is set to I{False}, the '-p' option
        is removed from the command.

        @type dirpath: str
        @param dirpath: Directory path to create.
        @type parents: boolean
        @param parents: Indicate if parents must be created.
        """
        command = ['mkdir', dirpath]
        if parents:
            command.insert(1, '-p')
        output = self.execute(" ".join(command))
        if not output[0]:
            raise OSError(output[2])


    def cp(self, src, dest, recursive=False):
        """Copy a file from a source to a destination on remote filesystem.

        @type src: str
        @param src: Path of the source on the remote host.
        @type dest: str
        @param dest: Path of the destination on the remote host.

        @rtype: list
        @return: Status, stdout, stderr
        """
        self._connected()
        if not recursive and self.isdir(src):
            raise OSError("%s is a directory" % src)

        command = ['cp',]
        if recursive:
            command.append('-R')
        command.append(src)
        command.append(dest)
        output = self.execute(' '.join(command))
        if not output[0]:
            raise OSError(output[2])


    def mv(self, old_path, new_path):
        """Move a file/directory.

        @type old_path: str
        @param old_path: Path of the file/directory to move.
        @type new_path: str
        @param new_path: New path of the file/directory.

        @rtype: list
        @return: status, stdout, stderr
        """
        self._connected()
        output = self.execute('mv %s %s' % (old_path, new_path))
        if not output[0]:
            raise OSError(output[2])


    def rm(self, filepath):
        """Remove a file.

        @type filepath: str
        @param filepath: Path of the file to remove.

        @rtype: list
        @return: status, stdout, stderr
        """
        self._connected()
        output = self.execute('rm %s' % filepath)
        if not output[0]:
            raise OSError(output[2])


    def rmdir(self, dirpath, safe=False):
        """Remove a directory.

        By default the directory is deleted recursively using I{rm -r} command
        but if I{safe} parameter is set to I{True}, the directory is deleted
        only if it is empty.

        @type dirpath: str
        @param dirpath: Path of the directory to remove.
        @type safe: boolean
        @param safe: Delete only an empty directory.

        @rtype: list
        @return: status, stdout, stderr
        """
        self._connected()
        command = 'rmdir %s' % dirpath if safe else 'rm -r %s' % dirpath
        output = self.execute(command)
        if not output[0]:
            raise OSError(output[2])


    def chown(self, path, user, recursive=False):
        """Change owner of a file/directory.

        @type path: str
        @param path: File/directory to set owner.
        @type user: str
        @param user: New owner.
        @type recursive: boolean
        @param recursive: Recursively set owner.

        @rtype: list
        @return: status, stdout, stderr
        """
        command = ['chown', user, path]
        if recursive:
            command.insert(1, '-R')
        return self.execute(" ".join(command))


    def chgrp(self, path, group, recursive=False):
        """Change group of a file/directory.

        @type path: str
        @param path: File/directory to set group.
        @type group: str
        @param group: New group.
        @type recursive: boolean
        @param recursive: Recursively set group.

        @rtype: list
        @return: status, stdout, stderr
        """
        command = ['chgrp', group, path]
        if recursive:
            command.insert(1, '-R')
        output = self.execute(" ".join(command))
        if not output[0]:
            raise OSError(output[2])


    def chmod(self, path, rights, recursive=False):
        """Change rights of a file/directory.

        @type path: str
        @param path: File/directory to set rights.
        @type rights: str
        @param rights: New rights.
        @type recursive: boolean
        @param recursive: Recursively set owner.

        @rtype: list
        @return: status, stdout, stderr
        """
        command = ['chmod', rights, path]
        if recursive:
            command.insert(1, '-R')
        output = self.execute(" ".join(command))
        if not output[0]:
            raise OSError(output[2])


    def read(self, filepath):
        """Get the content of a file and return it in a string.

        @type filepath: str
        @param filepath: Path of the file to read.

        @rtype: str
        @return: Content of the file.
        """
        self._connected()

        if not self.isfile(filepath):
            raise IOError("%s is not a file" % filepath)

        sftp = self.ssh.open_sftp()
        sftp_file = sftp.file(filepath, 'r')
        content = sftp_file.read()
        sftp_file.close()
        sftp.close()
        return content


    def readlines(self, filepath):
        """Get the content of a file and return it in a list of lines.

        @type filepath: str
        @param filepath: Path of the file to read.

        @rtype: list
        @return: List with lines of the file.
        """
        return self.read(filepath).split('\n')


    def write(self, filepath, content):
        """Write (replace if exist) a file.

        @type filepath: str
        @param filepath: Path of the file to create/replace.
        @type content: str
        @param content: Content of the file.

        @rtype: list
        @return: status, nothing, error message.
        """
        self._connected()

        dirpath = '/'.join(filepath.split('/')[:-1])
        if not self.isdir(dirpath):
            raise IOError(
                "base directory of the file %s already exists and it is not a directory"
            )
        try:
            sftp = self.ssh.open_sftp()
            sftp_file = sftp.file(filepath, 'w')
            sftp_file.write(content)
            sftp_file.close()
            return (True, '', '')
        except IOError as ioerr:
            return (False, '', ioerr)
        finally:
            sftp.close()


    def replace(self, filepath, old_pattern, value):
        """Replace in the content of a file a pattern by a new value.

        It use I{sed -i} command so patterns must be bash patterns and not
        python patterns (is there differences?).

        @type filepath: str
        @param filepath: Path of the file to sed.
        @type old_pattern: str
        @param old_pattern: Regular expression to replace.
        @type value: str
        @param value: New value.

        @rtype: list
        @return: status, nothing, error message.
        """
        self._connected()

        if not self.isfile(filepath):
            raise IOError("%s is not a file") % filepath

        return self.execute(
            "sed -i s/%s/%s/g %s"  % (old_pattern, value, filepath)
        )


    def sftp_get(self, local_src, rmt_dest):
        try:
            sftp = self.ssh.open_sftp()
            sftp.put(local_src, rmt_dest)
            sftp.close()
            return (True, '', '')
        except IOError as ioerr:
            return (False, '', ioerr)


    def get(self, local_path, rmt_path, method='sftp'):
        """Copy a file or a directory from the local host to the remote host.

        If method is 'sftp', the paramiko SFTP object is used otherwise it is
        one of the LocalHost copy function that is used. SFTP client implemented
        by paramiko is slow with big file and it is better to use scp command
        for example.

        @type local_path: str
        @param local_path: Path of the file on the local host.
        @type rmt_path: str
        @param rmt_path: Path of the file on the remote host.
        @type use_scp: boolean
        @param use_scp: Use 'scp' system command instead of paramiko.
        @type use_tar: boolean
        @param use_tar: Use 'tar' system command instead of paramiko.

        @rtype: list
        @return: status, stdout, stderr
        """
        self._connected()
        if method == 'sftp':
            return self.sftp_get(local_path, rmt_path)
        else:
            return LocalHost().rmt_copy(
                local_path,
                self.ip,
                rmt_path,
                method,
                username=self.username,
                password=self.password
            )


    def rmt_copy(self, path, hostname, rmt_path, username='root', method='scp'):
        """Copy a file from remote host to another host.

        It is a wrapper that execute a function of the current object according
        to given method. The function on current object has for format
        I{method}_copy. For example if method I{scp} is passed, it return the
        result of the object function I{scp_copy}.

        @type path: str
        @param path: Path of the file/directory to copy.
        @type hostname: str
        @param hostname: Hostname of the host on which copying file.
        @type rmt_path: str
        @param rmt_path: Where to copy file/directory on remote host.
        @type username: str
        @param username: User for copying file (keys must be on the host).
        @type method: str
        @param method: Method for copying file.

        @rtype: list
        @return: status, stdout, stderr
        """
        self._connected()
        try:
            function = getattr(self, '%s_copy' % method)
        except AttributeError:
            raise UnknownMethod("Invalid copy method '%s'" % method)
        return function(path, hostname, rmt_path, username)


    def scp_copy(self, path, hostname, rmt_path, username='root'):
        """Copy a file/directory from the remote host to another host using
        I{scp} command.

        The remote host must have SSH keys of the host on which the copy is done
        because it is not possible to use expect on the remote host.

        @type path: str
        @param path: Path of a file/directory on the remote host.
        @type hostname: str
        @param hostname: Host on which copy the file/directory.
        @type rmt_path: str
        @param rmt_path: Path of the destination in the other host.
        @type username: str
        @param username: User for the remote connection (remote host must have
                         SSH keys for this user).

        @rtype: list
        @return: status, stdout, stderr
        """
        self._connected()
        return self.execute(' '.join((
            'scp -rp',
            '-o StrictHostKeyChecking=no',
            path,
            '%s@%s:%s' % (username, hostname, rmt_path)
        )))


    def tar_copy(self, path, hostname, rmt_path, username='root'):
        """Copy a file/directory from the remote host to another host using
        I{tar} command.

        The command used is:
          tar czf - -C I{path} | ssh -o StrictHostKeyChecking I{rmt_user}@I{rmt_host}
          tar xzf - -C I{rmt_path}

        The remote host must have SSH keys of the host on which the copy is done
        because it is not possible to use expect on the remote host.

        @type path: str
        @param path: Path of a file/directory on the remote host.
        @type hostname: str
        @param hostname: Host on which copy the file/directory.
        @type rmt_path: str
        @param rmt_path: Path of the destination in the other host.
        @type username: str
        @param username: User for the remote connection (remote host must have
                         SSH keys for this user).

        @rtype: list
        @return: status, stdout, stderr
        """
        self._connected()
        return self.execute(' '.join((
            'tar czf - -C',
            os.path.abspath(os.path.dirname(path)),
            os.path.basename(path),
            '|',
            'ssh', '-o StrictHostKeyChecking=no',
            '%s@%s' % (username, hostname),
            'tar xzf - -C', rmt_path
        )))


    def get_os(self):
        """Get operating system.

        It parse the file I{/etc/issue} which is use by Linux like systems. If
        this not exists (ie: it is an UNIX system), the command I{uname -rs} is
        executed which work on very most common UNIX systems.

        @rtype: str
        @return: Operating system.
        """
        self._connected()
        try:
            content = self.readlines('/etc/issue')
            os_desc = content[0]
            os_desc = os_desc.replace('(\\n)', '').replace('(\l)', '').replace('(\\r)', '')
            os_desc = os_desc.replace('\\n', '').replace('\l', '').replace('\\r', '')
            os_desc = os_desc.strip()
        except IOError:
            status, stdout = self.execute('uname -rs')[:2]
            os_desc = stdout.strip() if status else ''
        return os_desc


    def get_arch(self):
        """Get architecture of the operating system.

        The command I{uname -m} is used.

        @rtype: str
        @return: Architecture of the operating system.
        """
        self._connected()
        status, stdout = self.execute('uname -m')[:2]
        return (stdout.strip() if status else '')


    def loaded(self, module):
        """Indicate if a module is loaded.

        @type module: str
        @param module: Name of a module.

        @rtype: boolean
        @return: I{True} if module is loaded, I{False} otherwise.
        """
        self._connected()
        status, stdout, stderr = self.execute('lsmod')
        if not status:
            return False

        for line in stdout.split('\n')[1:-1]:
            if line.split()[0] == module:
                return True
        return False


    def load(self, module, options=()):
        """Load a module (eventually with opions).

        @type module: str
        @param module: Name of a module
        @type options: list
        @param options: Options of the module for the loading.

        @rtype: list
        @return: status, stdout, stderr
        """
        self._connected()
        return self.execute('modprobe %s %s' % (module, ' '.join(options)))


    def unload(self, module):
        """ Unload a module.

        @type module: str
        @param module: Name of a module

        @rtype: list
        @return: status, stdout, stderr
        """
        self._connected()
        return self.execute('rmmod %s' % module)


    def manage_service(self, service, action, type='init'):
        """Manage host service.

        It use first I{service} command (upstart) and if it failed, I{/etc/init.d/}
        init script.

        @type service: str
        @param service: Name of the service.
        @type action: str
        @param action: Action to execute ('start', 'stop', 'restart', 'reload', ...)
        @type type: str
        @param type: Where init script are set ('init' or 'rc')

        @rtype: list
        @return: status, stdout, stderr
        """
        self._connected()
        status, stdout, stderr = self.execute('service %s %s' % (service, action))
        if status:
            return (status, stdout, stderr)
        return self.execute('/etc/%s.d/%s %s' % (type, service, action))


    def start(self, service, type='init'):
        """Start a service.

        It use I{manage_service} function with I{start} action.

        @type service: str
        @param: service: Name of the service.
        @type type: str
        @param type: Where init script are set ('init' or 'rc')

        @rtype: list
        @return: status, stdout, stderr
        """
        return self.manage_service(service, 'start', type)


    def stop(self, service, type='init'):
        """Stop a service.

        It use I{manage_service} function with I{stop} action.

        @type service: str
        @param: service: Name of the service.
        @type type: str
        @param type: Where init script are set ('init' or 'rc')

        @rtype: list
        @return: status, stdout, stderr
        """
        return self.manage_service(service, 'stop', type)


    def restart(self, service, type='init'):
        """Restart a service.

        It use I{manage_service} function with I{restart} action.

        @type service: str
        @param: service: Name of the service.
        @type type: str
        @param type: Where init script are set ('init' or 'rc')

        @rtype: list
        @return: status, stdout, stderr
        """
        return self.manage_service(service, 'restart', type)


    def reload(self, service, type='init'):
        """Reload a service.

        It use I{manage_service} function with I{reload} action.

        @type service: str
        @param: service: Name of the service.
        @type type: str
        @param type: Where init script are set ('init' or 'rc')

        @rtype: list
        @return: status, stdout, stderr
        """
        return self.manage_service(service, 'reload', type)


    def set_password(self, username, password, shadow_file='/etc/shadow'):
        """Set password for a user.

        The password is crypt then added/replaced in given shadow file.
        For crypting a password:

        >>> import crypt
        >>> import random
        >>> import string
        >>> choices = random.choice(string.letters + string.digits)
        >>> random_hash = ''.join([choices for i in xrange(0,8)])
        >>> crypt.crypt(password, '$6$%s$' % random_hash)

        @type username: str
        @param username: User to change password.
        @type password: str
        @param password: New password.
        @type shadow_file: str
        @param shadow_file: Path of the shadow file.

        @rtype: list
        @return: status, stdout, stderr
        """
        self._connected()
        hashed_password = crypt.crypt(password, '$6$%s$' % ''.join(
            [random.choice(string.letters + string.digits) for i in xrange(0,8)]
        ))
        shadow_line = '%s:%s:%s:0:99999:7:::' % (
            username,
            hashed_password,
            (datetime.today() - datetime(1970, 1, 1)).days
        )

#        file_content = self.execute('cat %s' % dest)[1]
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
        return self.write(shadow_file, '\n'.join(new_content))
