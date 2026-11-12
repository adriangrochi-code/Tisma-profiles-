#!/usr/bin/env python3
"""Fetches the programs that Tisma Slicer converted its bundles from (sources.json, "converted_from"), each at its
commit and only its profile folders (and, for the OrcaSlicer family, src/libslic3r for its option defaults), and
prints the --upstream and --source-config arguments of tools/convert.py for them.

With Tisma Slicer's converter (tools/profiles/convert_orca_profiles.py of the checkout of the bundles), it also fetches
the manufacturers' own slicers (sources.json, "official"), converts the vendor of each with that converter into
<dir>/official, and prints the --upstream and --official-bundle arguments for them (owner's rule: a manufacturer's
own slicer over OrcaSlicer).

Usage: fetch_sources.py <sources.json> <dir> [<convert_orca_profiles.py>]
"""

import glob
import json
import os
import subprocess
import sys

DIALECTS = {'https://github.com/SoftFever/OrcaSlicer': 'orcaslicer',
            'https://github.com/CrealityOfficial/CrealityPrint': 'crealityprint',
            'https://github.com/ELEGOO-3D/ElegooSlicer': 'elegooslicer'}


def git(*args, cwd=None):
    subprocess.run(['git'] + list(args), cwd=cwd, check=True, stdout=subprocess.DEVNULL)


def fetch(s, root, cone=True):
    """A checkout of s["repository"] at s["commit"] with only s["directory"] (its paths: space-separated, or a list;
    folders, or with cone False also files)."""
    folder = os.path.join(root, s['repository'].rstrip('/').split('/')[-1])
    if not os.path.isdir(os.path.join(folder, '.git')):
        os.makedirs(folder, exist_ok=True)
        git('init', '-q', cwd=folder)
        git('remote', 'add', 'origin', s['repository'] + '.git', cwd=folder)
    paths = s['directory'].split() if isinstance(s['directory'], str) else s['directory']
    if not cone:
        paths = ['/' + p.strip('/') + ('' if os.path.splitext(p)[1] else '/') for p in paths]  # anchored: file, dir
    git('sparse-checkout', 'set', *([] if cone else ['--no-cone']), *paths, cwd=folder)
    git('fetch', '-q', '--depth', '1', '--filter=blob:none', 'origin', s['commit'], cwd=folder)
    git('checkout', '-q', 'FETCH_HEAD', cwd=folder)
    return folder


def main():
    sources, root = sys.argv[1], sys.argv[2]
    converter = sys.argv[3] if len(sys.argv) > 3 else None
    data = json.load(open(sources, encoding='utf-8'))
    out = []
    for s in data['converted_from']:
        folder = fetch(s, root)
        out.append('--upstream=%s=%s' % (s['repository'], os.path.abspath(folder)))
        config = os.path.join(folder, 'src', 'libslic3r', 'PrintConfig.cpp')
        dialect = DIALECTS.get(s['repository'].rstrip('/'))
        if dialect and os.path.exists(config):
            # The program's option defaults, for the variables of its G-code that a preset does not set.
            out.append('--source-config=%s=%s' % (dialect, os.path.abspath(config)))
        print('%s at %s' % (s['program'], s['commit']), file=sys.stderr)
    for s in data.get('official', []) if converter else []:
        folder = fetch(s, os.path.join(root, 'official_sources'), cone=False)  # apart from converted_from's
        bundles = os.path.join(os.path.abspath(root), 'official')
        os.makedirs(bundles, exist_ok=True)
        tisma_root = os.path.join(os.path.dirname(os.path.abspath(converter)), '..', '..')
        subprocess.run([sys.executable, converter, os.path.join(folder, 'resources', 'profiles'), bundles,
                        '--tisma-root', tisma_root, '--orca-commit', s['commit'],
                        '--vendors', ','.join(s['vendors']), '--prefix', s['prefix'], '--source', s['program'],
                        '--url', s['repository']] + (['--maker', s['maker']] if s.get('maker') else []),
                       check=True, stdout=subprocess.DEVNULL)
        if not any(c['repository'] == s['repository'] for c in data['converted_from']):  # else read from there
            out.append('--upstream=%s=%s' % (s['repository'], os.path.abspath(folder)))
        replaces = s['replaces'] if isinstance(s['replaces'], list) else [s['replaces']]
        for ini in sorted(glob.glob(os.path.join(bundles, s['prefix'] + '*.ini'))):
            out.append('--official-bundle=%s=%s' % (ini, ','.join(replaces)))
        print('%s at %s (official, in place of %s)' % (s['program'], s['commit'], ', '.join(replaces)),
              file=sys.stderr)
    print(' '.join(out))


if __name__ == '__main__':
    main()
