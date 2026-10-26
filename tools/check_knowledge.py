#!/usr/bin/env python3
"""Checks the knowledge base (docs/KNOWLEDGE.md): JSON, format names, and that every reference points somewhere
(problems, procedures, calibrations, settings).

Usage: check_knowledge.py <knowledge dir>
"""

import json
import os
import re
import sys

FILES = {'materials.json': 'tisma-knowledge-materials', 'problems.json': 'tisma-knowledge-problems',
         'procedures.json': 'tisma-knowledge-procedures', 'glossary.json': 'tisma-knowledge-glossary',
         'tutorials.json': 'tisma-knowledge-tutorials', 'calibrations.json': 'tisma-knowledge-calibrations'}
CALIBRATIONS = {'temperature_tower', 'flow', 'retraction', 'max_flow', 'cooling', 'overhang_angle', 'supports',
                'dimensional', 'stringing_temperature', 'input_shaping', 'first_layer', 'pressure_advance', 'cornering',
                'vfa'}
KEY = re.compile(r'^[a-z]+(\.[a-z_]+)+$')
OPS = {'add', 'multiply', 'set', 'set_relative'}


def main():
    root = sys.argv[1]
    errors = []
    data = {}
    for name, fmt in FILES.items():
        path = os.path.join(root, name)
        try:
            with open(path, encoding='utf-8') as f:
                data[name] = json.load(f)
        except (OSError, ValueError) as e:
            errors.append('%s: %s' % (name, e))
            continue
        if data[name].get('format') != fmt:
            errors.append('%s: format must be %s' % (name, fmt))
        if not data[name].get('sources'):
            if name != 'materials.json':
                errors.append('%s: sources missing' % name)
    problems = {p['id'] for p in data.get('problems.json', {}).get('problems', [])}
    procedures = {p['id'] for p in data.get('procedures.json', {}).get('procedures', [])}

    def check_action(where, a):
        t = a.get('type')
        if t == 'setting':
            if not KEY.match(a.get('key', '')):
                errors.append('%s: bad setting key %r' % (where, a.get('key')))
            if a.get('op') not in OPS:
                errors.append('%s: op must be one of %s' % (where, ', '.join(sorted(OPS))))
            if a.get('op') == 'set_relative' and not KEY.match(a.get('of', '')):
                errors.append('%s: set_relative needs "of"' % where)
        elif t == 'procedure':
            if a.get('id') not in procedures:
                errors.append('%s: unknown procedure %r' % (where, a.get('id')))
        elif t == 'problem':
            if a.get('id') not in problems:
                errors.append('%s: unknown problem %r' % (where, a.get('id')))
        elif t == 'calibration':
            if a.get('id') not in CALIBRATIONS:
                errors.append('%s: unknown calibration %r' % (where, a.get('id')))
        elif t in ('hardware', 'model'):
            if not a.get('text'):
                errors.append('%s: text missing' % where)
        else:
            errors.append('%s: unknown action type %r' % (where, t))

    for p in data.get('problems.json', {}).get('problems', []):
        for c in p.get('causes', []):
            for i, a in enumerate(c.get('actions', [])):
                check_action('problems %s/%s[%d]' % (p['id'], c['id'], i), a)
    for t in data.get('tutorials.json', {}).get('tutorials', []):
        for i, s in enumerate(t.get('steps', [])):
            if 'open' in s:
                check_action('tutorials %s[%d]' % (t['id'], i), s['open'])
    cal = data.get('calibrations.json', {})
    cal_sources = {s.get('id') for s in cal.get('sources', [])}
    cal_ids = [c.get('id') for c in cal.get('calibrations', [])]
    if set(cal_ids) != CALIBRATIONS:
        errors.append('calibrations.json: ids must be exactly %s' % ', '.join(sorted(CALIBRATIONS)))
    for c in cal.get('calibrations', []):
        where = 'calibrations %s' % c.get('id')
        for field in ('name', 'group', 'order', 'why', 'steps', 'read', 'result', 'sources'):
            if field not in c:
                errors.append('%s: %s missing' % (where, field))
        if c.get('group') not in ('filament', 'printer'):
            errors.append('%s: group must be filament or printer' % where)
        for b in c.get('before', []):
            if b not in cal_ids:
                errors.append('%s: unknown calibration in before %r' % (where, b))
        r = c.get('result', {})
        if 'key' in r and not KEY.match(r['key']):
            errors.append('%s: bad result key %r' % (where, r['key']))
        if 'key' not in r and r.get('where') != 'printer_firmware':
            errors.append('%s: result needs a key or where = printer_firmware' % where)
        for sid in c.get('sources', []):
            if sid not in cal_sources:
                errors.append('%s: unknown source %r' % (where, sid))
        if 'open' in c:
            check_action(where, c['open'])
    for t in data.get('glossary.json', {}).get('terms', []):
        for k in t.get('settings', []):
            if not KEY.match(k):
                errors.append('glossary %s: bad setting key %r' % (t['term'], k))
    for e in errors:
        print(e)
    counts = {'materials': len(data.get('materials.json', {}).get('materials', [])), 'problems': len(problems),
              'procedures': len(procedures), 'terms': len(data.get('glossary.json', {}).get('terms', [])),
              'tutorials': len(data.get('tutorials.json', {}).get('tutorials', [])),
              'calibrations': len(cal.get('calibrations', []))}
    print(json.dumps(counts), '%d problems' % len(errors))
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
