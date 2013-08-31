# -*- coding: utf-8 -*-
from distutils.core import setup

setup(
    name='unix',
    version='0.1',
    author='François Ménabé',
    author_email='francois.menabe@gmail.com',
    packages=['unix', 'unix/linux'],
    license=open('LICENSE').read(),
    description='Manage Unix-like systems.',
    long_description=open('README.rst').read(),
    install_requires=[
        'paramiko',
        'pexpect'
    ],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: System Administrators',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Operating System :: Unix',
        'Topic :: System :: Systems Administration'
    ]
)
