Configuration examples
======================

Configuration location is ``${XDG_CONFIG_HOME}/mpd_sima/mpd_sima.cfg`` usually ``${XDG_CONFIG_HOME}``  is in ``${HOME}/.config/``.


Default configuration
---------------------

MPD_sima runs without explicit configuration as long as your MPD server is easy
to discover (``localhost:6600`` or exposed via environment variables ``MPD_HOST``/``MPD_PORT``).

The default configuration is to run in *track mode* with suggestions from
last.fm. In addition to `Lastfm` plugin set in **[sima]** section (within *internal*
option) there is a `Crop` plugin (keeps 10 tracks behind the currently playing
track) and a `Random` plugin (acting as a fallback if `Lastfm` did not find any
track to queue).

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

Here the configuration keeps the queue plugin *Lastfm* but configures it to queue albums (``queue_mode = album``) and ask for 2 albums to be add.

The configuration of MPD_sima in ``sima`` section is also modified for ``queue_length``. The value of 10 is to trigger album queueing when there are 10 tracks or less in the queue.

.. code:: ini

    [sima]
    internal = Crop, Lastfm, Random
    history_duration = 24
    queue_length = 10

    [crop]
    consume = 10

    [lastfm]
    queue_mode = album
    album_to_add = 2


Offline auto-queuing
--------------------

In addition to LastFm there are other *plugins* you can mix together or use alone to have a specific queue mode.

Genre auto-queuing
^^^^^^^^^^^^^^^^^^
With this mode MPD_sima is trying to queue tracks with genre tag similar to previously played tracks.

.. code:: ini

    [sima]
    internal = Crop, Genre, Random
    history_duration = 8

    [genre]
    queue_mode = track
    track_to_add = 1


Random queuing
^^^^^^^^^^^^^^
This mode allows random queuing with different flavour **pure** (total
randomness) or **sensible** (use play history to filter chosen tracks).
The **sensible** flavour will then tend to play track not in recently played.

The history duration is important for this plugin when running in **sensible** flavour since you might exhaust possible tracks to queue if the **history_duration** is larger than the total play time you have in your music library.

.. code:: ini

    [sima]
    internal = Crop, Random
    history_duration = 168

    [random]
    flavour = sensible

Tag queuing
^^^^^^^^^^^

This is the most complex and versatile offline mode. "Tags" plugin allows to queue track based on actual tags value.

Here is an example to have MPD_sima to queue only electronic music tagged with genres **electonica** or **IDM** or **glitch**:

.. code:: ini

    [sima]
    internal = Crop, Tags

    [tags]
    # Look for files with tagged with genre "electonica" OR "IDM" OR "glitch"
    genre = electonica, IDM, glitch

There are other supported tags, mainly **date**, **originaldate** or
**comment** (cf manual for the exact list). You can use more than one, entries
in tags sections are ANDed within a single MPD filter to look for titles.

For instance setting "genre=rock" and
"date=1982,1983,1984,1985,1986,1987,1988,1989" will end up looking for track
tagged with genre rock and date within 1982 through 1989:

.. code:: ini

    [sima]
    internal = Crop, Tags

    [tags]
    genre = rock
    date = 1982,1983,1984,1985,1986,1987,1988,1989

In case you want to make complex search in MPD library you can provide an `MPD
filter`_. This is a powerful feature, it comes at the cost of a different syntax, some might find it more readable some wont :D

For instance in the previous example you can simply replace **date** with the
current filter "`(date =~ '198[2-9]+')`":

.. code:: ini

    [sima]
    internal = Crop, Tags

    [tags]
    genre = rock
    filter = (date =~ '198[2-9]+')

And even go further and merge genre in the filter using "`((genre == 'rock') AND
(date =~ '198[2-9]+'))`".

.. code:: ini

    [sima]
    internal = Crop, Tags

    [tags]
    filter = (genre == 'rock' ) AND (date =~ '198[2-9]+'))


Since the setup for the filter can be tricky and it can be useful to validate
the syntax and have a look at what kind of artists the filter would return.

You can call MPD_sima to controls the configuration file. For instance with a config in `sima.cfg` run:

.. code:: bash

    ./mpd-sima --log-level info --config sima.cfg config-test


.. include:: ../links.rst

.. vim: spell spelllang=en
