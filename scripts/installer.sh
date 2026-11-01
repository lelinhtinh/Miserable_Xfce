#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
case ${1:-} in
 --snapshot|--baseline|--packages) action=${1#--}; shift; exec pkexec /usr/bin/bash "$root/scripts/system.sh" "$action" "$@" ;;
 --build) exec python "$root/scripts/build.py" ;;
 --apply) shift; exec python "$root/scripts/apply.py" --include-built "$@" ;;
 *) echo 'Usage: installer.sh --snapshot | --baseline | --packages | --build | --apply'; exit 2;;
esac
