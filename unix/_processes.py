#
# Class for managing process.
#
class Processes(object):
    def __init__(self, host):
        self._host = host


    def kill(self, pid, signal=15):
        return self._host.execute('kill', pid, s=signal)
