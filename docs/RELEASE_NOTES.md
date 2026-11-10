# Notas del paquete de perfiles

Convertido desde Tisma Slicer a6b4f62 y UVtools de8580d. El G-code, las listas de impresoras y los valores por defecto
de los programas salen de OrcaSlicer 1d577ea, Creality Print 59ae8cb, Elegoo Slicer 2d507e3 y Cura 5bea2f8.
AGPL-3.0-or-later.

## Qué cambia desde pack-2026.11.10-dcb4250

- **Perfiles por defecto que sirven:** 385 impresoras traían por defecto un filamento y 161 un perfil de impresión que
  no eran compatibles con ellas. Ahora el de origen si sirve; si no, el primero compatible, del mismo material.
- **G-code de filamento original** en la familia OrcaSlicer (3741 filamentos de OrcaSlicer y 316 de Creality Print),
  del programa de origen y en su dialecto, como el de las máquinas. Los valores de la máquina que el perfil no dice
  salen del valor por defecto del programa (`program_defaults`).
- **Boquillas que faltaban:** 6 variantes nuevas (por ejemplo la AnkerMake M5 con 0,2 y 0,25 mm) de impresoras que
  venían de dos fuentes; sus perfiles ya no quedan en la variante de 0,4.
- **Datos que el paquete de Tisma Slicer perdió:** la boquilla de la Anycubic i3 Mega y la Mega S, y la altura de 9
  impresoras (por ejemplo la Meltingplot MBL 480).
- **Datos de comunidad** enlazados a su modelo del paquete.
- **Más revisiones en la CI** (`tools/check_pack.py`): perfiles por defecto, boquilla de los perfiles de impresión,
  variantes sin fabricante, G-code de filamento de la familia OrcaSlicer, datos de comunidad.

El formato sigue en la versión 2: un lector anterior ignora los campos nuevos.

## Cuentas

902 modelos FDM con 2267 variantes y 156 de resina; 11 638 filamentos, 4419 perfiles de impresión, 484 resinas y 35
perfiles de impresión de resina. Unos 33 MB.

## Calidad

Con el motor de `dev` (3667e62) y el G-code propio de cada máquina (`validate.py --macros`), las 2267 variantes FDM
laminan, y en todas cada línea fija del G-code de inicio y de fin sale igual y en el mismo orden (GM13). De 18 324
combinaciones de impresora, filamento e impresión fallan 14 (0,08 %), por datos del programa de origen: 11 perfiles con
capas más gruesas que la boquilla y 3 de Geeetech con un ancho de primera capa de 0,133 mm en boquilla de 0,6 mm.
