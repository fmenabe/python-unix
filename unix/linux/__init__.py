# -*- coding: utf-8 -*-

import os
import unix
import os.path as path


#
# Exceptions.
#
class LinuxError(Exception):
    pass


#
# Base class for managing linux hosts.
#
def Linux(host):
    unix.isvalid(host)
    host.is_connected()

    instances = unix.instances(host)
    if len(instances) > 1:
        host = getattr(unix, instances[0]).clone(host)

    host_type = host.type
    if host_type != 'linux':
        raise LinuxError('this is not a Linux host (%s)' % host_type)


    class LinuxHost(host.__class__):
        def __init__(self):
            host.__class__.__init__(self)
            self.__dict__.update(host.__dict__)

    return LinuxHost(root)
