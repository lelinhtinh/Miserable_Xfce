#!/usr/bin/env bash
# Explicit opt-in for USB ELAN 04f3:0c3d; leaves PAM and enrollments untouched.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
[[ $EUID == 0 ]] || { echo 'Run with sudo or pkexec.' >&2; exit 1; }
build_root=${1:-$root/.build/elan-sigfm}
(cd "$build_root" && sha256sum -c SHA256SUMS)
dependencies=$(ldd "$build_root/libfprint-2.so.2")
if [[ $dependencies == *'not found'* ]]; then
  printf '%s\n' "$dependencies" >&2
  exit 1
fi
systemctl cat fprintd.service >/dev/null
backup_dir=$(mktemp -d /var/backups/elan-sigfm.XXXXXXXX)
for file in /usr/local/lib/elan-0c3d-sigfm/libfprint-2.so.2 /etc/systemd/system/fprintd.service.d/60-elan-0c3d-sigfm.conf; do
  if [[ -e $file ]]; then cp -a --parents "$file" "$backup_dir/"; fi
done
install -d -m 755 /usr/local/lib/elan-0c3d-sigfm /etc/systemd/system/fprintd.service.d
systemctl stop fprintd
install -m 755 "$build_root/libfprint-2.so.2" /usr/local/lib/elan-0c3d-sigfm/libfprint-2.so.2
install -m 644 "$root/config/fingerprint/60-elan-0c3d-sigfm.conf" /etc/systemd/system/fprintd.service.d/
systemctl daemon-reload
systemctl start fprintd
printf 'Installed. Previous files: %s\n' "$backup_dir"
