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
