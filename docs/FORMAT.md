# Formato del paquete de perfiles

Versión 2 (con el bloque `gcode` desde la versión del 05-11-2026; ver «G-code de la máquina»). Es el formato que lee el motor de Tisma (`tisma_engine`) para instalar impresoras, filamentos, perfiles de
impresión y resinas. Los perfiles de adentro usan el formato de perfil del motor (`docs/PROFILES.md` del motor) con
sus claves (`docs/CONFIG.md` del motor), así que el motor no necesita saber nada de los programas de donde salieron.

## Descarga

Cada versión es un release de este repositorio, con estos archivos:

| Archivo | Qué es |
|---|---|
| `index.json` | El índice: fabricantes, modelos, perfiles y los archivos comprimidos, con su tamaño y su SHA-256 |
| `index.json.xz` | El mismo índice, comprimido con xz (unos 0,12 MB en vez de 2,1 MB). Se puede bajar este y descomprimirlo en lugar de `index.json` |
| `compatible.json` | Qué impresoras sirve cada filamento y cada perfil de impresión |
| `<fabricante>.tar.xz` | Un archivo por fabricante: sus perfiles y sus imágenes (`vendors/<fabricante>/…`) |
| `community.tar.xz` | Los datos de la comunidad (`docs/COMMUNITY.md`) |
| `translation.tar.xz` | Las tablas de traducción de las claves de cada programa a las del motor (`translation/<dialecto>.json`; «Traducción de claves») |
| `stats.json` | Cuentas de la conversión y las claves de origen que no tienen equivalente en el motor |

**La última versión** está siempre en
`https://github.com/adriangrochi-code/Tisma-profiles-/releases/latest/download/<archivo>`.

Para instalar:
1. Bajar `index.json` (o `index.json.xz` y descomprimirlo: el resultado es el mismo archivo), y guardarlo como está.
2. Bajar `compatible.json` y los archivos de los fabricantes que se quieran (o todos).
3. Comprobar el tamaño y el SHA-256 de cada uno contra el índice. Si no coinciden, descartarlo.
4. Descomprimir cada `.tar.xz` en la carpeta del paquete. Adentro solo hay rutas relativas `vendors/<id>/…`,
   `community/…`, `knowledge/…` o `translation/…`. Una ruta absoluta, con `..` o que no empieza así no se
   descomprime.
5. Una versión nueva se reconoce porque `pack_version` del índice cambió.

**Tamaño de la versión del 05-11-2026:**
- `index.json`: unos 2,1 MB;
- cada fabricante: de unos KB a 2,7 MB;
- todo junto: unos 33 MB, en 243 archivos (con `stats.json`).

## `index.json`

| Clave | Qué es |
|---|---|
| `format`, `version` | `"tisma-profile-pack"` y `2`. Una versión mayor que la conocida no se carga |
| `pack_version` | La versión de este paquete (`AAAA.MM.DD-commit`) |
| `generated` | Fecha y hora de la conversión (UTC), o la de `SOURCE_DATE_EPOCH` si está definida (la CI usa la del commit) |
| `source`, `other_sources` | De dónde salieron los perfiles: repositorio, commit y carpeta de Tisma Slicer y de UVtools |
| `license` | `AGPL-3.0-or-later` (ver «Licencias») |
| `vendors` | Los fabricantes (abajo) |
| `printers` | Todas las impresoras como `<archivo del modelo>#<variante>`, en orden: el número de una impresora es su lugar en esta lista (para `compatible.json`) |
| `compatible`, `community`, `translation_archive` | Nombre, tamaño y SHA-256 de esos archivos |
| `translation` | La ruta de la tabla de traducción de cada dialecto, dentro de la carpeta del paquete: `{"prusaslicer": "translation/prusaslicer.json", …}` |
| `counts` | Cuentas de la conversión |

**Un fabricante** (`vendors[i]`):

| Clave | Qué es |
|---|---|
| `id` | Identificador del paquete de origen; también el nombre del archivo comprimido y de su carpeta |
| `name` | Nombre para mostrar |
| `license`, `origin` | La licencia y de qué programa salieron sus perfiles |
| `models` | Modelos de impresora (abajo) |
| `printers` | Sus impresoras, como en `index.json` |
| `filaments`, `prints`, `resins`, `resin_prints` | Rutas de cada perfil, dentro de la carpeta del paquete |
| `archive` | Nombre, tamaño y SHA-256 de su archivo comprimido |
| `counts` | Cuántos de cada cosa |

**Un modelo** (`models[i]`): `id`, `name`, `technology` (`fff` o `sla`), `family`, `default_materials` (nombres),
`assets` (rutas de `bed_model` en STL, `bed_texture` en SVG o PNG y `thumbnail` en PNG, si las hay), `file` (su archivo,
abajo), `variants` (`id` y `nozzle` de cada una) y `default_variant`. `from_source_program` (también en el archivo del
modelo), cuando el paquete de Tisma Slicer perdió algo del modelo que su programa de origen tiene (su `machine_model`):
qué campos salen de ahí (`family`, `default_materials`, `assets.thumbnail`, `assets.bed_model`, `assets.bed_texture`).
Pasa en los 12 modelos de Creality Print y Elegoo Slicer, cuyo paquete no guarda imágenes ni materiales.
En los modelos de UltiMaker Cura, `assets.bed_model` es la malla de la cama de su definición (`platform`), convertida al
marco de las demás camas (mm, Z hacia arriba, X e Y de la impresora, el centro de la cama donde lo tiene su polígono)
como la coloca Cura: un punto (x, y, z) de un STL u OBJ es (x, z, -y) en su escena (Y hacia arriba); de un 3MF, los
vértices del objeto con más caras tal como están; después el desplazamiento `platform_offset`, y un punto de la escena
(x, y, z) es (x, -z, y) en la impresora. Se escribe en STL binario, sin reducir. Entra solo si tiene su placa (caras
hacia arriba a menos de 3 mm de Z 0) bajo la mitad de la cama por lo menos: 151 modelos; 8 quedan sin cama. Suma unos
6 MB al paquete comprimido y unos 50 MB descomprimido.

## Un modelo de impresora (`vendors/<id>/models/<nombre>.json`)

Cada modelo aparece una sola vez. Sus boquillas (o variantes: alto flujo, modo silencioso…) no repiten lo que
comparten:

```json
{
 "format": "tisma-pack-model",
 "version": 2,
 "technology": "fff",
 "vendor": "…",
 "model": { "id": "…", "name": "…", "family": "…" },
 "default_variant": "0.4",
 "common": { "settings": { }, "gcode": { } },
 "variants": [ { "id": "0.4", "nozzle": 0.4, "name": "…", "settings": { }, "gcode": { }, "defaults": { },
                 "original": { } } ],
 "original_common": { },
 "also_in": [ ],
 "license": "AGPL-3.0-or-later",
 "origin": "…"
}
```

- **El perfil de una variante** es `common.settings` con `settings` de la variante encima (grupo por grupo, clave por
  clave). Se arma con `profile.kind` `printer` y el `name` de la variante.
- **`default_variant`:** la boquilla de 0,4 mm si hay una que no es de alto flujo; si no, la primera.
- **`defaults`:** rutas de los filamentos (`filament`, el primero es el que se elige) y del perfil de impresión
  (`print`) o, en resina, de `resin` y `resin_print`. Si el de origen no existía, el primero compatible del mismo
  paquete, después de un paquete de la misma marca, después de cualquiera.
- **`original_common` y `original` de cada variante:** los valores de origen, divididos igual.
- **`also_in`:** el mismo modelo venía de otra fuente (por ejemplo, de OrcaSlicer y del paquete del fabricante). Se
  guarda una vez, de la fuente del fabricante; las impresoras de la otra fuente apuntan a la variante de la misma
  boquilla. Si el modelo no tiene esa boquilla, la impresora de la otra fuente es una variante más, con su `license` y
  su `origin` propios (6 con la versión del 05-11-2026, por ejemplo la AnkerMake M5 con 0,2 y 0,25 mm).
- **`gcode`** (en `common` y en cada variante, FFF): el G-code propio de la máquina tal cual lo tiene su fuente, con
  sus macros (ver «G-code de la máquina»). Se arma igual que el perfil: `common.gcode` con el `gcode` de la variante
  encima, campo por campo y, en `templates`, `keys`, `from` y `values`, clave por clave.
- **`not_converted`** (en una variante): el G-code de inicio o de fin que no se pudo pasar a las variables simples de
  `profile`, con el motivo. Ese G-code está igual, entero, en `gcode`.

## Un perfil de filamento, impresión o resina (`vendors/<id>/<grupo>/<nombre>.json`)

```json
{
 "format": "tisma-pack-entry",
 "version": 2,
 "technology": "fff",
 "vendor": "Prusa Research",
 "profile": { "format": "tisma-profile", "version": 1, "kind": "printer", "name": "…", "settings": { } },
 "license": "AGPL-3.0-or-later",
 "origin": "…",
 "original": { }
}
```

- **`profile`:** un perfil del motor tal cual: se puede guardar como archivo de perfil o elegir. `kind` es
  `filament` o `print`. En resina, `resin` (los ajustes `resin.*` del material) o `resin_print`.
- **`original`:** todos los valores del perfil de origen, con la herencia resuelta y con los nombres del programa de
  origen. Están para no perder nada y para convertir más ajustes en versiones futuras del paquete. El motor no los
  interpreta.
- **Filamentos, impresión y resinas:**
  - `compatible`: el número de un conjunto de `compatible.json`, o `null` si no se sabe (sirve para todas);
  - `generic`: el perfil es genérico (de un paquete de plantillas), no de un fabricante.
- **Filamentos:** `material` con `type` (PLA, PETG…), `vendor`, `density` (g/cm³), `cost_per_kg`, `colour` y
  `soluble`.
- **Impresión:** `nozzle`, la boquilla para la que está hecho (en mm), cuando lo dice:
  1. la boquilla de todas sus impresoras, si es una sola;
  2. si no, la condición de origen, cuando pide `nozzle_diameter[0]==X` para todas (sin `or`);
  3. si no, su nombre («0.2 nozzle», «0.6mm nozzle», «nozzle 0.4»), si sus impresoras no dicen otra cosa.

  Sin `nozzle`, el perfil sirve para cualquier boquilla de sus impresoras.
- **Filamentos:** `gcode`, si el perfil trae G-code de inicio o de fin de filamento: el mismo bloque que el de la
  máquina, con `filament_start` y `filament_end` (ver «G-code de la máquina»). En la familia OrcaSlicer sale del
  programa de origen, en su dialecto (`origin` `source_program`), con los nombres viejos que el programa cambia al
  cargarlo ya cambiados (Creality Print: `initial_layer_height` por `first_layer_height`). Si el programa de origen no
  le da G-code (vacío), el filamento no trae `gcode`. Con la versión del 05-11-2026, 3741 filamentos de OrcaSlicer y
  316 de Creality Print, y 90 sin G-code.
- **`compatible_prints`** (filamentos): solo en un filamento que su fuente limita a algunos perfiles de impresión
  (`compatible_prints`, una lista de nombres, o si no `compatible_prints_condition` sobre los valores de la impresión,
  como `infill_speed >= 150` o `notes=~/.*SOLUBLE_SUPPORT.*/`): las rutas de los perfiles de impresión del paquete con
  los que sirve. Como en PrusaSlicer, con otra impresión el filamento no se ofrece. Con esta versión, 17 filamentos
  (Artillery X3/X4, Geeetech Thunder, HartSmart). `check_pack` falla si el filamento por defecto de una impresora no
  sirve con su impresión por defecto.
- **`source_values`** (filamentos), con `dialect`, `preset` y `values`: los valores del filamento para las variables
  que usa el G-code de las máquinas de ese dialecto. En los paquetes de PrusaSlicer, los de la sección del paquete,
  con su tipo (como `values`), también para su propio G-code de filamento (por ejemplo `filament_abrasive`, `filament_notes`). En la
  familia OrcaSlicer, los del mismo perfil en el programa de origen, con sus nombres (por ejemplo `temperature_vitrification`, `additional_fan_full_speed_layer`
  y `close_additional_fan_first_x_layers` de las Bambu Lab, que el paquete de Tisma Slicer no guarda). Con la versión
  del 05-11-2026, 7199 filamentos de paquetes de PrusaSlicer, 4121 de OrcaSlicer y 316 de Creality Print.
- **`source_values`** (impresiones de la familia OrcaSlicer), con `dialect`, `preset` y `values`: los valores del mismo
  perfil en el programa de origen para las variables que usa el G-code de las máquinas de ese dialecto y que
  PrusaSlicer no tiene (por ejemplo `outer_wall_acceleration`, `timelapse_type`, `print_sequence`); las que PrusaSlicer
  tiene salen de los ajustes traducidos de la impresión. Van, como las del filamento, en las variables del G-code de la
  máquina. Una lista de números de OrcaSlicer usada donde se espera un número (`{if outer_wall_acceleration > 0}`) vale
  la del extrusor en uso, o la única si hay una (así lo hace OrcaSlicer).
- **`source_over_bundle`** (en un filamento o un perfil de impresión de la familia OrcaSlicer): las claves del paquete de
  Tisma Slicer (nombres de PrusaSlicer) cuyo valor no es el que da el perfil del programa de origen pasado por el
  conversor de Tisma Slicer, como `{"clave": {"bundle": …, "source": …}}`. Vale el del origen (el perfil se comporta
  como en su programa): `profile.settings` es la traducción de `original` con esos valores. `stats.json`
  (`source_over_bundle`) los lista todos con el perfil. En un perfil de impresión para cualquier boquilla, los anchos
  de línea quedan como el paquete los tiene (ver abajo).
- **`kept_from_bundle`** (mismo formato que `source_over_bundle`): las claves que quedan como el paquete de Tisma
  Slicer las tiene aunque el programa de origen da otro valor, porque el motor no acepta el del origen. Hoy solo el
  borde (`brim_width`) de una impresión para impresoras de cinta: VertexSlice imprime 5 mm y el motor no pone borde en
  la cinta (spec `belt_printer.md`, regla 4). Queda anotado por si el motor lo admite más adelante.
- **`machine.flavor_choices`** (en `profile.settings` de una impresora): los firmwares entre los que el usuario
  elige, cuando el programa de origen no dice cuál. Hoy solo las impresoras de Cura con `machine_gcode_flavor`
  «RepRap (Marlin/Sprinter)»: `machine.flavor` es `"marlin"` (Marlin 2), el que vale si el usuario no elige, y
  `flavor_choices` es `["marlin_legacy", "marlin"]` (decisión del dueño del 11-11-2026; spec PF15). PrusaSlicer y la
  familia OrcaSlicer distinguen los dos (`marlin` es «Marlin (legacy)» y `marlin2` «Marlin 2»), así que ahí no va.
- **Perfiles de impresión por boquilla:** un perfil del origen para impresoras de varias boquillas cuyos anchos son un
  porcentaje de la boquilla de cada una (OrcaSlicer: `line_width = 105%`) se escribe una vez por boquilla, con el mismo
  nombre, `nozzle` y sus impresoras de esa boquilla, y los anchos en mm que da el origen para ella; la ruta lleva la
  boquilla (`…_0.4mm.json`). El perfil por defecto de cada impresora es el de su boquilla.
- **`from_source_program`** (en un filamento o en una variante de impresora): las claves del perfil (`grupo.clave`)
  que no salen de la traducción del paquete de Tisma Slicer porque el paquete las perdió: las temperaturas de la
  boquilla de 3 filamentos de la UltiMaker 2 extended+ y la boquilla de 3 de sus variantes, la altura de 9
  impresoras (por ejemplo la Meltingplot MBL 480), y los límites por eje (`max_feed_*`, `max_accel_*`, `jerk_*`,
  `corner_speed`) de 857 variantes de la familia OrcaSlicer, más la retracción y otros valores de las 6 que el paquete
  dejó casi vacías (Elegoo Neptune, UltiMaker 2 extended+), del programa de origen, traducidos como los del paquete
  (con el conversor de Tisma Slicer, que convierte el perfil entero: nombres, unidades, bases de los porcentajes,
`brim_type`…; las opciones que ese conversor no conoce, los límites por eje de la máquina, por nombre:
`machine_max_speed_*` es `machine_max_feedrate_*`; un valor que el programa llama de otro modo toma el nombre de
  PrusaSlicer por la constante de los dos `PrintConfig.cpp`, como la costura `back`, que es `rear`, y uno sin
  equivalente no se escribe); y la boquilla de la Anycubic i3 Mega y la Mega S, de su
  variante en el paquete («0.4»). Un límite de velocidad o de aceleración por eje que vale 0 no se escribe. En
  filamentos e impresiones de la familia OrcaSlicer, lo mismo: 37 impresiones (Artillery, Elegoo, UltiMaker) y 11
  filamentos (Snapmaker U1, UltiMaker 2 extended+) que el paquete dejó casi vacíos toman del programa de origen los
  valores que su perfil allí da (por ejemplo la altura de la primera capa). `material.*` también puede salir de ahí.

## `compatible.json`

```json
{ "format": "tisma-pack-compatible", "version": 1, "sets": [[0, 1, 2], [5, 9]] }
```

Cada conjunto es una lista de números de impresora (`index.json`, `printers`). Un filamento con `"compatible": 1`
sirve para las impresoras 5 y 9. Muchos perfiles comparten conjunto: hay unos 1700 para más de 16 000 perfiles.

- **Nunca hay un conjunto vacío.** Un perfil que no sirve para ninguna impresora del paquete no entra; queda en
  `stats.json`, `left_out`, con su condición o con las impresoras que nombra el programa de origen
  (`source_printers`). Con la versión del 05-11-2026 son 83 (67 de impresión, 15 filamentos y 1 de impresión de
  resina): condiciones que ninguna impresora cumple ni en el programa de origen, y perfiles para boquillas de un
  modelo que el paquete tiene con otras (por ejemplo, la Neptune 3 Max solo con 0,4 mm).
- **De la familia OrcaSlicer** (OrcaSlicer, Creality Print, Elegoo Slicer): la lista de impresoras sale del programa
  de origen, heredada de los padres como cualquier otro valor (así lo hace el programa). El paquete de Tisma Slicer la
  dejaba vacía en los perfiles que solo la heredan, y entonces servían para todas las impresoras de la marca, o le
  sumaba impresoras que el origen no nombra. Una impresora que Tisma Slicer guardó del paquete del fabricante (el
  mismo modelo de dos fuentes) se busca por modelo y boquilla. Con la versión del 05-11-2026, 6551 perfiles toman la
  lista del origen, y 2012 cambian de impresoras (1906 a menos).
- **Perfiles fusionados:** OrcaSlicer repite un perfil para cada impresora de una familia, y el conversor de Tisma
  Slicer guarda uno solo de los que tienen el mismo nombre base (antes de « @») y los mismos valores convertidos, para
  las impresoras de todos («0.20mm Standard @BBL X1C» queda como «0.20mm Standard @BBL P1P», también para la P1S, la
  X1 y la X1C). La lista suma las impresoras de todo el grupo, que se forma con ese mismo conversor
  (`tools/profiles/convert_orca_profiles.py` de Tisma Slicer, en el commit de los paquetes). 252 perfiles de
  impresión y 1452 filamentos suman impresoras así.
- **Perfiles que el paquete no trae:** un perfil de impresión del programa de origen para impresoras del paquete que
  no está en el paquete de Tisma Slicer, ni fusionado en uno que esté, se convierte con ese mismo conversor y entra
  con `from_source_program: ["*"]` y `source_preset` (`program`, `repository`, `commit`, `file` y `merged`, los
  presets de su grupo). Con esta versión es uno: «0.15mm Standard @UltiMaker 2 extended+ 0.6 nozzle».
- **Las condiciones** se evalúan como en el programa de origen: `num_extruders` es la cantidad de boquillas, un número
  escrito como texto (`"0.2"`) se compara como número, los textos tienen sus saltos de línea, y `=~` pide que la
  expresión regular cubra todo el valor, con `.` que también toma saltos de línea.

## G-code de la máquina (`gcode`, con macros)

Cada impresora FFF trae su G-code propio **tal cual** lo tiene su fuente, con el lenguaje de macros del programa de
origen (condiciones, cuentas, variables). Es lo que hace la nivelación, el Z offset, la calibración de flujo o la
limpieza de la boquilla de cada modelo. El motor lo interpreta (especificación de macros del motor,
`gcode_macros.md`).

**Las claves que tienen G-code con macros, sin tocar,** son las de `gcode.templates` (en los modelos y en los
filamentos). Ninguna otra clave del paquete tiene macros: `profile.settings.machine.start_gcode` y `end_gcode` siguen
siendo la versión con variables simples (abajo).

| Campo | Qué es |
|---|---|
| `dialect` | El lenguaje de macros y los nombres de las variables: `prusaslicer`, `orcaslicer`, `crealityprint`, `elegooslicer` o `cura` |
| `origin` | De dónde sale: `source_program` (los archivos del programa de origen, en el commit que nombra el paquete de Tisma Slicer), `bundle` (un paquete en formato PrusaSlicer, tal cual) o `converted_bundle` (el paquete que convirtió Tisma Slicer, con las variables ya con nombres de PrusaSlicer, cuando el programa de origen no lo tiene) |
| `source` | `repository`, `commit` y `preset` (el perfil o la definición de origen), o `bundle` y `section`; en `converted_bundle`, también `program`, `repository` y `commit` del programa del que salió |
| `templates` | El G-code, por nombre (tabla de abajo). Texto; en `cura`, `extruder_start` y `extruder_end` son una lista, uno por extrusor (`null` si no tiene) |
| `keys` | El nombre de origen de cada uno |
| `from` | El archivo o la sección de origen que lo define (después de la herencia y de los `include` de OrcaSlicer) |
| `relative_extrusion` | Si el programa de origen extruye en relativo con este G-code (`null` si no lo dice). En `cura` es casi siempre `false`: su G-code de inicio pone `M82`. Al usar `templates`, el motor extruye como dice este campo |
| `values` | Los valores de la máquina para las variables de sus macros. En `source_program` de la familia OrcaSlicer, todos los de la máquina en el programa de origen, con sus nombres (listas como listas). En `bundle` y `converted_bundle`, los de la sección del paquete que usan su G-code y el G-code de los filamentos, con el tipo que les da PrusaSlicer (su `PrintConfig.cpp`, el de Tisma Slicer en el commit de los paquetes): sí/no, números, textos y listas; como texto si el tipo no se conoce |
| `program_defaults` | Solo en `source_program` de la familia OrcaSlicer: las claves de `values` que el perfil no dice y que salen del valor por defecto del programa (su `PrintConfig.cpp`, en el commit de origen), como hace el programa al laminar; solo opciones de la máquina que usa el G-code de la máquina o de los filamentos (por ejemplo `support_air_filtration`) |
| `expressions` | Solo en `cura`: el G-code que Cura calcula con una expresión (`value`) en vez de un texto. No está en `templates` |

**Nombres de `templates`** (otras claves de G-code del origen quedan con su nombre):

| Nombre | `prusaslicer` | `orcaslicer`, `crealityprint`, `elegooslicer` | `cura` |
|---|---|---|---|
| `start` | `start_gcode` | `machine_start_gcode` | `machine_start_gcode` |
| `end` | `end_gcode` | `machine_end_gcode` | `machine_end_gcode` |
| `before_layer_change` | `before_layer_gcode` | `before_layer_change_gcode` | |
| `layer_change` | `layer_gcode` | `layer_change_gcode` | |
| `toolchange` | `toolchange_gcode` | `change_filament_gcode` | |
| `between_objects` | `between_objects_gcode` | `printing_by_object_gcode` | |
| `color_change` | `color_change_gcode` | | |
| `pause` | `pause_print_gcode` | `machine_pause_gcode` | |
| `custom` | `template_custom_gcode` | `template_custom_gcode` | |
| `timelapse` | | `time_lapse_gcode` | |
| `extrusion_role_change` | | `change_extrusion_role_gcode` | |
| `filament_start`, `filament_end` (filamentos) | `start_filament_gcode`, `end_filament_gcode` | | |
| `extruder_start`, `extruder_end` | | | `machine_extruder_start_code`, `machine_extruder_end_code` |

**Por qué del programa de origen:** Tisma Slicer convirtió los perfiles de OrcaSlicer, Creality Print, Elegoo Slicer y
Cura a su formato, y en eso perdió G-code: no siguió los `include` de OrcaSlicer (cada Bambu Lab tiene su G-code en
plantillas aparte), así que todas las Bambu Lab quedaban con el G-code genérico de la base, y muchas otras con el de
otro modelo de la misma base. Por eso el convertidor lee esos programas en el commit que dice cada paquete
(`sources.json`, `converted_from`). Los paquetes que ya eran de PrusaSlicer entran tal cual.

**Laminador del fabricante (`sources.json`, `official`):** cuando el fabricante tiene su propio laminador de la
familia OrcaSlicer, sus perfiles reemplazan a los de OrcaSlicer (regla del dueño; la página o la hoja técnica del
fabricante solo sirven para cotejar). `tools/fetch_sources.py` baja ese programa en su commit, lo convierte con el
mismo conversor de Tisma Slicer (`convert_orca_profiles.py --prefix … --source … --url …`) y le pasa a
`tools/convert.py` `--official-bundle <paquete>.ini=<el que reemplaza>`; el programa de origen de esos perfiles es el
del fabricante. Reemplaza modelo por modelo: del paquete reemplazado salen los modelos que tiene el del fabricante
(el mismo nombre sin las palabras de la marca), sus impresoras y los perfiles de impresión y filamentos que el del
fabricante tiene con el mismo nombre o que solo eran para esas impresoras; sus otros modelos quedan. Si el paquete
propio del fabricante en formato PrusaSlicer también tiene el modelo, vale ese, como antes, y el del laminador solo
agrega las boquillas que le faltan. Hoy: Bambu Lab desde Bambu Studio (`BambuStudio_BBL`, en lugar de `Orca_BBL`) y
QIDI desde QIDI Studio (sus cuatro series, en lugar de los modelos de `Orca_Qidi` que tiene; la X-CF Pro, la X-Max y la
X-Plus siguen de OrcaSlicer, y las Q1 Pro, X-Max 3, X-Plus 3, X-Plus 4 y X-Smart 3 de `QIDITechnology`) y Anycubic
desde Anycubic Slicer Next (14 modelos; Kobra 3 Max, Kobra 3 V2, Kobra Neo, Kobra S1 Max y Kobra X, que no tiene,
siguen de OrcaSlicer), Flashforge desde Orca-Flashforge, y Creality y Elegoo desde Creality Print y Elegoo Slicer (los
mismos commits que `converted_from`): Creality Print reemplaza a la vez los modelos de `Orca_Creality` y los de
`CrealityPrint_Creality` (el paquete de Tisma Slicer con los modelos que OrcaSlicer no tenía; `replaces` es una lista,
y `--official-bundle` toma varios nombres separados por comas). Un perfil del paquete reemplazado del que hereda otro que
queda, queda también. Un modelo del laminador del fabricante que no se puede usar (una impresora sin boquilla en mm o
sin un perfil de impresión propio) queda del paquete reemplazado: en Orca-Flashforge c45cc82 la Guider 2s solo tiene
plantillas de impresión y las boquillas HF de las Guider4 y Guider4 Pro dicen «0.6HF»; las tres siguen de OrcaSlicer
(`counts`, «official models left as the replaced bundle has them»). `stats.json`
(`official_over_replaced`) anota cada diferencia con el paquete reemplazado, preset por preset
(`{official, replaced, kind, name, key, replaced_value, official_value}`), y `counts` los presets que solo están en
uno de los dos. Los filamentos de la biblioteca de OrcaSlicer que nombran una impresora reemplazada siguen siendo
compatibles con la del fabricante del mismo nombre.

**Variables de los filamentos y la impresión:** los perfiles de filamento y de impresión siguen con los nombres de
PrusaSlicer (`original`). Un G-code `orcaslicer` usa los nombres de OrcaSlicer (`nozzle_temperature_initial_layer`
por `first_layer_temperature`, `bed_temperature_initial_layer_single` por `first_layer_bed_temperature`…).

**Las variables de cada dialecto** están en `docs/GCODE_VARIABLES.md`: una tabla por dialecto con cada variable que
usan los G-code del paquete (contadas en el paquete convertido), su tipo y qué es según las definiciones del programa
de origen, en qué G-code aparece y su nombre en PrusaSlicer. La genera `tools/gcode_variables.py` con cada versión
nueva del paquete; no se edita a mano.

Con la versión del 11-11-2026, de los 2317 perfiles de impresora FFF de origen: 903 de OrcaSlicer (uno es la
IdeaFormer IR3 V2 de VertexSlice, una variante de OrcaSlicer para impresoras de cinta con sus mismos nombres, por eso
con el dialecto `orcaslicer` y `source.repository` de VertexSlice), 17 de Creality Print (con la CR-30 PrintMill, que
allí se llama «Creality CR-30 0.4 nozzle»), 1 de Elegoo Slicer y 296 de Cura salen del programa de origen; 1060 de
paquetes de PrusaSlicer; 40 del paquete convertido: las de BlackBelt, porque su G-code en BlackBelt Cura usa
`{blackbelt_z_offset}`, que solo calcula ese programa a partir del ancho de pared, el ángulo y la separación; el
paquete de Tisma Slicer lo trae ya calculado para cada variante.

Una impresión para impresoras de cinta conserva el borde (brim) del paquete: VertexSlice imprime los 5 mm de su
proceso genérico, pero el motor no acepta un borde en una impresora de cinta.

## G-code de inicio y de fin con variables simples (`profile`)

- **Tal cual:** el G-code de inicio y de fin de una impresora entra en `profile.settings.machine` solo si funciona con
  las variables simples del motor (`[nombre]`, `{nombre}`, `{nombre[i]}`). Sale del mismo texto que `gcode` (con las
  variables de OrcaSlicer pasadas a los nombres de PrusaSlicer, como hace Tisma Slicer), salvo en Cura, que usa el
  del paquete convertido.
- **Valores fijos:** los que salen del perfil de la impresora (boquilla, modelo, tamaño de la cama…) se escriben en el
  texto al convertir.
- **Temperaturas:** quedan como variables que llena el perfil del filamento: `temperature`, `first_layer_temperature`,
  `bed_temperature`, `first_layer_bed_temperature`, `chamber_temperature`, `chamber_minimal_temperature` e
  `idle_temperature`.
- **Valores del laminado**, con estos nombres propios del paquete:

| Variable | Qué es |
|---|---|
| `first_layer_min_x`, `first_layer_min_y`, `first_layer_max_x`, `first_layer_max_y` | Caja de lo que se imprime en la primera capa, en mm |
| `first_layer_size_x`, `first_layer_size_y` | Su tamaño |
| `layer_count` | Cantidad de capas |
| `initial_tool` | El extrusor que empieza (0 con uno solo) |
| `travel_speed` | Velocidad de viaje, mm/s |
| `layer_height`, `first_layer_height` | Alturas de capa, mm |
| `year`, `month`, `day`, `hour`, `minute`, `second` | Fecha y hora del laminado |
| `input_filename_base` | Nombre del modelo, sin la extensión |

- **Lo que no entra:** un G-code con condiciones o cuentas (el lenguaje de macros del programa de origen) no entra en
  `profile`: queda entero en `gcode`, y el motivo en `not_converted`.
- **Cuántos entran:** con la versión del 05-11-2026, el de inicio de 1277 de 2317 perfiles de impresora de origen
  (antes 1334: ahora salen del G-code verdadero de cada modelo, y en 57 ese tiene macros).

## Traducción de claves (`translation/<dialecto>.json`)

Para abrir proyectos de otros programas (3MF de PrusaSlicer, OrcaSlicer, Creality Print, Elegoo Slicer o Cura), el
motor traduce sus ajustes con las mismas reglas que usa el convertidor: un archivo por dialecto, en
`translation.tar.xz`, con las rutas en `index.json`, `translation`. La tabla está en `tools/translation.py`, el
convertidor la aplica a cada perfil, y `tools/check_pack.py` comprueba que, aplicada al `original` de cada perfil del
paquete, da exactamente su `profile.settings`.

```json
{
 "format": "tisma-pack-translation",
 "version": 1,
 "dialect": "orcaslicer",
 "source": { "how": "…", "presets": { "printer": 902, "print": 2280, "filament": 4121 } },
 "kinds": {
  "print": {
   "wall_loops": { "engine": "walls.count", "group": "translated", "conversion": { "how": "number" },
                   "prusaslicer": "perimeters", "seen": [2218, 2276] },
   "bridge_flow": { "engine": null, "group": "none", "prusaslicer": "bridge_flow_ratio", "seen": [2202, 2268] }
  }
 }
}
```

- **`kinds`:** `printer`, `filament`, `print` y, en `prusaslicer`, `resin_printer`, `resin` y `resin_print`. Adentro,
  cada clave de origen que tienen los perfiles de ese programa.
- **`engine`:** la clave del motor (`grupo.clave`), o varias separadas por coma cuando una regla escribe más de una;
  `null` si no hay equivalente.
- **`group`:** `translated` (el mismo ajuste), `similar` (lo más parecido que tiene el motor; `note` dice en qué
  difiere) o `none` (sin equivalente).
- **`conversion`:** `how` y sus datos:

| `how` | Qué hace |
|---|---|
| `number` | El número (el primero de una lista). `nonzero`: no se escribe si es 0; `positive`: solo si es mayor que 0; `nonnegative`: no se escribe si es negativo; `max`: no se escribe si es mayor |
| `numbers` | La lista de números, uno por extrusor; `nonnegative`: no se escribe si alguno es negativo |
| `flag` | `1` o `true` es verdadero (el primer extrusor); solo si la clave está; `invert`: al revés |
| `factor` | El número por `factor` (no se escribe si es 0) |
| `map` | El valor por la tabla `values` (desconocido: no se escribe); `only`: solo esos resultados; `exclude`: esos no |
| `percent_of` | `"N%"` es ese porcentaje de la clave del motor `base` (ya traducida); un número queda como está |
| `first_item` | El texto del primer extrusor |
| `number_strip_percent` | El número sin el `%`; `nonnegative` y `max` como en `number` |
| `number_or_percent` | `"N%"` queda como texto; si no, el número; `nonzero`: no se escribe si es 0; `bare_percent_over`: un número sin `%` mayor que este es `"N%"` |
| `absolute_only` | El número; un porcentaje no se escribe |
| `percent_only` | El número de un `"N%"`; un número sin `%` no se escribe |
| `at_least` | El número si es al menos `min` |
| `points` | `"XxY,XxY,…"` como lista de puntos, con 3 o más |
| `rule` | Una conversión con sus pasos, por nombre (`rule`), descrita en `note`: `acceleration`, `fans`, `wall_width`, `role_width` (el ancho de un tipo de línea en mm: el suyo, si es 0 `extrusion_width`, y si los dos son 0 el automático del programa de origen solo donde el 0 del motor es otro, `auto` veces la boquilla), `xy_gap`, `extruders` (con dos boquillas o más: `machine.extruders`, la lista de boquillas si difieren y `machine.extruder_offset` si alguna no es 0, salvo con una MMU de una boquilla), `junction_deviation` (solo con `marlin2`), `gap_fill`, `limits_usage`, `correction`, `resin_notes`, `gcode_template` |

- **`with`:** las otras claves que usa la misma regla (nombres de PrusaSlicer).
- **Los otros dialectos** pasan cada clave a su nombre de PrusaSlicer (`prusaslicer`) y usan su traducción. El nombre
  sale de los mismos perfiles en el programa de origen y en el paquete de Tisma Slicer: la clave tiene el mismo valor
  con ese nombre en al menos el 90 % de los perfiles, también donde el valor no es el más común (para no confundir
  dos claves que casi siempre valen 0). `seen`: en cuántos perfiles coincide y en cuántos está. Si Tisma Slicer
  cambió también los valores, `prusaslicer_values` da cada valor de origen con el suyo (por ejemplo, el relleno
  `crosshatch` de OrcaSlicer es `grid`), también en una clave que conserva su nombre (la costura `back` de OrcaSlicer
  es `rear`; ahí, un valor que no aparece se escribe igual en PrusaSlicer). Una clave sin `prusaslicer` no tiene un
  nombre que los perfiles muestren.
- **Nombres que los valores no muestran** (familia OrcaSlicer): el conversor de Tisma Slicer cambia el valor, así que
  la comparación no los encuentra; van escritos en la tabla. Los anchos de línea (`line_width`,
  `outer_wall_line_width`, `inner_wall_line_width`, `initial_layer_line_width`, `sparse_infill_line_width`,
  `internal_solid_infill_line_width`, `support_line_width`, `top_surface_line_width`) llevan **`percent_of`**
  `"nozzle"`: en OrcaSlicer un `"N%"` es de la boquilla, y se pasa a mm con la del proyecto antes de la traducción de
  PrusaSlicer, donde un `"N%"` es de la altura de capa (spec PF12). `seam_slope_type` es `scarf_seam_placement`, con
  `prusaslicer_values` (`external`: `contours`, `all`: `everywhere`).
- **Nombres del conversor de Tisma Slicer:** una clave de la familia OrcaSlicer que la comparación no nombra y que el
  conversor de Tisma Slicer renombra toma ese nombre (con sus valores renombrados: los patrones de relleno y la
  costura), con **`renamed_by`** `"converter"`; por ejemplo `outer_wall_speed` de Creality Print. Las aceleraciones,
  que allí pueden ser `"N%"` de la aceleración por defecto, llevan `percent_of` `"acceleration.default"`: el
  porcentaje se pasa a número con la del proyecto antes de traducir (spec PF13; `percent_of` nombra una clave del motor
  o `"nozzle"`).
- **`plate_temperature`** (tablas de la familia OrcaSlicer): la temperatura de cama va por tipo de placa
  (`hot_plate_temp`, `textured_plate_temp`…, cada una con su `_initial_layer`). Arriba de la tabla, `plate_temperature`
  da `plates` (placa: [clave de la cama, clave de la primera capa]), `select` (las claves que nombran la placa:
  `curr_bed_type` del proyecto, si no `default_bed_type`), `index` (los nombres de las placas por número) y `order`
  (las claves a probar, en orden, si ninguna placa está nombrada). Cada clave de placa lleva `rule` `"plate_temperature"`,
  su `plate` y el nombre de PrusaSlicer (`bed_temperature` o `first_layer_bed_temperature`): vale la de la placa del
  proyecto (spec PF14), como el conversor de Tisma Slicer elige la de la placa de la impresora.
- **Solo lo que significa lo mismo:** una clave entra con el sentido y las unidades que le dan PrusaSlicer (su
  `PrintConfig.cpp`) y el motor (`docs/CONFIG.md` del motor, desde `dev` b3f296b). Si el valor de origen no tiene
  equivalente en el motor, no se escribe y `note` lo dice (por ejemplo, el ancho de la pared externa en %).
- **Con poca base:** Elegoo Slicer tiene una sola impresora en el paquete y Cura solo impresoras: casi todas sus
  claves quedan `none`.

Con la versión del 05-11-2026:

| Dialecto | Claves | Al motor | Con nombre de PrusaSlicer |
|---|---|---|---|
| `prusaslicer` | 806 | 171 | — |
| `orcaslicer` | 881 | 116 | 205 |
| `crealityprint` | 509 | 80 | 147 |
| `elegooslicer` | 90 | 0 | 0 |
| `cura` | 739 | 3 | 3 |

## Calidad

`tools/validate.py` lamina un cubo de 20 mm con el motor con cada variante FDM y su filamento y perfil por defecto, y
después con cada filamento y cada perfil de impresión en la primera impresora compatible. Con la versión del
10-11-2026 y el motor de `dev` (b926456):
- **variantes:** las 2267 laminan, también con el G-code propio de cada máquina (`--macros`), y en las 2255 que leen
  su G-code propio cada línea fija de su G-code de inicio y de fin sale igual y en el mismo orden (GM13);
- **todo:** 18 325 combinaciones, 16 fallan (0,09 %), por datos del programa de origen, que tampoco las lamina. 11 son
  perfiles de impresión con capas más gruesas que la boquilla de su impresora (CR-10 SE y LONGER LK10 de 0,2 mm, Voron
  de 0,25 y 0,3 mm), y 5 de capas de 0,2 mm en boquilla de 0,2 mm (LNL3D D3, LONGER LK10) cuya pared exterior de
  0,2 mm no es más ancha que la capa, lo que Tisma Slicer exige.

`tools/check_pack.py` revisa el paquete convertido y la CI falla si encuentra:
- un conjunto de compatibilidad vacío, o un perfil que apunta a uno que no existe;
- un G-code de inicio que comparten modelos distintos por error: sale del paquete convertido de Tisma Slicer cuando el
  programa de origen se puede leer (lo que pasaba con las Bambu Lab). Los modelos que comparten la base general del
  fabricante porque así están en el programa de origen quedan como notas;
- un perfil de impresión sin `nozzle` cuando su nombre o su condición dicen una boquilla;
- un bloque `gcode` sin dialecto conocido o con plantillas que no son texto.
- una variante FFF sin ningún perfil de impresión o filamento compatible.

## Licencias

Los perfiles vienen de programas con licencias libres, y cada perfil y cada fabricante dicen la suya:
- **PrusaSlicer, OrcaSlicer, Creality Print y Elegoo Slicer**, a través de Tisma Slicer: AGPL-3.0;
- **UVtools** (impresoras de resina y perfiles universales de impresión de resina): AGPL-3.0;
- **VertexSlice** (la IdeaFormer IR3 V2), **Bambu Studio** (las Bambu Lab), **QIDI Studio** (las QIDI), **Anycubic
  Slicer Next** (las Anycubic) y **Orca-Flashforge** (las Flashforge; `sources.json`, `official`, con Creality Print y
  Elegoo Slicer): AGPL-3.0, según el `LICENSE` de cada repositorio en su commit;
- **definiciones de UltiMaker Cura y BlackBelt Cura:** LGPL-3.0 (`licenses/Cura-LGPL-3.0.txt`), compatible con la
  AGPL-3.0.
- **mallas de las camas de UltiMaker Cura** (`resources/meshes`, en el commit de `sources.json`): LGPL-3.0, la licencia
  del repositorio; no tienen aviso propio, y `licenses_thirdparty` solo nombra a Qt. Van convertidas en
  `assets.bed_model` de los modelos de Cura (abajo). Las imágenes de `resources/images` son la placa trasera de Cura,
  no una textura de la cama, y no van.

El paquete entero se distribuye bajo la AGPL-3.0 o posterior (`LICENSE`). Un programa que lo descarga y lo lee como
datos no se vuelve parte del paquete.
