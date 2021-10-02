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
"""

#: DB Version
__DB_VERSION__ = 4
#: Default history duration for both request and purge in hours
__HIST_DURATION__ = int(30 * 24)

import sqlite3

from collections import deque
from datetime import (datetime, timedelta)
from datetime import timezone


from sima.lib.meta import Artist, Album
from sima.lib.track import Track
from sima.utils.utils import MPDSimaException


class SimaDBError(MPDSimaException):
    """
    Exceptions.
    """


class SimaDB:
    "SQLite management"

    def __init__(self, db_path=None):
        self._db_path = db_path

    def get_database_connection(self):
        """get database reference"""
        connection = sqlite3.connect(self._db_path, isolation_level=None)
        return connection

    def get_info(self):
        connection = self.get_database_connection()
        info = connection.execute("""SELECT * FROM db_info
                    WHERE name = "DB Version" LIMIT 1;""").fetchone()
        connection.close()
        return info

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
            'last_play TIMESTAMP, track INTEGER, '
            'FOREIGN KEY(track) REFERENCES tracks(id))')
        connection.execute(  # BLOCKLIST
            'CREATE TABLE IF NOT EXISTS blocklist (id INTEGER PRIMARY KEY, '
            'artist INTEGER, album INTEGER, track INTEGER, '
            'FOREIGN KEY(artist) REFERENCES artists(id), '
            'FOREIGN KEY(album)  REFERENCES albums(id), '
            'FOREIGN KEY(track)  REFERENCES tracks(id))')
        connection.execute(  # Genres (Many-to-many)
            'CREATE TABLE IF NOT EXISTS genres '
            '(id INTEGER PRIMARY KEY, name VARCHAR(100))')
        connection.execute(  # Junction Genres Tracks
                """CREATE TABLE IF NOT EXISTS tracks_genres
                ( track INTEGER, genre INTEGER,
                FOREIGN KEY(track) REFERENCES tracks(id)
                FOREIGN KEY(genre) REFERENCES genres(id))""")
        # Create cleanup triggers:
        # DELETE history → Tracks / Tracks_genres tables
        connection.execute('''
            CREATE TRIGGER IF NOT EXISTS del_history_cleanup_tracks
            AFTER DELETE ON history
            WHEN ((SELECT count(*) FROM history WHERE track=old.track) = 0 AND
                  (SELECT count(*) FROM blocklist WHERE track=old.track) = 0)
            BEGIN
             DELETE FROM tracks WHERE id = old.track;
             DELETE FROM tracks_genres WHERE track = old.track;
            END;
            ''')
        # DELETE Tracks_Genres → Genres table
        connection.execute('''
            CREATE TRIGGER IF NOT EXISTS del_tracks_genres_cleanup_genres
            AFTER DELETE ON tracks_genres
            WHEN ((SELECT count(*) FROM tracks_genres WHERE genre=old.genre) = 0)
            BEGIN
             DELETE FROM genres WHERE id = old.genre;
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
        # DELETE blocklist → Artists table
        # The "SELECT count(*) FROM blocklist" is useless,
        # there can be only one blocklist.artist
        connection.execute('''
            CREATE TRIGGER IF NOT EXISTS del_blocklist_cleanup_artists
            AFTER DELETE ON blocklist
            WHEN ((SELECT count(*) FROM tracks WHERE artist=old.artist) = 0 AND
                  (SELECT count(*) FROM blocklist WHERE artist=old.artist) = 0)
            BEGIN
             DELETE FROM artists WHERE id = old.artist;
            END;
            ''')
        # DELETE Tracks → Albums table
        # The "SELECT count(*) FROM blocklist" is useless,
        # there can be only one blocklist.album
        connection.execute('''
            CREATE TRIGGER IF NOT EXISTS del_blocklist_cleanup_albums
            AFTER DELETE ON blocklist
            WHEN ((SELECT count(*) FROM tracks WHERE album=old.album) = 0 AND
                  (SELECT count(*) FROM blocklist WHERE album=old.album) = 0)
            BEGIN
             DELETE FROM albums WHERE id = old.album;
            END;
            ''')
        connection.close()

    def drop_all(self):
        connection = self.get_database_connection()
        rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")
        for row in rows.fetchall():
            connection.execute(f'DROP TABLE IF EXISTS {row[0]}')
        connection.close()

    def _remove_blocklist_id(self, blid, with_connection=None):
        """Remove a blocklist id"""
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        connection = self.get_database_connection()
        connection.execute('DELETE FROM blocklist'
                           ' WHERE blocklist.id = ?', (blid,))
        connection.commit()
        if not with_connection:
            connection.close()

    def _get_album(self, album, connection):
        if album.mbid:
            return connection.execute(
                "SELECT id FROM albums WHERE mbid = ?",
                (album.mbid,))
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
                connection.close()
            return row[0]
        if not add:
            if not with_connection:
                connection.close()
            return None
        connection.execute(
            "INSERT INTO albums (name, mbid) VALUES (?, ?)",
            (album.name, album.mbid))
        connection.commit()
        rows = self._get_album(album, connection)
        for row in rows:
            if not with_connection:
                connection.close()
            return row[0]
        if not with_connection:
            connection.close()
        return None

    def _get_albumartist(self, artist, connection):
        if artist.mbid:
            return connection.execute(
                "SELECT id FROM albumartists WHERE mbid = ?",
                (artist.mbid,))
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
                connection.close()
            return row[0]
        if not add:
            if not with_connection:
                connection.close()
            return None
        connection.execute(
            "INSERT INTO albumartists (name, mbid) VALUES (?, ?)",
            (artist.name, artist.mbid))
        connection.commit()
        rows = self._get_albumartist(artist, connection)
        for row in rows:
            if not with_connection:
                connection.close()
            return row[0]
        if not with_connection:
            connection.close()

    def _get_artist(self, artist, connection):
        if artist.mbid:
            return connection.execute(
                "SELECT id FROM artists WHERE mbid = ?",
                (artist.mbid,))
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
                connection.close()
            return row[0]
        if not add:
            if not with_connection:
                connection.close()
            return None
        connection.execute(
            "INSERT INTO artists (name, mbid) VALUES (?, ?)",
            (artist.name, artist.mbid))
        connection.commit()
        rows = self._get_artist(artist, connection)
        for row in rows:
            if not with_connection:
                connection.close()
            return row[0]
        if not with_connection:
            connection.close()

    def get_genre(self, genre, with_connection=None, add=True):
        """get genre from the database.
        if not in database insert new entry.

        :param str genre: genre as a string
        :param sqlite3.Connection with_connection: SQLite connection
        """
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        rows = connection.execute(
            "SELECT id FROM genres WHERE name = ?", (genre,))
        for row in rows:
            if not with_connection:
                connection.close()
            return row[0]
        if not add:
            if not with_connection:
                connection.close()
            return None
        connection.execute(
            "INSERT INTO genres (name) VALUES (?)", (genre,))
        connection.commit()
        rows = connection.execute(
            "SELECT id FROM genres WHERE name = ?", (genre,))
        for row in rows:
            if not with_connection:
                connection.close()
            return row[0]

    def get_track(self, track, with_connection=None, add=True):
        """Get a track id from Tracks table, add if not existing,

        :param sima.lib.track.Track track: track to use
        :param bool add: add non existing track to database"""
        if not track.file:
            raise SimaDBError(f'Got a track with no file attribute: {track}')
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        rows = connection.execute(
            "SELECT * FROM tracks WHERE file = ?", (track.file,))
        for row in rows:
            if not with_connection:
                connection.close()
            return row[0]
        if not add:  # Not adding non existing track
            if not with_connection:
                connection.close()
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
        # Add track id to junction tables
        self._add_tracks_genres(track, connection)
        rows = connection.execute(
            "SELECT id FROM tracks WHERE file = ?", (track.file,))
        for row in rows:
            if not with_connection:
                connection.close()
            return row[0]
        if not with_connection:
            connection.close()
        return None

    def _add_tracks_genres(self, track, connection):
        if not track.genres:
            return
        rows = connection.execute(
            "SELECT id FROM tracks WHERE file = ?", (track.file,))
        trk_id = rows.fetchone()[0]
        for genre in track.genres:
            # add genre
            gen_id = self.get_genre(genre)
            connection.execute("""INSERT INTO tracks_genres (track, genre)
                    VALUES (?, ?)""", (trk_id, gen_id))

    def add_history(self, track, date=None):
        """Record last play date of track (ie. not a real play history).

        :param sima.lib.track.Track track: track to add to history
        :param datetime.datetime date: UTC datetime object (use "datetime.now(timezone.utc)" is not set)"""
        if not date:
            date = datetime.now(timezone.utc)
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
        connection.close()

    def purge_history(self, duration=__HIST_DURATION__):
        """Remove old entries in history

        :param int duration: Purge history record older than duration in hours"""
        connection = self.get_database_connection()
        connection.execute("DELETE FROM history WHERE last_play"
                           " < datetime('now', '-%i hours')" % duration)
        connection.execute('VACUUM')
        connection.commit()
        connection.close()

    def fetch_albums_history(self, needle=None, duration=__HIST_DURATION__):
        """
        :param sima.lib.meta.Artist needle: When specified, returns albums history for this artist.
        :param int duration: How long ago to fetch history from (in hours)
        """
        date = datetime.now(timezone.utc) - timedelta(hours=duration)
        connection = self.get_database_connection()
        connection.row_factory = sqlite3.Row
        rows = connection.execute("""
                SELECT albums.name AS name,
                       albums.mbid as mbid,
                       artists.name as artist,
                       artists.mbid as artist_mbib,
                       albumartists.name as albumartist,
                       albumartists.mbid as albumartist_mbib
                FROM history
                JOIN tracks ON history.track = tracks.id
                LEFT OUTER JOIN albums ON tracks.album = albums.id
                LEFT OUTER JOIN artists ON tracks.artist = artists.id
                LEFT OUTER JOIN albumartists ON tracks.albumartist = albumartists.id
                WHERE history.last_play > ? AND albums.name NOT NULL AND artists.name NOT NULL
                ORDER BY history.last_play DESC""", (date.isoformat(' '),))
        hist = []
        for row in rows:
            vals = dict(row)
            if needle:  # Here use artist instead of albumartist
                if needle != Artist(name=vals.get('artist'),
                                    mbid=vals.get('artist_mbib')):
                    continue
            # Use albumartist / MBIDs if possible to build album artist
            if not vals.get('albumartist'):
                vals['albumartist'] = vals.get('artist')
            if not vals.get('albumartist_mbib'):
                vals['albumartist_mbib'] = vals.get('artist_mbib')
            artist = Artist(name=vals.get('albumartist'),
                            mbid=vals.pop('albumartist_mbib'))
            album = Album(**vals, Artist=artist)
            if hist and hist[-1] == album:
                # remove consecutive dupes
                continue
            hist.append(album)
        connection.close()
        return hist

    def fetch_artists_history(self, needle=None, duration=__HIST_DURATION__):
        """Returns a list of Artist objects

        :param sima.lib.meta.MetaContainer needle: When specified, returns history for these artists only
        :param int duration: How long ago to fetch history from (in hours)
        :type needle: sima.lib.meta.Artist or sima.lib.meta.MetaContainer
        """
        date = datetime.now(timezone.utc) - timedelta(hours=duration)
        connection = self.get_database_connection()
        connection.row_factory = sqlite3.Row
        rows = connection.execute("""
                SELECT artists.name AS name,
                       artists.mbid as mbid
                FROM history
                JOIN tracks ON history.track = tracks.id
                LEFT OUTER JOIN artists ON tracks.artist = artists.id
                WHERE history.last_play > ? AND artists.name NOT NULL
                ORDER BY history.last_play DESC""", (date.isoformat(' '),))
        last = deque(maxlen=1)
        hist = []
        for row in rows:
            artist = Artist(**row)
            if last and last[0] == artist:  # remove consecutive dupes
                continue
            last.append(artist)
            if needle and isinstance(needle, (Artist, str)):
                if needle == artist:
                    hist.append(artist)  # No need to go further
                    break
                continue
            if needle and getattr(needle, '__contains__'):
                if artist in needle:
                    hist.append(artist)  # No need to go further
                continue
            hist.append(artist)
        connection.close()
        return hist

    def fetch_genres_history(self, duration=__HIST_DURATION__, limit=20):
        """Returns genre history

        :param int duration: How long ago to fetch history from (in hours)
        :param int limit: number of genre to fetch
        """
        date = datetime.now(timezone.utc) - timedelta(hours=duration)
        connection = self.get_database_connection()
        rows = connection.execute("""
                SELECT genres.name, artists.name
                FROM history
                JOIN tracks ON history.track = tracks.id
                LEFT OUTER JOIN tracks_genres ON tracks_genres.track = tracks.id
                LEFT OUTER JOIN artists ON tracks.artist = artists.id
                LEFT OUTER JOIN genres ON genres.id = tracks_genres.genre
                WHERE history.last_play > ? AND genres.name NOT NULL
                ORDER BY history.last_play DESC
                """, (date.isoformat(' '),))
        genres = []
        for row in rows:
            genres.append(row)
            if len({g[0] for g in genres}) >= limit:
                break
        connection.close()
        return genres

    def fetch_history(self, artist=None, duration=__HIST_DURATION__):
        """Fetches tracks history, more recent first

        :param sima.lib.meta.Artist artist: limit history to this artist
        :param int duration: How long ago to fetch history from (in hours)
        """
        date = datetime.now(timezone.utc) - timedelta(hours=duration)
        connection = self.get_database_connection()
        connection.row_factory = sqlite3.Row
        sql = """
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
              """
        if artist:
            if artist.mbid:
                rows = connection.execute(sql+"""
                        AND artists.mbid = ?
                        ORDER BY history.last_play DESC""",
                                          (date.isoformat(' '), artist.mbid))
            else:
                rows = connection.execute(sql+"""
                        AND artists.name = ?
                        ORDER BY history.last_play DESC""",
                                          (date.isoformat(' '), artist.name))
        else:
            rows = connection.execute(sql+'ORDER BY history.last_play DESC',
                                      (date.isoformat(' '),))
        hist = []
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
        track_id = self.get_track(track, with_connection=connection, add=add)
        rows = connection.execute(
            "SELECT id FROM blocklist WHERE track = ?", (track_id,))
        if not rows.fetchone():
            if not add:
                if not with_connection:
                    connection.close()
                return None
            connection.execute('INSERT INTO blocklist (track) VALUES (?)',
                               (track_id,))
            connection.commit()
        rows = connection.execute(
            "SELECT id FROM blocklist WHERE track = ?", (track_id,))
        blt = rows.fetchone()[0]
        if not with_connection:
            connection.close()
        return blt

    def get_bl_album(self, album, with_connection=None, add=True):
        """Add an album to blocklist

        :param sima.lib.meta.Album: Album object to add to blocklist
        :param sqlite3.Connection with_connection: sqlite3.Connection to reuse, else create a new one
        :param bool add: Default is to add a new record, set to False to fetch associated record"""
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        album_id = self.get_album(album, with_connection=connection, add=add)
        rows = connection.execute(
            "SELECT id FROM blocklist WHERE album = ?", (album_id,))
        if not rows.fetchone():
            if not add:
                if not with_connection:
                    connection.close()
                return None
            connection.execute('INSERT INTO blocklist (album) VALUES (?)',
                               (album_id,))
            connection.commit()
        rows = connection.execute(
            "SELECT id FROM blocklist WHERE album = ?", (album_id,))
        blitem = rows.fetchone()[0]
        if not with_connection:
            connection.close()
        return blitem

    def get_bl_artist(self, artist, with_connection=None, add=True):
        """Add an artist to blocklist

        :param sima.lib.meta.Artist: Artist object to add to blocklist
        :param sqlite3.Connection with_connection: sqlite3.Connection to reuse, else create a new one
        :param bool add: Default is to add a new record, set to False to fetch associated record"""
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        artist_id = self.get_artist(artist, with_connection=connection, add=add)
        rows = connection.execute(
            "SELECT id FROM blocklist WHERE artist = ?", (artist_id,))
        if not rows.fetchone():
            if not add:
                return None
            connection.execute('INSERT INTO blocklist (artist) VALUES (?)',
                               (artist_id,))
            connection.commit()
        rows = connection.execute(
            "SELECT id FROM blocklist WHERE artist = ?", (artist_id,))
        blitem = rows.fetchone()[0]
        if not with_connection:
            connection.close()
        return blitem

    def view_bl(self):
        connection = self.get_database_connection()
        connection.row_factory = sqlite3.Row
        rows = connection.execute("""SELECT artists.name AS artist,
               artists.mbid AS musicbrainz_artist,
               albums.name AS album,
               albums.mbid AS musicbrainz_album,
               tracks.title AS title,
               tracks.mbid AS musicbrainz_title,
               tracks.file AS file,
               blocklist.id
               FROM blocklist
               LEFT OUTER JOIN artists ON blocklist.artist = artists.id
               LEFT OUTER JOIN albums ON blocklist.album = albums.id
               LEFT OUTER JOIN tracks ON blocklist.track = tracks.id""")
        res = [dict(row) for row in rows.fetchall()]
        connection.close()
        return res

    def delete_bl(self, track=None, album=None, artist=None):
        if not (track or album or artist):
            return
        connection = self.get_database_connection()
        blid = None
        if track:
            blid = self.get_bl_track(track, with_connection=connection)
        if album:
            blid = self.get_bl_album(album, with_connection=connection)
        if artist:
            blid = self.get_bl_artist(artist, with_connection=connection)
        if not blid:
            return
        self._remove_blocklist_id(blid, with_connection=connection)
        connection.close()


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab fileencoding=utf8
