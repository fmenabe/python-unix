_FIELDS = ('spec', 'file', 'mntopts', 'freq', 'passno')

class Fstab:
    def __init__(self, host):
        self._host = host

    def list(self, filepath='/etc/fstab'):
        with self.open(filepath) as fhandler:
            return [zip(_FIELDS, elts)
                    for line in fhandler.read().splitlines()
                    if line and not line.decode().startswith('#')
                    for elts in [line.decode().split()]]

    def add(self, config, filepath='/etc/fstab'):
        with self._host.open(filepath, 'a') as fhandler:
            fhandler.write('    '.join(map(str, config)) + '\n')

    def delete(self, spec, filepath='/etc/fstab'):
        content = []
        with self._host.open(filepath) as fhandler:
            line = line.decode()
            if not line or line.startswith('#'):
                content.append(line)
            else:
                line.split()
