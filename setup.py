#!/usr/bin/python

from distutils.core import setup

setup(
    version="0.0.1",
    name='samba-gtk',
    packages=[
        'sambagtk',
    ],
    scripts=['bin/gtkldb', 'bin/gepdump', 'bin/gregedit'],
    maintainer='Jelmer Vernooij',
    maintainer_email='jelmer@samba.org',
    data_files=[ ('share/applications', ['meta/gepdump.desktop',
                                         'meta/gregedit.desktop',
                                         'meta/gtkldb.desktop',
                                         'meta/gwcrontab.desktop',
                                         'meta/gwsam.desktop',
                                         'meta/gwsvcctl.desktop']) ]
    )
