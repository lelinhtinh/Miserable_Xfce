#!/usr/bin/env bash
# Optional ELAN 04f3:0c3d build; does not modify the running system.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
build_root=${1:-$root/.build/elan-sigfm}
[[ $EUID != 0 ]] || { echo 'Build as the desktop user.' >&2; exit 1; }
[[ ! -e "$build_root/source" ]] || { echo 'Choose a fresh build directory.' >&2; exit 1; }
mapfile -t source_spec < <(python - "$root" <<'PY'
import hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
lock = json.loads((root / 'config/sources.lock.json').read_text())
header = root / 'vendor/doctest/doctest.h'
assert hashlib.sha256(header.read_bytes()).hexdigest() == lock['doctest/doctest.h']['sha256']
print(lock['elan-sigfm']['url'])
print(lock['elan-sigfm']['commit'])
PY
)
[[ ${#source_spec[@]} == 2 ]] || exit 1
mkdir -p "$build_root/source"
git -C "$build_root/source" init -q
git -C "$build_root/source" remote add origin "${source_spec[0]}"
git -C "$build_root/source" fetch --depth=1 origin "${source_spec[1]}"
git -C "$build_root/source" checkout --detach FETCH_HEAD
git -C "$build_root/source" apply "$root/patches/elan-sigfm.patch"
install -D -m 644 "$root/vendor/doctest/doctest.h" "$build_root/source/libfprint/sigfm/vendor/doctest/doctest.h"
meson setup "$build_root/output" "$build_root/source" -Ddrivers=elan -Ddoc=false -Dintrospection=false -Dudev_rules=disabled -Dudev_hwdb=disabled --buildtype=release
meson compile -C "$build_root/output" -j 4
meson test -C "$build_root/output" --print-errorlogs sigfm fpi-device fpi-ssm fpi-assembling
install -m 755 "$build_root/output/libfprint/libfprint-2.so.2.0.0" "$build_root/libfprint-2.so.2"
(cd "$build_root" && sha256sum libfprint-2.so.2 > SHA256SUMS)
printf 'Built library and checksum in %s\n' "$build_root"
