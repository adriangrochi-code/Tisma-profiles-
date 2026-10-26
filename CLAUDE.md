# Tisma profiles — notes for Claude

Free (AGPL-3.0-or-later) profile pack for the Tisma engine: converted printer, filament, print and resin profiles,
plus community data with sources. Format in `docs/FORMAT.md`, community data in `docs/COMMUNITY.md`.

## Working rules (from the project owner)

- Answer the owner in Spanish. Code, comments, commit messages and PR titles are in English; docs in Spanish.
- Conventional Commits. No model identifiers in code, commits or PR text, except the session attribution trailer.
- Every value has a source. Never invent data; leave it empty when no source gives it.
- Community data: numbers and own descriptions only, never copied text; people only by their public name.
- The engine repository (`tisma_engine`) is clean-room: never copy anything from this repository into it. The
  engine only downloads and reads the released pack.
- Before a change to the converter, run it and `tools/validate.py` with a build of the engine, and report the
  numbers in the commit or PR.
- Keep `docs/FORMAT.md` in step with the converter: a field added or changed there in the same commit.
