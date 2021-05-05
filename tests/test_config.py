#!/usr/bin/env python3
# coding: utf-8

import unittest
import os

from unittest.mock import patch

from sima.utils.config import ConfMan, DIRNAME, CONF_FILE
# import set_logger to set TRACE_LEVEL_NUM
from sima.lib.logger import set_logger


class TestConfMan(unittest.TestCase):
    """For some tests we don't care about file access check, then to ensure
    checks are properly mocked run test forcing non existent locations:

    XDG_DATA_HOME=/non/existent/ XDG_HOME_CONFIG=/non/existent/ python3 -m unittest -vf tests/test_config.py
    """

    @patch('sima.utils.config.makedirs')
    @patch('sima.utils.config.chmod')
    @patch('sima.utils.config.ConfMan.control_facc')
    def test_XDG_var(self, *args):
        config_home = '/foo/bar'
        os.environ['XDG_CONFIG_HOME'] = config_home
        conf_file = os.path.join(config_home, DIRNAME, CONF_FILE)
        conf = ConfMan({})
        self.assertEqual(conf.conf_file, conf_file)
        data_home = '/bar/foo'
        os.environ['XDG_DATA_HOME'] = data_home
        var_dir = os.path.join(data_home, DIRNAME)
        conf = ConfMan({})
        self.assertEqual(conf.config['sima']['var_dir'], var_dir)

    @patch('sima.utils.config.isdir')
    @patch('sima.utils.config.ConfMan.control_facc')
    def test_default_locations(self, mock_isdir, *args):
        home = '/foo'
        mock_isdir.return_value = True
        os.environ.pop('XDG_CONFIG_HOME', None)
        os.environ.pop('XDG_DATA_HOME', None)
        os.environ['HOME'] = home
        conf = ConfMan({})
        # Test var dir construction
        constructed_var_dir = conf.config['sima']['var_dir']
        expected_var_dir = os.path.join(home, '.local', 'share', DIRNAME)
        self.assertEqual(constructed_var_dir, expected_var_dir)
        # Test config construction
        constructed_config_location = conf.conf_file
        expected_config = os.path.join(home, '.config', DIRNAME, CONF_FILE)
        self.assertEqual(constructed_config_location, expected_config)

    @patch('sima.utils.config.makedirs')
    @patch('sima.utils.config.chmod')
    @patch('sima.utils.config.ConfMan.control_facc')
    def test_MPD_env_var(self, *args):
        host = 'example.org'
        passwd = 's2cr34!'
        port = '6601'
        os.environ.pop('MPD_HOST', None)
        os.environ.pop('MPD_PORT', None)
        # Test defaults
        conf = ConfMan({})
        self.assertEqual(dict(conf.config['MPD']),
                         {'host': 'localhost', 'port': '6600'})
        # Test provided env. var.
        os.environ['MPD_HOST'] = host
        conf = ConfMan({})
        self.assertEqual(dict(conf.config['MPD']),
                         {'host': host, 'port': '6600'})
        os.environ['MPD_HOST'] = f'{passwd}@{host}'
        conf = ConfMan({})
        self.assertEqual(dict(conf.config['MPD']),
                         {'host': host,
                          'password': passwd,
                          'port': '6600'})
        # Test abstract unix socket support with password
        os.environ['MPD_HOST'] = f'{passwd}@@/{host}'
        conf = ConfMan({})
        self.assertEqual(dict(conf.config['MPD']),
                         {'host': f'@/{host}',
                          'password': passwd,
                          'port': '6600'})
        # Test abstract unix socket support only
        os.environ['MPD_HOST'] = f'@/{host}'
        conf = ConfMan({})
        self.assertEqual(dict(conf.config['MPD']),
                         {'host': f'@/{host}',
                          'port': '6600'})
        # Test port
        os.environ['MPD_PORT'] = f'{port}'
        conf = ConfMan({})
        self.assertEqual(conf.config['MPD']['port'], port)

    @patch('sima.utils.config.makedirs')
    @patch('sima.utils.config.chmod')
    @patch('sima.utils.config.ConfMan.control_facc')
    def test_config_origin_priority(self, *args):
        # cli provided host overrides env. var.
        os.environ['MPD_HOST'] = 'baz.foo'
        conf = ConfMan({'host': 'cli.host'})
        self.assertEqual(conf.config['MPD']['host'], 'cli.host')
        # cli provided abstract socket overrides env. var.
        conf = ConfMan({'host': '@/abstract'})
        self.assertEqual(conf.config['MPD']['host'], '@/abstract')
        # cli provided passord and abstract socket overrides env. var.
        conf = ConfMan({'host': 'pass!@@/abstract'})
        self.assertEqual(conf.config['MPD']['host'], '@/abstract')
        self.assertEqual(conf.config['MPD']['password'], 'pass!')

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab fileencoding=utf8
