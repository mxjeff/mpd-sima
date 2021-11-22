========
mpd-sima
========

SYNOPSYS
--------

``mpd-sima [--daemon] [--config=conf_file] [--var-dir=var_directory] [--pid=pid_file] [--log=log_file] [--log-level=log_level] [--host=mpd_host] [--mpd_port=mpd_port]``

``mpd-sima {{-h | --help} --version}``

``mpd-sima [--config=conf_file] config-test``

``mpd-sima [--var-dir=var_directory] create-db``

``mpd-sima […] generate-config``

``mpd-sima [--var-dir=var_directory] purge-history``

``mpd-sima bl-view``

``mpd-sima bl-add-artist [artist]``

``mpd-sima bl-add-album [album]``

``mpd-sima bl-add-track [track]``

``mpd-sima bl-delete id``


DESCRIPTION
-----------

This manual page documents briefly the ``mpd-sima`` commands.

At start up default configuration is first overridden by user configuration in
mpd_sima.cfg (see FILES_) and finally command lines options are honored. For
instance you can override default MPD host (localhost) in your configuration
file or with ``-S my_mpd_server.local`` option. For default configuration see
CONFIGURATION_. See also environment variables special case for MPD host and
port in ENVIRONMENT_.


OPTIONS
-------

The program follows the usual GNU command line syntax, with long options
starting with two dashes ('-'). A summary of options is included below.

``-h``; ``--help``
   Print help and exit.

``--version``
   Print version and exit.

``--daemon``
   Start as a daemon. Log redirected to :file:`/dev/null`, usually setting
   ``--log`` and ``--pid`` options in daemon mode are a good idea to
   monitor/stop the process.

``-p pid_file``; ``--pid=pid_file``
   Use the specific file pid_file to store pid to.

   Default is not to store pid info.

``-l log_file``; ``--log=log_file``
   Use the specific file log_file to log messages to.

   Default is to log to stdout/stderr.

``-v log_level``; ``--log-level=log_level``
   Verbosity in [debug,info,warning,error].

   Default is to log info messages.

``-c conf_file``; ``--config=conf_file``
   Use the specific file conf_file to set up configuration instead of
   looking for the default user configuration file.

   Default is to look for :file:`${{XDG_CONFIG_HOME}}/mpd_sima/mpd_sima.cfg`.
   CLI option overrides any equivalent mentioned in configuration file, ie.
   launching mpd-sima with ``--port`` CLI option will ignore port setting in
   configuration file.

   For more details on configuration file see also `FILES <#files>`__ and `CONFIGURATION <#configuration>`__ sections.

``--var-dir=var_directory``
   Use the specific path var_directory to look for (or create) var files
   (ie. database) instead of looking at the default user data
   location.

   Default is to look in :file:`${{XDG_DATA_HOME}}/mpd_sima/`. Concerning
   :envvar:`XDG_DATA_HOME` see also `FILES section <#files>`__.

``-S mpd_host``; ``--host=mpd_host``
   Use the specific host mpd_host as MPD server.mpd_host can be an IP or
   a fully qualified domain name as long as your system can resolve it.
   This overrides MPD_HOST environment variable.
   Default is *localhost*.

   See also `ENVIRONMENT section <#environment>`__.

``-P mpd_port``; ``--port=mpd_port``
   Use the specific port number mpd_port on MPD server. This overrides
   MPD_PORT environment variable.Default is *6600*.

   See also `ENVIRONMENT section <#environment>`__

Command arguments
-----------------

``config-test``
   Test configuration file and exit. Uses the configuration file
   specified with ``--config`` or default location.
   Default is to use $XDG_CONFIG_HOME/mpd_sima/mpd_sima.cfg.

   config-test tests MPD connection and Tags plugin configuration.

``create-db``
   Create the database and exit. Uses folder specified with
   ``--var-dir`` or default directory.

   Default is to use :file:`${{XDG_DATA_HOME}}/mpd_sima/` (see `CONFIGURATION
   section <#configuration>`__ for more).

``generate-config``
   Generate a sample configuration file according to the current CLI
   options and environment variables. The configuration is written on stdout.

``purge-history``
   Purge play history in the database and exit. Uses folder specified
   with ``--var-dir`` or default directory.

   Default is to use :file:`${{XDG_DATA_HOME}}/mpd_sima/` (see `FILES section
   <#files>`__ for more).

``bl-view``
   View blocklist, useful to get entry IDs to remove with delete
   command.

``bl-add-artist artist``
   Add artist to the blocklist. If artist is not provided, try to get
   the currently playing artist.

``bl-add-album album``
   Add album to the blocklist. If album is not provided, try to get the
   currently playing album.

``bl-add-track track``
   Add track to the blocklist. If track is not provided, try to get the
   currently playing track.

``bl-delete id``
   Remove blocklist entry referenced by its id. Use bloclist view
   command to get the id.

ENVIRONMENT
-----------

:envvar:`MPD_HOST`, :envvar:`MPD_PORT`
   mpd-sima will look for MPD_HOST and MPD_PORT to override built-in
   configuration (set to "localhost:6600").

   mpd-sima expects MPD_HOST syntax as documented in mpc manual, cf.
   :manpage:`mpc(1)`. To use a password, provide a value of the form **password@host**.

:envvar:`HTTP_PROXY`, :envvar:`HTTPS_PROXY`
   mpd-sima honors HTTP_PROXY environment variables.


CONFIGURATION
-------------

:file:`mpd_sima.cfg`
   :file:`mpd_sima.cfg` is read if present. Otherwise built-in defaults are
   used. An example should be provided in the tarball within ``doc/examples/``.
   On Debian system please look in :file:`/usr/share/doc/mpd-sima`.

**DEFAULTS**

   Default is to look for MPD server at localhost:6600 (or
   :envvar:`MPD_HOST`/:envvar:`MPD_PORT` env. var. if set).

   The default plugins will use Last.fm to find similar tracks to queue and
   fallback to random if nothing if found.

   The get the defaults as detected by mpd-sima on your system you can
   run mpd-sima to print the config:

   ``mpd-sima generate-config``

.. only:: format_man

   For details about mpd_sima.cfg refer to the manual :manpage:`mpd_sima.cfg(5)`

.. only:: format_html

   For details about mpd_sima.cfg refer to the manual :doc:`mpd_sima.cfg.5`

.. include:: files.rst
.. include:: seealso.rst
.. include:: info.rst
