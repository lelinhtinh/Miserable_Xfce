"""Use a disposable Secret Service and encrypted files, never the user's daemon."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('keyring_tpm', ROOT / 'scripts/keyring_tpm.py')
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


def private_bus_worker():
    from gi.repository import Gio, GLib
    daemon = subprocess.Popen(
        ['/usr/bin/gnome-keyring-daemon', '--foreground', '--components=secrets',
         '--control-directory=' + os.environ['GNOME_KEYRING_CONTROL']],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        for _ in range(50):
            owned = bus.call_sync('org.freedesktop.DBus', '/org/freedesktop/DBus',
                                  'org.freedesktop.DBus', 'NameHasOwner',
                                  GLib.Variant('(s)', (helper.BUS_NAME,)), None,
                                  Gio.DBusCallFlags.NONE, 1000, None).unpack()[0]
            if owned:
                break
            time.sleep(.1)
        _, session = helper.call(bus, helper.SERVICE, 'org.freedesktop.Secret.Service',
                                 'OpenSession', '(sv)', ('plain', GLib.Variant('s', '')))
        password = 'non-secret-test-password'
        secret = (session, b'', password.encode(), 'text/plain')
        path = helper.call(bus, helper.SERVICE, helper.INTERNAL, 'CreateWithMasterPassword',
                           '(a{sv}(oayays))',
                           ({'org.freedesktop.Secret.Collection.Label': GLib.Variant('s', 'Test only')},
                            secret))[0]
        helper.call(bus, session, 'org.freedesktop.Secret.Session', 'Close')
        helper.call(bus, helper.SERVICE, 'org.freedesktop.Secret.Service', 'Lock', '(ao)', ([path],))
        assert helper.properties(bus, path)['Locked']
        try:
            helper.unlock_collection(bus, path, 'wrong-password')
        except GLib.Error:
            pass
        else:
            raise AssertionError('Wrong password accepted')
        assert helper.properties(bus, path)['Locked']
        assert helper.unlock_collection(bus, path, password)
        data = {'version': 1, 'uid': os.getuid(),
                'collections': [{'path': path, 'password': password}]}
        assert helper.validate_copy(data)[path]
        data['collections'][0]['password'] = 'wrong-password'
        assert not helper.validate_copy(data)[path]
        # Validating a copy leaves the original test daemon unlocked.
        assert not helper.properties(bus, path)['Locked']
        for file in Path(os.environ['XDG_DATA_HOME']).rglob('*.keyring'):
            assert password.encode() not in file.read_bytes()
    finally:
        daemon.terminate()
        daemon.wait(timeout=5)


class KeyringTPMTests(unittest.TestCase):
    def test_login_hook_is_repeatable_and_disable_preserves_other_settings(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(helper.Path, 'home', return_value=Path(tmp)):
            profile = Path(tmp) / '.xprofile'
            original = '#!/bin/sh\nexport CUSTOM_SESSION_SETTING=keep\n'
            profile.write_text(original)
            helper.configure_profile()
            helper.configure_profile()
            self.assertEqual(profile.read_text().count('# BEGIN MISERABLE KEYRING TPM'), 1)
            self.assertIn(original, profile.read_text())
            helper.disable()
            self.assertNotIn('MISERABLE KEYRING TPM', profile.read_text())
            self.assertIn(original, profile.read_text())

    def test_credential_rejects_wrong_account_empty_secret_and_bad_paths(self):
        data = {'version': 1, 'uid': 1000,
                'collections': [{'path': helper.SERVICE + '/collection/Login', 'password': 'example'}]}
        self.assertEqual(helper.parse_payload(json.dumps(data), 1000), data)
        with self.assertRaises(ValueError):
            helper.parse_payload(json.dumps(data), 1001)
        for path, password in (('/tmp/file', 'example'),
                               (helper.SERVICE + '/collection/session', 'example'),
                               (helper.SERVICE + '/collection/Login', '')):
            data['collections'] = [{'path': path, 'password': password}]
            with self.assertRaises(ValueError):
                helper.parse_payload(json.dumps(data), 1000)

    def test_unlock_requires_authenticated_local_session_before_reading_secret(self):
        with patch.object(helper.os, 'getuid', return_value=1000), \
                patch.object(helper, 'authenticated_local_session', return_value=False), \
                patch.object(helper.Path, 'read_bytes') as read:
            with self.assertRaises(ValueError):
                helper.unlock()
            read.assert_not_called()

    def test_private_bus_password_validation_and_encrypted_copy(self):
        runtime = os.environ.get('XDG_RUNTIME_DIR', '/tmp')
        with tempfile.TemporaryDirectory(prefix='keyring-tpm-test-', dir=runtime) as tmp:
            env = os.environ.copy()
            env.update(XDG_DATA_HOME=tmp + '/data', GNOME_KEYRING_CONTROL=tmp + '/control')
            env.pop('DBUS_SESSION_BUS_ADDRESS', None)
            subprocess.run(['/usr/bin/dbus-run-session', '--', sys.executable,
                            str(Path(__file__).resolve()), '--private-worker'],
                           env=env, check=True, timeout=45)


if __name__ == '__main__':
    if '--private-worker' in sys.argv:
        private_bus_worker()
    else:
        unittest.main()
