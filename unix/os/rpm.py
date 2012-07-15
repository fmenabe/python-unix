class RpmHost(Host):
    """Class based on Rpm packages and YUM package manager like Redhat,
    Centos, OEL, ...
    """
    def __init__(self, host=None):
        Host.__init__(self)
        if host:
            self.__dict__.update(host.__dict__)
        os_desc = self.get_os()
        if os_desc.lower().find('red hat') == -1 \
        and os_desc.lower().find('centos') == -1 \
        and os_desc.lower().find('oracle linux') == -1:
            raise InvalidOS('Not a Red Hat/Centos operating system')
        self.desc = os_desc
        self.version = os_desc.split('(')[0].split()[-1]
        self.arch = self.get_arch()


    def check_pkg(self, package):
        self._connected()
        status, stdout = self.execute('rpm -qa')[:2]
        if status and stdout.find(package) != -1:
            return True
        return False


    def add_repository(self, filepath):
        self._connected()
        return self.get(filepath, os.path.join(
            '/etc/yum.repos.d',
            os.path.basename(filepath))
        )


    def yum_install(self, packages, repository=''):
        self._connected()
        yum_cmd = '-y' if not repository else '-y --enablerepo=%s' % repository
        return self.execute(
            'yum install %s %s' % (yum_cmd, ' '.join(packages))
        )


    def yum_remove(self, packages):
        self._connected()
        return self.execute('yum erase -y %s' % ' '.join(packages))


    def rpm_install(self, filepath):
        self._connected()
        return self.execute('rpm -U %s' % filepath)
