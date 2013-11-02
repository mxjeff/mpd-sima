#!/bin/sh
#
#   SCRIPT NAME
#
#   version: 0.0 : Date: 1970/01/01 00:0:00
#
#   TODO:
#           *
DEBUG=${DEBUG:-"0"}     #  Set to 1 in order to enable DEBUG message.
                        ## Use "export DEBUG=1" in the calling script to enable it
                        ##  or run:
                        #           >$ DEBUG=1 script_name.sh
                        ## Only error message will be printed with DEBUG="0"


PY3=${PY3:-$(which python3.3)}
MUSICPD="http://media.kaliko.me/src/musicpd/dist/python-musicpd-0.3.1.tar.bz2"

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

pip $PIP_OPTIONS install $MUSICPD

deactivate

SIMA_LAUNCHER=$(readlink -f $(dirname $0))/launch
SIMA_VLAUNCHER=$(readlink -f $(dirname $0))/vlaunch
[ -x "$SIMA_LAUNCHER" ] || { echo "$SIMA_LAUNCHER not available"; exit 1; }

cat << EOF > $SIMA_VLAUNCHER
#!/bin/sh
. $INSTALL_DIR/venv/bin/activate
python $SIMA_LAUNCHER $@
EOF
chmod +x $SIMA_VLAUNCHER

echo 

# vim: fileencoding=utf8
