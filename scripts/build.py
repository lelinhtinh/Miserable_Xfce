#!/usr/bin/env python3
"""Build pinned tools into .build/install-home; never install into the live desktop."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / 'config/sources.lock.json').read_text())

def run(*args, cwd=None, env=None):
    subprocess.run([str(a) for a in args], cwd=cwd, env=env, check=True)

def repo(name, work):
    dst = work / name
    spec = LOCK[name]
    if not (dst / '.git').exists():
        dst.mkdir(parents=True, exist_ok=True)
        run('git', 'init', '-q', dst)
        run('git', 'remote', 'add', 'origin', spec['url'], cwd=dst)
    has_commit = subprocess.run(['git', '-C', str(dst), 'cat-file', '-e', spec['commit'] + '^{commit}'],
                                stderr=subprocess.DEVNULL).returncode == 0
    if not has_commit:
        run('git', 'fetch', '--depth', '1', 'origin', spec['commit'], cwd=dst)
    if not any(p.name != '.git' for p in dst.iterdir()):
        run('git', 'checkout', '-q', '--detach', spec['commit'], cwd=dst)
    # Refuse to erase user work; applied patches are managed in fresh trees.
    clean = subprocess.check_output(['git', '-C', str(dst), 'status', '--porcelain', '--untracked-files=no'], text=True)
    patch = ROOT / 'patches' / f'{name}.patch'
    if clean:
        if not patch.exists() or subprocess.run(['git', '-C', str(dst), 'apply', '--reverse', '--check', str(patch)],
                                               stderr=subprocess.DEVNULL).returncode:
            raise SystemExit(f'Unrecognized changes in build source: {dst}')
    else:
        run('git', 'checkout', '-q', '--detach', spec['commit'], cwd=dst)
        if patch.exists() and patch.stat().st_size:
            run('git', 'apply', patch, cwd=dst)
    return dst

def unpack(name, work, dirname):
    src = ROOT / 'vendor' / name
    actual = hashlib.sha256(src.read_bytes()).hexdigest()
    if actual != LOCK[name]['sha256']:
        raise SystemExit(f'Checksum mismatch: {src}')
    dst = work / dirname
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    with tarfile.open(src) as archive:
        archive.extractall(dst, filter='data')
    children = list(dst.iterdir())
    return children[0] if len(children) == 1 and children[0].is_dir() else dst

def install(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

def build(work, output, selected):
    work.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    bin_dir = output / '.local/bin'
    jobs = str(min(os.cpu_count() or 2, 4))
    if 'eww' in selected:
        src = repo('eww', work)
        run('cargo', 'build', '--release', '--locked', '--no-default-features', '--features', 'x11', '-j', jobs, cwd=src)
        install(src / 'target/release/eww', bin_dir / 'eww')
    if 'skippy' in selected:
        chip = unpack('chipmunk2d.tar.gz', work, 'chipmunk-source')
        chipbuild = work / 'chipmunk-build'
        run('cmake', '-S', chip, '-B', chipbuild, '-DBUILD_DEMOS=OFF', '-DBUILD_SHARED=OFF', '-DBUILD_STATIC=ON', '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_POLICY_VERSION_MINIMUM=3.5')
        run('cmake', '--build', chipbuild, '-j', jobs)
        src = unpack('skippy-xd.tar.gz', work, 'skippy-source')
        run('patch', '-p1', '-i', ROOT / 'patches/skippy-xd.patch', cwd=src)
        deps = 'x11 xcomposite xdamage xext xfixes xft xrender libjpeg libpng zlib xrandr xinerama'.split()
        cflags = subprocess.check_output(['pkg-config', '--cflags', *deps], text=True).split()
        libs = subprocess.check_output(['pkg-config', '--libs', *deps], text=True).split()
        sources = 'aabb clientwin config dlist focus img-xlib img layout mainwin skippy tooltip wm img-gif img-jpeg img-png'.split()
        run('cc', '-O2', '-DNDEBUG', '-std=gnu11', '-DSKIPPYXD_VERSION="0.11.0.1-local"',
            *['-DCFG_' + f for f in ('XINPUTLIB', 'GIFLIB', 'JPEG', 'LIBPNG', 'XRANDR', 'XINERAMA', 'CHIPMUNK')],
            '-I' + str(chip / 'include'), *cflags, *[src / 'src' / (s + '.c') for s in sources],
            chipbuild / 'src/libchipmunk.a', *libs, '-lXi', '-lgif', '-lm', '-pthread', '-o', work / 'skippy-xd')
        install(work / 'skippy-xd', bin_dir / 'skippy-xd')
    if 'pulse' in selected:
        src = repo('pulseaudio-plugin', work)
        builddir = src / 'build'
        setup = ['meson', 'setup'] + (['--reconfigure'] if (builddir / 'build.ninja').exists() else [])
        run(*setup, builddir, src, '--buildtype=release', '--prefix=/usr', '--libdir=lib')
        run('meson', 'compile', '-C', builddir, '-j', jobs)
        install(builddir / 'panel-plugin/libpulseaudio-plugin.so', output / '.local/lib/xfce4/panel/plugins/libpulseaudio-fixed.so')
        install(ROOT / 'config/pulseaudio-fixed.desktop', output / '.local/share/xfce4/panel/plugins/pulseaudio-fixed.desktop')
    if 'icons' in selected:
        for name, themes in [('numix-icon-theme', ['Numix']),
                             ('numix-icon-theme-circle', ['Numix-Circle'])]:
            src = repo(name, work)
            for theme in themes:
                dst = output / '.local/share/icons' / theme
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src / theme, dst, symlinks=True)
        for relative, link in json.loads((ROOT / 'config/icon-aliases.json').read_text()).items():
            dst = output / '.local/share/icons' / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.unlink(missing_ok=True)
            dst.symlink_to(link)
    if 'cortile' in selected:
        if platform.machine() != 'x86_64':
            raise SystemExit('Bundled Cortile release requires x86_64.')
        src = unpack('cortile_2.5.2_linux_amd64.tar.gz', work, 'cortile-release')
        install(src / 'cortile', bin_dir / 'cortile')
        # Retain the upstream release license alongside its binary.
        for license in src.glob('*LICENSE*'):
            install(license, output / '.local/share/licenses/cortile' / license.name)
    if 'xcape' in selected:
        src = '/usr/bin/xcape' if Path('/usr/bin/xcape').is_file() else shutil.which('xcape')
        if not src:
            raise SystemExit('Install repository package xcape first.')
        install(Path(src), bin_dir / 'xcape')
    report = {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in output.rglob('*') if p.is_file() and not p.is_symlink()}
    (work / 'outputs.sha256.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Built home overlay:', output)
    print('Apply offline with: python scripts/apply.py --include-built')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--only', action='append', choices=['eww', 'skippy', 'pulse', 'icons', 'cortile', 'xcape'])
    p.add_argument('--work-dir', type=Path, default=ROOT / '.build')
    a = p.parse_args()
    work = a.work_dir.resolve()
    build(work, work / 'install-home', a.only or ['eww', 'skippy', 'pulse', 'icons', 'cortile', 'xcape'])
