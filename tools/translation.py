"""The translation of the source programs' settings to the engine's keys (the engine's docs/CONFIG.md): one table,
which tools/convert.py applies to every profile and which the pack ships as data (docs/FORMAT.md, «Traducción de
claves») for the engine to open other programs' projects with the same translation.

TABLE has the PrusaSlicer names (the ones of Tisma Slicer's bundles). Each entry:
  from   the source key (or keys, the first one that gives a value)
  to     the engine key, "group.key" (None for a value the engine computes from others)
  how    the conversion: number, numbers, flag, factor, map, percent_of, first_item, number_strip_percent,
         width_of_layer, number_or_percent, percent_only, absolute_only, at_least, points, or rule (a conversion
         with its own steps, named)
  group  translated (the same setting), similar (the closest the engine has; the note says what differs)
  note   what the conversion does, when it is not plain
Every other key of the source has no equivalent (group none): tools/convert.py lists them in stats.json.
"""

import re

FORMAT_VERSION = 1

# The source's gcode_flavor (PrusaSlicer and OrcaSlicer names) as the engine's machine.flavor: "marlin" is Marlin 1
# (the engine's marlin_legacy) and "marlin2" Marlin 2 (the engine's marlin); "reprap" is RepRap/Sprinter.
FLAVORS = {'marlin': 'marlin_legacy', 'marlinlegacy': 'marlin_legacy', 'marlin2': 'marlin', 'klipper': 'klipper',
           'reprap': 'reprap', 'reprapfirmware': 'reprapfirmware', 'repetier': 'repetier', 'smoothie': 'smoothie',
           'teacup': 'teacup', 'makerware': 'makerware', 'sailfish': 'sailfish', 'mach3': 'mach3',
           'machinekit': 'machinekit', 'no-extrusion': 'no_extrusion'}

PATTERNS = {'rectilinear': 'rectilinear', 'monotonic': 'monotonic', 'grid': 'grid', 'gyroid': 'gyroid',
            'triangles': 'triangles', 'stars': 'stars', 'cubic': 'cubic', 'adaptivecubic': 'adaptive_cubic',
            'supportcubic': 'support_cubic', 'lightning': 'lightning', 'alignedrectilinear': 'aligned_rectilinear',
            'zigzag': 'zigzag', 'line': 'line', 'honeycomb': 'honeycomb', 'concentric': 'concentric',
            'hilbertcurve': 'hilbert', 'archimedeanchords': 'archimedean', 'octagramspiral': 'octagram',
            '3dhoneycomb': 'honeycomb_3d'}

SEAMS = {'aligned': 'aligned', 'nearest': 'nearest', 'random': 'random', 'rear': 'rear'}

# The top and bottom surface patterns the engine draws (surfaces.top_pattern / bottom_pattern).
SURFACE_PATTERNS = {'monotonic': 'monotonic', 'rectilinear': 'rectilinear', 'monotoniclines': 'monotonic_lines',
                    'alignedrectilinear': 'aligned_rectilinear', 'concentric': 'concentric',
                    'hilbertcurve': 'hilbert', 'archimedeanchords': 'archimedean', 'octagramspiral': 'octagram'}

FILAMENT_VARIABLES = ('temperature', 'first_layer_temperature', 'bed_temperature', 'first_layer_bed_temperature',
                      'chamber_temperature', 'chamber_minimal_temperature', 'idle_temperature')

# The printer's retraction and travel values a filament can set (filament_<key> in the source; "nil" leaves the
# printer's), with the engine's names (extrusion.retraction / extrusion.travel).
FILAMENT_OVERRIDES = {'retract_length': 'retraction.length', 'retract_speed': 'retraction.speed',
                      'deretract_speed': 'retraction.unretract_speed',
                      'retract_restart_extra': 'retraction.restart_extra', 'retract_lift': 'retraction.lift',
                      'retract_lift_above': 'retraction.lift_above', 'retract_lift_below': 'retraction.lift_below',
                      'retract_before_travel': 'retraction.min_travel',
                      'retract_layer_change': 'retraction.on_layer_change', 'wipe': 'retraction.wipe',
                      'retract_before_wipe': 'retraction.before_wipe', 'travel_ramping_lift': 'travel.ramping_lift',
                      'travel_slope': 'travel.slope', 'travel_max_lift': 'travel.max_lift'}
BARE_PERCENT = ('"N%" of the nozzle; a bare number over 10 is a percent (an OrcaSlicer percent option that Tisma '
                'Slicer\'s converter writes without "%")')
SHRINKAGE = 'percent; outside 0 to 20 not written (the engine\'s range; source data such as a Z size of 0.22 %)'
FLAG_OVERRIDES = ('retract_layer_change', 'wipe', 'travel_ramping_lift')

RESIN_NOTE_KEYS = {'LIFT_DISTANCE': 'lift_distance', 'LIFT_SPEED': 'lift_speed',
                   'BOTTOM_LIFT_DISTANCE': 'bottom_lift_distance', 'BOTTOM_LIFT_SPEED': 'bottom_lift_speed',
                   'RETRACT_SPEED': 'retract_speed', 'BOTTOM_RETRACT_SPEED': 'bottom_retract_speed',
                   'WAIT_BEFORE_EXPOSURE': 'wait_before_exposure',
                   'DELAY_BEFORE_EXPOSURE': 'wait_before_exposure',  # the same wait, as the Elegoo bundle names it
                   'BOTTOM_WAIT_BEFORE_EXPOSURE':
                   'bottom_wait_before_exposure', 'WAIT_AFTER_CURE': 'wait_after_cure',
                   'WAIT_AFTER_LIFT': 'wait_after_lift', 'LIGHT_PWM': 'light_pwm', 'BOTTOM_LIGHT_PWM':
                   'bottom_light_pwm', 'ANTIALIASING': 'antialiasing', 'DENSITY': 'density'}


def E(src, to, how='number', group='translated', note='', **kw):
    out = {'from': src, 'to': to, 'how': how, 'group': group}
    if note:
        out['note'] = note
    out.update(kw)
    return out


TABLE = {
    'printer': [
        E('nozzle_diameter', 'machine.nozzle_diameter', note='the first extruder'),
        E('bed_shape', 'machine.bed', 'points', used='written', note='"XxY" corners; written only with 3 or more'),
        E('max_print_height', 'machine.max_height'),
        E('gcode_flavor', 'machine.flavor', 'map', values=FLAVORS),
        E('use_relative_e_distances', 'machine.relative_extrusion', 'flag'),
        E(['start_gcode', 'end_gcode'], 'machine.start_gcode, machine.end_gcode', 'rule', rule='gcode_template',
          note='only with simple variables; the whole G-code is in the "gcode" block (docs/FORMAT.md)'),
        E('machine_max_feedrate_x', 'machine.max_feed_x', positive=True, note='not written when 0 (no limit)'),
        E('machine_max_feedrate_y', 'machine.max_feed_y', positive=True, note='not written when 0 (no limit)'),
        E('machine_max_feedrate_z', 'machine.max_feed_z', positive=True, note='not written when 0 (no limit)'),
        E('machine_max_feedrate_e', 'machine.max_feed_e', positive=True, note='not written when 0 (no limit)'),
        E(['machine_max_acceleration_extruding', 'machine_max_acceleration_travel'],
          'machine.acceleration, machine.travel_acceleration', 'rule', rule='acceleration',
          note='only when extruding is not 0; travel falls back to extruding'),
        E('machine_max_jerk_x', 'machine.corner_speed', nonzero=True, group='similar', used='written',
          note='the X jerk as the corner speed; not written when 0'),
        E('retract_length', 'retraction.length'),
        E('retract_speed', 'retraction.speed', nonzero=True),
        E('retract_lift', 'retraction.lift'),
        E('retract_before_travel', 'retraction.min_travel'),
        E('deretract_speed', 'retraction.unretract_speed', note='0: the retraction speed'),
        E('retract_restart_extra', 'retraction.restart_extra', note='negative: less filament back'),
        E('retract_layer_change', 'retraction.on_layer_change', 'flag'),
        E('wipe', 'retraction.wipe', 'flag'),
        E('retract_before_wipe', 'retraction.before_wipe', 'number_strip_percent', note='percent of the retraction'),
        E('retract_lift_above', 'retraction.lift_above'),
        E('retract_lift_below', 'retraction.lift_below'),
        E('use_firmware_retraction', 'retraction.firmware', 'flag'),
        E('retract_length_toolchange', 'retraction.toolchange_length', 'numbers', note='one per extruder'),
        E('retract_restart_extra_toolchange', 'retraction.toolchange_restart_extra', 'numbers',
          note='one per extruder; negative: less filament back'),
        E('z_offset', 'machine.z_offset'),
        E('silent_mode', 'machine.silent_mode', 'flag'),
        E('single_extruder_multi_material', 'machine.single_extruder_mmu', 'flag'),
        E(['extruder_offset'], 'machine.extruders, machine.nozzle_diameter, machine.extruder_offset', 'rule',
          rule='extruders', group='translated', used='written',
          note='as many extruders as nozzle_diameter has values (PrusaSlicer counts them so); the nozzles as a list '
               'when they differ; the offsets when one is not 0'),
        E('machine_limits_usage', 'machine.limits_usage', 'map',
          values={'emit_to_gcode': 'emit', 'time_estimate_only': 'time_only', 'ignore': 'ignore'}),
        E('max_layer_height', 'machine.max_layer_height', note='caps the variable layer height and the support layers'),
        E('min_layer_height', 'machine.min_layer_height', note='caps the variable layer height and the support layers'),
        E('machine_max_acceleration_x', 'machine.max_accel_x', positive=True,
          note='the normal mode (the first value); not written when 0 (no limit)'),
        E('machine_max_acceleration_y', 'machine.max_accel_y', positive=True,
          note='the normal mode (the first value); not written when 0 (no limit)'),
        E('machine_max_acceleration_z', 'machine.max_accel_z', positive=True,
          note='the normal mode (the first value); not written when 0 (no limit)'),
        E('machine_max_acceleration_e', 'machine.max_accel_e', positive=True,
          note='the normal mode (the first value); not written when 0 (no limit)'),
        E('machine_max_acceleration_retracting', 'machine.retract_acceleration',
          note='the normal mode (the first value)'),
        E('machine_max_jerk_y', 'machine.jerk_y', note='the normal mode (the first value)'),
        E('machine_max_jerk_z', 'machine.jerk_z', note='the normal mode (the first value)'),
        E('machine_max_jerk_e', 'machine.jerk_e', note='the normal mode (the first value)'),
        E('machine_min_extruding_rate', 'machine.min_extrude_feed', note='the normal mode (the first value)'),
        E('machine_min_travel_rate', 'machine.min_travel_feed', note='the normal mode (the first value)'),
        E(['machine_max_junction_deviation', 'gcode_flavor'], 'machine.junction_deviation', 'rule',
          rule='junction_deviation', note='the normal mode (the first value); only with marlin2, the one flavor '
                                         'the source programs send it to (M205 J), else they use the jerk'),
        E('travel_ramping_lift', 'travel.ramping_lift', 'flag'),
        E('travel_slope', 'travel.slope', note='the first extruder\'s'),
        E('travel_max_lift', 'travel.max_lift', note='the first extruder\'s; 0: the lift'),
        E('travel_lift_before_obstacle', 'travel.lift_before_obstacle', 'flag'),
        E(['thumbnails', 'thumbnails_format'], 'gcode.thumbnails', 'rule', rule='thumbnails',
          note='"WxH/FORMAT" list; a size without a format takes thumbnails_format'),
        E('binary_gcode', 'gcode.binary', 'flag'),
        E('remaining_times', 'gcode.progress', 'flag'),
        E('autoemit_temperature_commands', 'gcode.auto_temperatures', 'flag'),
        E('use_volumetric_e', 'gcode.volumetric_e', 'flag'),
        E('cooling_tube_length', 'mmu.cooling_tube_length'),
        E('cooling_tube_retraction', 'mmu.cooling_tube_position'),
        E('parking_pos_retraction', 'mmu.parking_position'),
        E('extra_loading_move', 'mmu.extra_loading_move'),
        E('high_current_on_filament_swap', 'mmu.high_current_on_swap', 'flag'),
        E('extruder_clearance_height', 'sequential.clearance_height'),
        E('extruder_clearance_radius', 'sequential.clearance_radius'),
    ],
    'filament': [
        E('filament_diameter', 'machine.filament_diameter'),
    ] + [E(k, 'machine.variables.' + k, 'first_item', note='text of the first extruder, for the G-code')
         for k in FILAMENT_VARIABLES] + [
        E('chamber_temperature', 'extrusion.chamber_temperature', nonzero=True, used='never',
          note='also a variable (above); not written when 0'),
        E(['cooling', 'fan_always_on', 'min_fan_speed', 'max_fan_speed'], 'cooling.fan_min, cooling.fan_max', 'rule',
          rule='fans', note='cooling off and fan not always on: both 0; else min_fan_speed and max_fan_speed'),
        E('slowdown_below_layer_time', 'cooling.min_layer_time'),
        E('min_print_speed', 'cooling.min_speed', positive=True),
        E('disable_fan_first_layers', 'cooling.fan_off_layers'),
        E('extrusion_multiplier', 'extrusion.flow', 'factor', factor=100, note='times 100 (percent)'),
        E('filament_max_volumetric_speed', 'extrusion.max_flow'),
        E('filament_abrasive', 'extrusion.abrasive', 'flag'),
        E('fan_below_layer_time', 'cooling.fan_below_time'),
        E('bridge_fan_speed', 'cooling.fan_bridges'),
        E('full_fan_speed_layer', 'cooling.full_fan_layer'),
        E('cooling_slowdown_logic', 'cooling.slowdown_logic', 'map',
          values={'uniform_cooling': 'uniform', 'consistent_surface': 'consistent_surface'}),
        E('cooling_perimeter_transition_distance', 'cooling.transition_distance'),
        E('filament_density', 'extrusion.density'),
        E('filament_cost', 'extrusion.cost'),
        E('filament_spool_weight', 'extrusion.spool_weight'),
        E('filament_type', 'extrusion.type', 'first_item'),
        E('filament_minimal_purge_on_wipe_tower', 'extrusion.min_purge_on_tower'),
        E('filament_infill_max_speed', 'extrusion.infill_max_speed'),
        E('filament_infill_max_crossing_speed', 'extrusion.infill_max_crossing_speed'),
        E('filament_loading_speed', 'extrusion.loading_speed', note='0: not used'),
        E('filament_loading_speed_start', 'extrusion.loading_speed_start', note='0: not used'),
        E('filament_unloading_speed', 'extrusion.unloading_speed', note='0: not used'),
        E('filament_unloading_speed_start', 'extrusion.unloading_speed_start', note='0: not used'),
        E('filament_cooling_moves', 'extrusion.cooling_moves'),
        E('filament_cooling_initial_speed', 'extrusion.cooling_initial_speed', note='0: not used'),
        E('filament_cooling_final_speed', 'extrusion.cooling_final_speed', note='0: not used'),
        E('filament_toolchange_delay', 'extrusion.toolchange_delay'),
        E('filament_load_time', 'extrusion.load_time'),
        E('filament_unload_time', 'extrusion.unload_time'),
        E('cooling', 'cooling.enabled', 'flag', note='the automatic cooling (slowdown and fan by layer time)'),
        E('fan_always_on', 'cooling.fan_always', 'flag'),
        E('enable_dynamic_fan_speeds', 'cooling.dynamic_overhang_fan', 'flag'),
        E('overhang_fan_speed_0', 'cooling.overhang_fan_0'),
        E('overhang_fan_speed_1', 'cooling.overhang_fan_1'),
        E('overhang_fan_speed_2', 'cooling.overhang_fan_2'),
        E('overhang_fan_speed_3', 'cooling.overhang_fan_3'),
        E('filament_shrinkage_compensation_xy', 'extrusion.shrinkage_xy', 'number_strip_percent', nonnegative=True,
          max=20, note=SHRINKAGE),
        E('filament_shrinkage_compensation_z', 'extrusion.shrinkage_z', 'number_strip_percent', nonnegative=True,
          max=20, note=SHRINKAGE),
        E('chamber_minimal_temperature', 'extrusion.chamber_min_temperature'),
        E('filament_purge_multiplier', 'extrusion.purge_multiplier', 'number_strip_percent', note='percent'),
        E('filament_ramming_parameters', 'extrusion.ramming', 'rule', rule='ramming', group='similar',
          note='the flows of each quarter second (mm3/s); the source\'s line width and step multipliers (the first '
               'two numbers) and its multi-tool part (after "|") are not used'),
        E(['filament_' + k for k in FILAMENT_OVERRIDES], 'extrusion.retraction, extrusion.travel', 'rule',
          rule='filament_overrides', note='the filament\'s own retraction and travel values; "nil": the printer\'s'),
    ],
    'print': [
        E('layer_height', 'layers.height'),
        E('first_layer_height', 'layers.first_height', 'percent_of', base='layers.height'),
        E('slice_closing_radius', 'slicing.gap_closing_radius'),
        E('xy_size_compensation', 'slicing.xy_offset'),
        E('elefant_foot_compensation', 'slicing.first_layer_shrink'),
        E('perimeters', 'walls.count'),
        E(['perimeter_extrusion_width', 'extrusion_width'], 'walls.width', 'rule', rule='wall_width',
          group='similar', note='the first one given, a percent of the layer height (as the source computes it); '
                                'else 1.125 times the nozzle'),
        E('seam_position', 'walls.seam', 'map', values=SEAMS),
        E('top_solid_layers', 'surfaces.top_layers'),
        E('bottom_solid_layers', 'surfaces.bottom_layers'),
        E('top_solid_min_thickness', 'surfaces.top_min_thickness'),
        E('bottom_solid_min_thickness', 'surfaces.bottom_min_thickness'),
        E('top_fill_pattern', 'surfaces.top_pattern', 'map', values=SURFACE_PATTERNS),
        E('bottom_fill_pattern', 'surfaces.bottom_pattern', 'map', values=SURFACE_PATTERNS),
        E('fill_density', 'infill.density', 'number_strip_percent'),
        E('fill_angle', 'infill.angle'),
        E('fill_pattern', 'infill.pattern', 'map', values=PATTERNS, exclude=['monotonic'], used='written'),
        E('infill_every_layers', 'infill.combine_layers', 'at_least', min=1),
        E('solid_infill_every_layers', 'infill.solid_every'),
        E('solid_infill_below_area', 'infill.solid_below_area'),
        E('perimeter_speed', 'speed.walls'),
        E('external_perimeter_speed', 'speed.outer_wall', 'number_or_percent', used='written',
          note='"N%" stays a percent of the wall speed'),
        E('infill_speed', 'speed.infill'),
        E('solid_infill_speed', 'speed.solid_infill', 'percent_of', base='speed.infill'),
        E('top_solid_infill_speed', 'speed.top_solid_infill', 'percent_of', base='speed.solid_infill'),
        E('support_material_speed', 'speed.support'),
        E('travel_speed', 'speed.travel'),
        E('first_layer_speed', 'speed.first_layer', 'number_or_percent',
          note='mm/s for every extrusion of the first layer, or "N%" of each extrusion\'s speed (as the source)'),
        E(['perimeter_speed', 'infill_speed', 'solid_infill_speed', 'support_material_speed'], 'speed.max', 'rule',
          rule='fastest', used='never', note='the fastest of these speeds'),
        E('skirts', 'adhesion.skirt_loops'),
        E('skirt_distance', 'adhesion.skirt_distance'),
        E('skirt_height', 'adhesion.skirt_layers'),
        E('brim_width', 'adhesion.brim_width'),
        E('support_material', 'support.enabled', 'flag'),
        E('support_material_threshold', 'support.threshold_angle'),
        E('support_material_contact_distance', 'support.z_gap'),
        E('support_material_xy_spacing', 'support.xy_gap', 'rule', rule='xy_gap',
          note='in mm; "N%" of the outer wall width as the source computes it (external_perimeter_extrusion_width, '
               'else extrusion_width, a percent of the layer height; else 1.125 times the nozzle); for any nozzle and '
               'no width, "N%" of the automatic walls.width'),
        E('support_material_spacing', 'support.spacing'),
        E('support_material_interface_layers', 'support.interface_layers'),
        E('support_material_bottom_interface_layers', 'support.bottom_interface_layers',
          note='-1: as the top interface'),
        E('support_material_interface_spacing', 'support.interface_spacing'),
        E('support_material_buildplate_only', 'support.buildplate_only', 'flag'),
        E('support_material_auto', 'support.automatic', 'flag'),
        E('support_material_interface_speed', 'speed.support_interface', 'number_or_percent',
          note='"N%" of the support speed'),
        E('bridge_speed', 'speed.bridges', nonzero=True),
        E('gap_fill_speed', 'speed.gap_fill, walls.gap_fill', 'rule', rule='gap_fill',
          note='0: no gap fill (walls.gap_fill false)'),
        E('small_perimeter_speed', 'speed.small_loops', 'number_or_percent', nonzero=True,
          note='"N%" of the wall speed; 0: automatic, not written'),
        E('first_layer_infill_speed', 'speed.first_layer_infill', 'number_or_percent', nonzero=True,
          note='"N%" of the solid infill speed; 0: the first layer speed, not written'),
        E('first_layer_extrusion_width', 'layers.first_line_width', 'number_or_percent',
          note='"N%" of the first layer height; 0: as the other layers'),
        E('external_perimeter_extrusion_width', 'walls.outer_width', 'width_of_layer', group='similar', used='written',
          note='in mm; "N%" of the layer height, as the source computes it; 0: automatic'),
        E('bridge_flow_ratio', 'extrusion.bridge_flow_ratio'),
        E('external_perimeters_first', 'walls.outer_first', 'flag'),
        E('avoid_crossing_perimeters', 'travel.avoid_crossing_walls', 'flag'),
        E('avoid_crossing_perimeters_max_detour', 'travel.max_detour', 'number_or_percent',
          note='"N%" of the straight travel'),
        E('raft_layers', 'adhesion.raft_layers'),
        E('brim_separation', 'adhesion.brim_gap'),
        E('spiral_vase', 'vase.enabled', 'flag'),
        E('wipe_tower', 'wipe_tower.enabled', 'flag'),
        E('wipe_tower_width', 'wipe_tower.width'),
        E('default_acceleration', 'acceleration.default'),
        E('perimeter_acceleration', 'acceleration.walls'),
        E('external_perimeter_acceleration', 'acceleration.outer_wall'),
        E('infill_acceleration', 'acceleration.infill'),
        E('solid_infill_acceleration', 'acceleration.solid_infill'),
        E('top_solid_infill_acceleration', 'acceleration.top_solid_infill'),
        E('bridge_acceleration', 'acceleration.bridges'),
        E('first_layer_acceleration', 'acceleration.first_layer'),
        E('travel_acceleration', 'acceleration.travel'),
        E('wipe_tower_acceleration', 'acceleration.wipe_tower'),
        E('ironing', 'ironing.enabled', 'flag'),
        E('ironing_type', 'ironing.surfaces', 'map', values={'top': 'top', 'topmost': 'topmost', 'solid': 'solid'}),
        E('ironing_flowrate', 'ironing.flow', 'number_strip_percent', note='percent of a normal layer'),
        E('ironing_spacing', 'ironing.spacing'),
        E('ironing_speed', 'ironing.speed'),
        # Line widths of a role: 0 takes extrusion_width, and both 0 the source's automatic width (Flow.cpp); "N%" is of
        # the layer height. Written in mm; the automatic width only where the engine's own 0 differs from it.
        E(['infill_extrusion_width', 'extrusion_width'], 'infill.width', 'rule', rule='role_width', auto=None,
          note='in mm ("N%" of the layer height); 0: extrusion_width; both 0: the engine\'s 1.125 times the nozzle, '
               'as the source'),
        E(['solid_infill_extrusion_width', 'extrusion_width'], 'surfaces.solid_width', 'rule', rule='role_width',
          auto=None, note='as infill.width'),
        E(['top_infill_extrusion_width', 'extrusion_width'], 'surfaces.top_width', 'rule', rule='role_width',
          auto=None, note='as infill.width; both 0: the nozzle, the engine\'s and the source\'s'),
        E(['support_material_extrusion_width', 'extrusion_width'], 'support.width', 'rule', rule='role_width',
          auto=1.0, note='as infill.width; both 0: the nozzle (the source\'s automatic support width; the engine\'s '
                         '0 is walls.width), not written for a print of any nozzle'),
        E('bridge_angle', 'surfaces.bridge_angle', note='0: each bridge\'s own'),
        E('interface_shells', 'surfaces.interface_shells', 'flag'),
        E('infill_first', 'infill.before_walls', 'flag'),
        E('infill_anchor_max', 'infill.max_link', 'absolute_only', group='similar',
          note='mm only; the source\'s 0 (no anchors) and "N%" are not written; the engine has no minimum anchor'),
        E('infill_overlap', 'infill.wall_overlap', 'percent_only', group='similar',
          note='"N%" only; the engine uses it for the solid lines that are not joined'),
        E('perimeter_generator', 'walls.generator', 'map', values={'arachne': 'variable', 'classic': 'fixed'}),
        E('overhangs', 'walls.detect_overhangs', 'flag'),
        E('extra_perimeters', 'walls.extra_if_needed', 'flag'),
        E('extra_perimeters_on_overhangs', 'walls.extra_on_overhangs', 'flag'),
        E('wall_transition_angle', 'walls.transition_angle'),
        E('wall_transition_length', 'walls.transition_length', 'number_or_percent',
          bare_percent_over=10, note=BARE_PERCENT),
        E('wall_transition_filter_deviation', 'walls.transition_margin', 'number_or_percent',
          bare_percent_over=10, note=BARE_PERCENT),
        E('wall_distribution_count', 'walls.spread_count'),
        E('min_bead_width', 'walls.min_line_width', 'number_or_percent',
          bare_percent_over=10, note=BARE_PERCENT),
        E('min_feature_size', 'walls.min_detail', 'number_or_percent',
          bare_percent_over=10, note=BARE_PERCENT),
        E('seam_gap', 'walls.seam_gap', 'number_or_percent', note='"N%" of the nozzle'),
        E('staggered_inner_seams', 'walls.staggered_inner_seams', 'flag'),
        E('avoid_crossing_curled_overhangs', 'walls.avoid_curled_overhangs', 'flag'),
        E('top_one_perimeter_type', 'walls.top_one_wall', 'map',
          values={'none': 'none', 'top': 'top', 'topmost': 'topmost'}),
        E('only_one_perimeter_first_layer', 'walls.first_layer_one_wall', 'flag'),
        E('scarf_seam_start_height', 'walls.scarf_start_height', 'percent_only', note='percent of the layer'),
        E('support_material_style', 'support.style', 'map',
          values={'grid': 'grid', 'snug': 'snug', 'organic': 'organic'}),
        E('support_material_pattern', 'support.pattern', 'map',
          values={'rectilinear': 'lines', 'rectilinear-grid': 'grid', 'honeycomb': 'honeycomb'}),
        E('support_material_interface_pattern', 'support.interface_pattern', 'map',
          values={'rectilinear': 'lines', 'concentric': 'concentric', 'auto': 'automatic'}),
        E('support_material_bottom_contact_distance', 'support.bottom_z_gap', note='0: as support.z_gap'),
        E('support_material_closing_radius', 'support.closing_radius'),
        E('support_material_enforce_layers', 'support.enforce_layers'),
        E('support_material_with_sheath', 'support.sheath', 'flag'),
        E('support_material_synchronize_layers', 'support.synchronize_layers', 'flag'),
        E('support_material_angle', 'support.line_angle'),
        E('support_material_interface_contact_loops', 'support.interface_contact_loops', 'flag'),
        E('support_tree_angle', 'support.tree_angle'),
        E('support_tree_angle_slow', 'support.tree_angle_preferred'),
        E('support_tree_branch_diameter', 'support.tree_branch_diameter'),
        E('support_tree_branch_diameter_angle', 'support.tree_branch_diameter_angle'),
        E('support_tree_branch_diameter_double_wall', 'support.tree_double_wall_diameter'),
        E('support_tree_branch_distance', 'support.tree_branch_distance'),
        E('support_tree_tip_diameter', 'support.tree_tip_diameter'),
        E('support_tree_top_rate', 'support.tree_top_rate', 'number_strip_percent'),
        E('brim_type', 'adhesion.brim_type', 'map',
          values={'outer_only': 'outer', 'inner_only': 'inner', 'outer_and_inner': 'outer_and_inner',
                  'no_brim': 'none'}),
        E('draft_shield', 'adhesion.draft_shield', 'map',
          values={'disabled': 'disabled', 'limited': 'limited', 'enabled': 'enabled', '0': 'disabled',
                  '1': 'enabled'}, note='"0" and "1": the older on/off form, as the source reads it'),
        E('raft_expansion', 'adhesion.raft_expansion'),
        E('raft_first_layer_density', 'adhesion.raft_first_layer_density', 'number_strip_percent'),
        E('raft_first_layer_expansion', 'adhesion.raft_first_layer_expansion'),
        E('raft_contact_distance', 'adhesion.raft_gap'),
        E('min_skirt_length', 'adhesion.skirt_min_filament'),
        E('fuzzy_skin', 'fuzzy.mode', 'map', values={'none': 'none', 'external': 'external', 'all': 'all'}),
        E('fuzzy_skin_thickness', 'fuzzy.thickness'),
        E('fuzzy_skin_point_dist', 'fuzzy.point_distance'),
        E('wipe_tower_x', 'wipe_tower.x'),
        E('wipe_tower_y', 'wipe_tower.y'),
        E('wipe_tower_rotation_angle', 'wipe_tower.rotation'),
        E('wipe_tower_brim_width', 'wipe_tower.brim_width'),
        E('wipe_tower_bridging', 'wipe_tower.bridging'),
        E('wipe_tower_no_sparse_layers', 'wipe_tower.no_sparse_layers', 'flag'),
        E('wipe_tower_extra_spacing', 'wipe_tower.extra_spacing', 'number_strip_percent', note='percent'),
        E('wipe_tower_extra_flow', 'wipe_tower.extra_flow', 'number_strip_percent', note='percent'),
        E('wipe_tower_cone_angle', 'wipe_tower.cone_angle'),
        E('travel_speed_z', 'speed.travel_z', nonzero=True, note='0: the travel speed, not written'),
        E('max_volumetric_speed', 'speed.max_flow', note='0: no limit'),
        E('enable_dynamic_overhang_speeds', 'speed.dynamic_overhangs', 'flag'),
        E('overhang_speed_0', 'speed.overhang_0', 'number_or_percent', nonzero=True,
          note='"N%" of the outer wall speed; 0 not written'),
        E('overhang_speed_1', 'speed.overhang_1', 'number_or_percent', nonzero=True, note='as overhang_0'),
        E('overhang_speed_2', 'speed.overhang_2', 'number_or_percent', nonzero=True, note='as overhang_0'),
        E('overhang_speed_3', 'speed.overhang_3', 'number_or_percent', nonzero=True, note='as overhang_0'),
        E('first_layer_speed_over_raft', 'speed.first_layer_over_raft', 'number_or_percent', nonzero=True,
          note='"N%" of each speed; 0 not written'),
        E('first_layer_acceleration_over_raft', 'acceleration.first_layer_over_raft', note='0: as each type'),
        E('gcode_label_objects', 'gcode.object_labels', 'map',
          values={'firmware': 'firmware', 'octoprint': 'octoprint', 'disabled': 'none', '1': 'octoprint',
                  '0': 'none'}, note='"1" and "0": the older on/off form, as the source reads it'),
        E('gcode_resolution', 'gcode.resolution'),
        E('ooze_prevention', 'extruders.ooze_prevention', 'flag'),
        E('standby_temperature_delta', 'extruders.standby_delta'),
        E('gcode_comments', 'gcode.verbose_comments', 'flag'),
        E('dont_support_bridges', 'support.under_bridges', 'flag', invert=True, note='the opposite'),
        E('slicing_mode', 'slicing.fill_mode', 'map',
          values={'regular': 'union', 'even_odd': 'even_odd', 'close_holes': 'fill_holes'}),
        E('max_volumetric_extrusion_rate_slope_positive', 'speed.flow_slope_up', note='0: off'),
        E('max_volumetric_extrusion_rate_slope_negative', 'speed.flow_slope_down', note='0: off'),
        E('arc_fitting', 'gcode.arcs', 'map', values={'emit_center': True, 'disabled': False}),
    ],
    'printer_sla': [
        E('display_pixels_x', 'machine.display_pixels_x'),
        E('display_pixels_y', 'machine.display_pixels_y'),
        E('display_width', 'machine.display_width'),
        E('display_height', 'machine.display_height'),
        E('display_mirror_x', 'machine.display_mirror_x', 'flag'),
        E('display_mirror_y', 'machine.display_mirror_y', 'flag'),
        E('max_print_height', 'machine.max_height'),
    ],
    'sla_material': [
        E('initial_layer_height', 'resin.first_layer_height',
          note='the height of the first layer (PrusaSlicer SLA); the other layers take the print\'s layer_height'),
        E('exposure_time', 'resin.exposure'),
        E('initial_exposure_time', 'resin.bottom_exposure'),
        E('material_correction', 'resin.scale_x, resin.scale_y, resin.scale_z', 'rule', rule='correction',
          note='material_correction_x/y/z, as PrusaSlicer scales (the list only switches it on)'),
        E('material_notes', ', '.join('resin.' + v for k, v in RESIN_NOTE_KEYS.items()
                                      if v not in ('bottom_retract_speed', 'bottom_wait_before_exposure')),
          'rule', rule='resin_notes', used='never', note='"NAME = number" lines of the notes (UVtools)'),
    ],
    'sla_print': [
        E('layer_height', 'resin.layer_height'),
        E('faded_layers', 'resin.bottom_layers'),
    ],
}


# ---------------------------------------------------------------------------------------------------------------------
# Applying the table

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


def put(settings, path, value):
    if value is None:
        return
    if isinstance(value, float):
        value = clean_num(value)
    parts = path.split('.')
    for p in parts[:-1]:
        settings = settings.setdefault(p, {})
    settings[parts[-1]] = value


def get(settings, path):
    for p in path.split('.'):
        if not isinstance(settings, dict) or p not in settings:
            return None
        settings = settings[p]
    return settings


def fix_point(p):
    """A bed point written '235-0' instead of '235x0' (a typo in one source bundle)."""
    p = p.strip()
    return p.replace('-', 'x', 1) if 'x' not in p and re.match(r'^\d+(\.\d+)?-\d+(\.\d+)?$', p) else p


def unescape(v):
    return v.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')


def _rule(name, e, c, s, ctx):
    """(written, used keys) of a rule."""
    if name == 'acceleration':
        acc = num(c.get('machine_max_acceleration_extruding'))
        if not acc:
            return False, ()
        put(s, 'machine.acceleration', acc)
        put(s, 'machine.travel_acceleration', num(c.get('machine_max_acceleration_travel')) or acc)
        return True, ('machine_max_acceleration_extruding', 'machine_max_acceleration_travel')
    if name == 'fans':
        if 'cooling' in c and not flag(c['cooling']) and not flag(c.get('fan_always_on', '0')):
            put(s, 'cooling.fan_min', 0)
            put(s, 'cooling.fan_max', 0)
            return True, ('cooling', 'fan_always_on')
        put(s, 'cooling.fan_min', num(c.get('min_fan_speed')))
        put(s, 'cooling.fan_max', num(c.get('max_fan_speed')))
        return True, ('min_fan_speed', 'max_fan_speed')
    if name == 'wall_width':
        # A percent is of the layer height, as the source program computes it (Flow.cpp: "extrusion width wrt. layer
        # height"); 0 is automatic.
        nozzle = ctx.get('nozzle')
        for key in e['from']:
            w = pct_or_abs(c.get(key), num(c.get('layer_height')))
            if w:
                put(s, 'walls.width', w)
                return True, (key,)
        if nozzle:
            put(s, 'walls.width', nozzle * 1.125)
        return True, ()
    if name == 'role_width':
        layer = num(c.get('layer_height'))
        for key in e['from']:
            w = pct_or_abs(c.get(key), layer)
            if w:
                put(s, e['to'], w)
                return True, (key,)
        nozzle = ctx.get('nozzle')
        if e.get('auto') and nozzle:
            put(s, e['to'], nozzle * e['auto'])
            return True, tuple(k for k in e['from'] if k in c)
        return bool(e['auto'] is None), tuple(k for k in e['from'] if k in c)
    if name == 'junction_deviation':
        if 'machine_max_junction_deviation' not in c:
            return False, ()
        if (c.get('gcode_flavor') or '').strip() != 'marlin2':
            return False, ('machine_max_junction_deviation',)
        put(s, 'machine.junction_deviation', num(c['machine_max_junction_deviation']))
        return True, ('machine_max_junction_deviation',)
    if name == 'thumbnails':
        v = (c.get('thumbnails') or '').strip().strip('"')
        if not v:
            return False, ()
        fmt = (c.get('thumbnails_format') or '').strip()
        items = [x.strip() for x in v.split(',') if x.strip()]
        if fmt:
            items = [x if '/' in x else x + '/' + fmt for x in items]
        put(s, 'gcode.thumbnails', ', '.join(items))
        return True, ('thumbnails',) + (('thumbnails_format',) if 'thumbnails_format' in c else ())
    if name == 'ramming':
        v = (c.get('filament_ramming_parameters') or '').strip().strip('"').split('|')[0].split()
        flows = [num(x) for x in v[2:]]
        if not flows or any(x is None for x in flows):
            return False, ()
        put(s, 'extrusion.ramming', [clean_num(x) for x in flows])
        return True, ('filament_ramming_parameters',)
    if name == 'filament_overrides':
        used = []
        for key, to in FILAMENT_OVERRIDES.items():
            v = (c.get('filament_' + key) or '').split(',')[0].strip()
            if not v or v == 'nil':
                continue
            if key in FLAG_OVERRIDES:
                value = flag(v)
            else:
                value = num(v.rstrip('%'))
                if value is None:
                    continue
            put(s, 'extrusion.' + to, value)
            used.append('filament_' + key)
        return bool(used), tuple(used)
    if name == 'xy_gap':
        v = (c.get('support_material_xy_spacing') or '').strip()
        if not v:
            return False, ()
        if not v.endswith('%'):
            put(s, 'support.xy_gap', num(v))
            return num(v) is not None, ('support_material_xy_spacing',)
        # The source program takes the percent of the outer wall's flow width (SupportParameters.cpp).
        width = None
        for key in ('external_perimeter_extrusion_width', 'extrusion_width'):
            width = pct_or_abs(c.get(key), num(c.get('layer_height')))
            if width:
                break
        nozzle = ctx.get('nozzle')
        if not width and not nozzle:
            # No width given and a profile for any nozzle: the automatic outer wall (1.125 times the nozzle) is the
            # engine's automatic walls.width, which a percent of support.xy_gap is of.
            put(s, 'support.xy_gap', v)
            return True, ('support_material_xy_spacing',)
        gap = pct_or_abs(v, width or 1.125 * nozzle)
        put(s, 'support.xy_gap', gap)
        return gap is not None, ('support_material_xy_spacing',)
    if name == 'extruders':
        nozzles = [num(x) for x in (c.get('nozzle_diameter') or '').split(',') if x.strip()]
        if len(nozzles) < 2 or any(x is None for x in nozzles):
            return False, ()
        put(s, 'machine.extruders', len(nozzles))
        if len(set(nozzles)) > 1:
            put(s, 'machine.nozzle_diameter', [clean_num(x) for x in nozzles])
        offsets = []
        for p in (c.get('extruder_offset') or '').split(','):
            m = re.match(r'\s*(-?[\d.]+)\s*x\s*(-?[\d.]+)', p)  # as PrusaSlicer reads a point (the rest ignored)
            if m:
                offsets.append([clean_num(float(m.group(1))), clean_num(float(m.group(2)))])
        if any(x or y for x, y in offsets) and not flag(c.get('single_extruder_multi_material', '0')):
            put(s, 'machine.extruder_offset', offsets)
        return True, ('extruder_offset',)
    if name == 'fastest':
        fastest = max([x for x in (get(s, 'speed.walls'), get(s, 'speed.infill'), get(s, 'speed.solid_infill'),
                                   num(c.get('support_material_speed'))) if x] or [0])
        if fastest:
            put(s, 'speed.max', fastest)
        return bool(fastest), ()
    if name == 'limits_usage':
        v = e['values'].get((c.get('machine_limits_usage') or '').strip())
        if v == 'emit' and (c.get('gcode_flavor') or '').strip() == 'klipper':
            v = None
        put(s, 'machine.limits_usage', v)
        return v is not None, ('machine_limits_usage',)
    if name == 'gap_fill':
        n = num(c.get('gap_fill_speed'))
        if n is None:
            return False, ('gap_fill_speed',)
        if n:
            put(s, 'speed.gap_fill', n)
        else:
            put(s, 'walls.gap_fill', False)
        return True, ('gap_fill_speed',)
    if name == 'correction':
        # PrusaSlicer scales by material_correction_x/y/z (SLAPrint::relative_correction: the list only has to have
        # two values or more); a bundle without them has the program's 1.
        corr = [x for x in c.get('material_correction', '').split(',') if x.strip()]
        axes = ['material_correction_' + a for a in 'xyz']
        if len(corr) < 2 and not any(k in c for k in axes):
            return False, ()
        for axis, k in zip('xyz', axes):
            v = num(c.get(k)) if k in c else 1
            put(s, 'resin.scale_' + axis, v if v else 1)
        return True, ('material_correction',) + tuple(k for k in axes if k in c)
    if name == 'resin_notes':
        notes = unescape((c.get('material_notes') or '').strip().strip('"'))
        for m in re.finditer(r'^\s*([A-Z_]+)\s*=\s*([-\d.]+)', notes, re.M):
            key = RESIN_NOTE_KEYS.get(m.group(1))
            if key and key not in ('bottom_retract_speed', 'bottom_wait_before_exposure'):
                put(s, 'resin.' + key, num(m.group(2)))
        return True, ()
    if name in ctx.get('rules', {}):
        return ctx['rules'][name](e, c, s)
    raise KeyError('no rule "%s"' % name)


def value_of(e, c, s):
    """The engine value of a plain entry, or None."""
    how, key = e['how'], e['from']
    v = c.get(key)
    if how == 'number':
        n = num(v)
        if e.get('nonzero') and not n:
            return None
        if e.get('nonnegative') and n is not None and n < 0:
            return None
        if e.get('max') is not None and n is not None and n > e['max']:
            return None
        if e.get('positive') and not (n and n > 0):
            return None
        return n
    if how == 'flag':
        if key not in c:
            return None
        return flag(str(v).split(',')[0]) != bool(e.get('invert'))  # the first extruder's
    if how == 'numbers':
        items = [num(x) for x in str(v).split(',')] if v not in (None, '') else []
        if not items or any(x is None for x in items) or (e.get('nonnegative') and any(x < 0 for x in items)):
            return None
        return [clean_num(x) for x in items]
    if how == 'factor':
        n = num(v)
        return n * e['factor'] if n else None
    if how == 'map':
        out = e['values'].get((v or '').strip())
        if out is None or (e.get('only') and out not in e['only']) or out in e.get('exclude', ()):
            return None
        return out
    if how == 'percent_of':
        return pct_or_abs(v, get(s, e['base']))
    if how == 'first_item':
        return first_text(v) if key in c else None
    if how == 'number_strip_percent':
        n = num(str(v if v is not None else '').rstrip('%'))
        if n is not None and ((e.get('nonnegative') and n < 0) or (e.get('max') is not None and n > e['max'])):
            return None
        return n
    if how == 'number_or_percent':
        if not v:
            return None
        if e.get('nonzero') and not num(v.rstrip('%')):
            return None
        if not v.endswith('%') and e.get('bare_percent_over') is not None and (num(v) or 0) > e['bare_percent_over']:
            return v.strip() + '%'
        return v if v.endswith('%') else num(v)
    if how == 'width_of_layer':
        # A line width: "N%" of the layer height (the source program's Flow.cpp); 0 or nothing is not written.
        w = pct_or_abs(v, num(c.get('layer_height'))) if v else None
        return w or None
    if how == 'percent_only':
        return num(v.strip()[:-1]) if v and v.strip().endswith('%') else None
    if how == 'absolute_only':
        return num(v) if v and not v.endswith('%') else None
    if how == 'at_least':
        n = num(v)
        return n if n and n >= e['min'] else None
    if how == 'points':
        pts = []
        for p in (v or '').split(','):
            p = fix_point(p)
            if 'x' in p:
                x, y = p.split('x', 1)
                if num(x) is not None and num(y) is not None:
                    pts.append([clean_num(num(x)), clean_num(num(y))])
        return pts if len(pts) >= 3 else None
    raise KeyError('no conversion "%s"' % how)


def translate(kind, c, nozzle=None, rules=None):
    """(engine settings, source keys used) of a source config of a kind (TABLE)."""
    s = {}
    used = set()
    ctx = {'nozzle': nozzle, 'rules': rules or {}}
    for e in TABLE[kind]:
        if e['how'] == 'rule':
            written, keys = _rule(e['rule'], e, c, s, ctx)
            used.update(keys)
            continue
        v = value_of(e, c, s)
        put(s, e['to'], v)
        mode = e.get('used', 'present' if e['how'] in ('flag', 'first_item') else 'always')
        if mode == 'always' or (mode == 'written' and v is not None) or (mode == 'present' and e['from'] in c):
            used.add(e['from'])
    return s, used


KIND_NAMES = {'printer': 'printer', 'filament': 'filament', 'print': 'print', 'printer_sla': 'resin_printer',
              'sla_material': 'resin', 'sla_print': 'resin_print'}


def table_json(dialect, keys_seen, renames=None, source=None):
    """The translation table of a dialect as the pack ships it (docs/FORMAT.md, «Traducción de claves»).
    keys_seen: {kind: source keys}; renames: {kind: {source key: (PrusaSlicer key, presets agreeing, presets)}}
    for the dialects other than prusaslicer."""
    by_key = {}
    for kind, entries in TABLE.items():
        for e in entries:
            srcs = e['from'] if isinstance(e['from'], list) else [e['from']]
            for src in srcs:
                by_key.setdefault((kind, src), (e, srcs))
    out = {'format': 'tisma-pack-translation', 'version': FORMAT_VERSION, 'dialect': dialect, 'kinds': {}}
    if source:
        out['source'] = source
    for kind in TABLE:
        if kind not in keys_seen:
            continue
        rows = {}
        for key in sorted(keys_seen[kind]):
            if renames is None:
                p, seen, values = key, None, None
            else:
                hit = renames.get(kind, {}).get(key)
                p, seen = (hit[0], list(hit[1:3])) if hit else (None, None)
                values = hit[3] if hit and len(hit) > 3 else None
            row = {}
            if p in (None,) or (kind, p) not in by_key:
                row = {'engine': None, 'group': 'none'}
            else:
                e, srcs = by_key[(kind, p)]
                row = {'engine': e['to'], 'group': e['group'],
                       'conversion': {k: v for k, v in e.items() if k not in ('from', 'to', 'group', 'note', 'used')}}
                if e.get('note'):
                    row['note'] = e['note']
                if len(srcs) > 1:
                    row['with'] = [x for x in srcs if x != p]
            if renames is not None:
                row['prusaslicer'] = p
                if seen:
                    row['seen'] = seen
                if values:
                    row['prusaslicer_values'] = values  # the source value -> the PrusaSlicer value
            rows[key] = row
        out['kinds'][KIND_NAMES[kind]] = rows
    return out


# ---------------------------------------------------------------------------------------------------------------------
# The other dialects: their names for the PrusaSlicer keys, as Tisma Slicer's bundles show them

def _norm(v):
    """A value as a tuple of plain texts, to compare a source program's value with the bundle's."""
    if isinstance(v, bool):
        v = '1' if v else '0'
    if isinstance(v, (list, tuple)):
        items = [str(x) for x in v]
    else:
        text = unescape(str(v).strip().strip('"'))
        items = re.split(r'\s*[;,]\s*', text) if ('\n' not in text) else [text]
    out = []
    for x in items:
        x = x.strip().strip('"')
        if x in ('true', 'True'):
            x = '1'
        elif x in ('false', 'False'):
            x = '0'
        try:
            f = float(x)
            x = repr(clean_num(f))
        except ValueError:
            pass
        out.append(x)
    while len(out) > 1 and out[-1] == out[0] and len(set(out)) == 1:
        out.pop()  # "0.4,0.4" (one per extruder) is "0.4"
    return tuple(out)


WORD_VALUE = re.compile(r'^[a-z][A-Za-z0-9_-]{0,39}$')  # an option's value: one lowercase word, not a number or a name


class Renames:
    """Pairs of (the source program's preset values, the bundle's resolved section) of the same preset; renames()
    gives, per kind, the source key whose value the bundle has under another (or the same) name in nearly every
    preset."""

    def __init__(self):
        self.samples = {}  # (dialect, kind) -> [(source values, bundle values)]

    def add(self, dialect, kind, source_values, bundle_values):
        self.samples.setdefault((dialect, kind), []).append((source_values, bundle_values))

    def renames(self, dialect, kind, min_presets=5, agreement=0.9, informative=3):
        """{source key: (PrusaSlicer key, presets agreeing, presets)}. A key keeps its own name when the bundle has
        it with the same value. Another name needs the same value in at least `agreement` of the presets, and also in
        the presets where the value is not its most common one (at least `informative` of them, with the same
        agreement), so that two keys that are mostly 0 or 1 are not taken for each other. Each PrusaSlicer key goes
        to one source key, the one that agrees most often where the value says something."""
        pairs = self.samples.get((dialect, kind), [])
        seen = {}  # source key -> [(value, PrusaSlicer keys with that value)]
        for src, dst in pairs:
            by_value = {}
            for k, v in dst.items():
                if k != 'inherits':
                    by_value.setdefault(_norm(v), set()).add(k)
            for k, v in src.items():
                if isinstance(v, dict):
                    continue
                nv = _norm(v)
                seen.setdefault(k, []).append((nv, by_value.get(nv, set())))
        chosen = {}
        for k, rows in seen.items():
            n = len(rows)
            if n < min_presets:
                continue
            counts = {}
            for nv, _ in rows:
                counts[nv] = counts.get(nv, 0) + 1
            mode = max(counts, key=counts.get)
            minority = [m for nv, m in rows if nv != mode]
            total, info = {}, {}
            for nv, m in rows:
                for p in m:
                    total[p] = total.get(p, 0) + 1
            for m in minority:
                for p in m:
                    info[p] = info.get(p, 0) + 1
            if total.get(k, 0) >= agreement * n:
                chosen[k] = (k, total[k], n, info.get(k, 0))
                continue
            if len(minority) < informative:
                continue
            best = sorted(info.items(), key=lambda x: (-x[1], -total.get(x[0], 0), x[0]))
            if not best:
                continue
            p, hits = best[0]
            if hits < agreement * len(minority) or total.get(p, 0) < agreement * n:
                continue
            if len(best) > 1 and best[1][1] == hits and total.get(best[1][0], 0) == total.get(p, 0):
                continue  # two PrusaSlicer keys agree as well: not known which one
            chosen[k] = (p, total[p], n, hits)
        out = {}
        for k, (p, hits, n, info) in sorted(chosen.items(), key=lambda x: (-(x[1][0] == x[0]), -x[1][3], x[0])):
            if p != k and any(v[0] == p for v in out.values()):
                continue
            out[k] = (p, hits, n)
        for k, (p, hits, n) in list(out.items()):
            if p == k:
                values = self._own_value_names(pairs, k, agreement)
                if values:
                    out[k] = (p, hits, n, values)
        out.update(self._value_maps(pairs, set(out), {v[0] for v in out.values()}, min_presets, agreement))
        return out

    @staticmethod
    def _own_value_names(pairs, key, agreement, min_hits=2):
        """For a key with the same name in the bundle: {source value: PrusaSlicer value} when some of its one-word
        values have another name there (OrcaSlicer's seam "back" is PrusaSlicer's "rear"), each seen with the same
        bundle value in at least `agreement` of its presets and `min_hits` of them; None when every value keeps its
        name."""
        table = {}
        for src, dst in pairs:
            if key not in src or key not in dst or isinstance(src[key], dict):
                continue
            sv, dv = _norm(src[key]), _norm(dst[key])
            if len(sv) != 1 or len(dv) != 1 or not WORD_VALUE.match(sv[0]) or not WORD_VALUE.match(dv[0]):
                continue
            table.setdefault(sv[0], {}).setdefault(dv[0], 0)
            table[sv[0]][dv[0]] += 1
        mapping = {}
        for sv, t in table.items():
            dv = max(t, key=lambda x: (t[x], x == sv))
            if t[dv] >= min_hits and t[dv] >= agreement * sum(t.values()):
                mapping[sv] = dv
        if all(a == b for a, b in mapping.items()):
            return None
        return dict(sorted(mapping.items()))

    @staticmethod
    def _value_maps(pairs, done_src, done_dst, min_presets, agreement, min_values=3, max_values=40):
        """Keys whose values the bundle renamed too ("zig-zag" -> "zigzag"): a source key and a PrusaSlicer key with
        at least `min_values` values each, where each source value always comes with the same bundle value.
        {source key: (PrusaSlicer key, presets agreeing, presets, {source value: bundle value})}."""
        joint = {}  # (source key, bundle key) -> {source value: {bundle value: count}}
        present = {}
        for src, dst in pairs:
            d = {k: _norm(v) for k, v in dst.items() if k not in done_dst and k != 'inherits'}
            d = {k: v for k, v in d.items() if len(v) == 1 and WORD_VALUE.match(v[0])}
            for k, v in src.items():
                if k in done_src or isinstance(v, (dict, list)):
                    continue
                nv = _norm(v)
                if len(nv) != 1 or not WORD_VALUE.match(nv[0]):
                    continue  # one word: a number that follows another, or a name, is no rename of its values
                present[k] = present.get(k, 0) + 1
                for p, pv in d.items():
                    joint.setdefault((k, p), {}).setdefault(nv[0], {})
                    joint[(k, p)][nv[0]][pv[0]] = joint[(k, p)][nv[0]].get(pv[0], 0) + 1
        best = {}
        for (k, p), table in joint.items():
            n = present[k]
            if n < min_presets or len(table) < min_values:
                continue
            mapping = {sv: max(t, key=t.get) for sv, t in table.items()}
            if len(set(mapping.values())) < max(min_values, 0.7 * len(mapping)) or len(table) > max_values or \
                    all(a == b for a, b in mapping.items()):
                continue
            hits = sum(table[sv][mapping[sv]] for sv in table)
            if hits < agreement * n:
                continue
            if k not in best or hits > best[k][1]:
                best[k] = (p, hits, n, dict(sorted(mapping.items())))
        out = {}
        for k, v in sorted(best.items(), key=lambda x: -x[1][1]):
            if not any(o[0] == v[0] for o in out.values()):
                out[k] = v
        return out


# ---------------------------------------------------------------------------------------------------------------------
# Values of a PrusaSlicer-format section with the types PrusaSlicer gives them (its PrintConfig.cpp)

def option_types(print_config_cpp):
    """{key: coType} of a PrintConfig.cpp (this->add("key", coType), and the per-axis machine limits)."""
    text = open(print_config_cpp, encoding='utf-8', errors='replace').read()
    out = {m.group(1): m.group(2) for m in re.finditer(r'this->add(?:_nullable)?\("(\w+)",\s*(co\w+)\)', text)}
    for m in re.finditer(r'this->add\("(\w+_)"\s*\+\s*axis\.name,\s*(co\w+)\)', text):
        for axis in 'xyze':
            out.setdefault(m.group(1) + axis, m.group(2))
    return out


def first_text(text):
    """The first item of a PrusaSlicer list, as the program holds it: without the quotes the bundle may write
    ("PLA";"PETG" is PLA)."""
    text = (text or '').strip()
    if text.startswith('"'):
        items = _strings(text)
        return items[0] if items else ''
    return text.split(',')[0].strip()


def _strings(text):
    """A PrusaSlicer list of texts: "a";"b" (or a;b, or a,b without quotes)."""
    if '"' in text:
        return [unescape(x) for x in re.findall(r'"((?:\\.|[^"\\])*)"', text)]
    return [x.strip() for x in re.split(r'[;,]', text)] if text else []


def typed(value, kind):
    """A bundle value (text) as PrusaSlicer holds it, for a coType; the text when the type is not known."""
    v = value.strip()
    scalar = {'coFloat': float, 'coInt': int}

    def number(x):
        x = x.strip()
        if x.endswith('%'):
            return x
        n = num(x)
        return clean_num(n) if n is not None else x
    if kind == 'coBool':
        return flag(v)
    if kind == 'coBools':
        return [flag(x) for x in v.split(',')] if v else []
    if kind in scalar or kind in ('coPercent', 'coFloatOrPercent'):
        return number(v)
    if kind in ('coFloats', 'coInts', 'coPercents', 'coFloatsOrPercents'):
        return [number(x) for x in v.split(',')] if v else []
    if kind == 'coStrings':
        return _strings(v)
    if kind in ('coString', 'coEnum'):
        return unescape(v[1:-1] if len(v) >= 2 and v[0] == v[-1] == '"' else v)
    if kind == 'coPoints':
        return [p.strip() for p in v.split(',')] if v else []
    return unescape(v[1:-1] if len(v) >= 2 and v[0] == v[-1] == '"' else v)
