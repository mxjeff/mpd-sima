#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import glob

from setuptools import setup, find_packages  # >= 2.0.2
from os import listdir
from os.path import isfile, isdir

from sima.info import __version__ as VERSION, __author__ as AUTHOR
from sima.info import __doc__ as DESCRIPTION, __email__ as EMAIL

data_files = [
    ('share/man/man1', ['data/man/mpd-sima.1', 'data/man/simadb_cli.1',]),
    ('share/man/man5', ['data/man/mpd_sima.cfg.5',]),
    ('share/doc/mpd-sima/examples/', glob.glob('doc/examples/*')),
    ('share/doc/mpd-sima/', [fi for fi in listdir('doc') if isfile(fi)]),
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
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        ]

setup(name='MPD_sima',
      version=VERSION,
      download_url='http://media.kaliko.me/src/sima/releases/',
      url='http://kaliko.me/code/mpd-sima',
      description='Automagically add titles to MPD playlist',
      author=AUTHOR,
      author_email= EMAIL,
      license='GPLv3',
      keywords='MPD',
      long_description=DESCRIPTION,
      classifiers=classifiers,
      install_requires=['python-musicpd>=0.4.1', 'requests>= 2.4.0'],
      packages=find_packages(exclude=["tests"]),
      include_package_data=True,
      data_files=data_files,
      scripts=['simadb_cli'],
      entry_points={
          'console_scripts': ['mpd-sima = sima.launch:main',]
          },
      test_suite="tests",
)

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
