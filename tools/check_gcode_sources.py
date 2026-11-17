#!/usr/bin/env python3
"""Every printer variant's G-code templates in a converted pack against the text of its source, as the source program
reads it: the OrcaSlicer-family preset (resolved with its parents; upstream.orca_machine_gcode), UltiMaker Cura's
definition, or the Tisma Slicer bundle section (or, for a printer key no section of its inheritance sets, the
program's default in PrintConfig.cpp). Exits with 1 and lists the variants that differ.

Usage: check_gcode_sources.py <pack> <upstream.args> <Tisma Slicer resources/profiles> [<Tisma Slicer PrintConfig.cpp>]
(upstream.args: the arguments tools/fetch_sources.py prints.)
"""

import collections
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import convert  # noqa: E402
import upstream  # noqa: E402


def merged(d, v):
    cg, vg = d['common'].get('gcode') or {}, v.get('gcode') or {}
    g = dict(cg, **vg)
    for k in ('templates', 'from', 'source', 'keys'):
        g[k] = dict(cg.get(k) or {}, **(vg.get(k) or {}))
    return g


def main():
    pack, args_file, profiles = sys.argv[1], sys.argv[2], sys.argv[3]
    defaults = upstream.program_defaults(sys.argv[4]) if len(sys.argv) > 4 else {}
    words = open(args_file).read().split()
    ups = {}
    official = []
    for a in words:
        if a.startswith('--upstream='):
            repo, _, d = a[len('--upstream='):].rpartition('=')
            ups[repo] = d
        elif a.startswith('--official-bundle='):
            official.append(a[len('--official-bundle='):].rpartition('=')[0])
    readers, bundles, everything = {}, {}, {}
    cura = None

    def bundle(bid):
        if bid not in bundles:
            path = os.path.join(profiles, bid + '.ini')
            if not os.path.exists(path):
                path = next((o for o in official if os.path.basename(o) == bid + '.ini'), path)
            bundles[bid] = convert.Bundle(path)
        return bundles[bid]

    counts, bad = collections.Counter(), []
    for f in sorted(glob.glob(os.path.join(pack, 'vendors', '*', 'models', '*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        for v in d['variants']:
            g = merged(d, v)
            t, src = g['templates'], g['source']
            where = '%s#%s' % (os.path.relpath(f, pack), v['id'])
            if not t:
                counts['without G-code (%s)' % d.get('technology')] += 1
                continue
            if g.get('origin') == 'source_program' and g.get('dialect') == 'cura':
                if cura is None:
                    cura = upstream.CuraDefinitions(os.path.join(ups['https://github.com/Ultimaker/Cura'], 'resources'))
                want = (upstream.cura_machine_gcode(cura, src['preset']) or {}).get('templates', {})
            elif g.get('origin') == 'source_program':
                froms = [x for x in g['from'].values() if isinstance(x, str)]
                vendor = collections.Counter(x.split('/')[0] for x in froms).most_common(1)[0][0]
                key = (src['repository'], vendor)
                if key not in readers:
                    readers[key] = upstream.OrcaVendor(os.path.join(ups[src['repository']], 'resources', 'profiles',
                                                                    vendor))
                want = (upstream.orca_machine_gcode(readers[key], src['preset']) or {}).get('templates', {})
            else:
                if not everything:
                    for ini in glob.glob(os.path.join(profiles, '*.ini')) + official:
                        for k2, val in bundle(os.path.basename(ini)[:-4]).sections.items():
                            everything.setdefault(k2, val)
                c = bundle(src['bundle']).flat('printer', src['section'], everything)
                want = {}
                for k in t:
                    key = g['keys'].get(k, '')
                    if g['from'].get(k) == 'PrintConfig.cpp':
                        # The program's default: only when no section sets the key.
                        want[k] = convert.gcode_text(defaults.get(key)) if key not in c else None
                    else:
                        want[k] = convert.gcode_text(c.get(key))
            for k, text in t.items():
                counts['checked (%s)' % (g.get('dialect') if g.get('origin') == 'source_program' else 'bundle')] += 1
                if want.get(k) != text:
                    bad.append('%s: %s differs from its source' % (where, k))
    print(json.dumps(dict(counts)))
    for b in bad:
        print(b)
    print('%d G-code templates differ from their source' % len(bad))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
