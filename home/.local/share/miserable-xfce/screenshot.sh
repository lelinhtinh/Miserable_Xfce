#!/usr/bin/env bash
set -euo pipefail
# Use the X11 backend in this XFCE session.
if [[ ${XDG_SESSION_TYPE:-x11} == x11 ]]; then export QT_QPA_PLATFORM=xcb; fi
exec /usr/bin/flameshot gui
