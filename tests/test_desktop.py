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
import time
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import apply as installer
import render_restore

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

    def test_personal_integrations_and_login_script_survive_reinstall_and_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)/'user';home.mkdir()
            outside=Path(tmp)/'login-script';outside.write_text('export KEEP_EXISTING=1\n')
            outside.chmod(0o600)
            profile=home/'.xprofile';profile.symlink_to(outside)
            custom={'.config/mimeapps.list':'[Default Applications]\ntext/html=firefox.desktop\n',
                    '.config/gtk-3.0/bookmarks':'file:///my/custom/path\n',
                    '.config/fcitx5/profile':'[Groups/0]\nDefaultIM=unikey\n'}
            for relative,content in custom.items():
                p=home/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
            self.install(home)
            first_backup=next((home/'.local/state/miserable-xfce/backups').iterdir())
            self.install(home)
            self.assertIn('export KEEP_EXISTING=1',profile.read_text())
            self.assertEqual(profile.read_text().count('# BEGIN Miserable Xfce input method'),1)
            self.assertIn('QT_IM_MODULE=fcitx',profile.read_text())
            self.assertEqual(profile.stat().st_mode & 0o777,0o600)
            self.assertEqual(outside.read_text(),'export KEEP_EXISTING=1\n')
            for relative,content in custom.items():self.assertEqual((home/relative).read_text(),content)
            subprocess.run(['sh','-n',str(profile)],check=True)
            with contextlib.redirect_stdout(io.StringIO()):installer.restore(first_backup)
            self.assertTrue(profile.is_symlink())
            self.assertEqual(profile.read_text(),'export KEEP_EXISTING=1\n')

    def test_hardware_restore_renders_only_enabled_features_and_validates_identifiers(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);config=tmp/'settings.toml'
            text=(ROOT/'home/.config/eww/settings.toml').read_text()
            config.write_text(text.replace('PCI:1:0:0','PCI:2:3:1').replace('alsa_card = "GEW1"','alsa_card = "DAC2"'))
            target=tmp/'stage';files=render_restore.render(config,target)
            self.assertEqual(len(files),6)
            self.assertIn(b'PCI:2:3:1',files['system/etc/X11/xorg.conf.d/90-rustdesk-virtual-monitor.conf'])
            self.assertIn('0000:02:03.1',(target/'install.sh').read_text())
            self.assertIn(b'-c DAC2 sset PCM 100%%',files['home/.config/systemd/user/fix-simgot.service'])
            subprocess.run(['bash','-n',str(target/'install.sh')],check=True)
            with self.assertRaises(ValueError):render_restore.render(config,target)
            config.write_text(text.replace('alsa_card = "GEW1"','alsa_card = "bad%name"'))
            with self.assertRaises(ValueError):render_restore.render(config,tmp/'invalid')
            self.assertFalse((tmp/'invalid').exists())
            config.write_text('[restore]\n')
            self.assertEqual(render_restore.render(config,tmp/'empty'),{})

    def test_generated_restore_installer_uses_target_user_and_keeps_file_backups(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);home=tmp/'user';home.mkdir();config=tmp/'config.toml'
            config.write_text((ROOT/'home/.config/eww/settings.toml').read_text().replace('nvidia_virtual_display = true','nvidia_virtual_display = false'))
            target=tmp/'stage';render_restore.render(config,target)
            original=home/'.config/systemd/user/fix-simgot.service';original.parent.mkdir(parents=True);original.write_text('original')
            bindir=tmp/'bin';bindir.mkdir();log=tmp/'commands'
            for name in ['sudo','systemctl','pulseaudio','wireplumber','amixer','fcitx5-lotus-server']:
                path=bindir/name
                path.write_text('#!/usr/bin/env python3\nimport os,sys,json\nfrom pathlib import Path\nwith Path(os.environ["RESTORE_TEST_LOG"]).open("a") as file:file.write(json.dumps(sys.argv)+"\\n")\n')
                path.chmod(0o755)
            identity=bindir/'id';identity.write_text('#!/bin/sh\ncase "$1" in -u) echo 1000;; -un) echo target-user;; esac\n');identity.chmod(0o755)
            for name in ['bash','dirname','install','python3']:(bindir/name).symlink_to(shutil.which(name))
            result=subprocess.run(['bash',str(target/'install.sh')],env={**os.environ,'HOME':str(home),'PATH':str(bindir),'RESTORE_TEST_LOG':str(log)},capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(original.with_name(original.name+'.~1~').read_text(),'original')
            self.assertIn('fcitx5-lotus-server@target-user.service',log.read_text())
            self.assertIn('GST_PLUGIN_LOADING_WHITELIST',(home/'.config/systemd/user/pulseaudio.service.d/80-gstreamer-audio-only.conf').read_text())

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

    def test_display_status_reports_actual_layout_without_changing_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);home=folder/'user';self.install(home)
            config=home/'.config/eww/settings.toml'
            config.write_text(config.read_text().replace('physical_output = "DP-4"','physical_output = "DP-9"').replace('virtual_output = "HDMI-0"','virtual_output = "HDMI-9"'))
            bindir=folder/'bin';bindir.mkdir();query=folder/'query'
            xrandr=bindir/'xrandr'
            xrandr.write_text('''#!/usr/bin/env python3
import os,sys
from pathlib import Path
assert sys.argv[1:] == ['--query'], 'Status must never mutate the display layout'
if os.environ.get('FAIL_QUERY'):sys.exit(1)
print(Path(os.environ['DISPLAY_QUERY']).read_text())
''');xrandr.chmod(0o755)
            env={**os.environ,'HOME':str(home),'MISERABLE_CONFIG':str(config),
                 'PATH':str(bindir)+os.pathsep+os.environ['PATH'],'DISPLAY_QUERY':str(query)}
            command=[str(home/'.local/bin/toggle-rustdesk-display'),'status','--json']
            layouts=[
                ('DP-9 connected primary 2560x1440-2560+0\nHDMI-9 connected', 'physical','virtual',True,'2560x1440'),
                ('DP-9 connected\nHDMI-9 connected primary 1920x1080+0-1080', 'virtual','physical',True,'1920x1080'),
                ('DP-9 connected 2560x1440+0+0\nHDMI-9 connected 1920x1080+2560+0', 'both','virtual',True,'DP-9 + HDMI-9'),
                ('DP-9 disconnected\nHDMI-9 connected 1920x1080+0+0', 'virtual','physical',False,'1920x1080'),
                ('eDP-1 connected primary 1920x1200+0+0', 'other','physical',False,'eDP-1'),
                ('DP-9 disconnected\nHDMI-9 connected', 'other','physical',False,'Không có màn hình'),
            ]
            for layout,mode,target,can_switch,label in layouts:
                with self.subTest(mode=mode,layout=layout):
                    query.write_text(layout)
                    status=json.loads(subprocess.check_output(command,env=env,text=True))
                    self.assertEqual((status['mode'],status['target'],status['can_switch']),(mode,target,can_switch))
                    self.assertIn(label,status['label'])
            result=subprocess.run(command,env={**env,'FAIL_QUERY':'1'},capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('Không đọc được trạng thái',result.stderr)

    def test_display_notifications_follow_real_state_after_switch_and_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);home=folder/'user';self.install(home)
            bindir=folder/'bin';bindir.mkdir();state=folder/'state';notifications=folder/'notifications'
            state.write_text(json.dumps({'DP-4':True,'HDMI-0':False}))
            xrandr=bindir/'xrandr'
            xrandr.write_text('''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
file=Path(os.environ['DISPLAY_STATE']);state=json.loads(file.read_text())
if sys.argv[1:]==['--query']:
 for name,active in state.items():print(name+' connected'+(' 1920x1080+0+0' if active else ''))
else:
 if os.environ.get('FAIL_ENABLE') and '--auto' in sys.argv:sys.exit(1)
 if os.environ.get('FAIL_DISABLE') and '--off' in sys.argv:sys.exit(1)
 state[sys.argv[2]]='--off' not in sys.argv
 file.write_text(json.dumps(state))
''');xrandr.chmod(0o755)
            notify=bindir/'notify-send'
            notify.write_text('''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
with Path(os.environ['NOTIFICATION_LOG']).open('a') as file:file.write(json.dumps(sys.argv[1:])+'\\n')
''');notify.chmod(0o755)
            env={**os.environ,'HOME':str(home),'XDG_RUNTIME_DIR':tmp,
                 'PATH':str(bindir)+os.pathsep+os.environ['PATH'],'DISPLAY_STATE':str(state),
                 'NOTIFICATION_LOG':str(notifications)}
            env.pop('MISERABLE_CONFIG',None)
            command=[str(home/'.local/bin/toggle-rustdesk-display')]
            def switch(*args, **extra):
                result=subprocess.run(command+list(args),env={**env,**extra},capture_output=True,text=True)
                # The helper deliberately releases its lock before notifying asynchronously.
                for _ in range(100):
                    if notifications.exists():break
                    time.sleep(.02)
                self.assertTrue(notifications.exists(),'No display notification was sent')
                return result
            result=switch()
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(state.read_text()),{'DP-4':False,'HDMI-0':True})
            args=json.loads(notifications.read_text().splitlines()[-1])
            self.assertIn('Màn hình ảo · HDMI-0 · 1920x1080',args[-1])
            notifications.unlink()
            result=switch('physical',FAIL_ENABLE='1')
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(json.loads(state.read_text()),{'DP-4':False,'HDMI-0':True})
            args=json.loads(notifications.read_text().splitlines()[-1])
            self.assertIn('critical',args)
            self.assertEqual(args[-2],'Không thể hoàn tất chuyển màn hình')
            self.assertIn('Màn hình ảo',args[-1])
            notifications.unlink()
            self.assertNotEqual(switch('physical',FAIL_DISABLE='1').returncode,0)
            self.assertEqual(json.loads(state.read_text()),{'DP-4':True,'HDMI-0':True})
            args=json.loads(notifications.read_text().splitlines()[-1])
            self.assertIn('critical',args)
            self.assertIn('Màn hình thật và ảo',args[-1])
            notifications.unlink()
            self.assertEqual(switch('physical').returncode,0)
            self.assertIn('Màn hình thật',json.loads(notifications.read_text().splitlines()[-1])[-1])

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
