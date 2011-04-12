#!/usr/bin/python

from distutils.core import setup

setup(
    version="0.0.1",
    name='samba-gtk',
    packages=[
        'sambagtk',
    ],
    scripts=['bin/gtkldb', 'bin/gepdump'],
    maintainer='Jelmer Vernooij',
    maintainer_email='jelmer@samba.org',
)
