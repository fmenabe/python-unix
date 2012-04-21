import socket
import subprocess
import pexpect

class LocalHost(object):
    """Class that execute command and actions on localhost.

    @sort: __init__, execute, expect, copy, scp_copy, tar_copy
    """
    def __init__(self):
        """Initialize object.

        This method only get hostname of the localhost.
        """
        self.hostname = socket.gethostname()


    def execute(self, command, piped_command=''):
        """Execute a command (and eventually a piped command) on the local host.

        TODO: given list of commands in parameters and piped then recursively.

        @type command: list
        @param command: List of parameters of the main command.
        @type piped_command: list
        @param piped_command: List of parameters of the piped command.

        @rtype: list
        @return: status, stdout, stderr
        """
        try:
            obj = subprocess.Popen(
                command,
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE
            )
            if piped_command:
                obj2 = subprocess.Popen(
                    piped_command,
                    stdin = obj.stdout,
                    stdout = subprocess.PIPE,
                    stderr = subprocess.PIPE
                )
                obj.stdout.close()
                stdout, stderr = obj2.communicate()
                return_code = obj2.returncode
            else:
                stdout, stderr = obj.communicate()
                return_code = obj.returncode
#            stderr = ''
            if return_code != 0:
                return (False, stdout, stderr)
            return (True, stdout, stderr)
        except OSError as oserr:
            return (False, '', oserr)


    def _execute(self, command, previous=None):
        if previous:
            obj = subprocess.Popen(
                command,
                stdin = previous.stdout,
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE
            )
            previous.stdout.close()
        else:
            obj = subprocess.Popen(
                command,
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE
            )
        return obj


    def execute(self, *commands):
        obj = None
        for command in commands:
            obj = self._execute(command, obj)

#        try:
        stdout, stderr = obj.communicate()
        if obj.returncode != 0:
            return (False, stdout, stderr)
        return (True, stdout, stderr)
#        except OSError as os_err:
#            return (False, '', os_err)


    def expect(self, command, pattern, value, repeat=1):
        """Execute command on the local host that need inputs.

        It is possible to repeat the couple pattern/value for the command but
        if pattern/value are different it don't work. For example, when changing
        a non root user password, the previous password is ask, so the first
        input is different of the two others!

        @type command: str
        @param command: Command(s) to execute.
        @type pattern: str
        @param pattern: Expected input of the command.
        @type value: str
        @param value: Value of the input.
        @type repeat: int
        @param repeat: Number of time the input is asked (two for password for
                       example).

        @rtype: list
        @return: status, stdout, stderr

        Exemple:

        >>> localhost.expect('passwd', 'assword', 'toto', 2)
        """
        child = pexpect.spawn(" ".join(command))
        for i in xrange(0, repeat):
            child.expect(pattern)
            child.sendline(value)
            time.sleep(0.1)
        output = "\n".join(
            [line.replace('\r\n', '') for line in child.readlines()[1:]]
        )

        child.close()
        return_code = child.exitstatus
        if return_code != 0:
            return (False, '', output)
        return (True, '', '')


    def rmt_copy(self, path, rmt_path, rmt_hostname, rmt_user='root', rmt_pwd='',
    method='scp'):
        """Wrapper for copy methods.

        @type path: str
        @param path: Path of the file/directory on localhost.
        @type rmt_path: str
        @param rmt_path: Remote path.
        @type rmt_hostname: str
        @param rmt_hostname: Hostname of the remote host.
        @type rmt_user: str
        @param rmt_user: User for copy.
        @type rmt_pwd: str
        @param rmt_pwd: Password.
        @type method: str
        @param method: Method ('scp', 'tar', ...) for copyign files.

        @rtype: list
        @return: status, stdout, stderr
        """
        function = getattr(self, '%s_copy' % method)
        return function(path, rmt_path, rmt_hostname, rmt_user, rmt_pwd)


    def scp_copy(self, path, rmt_path, rmt_hostname, rmt_user, rmt_pwd=''):
        """Copy a file or a directory from the local host to a remote host with
        SCP command.

        If no password is given it use I{execute} method otherwise I{expect}
        method.

        @type path: str
        @param path: Path of the file/directory on the local host.
        @type rmt_path: str
        @param rmt_path: Path of the file/directory on the remote host.
        @type rmt_hostname: str
        @param rmt_hostname: Hosrname of the remote host.
        @type rmt_user: str
        @param rmt_user: Username of the remote host.
        @type rmt_pwd: str
        @param rmt_pwd: Remote password (optionaly).

        @rtype: list
        @return: status, stdout, stderr
        """
        command = [
            'scp', '-rp',
            '-o', 'StrictHostKeyChecking=no',
            path,
            '%s@%s:%s' % (rmt_user, rmt_hostname, rmt_path)
        ]
        if rmt_pwd:
            command.insert(2, '-o PubkeyAuthentication=no')

        return self.execute(command) if not rmt_pwd else self.expect(
            command,
            "assword",
            rmt_pwd
        )


    def tar_copy(self, path, rmt_path, rmt_hostname, rmt_user, rmt_pwd='',
    transform=''):
        """Copy a file or a directory from the local host to a remote host with
        SCP command.

        If no password is given it use I{execute} method othewise I{expect}
        method.

        @type path: str
        @param path: Path of the file/directory on the local host.
        @type rmt_path: str
        @param rmt_path: Path of the file/directory on the remote host.
        @type rmt_hostname: str
        @param rmt_hostname: Hosrname of the remote host.
        @type rmt_user: str
        @param rmt_user: Username of the remote host.
        @type rmt_pwd: str
        @param rmt_pwd: Remote password (optionaly).
        @type transform: str
        @param transform: pattern for transforming file names.

        @rtype: list
        @return: status, stdout, stderr
        """
        src_dirname = os.path.abspath(os.path.dirname(path))
        src_filename = os.path.basename(path)
        command = ('tar', 'czf', '-', '-C', src_dirname, src_filename)
        pipe_command = [
            'ssh', '-o StrictHostKeyChecking=no',
            '%s@%s' % (rmt_user, rmt_hostname),
            'tar', 'xzf', '-', '-C', rmt_path
        ]
        if rmt_pwd:
            pipe_command.insert(2, '-o PubkeyAuthentication=no')
        if transform:
            pipe_command.append('--transform %s' % transform)

        return self.execute(
            command,
            pipe_command
        ) if not rmt_pwd else self.expect(
            (
                '/bin/sh -c "%s | %s"' % (
                ' '.join(command),
                ' '.join(pipe_command)
                ),
            ),
            'assword',
            rmt_pwd
        )
