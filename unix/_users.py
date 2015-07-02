# /etc/passwd fields.
_PASSWD_FIELDS = ('login', 'password', 'uid', 'gid', 'name', 'home', 'shell')#

class Users(object):
    def __init__(self, host):
        self._host = host


    def list(self, verbose=False):
        with self._host.set_controls(decode='utf-8'):
            status, stdout, stderr = self._host.execute('getent', 'passwd')
        if not status:
            raise UnixError(stderr)
        return [dict(zip(_PASSWD_FIELDS, user.split(':')))['login']
                for user in stdout.splitlines()]


    def get(self, uid):
        with self._host.set_controls(decode='utf-8'):
            status, stdout, stderr = self._host.execute('getent', 'passwd', uid)
        if not status:
            raise UnixError(stderr)
        return dict(zip(_PASSWD_FIELDS, stdout.splitlines()[0].split(':')))


    def uid(self, username):
        return self.get(username)['uid']


    def username(self, uid):
        return self.get(uid)['login']


    def groups(self, username):
        with self._host.set_controls(decode='utf-8'):
            status, stdout, stderr = self._host.execute('id', G=username)
        if not status:
            raise UnixError(stderr)
        return [int(gid) for gid in stdout.split()]


    def add(self, user, **kwargs):
#        self._host.isroot('useradd')
        return self._host.execute('useradd', user, **kwargs)


    def delete(self, user, **kwargs):
#        self._host.isroot('userdel')
        return self._host.execute('userdel', user, **kwargs)


    def update(self, user, **kwargs):
#        self._host.isroot('usermod')
        return self._host.execute('usermod', user, **kwargs)
