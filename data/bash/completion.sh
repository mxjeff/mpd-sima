# Copyright (c) 2010, 2011, 2013, 2014, 2015, 2021, 2022 kaliko <kaliko@azylum.org>
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
          -P --port \
          -h --help --version \
          --var-dir \
          -d --daemon \
          config-test \
          create-db \
          generate-config \
          purge-history \
          bl-view \
          bl-add-artist \
          bl-add-album \
          bl-add-track \
          bl-delete \
          random"

    if [[ ${cur} == -* || ${COMP_CWORD} -eq 1 ]] ; then
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi

    case "${prev}" in
        --var-dir)
            _filedir -d
            ;;
        -v|--log-level)
            COMPREPLY=( $(compgen -W "debug info warning error" -- ${cur} ))
            ;;
        -p|--pid|-l|--log|-c|--config)
            _filedir
            ;;
        --host|-S)
            _known_hosts_real -a "${cur}"
            ;;
        *)
            COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
            ;;
    esac
}
complete -o nosort -F _sima mpd_sima
complete -o nosort -F _sima mpd-sima
