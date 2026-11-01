#!/usr/bin/python
"""Start with tiling disabled while retaining cached layouts and proportions."""
import json
import os
from pathlib import Path

cache = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'cortile'
for path in cache.glob('*/workplaces/*/workspaces/*/*.json'):
    data = json.loads(path.read_text())
    if isinstance(data, dict) and 'Tiling' in data and data['Tiling'] is not False:
        data['Tiling'] = False
        temporary = path.with_suffix('.startup.tmp')
        temporary.write_text(json.dumps(data, separators=(',', ':')))
        temporary.replace(path)
