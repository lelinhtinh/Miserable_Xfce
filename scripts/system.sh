#!/usr/bin/env bash
# Privileged system steps. Invoke with sudo or pkexec; user configuration is separate.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
[[ $EUID == 0 ]] || { echo "Run with sudo or pkexec." >&2; exit 1; }
source /etc/os-release
[[ $ID == cachyos ]] || { echo "CachyOS is required." >&2; exit 1; }
read_packages() { sed '/^[[:space:]]*#/d; /^[[:space:]]*$/d' "$1"; }
case ${1:-} in
 snapshot)
  stamp=$(date +%Y%m%d-%H%M%S)
  backup_root=${2:-/var/lib/miserable-xfce/backups}
  record=$backup_root/$stamp
  install -d -m 0700 "$record" /var/lib/miserable-xfce/home-snapshots
  home_snapshot=/var/lib/miserable-xfce/home-snapshots/$stamp
  btrfs subvolume snapshot -r /home "$home_snapshot"
  number=$(snapper -c root create --type single --description "Miserable Xfce before reinstall $stamp" --userdata important=yes --print-number)
  pacman -Q > "$record/packages.txt"
  printf '%s\n' "$number" > "$record/root-snapshot-number"
  printf '%s\n' "$home_snapshot" > "$record/home-snapshot-path"
  tar -C "$root" --exclude='./.build' -czf "$record/source-before-cleanup.tar.gz" .
  sha256sum "$record/source-before-cleanup.tar.gz" > "$record/source-before-cleanup.sha256"
  printf '%s\n' "$record" > /var/lib/miserable-xfce/latest-snapshot
  echo "Snapshot record: $record; root #$number; home $home_snapshot"
  ;;
 baseline)
  record=$(cat /var/lib/miserable-xfce/latest-snapshot)
  number=$(cat "$record/root-snapshot-number")
  test -d "/.snapshots/$number/snapshot"
  btrfs subvolume show "$(cat "$record/home-snapshot-path")" >/dev/null
  sha256sum --check "$record/source-before-cleanup.sha256"
  # Remove only Plasma's desktop group/settings, retaining KDE libraries needed by apps.
  mapfile -t kde < <({ pacman -Qqg plasma 2>/dev/null || true; pacman -Qq cachyos-kde-settings 2>/dev/null || true; } | sort -u)
  if ((${#kde[@]})); then
   pacman -Rns --noconfirm "${kde[@]}"
  else
   echo 'KDE Plasma and cachyos-kde-settings are already absent.'
  fi
  mapfile -t packages < <(read_packages "$root/config/cachyos-xfce-packages.txt")
  pacman -Syu --needed --noconfirm "${packages[@]}"
  install -d /etc/lightdm/lightdm.conf.d
  printf '%s\n' '[Seat:*]' 'greeter-session=lightdm-gtk-greeter' 'user-session=xfce' > /etc/lightdm/lightdm.conf.d/50-xfce-migration.conf
  systemctl enable --force lightdm.service
  pacman -Q > "$record/packages-after-baseline.txt"
  echo "BASELINE_COMPLETE; snapshot record: $record"
  # Prepare the build dependencies in this authenticated operation; no user config changes here.
  bash "$root/scripts/system.sh" packages
  echo "CUSTOM_DEPENDENCIES_COMPLETE"
  ;;
 packages)
  mapfile -t packages < <(read_packages "$root/config/packages.txt")
  pacman -Syu --needed --noconfirm "${packages[@]}"
  ;;
 *) echo 'Usage: system.sh snapshot | baseline | packages' >&2; exit 2;;
esac
