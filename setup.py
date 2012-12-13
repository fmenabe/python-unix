# -*- coding: utf-8 -*-
from distutils.core import setup

setup(
    name='Unix System Manager',
    version='0.1',
    author='François Ménabé',
    author_email='francois.menabe@gmail.com',
    packages=['unix', 'unix/linux'],
    licence='LICENCE.txt',
    description='Manage (execute command, read/write files, ...) on local or remote Unix systems via SSH.',
    long_description=open('README.txt').read(),
    install_requires=[
        'paramiko',
        'pexpect'
    ]
)
