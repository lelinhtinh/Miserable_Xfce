#!/usr/bin/env python3
"""Exercise the authentication callback extracted from a patched source tree."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = args.source.resolve()
    text = (source / 'src/lightdm-gtk-greeter.c').read_text()
    # The next top-level callback bounds the complete production function.
    match = re.search(r'static void\nauthentication_complete_cb\b.*?(?=\nstatic void\n)', text, re.S)
    if match is None:
        raise SystemExit('Cannot locate the production authentication callback.')
    flags = subprocess.check_output(['pkg-config', '--cflags', '--libs', 'glib-2.0'], text=True).split()
    with tempfile.TemporaryDirectory(prefix='greeter-auth-') as temp:
        work = Path(temp)
        (work / 'authentication-complete.inc').write_text(match.group())
        subprocess.run(['cc', '-Wall', '-Wextra', '-Werror', '-I', str(source / 'src'),
                        '-I', str(work), str(root / 'tests/greeter-authentication.c'),
                        *flags, '-o', str(work / 'check')], check=True)
        subprocess.run([str(work / 'check')], check=True)


if __name__ == '__main__':
    main()
