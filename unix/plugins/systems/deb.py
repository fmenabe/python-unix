from unix.remote import RemoteHost

class DebHost(RemoteHost):
    """Class for managing host based on Deb packages and APT package manager
    like Debian, Ubuntu, ...
    """
    def __init__(self, host=None):
        """Initialize object.

        @type host: Host
        @param host: Host object from which copying attributs.
        """
        Host.__init__(self)
        if host:
            self.__dict__.update(host.__dict__)
        os_desc = self.get_os()
        if os_desc.lower().find('ubuntu') == -1 \
        and os_desc.lower().find('debian') == -1:
            raise InvalidOS('Not an Ubuntu/Debian operating system!')
        self.version = ' '.join(os_desc.split()[1:])
        self.arch = self.get_arch()


    def check_pkg(self, package):
        """Check a package is installed.

        @type package: str
        @param package: Package to check.

        @rtype: boolean
        @return: I{True} if package installed, I{False} otherwise.
        """
        self._connected()
        status, stdout = self.execute('dpkg -l')[:2]
        for line in stdout.split('\n'):
            if status and line.find(package) != -1 and line[0] != 'r':
                return True
        return False


        def add_key(self, filepath):
        """Add a repository GPG key.

        @type filepath: str
        @param filepath: Path of the key to add on remote host.

        @rtype: list
        @return: status, stdout, stderr
        """
        self._connected()
        remote_filepath = os.path.join('/tmp', os.path.basename(filepath))
        self.get(filepath, remote_filepath)
        return self.execute('apt-key add %s' % remote_filepath)


    def add_repository(self, filepath):
        """Add a repository.

        @type filepath: str
        @param filepath: Path of the repository file.

        @rtype: list
        @return: status, stdout, stderr
        """
        self._connected()
        return self.get(filepath, os.path.join(
            '/etc/apt/sources.list.d',
            os.path.basename(filepath)
        ))


    def apt_update(self):
        """Update package list.

        @rtype: list
        @return: status, stdout, stderr
        """
        self._connected()
        return self.execute('aptitude update')


    def apt_install(self, packages):
        """Install packages.

        @type packages: list
        @param packages: List of packages to install.

        @rtype: list
        @return: status, stdout, stderr
        """
        self._connected()
        return self.execute(
            '%s aptitude install -y %s' % (NO_DEBCONF, ' '.join(packages))
        )


    def apt_search(self, package):
        """Search if package exists

        @type package: str
        @param package: Package to search

        @rtype: list
        @return: status, stdout, stderr
        """
        self._connected()
        status, stdout, stderr = self.execute("aptitude search %s" % package)
        if status:
            for line in stdout.split("\n"):
                if line.find(package) != -1:
                    return True

        return False


    def apt_remove(self, packages, purge=False):
        """Remove packages.

        If I{purge} is set ti I{True}, configuration are also deleted.

        @type packages: list
        @param packages: List of packages to remove.

        @rtype: list
        @return: status, stdout, stderr
        """
        self._connected()
        apt_command = 'purge -y' if purge else 'remove -y'
        return self.execute(
            '%s aptitude %s %s' % (NO_DEBCONF, apt_command, ' '.join(packages))
        )


    def deb_install(self, filepath, force=False):
        """Install a deb package.

        If I{force} is set to I{True}, dependances are also installed.

        @type filepath: str
        @param filepath: Path of the package to install.

        @rtype: list
        @return: status, stdout, stderr
        """
        self._connected()
        command = '-i --force-depends' if force else '-i'
        return self.execute('%s dpkg %s %s' % (NO_DEBCONF, command, filepath))
