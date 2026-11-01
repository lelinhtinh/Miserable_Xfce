#!/usr/bin/python
import json
import os
import re
import subprocess
import sys
import time
from settings import load_settings
settings = load_settings()
host = settings["network"]["ping_host"]
if not host or host.startswith("-"):
    raise ValueError("network.ping_host cannot be empty or start with -")

if sys.argv[1] == 'disk':
    path = os.path.expanduser(settings['storage']['sidebar_path'])
    try:
        stat = os.statvfs(path)
    except OSError:
        print(json.dumps(dict(value='— GiB', description=path, css='low', tooltip='Không tìm thấy thư mục: ' + path), ensure_ascii=False))
        raise SystemExit(0)
    available = stat.f_bavail * stat.f_frsize
    total = stat.f_blocks * stat.f_frsize
    fraction = available / total if total else 0
    gib = available / 1024**3
    value = f'{gib:.1f} GiB' if gib < 1024 else f'{gib / 1024:.1f} TiB'
    data = dict(value=value, description=path,
                css='low' if fraction < .05 else 'good' if fraction < .15 else 'healthy',
                tooltip=f'Dung lượng khả dụng của {path}: {value} ({fraction:.0%} còn trống)')
else:
    network_name = 'Internet'
    try:
        route = subprocess.run(['ip', '-j', 'route', 'get', host],
                               capture_output=True, text=True, timeout=2)
        device = json.loads(route.stdout)[0]['dev']
        networks = subprocess.run(
            ['nmcli', '-t', '--escape', 'no', '-f', 'ACTIVE,SSID',
             'device', 'wifi', 'list', 'ifname', device, '--rescan', 'no'],
            capture_output=True, text=True, timeout=2)
        for line in networks.stdout.splitlines():
            if line.startswith('yes:') and line[4:]:
                network_name = line[4:]
                break
    except (subprocess.SubprocessError, ValueError, KeyError, IndexError, OSError):
        pass
    try:
        result = subprocess.run(['ping', '-n', '-c', '2', '-i', '0.2', '-W', '2', '-w', '3', host],
                                env={**os.environ, 'LC_ALL': 'C'}, capture_output=True, text=True, timeout=4)
        match = re.search(r'=\s*[\d.]+/([\d.]+)/[\d.]+/[\d.]+\s*ms', result.stdout)
        if not match:
            raise ValueError('No ICMP reply')
        latency = float(match[1])
        loss = re.search(r'([\d.]+)% packet loss', result.stdout)
        lost = float(loss[1]) if loss else 0
        data = dict(value=f'{latency:.0f} ms', description=network_name,
                    css='good' if lost or latency >= 100 else 'online',
                    tooltip=f'{network_name} · Ping tới {host}: trung bình {latency:.1f} ms · mất gói {lost:g}% · đo mỗi 10 giây')
    except (subprocess.SubprocessError, ValueError, OSError):
        data = dict(value='— ms', description=network_name, css='low',
                    tooltip='Không nhận được phản hồi ping từ 1.1.1.1. Có thể mất kết nối hoặc ICMP bị chặn; thử lại mỗi 10 giây.')
if sys.argv[1] != 'disk':
    data['measured_at'] = time.time_ns()
print(json.dumps(data, ensure_ascii=False))
