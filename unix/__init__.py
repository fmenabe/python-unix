from unix.host import Local, Remote, ConnectError
import unix.linux as linux

def instances(host):
    """Return list of class names on which the *host* inherit.

    ::
        >>> import unix
        >>> host = unix.linux.Deb(unix.Remote())
        >>> host.connect('myhost.mydomain')
        >>> unix.instance(host)
        >>> # ['DebHost', 'LinuxHost', 'Remote', object]
    """
    return [elt.__name__ for elt in host.__class__.mro()]


def ishost(host, value):
    """Return *True* if *value* is in the tree of instances of the *host*."""
    return True if value in instances(host) else False


def isvalid(host):
    """Return *True* if *Local* or *Remote* is in the tree of instances of the
    *host* (ie: this is a local or a remote host initialized by the respectives
    classes."""
    if not ishost(host, 'Local') and not ishost(host, 'Remote'):
        raise ValueError("this is not a 'Local' or a 'Remote' host")
