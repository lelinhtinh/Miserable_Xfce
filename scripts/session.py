#!/usr/bin/env python3
"""Reset to packaged Xfce defaults, or apply this repository to the running session."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from xfconf import apply_channel, reset

ROOT=Path(__file__).resolve().parents[1]
HOME=Path.home()
SERVICES=['cortile','skippy-overview','miserable-sidebar-anchor','whisker-win-key','miserable-display-tray']

def run(*args, check=True):
    return subprocess.run([str(a) for a in args],check=check,capture_output=True,text=True)

def stop_widgets():
    run('systemctl','--user','stop',*[s+'.service' for s in SERVICES],check=False)
    eww=HOME/'.local/bin/eww'
    if eww.exists():run(eww,'kill',check=False)
    run('xfce4-panel','--quit',check=False)
    # Wait for panel wrappers to release their config files before replacing them.
    for _ in range(30):
        if run('pgrep','-u',str(os.getuid()),'-x','xfce4-panel',check=False).returncode:
            break
        time.sleep(.1)

def start_panel():
    log=HOME/'.local/state/miserable-xfce/session.log';log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('a') as out:
        subprocess.Popen(['xfce4-panel'],stdout=out,stderr=out,start_new_session=True)
    time.sleep(2)
    if run('pgrep','-u',str(os.getuid()),'-x','xfce4-panel',check=False).returncode:
        raise RuntimeError(f'Panel did not start; see {log}')

def restart_settings():
    log=HOME/'.local/state/miserable-xfce/session.log';log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('a') as out:
        subprocess.Popen(['xfsettingsd','--replace'],stdout=out,stderr=out,start_new_session=True)
    time.sleep(.3)

def baseline():
    if not Path('/var/lib/miserable-xfce/latest-snapshot').exists():
        raise SystemExit('Create a system and home snapshot first.')
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup=HOME/'.local/state/miserable-xfce/vanilla-backups'/stamp;backup.mkdir(parents=True)
    stop_widgets()
    try:
        # Preserve display layout, input methods, audio and application data.
        for relative in ['.config/xfce4','.config/gtk-3.0/gtk.css','.config/gtk-3.0/settings.ini','.config/gtk-4.0/gtk.css','.config/gtk-4.0/settings.ini']:
            source=HOME/relative;dest=backup/relative
            if not source.exists():continue
            dest.parent.mkdir(parents=True,exist_ok=True)
            if source.is_dir():shutil.copytree(source,dest,symlinks=True)
            else:shutil.move(source,dest)
        channels=HOME/'.config/xfce4/xfconf/xfce-perchannel-xml'
        for file in channels.glob('*.xml'):
            if file.stem not in ['displays','keyboards']:reset(file.stem)
        panel=HOME/'.config/xfce4/panel'
        if panel.exists():shutil.rmtree(panel)
        apply_channel(Path('/etc/xdg/xfce4/panel/default.xml'))
        for file in Path('/etc/xdg/xfce4/xfconf/xfce-perchannel-xml').glob('*.xml'):
            apply_channel(file)
        restart_settings()
    finally:
        start_panel()
    theme=run('xfconf-query','-c','xsettings','-p','/Net/ThemeName').stdout.strip()
    icons=run('xfconf-query','-c','xsettings','-p','/Net/IconThemeName').stdout.strip()
    result={'theme':theme,'icons':icons,'backup':str(backup),'panel':'packaged /etc/xdg/xfce4/panel/default.xml'}
    (backup/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if theme!='Adwaita':raise RuntimeError('Packaged Xfce default was not applied')

def apply():
    stop_widgets()
    try:
        result=run(sys.executable,ROOT/'scripts/apply.py','--live','--include-built')
        print(result.stdout, end='')
        restart_settings()
        subprocess.run(['fc-cache','-f',str(HOME/'.local/share/fonts/miserable-xfce')],check=True)
    finally:
        start_panel()
    run(HOME/'.local/share/miserable-xfce/start-session.sh')
    print('Applied repository to live XFCE; user applications remained running.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['baseline','apply']);a=p.parse_args()
    if os.geteuid()==0 or os.environ.get('XDG_CURRENT_DESKTOP','').upper()!='XFCE':
        p.error('Run as the logged-in XFCE user.')
    (baseline if a.action=='baseline' else apply)()
