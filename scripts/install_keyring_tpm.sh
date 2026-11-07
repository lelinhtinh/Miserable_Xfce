#!/usr/bin/env bash
# Install an opt-in TPM credential consumer; enrollment is a separate user step.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
[[ $EUID == 0 && $# == 1 ]] || { echo 'Usage (root): install_keyring_tpm.sh USER' >&2; exit 1; }
account=$1
account_uid=$(id -u -- "$account")
[[ $account_uid -ge 1000 && $account =~ ^[a-z_][a-z0-9_-]*\$?$ ]] || exit 1
systemd-analyze has-tpm2 --quiet
python -c 'import gi; gi.require_version("Secret", "1"); from gi.repository import Gio, GLib, Secret'
command -v zenity >/dev/null
unit=miserable-keyring-tpm-$account_uid.service
rule=49-miserable-keyring-tpm-$account_uid.rules
backup_dir=$(mktemp -d /var/backups/miserable-keyring-tpm.XXXXXXXX)
for file in /usr/local/libexec/miserable-keyring-tpm /etc/systemd/system/"$unit" /etc/polkit-1/rules.d/"$rule"; do
  if [[ -e $file ]]; then cp -a --parents "$file" "$backup_dir/"; fi
done
install -D -m 755 "$root/scripts/keyring_tpm.py" /usr/local/libexec/miserable-keyring-tpm
install -d -m 755 /etc/systemd/system /etc/polkit-1/rules.d
cat > "/etc/systemd/system/$unit" <<EOF
[Unit]
Description=TPM-backed GNOME keyring unlock for $account
After=user@$account_uid.service
ConditionPathExists=/etc/credstore.encrypted/miserable-keyring-$account_uid.cred

[Service]
Type=oneshot
User=$account
Environment=XDG_RUNTIME_DIR=/run/user/$account_uid
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$account_uid/bus
LoadCredentialEncrypted=miserable-keyring:/etc/credstore.encrypted/miserable-keyring-$account_uid.cred
ExecStart=/usr/local/libexec/miserable-keyring-tpm unlock
TimeoutStartSec=20
UMask=0077
LimitCORE=0
MemorySwapMax=0
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=read-only
RestrictAddressFamilies=AF_UNIX
EOF
chmod 644 "/etc/systemd/system/$unit"
cat > "/etc/polkit-1/rules.d/$rule" <<EOF
polkit.addRule(function(action, subject) {
    if (action.id === "org.freedesktop.systemd1.manage-units" &&
        action.lookup("unit") === "$unit" &&
        action.lookup("verb") === "start" &&
        subject.user === "$account" && subject.local && subject.active) {
        return polkit.Result.YES;
    }
});
EOF
chmod 644 "/etc/polkit-1/rules.d/$rule"
systemctl daemon-reload
systemd-analyze verify "/etc/systemd/system/$unit"
printf 'Installed. Backup: %s\nEnroll as the desktop user: %s enroll\n' "$backup_dir" /usr/local/libexec/miserable-keyring-tpm
