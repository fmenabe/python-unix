from unix.host import Local, Remote, ConnectError

def instances(host):
    return [elt.__name__ for elt in host.__class__.mro()]


def ishost(host, value):
    return True if value in instances(host) else False
