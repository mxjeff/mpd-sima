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
        # Create cleanup triggers:
        # Tracks table
        connection.execute('''
                CREATE TRIGGER IF NOT EXISTS cleanup_tracks
                AFTER DELETE ON history
                WHEN ((SELECT count(*) FROM history WHERE track=old.id) = 0)
                BEGIN
                 DELETE FROM tracks WHERE id = old.id;
                END;
                ''')
        # Artists table
        connection.execute('''
                CREATE TRIGGER IF NOT EXISTS cleanup_artists
                AFTER DELETE ON tracks
                WHEN ((SELECT count(*) FROM tracks WHERE artist=old.artist) = 0)
                BEGIN
                 DELETE FROM artists WHERE id = old.artist;
                END;
                ''')
        # Albums table
        connection.execute('''
                CREATE TRIGGER IF NOT EXISTS cleanup_albums
                AFTER DELETE ON tracks
                WHEN ((SELECT count(*) FROM tracks WHERE album=old.album) = 0)
                BEGIN
                 DELETE FROM albums WHERE id = old.album;
                END;
                ''')
        # AlbumArtists table
        connection.execute('''
                CREATE TRIGGER IF NOT EXISTS cleanup_albumartists
                AFTER DELETE ON tracks
                WHEN ((SELECT count(*) FROM tracks WHERE albumartist=old.albumartist) = 0)
                BEGIN
                 DELETE FROM albumartists WHERE id = old.albumartist;
                END;
                ''')
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

    def get_history(self, duration=__HIST_DURATION__):
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


def main():
    db = SimaDB('/dev/shm/test.sqlite')
    db.create_db()

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab fileencoding=utf8
