import sys
import unix
import types


def _get_date(value):
    from datetime import datetime
    return datetime.fromtimestamp(int(value))

_MAP = dict(permissions_human=dict(fmt='A'),
            blocks=dict(fmt='b', type=int),
            blksize=dict(fmt='B', type=int),
            selinux=dict(fmt='C'),
            devnum=dict(fmt='d', type=int),
            devnum_hex=dict(fmt='D'),
            raw_mode=dict(fmt='f'),
            filetype=dict(fmt='F'),
            groupid=dict(fmt='g', type=int),
            groupname=dict(fmt='G'),
            hardlinks=dict(fmt='h', type=int),
            inodes=dict(fmt='i', type=int),
            mountpoint=dict(fmt='m'),
            filename=dict(fmt='n'),
            quoted_filename=dict(fmt='N'),
            optimal_blksize=dict(fmt='o', type=int),
            size=dict(fmt='s', type=int),
            major=dict(fmt='t', type=int),
            minor=dict(fmt='T', type=int),
            userid=dict(fmt='u', type=int),
            username=dict(fmt='U'),
            btime=dict(fmt='W', type=_get_date),
            atime=dict(fmt='X', type=_get_date),
            mtime=dict(fmt='Y', type=_get_date),
            ctime=dict(fmt='Z', type=_get_date),
            fs_freeblocks_users=dict(fs=True, fmt='a'),
            fs_blocks=dict(fs=True, fmt='b', type=int),
            fs_filenodes=dict(fs=True, fmt='c', type=int),
            fs_freefilenodes=dict(fs=True, fmt='d', type=int),
            fs_freeblocks=dict(fs=True, fmt='f'),
            fs_id=dict(fs=True, fmt='i'),
            fs_maxfilelen=dict(fs=True, fmt='l', type=int),
            fs_name=dict(fs=True, fmt='n'),
            fs_blocksize=dict(fs=True, fmt='s', type=int))



class StatError(Exception):
    pass


class Stat(object):
    def __init__(self, host, filepath, follow_links=False):
        self._host = host
        self._filepath = unix.format_path(filepath)
        self._follow_links = follow_links


    def _execute(self, fmt, fs=False):
        cmd = ('stat', self._filepath)
        kwargs = dict(file_system=fs, dereference=self._follow_links)
        status, stdout, stderr = self._host.execute(*cmd, format=fmt, **kwargs)
        if not status:
            raise StatError(stderr)
        return stdout.strip()


    @property
    def permissions(self):
        return '%04d' % int(self._execute('%a'))


def _add_method(obj, method, conf):
    cast = conf.pop('type', None)
    fmt = '%%%s' % conf['fmt']

    def _execute_fmt(self):
        stdout = self._execute(fmt, fs=conf.get('fs', False))
        return cast(stdout) if cast else stdout

    setattr(obj, method, property(_execute_fmt))


for method, conf in _MAP.items():
    _add_method(Stat, method, conf)
