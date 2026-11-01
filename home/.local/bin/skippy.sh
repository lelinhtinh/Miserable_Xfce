#!/usr/bin/env bash
set -euo pipefail
systemctl --user start skippy-overview.service
"$HOME/.local/bin/eww" close sidebar >/dev/null 2>&1 || true
"$HOME/.local/bin/eww" close sysstat >/dev/null 2>&1 || true
exec "$HOME/.local/bin/skippy-xd" --expose --desktop -1
