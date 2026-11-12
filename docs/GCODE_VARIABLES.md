# Variables del G-code de las máquinas

Cada variable que usan los G-code de `gcode.templates` del paquete (`docs/FORMAT.md`, «G-code de la máquina»), por dialecto, contada en el paquete convertido. Lo genera `tools/gcode_variables.py`: no se escribe a mano.

- **Tipo** y **qué es:** como los define el programa de origen (el nombre que muestra, en inglés). Vacío si sus definiciones no la tienen: la llena el programa al laminar o la define el firmware.
- **Dónde:** en qué G-code aparece y en cuántas variantes.
- **En PrusaSlicer:** el mismo nombre si PrusaSlicer lo tiene, o el que le pone Tisma Slicer al convertir (el mismo G-code en su paquete). Vacío si ninguno lo dice.
- **Propia de la macro:** la asigna el G-code mismo (`local` o `global`).

Definiciones: Tisma Slicer a6b4f62 (PrusaSlicer), OrcaSlicer 1d577ea, Creality Print 59ae8cb, Elegoo Slicer 2d507e3, UltiMaker Cura 5bea2f8, VertexSlice 1d6ad28.

## `prusaslicer`

104 variables.

| Variable | Tipo | Dónde | Qué es | En PrusaSlicer |
|---|---|---|---|---|
| `first_layer_temperature` | lista de enteros | `start`, `toolchange` (1031) | First layer nozzle temperature | `first_layer_temperature` |
| `first_layer_bed_temperature` | lista de enteros | `start` (1022) | First layer bed temperature | `first_layer_bed_temperature` |
| `layer_z` | número | `layer_change`, `before_layer_change`, `end`, `toolchange` (960) | Height of the current layer above the print bed, measured to the top of the layer | `layer_z` |
| `max_layer_z` | número | `end` (600) | Maximal layer Z | `max_layer_z` |
| `max_print_height` | número | `end`, `start` (549) | Max print height | `max_print_height` |
| `z_offset` | número | `end` (521) | Z offset | `z_offset` |
| `print_bed_max` | lista de números | `start`, `end` (411) | Top-right corner of print bed bounding box | `print_bed_max` |
| `travel_speed` | número | `start`, `end`, `toolchange` (360) | Speed for travel moves (jumps between distant extrusion points) | `travel_speed` |
| `nozzle_diameter` | lista de números | `start` (291) | This is the diameter of your extruder nozzle (for example: 0.5, 0.35 etc.) | `nozzle_diameter` |
| `idle_temperature` | lista de enteros | `start`, `toolchange` (289) | Idle temperature | `idle_temperature` |
| `layer_num` | entero | `toolchange`, `layer_change`, `before_layer_change`, `end` (278) | Zero-based index of the current layer (i.e | `layer_num` |
| `first_layer_print_min` | lista de números | `start` (266) | Bottom-left corner of first layer bounding box | `first_layer_print_min` |
| `first_layer_print_max` | lista de números | `start` (242) | Top-right corner of first layer bounding box | `first_layer_print_max` |
| `filament_type` | lista de textos | `start`, `toolchange` (219) | The filament material type for use in custom G-codes | `filament_type` |
| `initial_tool` | entero | `start`, `toolchange` (196) | Zero-based index of the first extruder used in the print | `initial_tool` |
| `filament_abrasive` | lista de sí/no | `start` (155) | This flag means that the material is abrasive and requires a hardened nozzle | `filament_abrasive` |
| `nozzle_high_flow` | lista de sí/no | `start` (155) | High flow nozzle | `nozzle_high_flow` |
| `filament_notes` | lista de textos | `start` (154) | You can put your notes regarding the filament here | `filament_notes` |
| `chamber_temperature` | lista de enteros | `start` (136) | Chamber temperature | `chamber_temperature` |
| `temperature` | lista de enteros | `start`, `toolchange`, `before_layer_change` (135) | Nozzle temperature | `temperature` |
| `layer_height` | número | `start` (133) | Layer height | `layer_height` |
| `chamber_minimal_temperature` | lista de enteros | `start` (116) | Chamber minimal temperature | `chamber_minimal_temperature` |
| `next_extruder` | entero | `toolchange` (112) | Index of the extruder that is being loaded | `next_extruder` |
| `retract_length` | lista de números | `start` (105) | Retraction Length | `retract_length` |
| `printer_model` | texto | `start` (98) | Type of the printer | `printer_model` |
| `is_extruder_used` | lista de sí/no | `start`, `end`, `layer_change` (97) | Is extruder used? | `is_extruder_used` |
| `first_layer_print_min_0` |  | `end`, `start` (84) |  |  |
| `first_layer_print_min_1` |  | `end`, `start` (84) |  |  |
| `machine_max_acceleration_extruding` | lista de números | `start` (81) | Maximum acceleration when extruding | `machine_max_acceleration_extruding` |
| `machine_max_acceleration_retracting` | lista de números | `start` (81) | Maximum acceleration when retracting | `machine_max_acceleration_retracting` |
| `machine_max_acceleration_travel` | lista de números | `start` (80) | Maximum acceleration for travel moves | `machine_max_acceleration_travel` |
| `initial_extruder` | entero | `start` (79) | Zero-based index of the first extruder used in the print | `initial_extruder` |
| `first_layer_height` | número o porcentaje | `start`, `toolchange` (78) | First layer height | `first_layer_height` |
| `bed_temperature` | lista de enteros | `toolchange`, `start`, `layer_change` (76) | Bed temperature | `bed_temperature` |
| `retract_length_toolchange` | lista de números | `start`, `toolchange` (75) | Retraction Length (Toolchange) | `retract_length_toolchange` |
| `standby_temperature_delta` | entero | `start`, `toolchange` (75) | Temperature variation | `standby_temperature_delta` |
| `machine_max_feedrate_x` | lista de números | `start`, `end` (73) |  | `machine_max_feedrate_x` |
| `machine_max_feedrate_z` | lista de números | `start`, `end` (73) |  | `machine_max_feedrate_z` |
| `first_layer_print_max_0` |  | `end` (72) |  |  |
| `first_layer_print_max_1` |  | `end` (72) |  |  |
| `machine_max_acceleration_e` | lista de números | `start` (72) |  | `machine_max_acceleration_e` |
| `machine_max_acceleration_x` | lista de números | `start` (72) |  | `machine_max_acceleration_x` |
| `machine_max_acceleration_y` | lista de números | `start` (72) |  | `machine_max_acceleration_y` |
| `machine_max_acceleration_z` | lista de números | `start` (72) |  | `machine_max_acceleration_z` |
| `machine_max_feedrate_e` | lista de números | `start` (72) |  | `machine_max_feedrate_e` |
| `machine_max_feedrate_y` | lista de números | `start` (72) |  | `machine_max_feedrate_y` |
| `machine_max_jerk_e` | lista de números | `start` (72) |  | `machine_max_jerk_e` |
| `machine_max_jerk_x` | lista de números | `start` (72) |  | `machine_max_jerk_x` |
| `machine_max_jerk_y` | lista de números | `start` (72) |  | `machine_max_jerk_y` |
| `machine_max_jerk_z` | lista de números | `start` (72) |  | `machine_max_jerk_z` |
| `max_fan_speed` | lista de enteros | `start` (72) | This setting represents the maximum speed of your fan | `max_fan_speed` |
| `physical_printer_preset` | texto | `start` (72) | Physical printer name | `physical_printer_preset` |
| `print_preset` | texto | `start` (72) | Print preset name | `print_preset` |
| `printer_preset` | texto | `start` (72) | Printer preset name | `printer_preset` |
| `current_extruder` | entero | `toolchange`, `start` (66) | Zero-based index of currently used extruder | `current_extruder` |
| `extruded_weight_total` | número | `before_layer_change`, `layer_change` (65) | Total weight of the print | `extruded_weight_total` |
| `spiral_vase` | sí/no | `layer_change` (65) | Spiral vase | `spiral_vase` |
| `has_wipe_tower` | sí/no | `start`, `toolchange`, `end` (60) | Has wipe tower | `has_wipe_tower` |
| `total_layer_count` | entero | `start`, `end` (58) | Total layer count | `total_layer_count` |
| `print_bed_min` | lista de números | `start` (50) | Bottom-left corner of print bed bounding box | `print_bed_min` |
| `default_acceleration` | número | `toolchange` (40) | Default | `default_acceleration` |
| `disable_fan_first_layers` | lista de enteros | `toolchange` (40) | Disable fan for the first | `disable_fan_first_layers` |
| `first_layer_acceleration` | número | `toolchange` (40) | First layer | `first_layer_acceleration` |
| `min_fan_speed` | lista de enteros | `toolchange` (40) | This setting represents the minimum PWM your fan needs to work | `min_fan_speed` |
| `total_toolchanges` | entero | `start`, `toolchange` (40) | Total number of toolchanges | `total_toolchanges` |
| `retract_speed` | lista de números | `toolchange`, `start` (37) | The speed for retractions (it only applies to the extruder motor) | `retract_speed` |
| `wipe_tower_x` |  | `toolchange` (36) |  |  |
| `wipe_tower_y` |  | `toolchange` (36) |  |  |
| `previous_extruder` | entero | `toolchange` (35) | Index of the extruder that is being unloaded | `previous_extruder` |
| `e_retracted` | lista de números | `start` (32) | Retraction | `e_retracted` |
| `filament_multitool_ramming` | lista de sí/no | `start` (32) | Enable ramming for multitool setups | `filament_multitool_ramming` |
| `max_speed_toolchange` | propia de la macro | `toolchange` (32) |  |  |
| `num_extruders` | entero | `start` (32) | Number of extruders | `num_extruders` |
| `position` | lista de números | `toolchange` (32) | Position | `position` |
| `speed_toolchange` | propia de la macro | `toolchange` (32) |  |  |
| `then` |  | `toolchange` (32) |  |  |
| `wait_for_extruder_temp` | propia de la macro | `toolchange` (32) |  |  |
| `zhop` | número | `start` (32) | Contains z-hop present at the beginning of the custom G-code block | `zhop` |
| `print_settings_id` | texto | `end`, `start` (29) |  | `print_settings_id` |
| `extra_loading_move` | número | `start` (21) | Extra loading distance | `extra_loading_move` |
| `parking_pos_retraction` | número | `start` (21) | Filament parking position | `parking_pos_retraction` |
| `has_single_extruder_multi_material_priming` | sí/no | `start` (17) | Has single extruder MM priming | `has_single_extruder_multi_material_priming` |
| `Checks` |  | `start` (12) |  |  |
| `Config` |  | `start` (12) |  |  |
| `Macros` |  | `start` (12) |  |  |
| `System` |  | `start` (12) |  |  |
| `directories` |  | `start` (12) |  |  |
| `filament_check` |  | `start` (12) |  |  |
| `filament_settings_id` | lista de textos | `start` (12) |  | `filament_settings_id` |
| `move` |  | `start` (12) |  |  |
| `nozzle_check` |  | `start` (12) |  |  |
| `first_layer_temperature_` |  | `start` (9) |  |  |
| `print_bed_size` | lista de números | `start` (5) | Size of the print bed bounding box | `print_bed_size` |
| `filament_max_volumetric_speed` | lista de números | `toolchange` (4) | Max volumetric speed | `filament_max_volumetric_speed` |
| `load_heightmap` |  | `start` (4) |  |  |
| `printer_settings_id` | texto | `start` (4) |  | `printer_settings_id` |
| `start_filament_gcode` | lista de textos | `start` (4) | Start G-code | `start_filament_gcode` |
| `travel_acceleration` | número | `toolchange` (4) | Travel | `travel_acceleration` |
| `day` | entero | `start` (2) | Day | `day` |
| `extruded_volume` | lista de números | `start` (2) | Volume per extruder | `extruded_volume` |
| `extrusion_width` | número o porcentaje | `start` (2) | Default extrusion width | `extrusion_width` |
| `filament_diameter` | lista de números | `start` (2) | Diameter | `filament_diameter` |
| `month` | entero | `start` (2) | Month | `month` |
| `year` | entero | `start` (2) | Year | `year` |

## `orcaslicer`

254 variables.

| Variable | Tipo | Dónde | Qué es | En PrusaSlicer |
|---|---|---|---|---|
| `layer_z` | número | `before_layer_change`, `layer_change`, `toolchange`, `timelapse`, `end`, `toolchange_gcode` (750) | Height of the current layer above the print bed, measured to the top of the layer | `layer_z` |
| `nozzle_temperature_initial_layer` | lista de enteros | `start`, `toolchange`, `toolchange_gcode`, `before_layer_change`, `end` (581) | First layer nozzle temperature | `first_layer_temperature` |
| `bed_temperature_initial_layer_single` | entero | `start`, `layer_change`, `before_layer_change` (509) | set by the program while slicing (GCode.cpp) | `first_layer_bed_temperature` |
| `layer_num` | entero | `layer_change`, `before_layer_change`, `toolchange`, `wrapping_detection_gcode`, `timelapse`, `toolchange_gcode`, `end` (289) | Index of the current layer | `layer_num` |
| `first_layer_print_min` | lista de números | `start`, `layer_change`, `before_layer_change` (272) | Bottom-left corner of the first layer bounding box | `first_layer_print_min` |
| `max_layer_z` | número | `end`, `toolchange`, `timelapse` (253) | Maximal layer Z | `max_layer_z` |
| `first_layer_temperature` | lista de enteros | `start`, `toolchange` (251) | set by the program while slicing (GCode.cpp) | `first_layer_temperature` |
| `total_layer_count` | entero | `start`, `layer_change` (224) | Total layer count | `total_layer_count` |
| `first_layer_print_max` | lista de números | `start`, `layer_change`, `before_layer_change` (194) | Top-right corner of the first layer bounding box | `first_layer_print_max` |
| `first_layer_bed_temperature` | lista de enteros | `start` (185) | set by the program while slicing (GCode.cpp) | `first_layer_bed_temperature` |
| `next_extruder` | entero | `toolchange`, `toolchange_gcode`, `filament_swap_gcode` (153) | set by the program while slicing (GCode.cpp) | `next_extruder` |
| `print_bed_max` | lista de números | `start`, `end`, `toolchange`, `layer_change` (140) | Top-right corner of print bed bounding box | `print_bed_max` |
| `initial_no_support_extruder` | entero | `start`, `toolchange` (132) | set by the program while slicing (Print.cpp) | `initial_extruder` |
| `chamber_temperature` | lista de enteros | `start`, `end` (127) | Chamber temperature | `chamber_temperature` |
| `filament_type` | lista de textos | `start`, `toolchange`, `layer_change`, `before_layer_change`, `end` (122) | Filament material type | `filament_type` |
| `curr_bed_type` | opción | `start`, `custom` (121) | Plate types supported by the printer | `curr_bed_type` |
| `initial_tool` | entero | `start`, `toolchange` (116) | Zero-based index of the first extruder used in the print | `initial_tool` |
| `nozzle_temperature` | lista de enteros | `start`, `toolchange`, `before_layer_change`, `end`, `toolchange_gcode` (109) | Nozzle temperature after the first layer | `temperature` |
| `z_after_toolchange` | número | `toolchange` (106) | set by the program while slicing (GCode.cpp) |  |
| `bed_temperature_initial_layer` | lista de enteros | `start` (102) | set by the program while slicing (GCode.cpp) | `first_layer_bed_temperature` |
| `new_filament_temp` | entero | `toolchange` (99) | set by the program while slicing (GCode.cpp) |  |
| `printable_height` | número | `end`, `toolchange` (96) | This is the maximum printable height which is limited by the height of the build area | `max_print_height` |
| `initial_extruder` | entero | `start`, `toolchange` (93) | Zero-based index of the first extruder used in the print | `initial_extruder` |
| `initial_layer_print_height` | número | `toolchange`, `start`, `before_layer_change`, `toolchange_gcode` (88) | First layer height | `first_layer_height` |
| `max_print_height` | entero | `end`, `toolchange`, `layer_change` (88) | set by the program while slicing (GCode.cpp) | `max_print_height` |
| `filament_max_volumetric_speed` | lista de números | `start`, `toolchange` (82) | Max volumetric speed | `filament_max_volumetric_speed` |
| `old_filament_temp` | entero | `toolchange` (82) | set by the program while slicing (GCode.cpp) |  |
| `first_layer_print_size` | lista de números | `start` (72) | Size of the first layer bounding box | `first_layer_print_size` |
| `z_offset` | número | `end`, `toolchange`, `start` (70) | Z offset | `z_offset` |
| `new_filament_e_feedrate` | entero | `toolchange` (67) | set by the program while slicing (GCode.cpp) |  |
| `old_filament_e_feedrate` | entero | `toolchange` (67) | set by the program while slicing (GCode.cpp) |  |
| `previous_extruder` | entero | `toolchange` (64) | set by the program while slicing (GCode.cpp) | `previous_extruder` |
| `timelapse_type` | opción | `timelapse`, `layer_change` (64) | If smooth or traditional mode is selected, a timelapse video will be generated for each print |  |
| `travel_speed` | lista de números | `end`, `start`, `toolchange` (64) | This is the speed at which traveling is done | `travel_speed` |
| `x_after_toolchange` | número | `toolchange` (64) | set by the program while slicing (GCode.cpp) |  |
| `y_after_toolchange` | número | `toolchange` (64) | set by the program while slicing (GCode.cpp) |  |
| `bed_temperature` | lista de enteros | `start`, `end`, `before_layer_change`, `toolchange` (63) | set by the program while slicing (GCode.cpp) | `bed_temperature` |
| `flush_length` | número | `toolchange` (63) | set by the program while slicing (GCode.cpp) |  |
| `initial_layer_acceleration` | lista de números | `toolchange` (62) | This is the printing acceleration for the first layer |  |
| `toolchange_count` | entero | `toolchange` (62) | set by the program while slicing (GCode.cpp) |  |
| `flush_temperatures` | lista de enteros | `toolchange`, `start` (60) | set by the program while slicing (GCode.cpp) |  |
| `flush_volumetric_speeds` | lista de números | `toolchange`, `start`, `end` (60) | set by the program while slicing (GCode.cpp) |  |
| `retraction_distances_when_cut` | lista de números | `toolchange`, `start` (60) | Retraction distance when cut |  |
| `spiral_mode` | sí/no | `timelapse`, `wrapping_detection_gcode`, `layer_change`, `end` (57) | Spiral vase | `spiral_vase` |
| `outer_wall_volumetric_speed` | número | `start`, `toolchange` (54) | set by the program while slicing (GCode.cpp) |  |
| `flush_length_1` |  | `toolchange` (52) |  |  |
| `flush_length_2` |  | `toolchange` (52) |  |  |
| `flush_length_3` |  | `toolchange` (52) |  |  |
| `flush_length_4` |  | `toolchange` (52) |  |  |
| `new_retract_length_toolchange` | número | `toolchange` (52) | set by the program while slicing (GCode.cpp) |  |
| `default_acceleration` | lista de números | `toolchange`, `start` (50) | This is the default acceleration for both normal printing and travel after the first layer | `default_acceleration` |
| `long_retractions_when_cut` | lista de sí/no | `toolchange` (48) | Long retraction when cut (beta) |  |
| `travel_point_1_x` | número | `toolchange` (48) | set by the program while slicing (GCode.cpp) |  |
| `travel_point_1_y` | número | `toolchange` (48) | set by the program while slicing (GCode.cpp) |  |
| `travel_point_2_x` | número | `toolchange` (48) | set by the program while slicing (GCode.cpp) |  |
| `travel_point_2_y` | número | `toolchange` (48) | set by the program while slicing (GCode.cpp) |  |
| `travel_point_3_x` | número | `toolchange` (48) | set by the program while slicing (GCode.cpp) |  |
| `travel_point_3_y` | número | `toolchange` (48) | set by the program while slicing (GCode.cpp) |  |
| `current_extruder` | entero | `toolchange`, `end`, `start`, `toolchange_gcode` (44) | Zero-based index of currently used extruder | `current_extruder` |
| `temperature` | lista de enteros | `start`, `toolchange` (42) | set by the program while slicing (GCode.cpp) | `temperature` |
| `old_retract_length_toolchange` | número | `toolchange` (40) | set by the program while slicing (GCode.cpp) |  |
| `nozzle_temperature_range_high` | lista de enteros | `toolchange`, `start` (39) |  |  |
| `print_time_sec` | texto | `file_start_gcode` (38) | Print time (seconds component) |  |
| `printer_model` | texto | `start` (37) | Type of the printer | `printer_model` |
| `filament_map` | lista de enteros | `toolchange`, `start`, `end` (36) | Filament map to extruder |  |
| `long_retraction_when_cut` | sí/no | `toolchange`, `end` (36) | set by the program while slicing (GCode.cpp) |  |
| `retraction_distance_when_cut` | número | `toolchange`, `end` (36) | set by the program while slicing (GCode.cpp) |  |
| `retraction_length` | lista de números | `start`, `layer_change`, `toolchange`, `end` (36) | Retraction Length | `retract_length` |
| `nozzle_diameter` | lista de números | `start`, `toolchange` (34) | The diameter of nozzle | `nozzle_diameter` |
| `print_sequence` | opción | `end`, `timelapse`, `toolchange` (34) | This determines the print sequence, allowing you to print layer-by-layer or object-by-object |  |
| `overall_chamber_temperature` | entero | `start`, `layer_change`, `toolchange` (32) | set by the program while slicing (GCode.cpp) |  |
| `adaptive_bed_mesh_max` | lista de números | `start` (30) | set by the program while slicing (GCode.cpp) | `first_layer_print_max` |
| `adaptive_bed_mesh_min` | lista de números | `start` (30) | set by the program while slicing (GCode.cpp) | `first_layer_print_min` |
| `bed_mesh_probe_count` | lista de enteros | `start` (28) | set by the program while slicing (GCode.cpp) |  |
| `current_filament_id` | entero | `toolchange`, `layer_change`, `end` (28) | set by the program while slicing (GCode.cpp) |  |
| `current_nozzle_id` | entero | `toolchange`, `layer_change` (28) | set by the program while slicing (GCode.cpp) |  |
| `filament_cooling_before_tower` | lista de números | `toolchange` (28) | Wipe tower cooling |  |
| `initial_no_support_filament_id` |  | `start` (28) |  |  |
| `max_print_z` | entero | `start` (28) | set by the program while slicing (GCode.cpp) |  |
| `min_vitrification_temperature` | entero | `start`, `layer_change`, `toolchange` (28) | set by the program while slicing (GCode.cpp) |  |
| `next_filament_id` | entero | `toolchange` (28) | set by the program while slicing (GCode.cpp) |  |
| `next_nozzle_id` | entero | `toolchange` (28) | set by the program while slicing (GCode.cpp) |  |
| `nozzle_diameter_at_nozzle_id` | lista de números | `start`, `toolchange`, `layer_change` (28) | set by the program while slicing (GCode.cpp) |  |
| `outer_wall_acceleration` | lista de números | `start` (28) | Acceleration of outer wall: using a lower value can improve quality |  |
| `print_time_day` | texto | `file_start_gcode` (28) | Print time (days component) |  |
| `print_time_hour` | texto | `file_start_gcode` (28) | Print time (hours component) |  |
| `print_time_minute` | texto | `file_start_gcode` (28) | Print time (minutes component) |  |
| `is_extruder_used` | lista de sí/no | `start`, `layer_change`, `end` (27) | Is extruder used? | `is_extruder_used` |
| `standby_temperature_delta` | entero | `start` (26) | Temperature variation | `standby_temperature_delta` |
| `print_bed_min` | lista de números | `start` (25) | Bottom-left corner of print bed bounding box | `print_bed_min` |
| `filament_tower_interface_print_temp` | lista de enteros | `toolchange` (24) | Interface layer print temperature |  |
| `filament_tower_interface_purge_volume` | lista de números | `toolchange` (24) | Interface layer purge length |  |
| `initial_nozzle_id` |  | `start` (24) |  |  |
| `is_prime_tower_interface` | sí/no | `toolchange` (24) | set by the program while slicing (GCode.cpp) |  |
| `timelapse_inline_photo` | sí/no | `timelapse` (24) | set by the program while slicing (GCode.cpp) |  |
| `has_tpu_in_first_layer` | sí/no | `start` (20) | set by the program while slicing (GCode.cpp) |  |
| `is_all_bbl_filament` |  | `start`, `layer_change`, `toolchange` (20) |  |  |
| `long_retraction_when_ec` |  | `toolchange`, `start`, `end` (20) |  |  |
| `retract_length_toolchange` | lista de números | `toolchange` (20) | Retraction Length (Toolchange) | `retract_length_toolchange` |
| `retraction_distance_when_ec` |  | `toolchange`, `start`, `end` (20) |  |  |
| `machine_max_acceleration_extruding` | lista de números | `start` (19) | Maximum acceleration for extruding | `machine_max_acceleration_extruding` |
| `machine_max_acceleration_retracting` | lista de números | `start` (19) | Maximum acceleration for retracting | `machine_max_acceleration_retracting` |
| `layer_height` | número | `before_layer_change`, `start`, `file_start_gcode`, `toolchange_gcode` (18) | This is the height for each layer | `layer_height` |
| `z_hop` | lista de números | `toolchange` (17) | Z-hop height | `retract_lift` |
| `additional_cooling_fan_speed` | lista de enteros | `layer_change`, `toolchange`, `start` (16) | Fan speed |  |
| `bed_mesh_algo` |  | `start` (16) |  | `bicubic` |
| `chamber_temperatures` |  | `start` (16) |  |  |
| `cooling_filter_enabled` | sí/no | `start` (16) | Use cooling filter |  |
| `curr_physical_extruder_id` | entero | `timelapse` (16) | set by the program while slicing (GCode.cpp) |  |
| `during_print_exhaust_fan_speed` | lista de enteros | `start`, `layer_change` (16) | Speed of exhaust fan during printing |  |
| `farthest_point_timelapse_enabled` | sí/no | `timelapse` (16) | set by the program while slicing (GCode.cpp) |  |
| `first_non_support_filaments` | lista de enteros | `start` (16) | set by the program while slicing (GCode.cpp) |  |
| `has_timelapse_safe_pos` | sí/no | `timelapse` (16) | set by the program while slicing (GCode.cpp) |  |
| `initial_no_support_hotend` |  | `start` (16) |  |  |
| `most_used_physical_extruder_id` | entero | `timelapse` (16) | set by the program while slicing (GCode.cpp) |  |
| `next_hotend` | entero | `toolchange` (16) | set by the program while slicing (GCode.cpp) |  |
| `timelapse_pos_x` | entero | `timelapse` (16) | set by the program while slicing (GCode.cpp) |  |
| `timelapse_pos_y` | entero | `timelapse` (16) | set by the program while slicing (GCode.cpp) |  |
| `travel_acceleration` | lista de números | `toolchange` (16) | Acceleration of travel moves | `travel_acceleration` |
| `wipe_avoid_perimeter` | sí/no | `toolchange` (16) | set by the program while slicing (GCode.cpp) |  |
| `wipe_avoid_pos_x` | número | `toolchange` (16) | set by the program while slicing (GCode.cpp) |  |
| `day` | entero | `start` (13) | Day | `day` |
| `hour` | entero | `start` (13) | Hour | `hour` |
| `minute` | entero | `start` (13) | Minute | `minute` |
| `month` | entero | `start` (13) | Month | `month` |
| `second` | entero | `start` (13) | Second | `second` |
| `year` | entero | `start` (13) | Year | `year` |
| `current_hotend` | entero | `toolchange`, `end` (12) | set by the program while slicing (GCode.cpp) |  |
| `first_filaments` | lista de enteros | `start` (12) | set by the program while slicing (GCode.cpp) |  |
| `first_layer_center_no_wipe_tower` | lista de números | `timelapse`, `end` (12) | set by the program while slicing (GCode.cpp) |  |
| `hold_chamber_temp_for_flat_print` | sí/no | `start` (12) | set by the program while slicing (GCode.cpp) |  |
| `hotend_cooling_rate` | lista de números | `toolchange` (12) |  |  |
| `hotend_heating_rate` | lista de números | `toolchange` (12) |  |  |
| `initial_filament_id` |  | `start` (12) |  |  |
| `new_extruder_retracted_length` | número | `toolchange` (12) | set by the program while slicing (GCode.cpp) |  |
| `nozzle_volume_types` | lista de textos | `toolchange` (12) | set by the program while slicing (GCode.cpp) |  |
| `print_bed_size` | lista de números | `start` (12) | Size of the print bed bounding box | `print_bed_size` |
| `scan_first_layer` | sí/no | `start` (12) | Scan first layer |  |
| `toolchange_z` | número | `toolchange` (12) | set by the program while slicing (GCode.cpp) | `toolchange_z` |
| `z_hop_types` | lista de opciones | `toolchange` (12) | Type of Z-hop |  |
| `machine_max_acceleration_travel` | lista de números | `start` (11) | Maximum acceleration for travel | `machine_max_acceleration_travel` |
| `pressure_advance` | lista de números | `start` (11) | Pressure advance (Klipper) AKA Linear advance factor (Marlin) |  |
| `notes` | texto | `start` (10) | Configuration notes | `notes` |
| `enable_pressure_advance` | lista de sí/no | `start` (9) | Enable pressure advance |  |
| `extruded_weight_total` | número | `before_layer_change`, `layer_change` (9) | Total weight of the print | `extruded_weight_total` |
| `additional_fan_full_speed_layer` | lista de enteros | `layer_change`, `toolchange` (8) | Full fan speed at layer |  |
| `close_additional_fan_first_x_layers` | lista de enteros | `layer_change`, `toolchange` (8) | For the first |  |
| `filament_ids` | lista de textos | `start`, `toolchange` (8) |  |  |
| `first_x_layer_fan_speed` | lista de números | `layer_change`, `toolchange` (8) | Special auxiliary cooling fan speed, effective only for the first x layers |  |
| `in_head_wrap_detect_zone` |  | `timelapse` (8) |  |  |
| `max_additional_fan` |  | `layer_change`, `toolchange` (8) |  |  |
| `position` | lista de números | `toolchange`, `end` (8) | Position | `position` |
| `filament_diameter` | lista de números | `start`, `toolchange` (7) | Diameter | `filament_diameter` |
| `filament_notes` | lista de textos | `start` (7) | You can put your notes regarding the filament here | `filament_notes` |
| `filament_settings_id` | lista de textos | `start`, `layer_change` (7) |  | `filament_settings_id` |
| `idle_temperature` | lista de enteros | `start` (7) | Idle temperature | `idle_temperature` |
| `nozzle_temperature_initial_layer_0` |  | `start` (7) |  | `first_layer_temperature` |
| `nozzle_temperature_initial_layer_1` |  | `start` (7) |  |  |
| `enable_prime_tower` | sí/no | `toolchange`, `start` (6) | Enable |  |
| `extra_loading_move` | número | `start` (5) | Extra loading distance | `extra_loading_move` |
| `extrude_length_` | propia de la macro | `toolchange` (5) |  |  |
| `flush_length_` | propia de la macro | `toolchange` (5) |  |  |
| `hot_plate_temp_initial_layer` | lista de enteros | `start` (5) | First layer bed temperature | `first_layer_bed_temperature` |
| `loops_` | propia de la macro | `toolchange` (5) |  |  |
| `parking_pos_retraction` | número | `start` (5) | Filament parking position | `parking_pos_retraction` |
| `then` |  | `toolchange`, `end` (5) |  |  |
| `adaptive_bed_mesh_margin` | número | `start` (4) | Mesh margin |  |
| `clear_to_x0` | sí/no | `timelapse` (4) | set by the program while slicing (GCode.cpp) |  |
| `curr_y_acceleration_limit` | número | `layer_change` (4) | set by the program while slicing (GCode.cpp) |  |
| `filament_pre_cooling_temperature_nc` | lista de enteros | `toolchange` (4) | Hotend change |  |
| `filament_retract_length_nc` | lista de números | `toolchange` (4) | length when change hotend |  |
| `fins_extrude_safe_temp` |  | `start`, `toolchange` (4) |  |  |
| `first_non_support_hotend` | lista de enteros | `start` (4) | set by the program while slicing (GCode.cpp) |  |
| `has_wipe_tower` | sí/no | `toolchange` (4) | Has wipe tower | `has_wipe_tower` |
| `initial_layer_travel_acceleration` | lista de números o porcentajes | `toolchange` (4) | First layer travel |  |
| `initial_no_support_nozzle_id` |  | `start` (4) |  |  |
| `max_speed_toolchange` | propia de la macro | `toolchange` (4) |  |  |
| `move_z` | propia de la macro | `end`, `toolchange` (4) |  |  |
| `nozzle_volume_type` | lista de opciones | `end` (4) |  |  |
| `parallel_printheads_count` | entero | `start`, `layer_change` (4) | Parallel printheads count |  |
| `print_settings_id` | texto | `end` (4) |  | `print_settings_id` |
| `print_time_total_sec` | texto | `file_start_gcode` (4) | Print time (total seconds) |  |
| `printer_notes` | texto | `start` (4) | You can put your notes regarding the printer here | `printer_notes` |
| `speed_toolchange` | propia de la macro | `toolchange` (4) |  |  |
| `temperature_vitrification` | lista de enteros | `start`, `toolchange` (4) | Softening temperature |  |
| `time_flush_` | propia de la macro | `toolchange` (4) |  |  |
| `used_filament_length` | texto | `file_start_gcode` (4) | Filament length (meters) |  |
| `wait_for_extruder_temp` | propia de la macro | `toolchange` (4) |  |  |
| `wipe_tower_center_pos_valid` | sí/no | `start`, `toolchange` (4) | set by the program while slicing (GCode.cpp) |  |
| `wipe_tower_center_pos_x` | número | `start`, `toolchange` (4) | set by the program while slicing (GCode.cpp) |  |
| `wipe_tower_center_pos_y` | número | `start`, `toolchange` (4) | set by the program while slicing (GCode.cpp) |  |
| `e_retracted` | lista de números | `toolchange`, `start` (3) | Retraction | `e_retracted` |
| `machine_max_speed_x` | lista de números | `start`, `end` (3) |  |  |
| `machine_max_speed_z` | lista de números | `start`, `end` (3) |  |  |
| `required_nozzle_HRC` | lista de enteros | `start` (3) | Required nozzle HRC |  |
| `retraction_speed` | lista de números | `toolchange`, `start` (3) | Speed for retracting filament from the nozzle |  |
| `total_toolchanges` | entero | `toolchange`, `start` (3) | Total tool changes | `total_toolchanges` |
| `chamber_minimal_temperature` | lista de enteros | `start` (2) | Chamber minimal temperature | `chamber_minimal_temperature` |
| `deretract_length` | propia de la macro | `toolchange`, `start` (2) |  |  |
| `deretraction_speed` | lista de números | `start`, `toolchange` (2) | Speed for reloading filament into the nozzle |  |
| `eject_temp` | propia de la macro | `start`, `toolchange` (2) |  |  |
| `extruded_volume` | lista de números | `start` (2) | Volume per extruder | `extruded_volume` |
| `fan_max_speed` | lista de números | `start`, `toolchange` (2) | The part cooling fan speed may be increased when auto cooling is enabled |  |
| `filament_area` | propia de la macro | `start`, `toolchange` (2) |  |  |
| `filament_flush_volumetric_speed` | lista de números | `start`, `toolchange` (2) | Flush volumetric speed |  |
| `filament_minimal_purge_on_wipe_tower` | lista de números | `toolchange` (2) | Minimal purge on wipe tower | `filament_minimal_purge_on_wipe_tower` |
| `filament_retract_length_toolchange` |  | `toolchange` (2) |  |  |
| `first_layer_height` | número | `start` (2) | set by the program while slicing (GCode.cpp) | `first_layer_height` |
| `inner_wall_speed` | lista de números | `start` (2) | This is the speed for inner walls |  |
| `low_temp_types` | propia de la macro | `layer_change`, `start` (2) |  |  |
| `machine_max_acceleration_e` | lista de números | `start` (2) |  | `machine_max_acceleration_e` |
| `machine_max_acceleration_x` | lista de números | `start` (2) |  | `machine_max_acceleration_x` |
| `machine_max_acceleration_y` | lista de números | `start` (2) |  | `machine_max_acceleration_y` |
| `machine_max_acceleration_z` | lista de números | `start` (2) |  | `machine_max_acceleration_z` |
| `machine_max_jerk_e` | lista de números | `start` (2) |  | `machine_max_jerk_e` |
| `machine_max_jerk_x` | lista de números | `start` (2) |  | `machine_max_jerk_x` |
| `machine_max_jerk_y` | lista de números | `start` (2) |  | `machine_max_jerk_y` |
| `machine_max_jerk_z` | lista de números | `start` (2) |  | `machine_max_jerk_z` |
| `machine_max_speed_e` | lista de números | `start` (2) |  |  |
| `machine_max_speed_y` | lista de números | `start` (2) |  |  |
| `outer_wall_line_width` | número o porcentaje | `start` (2) | Line width of outer wall |  |
| `outer_wall_speed` | lista de números | `start` (2) | This is the printing speed for the outer walls of parts |  |
| `perimeter_flow_rate` | propia de la macro | `start` (2) |  |  |
| `print_preset` | texto | `start` (2) | Print preset name | `print_preset` |
| `probe_temp` | propia de la macro | `start` (2) |  |  |
| `purge_mm` | propia de la macro | `start`, `toolchange` (2) |  |  |
| `purge_speed_fast` | propia de la macro | `start`, `toolchange` (2) |  |  |
| `purge_speed_slow` | propia de la macro | `start`, `toolchange` (2) |  |  |
| `retract_restart_extra_toolchange` | lista de números | `start`, `toolchange` (2) | Extra length on restart (Toolchange) | `retract_restart_extra_toolchange` |
| `retract_toolchange` | propia de la macro | `toolchange`, `start` (2) |  |  |
| `speed_tc` | propia de la macro | `toolchange`, `start` (2) |  |  |
| `target_temp` | propia de la macro | `toolchange`, `start` (2) |  |  |
| `tc_deretract_speed` | propia de la macro | `toolchange`, `start` (2) |  |  |
| `tc_retract_speed` | propia de la macro | `toolchange` (2) |  |  |
| `tool_init` | propia de la macro | `toolchange`, `start` (2) |  |  |
| `travel_slope` | lista de números | `toolchange` (2) | Traveling angle for Slope and Spiral Z-hop type | `travel_slope` |
| `used_tools` | propia de la macro | `start`, `layer_change` (2) |  |  |
| `EXTRUDE_SPEED_` | propia de la macro | `toolchange` (1) |  |  |
| `UNWIND_SPEED_` | propia de la macro | `toolchange` (1) |  |  |
| `curr_t` | propia de la macro | `toolchange` (1) |  |  |
| `filament_multitool_ramming` | lista de sí/no | `start` (1) | Enable ramming for multi-tool setups | `filament_multitool_ramming` |
| `first_flush_volume` | número | `toolchange` (1) | set by the program while slicing (GCode.cpp) |  |
| `index_` | propia de la macro | `toolchange` (1) |  |  |
| `initial_layer_speed` | lista de números | `start` (1) | This is the speed for the first layer except for solid infill sections |  |
| `input_filename_base` | texto | `start` (1) | Input filename without extension | `input_filename_base` |
| `line_width` | número o porcentaje | `start` (1) | Default line width if other line widths are set to 0 |  |
| `minimal_extrude_` | propia de la macro | `toolchange` (1) |  |  |
| `new_retract_length` | número | `toolchange` (1) | set by the program while slicing (GCode.cpp) |  |
| `next_t` | propia de la macro | `toolchange` (1) |  |  |
| `nozzle_temperature_range_low` | lista de enteros | `start` (1) |  |  |
| `retract_length` | lista de números | `start` (1) | set by the program while slicing (GCode.cpp) | `retract_length` |
| `step_from_` | propia de la macro | `toolchange` (1) |  |  |
| `step_into_` | propia de la macro | `toolchange` (1) |  |  |
| `tab_step_time_` | propia de la macro | `toolchange` (1) |  |  |

## `crealityprint`

38 variables.

| Variable | Tipo | Dónde | Qué es | En PrusaSlicer |
|---|---|---|---|---|
| `layer_z` | número | `before_layer_change`, `layer_change` (17) | Height of the current layer above the print bed, measured to the top of the layer | `layer_z` |
| `nozzle_temperature_initial_layer` | lista de enteros | `start` (17) | Initial layer nozzle temperature | `first_layer_temperature` |
| `bed_temperature_initial_layer_single` | entero | `start` (16) | set by the program while slicing (GCode.cpp) | `first_layer_bed_temperature` |
| `z_after_toolchange` | número | `toolchange` (15) | set by the program while slicing (GCode.cpp) |  |
| `initial_no_support_extruder` |  | `start` (14) |  | `initial_extruder` |
| `filament_max_volumetric_speed` | lista de números | `start` (10) | Max volumetric speed | `filament_max_volumetric_speed` |
| `initial_extruder` | entero | `start` (10) | Zero-based index of the first extruder used in the print | `initial_extruder` |
| `max_layer_z` | número | `end`, `toolchange` (7) | Maximal layer z | `max_layer_z` |
| `print_sequence` | opción | `end`, `toolchange` (5) | Print sequence, layer by layer or object by object |  |
| `max_print_height` | entero | `end` (2) | set by the program while slicing (GCode.cpp) | `max_print_height` |
| `prime_tower_width` | número | `toolchange` (2) | Width of prime tower |  |
| `print_bed_max` | lista de números | `end` (2) | Top-right corner of print bed bounding box | `print_bed_max` |
| `printable_height` | número | `end` (2) | Maximum printable height which is limited by mechanism of printer | `max_print_height` |
| `travel_speed` | lista de números | `end` (2) | Speed of travel which is faster and without extrusion | `travel_speed` |
| `wipe_tower_outer_wall_x` | número | `toolchange` (2) | set by the program while slicing (GCode.cpp) |  |
| `wipe_tower_outer_wall_y` | número | `toolchange` (2) | set by the program while slicing (GCode.cpp) |  |
| `wipe_tower_random_num` | número | `toolchange` (2) | set by the program while slicing (GCode.cpp) |  |
| `z_offset` | número | `end` (2) | Z offset | `z_offset` |
| `flush_length_1` |  | `toolchange` (1) |  |  |
| `flush_length_2` |  | `toolchange` (1) |  |  |
| `flush_length_3` |  | `toolchange` (1) |  |  |
| `flush_length_4` |  | `toolchange` (1) |  |  |
| `flush_length_5` |  | `toolchange` (1) |  |  |
| `long_retractions_when_cut` | lista de sí/no | `toolchange` (1) | Long retraction when cut(experimental) |  |
| `multicolor_method` | sí/no | `start`, `toolchange` (1) | multicolor method |  |
| `new_filament_e_feedrate` | entero | `toolchange` (1) | set by the program while slicing (GCode.cpp) |  |
| `new_filament_temp` | entero | `toolchange` (1) | set by the program while slicing (GCode.cpp) |  |
| `new_retract_length_toolchange` | número | `toolchange` (1) | set by the program while slicing (GCode.cpp) |  |
| `next_extruder` | entero | `toolchange` (1) | set by the program while slicing (GCode.cpp) | `next_extruder` |
| `nozzle_temperature_range_high` | lista de enteros | `toolchange`, `start` (1) | Max |  |
| `old_filament_e_feedrate` | entero | `toolchange` (1) | set by the program while slicing (GCode.cpp) |  |
| `old_retract_length_toolchange` | número | `toolchange` (1) | set by the program while slicing (GCode.cpp) |  |
| `outer_wall_volumetric_speed` | número | `start` (1) | set by the program while slicing (GCode.cpp) |  |
| `position` | lista de números | `toolchange` (1) | Position | `position` |
| `previous_extruder` | entero | `toolchange` (1) | set by the program while slicing (GCode.cpp) | `previous_extruder` |
| `retract_length_toolchange` | lista de números | `start` (1) | Retraction Length (Toolchange) | `retract_length_toolchange` |
| `retraction_distances_when_cut` | lista de números | `toolchange` (1) | Retraction distance when cut |  |
| `toolchange_count` | entero | `toolchange` (1) | set by the program while slicing (GCode.cpp) |  |

## `elegooslicer`

6 variables.

| Variable | Tipo | Dónde | Qué es | En PrusaSlicer |
|---|---|---|---|---|
| `first_layer_print_max` | lista de números | `start` (1) | Top-right corner of the first layer bounding box | `first_layer_print_max` |
| `first_layer_print_min` | lista de números | `start` (1) | Bottom-left corner of the first layer bounding box | `first_layer_print_min` |
| `first_layer_temperature` | lista de enteros | `start` (1) | set by the program while slicing (GCode.cpp) | `first_layer_temperature` |
| `initial_extruder` | entero | `start` (1) | Zero-based index of the first extruder used in the print | `initial_extruder` |
| `is_extruder_used` | lista de sí/no | `start` (1) | Is extruder used? | `is_extruder_used` |
| `layer_z` | número | `before_layer_change`, `layer_change` (1) | Height of the current layer above the print bed, measured to the top of the layer | `layer_z` |

## `cura`

33 variables.

| Variable | Tipo | Dónde | Qué es | En PrusaSlicer |
|---|---|---|---|---|
| `material_print_temperature_layer_0` | número | `start` (65) | Printing Temperature Initial Layer | `first_layer_temperature` |
| `material_bed_temperature_layer_0` | número | `start` (51) | Build Plate Temperature Initial Layer | `first_layer_bed_temperature` |
| `machine_depth` | número | `end` (31) | Machine Depth |  |
| `material_print_temperature` | número | `start` (27) | Printing Temperature | `temperature` |
| `material_bed_temperature` | número | `start` (19) | Build Plate Temperature | `bed_temperature` |
| `speed_travel` | número | `start`, `end` (19) | Travel Speed | `travel_speed` |
| `material_type` | texto | `start` (14) | Material Type | `filament_type` |
| `infill_sparse_density` | número | `start` (12) | Infill Density |  |
| `date` |  | `start` (7) | set by Cura when slicing (StartSliceJob.py) |  |
| `machine_name` | texto | `start` (7) | Machine Type |  |
| `time` |  | `start` (7) | set by Cura when slicing (StartSliceJob.py) |  |
| `build_volume_temperature` | número | `start` (6) | Build Volume Temperature |  |
| `day` |  | `start` (5) | set by Cura when slicing (StartSliceJob.py) | `day` |
| `filament_weight` |  | `start` (5) |  |  |
| `initial_extruder_nr` |  | `start` (5) |  | `initial_extruder` |
| `layer_height` | número | `start` (5) | Layer Height | `layer_height` |
| `wall_thickness` | número | `start` (5) | Wall Thickness |  |
| `layer_height_0` | número | `start` (4) | Initial Layer Height | `first_layer_height` |
| `machine_height` | número | `end` (4) | Machine Height |  |
| `machine_nozzle_size` | número | `start` (4) | Nozzle Diameter | `nozzle_diameter` |
| `material_name` | texto | `start` (4) | Material Name | `filament_settings_id` |
| `material_standby_temperature` | número | `start`, `end` (4) | Standby Temperature |  |
| `print_bed_temperature` |  | `start` (4) | set by Cura when slicing (StartSliceJob.py) | `bed_temperature` |
| `print_time` |  | `start` (2) |  | `print_time` |
| `filament_amount` |  | `start` (1) |  |  |
| `filament_cost` |  | `start` (1) |  | `filament_cost` |
| `jobname` |  | `end` (1) | set by Cura when slicing (StartSliceJob.py) |  |
| `print_temperature` |  | `start` (1) | set by Cura when slicing (StartSliceJob.py) |  |
| `purge_distance` |  | `extruder_start` (1) |  |  |
| `retraction_hop_height_after_extruder_switch` |  | `extruder_start` (1) |  |  |
| `switch_extruder_retraction_amount` | número | `extruder_start` (1) | Nozzle Switch Retraction Distance |  |
| `top_bottom_thickness` | número | `start` (1) | Top/Bottom Thickness |  |
| `z` |  | `start` (1) |  |  |
