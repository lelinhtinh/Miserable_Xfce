#!/usr/bin/env python3
"""Apply Miserable Xfce offline, or stage it in a temporary home."""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import xml.etree.ElementTree as ET
from xfconf import apply_channel

ROOT = Path(__file__).resolve().parents[1]

def restore(backup):
    backup = backup.resolve()
    manifest = json.loads((backup / 'manifest.json').read_text())
    target = Path(manifest['target'])
    for entry in reversed(manifest['files']):
        relative = Path(entry['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise SystemExit('Unsafe backup manifest path')
        dst = target / relative
        if dst.is_symlink() or dst.is_file():
            dst.unlink()
        if entry['existed']:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup / 'files' / relative, dst, follow_symlinks=False)
    print('Restored files to', target)


def apply(target, dry_run=False, include_built=False, live=False):
    target = target.resolve()
    if not re.fullmatch(r'/[A-Za-z0-9_./-]+', str(target)):
        raise SystemExit('Home path must contain only letters, digits, /, _, . and - for Exec templates.')
    sources = [ROOT / 'home']
    if include_built:
        built = ROOT / '.build/install-home'
        required = ['.local/bin/' + b for b in ('eww', 'skippy-xd', 'cortile', 'xcape')]
        required += ['.local/lib/xfce4/panel/plugins/libpulseaudio-fixed.so', '.local/share/icons/Numix-Circle/index.theme']
        missing = [r for r in required if not (built / r).is_file()]
        if missing:
            raise SystemExit('Build is incomplete: ' + ', '.join(missing))
        sources.append(built)
    files = {}
    for source in sources:
        for path in sorted(source.rglob('*')):
            if '__pycache__' in path.parts or path.suffix == '.pyc':
                continue
            if path.is_file() or path.is_symlink():
                files[path.relative_to(source)] = path
    personal = Path('.config/eww/settings.toml')
    settings_path = target / personal if (target / personal).is_file() else files[personal]
    with settings_path.open('rb') as file:
        settings = tomllib.load(file)
    if (target / personal).is_file():
        files.pop(personal)
    if live and target != Path.home().resolve():
        raise SystemExit('--live is only valid for the current home/session')
    if not dry_run and target == Path.home().resolve():
        if os.geteuid() == 0:
            raise SystemExit('Run as the desktop user, never with sudo.')
        if not live and subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', 'xfconfd'], stdout=subprocess.DEVNULL).returncode == 0:
            raise SystemExit('Log out of the desktop and run from a TTY: xfconfd is still running.')
    for relative in files:
        dst = target / relative
        # A symlinked parent could redirect writes outside the chosen home.
        for parent in dst.parents:
            if parent == target.parent:
                break
            if parent.is_symlink():
                raise SystemExit(f'Refusing symlinked destination directory: {parent}')
        if dst.exists() and dst.is_dir() and not dst.is_symlink():
            raise SystemExit(f'Expected a file, found directory: {dst}')
    if dry_run:
        for relative in files:
            print(relative)
        print(f'{len(files)} files')
        return
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup = target / '.local/state/miserable-xfce/backups' / stamp
    backup.mkdir(parents=True)
    manifest = {'target': str(target), 'files': []}
    manifest_path = backup / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    for relative, src in files.items():
        dst = target / relative
        existed = dst.exists() or dst.is_symlink()
        if existed:
            saved = backup / 'files' / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, saved, follow_symlinks=False)
        manifest['files'].append({'path': str(relative), 'existed': existed})
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    for relative, src in files.items():
        dst = target / relative
        if live and str(relative).startswith('.config/xfce4/xfconf/xfce-perchannel-xml/'):
            data = src.read_text().replace('@HOME@', str(target))
            tree = ET.fromstring(data)
            if src.name == 'xfce4-panel.xml':
                tree.find("./property[@name='panels']/property[@name='panel-2']/property[@name='size']").set('value', str(settings['desktop']['panel_height']))
            with tempfile.NamedTemporaryFile(suffix='.xml') as temp:
                ET.ElementTree(tree).write(temp, encoding='utf-8', xml_declaration=True)
                temp.flush()
                apply_channel(Path(temp.name))
            continue
        if dst.is_symlink():
            dst.unlink()
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_symlink():
            dst.unlink(missing_ok=True)
            dst.symlink_to(os.readlink(src))
            continue
        data = src.read_bytes()
        try:
            data = data.decode().replace('@HOME@', str(target)).encode()
        except UnicodeError:
            pass
        dst.write_bytes(data)
        shutil.copymode(src, dst)
    subprocess.run([sys.executable, str(target / '.local/share/miserable-xfce/configure.py'), '--home', str(target), *([] if live else ['--offline'])], check=True)
    print(f'Applied {len(files)} files to {target}')
    print('Backup:', backup)
    print(f'Rollback: python {ROOT / "scripts/apply.py"} --restore {backup}')
    print('Log in to Xfce (X11). Custom services start at login.')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--target', type=Path, default=Path.home(), help='alternate home for staging')
    p.add_argument('--live', action='store_true', help='apply xfconf through the running session D-Bus')
    p.add_argument('--include-built', action='store_true', help='include .build/install-home in backup and restore')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--restore', type=Path, metavar='BACKUP')
    a = p.parse_args()
    if a.restore:
        if a.dry_run or a.include_built:
            p.error('--restore cannot be combined with --dry-run or --include-built')
        # Apply the same offline requirement to rollback of the live home.
        manifest = json.loads((a.restore / 'manifest.json').read_text())
        if Path(manifest['target']).resolve() == Path.home().resolve():
            if os.geteuid() == 0 or subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', 'xfconfd'], stdout=subprocess.DEVNULL).returncode == 0:
                p.error('Rollback must run as the user from a TTY with xfconfd stopped.')
        restore(a.restore)
    else:
        apply(a.target, a.dry_run, a.include_built, a.live)
