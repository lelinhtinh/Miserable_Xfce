#!/usr/bin/env bash
set -euo pipefail
cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/eww"
mkdir -p "$cache_dir"
launch() { setsid -f "$@" </dev/null >>"$cache_dir/quick-actions.log" 2>&1; }
if [[ ${1:-} == --lock-internal ]]; then
 if command -v xfce4-screensaver >/dev/null; then
  if ! pgrep -u "$(id -u)" -f '^(/usr/bin/)?xfce4-screensaver([[:space:]]|$)' >/dev/null; then
   launch xfce4-screensaver
   sleep 0.7
  fi
 fi
 if ! xflock4; then
  notify-send 'Khóa màn hình' 'Không thể kết nối dịch vụ khóa màn hình.'
  exit 1
 fi
 exit 0
fi
case ${1:-} in home|store|network|screenshot|lock|logout) ;; *) exit 2;; esac
"$HOME/.local/bin/eww" close sidebar >/dev/null 2>&1 || true
case "$1" in
 home) launch thunar "$HOME";;
 store)
  mapfile -d '' -t command < <(python - <<'CONFIG'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home()/'.config/eww/scripts'))
from settings import load_settings
for arg in load_settings()['desktop']['store_command']:
    sys.stdout.buffer.write(arg.encode() + b'\0')
CONFIG
)
  launch "${command[@]}";;
 network) launch nm-connection-editor;;
 screenshot) sleep 0.3; launch "$HOME/.local/share/miserable-xfce/screenshot.sh";;
 lock) launch "$0" --lock-internal;;
 logout) launch xfce4-session-logout;;
esac
