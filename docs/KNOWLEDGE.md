# Base de conocimiento del asistente

Datos para el asistente y los tutoriales del motor, que funcionan sin conexión. Van en `knowledge/` y se publican en
`knowledge.tar.xz` junto con el paquete (`docs/FORMAT.md`, «Descarga»).

| Archivo | Qué trae |
|---|---|
| `materials.json` | 37 materiales: temperaturas de boquilla, cama y cabina, ventilador, si piden cama caliente, cabina o boquilla endurecida, superficies de cama, retracción con extrusor directo y Bowden, boquilla mínima y secado |
| `problems.json` | 27 problemas, cada uno con sus causas de la más común a la menos común, la pregunta para confirmar cada causa y los arreglos |
| `procedures.json` | 5 procedimientos paso a paso: nivelar la cama, destapar la boquilla, presión del extrusor, tubo de teflón y secado |
| `glossary.json` | 101 términos con su definición y los ajustes del motor relacionados |
| `tutorials.json` | 5 tutoriales guiados: primera impresión, primera capa, material nuevo, algo salió mal e Ingeniería |
| `calibrations.json` | 14 guías de calibración en el orden recomendado: para qué sirve, cuándo repetirla, qué va antes, pasos, cómo leer el resultado, qué ajuste cambia y con qué fórmula, consejos |

## Fuentes y derechos

- **Fuente:** el contenido sigue las guías de **Rafa Barajas** (`https://www.rafabarajas.com`): guía de solución de
  problemas v3.3.1, guía de materiales v3.2, glosario v1.4, tabla de parámetros base v2.0 y tabla de secado.
- **Qué se tomó:** los números de las tablas (temperaturas, retracción, secado), la lista de problemas, causas y
  arreglos, y la lista de términos.
- **Qué no se tomó:** el texto. Está escrito de nuevo con nuestras palabras; no se copian párrafos, tablas
  completas ni imágenes, y los PDF no van en este repositorio.
- **Cita:** cada archivo cita su fuente en `sources`. El asistente la muestra: «Basado en las guías de Rafa Barajas».
- **Calibraciones** (`calibrations.json`): el orden, los rangos y las fórmulas siguen la wiki de calibración de
  OrcaSlicer, la guía de ajuste de Andrew Ellis (`https://ellis3dp.com/Print-Tuning-Guide/`) y la documentación de
  Klipper (avance de presión y resonancias). Se tomaron los datos, no el texto: está escrito de nuevo y cada guía
  nombra sus fuentes.

## Acciones (`problems.json`, `tutorials.json`)

| `type` | Qué hace el asistente |
|---|---|
| `setting` | Cambia un ajuste del motor (`key`, con los nombres de `docs/CONFIG.md` del motor): `op` `add` suma `value`, `multiply` multiplica, `set` fija, `set_relative` fija `value` veces el ajuste `of` |
| `calibration` | Abre una prueba de calibración por su `id` (`first_layer`, `temperature_tower`, `max_flow`, `pressure_advance`, `flow`, `retraction`, `stringing_temperature`, `cooling`, `overhang_angle`, `supports`, `cornering`, `input_shaping`, `vfa`, `dimensional`), con su guía de `calibrations.json` |
| `procedure` | Abre un procedimiento de `procedures.json` |
| `problem` | Lleva a otro problema |
| `hardware`, `model` | Consejo sobre la impresora o el modelo, en `text`; no cambia ajustes |

- `why` explica la acción.
- `last_resort` en una causa indica que se revisa al final, después de las demás.

## Campos de cada archivo

**Arriba de todo:** cada archivo es un objeto con:

| Campo | Tipo | Qué es |
|---|---|---|
| `format` | texto | `tisma-knowledge-materials`, `-problems`, `-procedures`, `-glossary`, `-tutorials` o `-calibrations` |
| `version` | entero | Versión del formato del archivo (hoy 1) |
| `language` | texto | Idioma de todos los textos del archivo (hoy `es`); va por archivo, no por entrada |
| `sources` | lista | Fuentes del archivo: `id`, `title`, `author`, `url` (textos) |
| `notes` | lista de textos | Notas para quien lee el archivo |
| la lista | lista | `materials`, `problems`, `procedures`, `terms`, `tutorials` o `calibrations` |

`materials.json` trae además `fields`: un objeto de textos que explica los campos (no hace falta leerlo).

**Convenciones:** un campo opcional puede faltar o valer `null`; las dos cosas quieren decir «la fuente no lo da».
Un rango es una lista de dos números `[mín, máx]`; si el valor es fijo, los dos son iguales (`[100, 100]`).

### `materials.json` (`materials`)

| Campo | Tipo | Opcional | Qué es |
|---|---|---|---|
| `name` | texto | no | Nombre del material, único |
| `family` | texto | no | Grupo (`PLA`, `PETG`, `ABS`…). En los especiales es la primera palabra del nombre (el aditivo, como `Con` o `Brilla`), no un material base |
| `category` | texto | no | `básicos`, `variantes de PLA`, `de ingeniería`, `avanzados` o `especiales` |
| `nozzle_material` | texto | no | `latón` o `acero endurecido o inoxidable` |
| `abrasive` | sí/no | no | Pide boquilla de acero |
| `nozzle_temp`, `bed_temp` | rango | sí | °C |
| `fan` | rango | sí | % del ventilador de capa |
| `bed_required`, `enclosure` | texto | sí | `necesaria`, `recomendada`, `opcional`, `no necesaria` o `según el material base` |
| `surfaces` | lista de textos | sí | Superficies o adhesivos de cama |
| `base_table` | objeto | sí | Tabla de parámetros base: `nozzle_temp` y `bed_temp` (rangos, °C), `chamber_temp` (número, °C, opcional), `fan` (número, %), `enclosure` (`necesaria` o `no necesaria`), `retraction` con `direct` y `bowden` (mm; `bowden` puede ser `null`), `nozzle_diameter_min` (mm) |
| `drying` | objeto | sí | `before_printing` (`si` o `recomendado`), `temp` (rango, °C), `hours_before_printing`, `hours_mild` y `hours_severe` (horas, enteros) |
| `sources` | lista | no | Fuentes de esa entrada, como las del archivo, con `pages` (lista de enteros) opcional |

### `problems.json` (`problems`)

| Campo | Tipo | Opcional | Qué es |
|---|---|---|---|
| `id`, `name`, `symptoms` | texto | no | Identificador único, nombre y cómo se ve |
| `causes` | lista | no | De la más común a la menos común |
| `causes[].id`, `name`, `explain`, `check` | texto | no | La causa, por qué pasa y la pregunta para confirmarla |
| `causes[].last_resort` | sí/no | sí | Se revisa al final |
| `causes[].actions` | lista | no | Acciones, ver «Acciones» arriba |

Campos de cada acción según `type`:
- `setting`: `key`, `op` y `value` siempre; `unit` (`°C`, `mm`, `%` o `s`), `of` (solo con `set_relative`) y `why`
  opcionales. `value` es número, texto o sí/no según el ajuste;
- `calibration`, `procedure`, `problem`: `id`;
- `hardware`, `model`: `text`.

### `procedures.json` (`procedures`)

| Campo | Tipo | Opcional | Qué es |
|---|---|---|---|
| `id`, `name`, `for` | texto | no | Identificador, nombre y para qué casos sirve |
| `steps` | lista | no | Cada paso con `title` y `text` |
| `warnings`, `prevention`, `notes` | lista de textos | sí | Cuidados, cómo evitar que vuelva a pasar y notas |
| `applies_to` | texto | sí | A qué máquinas aplica |

### `glossary.json` (`terms`)

| Campo | Tipo | Opcional | Qué es |
|---|---|---|---|
| `term`, `definition` | texto | no | Término y definición |
| `settings` | lista de textos | sí | Claves de ajustes del motor relacionadas |

### `tutorials.json` (`tutorials`)

| Campo | Tipo | Opcional | Qué es |
|---|---|---|---|
| `id`, `name` | texto | no | Identificador y nombre |
| `when` | texto | no | Cuándo se ofrece: `first_start`, `on_request`, `new_filament` o `first_open:<panel>` (hoy `first_open:engineering`) |
| `minutes` | entero | no | Duración aproximada |
| `steps` | lista | no | Pasos |
| `steps[].anchor` | texto | no | La parte de la interfaz que se señala, por un nombre que define la ficha del asistente del motor. Hoy: `printer_selector`, `filament_selector`, `plate`, `plate_tools`, `quick_settings`, `slice_button`, `preview`, `send_button`, `calibrations`, `help_problems`, `help_procedures`, `engineering_panel`, `engineering_faces`, `engineering_loads`, `engineering_run`, `engineering_apply` |
| `steps[].title`, `steps[].text` | texto | no | Título y texto del paso |
| `steps[].wait_for` | texto | sí | Evento que hace avanzar solo: `printer_selected`, `filament_selected`, `model_added`, `sliced`, `fixed_face_added`, `load_added`, `analysis_done`. Sin él, la persona avanza a mano |
| `steps[].open` | objeto | sí | Algo para abrir desde el paso: `type` (`procedure` o `calibration`) e `id` |

## Revisión

`tools/check_knowledge.py knowledge` comprueba:
- el formato de cada archivo y sus fuentes;
- que cada procedimiento, problema y calibración nombrado exista;
- que las claves de ajustes tengan forma de clave del motor.

La CI no publica si falla.

## Guías de calibración (`calibrations.json`)

| Campo | Qué es |
|---|---|
| `id`, `name` | La prueba y su nombre |
| `group` | `filament` (se repite con cada filamento) o `printer` (se repite al cambiar la máquina) |
| `order` | Orden recomendado; `before` son las pruebas que tienen que estar hechas antes |
| `why`, `repeat` | Para qué sirve y cuándo repetirla |
| `steps` | Pasos |
| `read` | Lo que se ve (`look`) y qué significa (`means`) |
| `result` | El ajuste del motor que fija (`key`) o `where` `printer_firmware` si va en la impresora, y `text` con la fórmula |
| `tips` | Consejos y valores de referencia |
| `open` | Opcional: un procedimiento relacionado |
