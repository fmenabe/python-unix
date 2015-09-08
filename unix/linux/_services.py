class Service(object):
    def __init__(self, host):
        self._host = host

    def start(self, service):
        return self.do(service, 'start')

    def stop(self, service):
        return self.do(service, 'stop')

    def restart(self, service):
        return self.do(service, 'restart')

    def status(self, service):
        return self.do(service, 'status')


class Upstart(Service):
    def __init__(self, host):
        Service.__init__(self, host)

    def do(self, service, action):
        return self._host.execute('service', service, action)


class Systemd(Service):
    def __init__(self, host):
        Service.__init__(self, host)

    def do(self, service, action):
        return self._host.execute('systemctl', action, service)


class Initd(Service):
    def __init__(self, host):
        Service.__init__(self, host)

    def do(self, service, action):
        return self._host.execute('/etc/init.d/%s' % service, action)
