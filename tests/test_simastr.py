# -*- coding: utf-8 -*-

import unittest

import sima.lib.simastr


def fuzzystr(sta, stb):
    afz = sima.lib.simastr.SimaStr(sta)
    bfz = sima.lib.simastr.SimaStr(stb)
    return afz == bfz



class TestSequenceFunctions(unittest.TestCase):

    def test_fuzzystr(self):
        sima.lib.simastr.SimaStr.diafilter = False
        self.assertFalse(fuzzystr('eeee', 'éééé'))
        tests = [
                ('eeee', 'éééé', self.assertTrue),
                ('The Doors', 'Doors', self.assertTrue),
                ('Tigres Del Norte', 'Los Tigres Del Norte', self.assertTrue),
                (   'The Desert Sessions & PJ Harvey',
                    'Desert Sessions And PJ Harvey',
                    self.assertTrue
                    ),
                (   'Smells like teen spirit',
                    'Smells Like Teen Spirits (live)',
                    self.assertTrue
                    ),
                ]
        sima.lib.simastr.SimaStr.diafilter = True
        for sta, stb, assertfunc in tests:
            assertfunc(fuzzystr(sta, stb), '"{0}" == "{1}"'.format(sta, stb))

# vim: ai ts=4 sw=4 sts=4 expandtab
