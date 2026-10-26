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

## Fuentes y derechos

- **Fuente:** el contenido sigue las guías de **Rafa Barajas** (`https://www.rafabarajas.com`): guía de solución de
  problemas v3.3.1, guía de materiales v3.2, glosario v1.4, tabla de parámetros base v2.0 y tabla de secado.
- **Qué se tomó:** los números de las tablas (temperaturas, retracción, secado), la lista de problemas, causas y
  arreglos, y la lista de términos.
- **Qué no se tomó:** el texto. Está escrito de nuevo con nuestras palabras; no se copian párrafos, tablas
  completas ni imágenes, y los PDF no van en este repositorio.
- **Cita:** cada archivo cita su fuente en `sources`. El asistente la muestra: «Basado en las guías de Rafa Barajas».

## Acciones (`problems.json`, `tutorials.json`)

| `type` | Qué hace el asistente |
|---|---|
| `setting` | Cambia un ajuste del motor (`key`, con los nombres de `docs/CONFIG.md` del motor): `op` `add` suma `value`, `multiply` multiplica, `set` fija, `set_relative` fija `value` veces el ajuste `of` |
| `calibration` | Abre una prueba de calibración por su `id` (`temperature_tower`, `flow`, `retraction`, `max_flow`, `cooling`, `overhang_angle`, `supports`, `dimensional`, `stringing_temperature`, `input_shaping`, `first_layer`) |
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
