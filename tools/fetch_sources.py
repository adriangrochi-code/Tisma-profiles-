#!/usr/bin/env python3
"""Fetches the programs that Tisma Slicer converted its bundles from (sources.json, "converted_from"), each at its
commit and only its profile folders (and, for the OrcaSlicer family, src/libslic3r for its option defaults), and
prints the --upstream and --source-config arguments of tools/convert.py for them.

Usage: fetch_sources.py <sources.json> <dir>
"""

import json
import os
import subprocess
import sys

DIALECTS = {'https://github.com/SoftFever/OrcaSlicer': 'orcaslicer',
            'https://github.com/CrealityOfficial/CrealityPrint': 'crealityprint',
            'https://github.com/ELEGOO-3D/ElegooSlicer': 'elegooslicer'}


def git(*args, cwd=None):
    subprocess.run(['git'] + list(args), cwd=cwd, check=True, stdout=subprocess.DEVNULL)


def main():
    sources, root = sys.argv[1], sys.argv[2]
    out = []
    for s in json.load(open(sources, encoding='utf-8'))['converted_from']:
        folder = os.path.join(root, s['repository'].rstrip('/').split('/')[-1])
        if not os.path.isdir(os.path.join(folder, '.git')):
            os.makedirs(folder, exist_ok=True)
            git('init', '-q', cwd=folder)
            git('remote', 'add', 'origin', s['repository'] + '.git', cwd=folder)
        git('sparse-checkout', 'set', *s['directory'].split(), cwd=folder)
        git('fetch', '-q', '--depth', '1', '--filter=blob:none', 'origin', s['commit'], cwd=folder)
        git('checkout', '-q', 'FETCH_HEAD', cwd=folder)
        out.append('--upstream=%s=%s' % (s['repository'], os.path.abspath(folder)))
        config = os.path.join(folder, 'src', 'libslic3r', 'PrintConfig.cpp')
        dialect = DIALECTS.get(s['repository'].rstrip('/'))
        if dialect and os.path.exists(config):
            # The program's option defaults, for the variables of its G-code that a preset does not set.
            out.append('--source-config=%s=%s' % (dialect, os.path.abspath(config)))
        print('%s at %s' % (s['program'], s['commit']), file=sys.stderr)
    print(' '.join(out))


if __name__ == '__main__':
    main()
