# Tisma profiles

Perfiles libres de impresoras 3D, filamentos, perfiles de impresión y resinas para el motor de Tisma, más los datos
que junta la comunidad sobre cada máquina y cada material. Licencia AGPL-3.0 o posterior: uso libre, también
comercial, con las condiciones de la AGPL.

*Free (AGPL-3.0) 3D printer, filament, print and resin profiles for the Tisma engine, plus community data with
sources.*

## Qué hay

Versión del 26-10-2026, convertida desde los perfiles de Tisma Slicer y las impresoras de resina de UVtools:

| Qué | Cantidad |
|---|---|
| Paquetes de origen (fabricantes) | 236 |
| Modelos de impresora FDM | 902, con 2261 boquillas o variantes |
| Modelos de impresora de resina | 156 |
| Filamentos | 11 651 |
| Perfiles de impresión | 4483 |
| Resinas | 484 |
| Perfiles de impresión de resina | 36 |

Cada modelo está una sola vez: lo que comparten sus boquillas se guarda una vez, y cada boquilla solo con lo que
cambia. Los 24 modelos que venían de dos fuentes se guardan una sola vez.

Cada perfil trae:
- los ajustes que entiende el motor, con sus nombres;
- todos los valores de origen, para no perder nada;
- su licencia;
- las impresoras con las que sirve;
- las imágenes de la cama y de la impresora, cuando las hay.

## Cómo lo usa el motor

La primera vez que se abre, el motor descarga el índice de la última versión de este repositorio y los fabricantes
que se elijan. Después avisa cuando hay una versión nueva. El formato y la descarga están en `docs/FORMAT.md`.

El motor tiene su propia licencia (no comercial) y no incluye estos perfiles: los descarga y los lee como datos.

## Cómo se hace

- `tools/convert.py`: convierte los paquetes de perfiles de Tisma Slicer (`resources/profiles`, del commit de
  `sources.json`) al formato del paquete.
- `tools/package.py`: un archivo comprimido por fabricante, más el índice con el tamaño y el SHA-256 de cada uno.
- `tools/validate.py`: lamina un cubo con el motor con cada impresora, cada filamento y cada perfil de impresión.
- `tools/check_community.py`: revisa los datos de la comunidad.
- La CI (`.github/workflows/release.yml`) convierte, empaqueta y publica un release con cada cambio en `main`.

## Datos de la comunidad

Lo que se sabe de cada impresora, filamento y resina fuera de los perfiles, siempre con su fuente:
- datos de los fabricantes;
- mediciones de reseñas, videos y pruebas;
- recomendaciones.

Cómo agregarlos: `docs/COMMUNITY.md`.

## Licencias

- **Perfiles de PrusaSlicer, OrcaSlicer, Creality Print y Elegoo Slicer**, a través de Tisma Slicer: AGPL-3.0.
- **Definiciones de UltiMaker Cura y BlackBelt Cura:** LGPL-3.0 (`licenses/Cura-LGPL-3.0.txt`).
- **Impresoras de resina y perfiles universales de UVtools:** AGPL-3.0.
- **El paquete y las herramientas:** AGPL-3.0 o posterior (`LICENSE`).
- **Cada perfil** dice su licencia y su origen.
