#!/usr/bin/env bash
set -euo pipefail
[[ ${XDG_SESSION_TYPE:-x11} == x11 ]] || exit 0
[[ -n ${DISPLAY:-} ]] || exit 1
services=(cortile.service skippy-overview.service miserable-sidebar-anchor.service whisker-win-key.service)
# Migrate previously enabled units: XFCE autostart must import the X11 environment first.
for service in "${services[@]}"; do
 legacy="$HOME/.config/systemd/user/default.target.wants/$service"
 if [[ -L "$legacy" ]]; then
  rm -- "$legacy"
 fi
done
systemctl --user import-environment DISPLAY XAUTHORITY XDG_CURRENT_DESKTOP XDG_SESSION_TYPE
if [[ $(python "$HOME/.config/eww/scripts/settings.py" display physical_at_login) == True ]]; then
 "$HOME/.local/bin/toggle-rustdesk-display" physical || true
fi
python "$HOME/.local/share/miserable-xfce/configure.py"
systemctl --user daemon-reload
systemctl --user start "${services[@]}"
