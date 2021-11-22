FILES
-----

:file:`${{XDG_CONFIG_HOME}}/mpd_sima/mpd_sima.cfg`
        Configuration file.

:file:`${{XDG_DATA_HOME}}/mpd_sima/sima.db`
        SQLite internal DB file. Stores play history and blocklists.

:file:`${{XDG_DATA_HOME}}/mpd_sima/WEB_SERVICE/`
        HTTP cache.

.. only:: format_man

   Usually :envvar:`XDG_DATA_HOME` is set to :file:`${{HOME}}/.local/share` and
   :envvar:`XDG_CONFIG_HOME` to :file:`${{HOME}}/.config` (for regular users).
   You may override them using command line option ``--var-dir`` and ``--config``
   (cf. :manpage:`mpd-sima(1)`)

.. only:: format_html

   Usually :envvar:`XDG_DATA_HOME` is set to :file:`${{HOME}}/.local/share` and
   :envvar:`XDG_CONFIG_HOME` to :file:`${{HOME}}/.config` (for regular users).
   You may override them using command line option ``--var-dir`` and ``--config``
   (cf. :doc:`mpd-sima.1`)
