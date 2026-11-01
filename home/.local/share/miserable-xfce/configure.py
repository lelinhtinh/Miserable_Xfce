#!/usr/bin/env python3
"""Apply personal settings; --offline renders files without contacting the session."""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET


def configure(home, offline=False):
    sys.path.insert(0, str(home / '.config/eww/scripts'))
    from settings import load_settings
    settings = load_settings(home / '.config/eww/settings.toml')['desktop']
    panel = home / '.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml'
    if offline:
        tree = ET.parse(panel)
        tree.find("./property[@name='panels']/property[@name='panel-2']/property[@name='size']").set('value', str(settings['panel_height']))
        tree.write(panel, encoding='utf-8', xml_declaration=True)
    else:
        subprocess.run(['xfconf-query', '-c', 'xfce4-panel', '-p', '/panels/panel-2/size', '-s', str(settings['panel_height'])], check=True)
    if not offline and settings['wallpaper']:
        wallpaper = Path(settings['wallpaper'].replace('~', str(home), 1)).expanduser()
        if not wallpaper.is_file():
            raise ValueError(f'Wallpaper does not exist: {wallpaper}')
        monitors = subprocess.check_output(['xrandr', '--query'], text=True)
        for line in monitors.splitlines():
            parts = line.split()
            if len(parts) < 2 or parts[1] != 'connected':
                continue
            for workspace in range(4):
                prefix = f'/backdrop/screen0/monitor{parts[0]}/workspace{workspace}'
                for name, kind, value in [('last-image', 'string', str(wallpaper)), ('image-style', 'int', '5')]:
                    subprocess.run(['xfconf-query', '-c', 'xfce4-desktop', '-p', prefix + '/' + name,
                                    '-n', '-t', kind, '-s', value], check=True)
    helpers = home / '.config/xfce4/helpers.rc'
    helpers.write_text(f"WebBrowser={settings['browser']}\nTerminalEmulator={settings['terminal']}\n")
    dock = home / '.config/xfce4/panel/docklike-11.rc'
    content = dock.read_text()
    dock.write_text(re.sub(r'^pinned=.*$', 'pinned=' + ';'.join(settings['pinned_apps']) + ';', content, flags=re.MULTILINE))

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--home', type=Path, default=Path.home())
    p.add_argument('--offline', action='store_true')
    p.add_argument('--restart-panel', action='store_true')
    args = p.parse_args()
    configure(args.home, args.offline)
    if args.restart_panel and not args.offline:
        subprocess.run(['xfce4-panel', '--restart'], check=True)
