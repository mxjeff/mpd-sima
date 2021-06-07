.. _metadata-convention:

Music library metadata convention
=================================

In order to choose which tracks to add, your music library needs to follow some
conventions regarding **metadata** [1]_. Files in your library should be tagged
with the metadata best describing the music file.

Be aware that the benefit from a well tagged library goes far beyond the use of
MPD_sima alone. Any piece of software will take advantage of a well tagged
library, especially music players. If you already use MPD_ as a player, you are
already well aware of it.

A minimal set of tags required for MPD_sima to work would be ``ARTIST``, ``ALBUM``, ``TITLE``, but in order to work properly and with all plugins a more complete tag set is recommended.

MPD_sima is actually expecting: ``ARTIST``, ``ALBUM``, ``TITLE``, ``ALBUMARTIST``,
``GENRE`` and some MusicBrainzIDs_ [2]_ as well: ``MUSICBRAINZ_ARTISTID``,
``MUSICBRAINZ_ALBUMID`` and ``MUSICBRAINZ_ALBUMARTISTID``.

There are very good tools to (auto)tag you music library, picard_ is highly
recommended, beets_ is also a good alternative. Actually any piece of software
tagging your files with the most common tags (albumartist especially) and
MusicBrainzIDs_ [3]_ should be fine.



.. [1] commonly named tags or `ID3 tags`_ for MP3, but most audio format have some metadata features.

.. [2] MusicBrainz_ provides a reliable and unambiguous form of music identification; this music identification is performed through the use of MusicBrainz Identifiers (MBIDs_).
.. [3] cf 2_

.. include:: ../links.rst

.. vim: spell spelllang=en
