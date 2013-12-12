# -*- coding: utf-8 -*-

from .simastr import SimaStr
from .track import Track

class MetaException(Exception):
    pass

class NotSameArtist(MetaException):
    pass


class Meta:

    def __init__(self, **kwargs):
        self.name = None
        self.mbid = None
        if 'name' not in kwargs:
            raise MetaException('need at least a "name" argument')
        self.__dict__.update(kwargs)

    def __repr__(self):
        fmt = '{0}(name="{1.name}", mbid="{1.mbid}")'
        return fmt.format(self.__class__.__name__, self)

    def __str__(self):
        return str(self.name)

    def __eq__(self, other):
        """
        Perform mbid equality test if present,
        else fallback on fuzzy equality
        """
        if hasattr(other, 'mbid'):
            if other.mbid and self.mbid:
                return self.mbid == other.mbid
        return SimaStr(str(self)) == SimaStr(str(other))


class Artist(Meta):

    def __init__(self, **kwargs):
        self._aliases = []
        super().__init__(**kwargs)

    def append(self, name):
        self._aliases.append(name)

    @property
    def names(self):
        return self._aliases + [self.name]

    def __add__(self, other):
        if isinstance(other, Artist):
            if self.mbid == other.mbid:
                res = Artist(**self.__dict__)
                res._aliases.extend(other.names)
                return res
            else:
                raise NotSameArtist('different mbids: {0} and {1}'.format(self, other))


class TrackMB(Track):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if hasattr(self, 'musicbrainz_artistid'):
            self.artist = Artist(mbid=self.musicbrainz_artistid,
                                 name=self.artist)

# vim: ai ts=4 sw=4 sts=4 expandtab

