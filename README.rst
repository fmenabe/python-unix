Package for managing Unix hosts
===============================

This module aims to manage Unix-likes operating systems. It manage both local or
remote host in the same way. Commands can be executed interactively or not, and
the result is a list of three elements:

    * the status of the command (boolean based on return code)
    * the standard output (stdout)
    * the error output (stderr)

For executed commands on localhost, the module used is ``subprocess`` and for
remotes hosts, the module used is ``paramiko``.

Code is available on Github (http://github.com/fmenabe/python-unix)

Releases notes
--------------
1.0 (2015-07-02)
~~~~~~~~~~~~~~~~
    * Manage localhost (subprocess) and remote hosts (SSH; paramiko) uniformly.
    * Use controls for managing some behaviour (decoding outputs, locale, ...).
    * Implements basic commands for manipulating files and directories (``open``, ``copy``, ``mkdir``, ...).
    * Organize commands in objects accessible via properties:
        * path API (``exists``, ``isfile``, ...)
        * remote API for copying file using from one host to another
        * users and groups API
    * Manage Linux hosts:
        * chroot
        * autodetecting the distribution
        * manage arch, debian, ubuntu, redhat, centos, ...

0.1 (2015-03-05)
~~~~~~~~~~~~~~~~
    * Initial version.
