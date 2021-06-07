Installation
============

\*nix distributions
-------------------

Use your package manager, there are packages for Debian (and probably derivatives) and Arch via AUR.


Python virtualenv
-----------------

.. code:: bash

    # create venv
    python -m venv mpd_sima-venv
    # activate
    . ./mpd_sima-venv/bin/activate
    # Install the application
    pip install MPD_sima
    # Print help message
    mpd-sima --help

From Source
-----------

Virtualenv installation from source:

Run ``python ./vinstall.py`` from the source to generate the python virtualenv and install requirements.

It will setup a virtualenv within a "venv" directory (same level as vinstall.py file). It should also write a shell wrapper to run mpd-sima within the virtualenv.


.. code:: bash

    # Clone master branch
    git clone -b master git@gitlab.com:kaliko/sima.git
    # setup virtualenv
    python ./vinstall.py
    ./vmpd-sima --help

To restart from scratch or pull latest changes

.. code:: bash

    # Get into the local git repo (here sima directory)
    cd sima
    # Remove virtualenv
    rm -rf ./venv
    # Fetch and merge latest changes
    git pull
    # setup virtualenv
    python ./vinstall.py
    ./vmpd-sima --help


.. vim: spell spelllang=en
