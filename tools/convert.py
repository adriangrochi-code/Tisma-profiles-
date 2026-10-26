#!/usr/bin/env python3
"""Converts the Tisma Slicer vendor bundles (PrusaSlicer INI format, with the profiles it took from PrusaSlicer,
OrcaSlicer, Creality Print, Elegoo Slicer and Cura) and the UVtools resin printer profiles into a Tisma profile pack
(docs/FORMAT.md).

Each profile keeps every value of its source (inheritance resolved) under "original", and the values the engine
understands, under its own keys (the engine's docs/CONFIG.md), under "profile.settings".

Usage: convert.py <profiles dir> <out dir> [--source-commit SHA] [--uvtools DIR --uvtools-commit SHA]
"""

import argparse
import collections
import datetime
import hashlib
import json
import os
import re
import shutil
import sys

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


def lookup(config, ident):
    m = re.match(r'(\w+)\[(\d+)\]$', ident)
    if m:
        items = split_list(config.get(m.group(1), ''))
        i = int(m.group(2))
        return items[i] if i < len(items) else ''
    return config.get(ident, '').strip('"')


def as_value(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return v


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
            py.append('%s(re.search(%r, str(%s)) is not None)' % ('not ' if op == '!~' else '', rx, subject))
        elif m.group('num'):
            py.append(repr(float(m.group('num'))))
        elif m.group('str'):
            py.append(repr(m.group('str')[1:-1]))
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
            return bool(eval(code, {'re': re, 'V': lambda k: as_value(lookup(config, k))}))
        except Exception:
            return False
    return run


# ---------------------------------------------------------------------------------------------------------------------
# Value helpers

def num(v, default=None):
    if v is None:
        return default
    v = str(v).strip().split(',')[0].strip('"')
    try:
        return float(v)
    except ValueError:
        return default


def pct_or_abs(v, base):
    """'50%' of base, or an absolute number; None if unknown."""
    if v is None:
        return None
    v = str(v).strip()
    if v.endswith('%'):
        p = num(v[:-1])
        return None if p is None or base is None else base * p / 100
    return num(v)


def flag(v):
    return str(v).strip() in ('1', 'true', 'True')


def clean_num(x):
    if x is None:
        return None
    x = round(x, 6)
    return int(x) if x == int(x) else x


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


FLAVORS = {'marlin': 'marlin', 'marlin2': 'marlin', 'marlinlegacy': 'marlin', 'klipper': 'klipper',
           'reprap': 'reprap', 'reprapfirmware': 'reprap', 'repetier': 'marlin', 'sprinter': 'marlin',
           'smoothie': 'marlin', 'teacup': 'marlin', 'makerware': None, 'sailfish': None, 'mach3': None,
           'machinekit': None, 'no-extrusion': None}

PATTERNS = {'rectilinear': 'rectilinear', 'monotonic': 'monotonic', 'grid': 'grid', 'gyroid': 'gyroid',
            'triangles': 'triangles', 'stars': 'stars', 'cubic': 'cubic', 'adaptivecubic': 'adaptive_cubic',
            'supportcubic': 'support_cubic', 'lightning': 'lightning', 'alignedrectilinear': 'aligned_rectilinear',
            'zigzag': 'zigzag', 'line': 'line', 'honeycomb': 'honeycomb', 'concentric': 'concentric',
            'hilbertcurve': 'hilbert', 'archimedeanchords': 'archimedean', 'octagramspiral': 'octagram'}

SEAMS = {'aligned': 'aligned', 'nearest': 'nearest', 'random': 'random', 'rear': 'rear'}



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
FILAMENT_VARIABLES = ('temperature', 'first_layer_temperature', 'bed_temperature', 'first_layer_bed_temperature',
                      'chamber_temperature', 'chamber_minimal_temperature', 'idle_temperature')
PLACEHOLDER = re.compile(r'\[(\w+)\]|\{(\w+)(?:\[(\d+)\])?\}')


def fix_point(p):
    """A bed point written '235-0' instead of '235x0' (a typo in one source bundle)."""
    p = p.strip()
    return p.replace('-', 'x', 1) if 'x' not in p and re.match(r'^\d+(\.\d+)?-\d+(\.\d+)?$', p) else p


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
# Mapping to engine keys (docs/CONFIG.md of the engine). Each function returns (settings, used source keys).

def map_printer(c):
    s = {}
    used = set()

    def u(*keys):
        used.update(keys)
    nozzle = num(c.get('nozzle_diameter'))
    put(s, 'machine', 'nozzle_diameter', nozzle); u('nozzle_diameter')
    bed = c.get('bed_shape')
    if bed:
        pts = []
        for p in bed.split(','):
            p = fix_point(p)
            if 'x' in p:
                x, y = p.split('x', 1)
                if num(x) is not None and num(y) is not None:
                    pts.append([clean_num(num(x)), clean_num(num(y))])
        if len(pts) >= 3:
            put(s, 'machine', 'bed', pts); u('bed_shape')
    put(s, 'machine', 'max_height', num(c.get('max_print_height'))); u('max_print_height')
    flavor = FLAVORS.get(c.get('gcode_flavor', '').strip())
    put(s, 'machine', 'flavor', flavor); u('gcode_flavor')
    if 'use_relative_e_distances' in c:
        put(s, 'machine', 'relative_extrusion', flag(c['use_relative_e_distances'])); u('use_relative_e_distances')
    for key in ('start_gcode', 'end_gcode'):
        if c.get(key):
            text, why = engine_gcode(gcode_text(c[key]), c)
            if text is not None:
                put(s, 'machine', key, text); u(key)
            else:
                s.setdefault('_notes', {})[key] = why
    for axis in 'xyze':
        put(s, 'machine', 'max_feed_' + axis, num(c.get('machine_max_feedrate_' + axis)))
        u('machine_max_feedrate_' + axis)
    acc = num(c.get('machine_max_acceleration_extruding'))
    if acc:
        put(s, 'machine', 'acceleration', acc)
        travel = num(c.get('machine_max_acceleration_travel')) or acc
        put(s, 'machine', 'travel_acceleration', travel)
        u('machine_max_acceleration_extruding', 'machine_max_acceleration_travel')
    jerk = num(c.get('machine_max_jerk_x'))
    if jerk:
        put(s, 'machine', 'corner_speed', jerk); u('machine_max_jerk_x')
    put(s, 'retraction', 'length', num(c.get('retract_length'))); u('retract_length')
    put(s, 'retraction', 'speed', num(c.get('retract_speed')) or None); u('retract_speed')
    put(s, 'retraction', 'lift', num(c.get('retract_lift'))); u('retract_lift')
    put(s, 'retraction', 'min_travel', num(c.get('retract_before_travel'))); u('retract_before_travel')
    return s, used


def map_filament(c):
    s = {}
    used = set()

    def u(*keys):
        used.update(keys)
    put(s, 'machine', 'filament_diameter', num(c.get('filament_diameter'))); u('filament_diameter')
    variables = {}
    for key in FILAMENT_VARIABLES:
        if key in c:
            variables[key] = c[key].split(',')[0].strip(); u(key)
    if variables:
        put(s, 'machine', 'variables', variables)
    chamber = num(c.get('chamber_temperature'))
    if chamber:
        put(s, 'extrusion', 'chamber_temperature', chamber)
    if 'cooling' in c and not flag(c['cooling']) and not flag(c.get('fan_always_on', '0')):
        put(s, 'cooling', 'fan_min', 0); put(s, 'cooling', 'fan_max', 0); u('cooling', 'fan_always_on')
    else:
        put(s, 'cooling', 'fan_min', num(c.get('min_fan_speed'))); u('min_fan_speed')
        put(s, 'cooling', 'fan_max', num(c.get('max_fan_speed'))); u('max_fan_speed')
    put(s, 'cooling', 'min_layer_time', num(c.get('slowdown_below_layer_time'))); u('slowdown_below_layer_time')
    ms = num(c.get('min_print_speed'))
    put(s, 'cooling', 'min_speed', ms if ms and ms > 0 else None); u('min_print_speed')
    put(s, 'cooling', 'fan_off_layers', num(c.get('disable_fan_first_layers'))); u('disable_fan_first_layers')
    em = num(c.get('extrusion_multiplier'))
    put(s, 'extrusion', 'flow', em * 100 if em else None); u('extrusion_multiplier')
    put(s, 'extrusion', 'max_flow', num(c.get('filament_max_volumetric_speed'))); u('filament_max_volumetric_speed')
    if 'filament_abrasive' in c:
        put(s, 'extrusion', 'abrasive', flag(c['filament_abrasive'])); u('filament_abrasive')
    return s, used


def map_print(c, nozzle):
    s = {}
    used = set()

    def u(*keys):
        used.update(keys)
    lh = num(c.get('layer_height'))
    put(s, 'layers', 'height', lh); u('layer_height')
    put(s, 'layers', 'first_height', pct_or_abs(c.get('first_layer_height'), lh)); u('first_layer_height')
    put(s, 'slicing', 'gap_closing_radius', num(c.get('slice_closing_radius'))); u('slice_closing_radius')
    put(s, 'slicing', 'xy_offset', num(c.get('xy_size_compensation'))); u('xy_size_compensation')
    put(s, 'slicing', 'first_layer_shrink', num(c.get('elefant_foot_compensation'))); u('elefant_foot_compensation')
    put(s, 'walls', 'count', num(c.get('perimeters'))); u('perimeters')
    width = None
    for key in ('perimeter_extrusion_width', 'extrusion_width'):
        w = pct_or_abs(c.get(key), nozzle)
        if w:
            width = w; u(key)
            break
    if width is None and nozzle:
        width = nozzle * 1.125
    put(s, 'walls', 'width', width)
    put(s, 'walls', 'seam', SEAMS.get(c.get('seam_position', ''))); u('seam_position')
    put(s, 'surfaces', 'top_layers', num(c.get('top_solid_layers'))); u('top_solid_layers')
    put(s, 'surfaces', 'bottom_layers', num(c.get('bottom_solid_layers'))); u('bottom_solid_layers')
    put(s, 'surfaces', 'top_min_thickness', num(c.get('top_solid_min_thickness'))); u('top_solid_min_thickness')
    put(s, 'surfaces', 'bottom_min_thickness', num(c.get('bottom_solid_min_thickness')))
    u('bottom_solid_min_thickness')
    top = PATTERNS.get(c.get('top_fill_pattern', ''))
    if top in ('monotonic', 'rectilinear'):
        put(s, 'surfaces', 'top_pattern', top); u('top_fill_pattern')
    put(s, 'infill', 'density', num(str(c.get('fill_density', '')).rstrip('%'))); u('fill_density')
    put(s, 'infill', 'angle', num(c.get('fill_angle'))); u('fill_angle')
    pattern = PATTERNS.get(c.get('fill_pattern', ''))
    if pattern and pattern != 'monotonic':
        put(s, 'infill', 'pattern', pattern); u('fill_pattern')
    every = num(c.get('infill_every_layers'))
    put(s, 'infill', 'combine_layers', every if every and every >= 1 else None); u('infill_every_layers')
    put(s, 'infill', 'solid_every', num(c.get('solid_infill_every_layers'))); u('solid_infill_every_layers')
    put(s, 'infill', 'solid_below_area', num(c.get('solid_infill_below_area'))); u('solid_infill_below_area')
    walls = num(c.get('perimeter_speed'))
    put(s, 'speed', 'walls', walls); u('perimeter_speed')
    outer = c.get('external_perimeter_speed')
    if outer:
        put(s, 'speed', 'outer_wall', outer if outer.endswith('%') else num(outer)); u('external_perimeter_speed')
    infill = num(c.get('infill_speed'))
    put(s, 'speed', 'infill', infill); u('infill_speed')
    solid = pct_or_abs(c.get('solid_infill_speed'), infill)
    put(s, 'speed', 'solid_infill', solid); u('solid_infill_speed')
    put(s, 'speed', 'top_solid_infill', pct_or_abs(c.get('top_solid_infill_speed'), solid))
    u('top_solid_infill_speed')
    put(s, 'speed', 'support', num(c.get('support_material_speed'))); u('support_material_speed')
    put(s, 'speed', 'travel', num(c.get('travel_speed'))); u('travel_speed')
    first = c.get('first_layer_speed')
    if first and not first.endswith('%'):
        put(s, 'speed', 'first_layer', num(first)); u('first_layer_speed')
    fastest = max([x for x in (walls, infill, solid, num(c.get('support_material_speed'))) if x] or [0])
    if fastest:
        put(s, 'speed', 'max', fastest)
    put(s, 'adhesion', 'skirt_loops', num(c.get('skirts'))); u('skirts')
    put(s, 'adhesion', 'skirt_distance', num(c.get('skirt_distance'))); u('skirt_distance')
    put(s, 'adhesion', 'skirt_layers', num(c.get('skirt_height'))); u('skirt_height')
    put(s, 'adhesion', 'brim_width', num(c.get('brim_width'))); u('brim_width')
    if 'support_material' in c:
        put(s, 'support', 'enabled', flag(c['support_material'])); u('support_material')
    put(s, 'support', 'threshold_angle', num(c.get('support_material_threshold'))); u('support_material_threshold')
    put(s, 'support', 'z_gap', num(c.get('support_material_contact_distance')))
    u('support_material_contact_distance')
    put(s, 'support', 'xy_gap', pct_or_abs(c.get('support_material_xy_spacing'), width))
    u('support_material_xy_spacing')
    put(s, 'support', 'spacing', num(c.get('support_material_spacing'))); u('support_material_spacing')
    put(s, 'support', 'interface_layers', num(c.get('support_material_interface_layers')))
    u('support_material_interface_layers')
    return s, used


RESIN_NOTE_KEYS = {'LIFT_DISTANCE': 'lift_distance', 'LIFT_SPEED': 'lift_speed',
                   'BOTTOM_LIFT_DISTANCE': 'bottom_lift_distance', 'BOTTOM_LIFT_SPEED': 'bottom_lift_speed',
                   'RETRACT_SPEED': 'retract_speed', 'BOTTOM_RETRACT_SPEED': 'bottom_retract_speed',
                   'WAIT_BEFORE_EXPOSURE': 'wait_before_exposure', 'BOTTOM_WAIT_BEFORE_EXPOSURE':
                   'bottom_wait_before_exposure', 'WAIT_AFTER_CURE': 'wait_after_cure',
                   'WAIT_AFTER_LIFT': 'wait_after_lift', 'LIGHT_PWM': 'light_pwm', 'BOTTOM_LIGHT_PWM':
                   'bottom_light_pwm', 'ANTIALIASING': 'antialiasing', 'DENSITY': 'density'}


def map_resin_printer(c):
    s = {}
    used = set()
    for key in ('display_pixels_x', 'display_pixels_y', 'display_width', 'display_height'):
        put(s, 'machine', key, num(c.get(key))); used.add(key)
    for key in ('display_mirror_x', 'display_mirror_y'):
        if key in c:
            put(s, 'machine', key, flag(c[key])); used.add(key)
    put(s, 'machine', 'max_height', num(c.get('max_print_height'))); used.add('max_print_height')
    return s, used


def map_resin_material(c):
    s = {}
    used = set()
    put(s, 'resin', 'layer_height', num(c.get('initial_layer_height'))); used.add('initial_layer_height')
    put(s, 'resin', 'exposure', num(c.get('exposure_time'))); used.add('exposure_time')
    put(s, 'resin', 'bottom_exposure', num(c.get('initial_exposure_time'))); used.add('initial_exposure_time')
    corr = [num(x) for x in c.get('material_correction', '').split(',') if x.strip()]
    if len(corr) == 3 and all(x is not None for x in corr):
        for axis, v in zip('xyz', corr):
            put(s, 'resin', 'scale_' + axis, v)
        used.add('material_correction')
    notes = gcode_text(c.get('material_notes', '')) or ''
    for m in re.finditer(r'^\s*([A-Z_]+)\s*=\s*([-\d.]+)', notes, re.M):
        key = RESIN_NOTE_KEYS.get(m.group(1))
        if key and key not in ('bottom_retract_speed', 'bottom_wait_before_exposure'):
            put(s, 'resin', key, num(m.group(2)))
    return s, used


def map_resin_print(c):
    s = {}
    used = set()
    put(s, 'resin', 'layer_height', num(c.get('layer_height'))); used.add('layer_height')
    put(s, 'resin', 'bottom_layers', num(c.get('faded_layers'))); used.add('faded_layers')
    return s, used


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


def build_models(w, index, printer_entries):
    """One file per printer model, with what its nozzles (or variants) share written once and, per variant, only what
    changes. Models that two sources both have are kept once: from the manufacturer's own bundle when there is one.
    Returns {printer entry path: 'model file#variant id'}."""
    refs = {}
    groups = collections.OrderedDict()  # canonical (vendor, model) -> [(vendor dict, model dict)]
    for v in index['vendors']:
        words = {v['name'].lower(), canonical_vendor(v['id'])} | set(v['name'].lower().split())
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
        common = common_settings([e['profile']['settings'] for _, _, _, e in variants])
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
        for vid, nozzle, rel, e in variants:
            var = {'id': vid, 'nozzle': nozzle, 'name': e['profile']['name'],
                   'settings': diff_settings(common, e['profile']['settings']),
                   'defaults': e.get('defaults', {}), 'source_defaults': e.get('source_defaults', {})}
            for k in ('not_converted',):
                if k in e:
                    var[k] = e[k]
            var['original'] = {k: v for k, v in e['original'].items() if original_common.get(k, object()) != v}
            doc['variants'].append(var)
            refs[rel] = path + '#' + vid
        doc['original_common'] = original_common
        merged = []
        for v, m in items[1:]:
            # The same printer from another source: its printers point at the variant with the same nozzle.
            for rel in m['printers']:
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
        v['printers'] = sorted({refs[r] for r in v['printers'] if refs[r].startswith('vendors/%s/' % slug(v['id']))})
    return refs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('profiles')
    ap.add_argument('out')
    ap.add_argument('--source-commit', default='')
    ap.add_argument('--uvtools', help='a checkout of UVtools, for its resin printer profiles')
    ap.add_argument('--uvtools-commit', default='')
    args = ap.parse_args()

    bundles = [Bundle(os.path.join(args.profiles, f)) for f in sorted(os.listdir(args.profiles))
               if f.endswith('.ini')]
    if args.uvtools:
        bundles += uvtools_bundles(args.uvtools)
    everything = {}
    for b in bundles:
        for key, values in b.sections.items():
            everything.setdefault(key, values)

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
            settings, used = (map_resin_printer if sla else map_printer)(c)
            notes = settings.pop('_notes', {})
            rel = w.path(vdir, 'printers', slug(name) + '.json')
            entry = {'format': 'tisma-pack-entry', 'version': FORMAT_VERSION,
                     'technology': 'sla' if sla else 'fff', 'vendor': vendor_name,
                     'model': c.get('pack_model', c.get('printer_model', '')), 'variant': c.get('printer_variant', ''),
                     'profile': {'format': 'tisma-profile', 'version': 1, 'kind': 'printer', 'name': name,
                                 'settings': settings},
                     'defaults': {'filament': split_list(c.get('default_filament_profile', ''))
                                  if c.get('default_filament_profile') else [],
                                  'print': c.get('default_print_profile', '') or c.get('default_sla_print_profile', ''),
                                  'resin': c.get('default_sla_material_profile', '')},
                     'license': lic, 'origin': origin, 'original': c}
            if notes:
                entry['not_converted'] = notes
                for k, why in notes.items():
                    w.stats['%s not converted (%s)' % (k, why.split(':')[0])] += 1
            for k in c:
                if k not in used:
                    w.unmapped['printer_sla' if sla else 'printer'][k] += 1
            printer_entries[rel] = entry
            vendor['printers'].append(rel)
            printer_ids[rel] = len(printer_ids)
            printer_names[(b.id, name)] = rel
            printers.append((c, rel, sla))
            (all_sla if sla else all_printers).append((c, rel))
            w.stats['sla printers' if sla else 'printers'] += 1

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
            model['assets'] = assets
            model['printers'] = [rel for c, rel, sla in printers if c.get('pack_model', c.get('printer_model')) == mid]
            vendor['models'].append(model)

        deferred.append((b, vendor, printers, vdir, lic, origin))
        index['vendors'].append(vendor)

    by_kind = collections.defaultdict(list)  # kind -> [(bundle, entry path, compatible set number)]

    def compat_id(compatible):
        if compatible is None:
            return None
        key = tuple(sorted(printer_ids[r] for r in compatible))
        return compat_sets.setdefault(key, len(compat_sets))

    # Filaments, prints and resins, once every printer is known (the template bundles fit printers of all vendors).
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
            if listed:
                wanted = {printer_names.get((b.id, x)) for x in listed}
                compatible = [rel for pc, rel in pool if rel in wanted]
            elif cond is None:
                compatible = None
                w.stats['conditions not understood'] += 1
            else:
                compatible = [rel for pc, rel in pool if cond(pc)]
            nozzle = None
            if kind == 'print' and compatible:
                nozzles = {num(dict(pc).get('nozzle_diameter')) for pc, rel in pool if rel in compatible}
                nozzle = nozzles.pop() if len(nozzles) == 1 else None
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
                entry['material'] = {'type': c.get('filament_type', ''), 'vendor': c.get('filament_vendor', ''),
                                     'density': num(c.get('filament_density')),
                                     'cost_per_kg': num(c.get('filament_cost')),
                                     'colour': c.get('filament_colour', ''),
                                     'soluble': flag(c.get('filament_soluble', '0'))}
            if kind == 'print' and nozzle:
                entry['nozzle'] = nozzle
            w.write(rel, entry)
            vendor[group].append(rel)
            w.stats[kind] += 1
            by_name.setdefault((kind, b.id, name), (rel, entry['compatible']))
            by_name.setdefault((kind, None, name), (rel, entry['compatible']))
            by_kind[kind].append((b.id, rel, entry['compatible']))

    # Defaults of each printer, as pack entries: the ones its source names, or else the first compatible one of its
    # own bundle, or of any bundle.
    members = {n: set(k) for k, n in compat_sets.items()}
    bundle_of = {rel: v['id'] for v in index['vendors'] for rel in v['printers']}

    def fits(compat, pid):
        return compat is None or pid in members[compat]

    def pick(kind, names, rel):
        pid, bid = printer_ids[rel], bundle_of[rel]
        out = []
        for n in names:
            n = n[:-len(' @Template')] if n.endswith(' @Template') else n
            hit = by_name.get((kind, bid, n)) or by_name.get((kind, None, n))
            if hit and hit[0] not in out:
                out.append(hit[0])
        if out:
            return out, 'source'
        # The first compatible one of the printer's own bundle, then of a bundle of the same maker, then of any.
        brand = canonical_vendor(bid)
        for rank in (0, 1, 2):
            for b2, r2, compat in by_kind[kind]:
                level = 0 if b2 == bid else 1 if canonical_vendor(b2) == brand else 2
                if level == rank and compat is not None and fits(compat, pid):
                    return [r2], 'compatible'
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
    w.write('compatible.json', {'format': 'tisma-pack-compatible', 'version': FORMAT_VERSION, 'sets': compat_out})
    index['counts'] = dict(w.stats)
    w.write('index.json', index)
    w.write('stats.json', {'counts': dict(w.stats),
                           'unmapped_keys': {k: dict(v.most_common()) for k, v in w.unmapped.items()}})
    print(json.dumps(dict(w.stats)))


if __name__ == '__main__':
    main()
