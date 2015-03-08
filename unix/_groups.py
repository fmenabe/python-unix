# /etc/group fields.
_GROUP_FIELDS = ('name', 'password', 'gid', 'users')

class Groups(object):
    def __init__(self, host):
        self._host = host


    def list(self, verbose=False):
        with self._host.set_controls(decode='utf-8'):
            status, stdout, stderr = self._host.execute('getent', 'passwd')
        if not status:
            raise UnixError(stderr)
        return [dict(zip(_GROUP_FIELDS, group.split(':')))['name']
                for group in stdout.splitlines()]


    def get(self, gid):
        with self._host.set_controls(decode='utf-8'):
            status, stdout, stderr = self._host.execute('getent', 'group', gid)
        if not status:
            raise UnixError(stderr)
        return dict(zip(_GROUP_FIELDS, stdout.splitlines()[0].split(':')))


    def gid(self, groupname):
        return self.get(groupname)['gid']


    def groupname(self, gid):
        return self.get(gid)['name']


    def add(self, group, **kwargs):
        return self._host.execute('groupadd', group, **kwargs)


    def delete(self, group):
        return self._host.execute('groupdel', group)


    def update(self, group, **kwargs):
        return self._host.execute('groupmod', group, **kwargs)


    def users(self, groupname):
        for group in self.list():
            if group['name'] == groupname:
                return group['users']
