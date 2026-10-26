# Formato del paquete de perfiles

Versión 2. Es el formato que lee el motor de Tisma (`tisma_engine`) para instalar impresoras, filamentos, perfiles de
impresión y resinas. Los perfiles de adentro usan el formato de perfil del motor (`docs/PROFILES.md` del motor) con
sus claves (`docs/CONFIG.md` del motor), así que el motor no necesita saber nada de los programas de donde salieron.

## Descarga

Cada versión es un release de este repositorio, con estos archivos:

| Archivo | Qué es |
|---|---|
| `index.json` | El índice: fabricantes, modelos, perfiles y los archivos comprimidos, con su tamaño y su SHA-256 |
| `compatible.json` | Qué impresoras sirve cada filamento y cada perfil de impresión |
| `<fabricante>.tar.xz` | Un archivo por fabricante: sus perfiles y sus imágenes (`vendors/<fabricante>/…`) |
| `community.tar.xz` | Los datos de la comunidad (`docs/COMMUNITY.md`) |
| `stats.json` | Cuentas de la conversión y las claves de origen que no tienen equivalente en el motor |

**La última versión** está siempre en
`https://github.com/adriangrochi-code/Tisma-profiles-/releases/latest/download/<archivo>`.

Para instalar:
1. Bajar `index.json`, y guardarlo como está.
2. Bajar `compatible.json` y los archivos de los fabricantes que se quieran (o todos).
3. Comprobar el tamaño y el SHA-256 de cada uno contra el índice. Si no coinciden, descartarlo.
4. Descomprimir cada `.tar.xz` en la carpeta del paquete. Adentro solo hay rutas relativas `vendors/<id>/…` o
   `community/…`. Una ruta absoluta, con `..` o que no empieza así no se descomprime.
5. Una versión nueva se reconoce porque `pack_version` del índice cambió.

**Tamaño de la versión del 26-10-2026:**
- `index.json`: unos 2,1 MB;
- cada fabricante: de unos KB a 2,8 MB;
- todo junto: unos 32 MB, en 218 archivos.

## `index.json`

| Clave | Qué es |
|---|---|
| `format`, `version` | `"tisma-profile-pack"` y `2`. Una versión mayor que la conocida no se carga |
| `pack_version` | La versión de este paquete (`AAAA.MM.DD-commit`) |
| `generated` | Fecha y hora de la conversión (UTC) |
| `source`, `other_sources` | De dónde salieron los perfiles: repositorio, commit y carpeta de Tisma Slicer y de UVtools |
| `license` | `AGPL-3.0-or-later` (ver «Licencias») |
| `vendors` | Los fabricantes (abajo) |
| `printers` | Todas las impresoras como `<archivo del modelo>#<variante>`, en orden: el número de una impresora es su lugar en esta lista (para `compatible.json`) |
| `compatible`, `community` | Nombre, tamaño y SHA-256 de esos archivos |
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
abajo), `variants` (`id` y `nozzle` de cada una) y `default_variant`.

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
 "common": { "settings": { } },
 "variants": [ { "id": "0.4", "nozzle": 0.4, "name": "…", "settings": { }, "defaults": { }, "original": { } } ],
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
  boquilla.
- **`not_converted`** (en una variante): el G-code de inicio o de fin que no se pudo pasar, con el motivo.

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
- **Impresión:** `nozzle`, la boquilla para la que está hecho, si todas sus impresoras usan la misma.

## `compatible.json`

```json
{ "format": "tisma-pack-compatible", "version": 1, "sets": [[0, 1, 2], [5, 9]] }
```

Cada conjunto es una lista de números de impresora (`index.json`, `printers`). Un filamento con `"compatible": 1`
sirve para las impresoras 5 y 9. Muchos perfiles comparten conjunto: hay 1663 para más de 16 000 perfiles.

## G-code de inicio y de fin

- **Tal cual:** el G-code de inicio y de fin de una impresora entra solo si funciona con las variables simples del
  motor (`[nombre]`, `{nombre}`, `{nombre[i]}`).
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
  `profile`: la impresora queda sin ese G-code y el motor usa el suyo para el dialecto. Queda en `original` y en
  `not_converted`.
- **Cuántos entran:** con la versión del 26-10-2026, el de inicio de 1334 de 2317 perfiles de impresora de origen.

## Calidad

`tools/validate.py` lamina un cubo de 20 mm con el motor con cada variante FDM y su filamento y perfil por defecto, y
después con cada filamento y cada perfil de impresión en la primera impresora compatible. Con la versión del
26-10-2026 y el motor de `dev` (7f745d8):
- **variantes:** 2259 de 2261 laminan. Las 2 que no son de pellets, con capas de 2,5 y 4 mm, más que lo que acepta el
  motor (2 mm);
- **todo:** 18 011 combinaciones, 24 fallan (0,13 %). Son 20 perfiles de impresión de una boquilla más grande que la
  de la primera impresora compatible, y las 4 de pellets.

## Licencias

Los perfiles vienen de programas con licencias libres, y cada perfil y cada fabricante dicen la suya:
- **PrusaSlicer, OrcaSlicer, Creality Print y Elegoo Slicer**, a través de Tisma Slicer: AGPL-3.0;
- **UVtools** (impresoras de resina y perfiles universales de impresión de resina): AGPL-3.0;
- **definiciones de UltiMaker Cura y BlackBelt Cura:** LGPL-3.0 (`licenses/Cura-LGPL-3.0.txt`), compatible con la
  AGPL-3.0.

El paquete entero se distribuye bajo la AGPL-3.0 o posterior (`LICENSE`). Un programa que lo descarga y lo lee como
datos no se vuelve parte del paquete.
