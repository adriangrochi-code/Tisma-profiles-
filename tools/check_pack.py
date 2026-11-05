#!/usr/bin/env python3
"""Checks a converted profile pack (tools/convert.py) for the mistakes that a conversion can make without failing:

- an empty compatible set, or an entry that points to a set that is not there;
- different printer models that share one start G-code by accident: the text does not come from the model's source
  as its program reads it (the converter fell back to a converted bundle whose source program it can read, as when
  every Bambu Lab printer got the shared base's start G-code). Models that share the vendor-wide base of an
  OrcaSlicer-style source (fdm_machine_common) because they have none of their own there are listed as notes;
- a print profile without "nozzle" when its name or its condition gives one;
- a printer G-code block without its dialect, or with a template that is not text.

Usage: check_pack.py <pack dir> [--report FILE]
Exits with 1 and lists the problems when there are any.
"""

import argparse
import collections
import json
import os
import re
import sys

NOZZLE_CONDITION = re.compile(r'(?:^|\band\b|&&|\()\s*nozzle_diameter\[0\]\s*==\s*"?(\d+(?:\.\d+)?)"?\s*'
                              r'(?=\)|\band\b|&&|$)')
NOZZLE_NAME = re.compile(r'(?i)(?<![\d.])(\d+(?:\.\d+)?)\s*(?:mm)?\s*nozzle\b|\bnozzle\s*(\d+(?:\.\d+)?)(?![\d.])')
DIALECTS = ('prusaslicer', 'orcaslicer', 'crealityprint', 'elegooslicer', 'cura')
SOURCE_PROGRAMS = ('orcaslicer', 'crealityprint', 'elegooslicer', 'cura')  # the ones the converter reads
VENDOR_ROOT = re.compile(r'(^|/)fdm_machine_common\.json$')


def load(pack, rel):
    with open(os.path.join(pack, rel), encoding='utf-8') as f:
        return json.load(f)


def merged_block(common, own):
    out = {}
    for part in (common or {}, own or {}):
        for k, v in part.items():
            if isinstance(v, dict):
                out.setdefault(k, {}).update(v)
            else:
                out[k] = v
    return out


def nozzle_said(entry):
    """The nozzle that a print profile's name or condition gives, or None."""
    cond = str(entry.get('original', {}).get('compatible_printers_condition', '')).strip().strip('"')
    if ' or ' not in cond and '||' not in cond:
        found = {float(x) for x in NOZZLE_CONDITION.findall(cond)}
        if len(found) == 1:
            return found.pop()
    found = {float(a or b) for a, b in NOZZLE_NAME.findall(entry['profile']['name'])}
    if len(found) == 1 and 0.1 <= next(iter(found)) <= 3:
        return found.pop()
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pack')
    ap.add_argument('--report')
    args = ap.parse_args()

    index = load(args.pack, 'index.json')
    sets = load(args.pack, 'compatible.json')['sets']
    problems = collections.defaultdict(list)
    notes = collections.defaultdict(list)
    counts = collections.Counter()

    for i, s in enumerate(sets):
        if not s:
            problems['empty compatible set'].append('set %d' % i)
        bad = [p for p in s if not 0 <= p < len(index['printers'])]
        if bad:
            problems['compatible set with unknown printers'].append('set %d: %s' % (i, bad))

    for v in index['vendors']:
        for group in ('filaments', 'prints', 'resins', 'resin_prints'):
            for rel in v[group]:
                e = load(args.pack, rel)
                counts[group] += 1
                c = e.get('compatible')
                if c is not None and not (isinstance(c, int) and 0 <= c < len(sets)):
                    problems['entry pointing to a missing compatible set'].append(rel)
                elif c is not None and not sets[c]:
                    problems['entry with an empty compatible set'].append(rel)
                if group == 'prints' and e.get('nozzle') is None:
                    said = nozzle_said(e)
                    if said is not None:
                        problems['print without nozzle, and its name or condition gives %s' % said].append(rel)
                    else:
                        counts['prints for any nozzle'] += 1

    # Start G-code of every printer model variant.
    by_text = collections.defaultdict(list)
    for v in index['vendors']:
        for m in v['models']:
            if m['technology'] != 'fff':
                continue
            doc = load(args.pack, m['file'])
            for var in doc['variants']:
                counts['fff variants'] += 1
                g = merged_block(doc['common'].get('gcode'), var.get('gcode'))
                where = '%s#%s' % (m['file'], var['id'])
                if not g:
                    problems['printer without a G-code block'].append(where)
                    continue
                if g.get('dialect') not in DIALECTS:
                    problems['G-code block with an unknown dialect'].append('%s: %s' % (where, g.get('dialect')))
                for k, t in (g.get('templates') or {}).items():
                    if not (isinstance(t, str) or (isinstance(t, list) and all(x is None or isinstance(x, str)
                                                                                for x in t))):
                        problems['G-code template that is not text'].append('%s: %s' % (where, k))
                start = (g.get('templates') or {}).get('start')
                if start:
                    counts['fff variants with a start G-code'] += 1
                    by_text[start].append((doc['model']['name'], where, g))
    for text, users in by_text.items():
        models = sorted({u[0] for u in users})
        if len(models) < 2:
            continue
        counts['start G-codes shared by several models'] += 1
        fell_back = [w for name, w, g in users if g.get('origin') == 'converted_bundle' and
                     g.get('source', {}).get('program') in SOURCE_PROGRAMS]
        from_root = [w for name, w, g in users if VENDOR_ROOT.search(str((g.get('from') or {}).get('start', '')))]
        names = '%d models (%s)' % (len(models), ', '.join(models[:6]) + (', …' if len(models) > 6 else ''))
        if fell_back:
            problems['start G-code shared by different models by accident'].append(
                names + ': from the converted bundle instead of the source program')
        elif from_root:
            # As the source program has it (these models have no start G-code of their own there): not an error.
            notes['start G-code of the vendor-wide base, as in the source program'].append(names)

    report = {'counts': dict(counts), 'problems': dict(problems), 'notes': dict(notes)}
    if args.report:
        with open(args.report, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
    print(json.dumps(dict(counts)))
    for k, items in sorted(problems.items()):
        print('%d %s' % (len(items), k))
        for x in items[:10]:
            print('   ', x)
    for k, items in sorted(notes.items()):
        print('note: %d %s' % (len(items), k))
        for x in items[:10]:
            print('   ', x)
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
