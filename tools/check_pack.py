#!/usr/bin/env python3
"""Checks a converted profile pack (tools/convert.py) for the mistakes that a conversion can make without failing:

- an empty compatible set, or an entry that points to a set that is not there;
- different printer models that share one start G-code by accident: the text does not come from the model's source
  as its program reads it (the converter fell back to a converted bundle whose source program it can read, as when
  every Bambu Lab printer got the shared base's start G-code). Models that share the vendor-wide base of an
  OrcaSlicer-style source (fdm_machine_common) because they have none of their own there are listed as notes;
- a print profile without "nozzle" when its name or its condition gives one;
- a printer G-code block without its dialect, or with a template that is not text;
- a filament of the OrcaSlicer family whose G-code comes from the converted bundle instead of its source program;
- a print profile for one nozzle that fits printers with another nozzle;
- a printer variant of index.json that no vendor lists;
- with --community, a community printer file that names no model of the pack;
- a printer's default filament, print or resin that is not in the pack, or that does not fit the printer while
  another one does, and an FFF variant that no filament or print fits;
- a printer of the OrcaSlicer family without a translated value that its source program's preset gives (its
  gcode.values) and its bundle lost;
- a translation table (translation/<dialect>.json) that is malformed, that disagrees with the PrusaSlicer one, or
  that does not give, applied to a profile's "original", the profile's settings (the converter's translation).

Usage: check_pack.py <pack dir> [--report FILE] [--community DIR]
Exits with 1 and lists the problems when there are any.
"""

import argparse
import collections
import json
import os
import re
import sys

import translation
import upstream

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


def prune(d):
    """Removes the groups left empty."""
    for k in list(d):
        if isinstance(d[k], dict):
            prune(d[k])
            if not d[k]:
                del d[k]


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
    counts['profiles translated again'] += 1
    if expected != got:
        problems['translation table does not give the profile\'s settings'].append(where)


def source_text(v):
    return ','.join(str(x) for x in v) if isinstance(v, list) else '1' if v is True else '0' if v is False else str(v)


def lost_values(original, values):
    """The translated printer options that the bundle lacks and the source program's preset gives, as bundle text."""
    names = {v: k for k, v in upstream.ORCA_TO_PRUSA.items()}
    names.update({'machine_max_feedrate_' + a: 'machine_max_speed_' + a for a in 'xyze'})
    out = {}
    for e in translation.TABLE['printer']:
        for key in (e['from'] if isinstance(e.get('from'), list) else [e.get('from')]):
            if key and key not in original and names.get(key, key) in values:
                out[key] = source_text(values[names.get(key, key)])
    return out


def quoted_texts(d, path=''):
    """Paths of the texts still written with the quotes of the bundle files ("PLA" for PLA)."""
    if isinstance(d, dict):
        for k, v in d.items():
            yield from quoted_texts(v, path + '.' + k if path else k)
    elif isinstance(d, list):
        for v in d:
            yield from quoted_texts(v, path)
    elif isinstance(d, str) and len(d) >= 2 and d[0] == d[-1] == '"':
        yield path


def check_print_nozzles(pack, index, sets, problems, counts):
    """A print profile made for one nozzle fits no printer with another one."""
    nozzle, cache = {}, {}
    for i, ref in enumerate(index['printers']):
        path, vid = ref.split('#', 1)
        if path not in cache:
            cache[path] = load(pack, path)
        doc = cache[path]
        var = next((v for v in doc['variants'] if v['id'] == vid), None)
        n = merged_block(doc['common']['settings'], (var or {}).get('settings')).get('machine', {}).get('nozzle_diameter')
        nozzle[i] = n[0] if isinstance(n, list) else n
    for v in index['vendors']:
        for rel in v['prints']:
            e = load(pack, rel)
            if e.get('nozzle') is None or e.get('compatible') is None:
                continue
            other = sorted({nozzle[i] for i in sets[e['compatible']] if nozzle.get(i) not in (None, e['nozzle'])})
            if other:
                problems['print for one nozzle that fits printers with another'].append(
                    '%s (%s; also %s)' % (rel, e['nozzle'], ', '.join(str(x) for x in other)))


def check_defaults(pack, index, sets, problems, counts, notes=None):
    """Every printer's default profiles exist and fit it."""
    notes = notes if notes is not None else collections.defaultdict(list)
    place = {r: i for i, r in enumerate(index['printers'])}
    cache = {}
    fitting = {}  # (kind, printer number) -> some profile of that kind fits it
    named = collections.defaultdict(list)  # (kind, profile name) -> [(file, compatible set)]
    groups = {'filament': 'filaments', 'print': 'prints', 'resin': 'resins', 'resin_print': 'resin_prints'}
    for kind, group in groups.items():
        for v in index['vendors']:
            for rel in v[group]:
                e = load(pack, rel)
                c = e.get('compatible')
                named[(kind, e['profile']['name'])].append((rel, c))
                for i in (range(len(place)) if c is None else sets[c]):
                    fitting[(kind, i)] = True
    for ref, i in place.items():
        path, vid = ref.split('#', 1)
        if path not in cache:
            cache[path] = load(pack, path)
        var = next((v for v in cache[path]['variants'] if v['id'] == vid), None)
        if var is None:
            problems['index printer that its model file does not have'].append(ref)
            continue
        for path in quoted_texts(var.get('source_defaults') or {}):
            problems['text written with the quotes of the bundle file: source_defaults.' + path].append(ref)
        # The default print the source names, when the pack has it and it fits the printer, is the one chosen.
        said = ((var.get('source_defaults') or {}).get('print') or '').strip('"')
        kind = 'resin_print' if 'resin_print' in (var.get('defaults') or {}) else 'print'
        said = said[:-len(' @Template')] if said.endswith(' @Template') else said
        fits = [r for r, c in named.get((kind, said), []) if c is None or i in sets[c]]
        if fits and not set(fits) & set((var.get('defaults') or {}).get(kind) or []):
            problems['default %s other than the one the source names, which fits' % kind].append(
                '%s: %s' % (ref, said))
        if cache[path].get('technology') == 'fff':
            for kind in ('filament', 'print'):
                if not fitting.get((kind, i)):
                    problems['FFF variant with no compatible %s at all' % kind].append(ref)
        for kind, rels in (var.get('defaults') or {}).items():
            for rel in rels:
                counts['printer defaults'] += 1
                if not os.path.exists(os.path.join(pack, rel)):
                    problems['default profile that is not in the pack'].append('%s -> %s' % (ref, rel))
                    continue
                c = load(pack, rel).get('compatible')
                if c is not None and i not in sets[c] and fitting.get((kind, i)):
                    problems['default %s that does not fit its printer, while another one does' % kind].append(
                        '%s -> %s' % (ref, rel))


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
    ap.add_argument('--community', help='the community data folder: each printer file must name a pack model')
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
                settings = json.loads(json.dumps(e['profile']['settings']))
                for path in e.get('from_source_program', []):  # filled from the source program, not translated
                    parts = path.split('.')
                    node = settings
                    for part in parts[:-1]:
                        node = node.get(part, {})
                    node.pop(parts[-1], None)
                prune(settings)
                same_translation(KINDS[group], e['original'], settings, rel, problems, counts,
                                 nozzle=e.get('nozzle'))
                sv = (e.get('source_values') or {}).get('dialect')
                g = e.get('gcode') or {}
                if group == 'filaments' and sv in SOURCE_PROGRAMS and \
                        any(isinstance(t, str) and t.strip() for t in (g.get('templates') or {}).values()) and \
                        g.get('origin') != 'source_program':
                    problems['filament G-code from the converted bundle while its source program is read'].append(rel)
                for path in quoted_texts({'settings': e['profile']['settings'], 'material': e.get('material')}):
                    problems['text written with the quotes of the bundle file: ' + path].append(rel)
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
            for key, rel in (doc.get('assets') or {}).items():
                if not os.path.isfile(os.path.join(args.pack, rel)):
                    problems['model picture or bed that is not in the pack'].append('%s: %s' % (m['file'], key))
            if doc.get('assets') != m.get('assets'):
                problems['model whose index entry and file give other pictures'].append(m['file'])
            for var in doc['variants']:
                original = dict(doc.get('original_common', {}), **var.get('original', {}))
                settings = merged_block(doc['common']['settings'], var['settings'])
                settings = json.loads(json.dumps(settings))
                for path in var.get('from_source_program', []):  # filled from the source, not translated
                    group, _, key = path.partition('.')
                    settings.get(group, {}).pop(key, None)
                for path in quoted_texts(settings):
                    problems['text written with the quotes of the bundle file: ' + path].append(
                        '%s#%s' % (m['file'], var['id']))
                prune(settings)
                same_translation('printer' if m['technology'] == 'fff' else 'printer_sla', original, settings,
                                 '%s#%s' % (m['file'], var['id']), problems, counts)
                if m['technology'] == 'fff' and not (settings.get('machine') or {}).get('nozzle_diameter') and \
                        not any(p == 'machine.nozzle_diameter' for p in var.get('from_source_program', [])):
                    problems['FFF printer without a nozzle'].append('%s#%s' % (m['file'], var['id']))
            if m['technology'] != 'fff':
                continue
            for var in doc['variants']:
                counts['fff variants'] += 1
                g = merged_block(doc['common'].get('gcode'), var.get('gcode'))
                where = '%s#%s' % (m['file'], var['id'])
                if g and g.get('origin') == 'source_program' and g.get('dialect') != 'cura':
                    original = dict(doc.get('original_common', {}), **var.get('original', {}))
                    preset = {k: v for k, v in (g.get('values') or {}).items()
                              if k not in (g.get('program_defaults') or ())}  # not the program's own defaults
                    lost = lost_values(original, preset)
                    if lost:
                        full, _ = translation.translate('printer', dict(original, **lost),
                                                        rules={'gcode_template': lambda e, c, s: (True, ())})
                        have = merged_block(doc['common']['settings'], var['settings'])
                        for group, items in full.items():
                            for key, value in (items.items() if isinstance(items, dict) else ()):
                                if key not in (have.get(group) or {}):
                                    problems['printer without a value that its source program gives: %s.%s'
                                             % (group, key)].append(where)
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

    listed = {r for v in index['vendors'] for r in v['printers']}
    for ref in index['printers']:
        if ref not in listed:
            problems['printer variant that no vendor lists'].append(ref)
    check_defaults(args.pack, index, sets, problems, counts, notes)
    check_print_nozzles(args.pack, index, sets, problems, counts)
    if args.community:
        models = {(v['id'], m['id']) for v in index['vendors'] for m in v['models']}
        for root, _, files in os.walk(os.path.join(args.community, 'printers')):
            for f in sorted(files):
                if not f.endswith('.json'):
                    continue
                path = os.path.join(root, f)
                pm = (json.load(open(path, encoding='utf-8')).get('pack_model') or {})
                counts['community printers'] += 1
                if (pm.get('bundle'), pm.get('id')) not in models:
                    problems['community printer without a pack model of the pack'].append(path)
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
