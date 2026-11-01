"""Check installation, editable settings, resources and the live xfconf transport."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import apply as installer

class DesktopTests(unittest.TestCase):
    def install(self, target, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            installer.apply(target, **kwargs)

    def test_install_and_restore_keep_unrelated_files_and_symlinks(self):
        with tempfile.TemporaryDirectory(prefix='miserable-test-') as tmp:
            home = Path(tmp) / 'new-user'
            original = home / '.config/eww/eww.scss'
            original.parent.mkdir(parents=True)
            original.write_text('old style');original.chmod(0o600)
            outside = Path(tmp) / 'outside';outside.write_text('unchanged')
            link = home / '.config/rofi/config.rasi'
            link.parent.mkdir(parents=True);link.symlink_to(outside)
            other = home / '.config/other-app';other.write_text('keep')
            self.install(home)
            self.assertEqual(outside.read_text(), 'unchanged')
            self.assertEqual(other.read_text(), 'keep')
            self.assertFalse(link.is_symlink())
            for p in home.rglob('*'):
                if p.is_file() and '/backups/' not in str(p):
                    self.assertNotIn(b'@HOME@',p.read_bytes(),p)
            backup = next((home / '.local/state/miserable-xfce/backups').iterdir())
            with contextlib.redirect_stdout(io.StringIO()):installer.restore(backup)
            self.assertEqual(original.read_text(),'old style')
            self.assertEqual(original.stat().st_mode & 0o777,0o600)
            self.assertTrue(link.is_symlink())
            self.assertFalse((home / '.config/eww/settings.toml').exists())

    def test_reinstall_preserves_personal_settings_and_renders_panel(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)/'user';self.install(home)
            config=home/'.config/eww/settings.toml'
            config.write_text(config.read_text().replace('panel_height = 46','panel_height = 52').replace('browser = "google-chrome"','browser = "firefox"'))
            saved=config.read_bytes();self.install(home)
            self.assertEqual(config.read_bytes(),saved)
            tree=ET.parse(home/'.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml')
            self.assertEqual(tree.find("./property[@name='panels']/property[@name='panel-2']/property[@name='size']").get('value'),'52')
            self.assertIn('WebBrowser=firefox',(home/'.config/xfce4/helpers.rc').read_text())

    def test_data_path_with_spaces_and_missing_mount(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'Data Folder';folder.mkdir()
            config=Path(tmp)/'settings.toml'
            original=(ROOT/'home/.config/eww/settings.toml').read_text()
            config.write_text(original.replace('data_path = "/mnt/data"',f'data_path = "{folder}"'))
            env={**os.environ,'MISERABLE_CONFIG':str(config)}
            command=[sys.executable,str(ROOT/'home/.config/eww/scripts/disk'),'--data','--total']
            value=subprocess.check_output(command,env=env,text=True).strip()
            self.assertRegex(value,r'[0-9.]+ (GiB|TiB)')
            shutil.rmtree(folder)
            self.assertEqual(subprocess.check_output(command,env=env,text=True).strip(),'—')

    def test_invalid_weather_coordinates_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            config=Path(tmp)/'settings.toml';config.write_text((ROOT/'home/.config/eww/settings.toml').read_text().replace('latitude = 16.00495','latitude = 191'))
            result=subprocess.run([sys.executable,str(ROOT/'home/.config/eww/scripts/settings.py')],env={**os.environ,'MISERABLE_CONFIG':str(config)},capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0);self.assertIn('weather.latitude',result.stderr)

    def test_display_toggle_uses_config_and_keeps_working_output_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)/'user';self.install(home)
            config=home/'.config/eww/settings.toml'
            config.write_text(config.read_text().replace('physical_output = "DP-4"','physical_output = "DP-9"').replace('virtual_output = "HDMI-0"','virtual_output = "HDMI-9"'))
            bindir=Path(tmp)/'bin';bindir.mkdir()
            log=Path(tmp)/'commands'
            xrandr=bindir/'xrandr'
            xrandr.write_text('''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
if sys.argv[1:]==['--query']:
 print('DP-9 connected primary 2560x1440+0+0')
 print('HDMI-9 '+os.environ.get('VIRTUAL_STATE','connected'))
else:
 with Path(os.environ['DISPLAY_TEST_LOG']).open('a') as file: file.write(json.dumps(sys.argv[1:])+'\\n')
 if os.environ.get('FAIL_ENABLE') and '--mode' in sys.argv: sys.exit(1)
''');xrandr.chmod(0o755)
            notify=bindir/'notify-send';notify.write_text('#!/bin/sh\nexit 0\n');notify.chmod(0o755)
            env={**os.environ,'HOME':str(home),'MISERABLE_CONFIG':str(config),'XDG_RUNTIME_DIR':tmp,'PATH':str(bindir)+os.pathsep+os.environ['PATH'],'DISPLAY_TEST_LOG':str(log)}
            command=[str(home/'.local/bin/toggle-rustdesk-display')]
            self.assertEqual(subprocess.run(command,env=env).returncode,0)
            calls=[json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual(calls,[['--output','HDMI-9','--mode','1920x1080','--rate','60','--primary','--pos','0x0'],['--output','DP-9','--off']])
            log.unlink()
            self.assertNotEqual(subprocess.run(command,env={**env,'FAIL_ENABLE':'1'}).returncode,0)
            self.assertNotIn('--off',log.read_text())
            log.unlink()
            self.assertNotEqual(subprocess.run(command,env={**env,'VIRTUAL_STATE':'disconnected'}).returncode,0)
            self.assertFalse(log.exists())
            self.assertEqual(subprocess.run(command+['physical'],env=env).returncode,0)
            calls=[json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual(calls,[['--output','DP-9','--auto','--primary','--pos','0x0'],['--output','HDMI-9','--off']])

    def test_weather_uses_config_and_updates_label_without_refetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);bindir=folder/'bin';bindir.mkdir()
            log=folder/'requested-url'
            curl=bindir/'curl'
            curl.write_text('#!/usr/bin/env python3\nimport os,sys,json\nfrom pathlib import Path\nPath(os.environ["REQUEST_LOG"]).write_text(sys.argv[-1])\nprint(json.dumps({"current":{"temperature_2m":25.4,"weather_code":1,"is_day":1,"time":"2026-11-01T12:00"}}))\n')
            curl.chmod(0o755)
            config=folder/'settings.toml';config.write_text((ROOT/'home/.config/eww/settings.toml').read_text().replace('location = "Hoà Xuân, Đà Nẵng"','location = "Hà Nội"').replace('latitude = 16.00495','latitude = 21.0278'))
            env={**os.environ,'PATH':str(bindir)+os.pathsep+os.environ['PATH'],'MISERABLE_CONFIG':str(config),'XDG_CACHE_HOME':str(folder/'cache'),'REQUEST_LOG':str(log)}
            command=[sys.executable,str(ROOT/'home/.config/eww/scripts/weather')]
            result=json.loads(subprocess.check_output(command,env=env,text=True))
            self.assertEqual(result['location'],'Hà Nội');self.assertEqual(result['temp'],'25,4')
            self.assertIn('latitude=21.0278',log.read_text())
            stamp=log.stat().st_mtime_ns
            config.write_text(config.read_text().replace('location = "Hà Nội"','location = "Tên mới"'))
            result=json.loads(subprocess.check_output(command,env=env,text=True))
            self.assertEqual(result['location'],'Tên mới');self.assertEqual(log.stat().st_mtime_ns,stamp)

    def test_dry_run_and_symlink_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)/'user';self.install(home,dry_run=True);self.assertFalse(home.exists())
            home.mkdir();outside=Path(tmp)/'outside';outside.mkdir();(home/'.config').symlink_to(outside)
            with self.assertRaises(SystemExit):self.install(home)
            self.assertEqual(list(outside.iterdir()),[])

    def test_source_checksums_and_no_duplicate_profile(self):
        self.assertFalse((ROOT/'profiles').exists())
        for name,info in json.loads((ROOT/'config/sources.lock.json').read_text()).items():
            if 'sha256' in info:self.assertEqual(hashlib.sha256((ROOT/'vendor'/name).read_bytes()).hexdigest(),info['sha256'])
        for file in (ROOT/'home').rglob('*'):
            if file.is_file():
                self.assertNotIn(b'/home/bwin',file.read_bytes(),file)
                self.assertNotIn(b'/Documents/Codex/',file.read_bytes(),file)
                self.assertNotIn('displays.xml',str(file))

    def test_xml_launchers_and_shell_syntax(self):
        for p in (ROOT/'home/.config/xfce4').rglob('*.xml'):ET.parse(p)
        panel=ET.parse(ROOT/'home/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml')
        for plugin in panel.findall("./property[@name='plugins']/property"):
            if plugin.get('value')=='launcher':
                number=plugin.get('name').split('-')[1]
                for item in plugin.findall("./property[@name='items']/value"):
                    self.assertTrue((ROOT/f'home/.config/xfce4/panel/launcher-{number}'/item.get('value')).is_file())
        for folder in [ROOT/'scripts',ROOT/'home']:
            for p in folder.rglob('*'):
                if p.is_file() and p.read_bytes().startswith((b'#!/bin/bash',b'#!/usr/bin/env bash')):subprocess.run(['bash','-n',str(p)],check=True)

    def test_gtk_asset_graph_has_no_missing_or_unused_files(self):
        root=ROOT/'home/.themes/Lavanda-Dark-Compact-Tokyonight'
        for folder in [root/'gtk-3.0',root/'gtk-4.0']:
            needed=set()
            for css in folder.glob('*.css'):
                for relative in re.findall(r'url\([\s\"\']*([^\)\"\']+)',css.read_text()):
                    asset=(css.parent/relative.strip()).resolve()
                    self.assertTrue(asset.is_file(),asset)
                    needed.add(asset)
            for asset in (folder/'assets').rglob('*'):
                if asset.is_file():self.assertIn(asset.resolve(),needed,asset)

    @unittest.skipUnless(shutil.which('dbus-run-session') and shutil.which('xfconf-query'),'Needs xfconf and isolated D-Bus')
    def test_live_apply_uses_isolated_dbus(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)/'session';home.mkdir()
            env={**os.environ,'HOME':str(home),'XDG_CONFIG_HOME':str(home/'.config'),'XDG_CACHE_HOME':str(home/'.cache')}
            result=subprocess.run(['dbus-run-session','--',sys.executable,str(ROOT/'scripts/apply.py'),'--target',str(home),'--live'],env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('Applied',result.stdout)

if __name__=='__main__':unittest.main()
