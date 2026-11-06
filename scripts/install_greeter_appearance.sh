#!/usr/bin/env bash
# Usage: sudo bash scripts/install_greeter_appearance.sh USER WALLPAPER AVATAR
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
[[ $EUID == 0 && $# == 3 ]] || { echo 'Usage (root): install_greeter_appearance.sh USER WALLPAPER AVATAR' >&2; exit 1; }
account=$1
account_uid=$(id -u -- "$account")
[[ $account_uid != 0 ]] || { echo 'Choose a desktop account.' >&2; exit 1; }
[[ -f $2 && -f $3 ]] || { echo 'Wallpaper and avatar must be existing image files.' >&2; exit 1; }
grep -aFq 'start-session-on-authentication-success' /usr/bin/lightdm-gtk-greeter || {
  echo 'Install the patched lightdm-gtk-greeter package first.' >&2; exit 1;
}
account_path=/org/freedesktop/Accounts/User$account_uid
original_icon=$(busctl get-property org.freedesktop.Accounts "$account_path" org.freedesktop.Accounts.User IconFile)
backup_dir=$(mktemp -d /var/backups/lightdm-appearance.XXXXXXXX)
printf '%s\n' "$original_icon" > "$backup_dir/original-icon.txt"
for file in /etc/lightdm/lightdm-gtk-greeter.conf.d/70-fingerprint-appearance.conf /usr/local/share/lightdm/assets/background.png /usr/local/share/lightdm/assets/avatar.png; do
  if [[ -e $file ]]; then cp -a --parents "$file" "$backup_dir/"; fi
done
install -d -m 755 /usr/local/share/lightdm/assets /etc/lightdm/lightdm-gtk-greeter.conf.d
install -m 644 -- "$2" /usr/local/share/lightdm/assets/background.png
install -m 644 -- "$3" /usr/local/share/lightdm/assets/avatar.png
busctl call org.freedesktop.Accounts "$account_path" org.freedesktop.Accounts.User SetIconFile s /usr/local/share/lightdm/assets/avatar.png
install -m 644 "$root/config/lightdm/70-fingerprint-appearance.conf" /etc/lightdm/lightdm-gtk-greeter.conf.d/
printf 'Applies at the next greeter. Previous files: %s\n' "$backup_dir"
