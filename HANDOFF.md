# Handoff — profile pack session

State of the work on branch `profiles/next` (owner's request of 2026-11-05). Kept short; update it when something
changes.

## Done

1. **Each printer's own G-code, verbatim, with its macros** (`gcode` block in model files and filaments;
   `docs/FORMAT.md`, «G-code de la máquina»).
   - Root cause of the Bambu Lab bug: Tisma Slicer's converter did not follow OrcaSlicer's `include` (per-model
     G-code templates), and it also left many other OrcaSlicer/Creality Print printers with another model's G-code.
   - The converter now reads the source programs at the commit each Tisma Slicer bundle names
     (`sources.json` → `converted_from`, fetched by `tools/fetch_sources.py`): `tools/upstream.py` resolves
     `inherits` + `include` (OrcaSlicer family) and Cura definitions + extruders.
   - PrusaSlicer-format bundles are carried as they are (`origin: bundle`).
   - Format version stays 2: the block is additive; old readers ignore it.
2. **Compatible sets:** no set is empty. Condition evaluation fixed (`num_extruders`, numbers written as strings,
   escaped new lines in notes, whole-value regex match). 392 → 50 entries fit nothing, and those fit no printer in
   their source program either: left out, listed in `stats.json` → `left_out`.
3. **Print nozzle:** from all printers, else the condition's `nozzle_diameter[0]==X`, else the name. Printers whose
   bundle lost `nozzle_diameter` take it from the source program (3 UltiMaker 2 extended+ variants).
4. **CI check:** `tools/check_pack.py` (in `release.yml` before packaging, and the new `check.yml` on other branches).
5. Release candidate: built locally, see the numbers in the last commit. The owner publishes.

## Open

- Variables in `orcaslicer`/`cura` G-code use the source program's names; filament and print profiles keep
  PrusaSlicer names. `gcode.values` gives the machine values with the source names. The engine's macro spec
  (spec session) must say how it maps the rest.
- Cura start G-codes set `M82` (absolute E): `gcode.relative_extrusion` is `false` there while
  `profile.settings.machine.relative_extrusion` (from Tisma Slicer's bundle, which forced `M83`) is `true`.
- 42 printers still take their G-code from Tisma Slicer's converted bundle (BlackBelt, VertexSlice, CR-30 PrintMill):
  their programs are not read, or the preset has another name there.
- 4 groups of models share the vendor-wide base start G-code of OrcaSlicer (DeltaMaker, LONGER LK10, E3NG/VIRTU,
  WonderMaker): that is how the source has them; reported as notes, not failures.

## Contacts

- Spec/QA: session_01QadJfL7KViJEaJL92p8Swb (behaviour and format notes, how to try the pack).
- Engine: session_01JDAJxTVh345Lfm4794rJF8 — clean room: format and behaviour notes only, never code from here.
