.. MPD_sima documentation master file, created by
   sphinx-quickstart on Wed Nov 11 13:21:17 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

#########################
MPD_sima's documentation
#########################

MPD_sima is meant to **auto-magically queue** tracks in MPD_, it is a non interactive client for MPD_.

Actually there is no magic involved, it relies on music metadata found in music
files tags and external information providers such as last.fm_. Then to use
MPD_sima (or any advanced music players, MPD_ among them), you need to ensure
your library is correctly tagged (see :ref:`metadata-convention`).

The default setting for MPD_sima is to queue similar artists thanks to last.fm_
suggestions but there are other possibilities, see :ref:`configuration-examples`.

**To queue tracks from similar artists:**
  - start playing a track in MPD
  - launch MPD_sima

.. code-block:: sh

    # runs against localhost MPD (or whatever is set in MPD_HOST/MPD_PORT)
    mpd-sima

    # runs against a specific MPD server
    mpd-sima --host mpd.example.org


#####################
User's documentation
#####################

.. toctree::
   :maxdepth: 2
   :glob:

   user/*


############
Unix Manuals
############

These manual pages were written for the Debian system (and may be used by others).

.. toctree::
   :maxdepth: 2
   :titlesonly:

   man/mpd-sima.1.rst
   man/mpd_sima.cfg.5.rst


##########################
Development documentation
##########################

.. toctree::
   :maxdepth: 2
   :titlesonly:

   dev/mpdclient
   dev/meta
   dev/lastfm
   dev/cache
   dev/simadb


##################
Indices and tables
##################

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. include:: links.rst

.. vim: spell spelllang=en
