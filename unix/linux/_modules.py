class Modules(object):
    def __init__(self, host):
        self._host = host

    def list(self):
        status, stdout, stderr = self._host.execute('lsmod')
        if not status:
            raise LinuxError(stderr)
        return [line.split()[0] for line in stdout.splitlines()[1:]]

    def tree(self):
        pass

    def loaded(self, module):
        return module in self.list()

    def load(self, module, force=False, **params):
        return self._host.execute('modprobe', module,
                                  ' '.join('%s=%s' % (param, value)
                                           for param, value in params.items()),
                                  force=force)

    def unload(self, module, force=False):
        return self._host.execute('modprobe', module, remove=True, force=force)

    def options(self, module):
        pass
