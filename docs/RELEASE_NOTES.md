# Notas del paquete de perfiles

Convertido desde Tisma Slicer a6b4f62 y UVtools de8580d. El G-code y las listas de impresoras salen de OrcaSlicer
1d577ea, Creality Print 59ae8cb, Elegoo Slicer 2d507e3 y Cura 5bea2f8. AGPL-3.0-or-later.

## Qué cambia

- **El G-code propio de cada máquina, tal cual, con sus macros** (bloque `gcode` en cada modelo; `docs/FORMAT.md`,
  «G-code de la máquina»): inicio, fin, cambio de capa, de herramienta, pausa, timelapse y, en Cura, los de cada
  extrusor. Las Bambu Lab ya no comparten un G-code genérico: hay 25 distintos para sus 56 variantes, con nivelación,
  Z offset, calibración de flujo y limpieza de la boquilla.
- **Variables del G-code** por dialecto: `docs/GCODE_VARIABLES.md`.
- **Compatibilidad:** ningún conjunto vacío (antes 392 perfiles apuntaban a uno). Las condiciones se evalúan como en
  el programa de origen, y en la familia OrcaSlicer la lista de impresoras sale del origen: 2012 perfiles cambian
  de impresoras, casi todos a menos (antes servían para todas las de la marca). 83 perfiles que no sirven para
  ninguna impresora del paquete quedan fuera, listados en `stats.json`.
- **Boquilla** en los perfiles de impresión cuando sus impresoras, su condición o su nombre la dicen.
- **Revisión en la CI** (`tools/check_pack.py`) y `validate.py --macros`, que lamina con el G-code propio de cada máquina.

El formato sigue en la versión 2: un lector anterior ignora el bloque nuevo.

## Cuentas

902 modelos FDM con 2261 variantes y 156 de resina; 11 636 filamentos, 4416 perfiles de impresión, 484 resinas y 35
perfiles de impresión de resina. 240 archivos, 32,7 MB.

## Calidad

Con el motor de `dev` (3cb778f): las 2261 variantes laminan. De 18 313 combinaciones fallan 11 (0,06 %): perfiles que
el origen da con capas más gruesas que la boquilla.

## Con el motor actual

Con el motor de `dev` (b3f296b) y el G-code propio de cada máquina (`validate.py --macros`), las 2261 variantes FDM
laminan con su G-code, y en todas cada línea fija del G-code de inicio y de fin sale igual y en el mismo orden (GM13).

## También

- Los filamentos de la familia OrcaSlicer traen los valores del programa de origen que usa el G-code de las máquinas
  (`source_values`).
- Tablas de traducción de claves por programa (`translation.tar.xz`), para abrir proyectos de otros programas; los
  perfiles ganan 86 ajustes del motor que antes no tenían (aceleraciones por tipo, límites de la máquina, planchado,
  retracción, MMU…), con el mismo sentido que en el programa de origen.
