import re
from unix.sizes import kb2b

_MEMINFO = '/proc/meminfo'

_PARAM_RE = re.compile('(([a-zA-Z0-9_]*)(\((\w*)\))?):\s+(\d*)(.*)?')

class Memory(object):
    def __init__(self, host):
        self._host = host

        with self._host.open(_MEMINFO) as fhandler:
            for line in fhandler.read().splitlines():
                regex = _PARAM_RE.search(line.decode()).groups()
                param = regex[1].lower()
                if regex[3]:
                    param = '%s_%s' % (param, regex[3])
                if param.startswith('mem'):
                    param = param[3:]

                value = kb2b(regex[4], si=True) if regex[5] else regex[4]
                setattr(self, param, value)
