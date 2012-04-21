"""Module for managing host systems. He manage both localhost and remote hosts.
For connecting and executing commands on remote hosts, It use I{paramiko}
module which is a SSH/SFTP client in python.

The module is composed of three parts:
    - a class for managing localhost
    - a class for managing remote hosts
    - classes for most current operating systems based on packages type and
      package manager


Class for managing localhost
============================
The class is named B{Localhost}. This class has the two main methods I{execute}
and I{expect} that execute command in localhost, the first using B{subprocess}
module and the second using B{pexpect} module. I{expect} must be used when
an input is required (ex: passwd command).

Example of utilization:

>>> from unix.local import LocalHost
>>> localhost = Localhost()
>>> localhost.execute(('echo', '/etc/passwd'))
>>> localhost.expect(('passwd',), 'my_password', 2)


Class for managing remote hosts
===============================
The class is named B{Host} and contain notably:
    - a method for initialize object.
      This method to nothing except if an other B{Host} object is given. In this
      case the attributs (I{__dict__}) of the current object are copied from
      given object (it do a copy of the given host).
    - a method for connecting to the remote host.
      By default it use SSH keys of the user executing the script using the
      class but it is possible to indicate a password in parameter. In this
      case, for the commands needed a password (like I{scp}), the module
      I{pexpect} is used. There are some limitations for some commands!
    - a method I{execute} for executing command on the remote host.
      This method return a list of three elements:
        - I{status}: status of the command (False if return code
          different from 0 and True otherwise)
        - I{stdout}: the standard output
        - I{stderr}: the error output
      Others methods that executing commands are just wrapper to this method (
      ie: return the output of the I{execute} command with a predefined
      command).
    - methods for copy process. The are three possibility:
        - copy from the local host on the remote host
        - copy in the remote host filesystem
        - copy from the remote to an other remote host
      When copy from local host, there are three possibility:
        - using SFTP paramiko methods. This is used by default but can
          only copy files.
          TODO: copy directory with a recursive method
        - using I{scp} command
        - using I{reloadtar} command:
          tar czf - -C I{source} | ssh I{user}@I{host} tar xvf - -C I{dest}
    - methods for read/write/replace content in files.

Exemple of utilization:

>>> from unix.remote import RemoteHost
>>> host = RemoteHost()
>>> host.connect('example.com', 'root')
>>> host.execute('ls /')

Classes for managing Operating systems
======================================
There are two classes for the systems based on:
    - deb packages and APT package manager
    - rpm packages and YUM package manager
Theses classes herits from B{Host} and methods, like methods in B{Host}, are
only wrappers.
"""
