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


class Quotes(unittest.TestCase):
    def test_first_text_without_the_bundle_quotes(self):
        self.assertEqual(convert.first_text('"PLA";"PETG"'), 'PLA')
        self.assertEqual(convert.first_text('PLA'), 'PLA')


if __name__ == '__main__':
    unittest.main()
