"""Set complete xfconf channels through D-Bus, without fighting xfconfd's files."""
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


def reset(channel):
    result = subprocess.run(['xfconf-query', '-c', channel, '-p', '/', '-r', '-R'], capture_output=True, text=True)
    if result.returncode and 'does not exist' not in result.stderr + result.stdout:
        raise RuntimeError(result.stderr or result.stdout)


def apply_channel(path):
    tree = ET.parse(path)
    channel = tree.getroot().get('name')
    reset(channel)
    def visit(parent, prefix=''):
        for node in parent.findall('property'):
            key = prefix + '/' + node.get('name')
            kind = node.get('type')
            if kind != 'empty':
                command = ['xfconf-query', '-c', channel, '-p', key, '-n']
                if kind == 'array':
                    values = node.findall('value')
                    if not values:
                        continue
                    command += ['--force-array']
                    for value in values:
                        command += ['-t', value.get('type'), '-s', value.get('value')]
                else:
                    command += ['-t', kind, '-s', node.get('value')]
                subprocess.run(command, check=True, capture_output=True, text=True)
            visit(node, key)
    visit(tree.getroot())
