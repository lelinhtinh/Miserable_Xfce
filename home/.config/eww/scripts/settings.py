#!/usr/bin/env python3
"""Single runtime configuration shared by the desktop helpers (Python 3.11+)."""
import json
import math
import os
from pathlib import Path
import sys
import tomllib
from zoneinfo import ZoneInfo

DEFAULT_FILE = Path(__file__).resolve().parents[1] / 'settings.toml'

def load_settings(file=None):
    path = Path(file or os.environ.get('MISERABLE_CONFIG', DEFAULT_FILE)).expanduser()
    with path.open('rb') as file:
        settings = tomllib.load(file)
    for key, low, high in [('latitude', -90, 90), ('longitude', -180, 180)]:
        value = settings['weather'][key]
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f'weather.{key} must be between {low} and {high}')
    ZoneInfo(settings['weather']['timezone'])
    if not 60 <= settings['weather']['refresh_seconds'] <= 86400:
        raise ValueError('weather.refresh_seconds must be between 60 and 86400')
    if not 20 <= settings['desktop']['panel_height'] <= 128:
        raise ValueError('desktop.panel_height must be between 20 and 128')
    command = settings['desktop']['store_command']
    if not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
        raise ValueError('desktop.store_command must be a nonempty array of arguments')
    display = settings.setdefault('display', {})
    for key, value in {'physical_output': 'DP-4', 'virtual_output': 'HDMI-0',
                       'virtual_mode': '1920x1080', 'virtual_rate': '60'}.items():
        display.setdefault(key, value)
    return settings

def path_setting(section, key):
    return Path(load_settings()[section][key]).expanduser()

if __name__ == '__main__':
    settings = load_settings()
    if len(sys.argv) == 3:
        value = settings[sys.argv[1]][sys.argv[2]]
        if isinstance(value, str) and value.startswith('~'):
            value = str(Path(value).expanduser())
        print(value if isinstance(value, (str, int, float)) else json.dumps(value, ensure_ascii=False))
    else:
        print(json.dumps(settings, ensure_ascii=False, indent=2))
