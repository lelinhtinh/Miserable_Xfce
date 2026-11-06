#!/usr/bin/env bash
# Build the patched system package without installing or restarting LightDM.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
build_root=$(realpath -m -- "${1:-$root/.build/lightdm-package}")
[[ $EUID != 0 ]] || { echo 'Build as the desktop user.' >&2; exit 1; }
[[ ! -e $build_root ]] || { echo 'Choose a fresh build directory.' >&2; exit 1; }
mkdir -p "$build_root"
cp "$root/config/lightdm/PKGBUILD" "$build_root/"
cp "$root/vendor/lightdm-gtk-greeter-2.0.9.tar.gz" "$build_root/upstream-src.tar.gz"
cp "$root/patches/lightdm-gtk-greeter.patch" "$build_root/start-after-authentication.patch"
cd "$build_root"
makepkg --cleanbuild --noconfirm
python "$root/scripts/check_greeter.py" "$build_root/src/lightdm-gtk-greeter"
printf 'Built package in %s\n' "$build_root"
