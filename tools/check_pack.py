#!/usr/bin/env python3
"""Checks a converted profile pack (tools/convert.py) for the mistakes that a conversion can make without failing:

- an empty compatible set, or an entry that points to a set that is not there;
- different printer models that share one start G-code by accident: the text does not come from the model's source
  as its program reads it (the converter fell back to a converted bundle whose source program it can read, as when
  every Bambu Lab printer got the shared base's start G-code). Models that share the vendor-wide base of an
  OrcaSlicer-style source (fdm_machine_common) because they have none of their own there are listed as notes;
- a print profile without "nozzle" when its name or its condition gives one;
- a printer G-code block without its dialect, or with a template that is not text;
- a translation table (translation/<dialect>.json) that is malformed, that disagrees with the PrusaSlicer one, or
  that does not give, applied to a profile's "original", the profile's settings (the converter's translation).

Usage: check_pack.py <pack dir> [--report FILE]
Exits with 1 and lists the problems when there are any.
"""

import argparse
import collections
import json
import os
import re
import sys

import translation

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


KINDS = {'filaments': 'filament', 'prints': 'print', 'resins': 'sla_material', 'resin_prints': 'sla_print'}
GROUPS = ('translated', 'similar', 'none')


def same_translation(kind, original, settings, where, problems, counts, nozzle=None):
    """The translation table applied to a profile's source values gives the profile's settings."""

    def copy_gcode(e, c, s):  # converted with the engine's simple variables: taken as written
        for key in ('start_gcode', 'end_gcode'):
            if (settings.get('machine') or {}).get(key) is not None:
                s.setdefault('machine', {})[key] = settings['machine'][key]
        return True, ()
    expected, _ = translation.translate(kind, original, nozzle=nozzle, rules={'gcode_template': copy_gcode})
    got = json.loads(json.dumps(settings))
    if kind == 'printer' and 'nozzle_diameter' not in original:
        got.get('machine', {}).pop('nozzle_diameter', None)  # from the source program (docs/FORMAT.md)
    counts['profiles translated again'] += 1
    if expected != got:
        problems['translation table does not give the profile\'s settings'].append(where)


def check_tables(pack, index, problems, counts):
    tables = {}
    for dialect, rel in (index.get('translation') or {}).items():
        try:
            t = load(pack, rel)
        except (OSError, ValueError):
            problems['translation table missing or not JSON'].append(rel)
            continue
        if t.get('format') != 'tisma-pack-translation' or t.get('dialect') != dialect:
            problems['translation table with a wrong header'].append(rel)
        tables[dialect] = t
        for kind, rows in t.get('kinds', {}).items():
            for key, row in rows.items():
                counts['translation rows'] += 1
                bad = row.get('group') not in GROUPS or (row['group'] == 'none') != (row.get('engine') is None) or \
                    (row['group'] != 'none' and 'how' not in row.get('conversion', {}))
                if bad:
                    problems['malformed translation row'].append('%s %s %s' % (dialect, kind, key))
    if 'prusaslicer' not in tables:
        problems['no prusaslicer translation table'].append('index.json')
        return
    base = tables['prusaslicer']['kinds']
    for dialect, t in tables.items():
        if dialect == 'prusaslicer':
            continue
        for kind, rows in t['kinds'].items():
            for key, row in rows.items():
                p = row.get('prusaslicer')
                ref = base.get(kind, {}).get(p) if p else None
                if ref and (ref['engine'] != row['engine'] or ref['group'] != row['group']):
                    problems['translation row unlike its PrusaSlicer key'].append('%s %s %s' % (dialect, kind, key))


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
                same_translation(KINDS[group], e['original'], e['profile']['settings'], rel, problems, counts,
                                 nozzle=e.get('nozzle'))
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
            doc = load(args.pack, m['file'])
            for var in doc['variants']:
                original = dict(doc.get('original_common', {}), **var.get('original', {}))
                settings = merged_block(doc['common']['settings'], var['settings'])
                same_translation('printer' if m['technology'] == 'fff' else 'printer_sla', original, settings,
                                 '%s#%s' % (m['file'], var['id']), problems, counts)
            if m['technology'] != 'fff':
                continue
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

    check_tables(args.pack, index, problems, counts)
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
