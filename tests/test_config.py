#!/usr/bin/env python3
# coding: utf-8

import unittest
import os

from unittest.mock import patch

from sima.utils.config import ConfMan, DIRNAME, CONF_FILE
# import set_logger to set TRACE_LEVEL_NUM
from sima.lib.logger import set_logger


class TestConfMan(unittest.TestCase):

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

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab fileencoding=utf8
