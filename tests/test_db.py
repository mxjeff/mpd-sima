# coding: utf-8

import unittest
import os
import datetime

from sima.lib.db import SimaDB
from sima.lib.track import Track


DEVOLT = {
  'album': 'Grey',
  'albumartist': 'Devolt',
  'albumartistsort': 'Devolt',
  'artist': 'Devolt',
  'date': '2011-12-01',
  'disc': '1/1',
  'file': 'music/Devolt/2011-Grey/03-Devolt - Crazy.mp3',
  'last-modified': '2012-04-02T20:48:59Z',
  'musicbrainz_albumartistid': 'd8e7e3e2-49ab-4f7c-b148-fc946d521f99',
  'musicbrainz_albumid': 'ea2ef2cf-59e1-443a-817e-9066e3e0be4b',
  'musicbrainz_artistid': 'd8e7e3e2-49ab-4f7c-b148-fc946d521f99',
  'musicbrainz_trackid': 'fabf8fc9-2ae5-49c9-8214-a839c958d872',
  'time': '220',
  'duration': '220.000',
  'title': 'Crazy',
  'track': '3/6'}


class Main_TestDB(unittest.TestCase):
    db_file = 'file::memory:?cache=shared'
    #db_file = '/dev/shm/unittest.sqlite'

    @classmethod
    def setUpClass(self):
        self.db = SimaDB(db_path=self.db_file)
        # Maintain a connection to keep the database between test cases
        self.conn = self.db.get_database_connection()

    @classmethod
    def tearDownClass(self):
        self.conn.close()


class TestDB(Main_TestDB):

    def test_00_recreation(self):
        self.db.create_db()

    def test_01_add_track(self):
        trk = Track(**DEVOLT)
        trk_id = self.db.get_track(trk)
        self.assertEqual(trk_id, self.db.get_track(trk),
                         'Same track, same record')

    def test_02_history(self):
        curr = datetime.datetime.utcnow()
        # set records in the past to ease purging then
        last = curr - datetime.timedelta(hours=1)
        trk = Track(**DEVOLT)
        self.db.add_history(trk, date=last)
        self.db.add_history(trk, date=last)
        hist = self.db.get_history()
        self.assertEqual(len(hist), 1, 'same track results in a single record')

        trk_foo = Track(file="/foo/bar/baz.flac")
        self.db.add_history(trk_foo, date=last)
        hist = self.db.get_history()
        self.assertEqual(len(hist), 2)

        self.db.add_history(trk, date=last)
        hist = self.db.get_history()
        self.assertEqual(len(hist), 2)
        self.db.purge_history(duration=0)
        hist = self.db.get_history()
        self.assertEqual(len(hist), 0)

        # Controls we got history in the right order
        # recent first, oldest last
        hist = list()
        for i in range(1, 5):  # starts at 1 to ensure records are in the past
            trk = Track(file=f'/foo/bar.{i}', name='{i}-baz', album='foolbum')
            hist.append(trk)
            last = curr - datetime.timedelta(minutes=i)
            self.db.add_history(trk, date=last)
        hist_records = self.db.get_history()
        self.assertEqual(hist, hist_records)
        self.db.purge_history(duration=0)

    def test_04_triggers(self):
        self.db.purge_history(duration=0)
        curr = datetime.datetime.utcnow()
        tracks_ids = list()
        # Set 4 records, same album
        for i in range(1, 6):  # starts at 1 to ensure records are in the past
            trk = Track(file=f'/foo/{i}', name=f'{i}', artist='fooart',
                        albumartist='fooalbart', album='foolbum',)
            tracks_ids.append(self.db.get_track(trk))  # Add track, save its DB id
            # set records in the past to ease purging then
            last = curr - datetime.timedelta(minutes=i)
            self.db.add_history(trk, date=last)  # Add to history
        conn = self.db.get_database_connection()
        #  Add another track not related (not same album)
        track = Track(file='/baz/bar.baz', name='baz', artist='fooart',
                      albumartist='not-same', album='not-same',)
        self.db.get_track(track)
        # for tid in tracks_ids:
        for tid in tracks_ids[:-1]:
            # Delete lastest record
            conn.execute('DELETE FROM history WHERE history.track = ?', (tid,))
            c = conn.execute('SELECT albums.name FROM albums;')
            # There are still albums records (still a history using it)
            self.assertIn((trk.album,), c.fetchall())
        # purging last entry in history or album == trk.album
        c.execute('DELETE FROM history WHERE history.track = ?',
                  (tracks_ids[-1],))
        # triggers purge other tables if possible
        c.execute('SELECT albums.name FROM albums;')
        albums = c.fetchall()
        self.assertNotIn(('foolbum',), albums)
        conn.close()


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab fileencoding=utf8
