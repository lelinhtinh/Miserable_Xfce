#!/usr/bin/env bash
set -euo pipefail
widget=${1:-sidebar}
case "$widget" in sidebar|sysstat|calendarevent) ;; *) exit 1;; esac
binary="$HOME/.local/bin/eww"
mkdir -p "$HOME/.cache/eww"
if ! "$binary" ping >/dev/null 2>&1; then
 "$binary" daemon >> "$HOME/.cache/eww/miserable-daemon.log" 2>&1
 for _ in {1..50}; do
  "$binary" ping >/dev/null 2>&1 && break
  sleep 0.1
 done
fi
if [[ "$widget" == sidebar ]]; then
 systemctl --user start miserable-sidebar-anchor.service
 height=$(xfconf-query -c xfce4-panel -p /panels/panel-2/size)
 "$binary" open --toggle --screen "<primary>" --pos "0x-$height" "$widget"
else
 "$binary" open --toggle "$widget"
fi
