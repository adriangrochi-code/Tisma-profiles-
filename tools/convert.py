#!/usr/bin/env python3
"""Converts the Tisma Slicer vendor bundles (PrusaSlicer INI format, with the profiles it took from PrusaSlicer,
OrcaSlicer, Creality Print, Elegoo Slicer and Cura) and the UVtools resin printer profiles into a Tisma profile pack
(docs/FORMAT.md).

Each profile keeps every value of its source (inheritance resolved) under "original", and the values the engine
understands, under its own keys (the engine's docs/CONFIG.md), under "profile.settings".

Usage: convert.py <profiles dir> <out dir> [--source-commit SHA] [--uvtools DIR --uvtools-commit SHA]
                  [--upstream REPOSITORY=DIR ...]
"""

import argparse
import collections
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

import gcode_variables
import translation
import upstream
from translation import FILAMENT_VARIABLES, clean_num, first_text, fix_point, flag, num, pct_or_abs

FORMAT_VERSION = 2


# ---------------------------------------------------------------------------------------------------------------------
# Bundles

def parse_ini(path):
    """[(kind, name, {key: value})] in file order; kind is 'vendor' for the [vendor] section."""
    out = []
    current = None
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\r\n')
            if not line or line.lstrip().startswith('#'):
                continue
            m = re.match(r'\[([^:\]]+)(?::(.*))?\]\s*$', line)
            if m:
                current = {}
                out.append((m.group(1).strip(), (m.group(2) or '').strip(), current))
                continue
            if current is None or '=' not in line:
                continue
            k, v = line.split('=', 1)
            current[k.strip()] = v.strip()
    return out


class Bundle:
    def __init__(self, path):
        self.path = path
        self.id = os.path.splitext(os.path.basename(path))[0]
        self.vendor = {}
        self.models = collections.OrderedDict()
        self.sections = collections.OrderedDict()
        for kind, name, values in parse_ini(path):
            if kind == 'vendor':
                self.vendor = values
            elif kind == 'printer_model':
                self.models[name] = values
            else:
                self.sections.setdefault((kind, name), values)

    def flat(self, kind, name, fallback, depth=0):
        values = self.sections.get((kind, name))
        if values is None and fallback is not None:
            values = fallback.get((kind, name))
        if values is None and kind == 'filament' and name.endswith(' @Template'):
            values = self.sections.get((kind, name[:-len(' @Template')]))
        if values is None:
            raise KeyError('%s "%s" not found' % (kind, name))
        out = {}
        parents = values.get('inherits', '')
        if parents and depth < 30:
            for parent in [x.strip().strip('"') for x in parents.split(';') if x.strip()]:
                out.update(self.flat(kind, parent, fallback, depth + 1))
        out.update(values)
        out.pop('inherits', None)
        return out

    def defined_in(self, kind, name, key, fallback, depth=0):
        """The name of the section that sets a key for a resolved section (the same order as flat())."""
        values = self.sections.get((kind, name))
        if values is None and fallback is not None:
            values = fallback.get((kind, name))
        if values is None:
            return None
        if key in values:
            return name
        found = None
        parents = values.get('inherits', '')
        if parents and depth < 30:
            for parent in [x.strip().strip('"') for x in parents.split(';') if x.strip()]:
                found = self.defined_in(kind, parent, key, fallback, depth + 1) or found
        return found


class SyntheticBundle(Bundle):
    """A bundle made from loose preset files (one preset per file, every value written, no section header)."""

    def __init__(self, bundle_id, vendor_name):
        self.path = ''
        self.id = bundle_id
        self.vendor = {'name': vendor_name}
        self.models = collections.OrderedDict()
        self.sections = collections.OrderedDict()


def read_preset(path):
    values = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\r\n')
            if not line or line.lstrip().startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            values[k.strip()] = v.strip()
    values.pop('inherits', None)  # exported presets carry every value; the parent is not part of the bundle
    return values


def uvtools_bundles(root):
    """UVtools ships resin printers (PrusaSlicer/printer/<Vendor> <Model>.ini) and generic resin print profiles
    (PrusaSlicer/sla_print/*.ini)."""
    out = collections.OrderedDict()
    pdir = os.path.join(root, 'PrusaSlicer', 'printer')
    for f in sorted(os.listdir(pdir)):
        if not f.endswith('.ini'):
            continue
        name = f[:-4]
        vendor, _, model = name.partition(' ')
        b = out.setdefault(vendor, SyntheticBundle('UVtools_' + slug(vendor), vendor))
        c = read_preset(os.path.join(pdir, f))
        c['printer_technology'] = 'SLA'
        # The resin bundles of the makers fit 'PRINTER_TECHNOLOGY_SLA' printers of their brand; UVtools does not write
        # that keyword, so its printers would only get the generic Prusa resins.
        if 'PRINTER_TECHNOLOGY_SLA' not in c.get('printer_notes', ''):
            c['printer_notes'] = c.get('printer_notes', '') + '\\nPRINTER_TECHNOLOGY_SLA'
        mid = slug(model or name)
        # printer_model stays as written (UVtools sets the one whose resin materials fit); the pack model is apart.
        c['pack_model'] = mid
        c['printer_variant'] = c.get('printer_variant') or 'default'
        m = re.search(r'FILEFORMAT_([A-Za-z0-9_.]+)', c.get('printer_notes', ''))
        if m:
            c['file_format'] = m.group(1).lower()
        b.sections[('printer', name)] = c
        b.models[mid] = {'name': name, 'technology': 'SLA', 'family': vendor, 'variants': 'default'}
    sdir = os.path.join(root, 'PrusaSlicer', 'sla_print')
    if os.path.isdir(sdir):
        b = SyntheticBundle('UVtools_Universal', 'UVtools universal resin print profiles')
        for f in sorted(os.listdir(sdir)):
            if f.endswith('.ini'):
                c = read_preset(os.path.join(sdir, f))
                c['compatible_printers'] = ''
                c['compatible_printers_condition'] = ''
                b.sections[('sla_print', f[:-4])] = c
        out['~universal'] = b
    return list(out.values())


# ---------------------------------------------------------------------------------------------------------------------
# Compatibility conditions (the boolean expressions of compatible_printers_condition / compatible_prints_condition)

TOKEN = re.compile(r'\s*(?:(?P<re>[=!]~\s*/(?:\\.|[^/])*/)|(?P<num>\d+\.?\d*(?:[eE][-+]?\d+)?)|'
                   r'(?P<str>"(?:\\.|[^"])*")|(?P<id>[A-Za-z_][A-Za-z0-9_]*(?:\[\d+\])?)|'
                   r'(?P<op>&&|\|\||==|!=|<=|>=|<|>|\(|\)|!|=))')


def split_list(value):
    sep = ';' if ';' in value and ',' not in value.replace('";"', '') else ','
    return [x.strip().strip('"') for x in value.split(sep)]


def unescape(v):
    """A value as the source program holds it: the bundle files write new lines and quotes escaped."""
    return v.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')


def lookup(config, ident):
    m = re.match(r'(\w+)\[(\d+)\]$', ident)
    if m:
        items = split_list(config.get(m.group(1), ''))
        i = int(m.group(2))
        return unescape(items[i]) if i < len(items) else ''
    if ident == 'num_extruders' and ident not in config:
        # Not a stored setting: the source programs count the extruders from nozzle_diameter.
        return str(len(split_list(config.get('nozzle_diameter', '0.4'))))
    return unescape(config.get(ident, '').strip('"'))


def as_value(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return v


def text_of(v):
    """A number setting as the source program prints it in a regular expression match (0.4, not 0.4000)."""
    if isinstance(v, float):
        return str(int(v)) if v == int(v) else repr(v)
    return str(v)


def compile_condition(text):
    """A function of a config dict, or None if the expression is not understood."""
    text = text.strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"' and text.count('"') == 2:
        text = text[1:-1]
    if not text:
        return lambda c: True
    py = []
    pos = 0
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m or m.end() == pos:
            if text[pos:].strip() == '':
                break
            return None
        pos = m.end()
        if m.group('re'):
            op = m.group('re')[:2]
            rx = m.group('re')[2:].strip()[1:-1]
            if not py or not py[-1].startswith('V('):
                return None
            subject = py.pop()
            # The source programs match the whole value (boost::regex_match), where "." also takes new lines.
            py.append('%s(re.fullmatch(%r, S(%s), re.S) is not None)' % ('not ' if op == '!~' else '', rx, subject))
        elif m.group('num'):
            py.append(repr(float(m.group('num'))))
        elif m.group('str'):
            # A number written as a string ("0.2") compares with a number setting as a number.
            py.append(repr(as_value(m.group('str')[1:-1])))
        elif m.group('id'):
            word = m.group('id')
            if word in ('and', 'or', 'not'):
                py.append(' %s ' % word)
            elif word in ('true', 'false'):
                py.append(' %s ' % word.capitalize())
            else:
                py.append('V(%r)' % word)
        else:
            op = m.group('op')
            py.append({'!': ' not ', '=': '==', '&&': ' and ', '||': ' or '}.get(op, op))
    expr = ''.join(py).strip()
    try:
        code = compile(expr, '<condition>', 'eval')
    except SyntaxError:
        return None

    def run(config):
        try:
            return bool(eval(code, {'re': re, 'V': lambda k: as_value(lookup(config, k)), 'S': text_of}))
        except Exception:
            return False
    return run


# ---------------------------------------------------------------------------------------------------------------------
# Value helpers


def put(settings, group, key, value):
    if value is None:
        return
    if isinstance(value, float):
        value = clean_num(value)
    settings.setdefault(group, {})[key] = value


def gcode_text(v):
    if v is None:
        return None
    v = v.strip()
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        v = v[1:-1]
    return v.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')


# Placeholders of the source G-code templates. Values known from the printer profile are written in; values that only
# exist while slicing get the pack's own names (docs/FORMAT.md, "Variables"); filament temperatures stay as variables
# that the filament profile fills.
RUNTIME = {('first_layer_print_min', 0): 'first_layer_min_x', ('first_layer_print_min', 1): 'first_layer_min_y',
           ('first_layer_print_max', 0): 'first_layer_max_x', ('first_layer_print_max', 1): 'first_layer_max_y',
           ('first_layer_print_size', 0): 'first_layer_size_x', ('first_layer_print_size', 1): 'first_layer_size_y',
           ('total_layer_count', None): 'layer_count', ('initial_tool', None): 'initial_tool',
           ('initial_extruder', None): 'initial_tool', ('current_extruder', None): 'initial_tool',
           ('travel_speed', None): 'travel_speed', ('layer_height', None): 'layer_height',
           ('first_layer_height', None): 'first_layer_height', ('year', None): 'year', ('month', None): 'month',
           ('day', None): 'day', ('hour', None): 'hour', ('minute', None): 'minute', ('second', None): 'second',
           ('input_filename_base', None): 'input_filename_base'}
PLACEHOLDER = re.compile(r'\[(\w+)\]|\{(\w+)(?:\[(\d+)\])?\}')


def bed_box(c):
    pts = []
    for p in c.get('bed_shape', '').split(','):
        p = fix_point(p)
        if 'x' in p:
            x, y = num(p.split('x')[0]), num(p.split('x')[1])
            if x is not None and y is not None:
                pts.append((x, y))
    if not pts:
        return None
    lo = (min(p[0] for p in pts), min(p[1] for p in pts))
    hi = (max(p[0] for p in pts), max(p[1] for p in pts))
    return {'print_bed_min': lo, 'print_bed_max': hi, 'print_bed_size': (hi[0] - lo[0], hi[1] - lo[1])}


def engine_gcode(text, c):
    """(G-code for the engine, None) or (None, reason) when the template needs the source program's macro language
    or a value the pack cannot give."""
    box = bed_box(c) or {}
    missing = []

    def repl(m):
        name = m.group(1) or m.group(2)
        index = int(m.group(3)) if m.group(3) is not None else None
        if name in FILAMENT_VARIABLES:
            return '{%s}' % name
        key = (name, index if (name, index) in RUNTIME else None)
        if (name, index) in RUNTIME or key in RUNTIME:
            return '{%s}' % RUNTIME.get((name, index), RUNTIME.get(key))
        if name in box:
            v = box[name][index or 0]
            return str(clean_num(v))
        if name in c and name not in ('start_gcode', 'end_gcode'):
            items = split_list(c[name]) if index is not None else [c[name].strip('"')]
            if index is None or index < len(items):
                return items[index or 0]
        if name.isdigit():
            return m.group(0)
        missing.append(name)
        return m.group(0)
    out = PLACEHOLDER.sub(repl, text)
    rest = PLACEHOLDER.sub('', out)
    if '{' in rest:
        return None, 'macros'
    if missing:
        return None, 'unknown: ' + ', '.join(sorted(set(missing)))
    return out, None


# ---------------------------------------------------------------------------------------------------------------------
# The printer's own custom G-code, as its source program has it (docs/FORMAT.md, "G-code de la máquina")

class Sources:
    """The checkouts of the programs that Tisma Slicer converted its bundles from, by repository."""

    def __init__(self, specs):
        self.repos = {}
        for spec in specs or []:
            url, _, folder = spec.partition('=')
            commit = ''
            try:
                commit = subprocess.run(['git', '-C', folder, 'rev-parse', 'HEAD'], capture_output=True,
                                        text=True, check=True).stdout.strip()
            except (OSError, subprocess.CalledProcessError):
                pass
            self.repos[url.rstrip('/')] = (folder, commit)
        self.cache = {}
        self.bases = {}
        self.kinds = {}
        self.names = {}  # (repository, preset name in the source program) -> printer entry path
        self.matched = set()  # bundles with printers that the source program has
        self.unmatched = set()  # bundles with printers that it has not (made by hand from it, like the belt ones)

    def presets(self, bundle, kind):
        """The source program's "process" or "filament" presets of an OrcaSlicer-style bundle, or None."""
        base = self.bases.get(bundle.path)
        if base is None:
            return None
        if (base, kind) not in self.kinds:
            library = os.path.join(os.path.dirname(base), 'OrcaFilamentLibrary')
            self.kinds[(base, kind)] = upstream.OrcaVendor(base, (library,) if kind == 'filament' else (), kind=kind)
        return self.kinds[(base, kind)]

    def of(self, bundle, stats):
        """(dialect, repository, commit, reader) of a bundle converted from another program, or None. The reader is
        None when the checkout is missing or at another commit than the one the bundle was made from."""
        if not bundle.path or bundle.path in self.cache:
            return self.cache.get(bundle.path)
        src = upstream.bundle_source(bundle.path)
        out = None
        if src:
            program, repo, folder, commit = src
            dialect = upstream.DIALECTS.get(repo)
            reader = None
            have = self.repos.get(repo)
            if dialect is None:
                stats['bundles from a program the pack does not read (%s)' % program] += 1
            elif have and (not commit or have[1] == commit):
                if dialect == 'cura':
                    reader = upstream.CuraDefinitions(os.path.join(have[0], os.path.dirname(folder)))
                else:
                    reader = upstream.OrcaVendor(os.path.join(have[0], folder))
                    self.bases[bundle.path] = os.path.join(have[0], folder)
            else:
                stats['bundles without their source checkout (%s)' % dialect] += 1
            out = (dialect, repo, commit, reader)
        self.cache[bundle.path] = out
        return out


def bundle_gcode(b, kind, name, c, everything, keys):
    """The G-code block of a section, from the bundle itself (its keys as the bundle writes them)."""
    templates, source_keys, origin = {}, {}, {}
    for k, neutral in keys.items():
        text = gcode_text(c.get(k))
        if text:
            templates[neutral] = text
            source_keys[neutral] = k
            origin[neutral] = b.defined_in(kind, name, k, everything)
    return templates, source_keys, origin


PRINTER_KEYS = {k: v for k, v in upstream.PRUSA_KEYS.items() if not v.startswith('filament_')}
FILAMENT_KEYS = {k: v for k, v in upstream.PRUSA_KEYS.items() if v.startswith('filament_')}


def printer_gcode(b, name, c, everything, sources, stats, filament_names=frozenset()):
    """The printer's G-code block: from the source program when the bundle was converted from another one and its
    checkout is given, else from the bundle."""
    src = sources.of(b, stats)
    rel = flag(c['use_relative_e_distances']) if 'use_relative_e_distances' in c else None
    if src and src[3] is not None:
        dialect, repo, commit, reader = src
        if dialect == 'cura':
            m = re.search(r'CURA_DEFINITION_(\S+?)(?:\\n|$)', c.get('printer_notes', ''))
            block = upstream.cura_machine_gcode(reader, m.group(1)) if m else None
        else:
            block = upstream.orca_machine_gcode(reader, name)
        if block is not None and block['templates'] and not block.get('expressions', {}).get('start'):
            stats['printer G-code from the source program (%s)' % dialect] += 1
            out = {'dialect': dialect, 'origin': 'source_program',
                   'source': {'repository': repo, 'commit': commit, 'preset': block['preset']},
                   'templates': {k: v for k, v in block['templates'].items() if v},
                   'keys': block['keys'], 'from': block['from'],
                   'relative_extrusion': rel if block['relative_extrusion'] is None else block['relative_extrusion']}
            out['keys'] = {k: v for k, v in out['keys'].items() if k in out['templates']}
            out['from'] = {k: v for k, v in out['from'].items() if k in out['templates']}
            for k in ('expressions', 'values'):
                if block.get(k):
                    out[k] = block[k]
            return out
        stats['printer G-code from the bundle: not in the source program (%s)' % dialect] += 1
    templates, keys, origin = bundle_gcode(b, 'printer', name, c, everything, PRINTER_KEYS)
    out = {'dialect': 'prusaslicer', 'origin': 'converted_bundle' if src else 'bundle',
           'source': {'bundle': b.id, 'section': name}, 'templates': templates, 'keys': keys, 'from': origin,
           'relative_extrusion': rel}
    if src:
        # The program the bundle was converted from (its dialect, when the pack reads it), and its repository.
        out['source'].update({'program': src[0], 'repository': src[1], 'commit': src[2]})
    # The variables of its own G-code and of the filaments' G-code, which runs with the printer's values too.
    values = bundle_values(templates, c, template_names(templates) | filament_names)
    if values:
        out['values'] = values
    stats['printer G-code from the bundle (%s)' % ('converted by Tisma Slicer' if src else 'PrusaSlicer format')] += 1
    return out


def template_names(templates):
    names = set()
    for t in templates.values():
        for text in (t if isinstance(t, list) else [t]):
            if text:
                names.update(n for n, local in gcode_variables.variables(text) if not local)
    return names


OPTION_TYPES = {}  # PrusaSlicer's type of each key (its PrintConfig.cpp), when given (--prusa-config)


def bundle_values(templates, c, names=None):
    """The section's values of the variables that its G-code uses, for a PrusaSlicer-format bundle, typed as
    PrusaSlicer holds them (yes/no, numbers, lists; translation.typed); as text when the type is not known."""
    names = template_names(templates) if names is None else names
    return {k: translation.typed(c[k], OPTION_TYPES.get(k, ''))
            for k in sorted(names) if k in c and not k.endswith('_gcode')}


def source_filament_gcode(src, found, values):
    """The G-code block of a filament from the source program's preset (OrcaSlicer family), or None."""
    templates, keys = {}, {}
    for key, neutral in (('filament_start_gcode', 'filament_start'), ('filament_end_gcode', 'filament_end')):
        v = values.get(key)
        if isinstance(v, list):
            v = v[0] if v else ''
        if isinstance(v, str) and v.strip():
            templates[neutral] = v
            keys[neutral] = key
    if not templates:
        return None
    for old, new in upstream.LEGACY_RENAMES.get(src[0], {}).get('filament_start_gcode', []):
        if 'filament_start' in templates and old in templates['filament_start']:
            # As the program rewrites an old name when it loads the preset.
            templates['filament_start'] = templates['filament_start'].replace(old, new)
    return {'dialect': src[0], 'origin': 'source_program',
            'source': {'repository': src[1], 'commit': src[2], 'preset': found[0]}, 'templates': templates,
            'keys': keys}


def filament_gcode(b, name, c, everything, sources, stats):
    templates, keys, origin = bundle_gcode(b, 'filament', name, c, everything, FILAMENT_KEYS)
    if not templates:
        return None
    src = sources.of(b, stats)
    return {'dialect': 'prusaslicer', 'origin': 'converted_bundle' if src else 'bundle',
            'source': {'bundle': b.id, 'section': name}, 'templates': templates, 'keys': keys, 'from': origin}


def engine_texts(block, c):
    """The start and end G-code to convert for the engine (profile.settings), in the bundle's names: the source
    program's text with its variables renamed as Tisma Slicer does, or the bundle's own text."""
    if block['origin'] != 'source_program' or block['dialect'] == 'cura':
        return {k: gcode_text(c[k]) for k in ('start_gcode', 'end_gcode') if c.get(k)}
    return {k: upstream.to_prusa_names(block['templates'][n]) for k, n in (('start_gcode', 'start'),
                                                                         ('end_gcode', 'end'))
            if block['templates'].get(n)}


# ---------------------------------------------------------------------------------------------------------------------
# Mapping to engine keys (docs/CONFIG.md of the engine). Each function returns (settings, used source keys).

# PrusaSlicer names of the machine options that the OrcaSlicer family names otherwise (besides ORCA_TO_PRUSA).
MACHINE_RENAMES = {'machine_max_feedrate_' + a: 'machine_max_speed_' + a for a in 'xyze'}


def model_from_source(model, assets, base, mid, out, vdir):
    """Fills what the bundle lost of a model and its source program has (the machine_model file of its
    OrcaSlicer-style vendor folder `base`): family, default materials and pictures, copied into the pack. Tisma
    Slicer's Creality Print and Elegoo Slicer bundles keep none of them. The filled fields."""
    sm = upstream.orca_machine_model(base, mid)
    if not sm:
        return []
    filled = []
    if not model['family'] and sm.get('family'):
        model['family'] = sm['family']
        filled.append('family')
    if not model['default_materials'] and sm.get('default_materials'):
        model['default_materials'] = [x.strip() for x in sm['default_materials'].split(';') if x.strip()]
        filled.append('default_materials')
    for key, f in (('thumbnail', mid + '_cover.png'), ('bed_model', sm.get('bed_model', '')),
                   ('bed_texture', sm.get('bed_texture', ''))):
        src = os.path.join(base, f) if f else ''
        if key not in assets and f and os.path.isfile(src):
            rel = os.path.join(vdir, 'assets', f)
            os.makedirs(os.path.dirname(os.path.join(out, rel)), exist_ok=True)
            shutil.copyfile(src, os.path.join(out, rel))
            assets[key] = rel
            filled.append('assets.' + key)
    return filled


def lost_values(kind, c, source):
    """{PrusaSlicer key: bundle text} of the options of the translation table of a kind that the bundle lacks and the
    source program's preset (its values, with the source names) gives."""
    back = {v: k for k, v in upstream.ORCA_TO_PRUSA.items()}
    out = {}
    for e in translation.TABLE[kind]:
        for key in (e['from'] if isinstance(e.get('from'), list) else [e.get('from')]):
            if not key or key in c or key in out:
                continue
            name = MACHINE_RENAMES.get(key, back.get(key, key))
            if name not in source:
                continue
            v = source[name]
            out[key] = ','.join(str(x) for x in v) if isinstance(v, list) else \
                ('1' if v is True else '0' if v is False else str(v))
    return out


def leaves(d, prefix=''):
    """(group.key, value) of a profile's settings; the G-code variables one level deeper (machine.variables.x)."""
    for k, v in d.items():
        if isinstance(v, dict) and (not prefix or prefix == 'machine.' and k == 'variables'):
            yield from leaves(v, prefix + k + '.')
        else:
            yield prefix + k, v


def fill_lost(settings, full):
    """Puts in settings the values of full (the translation with the lost values) that settings lacks; their paths."""
    have = dict(leaves(settings))
    filled = []
    for path, value in leaves(full):
        if path not in have and not path.startswith('_'):
            node = settings
            parts = path.split('.')
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = clean_num(value) if isinstance(value, float) else value
            filled.append(path)
    return filled


def map_printer(c, texts=None):
    """texts: the start and end G-code to convert, when not the bundle's own (engine_texts)."""
    if texts is None:
        texts = {k: gcode_text(c[k]) for k in ('start_gcode', 'end_gcode') if c.get(k)}

    def gcode_template(e, c, s):
        used = []
        for key in ('start_gcode', 'end_gcode'):
            if texts.get(key):
                text, why = engine_gcode(texts[key], c)
                if text is not None:
                    put(s, 'machine', key, text)
                    used.append(key)
                else:
                    s.setdefault('_notes', {})[key] = why
        return bool(used), used
    return translation.translate('printer', c, rules={'gcode_template': gcode_template})


def map_filament(c):
    return translation.translate('filament', c)


def map_print(c, nozzle):
    return translation.translate('print', c, nozzle=nozzle)


def map_resin_printer(c):
    return translation.translate('printer_sla', c)


def map_resin_material(c):
    return translation.translate('sla_material', c)


def map_resin_print(c):
    return translation.translate('sla_print', c)


NOZZLE_CONDITION = re.compile(r'(?:^|\band\b|&&|\()\s*nozzle_diameter\[0\]\s*==\s*"?(\d+(?:\.\d+)?)"?\s*(?=\)|\band\b|&&|$)')
NOZZLE_NAME = re.compile(r'(?i)(?<![\d.])(\d+(?:\.\d+)?)\s*(?:mm)?\s*nozzle\b|\bnozzle\s*(\d+(?:\.\d+)?)(?![\d.])')


def print_nozzle(name, c, compatible, pool):
    """(nozzle, how) of a print profile: the nozzle of all its printers; or the one its condition requires (a
    "nozzle_diameter[0]==X" that every printer must meet); or the one its name says ("0.2 nozzle", "0.6mm nozzle"),
    when its printers do not say otherwise. (None, None) when nothing says it."""
    nozzles = set()
    if compatible:
        nozzles = {num(dict(pc).get('nozzle_diameter')) for pc, rel in pool if rel in compatible} - {None}
        if len(nozzles) == 1:
            return nozzles.pop(), 'printers'
    cond = c.get('compatible_printers_condition', '').strip().strip('"')
    if ' or ' not in cond and '||' not in cond:
        found = {float(x) for x in NOZZLE_CONDITION.findall(cond)}
        if len(found) == 1:
            return found.pop(), 'condition'
    found = {float(a or b) for a, b in NOZZLE_NAME.findall(name)}
    if len(found) == 1:
        n = found.pop()
        if 0.1 <= n <= 3 and (not nozzles or n in nozzles):
            return n, 'name'
    return None, None


# ---------------------------------------------------------------------------------------------------------------------
# Pack writer

def slug(text):
    s = re.sub(r'[^A-Za-z0-9._@+-]+', '_', text).strip('_')
    return s[:120] or 'profile'


class Writer:
    def __init__(self, out):
        self.out = out
        self.taken = set()
        self.stats = collections.Counter()
        self.unmapped = collections.defaultdict(collections.Counter)
        self.left_out = []

    def path(self, *parts):
        base = os.path.join(*parts)
        stem, ext = os.path.splitext(base)
        n = 1
        while base.lower() in self.taken:
            n += 1
            base = '%s (%d)%s' % (stem, n, ext)
        self.taken.add(base.lower())
        return base

    def write(self, rel, data):
        full = os.path.join(self.out, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=False)
            f.write('\n')


def license_of(bundle_id):
    if bundle_id.startswith('UVtools_'):
        return 'AGPL-3.0-or-later', 'UVtools resin printer profiles'
    if bundle_id.startswith('Cura_') or bundle_id == 'Belt_BLACKBELT_3D':
        return 'LGPL-3.0-or-later', 'UltiMaker Cura / BlackBelt Cura definitions'
    if bundle_id.startswith('Orca_'):
        return 'AGPL-3.0-or-later', 'OrcaSlicer profiles'
    if bundle_id.startswith('CrealityPrint_'):
        return 'AGPL-3.0-or-later', 'Creality Print profiles'
    if bundle_id.startswith('ElegooSlicer_'):
        return 'AGPL-3.0-or-later', 'Elegoo Slicer profiles'
    return 'AGPL-3.0-or-later', 'PrusaSlicer / Tisma Slicer vendor profiles'


def canonical_vendor(bundle_id):
    s = re.sub(r'^(orca|crealityprint|elegooslicer|cura|belt|uvtools)_', '', bundle_id.lower())
    s = re.sub(r'sla$', '', s)
    s = re.sub(r'research|technologies|technology|3d$', '', s)
    return re.sub(r'[^a-z0-9]', '', s)


def vendor_words(vendor_name, bundle_id):
    return {vendor_name.lower(), canonical_vendor(bundle_id)} | set(vendor_name.lower().split())


def is_hf(name):
    return bool(re.search(r'(?i)\bhf|high[- ]flow', name))


def same_model(machines, name, vendor_name, bundle_id, model_index):
    """The pack printers of the same model and nozzle as a printer preset of the source program, or None."""
    if machines is None or not hasattr(machines, 'find') or machines.find(name) is None:
        return None
    try:
        values, _ = machines.resolve(machines.find(name))
    except KeyError:
        return None
    model = values.get('printer_model')
    nozzle = values.get('nozzle_diameter')
    nozzle = num(nozzle[0] if isinstance(nozzle, list) and nozzle else nozzle)
    if not model or nozzle is None:
        return None
    key = (canonical_vendor(bundle_id), canonical_model(model, vendor_words(vendor_name, bundle_id)))
    hits = [rel for rel, n, hf in model_index.get(key, []) if n == nozzle and hf == is_hf(name)]
    return hits or None


def canonical_model(name, vendor_words):
    s = name.lower().replace('original ', '')
    for word in sorted(vendor_words, key=len, reverse=True):
        if word:
            s = s.replace(word, '')
    return re.sub(r'[^a-z0-9]', '', s)


def diff_settings(common, full):
    out = {}
    for group, values in full.items():
        if not isinstance(values, dict):
            if common.get(group) != values:
                out[group] = values
            continue
        for k, v in values.items():
            if common.get(group, {}).get(k, object()) != v:
                out.setdefault(group, {})[k] = v
    return out


def common_settings(settings_list):
    if not settings_list:
        return {}
    out = {}
    first = settings_list[0]
    for group, values in first.items():
        if not isinstance(values, dict):
            continue
        for k, v in values.items():
            if all(s.get(group, {}).get(k, object()) == v for s in settings_list[1:]):
                out.setdefault(group, {})[k] = v
    return out


def common_flat(dicts):
    if not dicts:
        return {}
    return {k: v for k, v in dicts[0].items() if all(d.get(k, object()) == v for d in dicts[1:])}


def common_block(blocks):
    """What every G-code block of a model shares: the plain fields, and each key of the dictionary fields."""
    out = {}
    first = blocks[0]
    for k, v in first.items():
        if isinstance(v, dict):
            same = {kk: vv for kk, vv in v.items()
                    if all(isinstance(b.get(k), dict) and b[k].get(kk, object()) == vv for b in blocks[1:])}
            if same:
                out[k] = same
        elif all(b.get(k, object()) == v for b in blocks[1:]):
            out[k] = v
    return out


def diff_block(common, block):
    out = {}
    for k, v in block.items():
        if isinstance(v, dict):
            own = {kk: vv for kk, vv in v.items() if common.get(k, {}).get(kk, object()) != vv}
            if own:
                out[k] = own
        elif common.get(k, object()) != v:
            out[k] = v
    return out


def build_models(w, index, printer_entries):
    """One file per printer model, with what its nozzles (or variants) share written once and, per variant, only what
    changes. Models that two sources both have are kept once: from the manufacturer's own bundle when there is one.
    Returns {printer entry path: 'model file#variant id'}."""
    refs = {}
    groups = collections.OrderedDict()  # canonical (vendor, model) -> [(vendor dict, model dict)]
    for v in index['vendors']:
        words = vendor_words(v['name'], v['id'])
        for m in v['models']:
            if not m['printers']:
                continue
            key = (m['technology'], canonical_vendor(v['id']), canonical_model(m['name'], words))
            groups.setdefault(key, []).append((v, m))
    # Printers without a model of their own get one each.
    in_model = {rel for v in index['vendors'] for m in v['models'] for rel in m['printers']}
    for v in index['vendors']:
        for rel in v['printers']:
            if rel not in in_model:
                e = printer_entries[rel]
                m = {'id': e['profile']['name'], 'name': e['profile']['name'], 'technology': e['technology'],
                     'family': '', 'variants': [], 'default_materials': [], 'assets': {}, 'printers': [rel]}
                v['models'].append(m)
                groups.setdefault((e['technology'], v['id'], rel), []).append((v, m))

    def preference(item):
        v, m = item
        derived = bool(re.match(r'^(Orca|CrealityPrint|ElegooSlicer|Cura|Belt|UVtools)_', v['id']))
        return (derived, -len(m['printers']))

    for key, items in groups.items():
        items.sort(key=preference)
        keep_v, keep_m = items[0]
        entries = [(rel, printer_entries[rel]) for rel in keep_m['printers']]
        variants = []
        seen = set()
        for rel, e in entries:
            vid = (e.get('variant') or '').strip()
            nozzle = e['profile']['settings'].get('machine', {}).get('nozzle_diameter')
            if not vid or vid == 'default':
                vid = str(nozzle) if nozzle is not None and len(entries) > 1 else 'default'
            if vid in seen:
                vid = e['profile']['name']
            seen.add(vid)
            variants.append((vid, nozzle, rel, e))
        # A printer of the same model from another source whose nozzle the kept model does not have becomes one more
        # variant (its profiles fit that nozzle, not the model's default one).
        extra = set()
        for v, m in items[1:]:
            for rel in m['printers']:
                e = printer_entries[rel]
                n = e['profile']['settings'].get('machine', {}).get('nozzle_diameter')
                hf = bool(re.match(r'(?i)hf', e.get('variant') or ''))
                if n is None or any(n2 == n and bool(re.match(r'(?i)hf', vid)) == hf for vid, n2, _, _ in variants):
                    continue
                vid = str(n) if not hf else 'HF' + str(n)
                if vid in seen:
                    vid = e['profile']['name']
                seen.add(vid)
                variants.append((vid, n, rel, e))
                extra.add(rel)
                w.stats['variants added from a second source (nozzle the model lacks)'] += 1
        common = common_settings([e['profile']['settings'] for _, _, _, e in variants])
        blocks = [e.get('gcode') for _, _, _, e in variants]
        common_gcode = common_block([g for g in blocks if g]) if all(blocks) else {}
        original_common = common_flat([e['original'] for _, _, _, e in variants])
        first = variants[0][3]
        path = w.path(os.path.dirname(os.path.dirname(keep_m['printers'][0])), 'models', slug(keep_m['name']) + '.json')
        default_variant = next((vid for vid, n, rel, e in variants if n == 0.4 and not re.match(r'(?i)hf', vid)),
                               variants[0][0])
        doc = {'format': 'tisma-pack-model', 'version': FORMAT_VERSION, 'technology': keep_m['technology'],
               'vendor': keep_v['name'], 'model': {'id': keep_m['id'], 'name': keep_m['name'],
                                                    'family': keep_m.get('family', '')},
               'assets': keep_m.get('assets', {}), 'license': first['license'], 'origin': first['origin'],
               'default_variant': default_variant,
               'common': {'settings': common}, 'variants': []}
        if keep_m.get('from_source_program'):
            doc['from_source_program'] = keep_m['from_source_program']
        if common_gcode:
            doc['common']['gcode'] = common_gcode
        for vid, nozzle, rel, e in variants:
            var = {'id': vid, 'nozzle': nozzle, 'name': e['profile']['name'],
                   'settings': diff_settings(common, e['profile']['settings']),
                   'defaults': e.get('defaults', {}), 'source_defaults': e.get('source_defaults', {})}
            if e.get('gcode'):
                own = diff_block(common_gcode, e['gcode'])
                if own:
                    var['gcode'] = own
            for k in ('not_converted', 'from_source_program'):
                if k in e:
                    var[k] = e[k]
            if rel in extra:
                # From the other source: its own license and origin.
                var['license'], var['origin'] = e['license'], e['origin']
            var['original'] = {k: v for k, v in e['original'].items() if original_common.get(k, object()) != v}
            doc['variants'].append(var)
            refs[rel] = path + '#' + vid
        doc['original_common'] = original_common
        merged = []
        for v, m in items[1:]:
            # The same printer from another source: its printers point at the variant with the same nozzle.
            for rel in m['printers']:
                if rel in extra:
                    continue
                e = printer_entries[rel]
                n = e['profile']['settings'].get('machine', {}).get('nozzle_diameter')
                hf = bool(re.match(r'(?i)hf', e.get('variant') or ''))
                match = next((vid for vid, n2, r2, e2 in variants if n2 == n and
                              bool(re.match(r'(?i)hf', vid)) == hf), default_variant)
                refs[rel] = path + '#' + match
            merged.append({'bundle': v['id'], 'model': m['name'], 'license': printer_entries[m['printers'][0]]['license'],
                           'origin': printer_entries[m['printers'][0]]['origin']})
            m['merged_into'] = path
            w.stats['models merged from a second source'] += 1
        if merged:
            doc['also_in'] = merged
        w.write(path, doc)
        keep_m['file'] = path
        keep_m['variants'] = [{'id': vid, 'nozzle': n} for vid, n, rel, e in variants]
        keep_m['default_variant'] = default_variant
        w.stats['models'] += 1
        w.stats['model variants'] += len(variants)
    for v in index['vendors']:
        for m in v['models']:
            m.pop('printers', None)
        v['models'] = [m for m in v['models'] if 'file' in m]
        own = 'vendors/%s/' % slug(v['id'])
        # Its variants, also those a printer of another source added to one of its models.
        v['printers'] = sorted({ref for ref in refs.values() if ref.startswith(own)})
    return refs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('profiles')
    ap.add_argument('out')
    ap.add_argument('--source-commit', default='')
    ap.add_argument('--uvtools', help='a checkout of UVtools, for its resin printer profiles')
    ap.add_argument('--uvtools-commit', default='')
    ap.add_argument('--upstream', action='append', metavar='REPOSITORY=DIR',
                    help='a checkout of a program that Tisma Slicer converted bundles from, at the commit the bundles '
                         'name (e.g. https://github.com/SoftFever/OrcaSlicer=orca), for each printer\'s own G-code')
    ap.add_argument('--source-config', action='append', metavar='DIALECT=PrintConfig.cpp',
                    help="a source program's PrintConfig.cpp, for the defaults of the options its G-code uses")
    ap.add_argument('--filament-gcode-from-bundle', dest='filament_gcode_from_source', action='store_false',
                    help="the OrcaSlicer family's filament G-code from Tisma Slicer's bundle, as before, instead of "
                         "the source program")
    ap.add_argument('--prusa-config', help="PrusaSlicer's PrintConfig.cpp (Tisma Slicer's, at the bundles' commit), "
                                           "for the types of the values in the G-code blocks")
    args = ap.parse_args()
    if args.prusa_config:
        OPTION_TYPES.update(translation.option_types(args.prusa_config))
    program_defaults = {}
    for spec in args.source_config or []:
        dialect, _, path = spec.partition('=')
        program_defaults[dialect] = upstream.program_defaults(path)
    sources = Sources(args.upstream)
    keys_seen = collections.defaultdict(set)  # kind -> source keys of the bundles (PrusaSlicer names)
    renames = translation.Renames()  # the other dialects' names, from the same presets

    bundles = [Bundle(os.path.join(args.profiles, f)) for f in sorted(os.listdir(args.profiles))
               if f.endswith('.ini')]
    if args.uvtools:
        bundles += uvtools_bundles(args.uvtools)
    everything = {}
    for b in bundles:
        for key, values in b.sections.items():
            everything.setdefault(key, values)

    # The variables that the filaments' own G-code uses (the bundles' text), for the printers' values.
    filament_names = set()
    for (kind, _), values in everything.items():
        if kind == 'filament':
            for key in FILAMENT_KEYS:
                if values.get(key):
                    filament_names.update(n for n, local in gcode_variables.variables(gcode_text(values[key]))
                                          if not local)

    w = Writer(args.out)
    index = {'format': 'tisma-profile-pack', 'version': FORMAT_VERSION,
             'generated': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
             'source': {'program': 'Tisma Slicer', 'repository':
                        'https://github.com/adriangrochi-code/Nuevo-slicer-basado-en-prusa-',
                        'commit': args.source_commit, 'directory': 'resources/profiles'},
             'license': 'AGPL-3.0-or-later', 'vendors': []}
    if args.uvtools:
        index['other_sources'] = [{'program': 'UVtools', 'repository': 'https://github.com/sn4k3/UVtools',
                                   'commit': args.uvtools_commit, 'directory': 'PrusaSlicer'}]
    all_printers = []  # (config, entry id) of every FDM printer, for the generic (template) bundles
    all_sla = []  # the same for resin printers: resin materials name their printers by keywords of any bundle
    deferred = []
    printer_ids = {}  # entry path -> number, its place in index['printers']
    compat_sets = {}  # tuple of printer numbers -> set number
    printer_entries = {}  # written last, with their defaults resolved to pack entries
    printer_names = {}  # (bundle, name) -> entry path
    model_index = {}  # (canonical vendor, canonical model) -> [(entry path, nozzle, high flow)], FFF
    by_name = {}  # (kind, bundle or None, name) -> (entry path, compatible set number)

    for b in bundles:
        lic, origin = license_of(b.id)
        vendor_name = b.vendor.get('full_name') or b.vendor.get('name') or b.id
        vdir = os.path.join('vendors', slug(b.id))
        vendor = {'id': b.id, 'name': vendor_name, 'license': lic, 'origin': origin,
                  'config_version': b.vendor.get('config_version', ''), 'models': [], 'printers': [],
                  'filaments': [], 'prints': [], 'resins': [], 'resin_prints': []}
        printers = []
        for (kind, name), values in b.sections.items():
            if kind != 'printer' or name.startswith('*'):
                continue
            try:
                c = b.flat(kind, name, everything)
            except KeyError as e:
                w.stats['broken'] += 1
                continue
            sla = c.get('printer_technology', 'FFF').upper() == 'SLA'
            block = None if sla else printer_gcode(b, name, c, everything, sources, w.stats, filament_names)
            if sla:
                settings, used = map_resin_printer(c)
            else:
                settings, used = map_printer(c, engine_texts(block, c))
            match = c
            filled = []
            source = (block or {}).get('values', {})
            given = source.get('nozzle_diameter')
            variant = num(c.get('printer_variant'))
            if not sla and 'nozzle_diameter' not in c and given:
                # The bundle lost the nozzle; its source program gives it.
                nozzle = num(given[0] if isinstance(given, list) else given)
                put(settings, 'machine', 'nozzle_diameter', nozzle)
                match = dict(c, nozzle_diameter=str(clean_num(nozzle)))
                filled.append('machine.nozzle_diameter')
                w.stats['printer nozzle from the source program'] += 1
            elif not sla and 'nozzle_diameter' not in c and variant and 0.1 <= variant <= 3:
                # No nozzle, but the bundle's variant of the printer is its nozzle ("0.4").
                put(settings, 'machine', 'nozzle_diameter', variant)
                match = dict(c, nozzle_diameter=str(clean_num(variant)))
                filled.append('machine.nozzle_diameter')
                w.stats['printer nozzle from its variant'] += 1
            height = num(source.get('printable_height'))
            if not sla and 'max_print_height' not in c and height:
                # The bundle lost the height; its source program gives it.
                put(settings, 'machine', 'max_height', height)
                filled.append('machine.max_height')
                w.stats['printer height from the source program'] += 1
            if not sla and block and block.get('origin') == 'source_program' and block['dialect'] != 'cura':
                # Other machine values the bundle lost (the per-axis limits of every OrcaSlicer-family printer, and
                # most of the values of a few): translated from the source program's preset, as the bundle would
                # have them.
                lost = lost_values('printer', c, source)
                if lost:
                    full, _ = map_printer(dict(c, **lost), engine_texts(block, dict(c, **lost)))
                    full.pop('_notes', None)
                    filled += fill_lost(settings, full)
                    if any(p not in ('machine.nozzle_diameter', 'machine.max_height') for p in filled):
                        w.stats['printer values from the source program'] += 1
            notes = settings.pop('_notes', {})
            rel = w.path(vdir, 'printers', slug(name) + '.json')
            entry = {'format': 'tisma-pack-entry', 'version': FORMAT_VERSION,
                     'technology': 'sla' if sla else 'fff', 'vendor': vendor_name,
                     'model': c.get('pack_model', c.get('printer_model', '')), 'variant': c.get('printer_variant', ''),
                     'profile': {'format': 'tisma-profile', 'version': 1, 'kind': 'printer', 'name': name,
                                 'settings': settings},
                     'defaults': {'filament': split_list(c.get('default_filament_profile', ''))
                                  if c.get('default_filament_profile') else [],
                                  # Without the quotes some bundles write: "0.20mm NORMAL @Papapiu".
                                  'print': translation.typed(c.get('default_print_profile', '') or
                                                             c.get('default_sla_print_profile', ''), 'coString'),
                                  'resin': translation.typed(c.get('default_sla_material_profile', ''),
                                                             'coString')},
                     'license': lic, 'origin': origin, 'original': c}
            if filled:
                entry['from_source_program'] = filled
            if block:
                entry['gcode'] = block
            if notes:
                entry['not_converted'] = notes
                for k, why in notes.items():
                    w.stats['%s not converted (%s)' % (k, why.split(':')[0])] += 1
            keys_seen['printer_sla' if sla else 'printer'].update(c)
            for k in c:
                if k not in used:
                    w.unmapped['printer_sla' if sla else 'printer'][k] += 1
            printer_entries[rel] = entry
            vendor['printers'].append(rel)
            printer_ids[rel] = len(printer_ids)
            printer_names[(b.id, name)] = rel
            if not sla:
                mid = c.get('pack_model', c.get('printer_model', ''))
                words = vendor_words(vendor_name, b.id)
                model_index.setdefault((canonical_vendor(b.id), canonical_model(
                    b.models.get(mid, {}).get('name', mid) or name, words)), []).append(
                    (rel, num(match.get('nozzle_diameter')), is_hf(name)))
            if block and block.get('origin') == 'source_program' and block['dialect'] != 'cura':
                sources.names[(block['source']['repository'], block['source']['preset'])] = rel
                sources.matched.add(b.path)
                if block.get('values'):
                    renames.add(block['dialect'], 'printer', block['values'], c)
            elif block and block.get('origin') == 'source_program' and block['dialect'] == 'cura':
                defs = sources.of(b, w.stats)[3]
                values, _, _ = defs.resolve(block['source']['preset'])
                renames.add('cura', 'printer', {k: dv for k, (dv, ex) in values.items()
                                                if dv is not None and ex is None}, c)
            elif block and block.get('origin') == 'converted_bundle':
                sources.unmatched.add(b.path)
            printers.append((match, rel, sla))
            (all_sla if sla else all_printers).append((match, rel))
            w.stats['sla printers' if sla else 'printers'] += 1

        base = sources.bases.get(b.path) if sources.of(b, w.stats) else None
        for mid, m in b.models.items():
            model = {'id': mid, 'name': m.get('name', mid), 'technology': m.get('technology', 'FFF').lower(),
                     'family': m.get('family', ''), 'variants': [x.strip() for x in m.get('variants', '').split(';')
                                                               if x.strip()],
                     'default_materials': [x.strip() for x in m.get('default_materials', '').split(';')
                                           if x.strip()]}
            assets = {}
            for key in ('bed_model', 'bed_texture', 'thumbnail'):
                f = m.get(key) or (mid + '_thumbnail.png' if key == 'thumbnail' else '')
                src = os.path.join(args.profiles, b.id, f) if f else ''
                if f and os.path.isfile(src):
                    rel = os.path.join(vdir, 'assets', f)
                    os.makedirs(os.path.dirname(os.path.join(args.out, rel)), exist_ok=True)
                    shutil.copyfile(src, os.path.join(args.out, rel))
                    assets[key] = rel
            filled = model_from_source(model, assets, base, mid, args.out, vdir) if base else []
            if filled:
                model['from_source_program'] = filled
                w.stats['models with values from the source program'] += 1
            model['assets'] = assets
            model['printers'] = [rel for c, rel, sla in printers if c.get('pack_model', c.get('printer_model')) == mid]
            vendor['models'].append(model)

        deferred.append((b, vendor, printers, vdir, lic, origin))
        index['vendors'].append(vendor)

    by_kind = collections.defaultdict(list)  # kind -> [(bundle, entry path, compatible set number)]
    material_of = {}  # filament entry path -> its material type (PLA, PETG…)

    def compat_id(compatible):
        if compatible is None:
            return None
        key = tuple(sorted(printer_ids[r] for r in compatible))
        return compat_sets.setdefault(key, len(compat_sets))

    # Filaments, prints and resins, once every printer is known (the template bundles fit printers of all vendors).
    # The variables that the printers' own G-code uses, by dialect: the filament values the source program has for
    # them go with each filament (source_values).
    template_variables = collections.defaultdict(set)
    template_variables_filaments = collections.defaultdict(set)  # dialect -> variables of the filaments' own G-code
    for entry in printer_entries.values():
        g = entry.get('gcode') or {}
        for t in (g.get('templates') or {}).values():
            for text in (t if isinstance(t, list) else [t]):
                if text:
                    template_variables[g.get('dialect')].update(n for n, local in gcode_variables.variables(text)
                                                                if not local)

    for b, vendor, printers, vdir, lic, origin in deferred:
        generic = b.id in ('Templates',) or not printers
        targets = [(c, rel) for c, rel in all_printers] if generic else [(c, rel) for c, rel, sla in printers]
        sla_targets = all_sla
        for (kind, name), values in b.sections.items():
            if name.startswith('*') or kind not in ('filament', 'print', 'sla_material', 'sla_print'):
                continue
            try:
                c = b.flat(kind, name, everything)
            except KeyError:
                w.stats['broken'] += 1
                continue
            cond = compile_condition(c.get('compatible_printers_condition', ''))
            listed = [x for x in split_list(c.get('compatible_printers', '')) if x] \
                if c.get('compatible_printers', '').strip() else []
            pool = sla_targets if kind.startswith('sla') else [t for t in targets]
            src = sources.of(b, w.stats) if kind in ('filament', 'print') else None
            straight = b.path in sources.matched or (not printers and b.path not in sources.unmatched)
            vendor_presets = sources.presets(b, 'process' if kind == 'print' else 'filament') \
                if src and straight else None
            from_source = upstream.orca_compatible(vendor_presets, name) if vendor_presets else None
            if from_source:
                source_values = vendor_presets.resolve(from_source[0])[0]
                renames.add(src[0], kind, source_values, c)
            else:
                source_values = None
            if from_source and from_source[1]:
                # The source program's list, inherited from the parents like any other value (Tisma Slicer's bundle
                # writes it empty in a preset that only inherits it, or with printers the source does not name).
                # The source program lets a profile fit printers of other vendors.
                wanted = set()
                for x in from_source[1]:
                    hit = sources.names.get((src[1], x)) or printer_names.get((b.id, x))
                    if hit is None:
                        # Tisma Slicer keeps a model that two sources have once, from the maker's own bundle: the
                        # printer of the same model and nozzle there (the rule build_models merges models by).
                        hit = same_model(src[3], x, vendor['name'], b.id, model_index)
                        if hit:
                            w.stats['%s compatible printer matched by model and nozzle' % kind] += 1
                    if hit:
                        wanted.update(hit if isinstance(hit, list) else [hit])
                compatible = [rel for pc, rel in all_printers if rel in wanted]
                pool = all_printers
                w.stats['%s compatible printers from the source program' % kind] += 1
            elif listed:
                wanted = {printer_names.get((b.id, x)) for x in listed}
                compatible = [rel for pc, rel in pool if rel in wanted]
            elif cond is None:
                compatible = None
                w.stats['conditions not understood'] += 1
            else:
                compatible = [rel for pc, rel in pool if cond(pc)]
            if compatible is not None and not compatible:
                # Fits no printer, in the pack or in its source program (a condition no printer meets, or a list of
                # printers that are not there): left out, and listed in stats.json.
                w.stats['%s left out: fits no printer' % kind] += 1
                w.left_out.append({'kind': kind, 'bundle': b.id, 'name': name,
                                   'condition': c.get('compatible_printers_condition', ''),
                                   'printers': c.get('compatible_printers', '')})
                if from_source and from_source[1]:
                    # The printers the source program names, none of them in the pack.
                    w.left_out[-1]['source_printers'] = from_source[1]
                continue
            nozzle, nozzle_from = None, None
            if kind == 'print':
                nozzle, nozzle_from = print_nozzle(name, c, compatible, pool)
                if nozzle_from:
                    w.stats['print nozzle from ' + nozzle_from] += 1
            if kind == 'filament':
                settings, used = map_filament(c)
                pk, folder, group = 'filament', 'filaments', 'filaments'
            elif kind == 'print':
                settings, used = map_print(c, nozzle)
                pk, folder, group = 'print', 'prints', 'prints'
            elif kind == 'sla_material':
                settings, used = map_resin_material(c)
                pk, folder, group = 'resin', 'resins', 'resins'
            else:
                settings, used = map_resin_print(c)
                pk, folder, group = 'resin_print', 'resin_prints', 'resin_prints'
            keys_seen[kind].update(c)
            for k in c:
                if k not in used:
                    w.unmapped[kind][k] += 1
            rel = w.path(vdir, folder, slug(name) + '.json')
            entry = {'format': 'tisma-pack-entry', 'version': FORMAT_VERSION,
                     'technology': 'sla' if kind.startswith('sla') else 'fff', 'vendor': vendor['name'],
                     'profile': {'format': 'tisma-profile', 'version': 1, 'kind': pk, 'name': name,
                                 'settings': settings},
                     'compatible': compat_id(compatible), 'generic': generic,
                     'license': lic, 'origin': origin, 'original': c}
            if kind == 'filament':
                entry['material'] = {'type': first_text(c.get('filament_type')),
                                     'vendor': first_text(c.get('filament_vendor')),
                                     'density': num(c.get('filament_density')),
                                     'cost_per_kg': num(c.get('filament_cost')),
                                     'colour': first_text(c.get('filament_colour')),
                                     'soluble': flag(c.get('filament_soluble', '0'))}
            if kind == 'print' and nozzle:
                entry['nozzle'] = nozzle
            lost = lost_values(kind, c, source_values) if source_values and kind in ('filament', 'print') else None
            if lost:
                # Values the bundle lost and the source program's preset gives: translated as the bundle would have
                # them.
                full, _ = map_filament(dict(c, **lost)) if kind == 'filament' else \
                    map_print(dict(c, **lost), nozzle)
                filled = fill_lost(settings, full)
                if filled:
                    entry['from_source_program'] = filled
                    w.stats['%s values from the source program' % kind] += 1
                if kind == 'filament':
                    for field, key in (('type', 'filament_type'), ('vendor', 'filament_vendor'),
                                       ('colour', 'filament_colour')):
                        if key in lost and not entry['material'][field]:
                            entry['material'][field] = first_text(lost[key])
                            entry.setdefault('from_source_program', []).append('material.' + field)
                    for field, key in (('density', 'filament_density'), ('cost_per_kg', 'filament_cost')):
                        if key in lost and entry['material'][field] is None:
                            entry['material'][field] = num(lost[key])
                            entry.setdefault('from_source_program', []).append('material.' + field)
            if kind == 'filament':
                fblock = filament_gcode(b, name, c, everything, sources, w.stats)
                own = source_filament_gcode(src, from_source, source_values) \
                    if source_values and args.filament_gcode_from_source else None
                if own:
                    # The filament's own G-code as the source program has it, in its dialect (Tisma Slicer's
                    # bundle renames only some of its variables).
                    fblock = own
                    entry['gcode'] = own
                    template_variables_filaments[src[0]].update(template_names(own['templates']))
                    w.stats['filament G-code from the source program (%s)' % src[0]] += 1
                elif source_values and args.filament_gcode_from_source and \
                        any(k in source_values for k in ('filament_start_gcode', 'filament_end_gcode')):
                    # The source program has no filament G-code for it (empty): none, not the bundle's text.
                    fblock = None
                    w.stats['filament without G-code in the source program (%s)' % src[0]] += 1
                if not source_values:
                    # A PrusaSlicer-format filament: its own values for the variables of the machines' G-code and of
                    # its own.
                    names = template_variables.get('prusaslicer', set()) | \
                        template_names((fblock or {}).get('templates') or {})
                    given = bundle_values({}, c, names)
                    if given:
                        entry['source_values'] = {'dialect': 'prusaslicer', 'preset': name, 'values': given}
                        w.stats['filaments with source_values (prusaslicer)'] += 1
                wanted = (template_variables.get(src[0], set()) | template_names((own or {}).get('templates') or {})) \
                    if src and source_values else None
                if wanted:
                    given = {k: v for k, v in sorted(source_values.items()) if k in wanted}
                    if given:
                        # The filament's values in the source program for the variables of the machines' G-code
                        # (Tisma Slicer's bundle does not keep all of them).
                        entry['source_values'] = {'dialect': src[0], 'preset': from_source[0], 'values': given}
                        w.stats['filaments with source_values (%s)' % src[0]] += 1
                if fblock:
                    entry['gcode'] = fblock
            w.write(rel, entry)
            vendor[group].append(rel)
            w.stats[kind] += 1
            by_name.setdefault((kind, b.id, name), (rel, entry['compatible']))
            by_name.setdefault((kind, None, name), (rel, entry['compatible']))
            by_kind[kind].append((b.id, rel, entry['compatible']))
            if kind == 'filament':
                material_of[rel] = entry['material']['type']

    # Defaults of each printer, as pack entries: the ones its source names, or else the first compatible one of its
    # own bundle, or of any bundle.
    members = {n: set(k) for k, n in compat_sets.items()}
    bundle_of = {rel: v['id'] for v in index['vendors'] for rel in v['printers']}

    def fits(compat, pid):
        return compat is None or pid in members[compat]

    def pick(kind, names, rel):
        pid, bid = printer_ids[rel], bundle_of[rel]
        out, unfit, unfit_hits = [], 0, []
        for n in names:
            n = n[:-len(' @Template')] if n.endswith(' @Template') else n
            hit = by_name.get((kind, bid, n)) or by_name.get((kind, None, n))
            if hit and hit[0] not in out:
                # Only one that fits the printer: the source programs take the first compatible profile when the
                # one a printer names does not fit it.
                if fits(hit[1], pid):
                    out.append(hit[0])
                else:
                    unfit += 1
                    unfit_hits.append(hit[0])
        if unfit:
            w.stats['default %s named by the source but not compatible' % kind] += 1
        if out:
            return out, 'source'
        # The first compatible one of the printer's own bundle, then of a bundle of the same maker, then of any; for
        # a filament, of the same material as the one the source names (PLA for a PLA) before any other.
        brand = canonical_vendor(bid)
        wanted = {material_of.get(r) for r in unfit_hits} - {None, ''} if kind == 'filament' else set()
        for rank in (0, 1, 2):
            for same in ((True, False) if wanted else (False,)):
                for b2, r2, compat in by_kind[kind]:
                    level = 0 if b2 == bid else 1 if canonical_vendor(b2) == brand else 2
                    if level == rank and compat is not None and fits(compat, pid) and \
                            (not same or material_of.get(r2) in wanted):
                        return [r2], 'compatible'
        if unfit_hits:
            # Nothing in the pack fits: the one the source names, as the source program would still have it.
            return unfit_hits, 'source, nothing fits'
        return [], 'none'

    for rel, entry in printer_entries.items():
        d = entry.pop('defaults')
        if entry['technology'] == 'sla':
            resins, how_r = pick('sla_material', [d['resin']] if d['resin'] else [], rel)
            prints, how_p = pick('sla_print', [d['print']] if d['print'] else [], rel)
            entry['defaults'] = {'resin': resins[:1], 'resin_print': prints[:1]}
            w.stats['default resin: ' + how_r] += 1
        else:
            fils, how_f = pick('filament', d['filament'], rel)
            prints, how_p = pick('print', [d['print']] if d['print'] else [], rel)
            entry['defaults'] = {'filament': fils, 'print': prints[:1]}
            w.stats['default filament: ' + how_f] += 1
        w.stats['default print: ' + how_p] += 1
        entry['source_defaults'] = d

    # The program's defaults (its PrintConfig.cpp) for the variables of its G-code that a preset does not set, as the
    # program fills them: in the printer's values, named in program_defaults.
    if program_defaults:
        machine_keys = collections.defaultdict(set)  # dialect -> keys that some machine preset of it sets
        for entry in printer_entries.values():
            g = entry.get('gcode') or {}
            if g.get('origin') == 'source_program':
                machine_keys[g['dialect']].update(g.get('values') or {})
        for rel, entry in printer_entries.items():
            g = entry.get('gcode') or {}
            d = g.get('dialect')
            if g.get('origin') != 'source_program' or d not in program_defaults:
                continue
            names = template_names(g.get('templates') or {}) | template_variables_filaments.get(d, set())
            values = g.setdefault('values', {})
            # Only machine options: a filament's value comes with the filament.
            added = sorted(n for n in names if n not in values and n in program_defaults[d] and n in machine_keys[d])
            for n in added:
                values[n] = program_defaults[d][n]
            if added:
                g['program_defaults'] = added
                w.stats['printers with program defaults in values (%s)' % d] += 1

    refs = build_models(w, index, printer_entries)

    # The compatible sets name printers by their place in index['printers']: move them to the model variants
    # (several source printers can end on the same variant when a model came from two sources).
    old = sorted(printer_ids, key=printer_ids.get)
    unique = []
    place = {}
    for rel in old:
        ref = refs[rel]
        if ref not in place:
            place[ref] = len(unique)
            unique.append(ref)
    remapped = {}
    for key, n in compat_sets.items():
        remapped[n] = sorted({place[refs[old[i]]] for i in key})
    index['printers'] = unique
    compat_out = [remapped[n] for n in range(len(compat_sets))]

    for v in index['vendors']:
        v['counts'] = {k: len(v[k]) for k in ('models', 'printers', 'filaments', 'prints', 'resins', 'resin_prints')}
    # The translation of each dialect's keys to the engine's (docs/FORMAT.md, «Traducción de claves»).
    index['translation'] = {}
    tables = {'prusaslicer': translation.table_json('prusaslicer', keys_seen)}
    for dialect in ('orcaslicer', 'crealityprint', 'elegooslicer', 'cura'):
        kinds = {k for d, k in renames.samples if d == dialect}
        if not kinds:
            continue
        seen = {k: set().union(*[set(x for x, v in sv.items() if not isinstance(v, dict))
                                  for sv, _ in renames.samples[(dialect, k)]]) for k in kinds}
        found = {k: renames.renames(dialect, k) for k in kinds}
        tables[dialect] = translation.table_json(dialect, seen, found, source={
            'how': 'the same presets in the source program and in Tisma Slicer\'s bundle: a key whose value the bundle '
                   'has under a PrusaSlicer name in nearly every preset', 'presets': {
                       translation.KIND_NAMES[k]: len(renames.samples[(dialect, k)]) for k in kinds}})
    for dialect, table in tables.items():
        rel = os.path.join('translation', dialect + '.json')
        w.write(rel, table)
        index['translation'][dialect] = rel
        for kind, rows in table['kinds'].items():
            for row in rows.values():
                w.stats['translation %s %s: %s' % (dialect, kind, row['group'])] += 1
    w.write('compatible.json', {'format': 'tisma-pack-compatible', 'version': FORMAT_VERSION, 'sets': compat_out})
    index['counts'] = dict(w.stats)
    w.write('index.json', index)
    w.write('stats.json', {'counts': dict(w.stats),
                           'left_out': w.left_out,
                           'unmapped_keys': {k: dict(v.most_common()) for k, v in w.unmapped.items()}})
    print(json.dumps(dict(w.stats)))


if __name__ == '__main__':
    main()
