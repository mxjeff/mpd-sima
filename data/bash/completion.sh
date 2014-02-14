# Copyright (c) 2010, 2011, 2013, 2014 Jack Kaliko <kaliko@azylum.org>
#
#  This file is part of MPD_sima
#
#  MPD_sima is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MPD_sima is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MPD_sima.  If not, see <http://www.gnu.org/licenses/>.
#
#

# Bash completion file
#
# On debian system either place this file in etc/bash_completion.d/ or source it
# in your barshrc.

_sima() {
    local cur prev opts
    COMPREPLY=()
    _get_comp_words_by_ref cur prev
    opts="-c --config \
          -p --pid \
          -l --log \
          -v --log-level \
          -S --host \
          -P --mpd_port \
          -h --help --version \
          --var_dir"

    if [[ ${cur} == -* || ${COMP_CWORD} -eq 1 ]] ; then
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi

    case "${prev}" in
        --var_dir)
            _filedir -d
            ;;
        -v|--log-level)
            COMPREPLY=( $(compgen -W "debug info warning error" -- ${cur} ))
            ;;
        -p|--pid|-l|--log)
            _filedir
            ;;
        -c|--config)
            _filedir
            if [ -z $XDG_DATA_HOME ]; then
                local confnames=$(for x in $(ls -1 $HOME/.config/mpd_sima/*.cfg 2>/dev/null) ; do echo "${x##*//}"; done)
            else
                local confnames=$(for x in $(ls -1 $HOME/.config/mpd_sima/*.cfg $XDG_DATA_HOME/mpd_sima/*.cfg 2>/dev/null) ; do echo "${x##*//}"; done)
            fi
            COMPREPLY+=( $(compgen -W "${confnames}") )
            return 0
            ;;
        --host|-S)
            COMPREPLY=( $(compgen -A hostname ${cur}) )
            ;;
        *)
            ;;
    esac
}
complete -F _sima mpd_sima
complete -F _sima mpd-sima

_art_names_list() {
    local IFS=$'\n'
    compgen -W "${artists}" -- ${cur}
}

_simadb_cli() {
    local cur prev opts artists
    local IFS=$'\n'
    COMPREPLY=()
    _get_comp_words_by_ref cur prev
    opts="--add_similarity -a --remove_similarity --remove_artist \
    --purge_hist --view_artist --view_all \
    --bl_curr_trk --bl_curr_art --bl_curr_al --bl_art --remove_bl --view_bl \
    --dbfile -d \
    --host -S --port -P \
    --reciprocal -r --check_names -c \
    --version -h --help"
    opts=$(echo $opts | sed 's/ /\n/g')

    if [[ ${cur} == -* || ${COMP_CWORD} -eq 1 ]] ; then
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi

    case "${prev}" in
        --bl_curr*|--view_bl|--view_all|--purge_hist|--version|--help|-h)
            return 0
            ;;
        -d|--dbfile)
            _filedir
            ;;
        --host|-S)
            COMPREPLY=( $(compgen -A hostname ${cur}) )
            ;;
        -a|--add_similarity|--view_artist|-v|--bl_art)
            if [ -x /usr/bin/mpc ]; then
                artists=$(for x in $(/usr/bin/mpc list artist) ; do echo "'${x}'"; done)
                COMPREPLY=( $(compgen -W "${artists}" -- ${cur}) )
                return 0
            fi
            # It should also complete artist name when the string ends with a comma
            return 0
            ;;
        *)
            ;;
    esac
}
complete -F _simadb_cli simadb_cli
