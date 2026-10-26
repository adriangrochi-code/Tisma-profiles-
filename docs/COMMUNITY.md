# Datos de la comunidad

Además de los perfiles convertidos, el paquete junta lo que se sabe de cada impresora, filamento y resina por fuera de
los perfiles:
- páginas y hojas técnicas de los fabricantes;
- configuraciones de firmware que publican;
- mediciones de reseñas, videos y pruebas;
- valores que la gente comparte en foros.

Cada valor lleva su fuente, y se marca de qué tipo es, para que el programa nunca mezcle un dato oficial con una
opinión.

## Dónde va cada cosa

```
community/printers/<Fabricante>/<Modelo>.json
community/filaments/<Fabricante>/<Nombre>.json
community/resins/<Fabricante>/<Nombre>.json
```

## Un archivo

```json
{
 "vendor": "Ejemplo",
 "model": "Impresora X",
 "pack_model": {"bundle": "Ejemplo", "id": "X"},
 "data": [
  {
   "key": "machine.acceleration",
   "value": 10000,
   "unit": "mm/s²",
   "kind": "official",
   "source": {
    "type": "manufacturer",
    "url": "https://ejemplo.com/impresora-x/especificaciones",
    "title": "Especificaciones de la Impresora X",
    "accessed": "2026-10-26"
   }
  },
  {
   "key": "measured.max_flow",
   "value": 24,
   "unit": "mm³/s",
   "kind": "measured",
   "conditions": "PLA a 220 °C, boquilla de 0,4 mm de fábrica",
   "source": {
    "type": "video",
    "url": "https://www.youtube.com/watch?v=...",
    "title": "Título del video",
    "author": "Nombre del canal",
    "published": "2026-05-01",
    "at": "12:34",
    "accessed": "2026-10-26"
   }
  }
 ]
}
```

- **Filamentos y resinas:** llevan `name` en lugar de `model`.
- **`pack_model`:** opcional. Une el archivo al modelo del paquete (`id` es el del índice).

**Tipos de dato (`kind`):**

| `kind` | Qué es | Cómo lo usa el programa |
|---|---|---|
| `official` | Lo publica el fabricante: página, manual, hoja técnica, firmware | Puede llenar un ajuste vacío del perfil |
| `measured` | Una medición con método: reseña, video, prueba propia | Se muestra como dato medido, con la fuente; nunca reemplaza solo un ajuste |
| `community` | Un valor que alguien recomienda, sin medición | Se muestra como sugerencia, con la fuente |

## Claves

- **Ajustes del motor:** con el mismo nombre que en su `docs/CONFIG.md` (`machine.acceleration`, `machine.max_flow`,
  `extrusion.pressure_advance`…).
- **Datos que todavía no son ajustes:** con estos nombres. Si hace falta uno nuevo, se agrega acá en el mismo cambio.

| Clave | Unidad | Qué es |
|---|---|---|
| `measured.max_flow` | mm³/s | Flujo máximo medido (con la temperatura y la boquilla en `conditions`) |
| `measured.acceleration` | mm/s² | Aceleración que la impresora sostiene sin perder pasos ni calidad |
| `measured.speed` | mm/s | Velocidad de impresión real, sin las rampas |
| `input_shaper.frequency_x`, `input_shaper.frequency_y` | Hz | Frecuencias de resonancia medidas |
| `input_shaper.type` | — | El tipo de input shaper que se eligió |
| `head.clearance_radius` | mm | Distancia de la boquilla al borde del cabezal |
| `head.gantry_height` | mm | Altura libre bajo el pórtico |
| `head.nozzle_to_fan_height` | mm | Altura de la boquilla sobre la parte más baja del ventilador |
| `bed.mesh_points` | — | Puntos de la malla de nivelación |
| `firmware.version` | — | Versión de firmware a la que vale el dato |
| `filament.tensile_strength_xy`, `filament.tensile_strength_z` | MPa | Resistencia a la tracción en el plano y entre capas |
| `filament.tensile_modulus_xy`, `filament.tensile_modulus_z` | MPa | Módulo de elasticidad |
| `filament.elongation_xy`, `filament.elongation_z` | % | Alargamiento a la rotura |
| `filament.impact_strength` | kJ/m² | Resistencia al impacto (método en `conditions`) |
| `filament.hdt` | °C | Temperatura de deflexión bajo carga (carga en `conditions`) |
| `filament.glass_transition` | °C | Transición vítrea |
| `filament.shrinkage_xy`, `filament.shrinkage_z` | % | Contracción |
| `filament.drying_temperature`, `filament.drying_hours` | °C, h | Secado |
| `filament.price_per_kg` | moneda/kg | Precio, con la moneda y la fecha en `conditions` |
| `resin.exposure`, `resin.bottom_exposure` | s | Exposición que alguien probó en esa impresora (en `conditions`) |
| `resin.viscosity` | mPa·s | Viscosidad |

## Reglas

1. **Siempre la fuente:** dirección web y fecha de consulta; en un video, también el minuto. Sin fuente no entra.
2. **Solo el dato, no el texto:** se anota el número y una descripción propia. No se copian párrafos, tablas ni
   transcripciones.
3. **Personas:** de una persona solo se anota el nombre público con el que firma su trabajo (canal, autor). Nada de
   datos personales.
4. **Nada de otros paquetes de perfiles** en esta carpeta: los perfiles entran por `tools/convert.py`, con su licencia.
5. **Revisión:** `tools/check_community.py community` revisa cada archivo; la CI no publica si falla.
