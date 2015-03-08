import unix

#
# Class for managing filesystem paths.
#
class Path(object):
    def __init__(self, host):
        self._host = host


    def exists(self, path):
        """Return the status of ``test -e`` command."""
        status, _, stderr = self._host.execute('test', path, e=True)
        if self._host.return_code not in (0, 1):
            raise unix.UnixError(stderr)
        return status


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
            options.update(s=True, h=False, k=True)
            status, stdout, stderr = self._host.execute('du', filepath, **options)
        if not status:
            raise OSError(stderr)
        return int(stdout.split('\t')[0])
