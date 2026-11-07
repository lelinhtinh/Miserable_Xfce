#!/usr/bin/env python3
"""TPM-backed unlock of existing GNOME keyrings; never change their passwords."""
import argparse
import json
import os
from pathlib import Path
import pwd
import re
import resource
import shutil
import subprocess
import sys
import tempfile
import time

import gi
gi.require_version('Secret', '1')
from gi.repository import Gio, GLib, Secret

BUS_NAME = 'org.freedesktop.secrets'
SERVICE = '/org/freedesktop/secrets'
COLLECTION = 'org.freedesktop.Secret.Collection'
INTERNAL = 'org.gnome.keyring.InternalUnsupportedGuiltRiddenInterface'
CREDENTIAL = 'miserable-keyring'
INSTALLED = '/usr/local/libexec/miserable-keyring-tpm'
MAX_BYTES = 65536


def call(bus, path, interface, method, signature=None, args=None):
    value = GLib.Variant(signature, args) if signature else None
    return bus.call_sync(BUS_NAME, path, interface, method, value, None,
                         Gio.DBusCallFlags.NONE, 5000, None).unpack()


def properties(bus, path):
    return call(bus, path, 'org.freedesktop.DBus.Properties', 'GetAll',
                '(s)', (COLLECTION,))[0]


def collections(bus):
    paths = call(bus, SERVICE, 'org.freedesktop.DBus.Properties', 'Get',
                 '(ss)', ('org.freedesktop.Secret.Service', 'Collections'))[0]
    return [path for path in paths if path != SERVICE + '/collection/session']


def unlock_collection(bus, path, password):
    # libsecret negotiates DH/AES transport; refuse a plaintext D-Bus session.
    # Use its connection so the encoded secret belongs to the same bus sender.
    service = Secret.Service.open_sync(Secret.Service, BUS_NAME,
                                       Secret.ServiceFlags.OPEN_SESSION, None)
    if service.get_session_algorithms() != 'dh-ietf1024-sha256-aes128-cbc-pkcs7':
        raise ValueError('Encrypted Secret Service transport is required.')
    value = Secret.Value.new(password, len(password.encode('utf-8')),
                              'text/plain; charset=utf8')
    secret = service.encode_dbus_secret(value)
    call(service.get_connection(), SERVICE, INTERNAL, 'UnlockWithMasterPassword',
         '(o(oayays))', (path, secret.unpack()))
    return not properties(bus, path)['Locked']


def parse_payload(raw, expected_uid):
    if len(raw) > MAX_BYTES:
        raise ValueError('Credential exceeds size limit.')
    data = json.loads(raw)
    if data.get('version') != 1 or data.get('uid') != expected_uid:
        raise ValueError('Credential version or account does not match.')
    entries = data.get('collections')
    if not isinstance(entries, list) or not 1 <= len(entries) <= 10:
        raise ValueError('Invalid collection list.')
    seen = set()
    for entry in entries:
        path, password = entry['path'], entry['password']
        if not isinstance(path, str) or not re.fullmatch(
                SERVICE + r'/collection/[A-Za-z0-9_]+', path):
            raise ValueError('Invalid collection path.')
        if path.endswith('/session') or path in seen:
            raise ValueError('Invalid or duplicate collection.')
        seen.add(path)
        if not isinstance(password, str) or not password or '\x00' in password:
            raise ValueError('A non-empty existing keyring password is required.')
    return data


def authenticated_local_session(uid):
    bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
    sessions = bus.call_sync('org.freedesktop.login1', '/org/freedesktop/login1',
                            'org.freedesktop.login1.Manager', 'ListSessions', None,
                            None, Gio.DBusCallFlags.NONE, 5000, None).unpack()[0]
    for _, session_uid, _, _, path in sessions:
        if session_uid != uid:
            continue
        props = bus.call_sync('org.freedesktop.login1', path,
                              'org.freedesktop.DBus.Properties', 'GetAll',
                              GLib.Variant('(s)', ('org.freedesktop.login1.Session',)),
                              None, Gio.DBusCallFlags.NONE, 5000, None).unpack()[0]
        if (props.get('Active') and not props.get('Remote')
                and props.get('Class') == 'user'
                and props.get('Service') == 'lightdm'
                and props.get('Type') in ('x11', 'wayland')):
            return True
    return False


def unlock():
    uid = os.getuid()
    if uid == 0 or not authenticated_local_session(uid):
        raise ValueError('No active local LightDM session for this account.')
    credential_dir = os.environ.get('CREDENTIALS_DIRECTORY')
    if not credential_dir:
        raise ValueError('Run through the installed system service.')
    raw = (Path(credential_dir) / CREDENTIAL).read_bytes()
    data = parse_payload(raw, uid)
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    opened = 0
    for entry in data['collections']:
        if properties(bus, entry['path'])['Locked']:
            if not unlock_collection(bus, entry['path'], entry['password']):
                raise ValueError('A keyring could not be unlocked.')
            opened += 1
    print(f'Keyrings ready: {len(data["collections"])}; unlocked: {opened}.')


def validate_child():
    """Run ONLY on a private D-Bus and tmpfs copy, never the active keyrings."""
    data = parse_payload(sys.stdin.buffer.read(MAX_BYTES + 1), os.getuid())
    runtime = Path(os.environ['KEYRING_TPM_VALIDATION'])
    expected_data = runtime / 'data'
    if (Path(os.environ['XDG_DATA_HOME']) != expected_data
            or not runtime.is_dir() or runtime.stat().st_uid != os.getuid()
            or not runtime.name.startswith('keyring-tpm-validate-')):
        raise ValueError('Invalid validation directory.')
    daemon = subprocess.Popen(['/usr/bin/gnome-keyring-daemon', '--foreground',
                               '--components=secrets',
                               '--control-directory=' + str(runtime / 'control')],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        ready = False
        for _ in range(50):
            ready = bus.call_sync('org.freedesktop.DBus', '/org/freedesktop/DBus',
                                  'org.freedesktop.DBus', 'NameHasOwner',
                                  GLib.Variant('(s)', (BUS_NAME,)), None,
                                  Gio.DBusCallFlags.NONE, 1000, None).unpack()[0]
            if ready:
                break
            if daemon.poll() is not None:
                break
            time.sleep(.1)
        if not ready:
            raise ValueError('Isolated keyring daemon did not start.')
        results = {}
        for entry in data['collections']:
            path = entry['path']
            # An already-open collection cannot prove a password is correct.
            if not properties(bus, path)['Locked']:
                raise ValueError('Validation copy must start locked.')
            try:
                results[path] = unlock_collection(bus, path, entry['password'])
            except GLib.Error:
                results[path] = False
        print(json.dumps(results))
    finally:
        daemon.terminate()
        try:
            daemon.wait(timeout=5)
        except subprocess.TimeoutExpired:
            daemon.kill()
            daemon.wait()


def validate_copy(data):
    # Copies remain encrypted and are removed after the isolated check.
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))
    with tempfile.TemporaryDirectory(prefix='keyring-tpm-validate-', dir=runtime) as tmp:
        work = Path(tmp)
        source = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'keyrings'
        shutil.copytree(source, work / 'data/keyrings')
        env = os.environ.copy()
        env.update(XDG_DATA_HOME=str(work / 'data'), XDG_RUNTIME_DIR=str(work),
                   GNOME_KEYRING_CONTROL=str(work / 'control'),
                   KEYRING_TPM_VALIDATION=str(work))
        env.pop('DBUS_SESSION_BUS_ADDRESS', None)
        result = subprocess.run(['/usr/bin/dbus-run-session', '--', sys.executable,
                                 str(Path(__file__).resolve()), 'validate-child'],
                                input=json.dumps(data).encode(), stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, env=env, timeout=30)
        if result.returncode:
            raise ValueError('Could not validate the encrypted keyring copy.')
        return json.loads(result.stdout)


def prompt_password(text):
    result = subprocess.run(['/usr/bin/zenity', '--password',
                             '--title=Mở keyring bằng TPM', '--text=' + text],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if result.returncode:
        raise ValueError('Enrollment cancelled; existing configuration retained.')
    password = result.stdout.removesuffix(b'\n').decode('utf-8')
    if not password:
        raise ValueError('Empty password refused; keyrings must stay encrypted.')
    return password


def configure_profile():
    profile = Path.home() / '.xprofile'
    start = '# BEGIN MISERABLE KEYRING TPM'
    end = '# END MISERABLE KEYRING TPM'
    old = profile.read_text() if profile.exists() else '#!/bin/sh\n'
    block = (f'{start}\n'
             'if [ "${XDG_SESSION_TYPE:-x11}" = x11 ]; then\n'
             f'    if ! /usr/bin/systemctl --no-ask-password start miserable-keyring-tpm-{os.getuid()}.service; then\n'
             '        /usr/bin/logger -t miserable-keyring-tpm "Automatic unlock unavailable; use the normal keyring password prompt."\n'
             '    fi\n'
             f'fi\n{end}')
    if start in old or end in old:
        if old.count(start) != 1 or old.count(end) != 1 or old.index(start) > old.index(end):
            raise ValueError('Ambiguous .xprofile block; retained existing file.')
        new = re.sub(re.escape(start) + r'.*?' + re.escape(end), lambda _: block, old, flags=re.S)
    else:
        new = old.rstrip() + '\n\n' + block + '\n'
    state = Path.home() / '.local/state/miserable-keyring-tpm'
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(prefix='xprofile-', dir=state, delete=False) as backup:
        backup.write(old.encode())
    with tempfile.NamedTemporaryFile(prefix='.xprofile-', dir=profile.parent, delete=False) as out:
        out.write(new.encode())
        staging = Path(out.name)
    os.chmod(staging, profile.stat().st_mode & 0o777 if profile.exists() else 0o600)
    staging.replace(profile)


def disable():
    if os.getuid() == 0:
        raise ValueError('Remove the login hook as the desktop user.')
    profile = Path.home() / '.xprofile'
    if not profile.exists():
        return
    old = profile.read_text()
    start, end = '# BEGIN MISERABLE KEYRING TPM', '# END MISERABLE KEYRING TPM'
    if start not in old and end not in old:
        return
    if old.count(start) != 1 or old.count(end) != 1 or old.index(start) > old.index(end):
        raise ValueError('Ambiguous .xprofile block; retained existing file.')
    new = re.sub(re.escape(start) + r'.*?' + re.escape(end) + r'\n?', '', old, flags=re.S)
    state = Path.home() / '.local/state/miserable-keyring-tpm'
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(prefix='xprofile-disable-', dir=state, delete=False) as backup:
        backup.write(old.encode())
    profile.write_text(new)
    print('Automatic keyring unlock disabled; keyrings and TPM credential retained.')


def enroll():
    if os.getuid() == 0:
        raise ValueError('Run enrollment as the desktop user.')
    if not authenticated_local_session(os.getuid()):
        raise ValueError('Enroll from an active local LightDM session.')
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    targets = collections(bus)
    default = call(bus, SERVICE, 'org.freedesktop.Secret.Service', 'ReadAlias',
                   '(s)', ('default',))[0]
    targets.sort(key=lambda p: p != default)
    if not targets:
        raise ValueError('No existing keyrings to enroll.')
    data = {'version': 1, 'uid': os.getuid(), 'collections': []}
    previous = None
    for path in targets:
        password = previous
        for attempt in range(4):
            if password is None:
                ident = path.rsplit('/', 1)[1]
                password = prompt_password(
                    f'Nhập mật khẩu hiện tại của keyring “{ident}”.\n'
                    'Mật khẩu chỉ dùng trên máy này để mã hóa bằng TPM; không đổi mật khẩu keyring.')
            candidate = {'version': 1, 'uid': os.getuid(),
                         'collections': [{'path': path, 'password': password}]}
            if validate_copy(candidate).get(path):
                data['collections'].append(candidate['collections'][0])
                previous = password
                break
            password = None
        else:
            raise ValueError('Password validation failed; no credential was replaced.')
    result = subprocess.run(['/usr/bin/pkexec', INSTALLED, 'seal', str(os.getuid())],
                            input=json.dumps(data).encode(), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    if result.returncode:
        raise ValueError('TPM enrollment failed; no login hook was added.')
    configure_profile()
    print('TPM credential enrolled; login hook installed.')


def seal(uid):
    if os.getuid() != 0:
        raise ValueError('Sealing requires administrative authentication.')
    if uid < 1000 or (os.environ.get('PKEXEC_UID') and int(os.environ['PKEXEC_UID']) != uid):
        raise ValueError('Invalid target account.')
    pwd.getpwuid(uid)
    raw = sys.stdin.buffer.read(MAX_BYTES + 1)
    parse_payload(raw, uid)
    directory = Path('/etc/credstore.encrypted')
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    output = directory / f'miserable-keyring-{uid}.cred'
    with tempfile.TemporaryDirectory(prefix='.keyring-tpm-', dir=directory) as tmp:
        ciphertext = Path(tmp) / 'credential'
        result = subprocess.run(['/usr/bin/systemd-creds', '--with-key=host+tpm2',
                                 '--tpm2-device=/dev/tpmrm0', '--tpm2-pcrs=4+7',
                                 '--name=' + CREDENTIAL, 'encrypt', '-', str(ciphertext)],
                                input=raw, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if result.returncode:
            raise ValueError('TPM encryption failed.')
        verify = subprocess.run(['/usr/bin/systemd-creds', '--name=' + CREDENTIAL,
                                 'decrypt', str(ciphertext), '-'], stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL)
        if verify.returncode or verify.stdout != raw:
            raise ValueError('TPM round-trip verification failed.')
        if output.exists():
            backup = Path(tempfile.mkdtemp(prefix='keyring-tpm-', dir='/var/backups'))
            shutil.copy2(output, backup / output.name)
        os.chmod(ciphertext, 0o600)
        ciphertext.replace(output)
    print('TPM credential sealed and round-trip verified.')


def main():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('enroll', 'seal', 'unlock', 'validate-child', 'disable'))
    parser.add_argument('uid', nargs='?', type=int)
    args = parser.parse_args()
    try:
        if args.action == 'seal':
            if args.uid is None:
                raise ValueError('A target UID is required.')
            seal(args.uid)
        else:
            {'enroll': enroll, 'unlock': unlock, 'validate-child': validate_child,
             'disable': disable}[args.action]()
    except (ValueError, OSError, GLib.Error, subprocess.SubprocessError, KeyError):
        # No traceback or secret-bearing request is written to the journal.
        print('Keyring TPM operation failed or was cancelled. Existing keyring passwords are unchanged.',
              file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
