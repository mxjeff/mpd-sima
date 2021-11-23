============
mpd_sima.cfg
============

DESCRIPTION
-----------

This manual page documents briefly ``mpd-sima`` configuration options available
in user configuration file (see `FILES <#files>`__).

EXAMPLES
--------

File tags queue mode (offline mode).
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Here is an example of autoqueue using file tags only.

::

    [MPD]
    # Uses defaults for MPD connection
    #host = localhost
    #port = 6600
    #password = s3cr3t

    [sima] # Setup internal plugins
    # Tags plugin falls back to Random if nothing is found then Crop the queue
    internal = Tags, Random, Crop
    history_duration = 48  # 48h / 24 = 2 days
    queue_length = 2       # triggers autoqueue when 2 tracks remains to play

    [tags]
    # Look for files with tagged with genre "electronica" OR "IDM" OR "glitch"
    genre = electronica, IDM, glitch

    [crop]
    # keep 30 played tracks in playlist
    consume = 30


Album queue mode using last.fm recommendations (online mode).
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Here is an example of album queue configuration using online
recommendations system.

::

    [sima]
    history_duration = 96  # 4 days in hours, get a larger history for album mode
    queue_length = 5

    [crop]
    consume = 20

    [lastfm]
    queue_mode = album
    album_to_add = 1

.. _options:

Configuration file
------------------

The configuration file consists of sections, led by a ``[section]``
header and followed by ``name: value`` entries, with continuations in
the style of :rfc:`822` (see section 3.1.1, “LONG HEADER FIELDS”);
``name=value`` is also accepted. Lines beginning with ``'#'`` or ``';'``
are ignored and may be used to provide comments (*Nota Bene:* inline
comment are possible using ``'#'``).

The default values are used in the options lists below.

.. _MPD:

MPD section
^^^^^^^^^^^

This section is meant to configure MPD access, MPD host address / port
and password if necessary.

**[MPD]**

**host=localhost**
    Set MPD host. Use IP or FQDN.

**port=6600**
    Set host port to access MPD to.

**password=s3cr3t**
    Set MPD password to use. Do not use this option if you don't have
    enabled password protected access on your MPD server.

.. _log:

log section
^^^^^^^^^^^

Configure logging.

**[log]**

**logfile=**
    File to log to, usually in dæmon mode.Default (empty or unset) is to
    log to stdin/stdout.

**verbosity=info**
    Logging verbosity among debug, info, warning, error.

.. _daemon:

Process daemonization
^^^^^^^^^^^^^^^^^^^^^

Configure process daemon.

**[daemon]**

**daemon=false**
    Whether to daemonize process or not.

**pidfile=**
    Where to store process ID.

.. _sima:

sima section
^^^^^^^^^^^^

Core mpd-sima configuration.

**[sima]**


**internal=Lastfm, Random, Crop**
    mpd-sima's plugin management for internal source plugin and contrib (ie. external plugins).

    Plugins list is a comma separated string list.

    Optional plugin's configuration lays in its own section.
    For instance a "AwesomePlugin" declared here gets its configuration from the corresponding section "[awesomeplugin]".

    The default list of plugins to load at startup: Lastfm,Random,Crop.

    Crop is an utility plugin, it does not queue any tracks (cf. below).

    Random will queue a track at random if other plugins did not return any tracks.

    You can add, combine here as many plugins you want.

    The priority may be used to order them.

**history_duration=8**
    How far to look back in history to avoid to play twice the same track/title (duration in hours).

    The history_duration is also used to give priority to not recently played artists. Artist/tracks not in the scope of history have higther priority.

**queue_length=2**
    Threshold value triggering queue process.

**musicbrainzid=true**
    Use MusicBrainzIdentifier to search music (mainly for artists). Default is True, switch to False if you don't have MusicBrainzIdentifier set for at least 80% of you music library.

    Consider using these metadata as it enhances a lot artist/album/tracks identification. Use Picard to tag your file: https://picard.musicbrainz.org/.

**repeat_disable_queue=true**
    Prevent disabling queuing in repeat play mode.

**single_disable_queue=true**
    Prevent disabling queuing in single play mod


.. _crop:

Crop section
^^^^^^^^^^^^

crop plugin's configuration:

**[crop]**

**consume=10**
    How many played tracks to keep in the queue. Allows you to maintain a
    fixed length queue. Set to some negative integer to keep all played
    tracks.

**priority=10**
    Plugin priority

.. _random:

Random section
^^^^^^^^^^^^^^

When no similar tracks are found, falling back to random queuing.

Random plugin's configuration:

**[random]**

**track_to_add=1**
    How many track(s) to add.

**flavour=sensible**
    Different mode, aka random flavour, are available: **pure**, **sensible**,

      -  **pure**: pure random choice, even among recently played track.

      -  **sensible**: use play history to filter chosen tracks.

**priority=50**
    Plugin priority

.. _lastfm:

LastFm section
^^^^^^^^^^^^^^

LastFM plugin's configuration.


**[lastfm]**

**queue_mode=track**

    Queue mode to use among track, top and album (see `QUEUE MODE section
    <#queue_mode>`__ for info about queue modes).

**max_art=20**

    Maximum number of similar artist to retrieve from local media
    library. When set to something superior to zero, it tries to get as
    much similar artists from media library.

**depth=1**
    How many artists to base on similar artists search. The first is the
    last played artist and so on back in the history. Highter depth
    generates wider suggestions, it might help to reduce looping over
    same artists.

**single_album=false**
    Prevent from queueing a track from the same album (it often happens
    with OST). Only relevant in "track" queue mode.

**track_to_add=1**
    How many track(s) to add. Only relevant in ``top`` and ``track``
    queue modes. This is actually an upper limit, min(``max_art``,
    ``track_to_add``) will be used.

**album_to_add=1**
    How many album(s) to add. Only relevant in ``album`` queue modes.

**track_to_add_from_album=0**
    How many track(s) to add from each selected albums. Only relevant in
    ``album`` queue modes. When set to 0 or lower the whole album is
    queued.

**cache=True**
    Whether or not to use on-disk persistent http cache.When set to
    "true", sima will use a persistent cache for its http client. The
    cache is written along with the dbfile in:
    ``$XDG_DATA_HOME/mpd_sima/http/WEB_SERVICE``. If set to "false",
    caching is still done but in memory.

**priority=100**
    Plugin priority

.. _genre:

Genre section
^^^^^^^^^^^^^

Genre plugin's configuration.

This plugin permits offline autoqueuing based on files genre tag only.

It will try to queue tracks with similar genres (track's genre being read from
tags).


**[genre]**

**queue_mode=track**
    Queue mode to use among track, album (see
    `QUEUE MODE section <#queue_mode>`__ for more info).

**single_album=false**
    Prevent from queueing a track from the same album (it often happens with
    OST). Only relevant in "track" queue mode.

**priority=80**
    Plugin priority

**track_to_add=1**
    How many track(s) to add.

**album_to_add=1**
    How many album(s) to add. Only relevant in ``album`` queue mode.

.. _tags:

Tags section
^^^^^^^^^^^^

Tags plugin's configuration. There is no default configuration for this
plugin, it does not work out of the box.

This plugin permits offline autoqueuing based on files tags only.
Supported tags are ``'comment'``, ``'date'``, ``'genre'``, ``'label'``
and ``'originaldate'``.

In addition to supported tags above you can use an MPD filter. Please
refer to MPD protocol documentation for more.

All tag entries in this section are ANDed as a single MPD filter to look
for titles in the library. Moreover, for each tags, comma separated
values are also ORed. For instance setting "``genre=rock``" and
"``date=1982,1983,1984,1985,1986,1987,1988,1989``" will end up looking
for track tagged with genre ``rock`` and date within 1982 through 1989.
Using an MPD filter to replace ``date`` you can achieve the same with
the following setting: "``genre=rock``" and
"``filter=(date =~ '198[2-9]+')``" (provided your MPD server was
compiled with libpcre).

**[tags]**

**queue_mode=track**
    Queue mode to use among track, album (see `QUEUE MODES section
    <#queue_mode>`__ for info).

**single_album=false**
    Prevent from queueing a track from the same album (it often happens with
    OST). Only relevant in "track" queue mode.

**filter=**
    You can use here any valid MPD filter as defined in MPD protocol
    documentation.

**comment=**

**date=**

**genre=**

**label=**

**originaldate=**

**priority=80**
    Plugin priority

**track_to_add=1**
    How many track(s) to add.

**album_to_add=1**
   How many album(s) to add. Only relevant in ``album`` queue mode.

.. _queue_mode:

QUEUE MODES
-----------

Different queue modes are available with some plugins (check for
``queue_mode`` presence in plugin config).

mpd-sima tries preferably to chose among unplayed artists or at least
not recently played artist.

``track``
    Queue a similar track chosen at random from a similar artist.

``top``
    Queue a track from a similar artist, chosen among "top tracks"
    according to last.fm data mining.

``album``
    Queue a whole album chosen at random from a similar artist.

    *Nota Bene:* Due to the track point of view of database build upon
    tracks tags an album lookup for a specific artist will return albums
    as soon as this artist appears in a single track of the album. For
    instance looking for album from "The Velvet Underground" will fetch
    "Last Days" and "Juno" OSTs because the band appears on the
    soundtrack of these two movies. A solution is for you to set
    AlbumArtists tag to something different than the actual artist of the
    track. For compilations, OSTs etc. a strong convention is to use
    "Various Artists" for this tag.

    mpd-sima is currently looking for AlbumArtists tags and avoid album
    where this tag is set with "Various Artists". If a single track
    within an album is found with AlbumArtists:"Various Artists" the
    complete album is skipped and won't be queued.

.. include:: files.rst
.. include:: seealso.rst
.. include:: info.rst
