#!/bin/sh
#
#   vinstall.sh
#
#   version: 0.2 : Date: 2013/11/13
#
#   TODO:
#           *
DEBUG=${DEBUG:-"0"}     #  Set to 1 in order to enable DEBUG message.
                        ## Use "export DEBUG=1" in the calling script to enable it
                        ##  or run:
                        #           >$ DEBUG=1 script_name.sh
                        ## Only error message will be printed with DEBUG="0"


PY3=${PY3:-$(which python3)}

# Test virtualenv presence
[ -x "$(which virtualenv)" ] || { echo "Cannot find virtualenv executable!"; exit 1; }
[ -x "$(which ${PY3})"  ] || { echo "Cannot find a python3.3 interpreter!"; exit 1; }
[ "$DEBUG" != "0" ] && echo "python: $PY3"

INSTALL_DIR=${INSTALL_DIR:-$(dirname $0)}
# canonicalize path
INSTALL_DIR=$(readlink -f ${INSTALL_DIR})
[ "$DEBUG" != "0" ] && echo "install dir: $INSTALL_DIR"

VENV_OPTIONS="--python=$PY3 --prompt="sima_venv" --no-site-packages --clear"
[ "$DEBUG" = "0" ] && VENV_OPTIONS="$VENV_OPTIONS --quiet"

virtualenv $VENV_OPTIONS $INSTALL_DIR/venv || { echo "something went wrong generating virtualenv"; exit 1; }

. $INSTALL_DIR/venv/bin/activate

PIP_OPTIONS=""
[ "$DEBUG" = "0" ] && PIP_OPTIONS="$PIP_OPTIONS --quiet"

pip $PIP_OPTIONS install --pre python-musicpd || exit 1

echo Installing mpd-sima
$(dirname $0)/setup.py --quiet install || exit 1

deactivate

SIMA_LAUNCHER=mpd-sima
SIMA_VLAUNCHER=$INSTALL_DIR/vmpd-sima

cat << EOF > "$SIMA_VLAUNCHER"
#!/bin/sh
. $INSTALL_DIR/venv/bin/activate
$SIMA_LAUNCHER "\$@"
EOF
chmod +x $SIMA_VLAUNCHER

echo Cleaning up
rm -rf $(dirname $0)/dist
rm -rf $(dirname $0)/build
rm -rf $(dirname $0)/sima.egg-info

echo

# vim: fileencoding=utf8
