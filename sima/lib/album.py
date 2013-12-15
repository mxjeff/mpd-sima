# -*- coding: utf-8 -*-

from .track import Track

class MetaException(Exception):
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

    def __hash__(self):
        if self.mbid is not None:
            return hash(self.mbid)
        else:
            return id(self)


class Album(Meta):
    __hash__ = Meta.__hash__

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __eq__(self, other):
        """
        Perform mbid equality test if present,
        else fallback on self.name equality
        """
        if hasattr(other, 'mbid'):
            if other.mbid and self.mbid:
                return self.mbid == other.mbid
        return str(self) == str(other)

    @property
    def album(self):
        return self.name

# vim: ai ts=4 sw=4 sts=4 expandtab
