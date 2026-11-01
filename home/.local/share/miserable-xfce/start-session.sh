#!/usr/bin/env bash
set -euo pipefail
[[ ${XDG_SESSION_TYPE:-x11} == x11 ]] || exit 0
systemctl --user import-environment DISPLAY XAUTHORITY XDG_CURRENT_DESKTOP XDG_SESSION_TYPE
python "$HOME/.local/share/miserable-xfce/configure.py"
systemctl --user daemon-reload
systemctl --user start cortile.service skippy-overview.service miserable-sidebar-anchor.service whisker-win-key.service
