"""Reads the original printer profiles of the programs that Tisma Slicer converted its bundles from (OrcaSlicer,
Creality Print, Elegoo Slicer: JSON presets; UltiMaker Cura: definition files), to take each printer's own custom
G-code as written there, macros included.

Tisma Slicer's bundles name their source in their first lines ("converted from <program> (<repository>, <folder>)" and
"from commit <sha>"). Its converter renamed the source's variables to PrusaSlicer's and, for OrcaSlicer, did not
follow "include" (the per-model G-code templates of the Bambu Lab printers), so the pack takes the G-code from the
source itself, with the source's own variable names (its "dialect"; docs/FORMAT.md, "G-code de la máquina").
"""

import glob
import json
import os
import re

HEADER = re.compile(r'converted from ([^(]+?) \((https://github\.com/[^,\s]+), ([^)]+)\)')
COMMIT = re.compile(r'from commit ([0-9a-f]{40})')

DIALECTS = {'https://github.com/SoftFever/OrcaSlicer': 'orcaslicer',
            'https://github.com/CrealityOfficial/CrealityPrint': 'crealityprint',
            'https://github.com/ELEGOO-3D/ElegooSlicer': 'elegooslicer',
            'https://github.com/Ultimaker/Cura': 'cura'}

# The custom G-code keys of each dialect and the pack's name for each (docs/FORMAT.md). Keys of a dialect that end in
# "_gcode" and are not here are kept with their own name.
PRUSA_KEYS = {'start_gcode': 'start', 'end_gcode': 'end', 'before_layer_gcode': 'before_layer_change',
              'layer_gcode': 'layer_change', 'toolchange_gcode': 'toolchange', 'between_objects_gcode':
              'between_objects', 'color_change_gcode': 'color_change', 'pause_print_gcode': 'pause',
              'template_custom_gcode': 'custom', 'start_filament_gcode': 'filament_start',
              'end_filament_gcode': 'filament_end'}
ORCA_KEYS = {'machine_start_gcode': 'start', 'machine_end_gcode': 'end', 'before_layer_change_gcode':
             'before_layer_change', 'layer_change_gcode': 'layer_change', 'change_filament_gcode': 'toolchange',
             'printing_by_object_gcode': 'between_objects', 'machine_pause_gcode': 'pause',
             'template_custom_gcode': 'custom', 'time_lapse_gcode': 'timelapse', 'change_extrusion_role_gcode':
             'extrusion_role_change', 'filament_start_gcode': 'filament_start', 'filament_end_gcode': 'filament_end'}
CURA_KEYS = {'machine_start_gcode': 'start', 'machine_end_gcode': 'end'}
CURA_EXTRUDER_KEYS = {'machine_extruder_start_code': 'extruder_start', 'machine_extruder_end_code': 'extruder_end'}
NON_GCODE = {'machine_start_gcode', 'machine_end_gcode'}  # Cura keys that are G-code without the suffix rule


def bundle_source(path):
    """(program, repository, folder, commit) of a Tisma Slicer bundle, from its first lines, or None."""
    with open(path, encoding='utf-8') as f:
        head = ' '.join(line.lstrip('#').strip() for line in f.read(1200).splitlines() if line.startswith('#'))
    m, c = HEADER.search(head), COMMIT.search(head)
    if not m:
        return None
    return m.group(1).strip(), m.group(2).rstrip('/'), m.group(3).strip(), c.group(1) if c else ''


class OrcaVendor:
    """The presets of one kind ("machine", "process" or "filament") of an OrcaSlicer-style vendor folder
    (resources/profiles/<vendor>), by name. Parents not in the folder are looked for in the fallback folders (the
    shared OrcaFilamentLibrary for filaments)."""

    def __init__(self, folder, fallback_folders=(), kind='machine'):
        self.folder = folder
        self.presets = {}
        for root in (folder,) + tuple(fallback_folders):
            for f in sorted(glob.glob(os.path.join(root, kind, '**', '*.json'), recursive=True)):
                try:
                    d = json.load(open(f, encoding='utf-8'))
                except (ValueError, UnicodeDecodeError):
                    continue
                if isinstance(d, dict) and d.get('name'):
                    self.presets.setdefault(d['name'], (os.path.relpath(f, os.path.dirname(folder)), d))

    def find(self, name):
        """The preset of a Tisma Slicer name. Tisma Slicer adds ' @Orca <vendor>' when a name clashes."""
        if name in self.presets:
            return name
        short = re.sub(r' @(Orca|CrealityPrint|ElegooSlicer)\b.*$', '', name)
        return short if short in self.presets else None

    def resolve(self, name, depth=0):
        """(values, {key: file that set it}) with "inherits" and "include" followed: the parent first, then the
        included templates in order, then the preset's own values."""
        path, d = self.presets[name]
        values, where = {}, {}
        parent = d.get('inherits')
        if parent and depth < 30:
            if parent not in self.presets:
                raise KeyError('parent "%s" of "%s" not found' % (parent, name))
            values, where = self.resolve(parent, depth + 1)
        includes = d.get('include') or []
        if isinstance(includes, str):
            includes = [includes]
        for inc in includes:
            if inc not in self.presets:
                raise KeyError('include "%s" of "%s" not found' % (inc, name))
            ipath, idoc = self.presets[inc]
            for k, v in idoc.items():
                if k not in ('name', 'type', 'instantiation', 'inherits', 'from', 'setting_id', 'include'):
                    values[k] = v
                    where[k] = ipath
        for k, v in d.items():
            if k in ('inherits', 'include'):
                continue
            values[k] = v
            where[k] = path
        return values, where


class CuraDefinitions:
    """UltiMaker Cura machine definitions (resources/definitions) and their extruders (resources/extruders)."""

    def __init__(self, resources):
        self.defs = {}
        for kind in ('definitions', 'extruders'):
            for f in glob.glob(os.path.join(resources, kind, '*.def.json')):
                try:
                    d = json.load(open(f, encoding='utf-8'))
                except (ValueError, UnicodeDecodeError):
                    continue
                self.defs[os.path.basename(f)[:-len('.def.json')]] = (os.path.join(kind, os.path.basename(f)), d)

    def resolve(self, def_id, depth=0):
        """({key: (default_value or None, value expression or None)}, {key: file}, metadata) of a definition."""
        path, d = self.defs[def_id]
        values, where, meta = {}, {}, {}
        if d.get('inherits') and depth < 30:
            values, where, meta = self.resolve(d['inherits'], depth + 1)
        meta = dict(meta, **d.get('metadata', {}))
        for k, o in (d.get('overrides') or {}).items():
            if not isinstance(o, dict):
                continue
            dv = o.get('default_value', o.get('default value'))
            ex = o.get('value')
            if dv is None and ex is None:
                continue
            old = values.get(k, (None, None))
            # A value expression wins over a default value (Cura), and an override of either replaces the other.
            values[k] = (dv if dv is not None else (old[0] if ex is None else None), ex)
            where[k] = path
        # fdmprinter.def.json declares the settings in "settings" with their default values.
        for k, dv in _setting_defaults(d.get('settings') or {}):
            if k not in values:
                values[k] = (dv, None)
                where[k] = path
        return values, where, meta


def _setting_defaults(tree):
    for k, s in tree.items():
        if not isinstance(s, dict):
            continue
        if 'default_value' in s and s.get('type') != 'category':
            yield k, s['default_value']
        yield from _setting_defaults(s.get('children') or {})


def orca_compatible(vendor, name):
    """(compatible_printers list, compatible_printers_condition) of a process or filament preset as the source
    program resolves it (inherited from its parents like every other value), or None if the preset is unknown."""
    key = vendor.find(name)
    if key is None:
        return None
    values, _ = vendor.resolve(key)
    printers = values.get('compatible_printers') or []
    if isinstance(printers, str):
        printers = [x.strip().strip('"') for x in printers.split(';') if x.strip()]
    return key, list(printers), str(values.get('compatible_printers_condition') or '')


def _gcode_keys(values, table):
    out = {}
    for k, v in values.items():
        if not isinstance(v, str):
            continue
        if k in table:
            out[table[k]] = (k, v)
        elif k.endswith('_gcode') and k not in NON_GCODE:
            out[k] = (k, v)
    return out


def orca_machine_gcode(vendor, name):
    """The G-code block (docs/FORMAT.md) of an OrcaSlicer-style printer preset, or None if the preset is unknown."""
    key = vendor.find(name)
    if key is None:
        return None
    values, where = vendor.resolve(key)
    templates, keys, origin = {}, {}, {}
    for neutral, (k, v) in sorted(_gcode_keys(values, ORCA_KEYS).items()):
        templates[neutral] = v
        keys[neutral] = k
        origin[neutral] = where[k]
    rel = values.get('use_relative_e_distances')
    return {'preset': key, 'templates': templates, 'keys': keys, 'from': origin,
            'relative_extrusion': None if rel is None else str(rel).strip() in ('1', 'true'),
            'values': {k: v for k, v in values.items() if not (isinstance(v, str) and k.endswith('_gcode'))
                       and k not in ('name', 'type', 'instantiation', 'from', 'setting_id')}}


def cura_machine_gcode(cura, def_id):
    """The G-code block of a Cura machine definition and its extruders, or None if the definition is unknown.
    Templates that Cura computes with a value expression are left out (listed in "expressions")."""
    if def_id not in cura.defs:
        return None
    values, where, meta = cura.resolve(def_id)
    templates, keys, origin, expressions = {}, {}, {}, {}
    for k, neutral in CURA_KEYS.items():
        if k not in values:
            continue
        dv, ex = values[k]
        if ex is not None:
            expressions[neutral] = ex
        elif isinstance(dv, str):
            templates[neutral] = dv
            keys[neutral] = k
            origin[neutral] = where[k]
    trains = meta.get('machine_extruder_trains') or {}
    for k, neutral in CURA_EXTRUDER_KEYS.items():
        per = []
        for i in sorted(trains, key=lambda x: int(x)):
            eid = trains[i]
            if eid not in cura.defs:
                per.append(None)
                continue
            ev, ew, _ = cura.resolve(eid)
            dv, ex = ev.get(k, (None, None))
            if ex is not None:
                expressions.setdefault(neutral, []).append(ex)
            per.append(dv if ex is None and isinstance(dv, str) else None)
        if any(per):
            templates[neutral] = per
            keys[neutral] = k
            origin[neutral] = [cura.defs[trains[i]][0] if trains[i] in cura.defs else None
                               for i in sorted(trains, key=lambda x: int(x))]
    rel = values.get('relative_extrusion', (False, None))[0]
    out = {'preset': def_id, 'templates': templates, 'keys': keys, 'from': origin,
           'relative_extrusion': bool(rel)}
    if expressions:
        out['expressions'] = expressions
    return out


# The variables of the OrcaSlicer family that Tisma Slicer renames to PrusaSlicer's when it converts a G-code template,
# as its bundles show (the same template in the source program and in the bundle). Only used to convert the start and
# end G-code for the engine's simple variables (profile.settings); the G-code block keeps the source's own names.
ORCA_TO_PRUSA = {'nozzle_temperature_initial_layer': 'first_layer_temperature', 'nozzle_temperature': 'temperature',
                 'bed_temperature_initial_layer_single': 'first_layer_bed_temperature',
                 'bed_temperature_initial_layer': 'first_layer_bed_temperature',
                 'initial_no_support_extruder': 'initial_extruder', 'initial_layer_print_height': 'first_layer_height',
                 'printable_height': 'max_print_height', 'adaptive_bed_mesh_min': 'first_layer_print_min',
                 'adaptive_bed_mesh_max': 'first_layer_print_max', 'retraction_length': 'retract_length',
                 'z_hop': 'retract_lift', 'spiral_mode': 'spiral_vase'}
_SPAN = re.compile(r'\[[^\]\n]*\]|\{[^}\n]*\}')
_WORD = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')


def to_prusa_names(text):
    return _SPAN.sub(lambda m: _WORD.sub(lambda w: ORCA_TO_PRUSA.get(w.group(0), w.group(0)), m.group(0)), text)


# The default values of a program's options (its PrintConfig.cpp), for the variables a G-code uses that a preset does
# not set: the program takes them from there.
_DEFAULT = re.compile(r'set_default_value\(\s*new\s+ConfigOption(\w+?)(?:<[^>]*>)?\s*(\(|\{)(.*?)(\)|\})\s*\)\s*;',
                      re.S)


def _default_value(kind, body):
    body = body.strip()
    items = [x.strip() for x in re.split(r',(?![^{]*\})', body) if x.strip()] if body else []

    def one(x, scalar):
        x = x.strip().rstrip('f').strip()
        if scalar == 'Bool':
            return {'true': True, 'false': False, '1': True, '0': False}.get(x)
        if scalar in ('Int', 'Float', 'Percent'):
            try:
                n = float(x.rstrip('.'))
            except ValueError:
                return None
            return int(n) if scalar == 'Int' or n == int(n) else n
        if scalar == 'String':
            m = re.fullmatch(r'L?\(?"((?:\\.|[^"\\])*)"\)?', x)
            return m.group(1) if m else None
        return None
    base = kind[:-1] if kind.endswith('s') and kind[:-1] in ('Bool', 'Int', 'Float', 'Percent', 'String') else None
    if base:
        values = [one(x, base) for x in items]
        return values if all(v is not None for v in values) else None
    if kind in ('Bool', 'Int', 'Float', 'Percent', 'String'):
        return one(body, kind) if body else ('' if kind == 'String' else None)
    return None


def program_defaults(print_config_cpp):
    """{key: default value} of the options of a PrintConfig.cpp whose default is a plain yes/no, number or text, or a
    list of them."""
    text = open(print_config_cpp, encoding='utf-8', errors='replace').read()
    out = {}
    for m in re.finditer(r'this->add(?:_nullable)?\("(\w+)",\s*co\w+\)', text):
        rest = text[m.end():m.end() + 4000]
        nxt = re.search(r'this->add', rest)
        rest = rest[:nxt.start()] if nxt else rest
        d = _DEFAULT.search(rest)
        if d:
            v = _default_value(d.group(1), d.group(3))
            if v is not None:
                out.setdefault(m.group(1), v)
    return out


# How the programs rewrite an old name when they load a preset (their PrintConfig.cpp, handle_legacy).
LEGACY_RENAMES = {'crealityprint': {'filament_start_gcode': [('initial_layer_height', 'first_layer_height')]}}
