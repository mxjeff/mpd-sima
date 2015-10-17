# -*- coding: utf-8 -*-
#
# Copyright (c) 2009-2013 Jack Kaliko <jack@azylum.org>
# Copyright (c) 2009, Eric Casteleijn <thisfred@gmail.com>
# Copyright (c) 2008 Rick van Hattem
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

#    DOC:
#    MuscicBrainz ID: <http://musicbrainz.org/doc/MusicBrainzIdentifier>
#    Artists: <http://musicbrainz.org/doc/Artist_Name>
#             <http://musicbrainz.org/doc/Same_Artist_With_Different_Names>

__DB_VERSION__ = 3
__HIST_DURATION__ = int(30 * 24)  # in hours

import sqlite3

from datetime import (datetime, timedelta)
from os.path import dirname, isdir
from os import (access, W_OK, F_OK)


class SimaDBError(Exception):
    """
    Exceptions.
    """
    pass


class SimaDBAccessError(SimaDBError):
    """Error on accessing DB file"""
    pass


class SimaDBNoFile(SimaDBError):
    """No DB file present"""
    pass


class SimaDB(object):
    "SQLite management"

    def __init__(self, db_path=None):
        self._db_path = db_path
        self.db_path_mod_control()

    def db_path_mod_control(self):
        """Controls DB path access & write permissions"""
        db_path = self._db_path
        # Controls directory access
        if not isdir(dirname(db_path)):
            raise SimaDBAccessError('Not a regular directory: "%s"' %
                                    dirname(db_path))
        if not access(dirname(db_path), W_OK):
            raise SimaDBAccessError('No write access to "%s"' % dirname(db_path))
        # Is a file but no write access
        if access(db_path, F_OK) and not access(db_path, W_OK | F_OK):
            raise SimaDBAccessError('No write access to "%s"' % db_path)
        # No file
        if not access(db_path, F_OK):
            raise SimaDBNoFile('No DB file in "%s"' % db_path)

    def close_database_connection(self, connection):
        """Close the database connection."""
        connection.close()

    def get_database_connection(self):
        """get database reference"""
        connection = sqlite3.connect(
            self._db_path, timeout=5.0, isolation_level="immediate")
        #connection.text_factory = str
        return connection

    def get_artist(self, artist_name, mbid=None,
                   with_connection=None, add_not=False):
        """get artist information from the database.
        if not in database insert new entry."""
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        rows = connection.execute(
            "SELECT * FROM artists WHERE name = ?", (artist_name,))
        for row in rows:
            if not with_connection:
                self.close_database_connection(connection)
            return row
        if add_not:
            if not with_connection:
                self.close_database_connection(connection)
            return False
        connection.execute(
            "INSERT INTO artists (name, mbid) VALUES (?, ?)",
            (artist_name, mbid))
        connection.commit()
        rows = connection.execute(
            "SELECT * FROM artists WHERE name = ?", (artist_name,))
        for row in rows:
            if not with_connection:
                self.close_database_connection(connection)
            return row
        if not with_connection:
            self.close_database_connection(connection)

    def get_track(self, track, with_connection=None, add_not=False):
        """
        Get a track from Tracks table, add if not existing,
        Attention: use Track() object!!
        if not in database insert new entry."""
        art = track.artist
        nam = track.title
        fil = track.file
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        art_id = self.get_artist(art, with_connection=connection)[0]
        alb_id = self.get_album(track, with_connection=connection)[0]
        rows = connection.execute(
            "SELECT * FROM tracks WHERE name = ? AND"
            " artist = ? AND file = ?", (nam, art_id, fil))
        for row in rows:
            if not with_connection:
                self.close_database_connection(connection)
            return row
        if add_not:
            return False
        connection.execute(
            "INSERT INTO tracks (artist, album, name, file) VALUES (?, ?, ?, ?)",
            (art_id, alb_id, nam, fil))
        connection.commit()
        rows = connection.execute(
            "SELECT * FROM tracks WHERE name = ? AND"
            " artist = ? AND album = ? AND file = ?",
            (nam, art_id, alb_id, fil,))
        for row in rows:
            if not with_connection:
                self.close_database_connection(connection)
            return row
        if not with_connection:
            connection.commit()
            self.close_database_connection(connection)

    def get_album(self, track, mbid=None,
                  with_connection=None, add_not=False):
        """
        get album information from the database.
        if not in database insert new entry.
        Attention: use Track|Album object!!
        Use AlbumArtist tag if provided, fallback to Album tag
        """
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        if track.albumartist:
            artist = track.albumartist
        else:
            artist = track.artist
        art_id = self.get_artist(artist, with_connection=connection)[0]
        album = track.album
        rows = connection.execute(
            "SELECT * FROM albums WHERE name = ? AND artist = ?",
            (album, art_id))
        for row in rows:
            if not with_connection:
                self.close_database_connection(connection)
            return row
        if add_not:
            return False
        connection.execute(
            "INSERT INTO albums (name, artist, mbid) VALUES (?, ?, ?)",
            (album, art_id, mbid))
        connection.commit()
        rows = connection.execute(
            "SELECT * FROM albums WHERE name = ? AND artist = ?",
            (album, art_id))
        for row in rows:
            if not with_connection:
                self.close_database_connection(connection)
            return row
        if not with_connection:
            self.close_database_connection(connection)

    def get_artists(self, with_connection=None):
        """Returns all artists in DB"""
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        rows = connection.execute("SELECT name FROM artists ORDER BY name")
        results = [row for row in rows]
        if not with_connection:
            self.close_database_connection(connection)
        for artist in results:
            yield artist

    def get_bl_artist(self, artist_name,
                      with_connection=None, add_not=None):
        """get blacklisted artist information from the database."""
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        art = self.get_artist(artist_name, with_connection=connection,
                              add_not=add_not)
        if not art:
            return False
        art_id = art[0]
        rows = connection.execute("SELECT * FROM black_list WHERE artist = ?",
                                  (art_id,))
        for row in rows:
            if not with_connection:
                self.close_database_connection(connection)
            return row
        if add_not:
            if not with_connection:
                self.close_database_connection(connection)
            return False
        connection.execute("INSERT INTO black_list (artist) VALUES (?)",
                           (art_id,))
        connection.execute("UPDATE black_list SET updated = DATETIME('now')"
                           " WHERE artist = ?", (art_id,))
        connection.commit()
        rows = connection.execute("SELECT * FROM black_list WHERE artist = ?",
                                  (art_id,))
        for row in rows:
            if not with_connection:
                self.close_database_connection(connection)
            return row
        if not with_connection:
            self.close_database_connection(connection)
        return False

    def get_bl_album(self, track, with_connection=None, add_not=None):
        """get blacklisted album information from the database."""
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        album = self.get_album(track, with_connection=connection,
                               add_not=add_not)
        if not album:
            return False
        alb_id = album[0]
        rows = connection.execute("SELECT * FROM black_list WHERE album = ?",
                                  (alb_id,))
        for row in rows:
            if not with_connection:
                self.close_database_connection(connection)
            return row
        if add_not:
            if not with_connection:
                self.close_database_connection(connection)
            return False
        connection.execute("INSERT INTO black_list (album) VALUES (?)",
                           (alb_id,))
        connection.execute("UPDATE black_list SET updated = DATETIME('now')"
                           " WHERE album = ?", (alb_id,))
        connection.commit()
        rows = connection.execute("SELECT * FROM black_list WHERE album = ?",
                                  (alb_id,))
        for row in rows:
            if not with_connection:
                self.close_database_connection(connection)
            return row
        if not with_connection:
            self.close_database_connection(connection)
        return False

    def get_bl_track(self, track, with_connection=None, add_not=None):
        """get blacklisted track information from the database."""
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        track = self.get_track(track, with_connection=connection,
                               add_not=add_not)
        if not track:
            return False
        track_id = track[0]
        rows = connection.execute("SELECT * FROM black_list WHERE track = ?",
                                  (track_id,))
        for row in rows:
            if not with_connection:
                self.close_database_connection(connection)
            return row
        if add_not:
            if not with_connection:
                self.close_database_connection(connection)
            return False
        connection.execute("INSERT INTO black_list (track) VALUES (?)",
                           (track_id,))
        connection.execute("UPDATE black_list SET updated = DATETIME('now')"
                           " WHERE track = ?", (track_id,))
        connection.commit()
        rows = connection.execute("SELECT * FROM black_list WHERE track = ?",
                                  (track_id,))
        for row in rows:
            if not with_connection:
                self.close_database_connection(connection)
            return row
        if not with_connection:
            self.close_database_connection(connection)
        return False

    def get_artists_history(self, artists, duration=__HIST_DURATION__):
        """
        """
        date = datetime.utcnow() - timedelta(hours=duration)
        connection = self.get_database_connection()
        rows = connection.execute(
            "SELECT arts.name, albs.name, trs.name, trs.file"
            " FROM artists AS arts, tracks AS trs, history AS hist, albums AS albs"
            " WHERE trs.id = hist.track AND trs.artist = arts.id AND trs.album = albs.id"
            " AND hist.last_play > ? ORDER BY hist.last_play DESC", (date.isoformat(' '),))
        for row in rows:
            if artists and row[0] not in artists:
                continue
            for art in artists:
                if row[0] == art:
                    yield art
        self.close_database_connection(connection)

    def get_history(self, artist=None, artists=None, duration=__HIST_DURATION__):
        """Retrieve complete play history, most recent tracks first
        artist  : filter history for specific artist
        artists : filter history for specific artists list
        """ # pylint: disable=C0301
        date = datetime.utcnow() - timedelta(hours=duration)
        connection = self.get_database_connection()
        if artist:
            rows = connection.execute(
                "SELECT arts.name, albs.name, trs.name, trs.file, hist.last_play"
                " FROM artists AS arts, tracks AS trs, history AS hist, albums AS albs"
                " WHERE trs.id = hist.track AND trs.artist = arts.id AND trs.album = albs.id"
                " AND hist.last_play > ? AND arts.name = ?"
                " ORDER BY hist.last_play DESC", (date.isoformat(' '), artist,))
        else:
            rows = connection.execute(
                "SELECT arts.name, albs.name, trs.name, trs.file"
                " FROM artists AS arts, tracks AS trs, history AS hist, albums AS albs"
                " WHERE trs.id = hist.track AND trs.artist = arts.id AND trs.album = albs.id"
                " AND hist.last_play > ? ORDER BY hist.last_play DESC", (date.isoformat(' '),))
        for row in rows:
            if artists and row[0] not in artists:
                continue
            yield row
        self.close_database_connection(connection)

    def get_black_list(self):
        """Retrieve complete black list."""
        connection = self.get_database_connection()
        rows = connection.execute('SELECT black_list.rowid, artists.name'
                                  ' FROM artists INNER JOIN black_list'
                                  ' ON artists.id = black_list.artist')
        yield ('Row ID', 'Actual black listed element', 'Extra information',)
        yield ('',)
        yield ('Row ID', 'Artist',)
        for row in rows:
            yield row
        rows = connection.execute(
                'SELECT black_list.rowid, albums.name, artists.name'
                ' FROM artists, albums INNER JOIN black_list'
                ' ON albums.id = black_list.album'
                ' WHERE artists.id = albums.artist')
        yield ('',)
        yield ('Row ID', 'Album', 'Artist name')
        for row in rows:
            yield row
        rows = connection.execute(
                'SELECT black_list.rowid, tracks.name, artists.name'
                ' FROM artists, tracks INNER JOIN black_list'
                ' ON tracks.id = black_list.track'
                ' WHERE tracks.artist = artists.id')
        yield ('',)
        yield ('Row ID', 'Title', 'Artist name')
        for row in rows:
            yield row
        self.close_database_connection(connection)

    def _set_mbid(self, artist_id=None, mbid=None, with_connection=None):
        """"""
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        connection.execute("UPDATE artists SET mbid = ? WHERE id = ?",
                           (mbid, artist_id))
        connection.commit()
        if not with_connection:
            self.close_database_connection(connection)

    def _remove_bl(self, rowid):
        """Remove bl row id"""
        connection = self.get_database_connection()
        connection.execute('DELETE FROM black_list'
                           ' WHERE black_list.rowid = ?', (rowid,))
        connection.commit()
        self.close_database_connection(connection)

    def add_history(self, track):
        """Add to history"""
        connection = self.get_database_connection()
        track_id = self.get_track(track, with_connection=connection)[0]
        rows = connection.execute("SELECT * FROM history WHERE track = ? ",
                                  (track_id,))
        if not rows.fetchone():
            connection.execute("INSERT INTO history (track) VALUES (?)",
                               (track_id,))
        connection.execute("UPDATE history SET last_play = DATETIME('now') "
                           " WHERE track = ?", (track_id,))
        connection.commit()
        self.close_database_connection(connection)

    def _clean_artists_table(self, with_connection=None):
        """Clean orphan artists"""
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        artists_ids = set([row[0] for row in connection.execute(
            "SELECT id FROM artists")])
        artist_2_artist_ids = set([row[0] for row in connection.execute(
            "SELECT artist FROM black_list")] +
            [row[0] for row in connection.execute(
            "SELECT artist FROM albums")] +
            [row[0] for row in connection.execute(
            "SELECT artist FROM tracks")])
        orphans = [(orphan,) for orphan in artists_ids - artist_2_artist_ids]
        connection.executemany('DELETE FROM artists WHERE id = (?);', orphans)
        if not with_connection:
            connection.commit()
            self.close_database_connection(connection)

    def _clean_albums_table(self, with_connection=None):
        """Clean orphan albums"""
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        orphan_black_ids = set([row[0] for row in connection.execute(
            """SELECT albums.id FROM albums
            LEFT JOIN black_list ON albums.id = black_list.album
            WHERE ( black_list.album IS NULL )""")])
        orphan_tracks_ids = set([row[0] for row in connection.execute(
            """SELECT albums.id FROM albums
            LEFT JOIN tracks ON albums.id = tracks.album
            WHERE tracks.album IS NULL""")])
        orphans = [(orphan,) for orphan in orphan_black_ids & orphan_tracks_ids]
        connection.executemany('DELETE FROM albums WHERE id = (?);', orphans)
        if not with_connection:
            connection.commit()
            self.close_database_connection(connection)

    def _clean_tracks_table(self, with_connection=None):
        """Clean orphan tracks"""
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        hist_orphan_ids = set([row[0] for row in connection.execute(
            """SELECT tracks.id FROM tracks
            LEFT JOIN history ON tracks.id = history.track
            WHERE history.track IS NULL""")])
        black_list_orphan_ids = set([row[0] for row in connection.execute(
            """SELECT tracks.id FROM tracks
            LEFT JOIN black_list ON tracks.id = black_list.track
            WHERE black_list.track IS NULL""")])
        orphans = [(orphan,) for orphan in hist_orphan_ids & black_list_orphan_ids]
        connection.executemany('DELETE FROM tracks WHERE id = (?);', orphans)
        if not with_connection:
            connection.commit()
            self.close_database_connection(connection)

    def clean_database(self, with_connection=None):
        """Wrapper around _clean_* methods"""
        if with_connection:
            connection = with_connection
        else:
            connection = self.get_database_connection()
        self._clean_tracks_table(with_connection=connection)
        self._clean_albums_table(with_connection=connection)
        self._clean_artists_table(with_connection=connection)
        connection.execute("VACUUM")
        if not with_connection:
            connection.commit()
            self.close_database_connection(connection)

    def purge_history(self, duration=__HIST_DURATION__):
        """Remove old entries in history"""
        connection = self.get_database_connection()
        connection.execute("DELETE FROM history WHERE last_play"
                           " < datetime('now', '-%i hours')" % duration)
        connection.commit()
        self.close_database_connection(connection)

    def _set_dbversion(self):
        """Add db version"""
        connection = self.get_database_connection()
        connection.execute('INSERT INTO db_info (version, name) VALUES (?, ?)',
                           (__DB_VERSION__, 'Sima DB'))
        connection.commit()
        self.close_database_connection(connection)

    def create_db(self):
        """ Set up a database
        """
        connection = self.get_database_connection()
        connection.execute(
            'CREATE TABLE IF NOT EXISTS db_info'
            ' (version INTEGER, name CHAR(36))')
        connection.execute(
            'CREATE TABLE IF NOT EXISTS artists (id INTEGER PRIMARY KEY, name'
            ' VARCHAR(100), mbid CHAR(36))')
        connection.execute(
            'CREATE TABLE IF NOT EXISTS albums (id INTEGER PRIMARY KEY,'
            ' artist INTEGER, name VARCHAR(100), mbid CHAR(36))')
        connection.execute(
            'CREATE TABLE IF NOT EXISTS tracks (id INTEGER PRIMARY KEY,'
            ' name VARCHAR(100), artist INTEGER, album INTEGER,'
            ' file VARCHAR(500), mbid CHAR(36))')
        connection.execute(
            'CREATE TABLE IF NOT EXISTS black_list (artist INTEGER,'
            ' album INTEGER, track INTEGER, updated DATE)')
        connection.execute(
            'CREATE TABLE IF NOT EXISTS history (last_play DATE,'
            ' track integer)')
        connection.commit()
        self.close_database_connection(connection)
        self._set_dbversion()


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
