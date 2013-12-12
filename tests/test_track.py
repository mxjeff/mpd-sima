# -*- coding: utf-8 -*-

import unittest

from sima.lib.track import Track

DEVOLT = {
  'album': 'Grey',
  'albumartist': ['Devolt', 'Devolt Band'],
  'albumartistsort': 'Devolt',
  'artist': 'Devolt',
  'date': '2011-12-01',
  'disc': '1/1',
  'file': 'gberret.music/Devolt/2011-Grey/03-Devolt - Crazy.mp3',
  'last-modified': '2012-04-02T20:48:59Z',
  'musicbrainz_albumartistid': 'd8e7e3e2-49ab-4f7c-b148-fc946d521f99',
  'musicbrainz_albumid': 'ea2ef2cf-59e1-443a-817e-9066e3e0be4b',
  'musicbrainz_artistid': 'd8e7e3e2-49ab-4f7c-b148-fc946d521f99',
  'musicbrainz_trackid': 'fabf8fc9-2ae5-49c9-8214-a839c958d872',
  'time': '220',
  'title': 'Crazy',
  'track': '3/6'}


class TestTrackObject(unittest.TestCase):

    def test_tagcollapse(self):
        trk = Track(**DEVOLT)
        self.assertTrue(trk.collapse_tags_bool, 'Should have collapsed a tag')
        self.assertFalse(isinstance(trk.albumartist, list), 'Failed to collapse albumartist tag')

    def test_boolean_type(self):
        self.assertFalse(bool(Track()))

# vim: ai ts=4 sw=4 sts=4 expandtab
