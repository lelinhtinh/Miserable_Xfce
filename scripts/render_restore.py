#!/usr/bin/env python3
"""Stage the snapshot's optional hardware settings; never change the live machine."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import tomllib

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / 'config/restore'


def render(config, target):
    with config.open('rb') as file:
        settings = tomllib.load(file)
    options = settings.get('restore', {})
    display = settings.get('display', {})
    for name in ('nvidia_virtual_display', 'lotus_server', 'pulse_codec_filter', 'wireplumber_video_only', 'dac_volume'):
        if not isinstance(options.get(name, False), bool):
            raise ValueError(f'restore.{name} must be true or false')
    if target.exists() and (target.is_symlink() or not target.is_dir() or any(target.iterdir())):
        raise ValueError('Choose a new or empty staging directory')
    files = {}

    def add(path, replacements=None):
        data = (TEMPLATES / path).read_bytes()
        for key, value in (replacements or {}).items():
            data = data.replace(('@' + key + '@').encode(), value.encode())
        files[path] = data

    for key, path in {
        'pulse_codec_filter': 'home/.config/systemd/user/pulseaudio.service.d/80-gstreamer-audio-only.conf',
        'wireplumber_video_only': 'home/.config/systemd/user/wireplumber.service.d/90-pulseaudio-coexistence.conf',
    }.items():
        if options.get(key, False):
            add(path)
    if options.get('dac_volume', False):
        values = {'ALSA_CARD': options['alsa_card'], 'ALSA_CONTROL': options['alsa_control']}
        if not all(isinstance(v, str) and re.fullmatch(r'[A-Za-z0-9_-]+', v) for v in values.values()):
            raise ValueError('ALSA card/control must be simple identifiers')
        add('home/.config/systemd/user/fix-simgot.service', values)
    nvidia_address = None
    if options.get('nvidia_virtual_display', False):
        bus = display['nvidia_bus_id']
        match = re.fullmatch(r'PCI:(\d+):(\d+):(\d+)', bus)
        if not match:
            raise ValueError('display.nvidia_bus_id must look like PCI:1:0:0')
        bus_number, device, function = map(int, match.groups())
        if not (0 <= bus_number <= 255 and 0 <= device <= 31 and 0 <= function <= 7):
            raise ValueError('NVIDIA PCI address out of range')
        nvidia_address = f'0000:{bus_number:02x}:{device:02x}.{function}'
        values = {'NVIDIA_BUS_ID': bus, 'PHYSICAL_OUTPUT': display['physical_output'],
                  'NVIDIA_PHYSICAL': display['nvidia_physical'], 'NVIDIA_VIRTUAL': display['nvidia_virtual']}
        if not all(isinstance(v, str) and re.fullmatch(r'[A-Za-z0-9:_-]+', v) for v in values.values()):
            raise ValueError('Invalid NVIDIA output identifiers')
        if values['NVIDIA_PHYSICAL'] == values['NVIDIA_VIRTUAL']:
            raise ValueError('Physical and virtual NVIDIA outputs must differ')
        add('system/etc/X11/xorg.conf.d/90-rustdesk-virtual-monitor.conf', values)
        edid_path = 'system/usr/share/rustdesk-virtual-display/monitor.edid'
        add(edid_path)
        edid = files[edid_path]
        if len(edid) != 128 or edid[:8] != bytes.fromhex('00ffffffffffff00') or sum(edid) % 256:
            raise ValueError('Invalid virtual monitor EDID')
    if options.get('lotus_server', False):
        add('lotus-server-logging.conf')

    # The generated installer checks prerequisites before installing any file.
    commands = ['#!/usr/bin/env bash', 'set -euo pipefail',
                '[[ $(id -u) != 0 ]] || { echo "Run as the desktop user, not root"; exit 1; }',
                'bundle=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)']
    needs_pulse = options.get('pulse_codec_filter') or options.get('wireplumber_video_only')
    if needs_pulse:
        commands.append('command -v pulseaudio >/dev/null || { echo "Install real PulseAudio first; see docs/restore.md"; exit 1; }')
        commands.append('! command -v pipewire-pulse >/dev/null || { echo "Choose the PulseAudio stack before installing these audio overrides"; exit 1; }')
    if options.get('wireplumber_video_only'):
        commands.append('command -v wireplumber >/dev/null || { echo "WirePlumber is required"; exit 1; }')
    if options.get('dac_volume'):
        commands.append('command -v amixer >/dev/null || { echo "alsa-utils is required"; exit 1; }')
    if options.get('lotus_server'):
        commands.append('command -v fcitx5-lotus-server >/dev/null || { echo "Install fcitx5-lotus-bin first"; exit 1; }')
    if nvidia_address:
        commands.append(f'[[ -e /sys/bus/pci/drivers/nvidia/{nvidia_address} ]] || {{ echo "Configured PCI device is not using NVIDIA"; exit 1; }}')
    for path in sorted(files):
        if path.startswith('home/'):
            commands.append(f'install -D -m644 --backup=numbered "$bundle/{path}" "$HOME/{path[5:]}"')
        elif path.startswith('system/'):
            commands.append(f'sudo install -D -m644 --backup=numbered "$bundle/{path}" {shlex.quote("/" + path[7:])}')
    if options.get('lotus_server'):
        commands += ['sudo install -D -m644 --backup=numbered "$bundle/lotus-server-logging.conf" "/etc/systemd/system/fcitx5-lotus-server@$(id -un).service.d/override.conf"',
                     'sudo systemctl daemon-reload', 'sudo systemctl enable "fcitx5-lotus-server@$(id -un).service"']
    if any(path.startswith('home/') for path in files):
        commands.append('systemctl --user daemon-reload')
    if needs_pulse:
        commands.append('systemctl --user enable pulseaudio.socket')
    if options.get('wireplumber_video_only'):
        commands += ['systemctl --user enable pipewire.socket wireplumber.service']
    if options.get('dac_volume'):
        commands.append('systemctl --user enable fix-simgot.service')
    commands.append('echo "Configuration installed. Review backups; changes take effect at next login/reboot."')
    target.mkdir(parents=True, exist_ok=True)
    for path, data in files.items():
        dst = target / path
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
    installer = target / 'install.sh'
    installer.write_text('\n'.join(commands) + '\n')
    installer.chmod(0o755)
    (target / 'manifest.json').write_text(json.dumps({path: hashlib.sha256(data).hexdigest() for path, data in files.items()}, indent=2) + '\n')
    return files


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'home/.config/eww/settings.toml')
    parser.add_argument('--target', type=Path, required=True)
    args = parser.parse_args()
    try:
        files = render(args.config, args.target)
    except (ValueError, KeyError) as error:
        parser.error(str(error))
    print(f'Rendered {len(files)} files to {args.target}; review install.sh before running it.')
