import os.path as path


class Sysctl(object):
    def __init__(self, host):
        self._host = host

    def list(self):
        params = self._host.execute('sysctl', all=True)[1]
        for line in params.splitlines():
            param, value = line.split(' = ')
            yield (param, int(value) if value.isdigit() else value)

    def get(self, param):
        value = self._host.execute('sysctl', param, binary=True)[1]
        return int(value) if value.isdigit() else value

    def set(self, param, value):
        return self._host.execute('sysctl', '%s=%s' % (param, value), write=True)

    def write(self, config, filename=None):
        if not filename.endswith('.conf'):
            return [False, '', "file extension must be '.conf'"]
        filepath = (path.join('/etc/sysctl.d/%s' % filename)
                    if filename
                    else'/etc/sysctl.conf')
        with self._host.open(filepath, 'w') as fhandler:
            fhandler.write('\n'.join('%s = %s' % (param, value)
                                     for param, value in config.items()))
        return self._host.execute('sysctl', p=filepath)

    def read(self, filename=None):
        filepath = (path.join('/etc/sysctl.d/%s' % filename)
                    if filename
                    else'/etc/sysctl.conf')
        with self._host.open(filepath) as fhandler:
            return {param.strip(): value.strip()
                    for line in fhandler.read().splitlines()
                    if line and not line.startswith('#')
                    for param, value in [line.split('=')]}
