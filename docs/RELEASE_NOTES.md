# Notas del paquete de perfiles

Convertido desde Tisma Slicer a6b4f62 y UVtools de8580d. El G-code, las listas de impresoras y los valores por defecto
de los programas salen de OrcaSlicer 1d577ea, Creality Print 59ae8cb, Elegoo Slicer 2d507e3 y Cura 5bea2f8.
AGPL-3.0-or-later.

## Qué cambia desde pack-2026.11.10-dcb4250

- **Como en el programa de origen, también donde el paquete de Tisma Slicer difiere:** 160 valores de filamentos de la
  familia OrcaSlicer (por ejemplo el ABS de Anycubic para la Kobra S1 Max 0.8: 220 °C, no 250) y los anchos de línea
  que OrcaSlicer da en % de la boquilla: 113 perfiles de impresión para varias boquillas van ahora uno por boquilla,
  con sus anchos (la Ender-3 V3 KE con 0,4 mm ya no imprime líneas de 0,21 mm). Cada cambio está en `stats.json`
  (`source_over_bundle`).
- **Unos 80 ajustes más llegan al motor** en vez de quedar en los suyos por defecto: soporte bajo los puentes (1040
  perfiles de impresión), estilo de soporte y árboles, patrones de superficie, anchos de cada tipo de línea, paredes
  Arachne o clásicas, velocidades y ventilador en voladizos, piel rugosa, torre de purga, etiquetas de objetos, arcos,
  miniaturas, G-code binario, temperaturas automáticas, retracción y contracción propias de cada filamento.
- **Firmware de cada impresora:** 647 variantes con Marlin 1 iban como Marlin 2, 114 con RepRapFirmware como RepRap
  genérico y 13 Repetier como Marlin; la desviación de unión (`M205 J`) solo con Marlin 2, como en el origen.
- **Impresoras de varios extrusores** (323 variantes): cuántos tiene, sus boquillas y desplazamientos, el extrusor
  del soporte, de su interfaz y de la torre de purga, la prevención de goteo y el volumen de purga.
- **Impresoras de cinta** (Creality CR-30, BlackBelt, IdeaFormer: 42 variantes) como de cinta, y la Ginger G1 como
  impresora de pellets.
- **Sin tope de velocidad que el origen no tiene:** unos 200 perfiles de impresión imprimían más lento la pared
  exterior, los puentes o el relleno de huecos.
- **Resina:** la altura de la primera capa como primera capa (antes pisaba la altura de todas).
- **Perfiles por defecto que sirven:** 385 impresoras traían por defecto un filamento y 161 un perfil de impresión que
  no eran compatibles con ellas. Ahora el de origen si sirve; si no, el primero compatible, del mismo material.
  Además, 197 impresoras (172 de Creality, entre ellas la Ender-3) no recibían el perfil de impresión que nombra su
  fuente, porque el paquete lo escribía entre comillas; ahora lo reciben.
- **G-code de filamento original** en la familia OrcaSlicer (3741 filamentos de OrcaSlicer y 316 de Creality Print),
  del programa de origen y en su dialecto, como el de las máquinas. Los valores de la máquina que el perfil no dice
  salen del valor por defecto del programa (`program_defaults`).
- **Impresoras sin perfiles de impresión:** 75 variantes, entre ellas la Bambu Lab P1S, la X1 y la X1 Carbon con 0,4 mm,
  no tenían ningún perfil de impresión: el paquete de Tisma Slicer guarda uno solo de los perfiles iguales que
  OrcaSlicer repite para cada impresora, y la lista de impresoras ahora suma las de todos. Ahora todas tienen.
- **Boquillas que faltaban:** 6 variantes nuevas (por ejemplo la AnkerMake M5 con 0,2 y 0,25 mm) de impresoras que
  venían de dos fuentes; sus perfiles ya no quedan en la variante de 0,4.
- **Datos que el paquete de Tisma Slicer perdió:** la boquilla de la Anycubic i3 Mega y la Mega S, la altura de 9
  impresoras (por ejemplo la Meltingplot MBL 480), y los límites de velocidad, aceleración y jerk por eje de 857
  variantes de la familia OrcaSlicer (más la retracción de la Elegoo Neptune y la UltiMaker 2 extended+), y los
  valores de 37 impresiones y 11 filamentos que el paquete dejó casi vacíos (por ejemplo la altura de la primera
  capa de las impresiones de Elegoo y Artillery), del programa de origen.
- **Datos de comunidad** enlazados a su modelo del paquete.
- **Camas de UltiMaker Cura:** 151 modelos de Cura traen la malla de su cama, convertida de Cura (LGPL-3.0); el paquete
  pesa unos 6 MB más.
- **Imágenes y materiales de los modelos de Creality Print y Elegoo Slicer** (12 modelos, por ejemplo la Creality
  Z2): miniatura, modelo de cama y materiales por defecto, del programa de origen.
- **Tablas de traducción:** la de OrcaSlicer da ahora los valores que tienen otro nombre en una clave con el mismo
  nombre (la costura `back` es `rear`; la piel rugosa `disabled_fuzzy` es `none`).
- **Tipo de material sin comillas:** 4682 filamentos de la familia OrcaSlicer decían `"PLA"` (con las comillas del
  archivo) en vez de `PLA`.
- **Más revisiones en la CI** (`tools/check_pack.py`): perfiles por defecto, boquilla de los perfiles de impresión,
  variantes sin fabricante, G-code de filamento de la familia OrcaSlicer, datos de comunidad, textos con comillas,
  valores que el programa de origen da y el paquete perdió, bloque de material igual a los ajustes del filamento.

El formato sigue en la versión 2: un lector anterior ignora los campos nuevos.

## Cuentas

902 modelos FDM con 2267 variantes y 156 de resina; 11 638 filamentos, 4625 perfiles de impresión (4420 del origen,
113 de ellos uno por boquilla), 484 resinas y 35 perfiles de impresión de resina. Unos 40 MB.

## Calidad

Con el motor de `dev` (05023bf):
- las 2267 variantes FDM laminan con su G-code propio (`validate.py --macros`) salvo 2, la Flashforge Adventurer 3,
  cuya torre de purga pide E relativa con E absoluta (Tisma Slicer tampoco la lamina); en las 2265 que leen su G-code
  propio cada línea fija del G-code de inicio y de fin sale igual y en el mismo orden (GM13);
- de 18 530 combinaciones de impresora, filamento e impresión fallan 16 (0,09 %), que los programas de origen
  tampoco laminan: 11 con capas más gruesas que la boquilla y 5 con una pared exterior no más ancha que la capa;
- el lector de paquetes del motor (`validate.py --reader`, como los carga la aplicación) toma cada valor de los
  19 205 perfiles; solo rechaza 35 pares de filamento e impresión que las condiciones del origen excluyen.
