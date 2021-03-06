# coding: utf-8

import datetime
import unittest
import os

from sima.lib.simadb import SimaDB
from sima.lib.track import Track
from sima.lib.meta import Album, Artist, MetaContainer


DEVOLT = {
    'album': 'Grey',
    'albumartist': 'Devolt',
    'albumartistsort': 'Devolt',
    'artist': 'Devolt',
    'genre': ['Rock'],
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

DB_FILE = 'file::memory:?cache=shared'
KEEP_FILE = True  # File db in file to ease debug
if KEEP_FILE:
    DB_FILE = '/dev/shm/unittest.sqlite'
CURRENT = datetime.datetime.utcnow()
IN_THE_PAST = CURRENT - datetime.timedelta(hours=1)


class Main(unittest.TestCase):
    """Deal with database creation and purge between tests"""

    @classmethod
    def setUpClass(self):
        self.db = SimaDB(db_path=DB_FILE)

    def setUp(self):
        # Maintain a connection to keep the database (when stored in memory)
        self.conn = self.db.get_database_connection()
        self.db.drop_all()
        self.db.create_db()

    def tearDown(self):
        if not KEEP_FILE:
            self.db.drop_all()
        self.conn.close()

    @classmethod
    def tearDownClass(self):
        if KEEP_FILE:
            return
        if os.path.isfile(DB_FILE):
            os.unlink(DB_FILE)


class Test_00DB(Main):

    def test_00_recreation(self):
        self.db.create_db()

    def test_01_add_track(self):
        trk = Track(**DEVOLT)
        trk_id = self.db.get_track(trk)
        self.assertEqual(trk_id, self.db.get_track(trk, add=False),
                         'Same track, same record')

    def test_02_history(self):
        # set records in the past to ease purging then
        last = CURRENT - datetime.timedelta(seconds=5)
        trk = Track(**DEVOLT)
        self.db.add_history(trk, date=last)
        self.db.add_history(trk, date=last)
        hist = self.db.fetch_history()
        self.assertEqual(len(hist), 1, 'same track results in a single record')

        trk_foo = Track(file="/foo/bar/baz.flac")
        self.db.add_history(trk_foo, date=last)
        hist = self.db.fetch_history()
        self.assertEqual(len(hist), 2)

        self.db.add_history(trk, date=last)
        hist = self.db.fetch_history()
        self.assertEqual(len(hist), 2)
        self.db.purge_history(duration=0)
        hist = self.db.fetch_history()
        self.assertEqual(len(hist), 0)

        # Controls we got history in the right order
        # recent first, oldest last
        hist = list()
        for i in range(1, 5):  # starts at 1 to ensure records are in the past
            trk = Track(file=f'/foo/bar.{i}', name=f'{i}-baz',
                        album='foolbum', genre=f'{i}')
            hist.append(trk)
            last = CURRENT - datetime.timedelta(minutes=i)
            self.db.add_history(trk, date=last)
        hist_records = self.db.fetch_history()
        self.assertEqual(hist, hist_records)
        self.db.purge_history(duration=0)

    def test_history_to_tracks(self):
        tr = dict(**DEVOLT)
        tr.pop('file')
        trk01 = Track(file='01', **tr)
        self.db.add_history(trk01, CURRENT-datetime.timedelta(minutes=1))
        #
        tr.pop('musicbrainz_artistid')
        trk02 = Track(file='02', **tr)
        self.db.add_history(trk02, CURRENT-datetime.timedelta(minutes=2))
        #
        tr.pop('musicbrainz_albumid')
        trk03 = Track(file='03', **tr)
        self.db.add_history(trk03, CURRENT-datetime.timedelta(minutes=3))
        #
        tr.pop('musicbrainz_albumartistid')
        trk04 = Track(file='04', **tr)
        self.db.add_history(trk04, CURRENT-datetime.timedelta(minutes=4))
        #
        tr.pop('musicbrainz_trackid')
        trk05 = Track(file='05', **tr)
        self.db.add_history(trk05, CURRENT-datetime.timedelta(minutes=5))
        history = self.db.fetch_history()
        self.assertEqual(len(history), 5)
        # Controls history ordering, recent first
        self.assertEqual(history, [trk01, trk02, trk03, trk04, trk05])

    def test_history_to_artists(self):
        tr = dict(**DEVOLT)
        tr.pop('file')
        tr.pop('musicbrainz_artistid')
        #
        trk01 = Track(file='01', **tr)
        self.db.add_history(trk01, CURRENT-datetime.timedelta(hours=1))
        #
        trk02 = Track(file='02', **tr)
        self.db.add_history(trk02, CURRENT-datetime.timedelta(hours=1))
        self.db.add_history(trk02, CURRENT-datetime.timedelta(hours=1))
        #
        trk03 = Track(file='03', **tr)
        self.db.add_history(trk03, CURRENT-datetime.timedelta(hours=1))
        # got multiple tracks, same artist/album, got artist/album history len = 1
        art_history = self.db.fetch_artists_history()
        alb_history = self.db.fetch_albums_history()
        self.assertEqual(len(art_history), 1)
        self.assertEqual(len(alb_history), 1)
        self.assertEqual(art_history, [trk01.Artist])

        # Now add new artist to history
        trk04 = Track(file='04', artist='New Art')
        trk05 = Track(file='05', artist='New² Art')
        self.db.add_history(trk04, CURRENT-datetime.timedelta(minutes=3))
        self.db.add_history(trk03, CURRENT-datetime.timedelta(minutes=2))
        self.db.add_history(trk05, CURRENT-datetime.timedelta(minutes=1))
        art_history = self.db.fetch_artists_history()
        # Now we should have 4 artists in history
        self.assertEqual(len(art_history), 4)
        # Controling order, recent first
        self.assertEqual([trk05.artist, trk03.artist,
                         trk04.artist, trk03.artist],
                         art_history)

    def test_albums_history(self):
        # set records in the past to ease purging then
        last = CURRENT - datetime.timedelta(seconds=5)
        track = {
            'album': 'album', 'title': 'title',
            'albumartist': 'albumartist',
            'artist': 'artist',
            'file': 'foo/bar.flac',
            'musicbrainz_albumartistid': 'd8e7e3e2-49ab-4f7c-b148-fc946d521f99',
            'musicbrainz_albumid': 'ea2ef2cf-59e1-443a-817e-9066e3e0be4b',
            'musicbrainz_artistid': 'd8e7e3e2-49ab-4f7c-b148-fc946d521f99',}
        self.db.purge_history(duration=0)
        self.db.add_history(Track(**track), last)
        alb_history = self.db.fetch_albums_history()
        alb = alb_history[0]
        self.assertEqual(alb.Artist.name, track.get('albumartist'))
        # Fetching Album history for "artist" should return "album"
        artist = Artist(track.get('artist'), mbid=track.get('musicbrainz_artistid'))
        alb_history = self.db.fetch_albums_history(artist)
        self.assertTrue(alb_history)
        # Falls back to album and MBID when albumartist and
        # musicbrainz_albumartistid are not set
        self.db.purge_history(duration=0)
        track = {
            'album': 'no albumartist set', 'title': 'title',
            'artist': 'no album artist set',
            'file': 'bar/foo.flac',
            'musicbrainz_artistid': 'dddddddd-49ab-4f7c-b148-dddddddddddd',}
        self.db.add_history(Track(**track), last)
        alb_history = self.db.fetch_albums_history()
        album = alb_history[0]
        self.assertEqual(album.albumartist, track['artist'])
        self.assertEqual(album.Artist.mbid, track['musicbrainz_artistid'])

    def test_04_filtering_history(self):
        # Controls artist history filtering
        for i in range(0, 5):
            trk = Track(file=f'/foo/bar.{i}', name=f'{i}-baz',
                        artist=f'{i}-art', album=f'{i}-lbum')
            last = CURRENT - datetime.timedelta(minutes=i)
            self.db.add_history(trk, date=last)
            if i == 5:  # bounce latest record
                self.db.add_history(trk, date=last)
        art_history = self.db.fetch_artists_history()
        # Already checked but to be sure, we should have 5 artists in history
        self.assertEqual(len(art_history), 5)
        for needle in ['4-art', Artist(name='4-art')]:
            art_history = self.db.fetch_artists_history(needle=needle)
            self.assertEqual(art_history, [needle])
        needle = Artist(name='not-art')
        art_history = self.db.fetch_artists_history(needle=needle)
        self.assertEqual(art_history, [])
        # Controls artists history filtering
        #   for a list of Artist objects
        needle_list = [Artist(name='3-art'), Artist(name='4-art')]
        art_history = self.db.fetch_artists_history(needle=needle_list)
        self.assertEqual(art_history, needle_list)
        #   for a MetaContainer
        needle_meta = MetaContainer(needle_list)
        art_history = self.db.fetch_artists_history(needle=needle_meta)
        self.assertEqual(art_history, needle_list)
        #   for a list of string (Meta object handles Artist/str comparison)
        art_history = self.db.fetch_artists_history(['3-art', '4-art'])
        self.assertEqual(art_history, needle_list)

        # Controls album history filtering
        needle = Artist(name='4-art')
        alb_history = self.db.fetch_albums_history(needle=needle)
        self.assertEqual(alb_history, [Album(name='4-lbum')])

    def test_05_triggers(self):
        self.db.purge_history(duration=0)
        tracks_ids = list()
        #  Add a first track
        track = Track(file='/baz/bar.baz', name='baz', artist='fooart',
                      albumartist='not-same', album='not-same',)
        self.db.get_track(track)
        # Set 6 more records from same artist but not same album
        for i in range(1, 6):  # starts at 1 to ensure records are in the past
            trk = Track(file=f'/foo/{i}', name=f'{i}', artist='fooart',
                        albumartist='fooalbart', album='foolbum',)
            # Add track, save its DB id
            tracks_ids.append(self.db.get_track(trk))
            # set records in the past to ease purging then
            last = CURRENT - datetime.timedelta(minutes=i)
            self.db.add_history(trk, date=last)  # Add to history
        conn = self.db.get_database_connection()
        # for tid in tracks_ids:
        for tid in tracks_ids[:-1]:
            # Delete lastest record
            conn.execute('DELETE FROM history WHERE history.track = ?',
                         (tid,))
            c = conn.execute('SELECT albums.name FROM albums;')
            # There are still albums records (still a history using it)
            self.assertIn((trk.album,), c.fetchall())
        # purging last entry in history for album == trk.album
        conn.execute('DELETE FROM history WHERE history.track = ?',
                     (tracks_ids[-1],))
        # triggers purge other tables if possible
        conn.execute('SELECT albums.name FROM albums;')
        albums = c.fetchall()
        # No more "foolbum" in the table albums
        self.assertNotIn(('foolbum',), albums)
        # There is still "fooart" though
        c = conn.execute('SELECT artists.name FROM artists;')
        artists = c.fetchall()
        # No more "foolbum" in the table albums
        self.assertIn(('fooart',), artists)
        conn.close()

    def test_06_add_album(self):
        pass

class Test_01BlockList(Main):

    def test_blocklist_addition(self):
        trk = Track(file='/foo/bar/baz', name='title')
        self.assertIs(self.db.get_bl_track(trk, add=False), None)
        tracks_ids = list()
        # Set 6 records, same album
        for i in range(1, 6):  # starts at 1 to ensure records are in the past
            trk = Track(file=f'/foo/{i}', name=f'{i}', artist='fooart',
                        albumartist='fooalbart', album='foolbum',)
            # Add track, save its DB id
            tracks_ids.append(self.db.get_track(trk))
            if i == 1:
                self.db.get_bl_track(trk)
                self.assertIsNot(self.db.get_bl_track(trk, add=False), None)
            if i == 2:
                self.db.get_bl_album(Album(name=trk.album))
            if i == 3:
                self.db.get_bl_artist(trk.Artist)
            if i == 4:
                self.assertIs(self.db.get_bl_track(trk, add=False), None)


    def test_blocklist_triggers_00(self):
        trk01 = Track(file='01', name='01', artist='artist A', album='album A')
        blart01_id = self.db.get_bl_artist(trk01.Artist)
        blalb01_id = self.db.get_bl_album(Album(name=trk01.album, mbid=trk01.musicbrainz_albumid))
        conn = self.db.get_database_connection()
        self.db._remove_blocklist_id(blart01_id, with_connection=conn)
        self.db._remove_blocklist_id(blalb01_id, with_connection=conn)
        albums = conn.execute('SELECT albums.name FROM albums;').fetchall()
        artists = conn.execute('SELECT artists.name FROM artists;').fetchall()
        conn.close()
        self.assertNotIn((trk01.album,), albums)
        self.assertNotIn((trk01.artist,), artists)

    def test_blocklist_triggers_01(self):
        trk01 = Track(file='01', name='01', artist='artist A', album='album A')
        trk02 = Track(file='02', name='01', artist='artist A', album='album B')
        trk01_id = self.db.get_bl_track(trk01)
        trk02_id = self.db.get_bl_track(trk02)
        self.db.add_history(trk01, IN_THE_PAST)
        self.db._remove_blocklist_id(trk01_id)
        # bl trk01 removed:
        # albums/artists table not affected since trk01_id still in history
        conn = self.db.get_database_connection()
        albums = conn.execute('SELECT albums.name FROM albums;').fetchall()
        artists = conn.execute('SELECT artists.name FROM artists;').fetchall()
        self.assertIn(('album A',), albums)
        self.assertIn(('artist A',), artists)
        self.db.purge_history(0)
        # remove last reference to trk01
        albums = conn.execute('SELECT albums.name FROM albums;').fetchall()
        self.assertNotIn(('album A',), albums)
        self.assertIn(('artist A',), artists)
        # remove trk02
        self.db._remove_blocklist_id(trk02_id)
        albums = conn.execute('SELECT albums.name FROM albums;').fetchall()
        artists = conn.execute('SELECT artists.name FROM artists;').fetchall()
        self.assertNotIn(('album B',), albums)
        self.assertNotIn(('artist A'), artists)
        conn.close()


class Test_02Genre(Main):

    def test_genre(self):
        conn = self.db.get_database_connection()
        self.db.get_genre('Post-Rock', with_connection=conn)
        genres = list()
        for i in range(1, 15):  # starts at 1 to ensure records are in the past
            trk = Track(file=f'/foo/bar.{i}', name=f'{i}-baz',
                        album='foolbum', artist=f'{i}-art', genre=f'{i}')
            genres.append(f'{i}')
            last = CURRENT - datetime.timedelta(minutes=i)
            self.db.add_history(trk, date=last)
        genre_hist = self.db.fetch_genres_history(limit=10)
        self.assertEqual([g[0] for g in genre_hist], genres[:10])

    def test_null_genres(self):
        conn = self.db.get_database_connection()
        genres = list()
        for i in range(1, 2):  # starts at 1 to ensure records are in the past
            trk = Track(file=f'/foo/bar.{i}', name=f'{i}-baz',
                        album='foolbum', artist=f'{i}-art')
            last = CURRENT - datetime.timedelta(minutes=i)
            self.db.add_history(trk, date=last)
        genre_hist = self.db.fetch_genres_history(limit=10)
        self.assertEqual(genre_hist, [])

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab fileencoding=utf8
