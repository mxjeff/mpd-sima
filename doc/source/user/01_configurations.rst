Configuration examples
======================

Configuration location is ``${XDG_CONFIG_HOME}/mpd_sima/mpd_sima.cfg`` usually ``${XDG_CONFIG_HOME}``  is in ``${HOME}/.config/``.


Default configuration
---------------------

MPD_sima runs without explicit configuration as long as your MPD server is easy
to discover (``localhost:6600`` or exposed via environment variables ``MPD_HOST``/``MPD_PORT``).

The default configuration is to run in *track mode* with suggestions from last.fm:

.. code:: ini

    [MPD]
    # Change MPD server here
    #host = mpdserver.example.org
    #port = 6600

    [sima]
    internal = Crop, Lastfm, Random
    history_duration = 8
    queue_length = 2

    [crop]
    consume = 10

    [lastfm]
    queue_mode = track
    single_album = False
    track_to_add = 1

Album mode
^^^^^^^^^^

One of the first request added to MPD_sima was album mode. It allows to queue whole album instead of single tracks.

Here the configuration keeps the queue plugin *Lastfm* but configure it to queue albums (``queue_mode = album``) and ask for 2 albums to be add.

The configuration of MPD_sima in ``sima`` section is also modified for ``queue_length``. The value of 10 is to trigger album queueing when there are 10 tracks or less in the queue.

.. code:: ini

    [MPD]
    # Change MPD server here
    #host = mpdserver.example.org
    #port = 6600

    [sima]
    internal = Crop, Lastfm, Random
    history_duration = 8
    queue_length = 10

    [crop]
    consume = 10

    [lastfm]
    queue_mode = album
    album_to_add = 2


Offline auto-queuing
--------------------


.. vim: spell spelllang=en
