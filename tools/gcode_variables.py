#!/usr/bin/env python3
"""Lists, per dialect, every variable that the pack's G-code templates use (docs/FORMAT.md, «G-code de la máquina»),
counted from the converted pack, with its type and label as the source program defines them, and its name in
PrusaSlicer. Writes docs/GCODE_VARIABLES.md.

Nothing is written by hand: the type and the label come from the source program's own definitions (PrintConfig.cpp
of PrusaSlicer, as in Tisma Slicer, and of OrcaSlicer, Creality Print and Elegoo Slicer; fdmprinter.def.json,
fdmextruder.def.json and StartSliceJob.py of Cura). The PrusaSlicer name is the same name when PrusaSlicer has it,
or the one Tisma Slicer's converter renamed it to, as its bundles show (the bundle's text of the same G-code). What no
source gives stays empty.

Usage: gcode_variables.py <pack dir> <out.md> --defs DIALECT=PrintConfig.cpp ... [--cura DIR]
                          [--sources TEXT | --sources-json sources.json]
"""

import argparse
import collections
import difflib
import json
import os
import re

import upstream

TYPES = {'coFloat': 'número', 'coFloats': 'lista de números', 'coInt': 'entero', 'coInts': 'lista de enteros',
         'coString': 'texto', 'coStrings': 'lista de textos', 'coBool': 'sí/no', 'coBools': 'lista de sí/no',
         'coPercent': 'porcentaje', 'coPercents': 'lista de porcentajes', 'coFloatOrPercent': 'número o porcentaje',
         'coFloatsOrPercents': 'lista de números o porcentajes', 'coEnum': 'opción', 'coEnums': 'lista de opciones',
         'coPoint': 'punto', 'coPoints': 'lista de puntos', 'coPoint3': 'punto 3D', 'coNone': ''}
CURA_TYPES = {'float': 'número', 'int': 'entero', 'str': 'texto', 'bool': 'sí/no', 'enum': 'opción',
              'extruder': 'extrusor (entero)', 'optional_extruder': 'extrusor (entero)', '[int]': 'lista de enteros',
              'polygon': 'polígono', 'polygons': 'polígonos', 'vector': 'vector'}
# Words of the macro languages, not variables.
KEYWORDS = {'if', 'elsif', 'else', 'endif', 'and', 'or', 'not', 'true', 'false', 'local', 'global', 'is_nil', 'min',
            'max', 'int', 'round', 'digits', 'zdigits', 'interpolate_table', 'one_of', 'size', 'empty',
            'regex_replace', 'filament_extruder_id'} - {'filament_extruder_id'}
SPAN = re.compile(r'\[([A-Za-z_]\w*)(?:\[[^\]]*\])?\]|\{([^{}]*)\}')
WORD = re.compile(r'(?<![\w."\'])([A-Za-z_]\w*)(?!\w)(?!\s*\()')
STRING = re.compile(r'"(?:\\.|[^"\\])*"')
REGEX = re.compile(r'(?<=~)\s*/(?:\\.|[^/\\])*/')  # the pattern of a =~ or !~ match
LOCAL = re.compile(r'\b(?:local|global)\s+([A-Za-z_]\w*)\s*=')


def variables(text):
    """[(name, local)] of a template; local: assigned in the template itself (a macro's own variable)."""
    own = set(LOCAL.findall(text))
    out = []
    for m in SPAN.finditer(text):
        if m.group(1):
            out.append(m.group(1))
            continue
        inner = REGEX.sub('', STRING.sub('', m.group(2)))
        out.extend(w for w in WORD.findall(inner) if w not in KEYWORDS and not w[0].isdigit())
    return [(n, n in own) for n in out]


def config_defs(path):
    """{key: (type, label)} from a PrintConfig.cpp: each this->add("key", coType) and the label after it."""
    out = {}
    text = open(path, encoding='utf-8', errors='replace').read()
    for m in re.finditer(r'this->add(?:_nullable)?\("(\w+)",\s*(co\w+)\)', text):
        rest = text[m.end():m.end() + 1500]
        nxt = re.search(r'this->add', rest)
        rest = rest[:nxt.start()] if nxt else rest
        full = re.search(r'def->full_label\s*=\s*L\("((?:\\.|[^"\\])*)"\)', rest)
        lab = re.search(r'def->label\s*=\s*L\("((?:\\.|[^"\\])*)"\)', rest)
        tip = re.search(r'def->tooltip\s*=\s*L\("((?:\\.|[^"\\])*)"\)', rest)
        label = full.group(1) if full else lab.group(1) if lab else ''
        if tip and len(label.split()) < 3:
            # A short label ("First layer") says little without its page: the first sentence of the tooltip.
            first = tip.group(1).split('. ')[0].rstrip('.')
            label = first if len(first) <= 110 else label or first[:110]
        out.setdefault(m.group(1), (TYPES.get(m.group(2), m.group(2)), label.replace('\\"', '"')))
    # Settings added once per axis ("machine_max_feedrate_" + axis.name).
    for m in re.finditer(r'this->add\("(\w+_)"\s*\+\s*axis\.name,\s*(co\w+)\)', text):
        for axis in 'xyze':
            out.setdefault(m.group(1) + axis, (TYPES.get(m.group(2), m.group(2)), ''))
    # Values the program sets while slicing (placeholders that are not settings).
    folder = os.path.dirname(path)
    files = sorted(os.path.relpath(os.path.join(r, f), folder) for r, _, fs in os.walk(folder) for f in fs
                   if f.endswith('.cpp'))
    for f in files:
        body = open(os.path.join(folder, f), encoding='utf-8', errors='replace').read()
        for m in re.finditer(r'(?:set_key_value|\.set)\(\s*"(\w+)"\s*,\s*new\s+(ConfigOption\w+)', body):
            typ = 'co' + m.group(2)[len('ConfigOption'):]
            typ = re.sub(r'Nullable$', '', typ)
            out.setdefault(m.group(1), (TYPES.get(typ, typ), 'set by the program while slicing (%s)' % f))
    return out


def cura_defs(cura):
    out = {}
    for f in ('resources/definitions/fdmprinter.def.json', 'resources/definitions/fdmextruder.def.json'):
        p = os.path.join(cura, f)
        if not os.path.exists(p):
            continue

        def walk(tree):
            for k, s in tree.items():
                if isinstance(s, dict):
                    if s.get('type') and s.get('type') != 'category':
                        out.setdefault(k, (CURA_TYPES.get(s['type'], s['type']), s.get('label', '')))
                    walk(s.get('children') or {})
        walk(json.load(open(p, encoding='utf-8')).get('settings', {}))
    job = os.path.join(cura, 'plugins/CuraEngineBackend/StartSliceJob.py')
    if os.path.exists(job):
        for k in re.findall(r'result\["(\w+)"\]\s*=', open(job, encoding='utf-8').read()):
            out.setdefault(k, ('', 'set by Cura when slicing (StartSliceJob.py)'))
    return out


def merged(common, own):
    out = {}
    for part in (common or {}, own or {}):
        for k, v in part.items():
            if isinstance(v, dict):
                out.setdefault(k, {}).update(v)
            else:
                out[k] = v
    return out


def renames(pairs):
    """{source name: PrusaSlicer name} that Tisma Slicer's text shows: one-word changes inside placeholders where the
    same template is otherwise equal, kept when one name always becomes the same other one, seen 3 times or more."""
    seen = collections.defaultdict(collections.Counter)
    tok = re.compile(r'[A-Za-z_]\w*|\S')
    for src, dst in pairs:
        a, b = tok.findall(src), tok.findall(dst)
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
        ops = [o for o in sm.get_opcodes() if o[0] != 'equal']
        if not ops or len(ops) > 12:
            continue
        for op, i1, i2, j1, j2 in ops:
            if op != 'replace':
                continue
            wa, wb = a[i1:i2], b[j1:j2]
            ida = [x for x in wa if re.match(r'[A-Za-z_]', x)]
            idb = [x for x in wb if re.match(r'[A-Za-z_]', x)]
            # One name for another, with at most the brackets around it changed ({name} -> [name]).
            if len(ida) == 1 and len(idb) == 1 and all(x in '[]{}' for x in wa + wb if x not in ida + idb):
                inside = any(x in '[{' for x in wa) or (i1 > 0 and a[i1 - 1] in '[{')
                if inside:
                    seen[ida[0]][idb[0]] += 1
    return {k: c.most_common(1)[0][0] for k, c in seen.items()
            if c.most_common(1)[0][1] >= 3 and c.most_common(1)[0][1] >= 0.9 * sum(c.values())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pack')
    ap.add_argument('out')
    ap.add_argument('--defs', action='append', default=[], metavar='DIALECT=PrintConfig.cpp')
    ap.add_argument('--cura', help='a checkout of Cura (resources/definitions, plugins/CuraEngineBackend)')
    ap.add_argument('--sources', default='', help='a line that names the commits of the definitions')
    ap.add_argument('--sources-json', help='sources.json: the line that names the commits, made from it')
    args = ap.parse_args()
    if args.sources_json:
        s = json.load(open(args.sources_json, encoding='utf-8'))
        args.sources = 'Definiciones: Tisma Slicer %s (PrusaSlicer), %s.' % (
            s['tisma_slicer']['commit'][:7],
            ', '.join('%s %s' % (x['program'], x['commit'][:7]) for x in s['converted_from']))

    defs = {}
    for spec in args.defs:
        d, _, path = spec.partition('=')
        defs[d] = config_defs(path)
    if args.cura:
        defs['cura'] = cura_defs(args.cura)
    prusa = defs.get('prusaslicer', {})

    index = json.load(open(os.path.join(args.pack, 'index.json'), encoding='utf-8'))
    use = collections.defaultdict(lambda: collections.defaultdict(lambda: {'templates': collections.Counter(),
                                                                          'variants': set(), 'local': False}))
    pairs = collections.defaultdict(list)
    for v in index['vendors']:
        for m in v['models']:
            if m['technology'] != 'fff':
                continue
            doc = json.load(open(os.path.join(args.pack, m['file']), encoding='utf-8'))
            for var in doc['variants']:
                g = merged(doc['common'].get('gcode'), var.get('gcode'))
                dialect = g.get('dialect')
                original = merged({'': doc.get('original_common', {})}, {'': var.get('original', {})})['']
                for name, t in (g.get('templates') or {}).items():
                    for text in (t if isinstance(t, list) else [t]):
                        if not text:
                            continue
                        for n, local in variables(text):
                            u = use[dialect][n]
                            u['templates'][name] += 1
                            u['variants'].add(m['file'] + '#' + var['id'])
                            u['local'] = u['local'] or local
                        key = {'start': 'start_gcode', 'end': 'end_gcode'}.get(name)
                        if dialect != 'prusaslicer' and key and original.get(key):
                            pairs[dialect].append((text, original[key].replace('\\n', '\n')))

    lines = ['# Variables del G-code de las máquinas', '',
             'Cada variable que usan los G-code de `gcode.templates` del paquete (`docs/FORMAT.md`, «G-code de la '
             'máquina»), por dialecto, contada en el paquete convertido. Lo genera `tools/gcode_variables.py`: no se '
             'escribe a mano.', '',
             '- **Tipo** y **qué es:** como los define el programa de origen (el nombre que muestra, en inglés). '
             'Vacío si sus definiciones no la tienen: la llena el programa al laminar o la define el firmware.',
             '- **Dónde:** en qué G-code aparece y en cuántas variantes.',
             '- **En PrusaSlicer:** el mismo nombre si PrusaSlicer lo tiene, o el que le pone Tisma Slicer al '
             'convertir (el mismo G-code en su paquete). Vacío si ninguno lo dice.',
             '- **Propia de la macro:** la asigna el G-code mismo (`local` o `global`).', '']
    if args.sources:
        lines += [args.sources, '']
    for dialect in ('prusaslicer', 'orcaslicer', 'crealityprint', 'elegooslicer', 'cura'):
        if dialect not in use:
            continue
        ren = renames(pairs[dialect]) if dialect != 'prusaslicer' else {}
        if dialect in ('orcaslicer', 'crealityprint', 'elegooslicer'):
            ren = dict(ren, **upstream.ORCA_TO_PRUSA)  # the renaming the converter itself uses
        own = defs.get(dialect, {})
        names = sorted(use[dialect], key=lambda n: (-len(use[dialect][n]['variants']), n))
        lines += ['## `%s`' % dialect, '', '%d variables.' % len(names), '',
                  '| Variable | Tipo | Dónde | Qué es | En PrusaSlicer |', '|---|---|---|---|---|']
        for n in names:
            u = use[dialect][n]
            typ, label = own.get(n, ('', ''))
            if u['local'] and not own.get(n):
                typ, label = 'propia de la macro', ''
            where = ', '.join('`%s`' % t for t, _ in u['templates'].most_common()) + \
                ' (%d)' % len(u['variants'])
            if dialect == 'prusaslicer':
                eq = n if n in prusa else ''
            else:
                eq = ren.get(n) or (n if n in prusa else '')
            cell = lambda s: str(s).replace('|', '\\|')
            lines.append('| `%s` | %s | %s | %s | %s |' % (n, cell(typ), where, cell(label),
                                                            '`%s`' % eq if eq else ''))
        lines.append('')
    with open(args.out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines))
    print({d: len(use[d]) for d in use})


if __name__ == '__main__':
    main()
