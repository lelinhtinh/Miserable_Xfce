#!/usr/bin/env bash
# Retain encrypted credentials in a private backup; never remove keyring data.
set -euo pipefail
[[ $EUID == 0 && $# == 1 ]] || { echo 'Usage (root): uninstall_keyring_tpm.sh USER' >&2; exit 1; }
account=$1
account_uid=$(id -u -- "$account")
[[ $account_uid -ge 1000 ]] || exit 1
runuser -u "$account" -- /usr/local/libexec/miserable-keyring-tpm disable
systemctl stop "miserable-keyring-tpm-$account_uid.service"
backup_dir=$(mktemp -d /var/backups/miserable-keyring-tpm-disabled.XXXXXXXX)
for file in "/etc/systemd/system/miserable-keyring-tpm-$account_uid.service" "/etc/polkit-1/rules.d/49-miserable-keyring-tpm-$account_uid.rules" "/etc/credstore.encrypted/miserable-keyring-$account_uid.cred"; do
  if [[ -e $file ]]; then mv -- "$file" "$backup_dir/"; fi
done
systemctl daemon-reload
printf 'Disabled. Encrypted credential and configuration retained in %s\n' "$backup_dir"
