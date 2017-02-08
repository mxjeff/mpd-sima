#!/usr/bin/env python3
# Copyright (C) 2013 Vinay Sajip. New BSD License.
# Copyright (C) 2014 Kaliko Jack
#
from __future__ import print_function

REQ_VER = (3,3)
import sys
if sys.version_info < REQ_VER:
    print('Need at least python {0}.{1} to run this script'.format(*REQ_VER), file=sys.stderr)
    sys.exit(1)

import os
import os.path
import venv

from subprocess import Popen, PIPE
from threading import Thread
from urllib.parse import urlparse
from urllib.request import urlretrieve
from shutil import rmtree

class ExtendedEnvBuilder(venv.EnvBuilder):
    """
    This builder installs setuptools and pip so that you can pip or
    easy_install other packages into the created environment.
    """

    def __init__(self, *args, **kwargs):
        self.verbose = kwargs.pop('verbose', False)
        super().__init__(*args, **kwargs)

    def post_setup(self, context):
        """
        Set up any packages which need to be pre-installed into the
        environment being created.

        :param context: The information for the environment creation request
                        being processed.
        """
        os.environ['VIRTUAL_ENV'] = context.env_dir
        self.install_setuptools(context)
        self.install_pip(context)
        setup = os.path.abspath(os.path.join(context.env_dir, '../setup.py'))
        self.install_script(context, 'sima', setup=setup)

    def reader(self, stream, context):
        """
        Read lines from a subprocess' output stream and write progress
        information to sys.stderr.
        """
        while True:
            s = stream.readline()
            if not s:
                break
            if not self.verbose:
                sys.stderr.write('.')
            else:
                sys.stderr.write(s.decode('utf-8'))
            sys.stderr.flush()
        stream.close()

    def install_script(self, context, name, url=None, setup=None):
        if url:
            binpath = context.bin_path
            _, _, path, _, _, _ = urlparse(url)
            fn = os.path.split(path)[-1]
            distpath = os.path.join(binpath, fn)
            # Download script into the env's binaries folder
            urlretrieve(url, distpath)
        if url:
            args = [context.env_exe, fn]
        else:
            args = [context.env_exe, setup, 'install']
            binpath = os.path.dirname(setup)
        if self.verbose:
            term = '\n'
        else:
            term = ''
        sys.stderr.write('Installing %s ...%s' % (name, term))
        sys.stderr.flush()
        # Install in the env
        p = Popen(args, stdout=PIPE, stderr=PIPE, cwd=binpath)
        t1 = Thread(target=self.reader, args=(p.stdout, 'stdout'))
        t1.start()
        t2 = Thread(target=self.reader, args=(p.stderr, 'stderr'))
        t2.start()
        p.wait()
        t1.join()
        t2.join()
        sys.stderr.write('done.\n')
        if url:
            # Clean up - no longer needed
            os.unlink(distpath)

    def install_setuptools(self, context):
        """
        Install setuptools in the environment.

        :param context: The information for the environment creation request
                        being processed.
        """
        url = 'https://bitbucket.org/pypa/setuptools/downloads/ez_setup.py'
        self.install_script(context, 'setuptools', url)
        # clear up the setuptools archive which gets downloaded
        pred = lambda o: o.startswith('setuptools-') and o.endswith('.tar.gz')
        files = filter(pred, os.listdir(context.bin_path))
        for f in files:
            f = os.path.join(context.bin_path, f)
            os.unlink(f)

    def install_pip(self, context):
        """
        Install pip in the environment.

        :param context: The information for the environment creation request
                        being processed.
        """
        url = 'https://bootstrap.pypa.io/get-pip.py'
        self.install_script(context, 'pip', url)
        # pip installs to "local/bin" on Linux, but it needs to be accessible
        # from "bin" since the "activate" script prepends "bin" to $PATH
        pip_path = os.path.join(context.env_dir, 'local', 'bin', 'pip')
        if sys.platform != 'win32' and os.path.exists(pip_path):
            self.symlink_or_copy(pip_path, os.path.join(context.bin_path, 'pip'))


def main(args=None):
    root = os.path.dirname(os.path.abspath(__file__))
    vdir = os.path.join(root, 'venv')
    builder = ExtendedEnvBuilder(clear=True, verbose=False)
    builder.create(vdir)
    # clean up
    for residu in ['MPD_sima.egg-info', 'dist', 'build']:
        if os.path.exists(os.path.join(root, residu)):
            rmtree(os.path.join(root, residu))
    # Write wrapper
    with open(os.path.join(root, 'vmpd-sima'),'w') as fd:
        fd.write('#!/bin/sh\n')
        fd.write('. "{}/venv/bin/activate"\n'.format(root))
        fd.write('"{}/venv/bin/mpd-sima" "$@"'.format(root))
    os.chmod(os.path.join(root, 'vmpd-sima'), 0o744)

if __name__ == '__main__':
    rc = 1
    try:
        main()
        rc = 0
    except ImportError as e:
        print('Error: %s' % e)
    sys.exit(rc)
