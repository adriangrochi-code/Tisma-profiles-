#!/usr/bin/env python3
"""Tests of the converter's pieces that the pack check cannot see (it does not read the source programs).

Usage: python3 -m unittest discover -s tools -p 'test_*.py'
"""

import os
import json
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import convert  # noqa: E402


class LostValues(unittest.TestCase):
    """Values that Tisma Slicer's bundle lost are taken from the source program's preset, never over the bundle's."""

    def test_sparse_print_takes_the_source_values(self):
        # A print of the bundle with only its layer height (as Orca_Elegoo's "0.16mm Optimal @Elegoo N3Max").
        bundle = {'layer_height': '0.16'}
        source = {'layer_height': '0.12', 'initial_layer_print_height': '0.2', 'travel_speed': '150',
                  'seam_position': 'aligned', 'brim_width': '5'}
        lost = convert.lost_values('print', bundle, source)
        self.assertNotIn('layer_height', lost)  # the bundle has it
        self.assertEqual(lost['first_layer_height'], '0.2')  # OrcaSlicer's name for it
        settings, _ = convert.map_print(bundle, 0.4)
        full, _ = convert.map_print(dict(bundle, **lost), 0.4)
        filled = convert.fill_lost(settings, full)
        self.assertEqual(settings['layers'], {'height': 0.16, 'first_height': 0.2})
        self.assertEqual(settings['speed']['travel'], 150)
        self.assertEqual(settings['walls']['seam'], 'aligned')
        self.assertIn('layers.first_height', filled)
        self.assertNotIn('layers.height', filled)

    def test_value_named_otherwise_in_the_source_program(self):
        # OrcaSlicer's PrintConfig.cpp: seam "back" is spRear, PrusaSlicer's "rear"; "aligned_back" has no
        # PrusaSlicer value.
        with tempfile.TemporaryDirectory() as tmp:
            orca, prusa = os.path.join(tmp, 'orca.cpp'), os.path.join(tmp, 'prusa.cpp')
            open(orca, 'w').write('static t_config_enum_values s_keys_map_SeamPosition {\n { "aligned", spAligned },\n'
                                  ' { "aligned_back", spAlignedBack },\n { "back", spRear }\n};\n'
                                  'def = this->add("seam_position", coEnum);\n'
                                  'def->enum_keys_map = &ConfigOptionEnum<SeamPosition>::get_enum_values();\n')
            open(prusa, 'w').write('static const t_config_enum_values s_keys_map_SeamPosition {\n'
                                   ' { "aligned", spAligned },\n { "rear", spRear }\n};\n'
                                   'def = this->add("seam_position", coEnum);\n def->set_enum<SeamPosition>({});\n')
            names = convert.upstream.value_names(orca, prusa)
        self.assertEqual(names, {'seam_position': {'aligned': 'aligned', 'aligned_back': None, 'back': 'rear'}})
        convert.VALUE_NAMES['orcaslicer'] = names
        try:
            self.assertEqual(convert.lost_values('print', {}, {'seam_position': 'back'}, 'orcaslicer'),
                             {'seam_position': 'rear'})
            self.assertEqual(convert.lost_values('print', {}, {'seam_position': 'aligned_back'}, 'orcaslicer'), {})
        finally:
            convert.VALUE_NAMES.pop('orcaslicer')

    def test_scarf_seam_from_orcaslicer(self):
        # OrcaSlicer "0.20mm Standard @Creality Sermoon V1": seam_slope_type external ("Contour"), 12 mm long.
        lost = convert.lost_values('print', {}, {'seam_slope_type': 'external', 'seam_slope_min_length': '12'},
                                   'orcaslicer')
        self.assertEqual(lost, {'scarf_seam_placement': 'external', 'scarf_seam_length': '12'})
        settings, _ = convert.map_print(dict({'layer_height': '0.2'}, **lost), 0.4)
        self.assertEqual((settings['walls']['scarf'], settings['walls']['scarf_length']), ('contours', 12))

    def test_with_tisma_slicers_converter(self):
        # Tisma Slicer's converter turns the whole preset (brim_type "no_brim" is a 0 mm brim, printable_area the bed),
        # and misses the per-axis machine limits (it does not know their type): those by name.
        class Conv:
            types = {'brim_width': 'coFloat', 'brim_type': 'coEnum', 'bed_shape': 'coPoints'}

            def convert(self, kind, flat, nozzle):
                out = {'bed_shape': '0x0,200x0,200x200,0x200'} if kind == 'printer' else {}
                if flat.get('brim_type') == 'no_brim':
                    out['brim_width'] = '0'
                return out
        self.assertEqual(convert.lost_values('print', {}, {'brim_type': 'no_brim', 'brim_width': '5'}, 'orcaslicer',
                                             Conv()), {'brim_width': '0'})
        lost = convert.lost_values('printer', {}, {'printable_area': ['0x0', '200x0', '200x200', '0x200'],
                                                   'machine_max_acceleration_x': ['3000', '3000'],
                                                   'machine_max_speed_x': ['300', '300']}, 'orcaslicer', Conv())
        self.assertEqual(lost, {'bed_shape': '0x0,200x0,200x200,0x200', 'machine_max_acceleration_x': '3000,3000',
                                'machine_max_feedrate_x': '300,300'})
        # A converter that knows the per-axis types (Tisma Slicer e54d3a2) but not OrcaSlicer's speed name.
        Conv.types = dict(Conv.types, machine_max_acceleration_x='coFloats', machine_max_feedrate_x='coFloats')
        lost = convert.lost_values('printer', {}, {'machine_max_speed_x': ['300', '300']}, 'orcaslicer', Conv())
        self.assertEqual(lost, {'bed_shape': '0x0,200x0,200x200,0x200', 'machine_max_feedrate_x': '300,300'})

    def test_filament_temperatures_go_to_the_variables(self):
        bundle = {'filament_diameter': '1.75'}
        source = {'nozzle_temperature': ['250'], 'nozzle_temperature_initial_layer': ['250'], 'filament_type': ['ABS']}
        lost = convert.lost_values('filament', bundle, source)
        settings, _ = convert.map_filament(bundle)
        full, _ = convert.map_filament(dict(bundle, **lost))
        filled = convert.fill_lost(settings, full)
        self.assertEqual(settings['machine']['variables']['temperature'], '250')
        self.assertEqual(settings['extrusion']['type'], 'ABS')
        self.assertIn('machine.variables.first_layer_temperature', filled)

    def test_printer_limits_with_the_source_names(self):
        bundle = {'nozzle_diameter': '0.4', 'machine_max_acceleration_extruding': '1000'}
        source = {'machine_max_speed_x': ['300', '200'], 'machine_max_speed_e': ['0', '0'],
                  'machine_max_acceleration_x': ['3000', '3000']}
        lost = convert.lost_values('printer', bundle, source)
        self.assertEqual(lost['machine_max_feedrate_x'], '300,200')
        settings, _ = convert.map_printer(bundle, {})
        full, _ = convert.map_printer(dict(bundle, **lost), {})
        convert.fill_lost(settings, full)
        self.assertEqual(settings['machine']['max_feed_x'], 300)
        self.assertEqual(settings['machine']['max_accel_x'], 3000)
        self.assertNotIn('max_feed_e', settings['machine'])  # 0: no limit, not written


class OrcaProjectWidths(unittest.TestCase):
    def test_widths_in_percent_of_the_nozzle(self):
        # An OrcaSlicer 3MF: line_width "105%" is of the nozzle; without a name the engine dropped the widths.
        t = convert.translation.table_json('orcaslicer', {'print': {'line_width', 'seam_slope_type'}}, renames={})
        row = t['kinds']['print']['line_width']
        self.assertEqual((row['prusaslicer'], row['percent_of'], row['engine']),
                         ('extrusion_width', 'nozzle', 'walls.width'))
        self.assertEqual(t['kinds']['print']['seam_slope_type']['prusaslicer_values']['external'], 'contours')

    def test_names_from_tisma_slicers_converter(self):
        # Creality Print "outer_wall_speed": the value comparison finds no name; Tisma Slicer's converter renames it.
        t = convert.translation.table_json('crealityprint', {'print': {'outer_wall_speed', 'sparse_infill_pattern'}},
                                           renames={}, fallback={
                                               'outer_wall_speed': ('external_perimeter_speed', {}),
                                               'sparse_infill_pattern': ('fill_pattern', {
                                                   'prusaslicer_values': {'crosshatch': 'grid'}})})
        row = t['kinds']['print']['outer_wall_speed']
        self.assertEqual((row['prusaslicer'], row['engine'], row['renamed_by']),
                         ('external_perimeter_speed', 'speed.outer_wall', 'converter'))
        self.assertEqual(t['kinds']['print']['sparse_infill_pattern']['prusaslicer_values'], {'crosshatch': 'grid'})

    def test_bed_temperature_of_the_projects_plate(self):
        # OrcaSlicer: one bed temperature per plate type; a project's is the one of its plate (spec PF14).
        plates = {'plates': {'High Temp Plate': ['hot_plate_temp', 'hot_plate_temp_initial_layer']},
                  'select': ['curr_bed_type', 'default_bed_type'], 'index': ['Default Plate', 'High Temp Plate'],
                  'order': ['hot_plate_temp']}
        t = convert.translation.table_json(
            'orcaslicer', {'filament': {'hot_plate_temp', 'hot_plate_temp_initial_layer'}}, renames={}, plates=plates)
        self.assertEqual(t['plate_temperature'], plates)
        row = t['kinds']['filament']['hot_plate_temp_initial_layer']
        self.assertEqual((row['prusaslicer'], row['rule'], row['plate']),
                         ('first_layer_bed_temperature', 'plate_temperature', 'High Temp Plate'))
        self.assertEqual(row['engine'], 'machine.variables.first_layer_bed_temperature')

    def test_accelerations_in_percent_of_the_default(self):
        # OrcaSlicer sparse_infill_acceleration "100%" is of default_acceleration (567 presets).
        S = os.environ.get('TISMA_CONVERTER')
        if not S:
            self.skipTest('needs Tisma Slicer\'s converter (TISMA_CONVERTER)')
        r = convert.converter_renames(S)
        self.assertEqual(r['sparse_infill_acceleration'],
                         ('infill_acceleration', {'percent_of': 'acceleration.default'}))


class SourceOverBundle(unittest.TestCase):
    """Where Tisma Slicer's bundle has another value than its source program's preset, the source's wins (the
    profile behaves as in its source program)."""

    class Conv:
        def __init__(self, out):
            self.out = out

        def convert(self, kind, flat, nozzle):
            return {k: (v(nozzle) if callable(v) else v) for k, v in self.out.items()}

    def test_source_value_wins(self):
        # OrcaSlicer 1d577ea "Anycubic ABS @Anycubic Kobra S1 Max 0.8 nozzle": 220 degrees; the bundle has 250.
        conv = self.Conv({'first_layer_temperature': '220', 'temperature': '220', 'bed_temperature': '90'})
        over = convert.source_over_bundle('filament', {'first_layer_temperature': '250', 'temperature': '220',
                                                       'bed_temperature': '90.0'}, {}, conv)
        self.assertEqual(over, {'first_layer_temperature': ('250', '220')})

    def test_widths_of_a_print_for_any_nozzle(self):
        # A width in % of each printer's nozzle: for a print of any nozzle the bundle's mm are not replaced here.
        conv = self.Conv({'extrusion_width': lambda n: '%g' % (1.05 * n), 'perimeters': '2'})
        self.assertEqual(convert.source_over_bundle('print', {'extrusion_width': '0.21', 'perimeters': '3'}, {}, conv),
                         {'perimeters': ('3', '2')})
        self.assertEqual(convert.source_over_bundle('print', {'extrusion_width': '0.21'}, {}, conv, 0.4),
                         {'extrusion_width': ('0.21', '0.42')})

    def test_belt_print_keeps_the_bundles_brim(self):
        # VertexSlice 1d6ad28 "0.20mm Standard @IdeaFormer IR3 V2": brim_width 5 (its generic process); Tisma Slicer's
        # belt bundle has 0, and the engine refuses a brim on a belt printer.
        conv = self.Conv({'brim_width': '5', 'perimeters': '2'})
        belt = {'brim_width': '0', 'perimeters': '3',
                'compatible_printers_condition': 'printer_notes=~/.*BELT_IDEAFORMER_IR3V2.*/'}
        kept = {}
        self.assertEqual(convert.source_over_bundle('print', belt, {}, conv, kept=kept), {'perimeters': ('3', '2')})
        self.assertEqual(kept, {'brim_width': ('0', '5')})
        self.assertEqual(convert.source_over_bundle('print', {'brim_width': '0'}, {}, conv), {'brim_width': ('0', '5')})


class OfficialBundles(unittest.TestCase):
    def test_differences_with_the_replaced_bundle(self):
        # Bambu Studio 930fe93 against OrcaSlicer 1d577ea, as Tisma Slicer's converter writes them: "Bambu Lab A1 0.4
        # nozzle" gets extruder_clearance_radius 57 (none in OrcaSlicer's); a preset only in one is counted.
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, 'Orca_BBL.ini'), 'w') as f:
                f.write('[printer:Bambu Lab A1 0.4 nozzle]\nprinter_notes = PRINTER_VENDOR_ORCA_BBL\n'
                        'bed_shape = 0x0,256x0,256x256,0x256\n\n[print:Old only]\nperimeters = 2\n')
            new = os.path.join(d, 'new', 'BambuStudio_BBL.ini')
            os.makedirs(os.path.dirname(new))
            with open(new, 'w') as f:
                f.write('[printer:Bambu Lab A1 0.4 nozzle]\nprinter_notes = PRINTER_VENDOR_BAMBUSTUDIO_BBL\n'
                        'bed_shape = 0x0,256x0,256x256,0x256\nextruder_clearance_radius = 57\n\n'
                        '[printer:Bambu Lab H3C 0.4 nozzle]\nprinter_notes = x\n')
            stats = convert.collections.Counter()
            out = convert.official_differences({new: 'Orca_BBL'}, d, stats)
        self.assertEqual([(x['key'], x['replaced_value'], x['official_value']) for x in out],
                         [('extruder_clearance_radius', None, '57'),
                          ('printer_notes', 'PRINTER_VENDOR_ORCA_BBL', 'PRINTER_VENDOR_BAMBUSTUDIO_BBL')])
        self.assertEqual(stats['official presets not in the replaced bundle (printer)'], 1)
        self.assertEqual(stats['replaced presets not in the official bundles'], 1)


class ReplaceModels(unittest.TestCase):
    def test_only_the_models_the_official_bundle_has(self):
        # QIDI Studio 21d4745 has the Q1 Pro but not the X-CF Pro of OrcaSlicer's Qidi bundle: the X-CF Pro, its
        # printer and its print stay; the Q1 Pro's printer, its own print and a filament QIDI Studio has go.
        with tempfile.TemporaryDirectory() as d:
            old, new = os.path.join(d, 'Orca_Qidi.ini'), os.path.join(d, 'QIDIStudio_Q_Series.ini')
            with open(old, 'w') as f:
                f.write('[vendor]\nname = Qidi\n\n[printer_model:Qidi Q1 Pro]\nname = Qidi Q1 Pro\n\n'
                        '[printer_model:Qidi X-CF Pro]\nname = Qidi X-CF Pro\n\n'
                        '[printer:Qidi Q1 Pro 0.4 nozzle]\nprinter_model = Qidi Q1 Pro\n\n'
                        '[printer:Qidi X-CF Pro 0.4 nozzle]\nprinter_model = Qidi X-CF Pro\n\n'
                        '[print:0.2mm @Qidi Q1 Pro]\ncompatible_printers = "Qidi Q1 Pro 0.4 nozzle"\n\n'
                        '[print:0.2mm @Qidi X-CF Pro]\ncompatible_printers = "Qidi X-CF Pro 0.4 nozzle"\n\n'
                        '[filament:QIDI PLA Rapido]\ncompatible_printers = "Qidi X-CF Pro 0.4 nozzle"\n')
            with open(new, 'w') as f:
                f.write('[vendor]\nname = Qidi\n\n[printer_model:Q1 Pro]\nname = Q1 Pro\n\n'
                        '[printer:Qidi Q1 Pro 0.4 nozzle]\nprinter_model = Q1 Pro\nnozzle_diameter = 0.4\n\n'
                        '[print:0.2mm @Qidi Q1 Pro]\ncompatible_printers = "Qidi Q1 Pro 0.4 nozzle"\n\n'
                        '[filament:QIDI PLA Rapido]\ncompatible_printers = "Qidi Q1 Pro 0.4 nozzle"\n')
            o = convert.Bundle(old)
            gone = convert.replace_models(o, convert.Bundle(new))
        self.assertEqual(gone, {'Qidi Q1 Pro 0.4 nozzle'})
        self.assertEqual(list(o.models), ['Qidi X-CF Pro'])
        self.assertEqual(sorted(o.sections), [('print', '0.2mm @Qidi X-CF Pro'), ('printer', 'Qidi X-CF Pro 0.4 nozzle')])

    def test_an_unusable_official_model_stays_from_the_replaced_bundle(self):
        # Orca-Flashforge c45cc82: the Guider 2s has only print templates (instantiation false), and the Guider4 HF
        # nozzles are "0.6HF"; OrcaSlicer's Flashforge has them usable, so those models stay from it.
        with tempfile.TemporaryDirectory() as d:
            old, new = os.path.join(d, 'Orca_Flashforge.ini'), os.path.join(d, 'OrcaFlashforge_Flashforge.ini')
            with open(old, 'w') as f:
                f.write('[vendor]\nname = Flashforge\n\n[printer_model:Flashforge Guider4]\nname = Flashforge Guider4\n\n'
                        '[printer:Flashforge Guider4 0.6 HF nozzle]\nprinter_model = Flashforge Guider4\n'
                        'nozzle_diameter = 0.6\n\n[print:0.30mm @FF G4]\n'
                        'compatible_printers = "Flashforge Guider4 0.6 HF nozzle"\n')
            with open(new, 'w') as f:
                f.write('[vendor]\nname = Flashforge\n\n[printer_model:Flashforge Guider4]\nname = Flashforge Guider4\n\n'
                        '[printer:Flashforge Guider4 0.6 HF nozzle]\nprinter_model = Flashforge Guider4\n'
                        'nozzle_diameter = 0.6HF\n\n[print:0.30mm @FF G4]\n'
                        'compatible_printers = "Flashforge Guider4 0.6 HF nozzle"\n')
            o, n = convert.Bundle(old), convert.Bundle(new)
            stats = convert.collections.Counter()
            convert.replace_models(o, n, stats)
        self.assertEqual(list(o.models), ['Flashforge Guider4'])
        self.assertEqual(list(n.models), [])
        self.assertEqual(sum(stats.values()), 1)

    def test_a_parent_of_a_remaining_preset_stays(self):
        # OrcaSlicer 1d577ea "Anycubic PLA-CF @Anycubic Kobra S1 Max 0.4 nozzle" (a model Anycubic Slicer Next 6103ed8
        # lacks) inherits "Generic PLA-CF @Anycubic", whose printers are all models Anycubic Slicer Next has.
        with tempfile.TemporaryDirectory() as d:
            old, new = os.path.join(d, 'Orca_Anycubic.ini'), os.path.join(d, 'AnycubicSlicerNext_Anycubic.ini')
            with open(old, 'w') as f:
                f.write('[vendor]\nname = Anycubic\n\n[printer_model:Anycubic Kobra 3]\nname = Anycubic Kobra 3\n\n'
                        '[printer:Anycubic Kobra 3 0.4 nozzle]\nprinter_model = Anycubic Kobra 3\n\n'
                        '[filament:Generic PLA-CF @Anycubic]\ncompatible_printers = "Anycubic Kobra 3 0.4 nozzle"\n\n'
                        '[filament:Anycubic PLA-CF @Anycubic Kobra S1 Max 0.4 nozzle]\n'
                        'inherits = Generic PLA-CF @Anycubic\ncompatible_printers = "Anycubic Kobra S1 Max 0.4 nozzle"\n')
            with open(new, 'w') as f:
                f.write('[vendor]\nname = Anycubic\n\n[printer_model:Anycubic Kobra 3]\nname = Anycubic Kobra 3\n\n'
                        '[printer:Anycubic Kobra 3 0.4 nozzle]\nprinter_model = Anycubic Kobra 3\nnozzle_diameter = 0.4\n\n'
                        '[print:0.2mm @Anycubic Kobra 3]\ncompatible_printers = "Anycubic Kobra 3 0.4 nozzle"\n')
            o = convert.Bundle(old)
            convert.replace_models(o, convert.Bundle(new))
        self.assertIn(('filament', 'Generic PLA-CF @Anycubic'), o.sections)


class CuraFlavor(unittest.TestCase):
    def test_marlin_without_a_version(self):
        # Cura 5bea2f8 fdmprinter.def.json: machine_gcode_flavor "RepRap (Marlin/Sprinter)", which does not say which
        # Marlin; a definition inherits it.
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'definitions'))
            json.dump({'settings': {'machine_settings': {'children': {
                'machine_gcode_flavor': {'default_value': 'RepRap (Marlin/Sprinter)'},
                'machine_start_gcode': {'default_value': 'G28'}}}}},
                open(os.path.join(d, 'definitions', 'fdmprinter.def.json'), 'w'))
            json.dump({'inherits': 'fdmprinter'}, open(os.path.join(d, 'definitions', 'box.def.json'), 'w'))
            block = convert.upstream.cura_machine_gcode(convert.upstream.CuraDefinitions(d), 'box')
        self.assertEqual(block['flavor'], convert.CURA_MARLIN)


class DialectTables(unittest.TestCase):
    def test_same_key_with_other_value_names(self):
        # OrcaSlicer's seam "back" is PrusaSlicer's "rear": the key keeps its name, its values do not.
        r = convert.translation.Renames()
        for i in range(20):
            seam = ('aligned', 'nearest', 'back')[i % 3]
            r.add('orcaslicer', 'print', {'seam_position': seam, 'layer_height': '0.2'},
                  {'seam_position': 'rear' if seam == 'back' else seam, 'layer_height': '0.2'})
        got = r.renames('orcaslicer', 'print')
        self.assertEqual(got['seam_position'][0], 'seam_position')
        self.assertEqual(got['seam_position'][3], {'aligned': 'aligned', 'back': 'rear', 'nearest': 'nearest'})
        self.assertEqual(len(got['layer_height']), 3)  # numbers: no value names


class Models(unittest.TestCase):
    def test_model_takes_what_the_bundle_lost_from_the_source_program(self):
        # As Creality Print's "Creality Z2": the bundle keeps the name and family, no materials nor pictures.
        with tempfile.TemporaryDirectory() as tmp:
            base = os.path.join(tmp, 'Creality')
            os.makedirs(os.path.join(base, 'machine'))
            json.dump({'type': 'machine_model', 'name': 'Creality Z2', 'family': 'Creality',
                       'bed_model': 'k1_bed.stl', 'bed_texture': 'missing.svg',
                       'default_materials': 'Hyper PLA;CR-PETG'},
                      open(os.path.join(base, 'machine', 'Creality Z2.json'), 'w'))
            for f in ('k1_bed.stl', 'Creality Z2_cover.png'):
                open(os.path.join(base, f), 'w').write('x')
            out = os.path.join(tmp, 'pack')
            model = {'family': 'Creality', 'default_materials': []}
            assets = {}
            filled = convert.model_from_source(model, assets, base, 'Creality Z2', out, 'vendors/V')
            self.assertEqual(filled, ['default_materials', 'assets.thumbnail', 'assets.bed_model'])
            self.assertEqual(model['default_materials'], ['Hyper PLA', 'CR-PETG'])
            self.assertTrue(os.path.isfile(os.path.join(out, assets['bed_model'])))
            self.assertNotIn('bed_texture', assets)  # the source names a file it does not have
            self.assertEqual(convert.model_from_source(model, assets, base, 'Other', out, 'vendors/V'), [])


class Assets(unittest.TestCase):
    def test_file_named_in_another_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            open(os.path.join(tmp, '125x130.svg'), 'w').write('x')
            self.assertEqual(convert.asset_file(tmp, '125X130.svg'), '125x130.svg')
            self.assertEqual(convert.asset_file(tmp, 'other.svg'), 'other.svg')
            self.assertEqual(convert.asset_file(os.path.join(tmp, 'none'), 'a.svg'), 'a.svg')


class Reproducible(unittest.TestCase):
    def test_generated_time_from_source_date_epoch(self):
        old = os.environ.get('SOURCE_DATE_EPOCH')
        os.environ['SOURCE_DATE_EPOCH'] = '1762732800'
        try:
            self.assertEqual(convert.generated_time(), '2025-11-10T00:00:00Z')
        finally:
            if old is None:
                del os.environ['SOURCE_DATE_EPOCH']
            else:
                os.environ['SOURCE_DATE_EPOCH'] = old


class SourceValues(unittest.TestCase):
    def test_print_values_for_the_machine_gcode(self):
        # OrcaSlicer machine G-code reads outer_wall_acceleration, a print setting, by its own name.
        values = {'outer_wall_acceleration': ['5000'], 'layer_height': '0.2', 'sparse_infill_density': '15%'}
        self.assertEqual(convert.template_values(values, {'outer_wall_acceleration', 'curr_bed_type'}),
                         {'outer_wall_acceleration': ['5000']})
        # A variable PrusaSlicer has too is the engine's, from the translated print (not a per-extruder list).
        values['default_acceleration'] = ['10000', '10000']
        self.assertEqual(convert.template_values(values, {'outer_wall_acceleration', 'default_acceleration'},
                                                 exclude={'default_acceleration': 'coFloat'}),
                         {'outer_wall_acceleration': ['5000']})


class MergedPresets(unittest.TestCase):
    def test_groups_of_the_same_base_name_and_values(self):
        # OrcaSlicer repeats "0.20mm Standard" for the X1C and the P1P; Tisma Slicer keeps one, for both printers.
        with tempfile.TemporaryDirectory() as tmp:
            base = os.path.join(tmp, 'BBL')
            os.makedirs(os.path.join(base, 'process'))
            for name, printers, speed in (('0.20mm Standard @BBL X1C', ['X1C 0.4', 'P1S 0.4'], '200'),
                                          ('0.20mm Standard @BBL P1P', ['P1P 0.4'], '200'),
                                          ('0.20mm Standard @BBL A1', ['A1 0.4'], '180')):
                with open(os.path.join(base, 'process', name + '.json'), 'w') as f:
                    json.dump({'type': 'process', 'name': name, 'instantiation': 'true', 'setting_id': name,
                               'compatible_printers': printers, 'outer_wall_speed': speed}, f)
            vendor = convert.upstream.OrcaVendor(base, kind='process')
            groups = convert.upstream.merged_groups(vendor)
        self.assertEqual(sorted(groups), [(['0.20mm Standard @BBL A1'], ['A1 0.4']),
                                          (['0.20mm Standard @BBL P1P', '0.20mm Standard @BBL X1C'],
                                           ['P1P 0.4', 'X1C 0.4', 'P1S 0.4'])])
        converted = lambda values, printers: {'outer_wall': 1}  # a converter that drops the speed: one group
        self.assertEqual(len(convert.upstream.merged_groups(vendor, converted)), 1)


class CuraBeds(unittest.TestCase):
    def test_platform_in_the_bed_frame(self):
        # A 100 x 80 mm plate 5 mm thick, top at Z 0, as an STL in Cura's files (Z up, around the bed's centre), and
        # the same as an OBJ; Cura moves it by platform_offset in its scene (Y up): (1, -5, 2) is 1 mm right, 5 mm
        # down and 2 mm toward the front (-2 on the printer's Y).
        import cura_platform
        quad = [((-50, -40, 0), (50, -40, 0), (50, 40, 0)), ((-50, -40, 0), (50, 40, 0), (-50, 40, 0)),
                ((-50, -40, -5), (50, 40, -5), (50, -40, -5))]
        with tempfile.TemporaryDirectory() as tmp:
            stl = os.path.join(tmp, 'p.stl')
            with open(stl, 'wb') as f:
                f.write(cura_platform.binary_stl(quad))
            obj = os.path.join(tmp, 'p.obj')
            with open(obj, 'w') as f:
                f.write('v -50 -40 0\nv 50 -40 0\nv 50 40 0\nv -50 40 0\nf 1 2 3 4\n')
            tris = cura_platform.platform_triangles(stl, [1, -5, 2])
            self.assertEqual(tris[0][0], (-49.0, -42.0, -5.0))
            self.assertEqual(cura_platform.platform_triangles(obj)[1], ((-50, -40, 0), (50, 40, 0), (-50, 40, 0)))
            bed = [[0, 0], [100, 0], [100, 80], [0, 80]]
            data, share = cura_platform.bed_model(stl, None, bed)
            self.assertAlmostEqual(share, 1.0)
            self.assertEqual(cura_platform.read_binary_stl(data)[0][0], (0.0, 0.0, 0.0))
            self.assertEqual(cura_platform.bed_model(stl, [0, -10, 0], bed)[1], 0.0)  # plate 10 mm down: none


class Widths(unittest.TestCase):
    def test_percent_wall_width_is_of_the_layer_height(self):
        # Tisma Slicer (PrusaSlicer) computes a width in % over the layer height (Flow.cpp), not over the nozzle.
        settings, _ = convert.map_print({'layer_height': '0.12', 'perimeter_extrusion_width': '111%'}, 0.4)
        self.assertAlmostEqual(settings['walls']['width'], 0.1332)
        settings, _ = convert.map_print({'layer_height': '0.2', 'perimeter_extrusion_width': '0',
                                         'extrusion_width': '0.45'}, 0.4)
        self.assertEqual(settings['walls']['width'], 0.45)
        settings, _ = convert.map_print({'layer_height': '0.2', 'perimeter_extrusion_width': '0'}, 0.4)
        self.assertEqual(settings['walls']['width'], 0.45)  # automatic: 1.125 times the nozzle
        settings, _ = convert.map_print({'layer_height': '0.12', 'external_perimeter_extrusion_width': '105%'}, 0.4)
        self.assertAlmostEqual(settings['walls']['outer_width'], 0.126)
        settings, _ = convert.map_print({'layer_height': '0.12', 'external_perimeter_extrusion_width': '0'}, 0.4)
        self.assertNotIn('outer_width', settings['walls'])
        # E2D "0.20mm QUALITY @E2D i310": no outer width of its own, extrusion_width 0.4: the source prints the outer
        # wall at 0.4 mm (Flow.cpp takes extrusion_width), not at the automatic 0.45.
        settings, _ = convert.map_print({'layer_height': '0.2', 'external_perimeter_extrusion_width': '0',
                                         'extrusion_width': '0.4'}, 0.4)
        self.assertEqual(settings['walls']['outer_width'], 0.4)


class SupportGap(unittest.TestCase):
    def test_percent_of_the_outer_wall_width(self):
        # Comgrow T500 "0.20mm Standard": 60% of the 0.42 mm outer wall (not of the 0.45 mm walls) is 0.252 mm.
        settings, _ = convert.map_print({'layer_height': '0.2', 'support_material_xy_spacing': '60%',
                                         'external_perimeter_extrusion_width': '0.42',
                                         'perimeter_extrusion_width': '0.45'}, 0.4)
        self.assertAlmostEqual(settings['support']['xy_gap'], 0.252)
        settings, _ = convert.map_print({'layer_height': '0.2', 'support_material_xy_spacing': '50%'}, 0.4)
        self.assertAlmostEqual(settings['support']['xy_gap'], 0.225)  # of the automatic 1.125 x nozzle
        settings, _ = convert.map_print({'layer_height': '0.2', 'support_material_xy_spacing': '60%'}, None)
        self.assertEqual(settings['support']['xy_gap'], '60%')  # for any nozzle: of the automatic walls.width
        settings, _ = convert.map_print({'layer_height': '0.2', 'support_material_xy_spacing': '0.3'}, 0.4)
        self.assertEqual(settings['support']['xy_gap'], 0.3)


class PrintOptions(unittest.TestCase):
    """Print options the engine reads (its docs/CONFIG.md) and the bundles set: written, not left to the engine's
    defaults."""

    def test_support_extruders(self):
        # Prusa "0.15mm OPTIMAL SOLUBLE INTERFACE @MK2.5" (MMU, 5 tools): the interface with tool 5, the base with
        # the one printing. On a machine with fewer tools the engine takes the first, as the source (ME14).
        settings, _ = convert.map_print({'layer_height': '0.2', 'support_material_extruder': '0',
                                         'support_material_interface_extruder': '5'}, 0.4)
        self.assertEqual(settings['extruders'], {'support': 0, 'support_interface': 5})

    def test_retract_only_crossing_walls(self):
        # Voron bundle prints: only_retract_when_crossing_perimeters = 1. OrcaSlicer's reduce_infill_retraction (read
        # from the source preset by name, Tisma Slicer's converter drops it) goes to the same setting.
        settings, _ = convert.map_print({'layer_height': '0.2', 'only_retract_when_crossing_perimeters': '1'}, 0.4)
        self.assertIs(settings['retraction']['only_crossing_walls'], True)
        settings, _ = convert.map_print({'layer_height': '0.2', 'reduce_infill_retraction': '0'}, 0.4)
        self.assertIs(settings['retraction']['only_crossing_walls'], False)
        lost = convert.lost_values('print', {}, {'reduce_infill_retraction': '1'}, 'orcaslicer')
        self.assertEqual(lost, {'reduce_infill_retraction': '1'})

    def test_tisma_options(self):
        # Geeetech "M1 speed" prints: gap_fill_enabled = 0 with a gap fill speed of 100 (no gap fill in the source).
        settings, _ = convert.map_print({'layer_height': '0.2', 'gap_fill_enabled': '0', 'gap_fill_speed': '100',
                                         'over_bridge_speed': '35%', 'travel_short_distance_acceleration': '250'},
                                        0.4)
        self.assertIs(settings['walls']['gap_fill'], False)
        self.assertEqual((settings['speed']['over_bridges'], settings['acceleration']['short_travel']), ('35%', 250))
        printer, _ = convert.map_printer({'nozzle_high_flow': '1,1', 'multimaterial_purging': '80'})
        self.assertEqual((printer['machine']['high_flow_nozzle'], printer['wipe_tower']['purge_volumes']), (True, 80))

    def test_no_speed_cap(self):
        # The source programs cap no set speed (max_print_speed is only for speeds left at 0): IdeaFormer IR3
        # "0.20mm Standard" prints its outer wall at 120 mm/s with walls at 50. speed.max would cap it.
        settings, _ = convert.map_print({'layer_height': '0.2', 'perimeter_speed': '50', 'infill_speed': '50',
                                         'external_perimeter_speed': '120', 'max_print_speed': '80'}, 0.4)
        self.assertNotIn('max', settings['speed'])
        self.assertEqual(settings['speed']['outer_wall'], 120)

    def test_ooze_prevention(self):
        settings, _ = convert.map_print({'layer_height': '0.2', 'ooze_prevention': '1',
                                         'standby_temperature_delta': '-150'}, 0.4)
        self.assertEqual(settings['extruders'], {'ooze_prevention': True, 'standby_delta': -150})

    def test_honeycomb_3d(self):
        settings, _ = convert.map_print({'layer_height': '0.2', 'fill_pattern': '3dhoneycomb'}, 0.4)
        self.assertEqual(settings['infill']['pattern'], 'honeycomb_3d')

    def test_surface_patterns(self):
        settings, _ = convert.map_print({'layer_height': '0.2', 'top_fill_pattern': 'monotoniclines',
                                         'bottom_fill_pattern': 'concentric'}, 0.4)
        self.assertEqual(settings['surfaces']['top_pattern'], 'monotonic_lines')
        self.assertEqual(settings['surfaces']['bottom_pattern'], 'concentric')

    def test_role_widths(self):
        # A role's 0 is extrusion_width; both 0 is the source's automatic width (the support's is the nozzle).
        settings, _ = convert.map_print({'layer_height': '0.2', 'infill_extrusion_width': '0',
                                         'extrusion_width': '0.5', 'top_infill_extrusion_width': '200%',
                                         'support_material_extrusion_width': '0'}, 0.4)
        self.assertEqual(settings['infill']['width'], 0.5)
        self.assertEqual(settings['surfaces']['top_width'], 0.4)
        self.assertEqual(settings['support']['width'], 0.5)
        settings, _ = convert.map_print({'layer_height': '0.2', 'infill_extrusion_width': '0',
                                         'extrusion_width': '0', 'support_material_extrusion_width': '0'}, 0.6)
        self.assertNotIn('width', settings.get('infill', {}))
        self.assertEqual(settings['support']['width'], 0.6)
        settings, _ = convert.map_print({'layer_height': '0.2', 'support_material_extrusion_width': '0'}, None)
        self.assertNotIn('width', settings.get('support', {}))

    def test_support_brim_labels(self):
        settings, _ = convert.map_print({'layer_height': '0.2', 'support_material_style': 'organic',
                                         'support_material_pattern': 'rectilinear-grid',
                                         'support_material_interface_pattern': 'auto', 'brim_type': 'no_brim',
                                         'draft_shield': '0', 'gcode_label_objects': '1', 'arc_fitting': 'disabled',
                                         'support_tree_top_rate': '30%', 'infill_overlap': '30',
                                         'perimeter_generator': 'classic'}, 0.4)
        self.assertEqual(settings['support'], dict(settings['support'], style='organic', pattern='grid',
                                                   interface_pattern='automatic', tree_top_rate=30))
        self.assertEqual(settings['adhesion']['brim_type'], 'none')
        self.assertEqual(settings['adhesion']['draft_shield'], 'disabled')
        self.assertEqual(settings['gcode'], {'object_labels': 'octoprint', 'arcs': False})
        self.assertNotIn('wall_overlap', settings.get('infill', {}))  # mm: not the engine's percent
        self.assertEqual(settings['walls']['generator'], 'fixed')
        settings, _ = convert.map_print({'layer_height': '0.2', 'dont_support_bridges': '0'}, 0.4)
        self.assertIs(settings['support']['under_bridges'], True)
        # OrcaSlicer's min_bead_width "100" is 100 % (a percent option); the bundle has it without "%".
        settings, _ = convert.map_print({'layer_height': '0.2', 'min_bead_width': '100', 'min_feature_size': '0.1'},
                                        0.4)
        self.assertEqual((settings['walls']['min_line_width'], settings['walls']['min_detail']), ('100%', 0.1))


class FilamentAndPrinterOptions(unittest.TestCase):
    def test_filament_overrides_and_ramming(self):
        settings, _ = convert.translation.translate('filament', {
            'filament_retract_length': '0.8', 'filament_retract_lift': 'nil', 'filament_wipe': '1',
            'filament_travel_slope': '3', 'filament_ramming_parameters': '"120 100 6.6 6.8 7.2| 0.05 6.6"',
            'cooling': '0', 'filament_shrinkage_compensation_xy': '0.22%'})
        self.assertEqual(settings['extrusion']['retraction'], {'length': 0.8, 'wipe': True})
        self.assertEqual(settings['extrusion']['travel'], {'slope': 3})
        self.assertEqual(settings['extrusion']['ramming'], [6.6, 6.8, 7.2])
        self.assertEqual(settings['extrusion']['shrinkage_xy'], 0.22)
        odd, _ = convert.translation.translate('filament', {'filament_shrinkage_compensation_z': '99.78%',
                                                             'filament_shrinkage_compensation_xy': '-1%'})
        self.assertNotIn('extrusion', odd)
        self.assertIs(settings['cooling']['enabled'], False)

    def test_printer_thumbnails_and_ramp(self):
        settings, _ = convert.map_printer({
            'thumbnails': '64x64,400x300', 'thumbnails_format': 'JPG', 'travel_ramping_lift': '1,1',
            'travel_max_lift': '1.5,1.5', 'extruder_clearance_radius': '45'})
        self.assertEqual(settings['gcode']['thumbnails'], '64x64/JPG, 400x300/JPG')
        self.assertEqual(settings['travel'], {'ramping_lift': True, 'max_lift': 1.5})
        self.assertEqual(settings['sequential']['clearance_radius'], 45)
        # PrusaSlicer's "marlin" is Marlin 1 (the engine's marlin_legacy: M204 S is the printing acceleration),
        # "marlin2" Marlin 2, "reprapfirmware" Duet (G10/M116 temperatures), not the generic reprap.
        for flavor, engine in (('marlin', 'marlin_legacy'), ('marlin2', 'marlin'), ('reprapfirmware', 'reprapfirmware'),
                               ('reprap', 'reprap'), ('repetier', 'repetier'), ('no-extrusion', 'no_extrusion')):
            settings, _ = convert.map_printer({'gcode_flavor': flavor})
            self.assertEqual(settings['machine']['flavor'], engine)
        # Junction deviation (M205 J) only with marlin2: on legacy Marlin, RepRapFirmware or Klipper the source
        # programs keep the jerk (SeeMeCNC RepRapFirmware printers have 0.01).
        settings, _ = convert.map_printer({'machine_max_junction_deviation': '0.01,0', 'gcode_flavor': 'marlin2'})
        self.assertEqual(settings['machine']['junction_deviation'], 0.01)
        for flavor in ('marlin', 'reprapfirmware', 'klipper'):
            settings, _ = convert.map_printer({'machine_max_junction_deviation': '0.01', 'gcode_flavor': flavor})
            self.assertNotIn('junction_deviation', settings.get('machine', {}))
        # Ginger Additive G1 (OrcaSlicer): a pellet printer; Tisma Slicer's bundle lost the flag, the source has it.
        settings, _ = convert.map_printer({'pellet_modded_printer': '1'})
        self.assertEqual(settings['machine']['feedstock'], 'pellet')
        lost = convert.lost_values('printer', {}, {'pellet_modded_printer': '1'}, 'orcaslicer')
        self.assertEqual(lost, {'pellet_modded_printer': '1'})
        # Creality CR-30 (Belt_Creality): a belt printer at 45 degrees, the belt on Z. Without these the engine
        # slices it as a cartesian printer with a 1000 mm bed.
        settings, _ = convert.map_printer({'belt_printer': '1', 'belt_angle': '45', 'belt_axis_z': '1'})
        self.assertEqual(settings['belt'], {'enabled': True, 'angle': 45, 'belt_is_z': True})
        settings, _ = convert.map_printer({'autoemit_temperature_commands': '0'})
        self.assertIs(settings['gcode']['auto_temperatures'], False)


class PrintLimits(unittest.TestCase):
    def test_filament_for_some_prints(self):
        prints = {('G', 'p/fast.json'): ('0.20 mm NORMAL @High-speed', {'infill_speed': '250', 'notes': ''}),
                  ('G', 'p/slow.json'): ('0.20 mm NORMAL', {'infill_speed': '60', 'notes': 'SOLUBLE_SUPPORT'})}
        # Geeetech "Thunder HS-PLA": compatible_prints_condition = infill_speed >= 150
        self.assertEqual(convert.prints_for({'compatible_prints_condition': 'infill_speed >= 150'}, prints),
                         ['p/fast.json'])
        self.assertEqual(convert.prints_for({'compatible_prints_condition': 'notes=~/.*SOLUBLE_SUPPORT.*/'}, prints),
                         ['p/slow.json'])
        # A list of names wins over the condition, as in PrusaSlicer.
        self.assertEqual(convert.prints_for({'compatible_prints': '"0.20 mm NORMAL"',
                                             'compatible_prints_condition': 'infill_speed >= 150'}, prints),
                         ['p/slow.json'])
        self.assertIsNone(convert.prints_for({}, prints))


class FirstLayerSpeed(unittest.TestCase):
    def test_percent_kept(self):
        # Tisma Slicer: "35%" is 35 % of each extrusion's speed on the first layer (GCode.cpp); the engine reads it.
        settings, _ = convert.map_print({'layer_height': '0.2', 'first_layer_speed': '35%'}, 0.4)
        self.assertEqual(settings['speed']['first_layer'], '35%')
        settings, _ = convert.map_print({'layer_height': '0.2', 'first_layer_speed': '30'}, 0.4)
        self.assertEqual(settings['speed']['first_layer'], 30)


class ResinNotes(unittest.TestCase):
    def test_delay_before_exposure(self):
        # ElegooSLA "Generic Standard Resin @ELEGOO SATURN 4": "#Distances in mm, speeds in mm/s, waits in s."
        notes = '"#Distances in mm, speeds in mm/s, waits in s.\\nLIFT_SPEED=1.1667\\nDELAY_BEFORE_EXPOSURE=0.5"'
        settings, _ = convert.map_resin_material({'material_notes': notes})
        self.assertEqual(settings['resin']['wait_before_exposure'], 0.5)
        self.assertEqual(settings['resin']['lift_speed'], 1.1667)


class ResinCorrection(unittest.TestCase):
    def test_per_axis_values(self):
        # PrusaSlicer scales an SLA part by material_correction_x/y/z, not by the "1,1,1" list.
        settings, _ = convert.map_resin_material({'material_correction': '1,1,1', 'material_correction_x': '1.0073',
                                                  'material_correction_y': '1.0073'})
        self.assertEqual((settings['resin']['scale_x'], settings['resin']['scale_y'], settings['resin']['scale_z']),
                         (1.0073, 1.0073, 1))


class ResinLayers(unittest.TestCase):
    def test_initial_layer_height_is_the_first_layer(self):
        # PrusaSlicer SLA: the resin's initial_layer_height is the first layer only; the print's layer_height the rest.
        settings, _ = convert.map_resin_material({'initial_layer_height': '0.05', 'exposure_time': '2'})
        self.assertEqual(settings['resin']['first_layer_height'], 0.05)
        self.assertNotIn('layer_height', settings['resin'])


class Extruders(unittest.TestCase):
    def test_count_nozzles_and_offsets(self):
        # UltiMaker S5: two 0.4 mm nozzles, the second 22 mm behind in Y.
        settings, _ = convert.map_printer({'nozzle_diameter': '0.4,0.4', 'extruder_offset': '0x0,0x22'}, {})
        m = settings['machine']
        self.assertEqual((m['extruders'], m['nozzle_diameter'], m['extruder_offset']), (2, 0.4, [[0, 0], [0, 22]]))
        # Snapmaker U1 "0.4+0.6": four extruders, two nozzles of each.
        settings, _ = convert.map_printer({'nozzle_diameter': '0.4,0.4,0.6,0.6'}, {})
        self.assertEqual(settings['machine']['nozzle_diameter'], [0.4, 0.4, 0.6, 0.6])
        # An MMU (one nozzle) has no offsets; one extruder writes none of these.
        settings, _ = convert.map_printer({'nozzle_diameter': '0.4,0.4', 'extruder_offset': '0x0,5x0',
                                           'single_extruder_multi_material': '1'}, {})
        self.assertNotIn('extruder_offset', settings['machine'])
        settings, _ = convert.map_printer({'nozzle_diameter': '0.4'}, {})
        self.assertNotIn('extruders', settings['machine'])


class Quotes(unittest.TestCase):
    def test_first_text_without_the_bundle_quotes(self):
        self.assertEqual(convert.first_text('"PLA";"PETG"'), 'PLA')
        self.assertEqual(convert.first_text('PLA'), 'PLA')


if __name__ == '__main__':
    unittest.main()
