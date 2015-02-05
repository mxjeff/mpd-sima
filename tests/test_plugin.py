# -*- coding: utf-8 -*-

import unittest
import configparser

from unittest.mock import Mock

import sima.lib.plugin

class SomePlugin(sima.lib.plugin.Plugin):

    def __init__(self, daemon):
        sima.lib.plugin.Plugin.__init__(self, daemon)


class TestFileAccessControl(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_plugin_conf_discovery(self):
        config = configparser.ConfigParser()
        default = {'priority': '42', 'option': 'value'}
        config.read_dict({'someplugin': default})
        daemon = Mock(config=config)
        plugin = SomePlugin(daemon)
        self.assertEqual(dict(plugin.plugin_conf), default)

    def test_plugin_default_priority(self):
        config = configparser.ConfigParser()
        default = {'option': 'value'}
        config.read_dict({'someplugin': default})
        daemon = Mock(config=config)
        plugin = SomePlugin(daemon)
        self.assertEqual(plugin.plugin_conf.get('priority'), '80')
        self.assertEqual(plugin.plugin_conf.get('option'), default.get('option'))

        config = configparser.ConfigParser()
        config.read_dict({})
        daemon = Mock(config=config)
        plugin = SomePlugin(daemon)
        self.assertEqual(plugin.plugin_conf.get('priority'), '80')


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
