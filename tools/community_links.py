#!/usr/bin/env python3
"""Rebuilds the pack_filament links of the community filament files (docs/COMMUNITY.md) against a converted pack: the
pack filaments of the same maker whose name, before " @", is the file's name or one of its hand-checked aliases
(community/filament_aliases.json), compared without case, spaces and punctuation. Never by similarity.

Usage: community_links.py <pack> <community>
"""

import collections
import glob
import json
import os
import re
import sys


def key(name, maker=''):
    """The name without case, spaces, punctuation (but +) and the maker's word."""
    s = name.lower()
    if maker:
        s = s.replace(maker, '')
    return re.sub(r'[^a-z0-9+]', '', s)


def main():
    pack, community = sys.argv[1], sys.argv[2]
    aliases = collections.defaultdict(list)
    path = os.path.join(community, 'filament_aliases.json')
    if os.path.exists(path):
        for a in json.load(open(path, encoding='utf-8'))['aliases']:
            aliases[a['file']].append(a['pack_name'])
    names = collections.defaultdict(set)  # name key -> {(bundle, profile name, material vendor)}
    for f in glob.glob(os.path.join(pack, 'vendors', '*', 'filaments', '*.json')):
        e = json.load(open(f, encoding='utf-8'))
        n = e['profile']['name']
        names[n.split(' @')[0].lower()].add((f.split(os.sep)[-3], n, str((e.get('material') or {}).get('vendor', ''))))
    by_key = collections.defaultdict(lambda: collections.defaultdict(set))  # maker -> key -> entries
    linked = total = 0
    folder = os.path.join(community, 'filaments')
    for f in sorted(glob.glob(os.path.join(folder, '*', '*.json'))):
        rel = os.path.relpath(f, folder)
        d = json.load(open(f, encoding='utf-8'))
        maker = d['vendor'].split()[0].lower()
        if maker not in by_key:
            for base, entries in names.items():
                for bundle, n, vendor in entries:
                    # Only the maker's filaments: its name in the material's vendor or in the profile's name.
                    if maker in vendor.lower() or maker in n.lower():
                        by_key[maker][key(base, maker)].add((bundle, n))
        found = set()
        for name in [d['name']] + aliases.get(rel, []):
            found |= by_key[maker].get(key(name, maker), set())
        data = d.pop('data')
        d.pop('pack_filament', None)
        if found:
            d['pack_filament'] = [{'bundle': b, 'name': n} for b, n in sorted(found)]
            linked += 1
            total += len(found)
        d['data'] = data
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write(json.dumps(d, indent=1, ensure_ascii=False) + '\n')
    print('%d community filaments linked to %d pack filaments' % (linked, total))


if __name__ == '__main__':
    main()
