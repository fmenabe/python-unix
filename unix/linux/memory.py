import re
from unix.sizes import kb2b

_MEMINFO = '/proc/meminfo'

_PARAM_RE = re.compile(r'^(?P<param>[a-zA-Z0-9_]*)(\((?P<anon>\w*)\))?:'
                        '\s+(?P<value>\d*)(\s+(?P<unit>\w*))?$')

class Memory(object):
    def __init__(self, host):
        self._host = host

        with self._host.open(_MEMINFO) as fhandler:
            for line in fhandler.read().splitlines():
                regex = _PARAM_RE.search(line.decode()).groupdict()
                param = regex['param'].lower()
                if param.startswith('mem'):
                    param = param[3:]
                if regex['anon']:
                    param = '%s_%s' % (param, regex['anon'])

                value = kb2b(regex['value'], si=True) if regex['unit'] else regex['value']
                setattr(self, param, value)
