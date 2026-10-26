#!/usr/bin/env python3
"""Slices a 20 mm cube with every FFF printer of a profile pack, its default filament and its default print profile,
through the Tisma engine command line, and reports what fails.

Usage: validate.py <pack dir> <tisma-engine binary> <report.json> [--jobs N] [--limit N]
"""

import argparse
import collections
import concurrent.futures
import itertools
import json
import os
import re
import struct
import subprocess
import tempfile


def cube_stl(path, cx, cy, size=20.0):
    x0, y0, x1, y1, z1 = cx - size / 2, cy - size / 2, cx + size / 2, cy + size / 2, size
    v = [(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    faces = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7),
             (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    with open(path, 'wb') as f:
        f.write(b'\0' * 80 + struct.pack('<I', len(faces)))
        for a, b, c in faces:
            f.write(struct.pack('<3f', 0, 0, 0))
            for i in (a, b, c):
                f.write(struct.pack('<3f', *v[i]))
            f.write(b'\0\0')


def merge(dst, src):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            merge(dst[k], v)
        else:
            dst[k] = v
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pack')
    ap.add_argument('engine')
    ap.add_argument('report')
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 4)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--all', action='store_true', help='also every filament and print profile')
    args = ap.parse_args()

    index = json.load(open(os.path.join(args.pack, 'index.json'), encoding='utf-8'))
    work = []
    for v in index['vendors']:
        for rel in v['printers']:
            e = json.load(open(os.path.join(args.pack, rel), encoding='utf-8'))
            if e['technology'] != 'fff':
                continue
            fil = (e['defaults']['filament'] or [None])[0]
            pr = (e['defaults']['print'] or [None])[0]
            work.append((rel, e, fil, pr))
    if args.all:
        # Every filament and print profile too, each with the first printer it fits and that printer's default for
        # the other part.
        sets = json.load(open(os.path.join(args.pack, 'compatible.json'), encoding='utf-8'))['sets']
        printers = index['printers']
        loaded = {}

        def printer(rel):
            if rel not in loaded:
                loaded[rel] = json.load(open(os.path.join(args.pack, rel), encoding='utf-8'))
            return loaded[rel]
        for v in index['vendors']:
            for group in ('filaments', 'prints'):
                for rel in v[group]:
                    e = json.load(open(os.path.join(args.pack, rel), encoding='utf-8'))
                    if e['compatible'] is None or not sets[e['compatible']]:
                        continue
                    own = [printers[i] for i in sets[e['compatible']] if printers[i].startswith(os.path.dirname(
                        os.path.dirname(rel)) + '/')]
                    prel = (own or [printers[i] for i in sets[e['compatible']]])[0]
                    pe = printer(prel)
                    if pe['technology'] != 'fff':
                        continue
                    if group == 'filaments':
                        work.append((prel, pe, rel, (pe['defaults']['print'] or [None])[0]))
                    else:
                        work.append((prel, pe, (pe['defaults']['filament'] or [None])[0], rel))
    if args.limit:
        work = work[:args.limit]

    tmp = tempfile.mkdtemp(prefix='packcheck_')
    counter = itertools.count()

    def run(item):
        rel, e, fil, pr = item
        cfg = {}
        merge(cfg, e['profile']['settings'])
        for part in (fil, pr):
            if part:
                merge(cfg, json.load(open(os.path.join(args.pack, part), encoding='utf-8'))['profile']['settings'])
        bed = cfg.get('machine', {}).get('bed') or [[0, 0], [200, 0], [200, 200], [0, 200]]
        cx = (min(p[0] for p in bed) + max(p[0] for p in bed)) / 2
        cy = (min(p[1] for p in bed) + max(p[1] for p in bed)) / 2
        key = '%06d' % next(counter)
        stl = os.path.join(tmp, key + '.stl')
        cube_stl(stl, cx, cy)
        cfg_path = os.path.join(tmp, key + '.json')
        json.dump(cfg, open(cfg_path, 'w'))
        out = os.path.join(tmp, key + '.gcode')
        p = subprocess.run([args.engine, 'slice', stl, '--config', cfg_path, '-o', out], capture_output=True,
                           text=True, timeout=600)
        res = {'printer': rel, 'filament': fil, 'print': pr, 'exit': p.returncode}
        if p.returncode != 0:
            res['error'] = ([l for l in (p.stderr + p.stdout).splitlines() if 'error' in l.lower()] or
                            (p.stderr + p.stdout).splitlines()[-1:] or [''])[0][:300]
        elif os.path.exists(out):
            text = open(out, encoding='utf-8', errors='replace').read()
            left = sorted(set(re.findall(r'\{(\w+)(?:\[\d+\])?\}|\[(\w+)\]', text.split(';TYPE')[0])))
            res['placeholders_left'] = sorted({a or b for a, b in left})
            res['size'] = len(text)
        for f in (stl, cfg_path, out):
            if os.path.exists(f):
                os.remove(f)
        return res

    results = []
    with concurrent.futures.ThreadPoolExecutor(args.jobs) as ex:
        for r in ex.map(run, work):
            results.append(r)
    summary = collections.Counter('ok' if r['exit'] == 0 else 'exit %d' % r['exit'] for r in results)
    errors = collections.Counter(re.sub(r'[\d.]+', 'N', r.get('error', ''))[:160] for r in results if r['exit'])
    left = collections.Counter(n for r in results for n in r.get('placeholders_left', []))
    report = {'summary': dict(summary), 'no_filament': sum(1 for r in results if not r['filament']),
              'no_print': sum(1 for r in results if not r['print']), 'errors': dict(errors.most_common()),
              'placeholders_left': dict(left.most_common()), 'results': results}
    json.dump(report, open(args.report, 'w'), indent=1)
    print(json.dumps({k: report[k] for k in ('summary', 'no_filament', 'no_print')}))
    for k, n in errors.most_common(15):
        print(n, k)
    print('placeholders left:', dict(left.most_common(15)))


if __name__ == '__main__':
    main()
