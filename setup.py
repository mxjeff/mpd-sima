#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import glob

from setuptools import setup
#from distutils.core import setup
from os import listdir
from os.path import isfile, isdir

from sima.core import __version__ as VERSION

DESCRIPTION = """
sima is a Python application meant to feed your MPD playlist with tracks
from artists similar to your currently playing track, provided that these
artists are found in MPD library. Similar artists are fetched from last.fm.

sima can queue track, top track or whole album for similar artists.

This client allows you to never run out of music when your playlist
queue is getting short.
"""

data_files = [
    #('share/man/man1', ['data/mpd-sima.1', 'data/simadb_cli.1',]),
    #('share/man/man5', ['data/mpd-sima.cfg.5',]),
    #('share/doc/mpd-sima/examples/', glob.glob('doc/examples/*')),
    #('share/doc/mpd-sima/', [fi for fi in listdir('doc') if isfile(fi)]),
]
classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Environment :: No Input/Output (Daemon)",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: POSIX",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Utilities",
        "Programming Language :: Python :: 3",
        ]

setup(name='sima',
      version=VERSION,
      download_url='http://codingteam.net/project/sima/download',
      url='http://codingteam.net/project/sima',
      description='Automagically add titles to MPD playlist',
      author='Jack Kaliko',
      author_email='Jack Kaliko <kaliko@azylum.org>',
      license='GPLv3',
      keywords='MPD',
      long_description=DESCRIPTION,
      classifiers=classifiers,
      install_requires=['distribute', 'python-musicpd'],
      packages=['sima','sima.lib', 'sima.utils',
                'sima.plugins.core',
                'sima.plugins.internal',
                'sima.plugins.contrib'],
      include_package_data=True,
      data_files=data_files,
      scripts=['launch'],
      entry_points={
          'console_scripts': ['sima = launch:mainc',]
          },
)

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
