import os
import crypt
import random
import string
from datetime import datetime

_SHADOW_FILE = '/etc/shadow'
_SSH_DIR = '/etc/ssh'
_SALT_CHOICES = string.ascii_letters + string.digits

_HOSTS_CONTENT= """127.0.0.1    localhost
$(IP)   $(HOSTNAME).$(DOMAIN)   $(HOSTNAME)

# The following lines are desirable for IPv6 capable hosts
::1     localhost ip6-localhost ip6-loopback
fe00::0 ip6-localnet
ff00::0 ip6-mcastprefix
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
"""

class Conf:
    def __init__(self, host):
        self._host = host


    def set_hosts(self, ip, hostname, domain):
        try:
            with self._host.open('/etc/hosts', 'w') as fhandler:
                fhandler.write(_HOSTS_CONTENT.replace('$(IP)', ip)
                                             .replace('$(HOSTNAME)', hostname)
                                             .replace('$(DOMAIN)', domain))
            return [True, u'', u'']
        except OSError as err:
            return [False, u'', err]


    def set_password(self, username, password):
        # Hash password.
        salt = ''.join([random.choice(_SALT_CHOICES) for _ in range(0,8)])
        hashed_pwd = crypt.crypt(password, '$6$%s$' % salt)
        user_line = ':'.join((username, hashed_pwd,
                              str((datetime.today() - datetime(1970, 1, 1)).days),
                              '0', '99999', '7', '', '', ''))

        # Generate the new content of the shadow file.
        content = []
        in_file = False
        with self._host.open(_SHADOW_FILE) as fhandler:
            for line in fhandler.read().splitlines():
                line = line.decode()
                if line.split(':')[0] == username:
                    content.append(user_line)
                    in_file = True
                else:
                    content.append(line)
            if not in_file:
                content.append(user_line)

        # Write content to the file.
        try:
            with self._host.open(_SHADOW_FILE, 'w') as fhandler:
                fhandler.write(u'\n'.join(content))
            return [True, u'', u'']
        except OSError as err:
            return [False, u'', err]


    def gen_ssh_keys(self, algos=['rsa', 'dsa']):
        keys = [os.path.join(_SSH_DIR, filename)
                for filename in self._host.listdir(_SSH_DIR)
                if 'ssh_host_' in filename]

        for key in keys:
            status, stdout, stderr = self._host.remove(key)
            if not status:
                stderr = 'unable to remove old key (%s): %s' % (key, stderr)
                return [status, stdout, stderr]

        for algo in algos:
            keyfile = os.path.join(_SSH_DIR, 'ssh_host_%s_key'% algo)
            options = dict(N='""', t=algo, f=keyfile)
            status, stdout, stderr = self._host.execute('ssh-keygen', **options)
            if not status:
                stderr = 'unable to generate %s key: %s' % (algo.upper(), stderr)
                return [status, stdout, stderr]

        return [True, u'', u'']
