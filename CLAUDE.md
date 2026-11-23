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

## Code style: Marlin style (owner, 2026-11-23)

From now on, for new code and for everything touched (no need to rewrite existing code at once), code is written and
documented "Marlin style", in as much detail as it takes for anyone to understand it by reading it. Comments stay in
English (owner's decision for this repository); docs stay in Spanish.

1. A header in each file: what it is, what it is for, how it fits with the rest, units and conventions, and a usage
   example.
2. Sections with large separators as in Marlin (lines of `=====` with the section name) and `--- name ---`
   subsections.
3. Every configuration parameter or table explained where it is defined, as in Marlin's Configuration.h: what it
   does, unit, reasonable range, default value, and what happens if it is overdone.
4. Every function and class documented: what it does, parameters with units, what it returns, errors, and why it is
   done this way when that is not obvious.
5. Inline comments for what is not evident (formulas explained, performance shortcuts, compatibility, safety); no
   comments on the obvious.
6. Descriptive names, no cryptic abbreviations.
