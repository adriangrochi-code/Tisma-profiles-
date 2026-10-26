#!/usr/bin/env python3
"""Checks the community data files (docs/COMMUNITY.md): JSON, required fields, kinds, sources and keys.

Usage: check_community.py <community dir>
Exits with 1 and lists file and problem when something is wrong.
"""

import json
import os
import re
import sys

KINDS = {'official', 'measured', 'community'}
SOURCE_TYPES = {'manufacturer', 'datasheet', 'firmware', 'video', 'article', 'forum', 'test', 'other'}
GROUPS = {'printers': ('vendor', 'model'), 'filaments': ('vendor', 'name'), 'resins': ('vendor', 'name')}
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
KEY = re.compile(r'^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$')


def check_value(path, i, item, errors):
    where = '%s: data[%d]' % (path, i)
    for field in ('key', 'value', 'kind', 'source'):
        if field not in item:
            errors.append('%s: missing "%s"' % (where, field))
    if 'key' in item and not KEY.match(str(item['key'])):
        errors.append('%s: key "%s" is not group.name' % (where, item['key']))
    if item.get('kind') not in KINDS:
        errors.append('%s: kind must be one of %s' % (where, ', '.join(sorted(KINDS))))
    if not isinstance(item.get('value'), (int, float, str, bool, list)):
        errors.append('%s: value must be a number, text, yes/no or a list' % where)
    src = item.get('source')
    if not isinstance(src, dict):
        errors.append('%s: source must be an object' % where)
        return
    if src.get('type') not in SOURCE_TYPES:
        errors.append('%s: source.type must be one of %s' % (where, ', '.join(sorted(SOURCE_TYPES))))
    if not str(src.get('url', '')).startswith(('https://', 'http://')):
        errors.append('%s: source.url must be a web address' % where)
    for field in ('published', 'accessed'):
        if field in src and not DATE.match(str(src[field])):
            errors.append('%s: source.%s must be YYYY-MM-DD' % (where, field))
    if 'accessed' not in src:
        errors.append('%s: source.accessed is required' % where)


def main():
    root = sys.argv[1]
    errors = []
    count = 0
    for group, names in GROUPS.items():
        folder = os.path.join(root, group)
        if not os.path.isdir(folder):
            continue
        for base, dirs, files in os.walk(folder):
            for f in sorted(files):
                if not f.endswith('.json'):
                    continue
                path = os.path.join(base, f)
                count += 1
                try:
                    with open(path, encoding='utf-8') as fh:
                        d = json.load(fh)
                except (OSError, ValueError) as e:
                    errors.append('%s: not valid JSON (%s)' % (path, e))
                    continue
                for field in names:
                    if not str(d.get(field, '')).strip():
                        errors.append('%s: missing "%s"' % (path, field))
                if not isinstance(d.get('data'), list) or not d['data']:
                    errors.append('%s: "data" must be a list with at least one value' % path)
                    continue
                for i, item in enumerate(d['data']):
                    check_value(path, i, item, errors)
    for e in errors:
        print(e)
    print('%d files, %d problems' % (count, len(errors)))
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
