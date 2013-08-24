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

Code is available on Github (http://github.com/fmenabe/python-clg)

Releases notes
--------------
0.1
~~~
    * First import
