# Copyright (c) 2009-2013, 2019-2021 kaliko <kaliko@azylum.org>
#
#  This file is part of sima
#
#  sima is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  sima is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with sima.  If not, see <http://www.gnu.org/licenses/>.
#
#
"""SQlite database library

https://stackoverflow.com/questions/62818662/sqlite-foreign-key-reverse-cascade-delete
"""

__DB_VERSION__ = 4
__HIST_DURATION__ = int(30 * 24)  # in hours

import sqlite3

from datetime import (datetime, timedelta)

from sima.lib.meta import Artist, Album
from sima.lib.track import Track


class SimaDBError(Exception):
    """
    Exceptions.
    """


class SimaDB:
    "SQLite management"

    def __init__(self, db_path=None):
        self._db_path = db_path

    def get_database_connection(self):
        """get database reference"""
        connection = sqlite3.connect(
            self._db_path, isolation_level=None)
        return connection

    def close_database_connection(self, connection):
        """Close the database connection."""
        connection.close()

    def create_db(self):
        """ Set up a database
        """
        connection = self.get_database_connection()
        connection.execute(
            'CREATE TABLE IF NOT EXISTS db_info'
            ' (name CHAR(50), value CHAR(50))')
        connection.execute('''INSERT INTO db_info (name, value) SELECT ?, ?
                           WHERE NOT EXISTS
                           ( SELECT 1 FROM db_info WHERE name = ? )''',
                           ('DB Version', __DB_VERSION__, 'DB Version'))
        connection.execute(  # ARTISTS
            'CREATE TABLE IF NOT EXISTS artists (id INTEGER PRIMARY KEY, '
            'name VARCHAR(100), mbid CHAR(36))')
        connection.execute(  # ALBUMS
            'CREATE TABLE IF NOT EXISTS albums (id INTEGER PRIMARY KEY, '
            'name VARCHAR(100), mbid CHAR(36))')
        connection.execute(  # ALBUMARTISTS
            'CREATE TABLE IF NOT EXISTS albumartists (id INTEGER PRIMARY KEY, '
            'name VARCHAR(100), mbid CHAR(36))')
        connection.execute(  # TRACKS
            'CREATE TABLE IF NOT EXISTS tracks (id INTEGER PRIMARY KEY, '
            'title VARCHAR(100), artist INTEGER, '
            'album INTEGER, albumartist INTEGER, '
            'file VARCHAR(500), mbid CHAR(36), '
            'FOREIGN KEY(artist)       REFERENCES artists(id), '
            'FOREIGN KEY(album)        REFERENCES albums(id), '
            'FOREIGN KEY(albumartist)  REFERENCES albumartists(id))')
        connection.execute(  # HISTORY
            'CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, '
            'last_play TIMESTAMP, track integer, '
            'FOREIGN KEY(track) REFERENCES tracks(id))')
        connection.execute(  # BLOCKLIST
            'CREATE TABLE IF NOT EXISTS blocklist (id INTEGER PRIMARY KEY, '
            'artist INTEGER, album INTEGER, track INTEGER, '
            'FOREIGN KEY(artist) REFERENCES artists(id), '
            'FOREIGN KEY(album)  REFERENCES albums(id), '
            'FOREIGN KEY(track)  REFERENCES tracks(id))')
        # Create cleanup triggers:
        # DELETE history → Tracks table
        connection.execute('''
           CREATE TRIGGER IF NOT EXISTS del_history_cleanup_tracks
           AFTER DELETE ON history
           WHEN ((SELECT count(*) FROM history WHERE track=old.track) = 0 AND
                 (SELECT count(*) FROM blocklist WHERE track=old.track) = 0)
           BEGIN
            DELETE FROM tracks WHERE id = old.track;
           END;
           ''')
        # DELETE Tracks → Artists table
        connection.execute('''
           CREATE TRIGGER IF NOT EXISTS del_tracks_cleanup_artists
           AFTER DELETE ON tracks
           WHEN ((SELECT count(*) FROM tracks WHERE artist=old.artist) = 0 AND
                 (SELECT count(*) FROM blocklist WHERE artist=old.artist) = 0)
           BEGIN
            DELETE FROM artists WHERE id = old.artist;
           END;
           ''')
        # DELETE Tracks → Albums table
        connection.execute('''
           CREATE TRIGGER IF NOT EXISTS del_tracks_cleanup_albums
           AFTER DELETE ON tracks
           WHEN ((SELECT count(*) FROM tracks WHERE album=old.album) = 0 AND
                 (SELECT count(*) FROM blocklist WHERE album=old.album) = 0)
           BEGIN
            DELETE FROM albums WHERE id = old.album;
           END;
           ''')
        # DELETE Tracks → cleanup AlbumArtists table
        connection.execute('''
           CREATE TRIGGER IF NOT EXISTS del_tracks_cleanup_albumartists
           AFTER DELETE ON tracks
           WHEN ((SELECT count(*) FROM tracks WHERE albumartist=old.albumartist) = 0)
           BEGIN
            DELETE FROM albumartists WHERE id = old.albumartist;
           END;
           ''')
        # DELETE blocklist → Tracks table
        connection.execute('''
           CREATE TRIGGER IF NOT EXISTS del_blocklist_cleanup_tracks
           AFTER DELETE ON blocklist
           WHEN ((SELECT count(*) FROM history WHERE track=old.track) = 0 AND
                 (SELECT count(*) FROM blocklist WHERE track=old.track) = 0)
           BEGIN
            DELETE FROM tracks WHERE id = old.track;
           END;
           ''')
        self.close_database_connection(connection)

    def drop_all(self):
        connection = self.get_database_connection()
        rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")
        for r in rows.fetchall():
            connection.execute(f'DROP TABLE IF EXISTS {r[0]}')
        connection.close()

    def _remove_blocklist_id(self, blid):
        """Remove id"""
        connection = self.get_database_connection()
        connection.execute('DELETE FROM blocklist'
                           ' WHERE blocklist.id = ?', (blid,))
        connection.commit()
        self.close_database_connection(connection)

    def _get_album(self, album, connection):
        if album.mbid:
            return connection.execute(
                "SELECT id FROM albums WHERE mbid = ?",
                (album.mbid,))
        else:
            return connection.execute(
                "SELECT id FROM albums WHERE name = ? AND mbid IS NULL",
                (album.name,))

    def get_album(self, album, with_connection=None, add=True):
        """get album information from the database.
        if not in database insert new entry.

        :param sima.lib.meta.Album album: album objet
        :param sqlite3.Connection with_connection: SQLite connection
        """
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        rows = self._get_album(album, connection)
        for row in rows:
            if not with_connection:
                self.close_database_connection(connection)
            return row[0]
        if not add:
            if not with_connection:
                self.close_database_connection(connection)
            return None
        connection.execute(
            "INSERT INTO albums (name, mbid) VALUES (?, ?)",
            (album.name, album.mbid))
        connection.commit()
        rows = self._get_album(album, connection)
        for row in rows:
            if not with_connection:
                self.close_database_connection(connection)
            return row[0]
        print('damned: %s' % album.mbid)
        if not with_connection:
            self.close_database_connection(connection)
        return None

    def _get_albumartist(self, artist, connection):
        if artist.mbid:
            return connection.execute(
                "SELECT id FROM albumartists WHERE mbid = ?",
                (artist.mbid,))
        else:
            return connection.execute(
                "SELECT id FROM albumartists WHERE name = ? AND mbid IS NULL",
                (artist.name,))

    def get_albumartist(self, artist, with_connection=None, add=True):
        """get albumartist information from the database.
        if not in database insert new entry.

        :param sima.lib.meta.Artist artist: artist
        :param sqlite3.Connection with_connection: SQLite connection
        """
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        rows = self._get_albumartist(artist, connection)
        for row in rows:
            if not with_connection:
                self.close_database_connection(connection)
            return row[0]
        if not add:
            if not with_connection:
                self.close_database_connection(connection)
            return None
        connection.execute(
            "INSERT INTO albumartists (name, mbid) VALUES (?, ?)",
            (artist.name, artist.mbid))
        connection.commit()
        rows = self._get_albumartist(artist, connection)
        for row in rows:
            if not with_connection:
                self.close_database_connection(connection)
            return row[0]
        if not with_connection:
            self.close_database_connection(connection)

    def _get_artist(self, artist, connection):
        if artist.mbid:
            return connection.execute(
                "SELECT id FROM artists WHERE mbid = ?",
                (artist.mbid,))
        else:
            return connection.execute(
                "SELECT id FROM artists WHERE name = ? AND mbid IS NULL", (artist.name,))

    def get_artist(self, artist, with_connection=None, add=True):
        """get artist information from the database.
        if not in database insert new entry.

        :param sima.lib.meta.Artist artist: artist
        :param sqlite3.Connection with_connection: SQLite connection
        """
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        rows = self._get_artist(artist, connection)
        for row in rows:
            if not with_connection:
                self.close_database_connection(connection)
            return row[0]
        if not add:
            if not with_connection:
                self.close_database_connection(connection)
            return None
        connection.execute(
            "INSERT INTO artists (name, mbid) VALUES (?, ?)",
            (artist.name, artist.mbid))
        connection.commit()
        rows = self._get_artist(artist, connection)
        for row in rows:
            if not with_connection:
                self.close_database_connection(connection)
            return row[0]
        if not with_connection:
            self.close_database_connection(connection)

    def get_track(self, track, with_connection=None, add=True):
        """Get a track from Tracks table, add if not existing,
        Attention: use Track() object!!
        if not in database insert new entry."""
        if not track.file:
            raise SimaDBError('Got a track with no file attribute: %r' % track)
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        rows = connection.execute(
            "SELECT * FROM tracks WHERE file = ?", (track.file,))
        for row in rows:
            if not with_connection:
                self.close_database_connection(connection)
            return row[0]
        if not add:  # Not adding non existing track
            return None
        # Get an artist record or None
        if track.artist:
            art = Artist(name=track.artist, mbid=track.musicbrainz_artistid)
            art_id = self.get_artist(art, with_connection=connection)
        else:
            art_id = None
        # Get an albumartist record or None
        if track.albumartist:
            albart = Artist(name=track.albumartist,
                            mbid=track.musicbrainz_albumartistid)
            albart_id = self.get_albumartist(albart, with_connection=connection)
        else:
            albart_id = None
        # Get an album record or None
        if track.album:
            alb = Album(name=track.album, mbid=track.musicbrainz_albumid)
            alb_id = self.get_album(alb, with_connection=connection)
        else:
            alb_id = None
        connection.execute(
            """INSERT INTO tracks (artist, albumartist, album, title, mbid, file)
                VALUES (?, ?, ?, ?, ?, ?)""",
            (art_id, albart_id, alb_id, track.title, track.musicbrainz_trackid,
                track.file))
        connection.commit()
        rows = connection.execute(
            "SELECT id FROM tracks WHERE file = ?", (track.file,))
        for row in rows:
            if not with_connection:
                self.close_database_connection(connection)
            return row[0]
        if not with_connection:
            connection.commit()
            self.close_database_connection(connection)
        return None

    def add_history(self, track, date=None):
        """Record last play date of track (ie. not a real exhautive play history).
        :param track sima.lib.track.Track: track to add to history"""
        if not date:
            date = datetime.now()
        connection = self.get_database_connection()
        track_id = self.get_track(track, with_connection=connection)
        rows = connection.execute("SELECT * FROM history WHERE track = ? ",
                                  (track_id,))
        if not rows.fetchone():
            connection.execute("INSERT INTO history (track) VALUES (?)",
                               (track_id,))
        connection.execute("UPDATE history SET last_play = ? "
                           " WHERE track = ?", (date, track_id,))
        connection.commit()
        self.close_database_connection(connection)

    def purge_history(self, duration=__HIST_DURATION__):
        """Remove old entries in history
        :param duration int: Purge history record older than duration in hours
                            (defaults to __HIST_DURATION__)"""
        connection = self.get_database_connection()
        connection.execute("DELETE FROM history WHERE last_play"
                           " < datetime('now', '-%i hours')" % duration)
        connection.commit()
        self.close_database_connection(connection)

    def fetch_artists_history(self, duration=__HIST_DURATION__):
        date = datetime.utcnow() - timedelta(hours=duration)
        connection = self.get_database_connection()
        connection.row_factory = sqlite3.Row
        rows = connection.execute("""
                SELECT artists.name AS name,
                       artists.mbid as mbid
                FROM history
                JOIN tracks ON history.track = tracks.id
                LEFT OUTER JOIN artists ON tracks.artist = artists.id
                WHERE history.last_play > ?
                ORDER BY history.last_play DESC""", (date.isoformat(' '),))
        hist = list()
        for row in rows:
            if hist and hist[-1] == Album(**row):  # remove consecutive dupes
                continue
            hist.append(Album(**row))
        connection.close()
        return hist

    def fetch_history(self, duration=__HIST_DURATION__):
        """Fetches tracks history, more recent first
        :param int duration: How long ago to fetch history from
        """
        date = datetime.utcnow() - timedelta(hours=duration)
        connection = self.get_database_connection()
        connection.row_factory = sqlite3.Row
        rows = connection.execute("""
                SELECT tracks.title, tracks.file, artists.name AS artist,
                       albumartists.name AS albumartist,
                       artists.mbid as musicbrainz_artistid,
                       albums.name AS album,
                       albums.mbid AS musicbrainz_albumid,
                       tracks.mbid as musicbrainz_trackid
                FROM history
                JOIN tracks ON history.track = tracks.id
                LEFT OUTER JOIN artists ON tracks.artist = artists.id
                LEFT OUTER JOIN albumartists ON tracks.albumartist = albumartists.id
                LEFT OUTER JOIN albums ON tracks.album = albums.id
                WHERE history.last_play > ?
                ORDER BY history.last_play DESC""", (date.isoformat(' '),))
        hist = list()
        for row in rows:
            hist.append(Track(**row))
        connection.close()
        return hist

    def get_bl_track(self, track, with_connection=None, add=True):
        """Add a track to blocklist
        :param sima.lib.track.Track track: Track object to add to blocklist
        :param sqlite3.Connection with_connection: sqlite3.Connection to reuse, else create a new one
        :param bool add: Default is to add a new record, set to False to fetch associated record"""
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        track_id = self.get_track(track, with_connection=connection, add=True)
        rows = connection.execute(
            "SELECT * FROM blocklist WHERE track = ?", (track_id,))
        if not rows.fetchone():
            if not add:
                return None
            connection.execute('INSERT INTO blocklist (track) VALUES (?)',
                               (track_id,))
            connection.commit()
        rows = connection.execute(
            "SELECT * FROM blocklist WHERE track = ?", (track_id,))
        return rows.fetchone()[0]

    def get_bl_album(self, album, with_connection=None, add=True):
        """Add an album to blocklist
        :param sima.lib.meta.Album: Album object to add to blocklist
        :param sqlite3.Connection with_connection: sqlite3.Connection to reuse, ele create a new one
        :param bool add: Default is to add a new record, set to False to fetch associated record"""
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        album_id = self.get_album(album, with_connection=connection, add=True)
        rows = connection.execute(
            "SELECT * FROM blocklist WHERE album = ?", (album_id,))
        if not rows.fetchone():
            if not add:
                return None
            connection.execute('INSERT INTO blocklist (album) VALUES (?)',
                               (album_id,))
            connection.commit()
        rows = connection.execute(
            "SELECT * FROM blocklist WHERE album = ?", (album_id,))
        return rows.fetchone()

    def get_bl_artist(self, artist, with_connection=None, add=True):
        """Add an artist to blocklist
        :param sima.lib.meta.Artist: Artist object to add to blocklist
        :param sqlite3.Connection with_connection: sqlite3.Connection to reuse, ele create a new one
        :param bool add: Default is to add a new record, set to False to fetch associated record"""
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        artist_id = self.get_artist(artist, with_connection=connection, add=True)
        rows = connection.execute(
            "SELECT * FROM blocklist WHERE artist = ?", (artist_id,))
        if not rows.fetchone():
            if not add:
                return None
            connection.execute('INSERT INTO blocklist (artist) VALUES (?)',
                               (artist_id,))
            connection.commit()
        rows = connection.execute(
            "SELECT * FROM blocklist WHERE artist = ?", (artist_id,))
        return rows.fetchone()


def main():
    DEVOLT = {
        'album': 'Grey',
        'albumartist': 'Devolt',
        'artist': 'Devolt',
        'date': '2011-12-01',
        'file': 'music/Devolt/2011-Grey/03-Devolt - Crazy.mp3',
        'musicbrainz_albumartistid': 'd8e7e3e2-49ab-4f7c-b148-fc946d521f99',
        'musicbrainz_albumid': 'ea2ef2cf-59e1-443a-817e-9066e3e0be4b',
        'musicbrainz_artistid': 'd8e7e3e2-49ab-4f7c-b148-fc946d521f99',
        'musicbrainz_trackid': 'fabf8fc9-2ae5-49c9-8214-a839c958d872',
        'duration': '220.000',
        'title': 'Crazy'}
    db = SimaDB('/dev/shm/test.sqlite')
    db.create_db()
    db.add_history(Track(**DEVOLT))
    DEVOLT['file'] = 'foo'
    print(db.get_bl_track(Track(**DEVOLT)))
    db.add_history(Track(**DEVOLT))

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab fileencoding=utf8
