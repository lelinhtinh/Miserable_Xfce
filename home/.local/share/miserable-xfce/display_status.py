#!/usr/bin/env python3
"""Read the actual XRandR state for the display tray and notifications."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path.home() / '.config/eww/scripts'))
from settings import load_settings


def read_status():
    config = load_settings()['display']
    physical, virtual = config['physical_output'], config['virtual_output']
    if not physical or not virtual or physical == virtual:
        raise ValueError('Tên cổng màn hình thật và ảo phải khác nhau và không được để trống.')
    result = subprocess.run(['xrandr', '--query'], capture_output=True, text=True,
                            check=True, timeout=5, env={**os.environ, 'LC_ALL': 'C'})
    outputs = {}
    for line in result.stdout.splitlines():
        fields = line.split()
        if line[:1].isspace() or len(fields) < 2 or fields[1] not in ('connected', 'disconnected', 'unknown'):
            continue
        geometry = re.search(r'(?:^|\s)(\d+x\d+)[+-]\d+[+-]\d+(?:\s|$)', line)
        outputs[fields[0]] = {'connected': fields[1] == 'connected',
                              'resolution': geometry[1] if geometry else None}
    active = [name for name, output in outputs.items() if output['resolution']]
    p_active, v_active = physical in active, virtual in active
    mode = 'both' if p_active and v_active else 'physical' if p_active else 'virtual' if v_active else 'other'
    names = {'physical': 'Màn hình thật', 'virtual': 'Màn hình ảo'}
    if mode in names:
        name = physical if p_active else virtual
        label = f'{names[mode]} · {name} · {outputs[name]["resolution"]}'
    elif mode == 'both':
        label = f'Màn hình thật và ảo · {physical} + {virtual}'
    else:
        label = 'Màn hình khác · ' + ', '.join(active) if active else 'Không có màn hình đang hoạt động'
    target = 'virtual' if p_active else 'physical'
    target_output = virtual if target == 'virtual' else physical
    return {'mode': mode, 'label': label, 'outputs': outputs, 'target': target,
            'target_output': target_output,
            'can_switch': outputs.get(target_output, {}).get('connected', False)}


def notify(label, title='Trạng thái màn hình', error=False):
    try:
        subprocess.run(['notify-send', '-a', 'Miserable Xfce', '-i', 'video-display',
                        '-u', 'critical' if error else 'normal', '-t', '4000', title, label],
                       check=False, timeout=5, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        pass  # Notification availability must not affect display switching.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--notify', action='store_true')
    parser.add_argument('--error', action='store_true')
    args = parser.parse_args()
    try:
        status = read_status()
        label = status['label']
        print(json.dumps(status, ensure_ascii=False) if args.json else label)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        label = f'Không đọc được trạng thái màn hình: {exc}'
        print(label, file=sys.stderr)
        if args.notify:
            notify(label, error=True)
        return 1
    if args.notify:
        notify(label, title='Không thể hoàn tất chuyển màn hình' if args.error else 'Trạng thái màn hình',
               error=args.error)
    return 0


if __name__ == '__main__':
    sys.exit(main())
