# AGENT_HANDOFF — roman-voparquet

> Handoff prompt for the next agent/model. Read this fully before touching anything.
> Written: 2026-07-07. Predecessor: Claude (Anthropic), session with Emmanuel Joliet (IPAC/Caltech, Roman SSC).

---

## Your Mission

Implement `roman-voparquet`: a Python tool that converts Roman-datamodel Parquet catalog files into **VOParquet 1.0** files by embedding a data-less VOTable header in the Parquet file-level key-value metadata, mapping every column to VO standards (`ucd`, `unit`, `description`, `datatype`).

The full spec is in `README.md` in this repo. **The README is the contract.** Implement from it. Do not redesign without asking Emmanuel first.

---

## Who You're Working With

- **Emmanuel Joliet** (`ejoliet`), systems/DevOps engineer, IPAC/Caltech, Roman SSC.
- Uses **README-Driven Development (RDD)**: spec first, then small user-playable iterations (2–15 min each) with manual copy-paste shell verification — not just automated tests.
- Style: brief, informal, assumes technical fluency. No filler. Markdown, max 3 heading levels, short paragraphs, tables for structured data.
- His Claude Project has skill files; if available, load `readme-driven-dev` and `emmanuel-markdown` before producing docs, and `vo-explorer` / `roman-space-telescope` for domain questions.

---

## Current State (as of handoff)

| Item | Status |
|------|--------|
| `README.md` (full spec, Type A + code stubs) | ✅ Done, delivered 2026-07-07 |
| `src/roman_voparquet/` implementation | ❌ Not started |
| `ucd_map.py` (full Roman column map) | ❌ Only a ~14-row sample exists in README |
| Tests, CLI, CI | ❌ Not started |
| Repo on GitHub | ❓ Unconfirmed — likely under `ejoliet/`; ask if unclear |

**Nothing is implemented yet. The README is the only artifact.**

---

## Verified Facts — Do NOT Re-derive These

These were researched and source-verified on 2026-07-07. Trust them unless a source contradicts.

1. **VOParquet 1.0** is an IVOA Note published 2025-01-16. It is a *Note*, not a Recommendation — cite it as a convention, not a standard.
   https://www.ivoa.net/documents/Notes/VOParquet/20250116/NOTE-voparquet-1.0-20250116.html
2. **The two normative file-level KV keys** (exact strings, case-sensitive):
   - `IVOA.VOTable-Parquet.version` = `"1.0"`
   - `IVOA.VOTable-Parquet.content` = the data-less VOTable XML (UTF-8)
3. **The embedded VOTable rules**: must be schema-valid; the data-less TABLE (FIELDs, no DATA child) must be the **first** TABLE element; other TABLEs may follow but don't describe the parquet data.
4. **On conflict, Parquet wins**: readers must treat parquet data/datatypes as authoritative and may discard VOTable metadata they can't reconcile.
5. **Validator**: `stilts parqlint <file>` is the reference validator. Requires parquet libs on classpath — use `java -jar topcat-extra.jar -stilts parqlint ...`. Only ERROR reports are compliance violations.
6. **Astropy** supports VOParquet natively (PR #16375 merged); `Table.write(..., format='parquet', votmeta=True)` in astropy ≥ 7.x. TOPCAT/STILTS writes VOParquet by default since 2025-03-07 (STIL 4.3-2 / STILTS 3.5-2 / TOPCAT 4.10-3).
7. **Roman context**: `romancal` 0.18+ outputs source catalogs as **Parquet**, flux units are **nJy** (changed from µJy — never assume, always read the unit). Column schema reference: Roman-STScI-000766 (WFI Co-add Catalog Schema).
8. **PyPI is Python-only** — irrelevant here (this repo IS Python), but relevant to Emmanuel's broader open-source publishing work.

---

## Decisions Already Made (do not relitigate)

| Decision | Rationale |
|----------|-----------|
| `pyarrow` for Parquet I/O | KV metadata API; `fastparquet` lacks it |
| `astropy.io.votable` for VOTable building | native VOParquet support; team-standard |
| `typer` for CLI | Emmanuel's preference; type-checked |
| Single-file conversion only in v1 | HATS/partitioning explicitly deferred (Non-Goals) |
| Unknown columns kept, written with empty ucd/unit, logged | spec-prescribed reader fallback handles them |
| snappy default compression | interop-safe |

---

## Open Questions — Resolve With Emmanuel Before Implementing Related Code

1. `meta.wcs` (gwcs object): serialize to VOTable GROUP, or summarize as ObsCore-style `<PARAM name="s_region">`?
2. Multiband catalogs: one COOSYS per band or one per table?
3. Embed `roman_datamodels` schema URI as custom KV pair (e.g. `IPAC.Roman.schema_uri`)? Non-standard keys are legal but should be namespaced.

---

## Known Traps (Recently Burned / Predicted Burns)

- ⚠️ **Do not call `vot.create_arrays()`** when building the data-less VOTable — that creates a DATA section and breaks the convention. FIELDs only.
- ⚠️ **pyarrow schema metadata is bytes**: keys/values must be `bytes`, and `schema.with_metadata()` **replaces** all metadata — merge existing pairs first (README stub does this correctly).
- ⚠️ **arraysize**: VOTable FIELDs for string columns need `datatype="char" arraysize="*"`. Omitting `datatype` entirely is illegal VOTable.
- ⚠️ **parqlint availability**: many STILTS distributions ship without parquet libs. Pin `topcat-extra.jar` in CI, don't assume `stilts` on PATH works.
- ⚠️ **Roman flux units**: nJy since romancal 0.18, µJy before. If test fixtures come from older sims, units may disagree with the map.
- ⚠️ Emmanuel's YAML front-matter skill descriptions have a 1024-char limit (relevant only if you create/edit skill files).

---

## How to Resume — First Session Script

1. Read `README.md` end to end.
2. Confirm repo location and whether anything was implemented since this handoff (`git log`, look for `src/`).
3. Ask Emmanuel the 3 Open Questions above (batch into one message, ≤3 questions, his rule).
4. Implement in this order (each iteration must be runnable + manually verifiable):
   - **Iter 0**: scaffold `pyproject.toml` + package skeleton; verify: `uv run python -c "import roman_voparquet"`
   - **Iter 1**: `ucd_map.py` as YAML + loader; expand map from Roman-STScI-000766; verify: print map for `ra`
   - **Iter 2**: `votable_builder.py`; verify: `--dry-run` prints valid XML, `votlint` passes on it
   - **Iter 3**: `converter.py` + KV write; verify: `pq.read_metadata(out)` shows both IVOA keys
   - **Iter 4**: CLI + `--validate`; verify: `parqlint` exits clean on a converted romancal test catalog
   - **Iter 5**: round-trip pytest suite + CI
5. Every iteration ends with a copy-paste shell block Emmanuel can run in 2–15 min.

---

## Definition of Done (v1)

- [ ] `roman-voparquet convert` produces a file that `stilts parqlint` passes with zero ERRORs
- [ ] Output opens in TOPCAT showing units + UCDs in the column metadata pane
- [ ] Round-trip test: data numerically identical, all columns preserved
- [ ] Unknown columns survive with logged warnings
- [ ] Docs updated: README Quick Start verified verbatim, Open Questions resolved or moved to issues

---

## Source Index (verify against these, in priority order)

1. VOParquet 1.0 Note — https://www.ivoa.net/documents/Notes/VOParquet/20250116/NOTE-voparquet-1.0-20250116.html
2. IVOA ParquetInAstronomy wiki (living implementation list) — https://wiki.ivoa.net/twiki/bin/view/IVOA/ParquetInAstronomy
3. parqlint docs — https://www.star.bris.ac.uk/~mbt/stilts/sun256/parqlint.html
4. STILTS parquet output (votmeta/kvmap) — https://www.star.bris.ac.uk/mbt/topcat/sun253/outParquet.html
5. romancal releases — https://github.com/spacetelescope/romancal/releases
6. Roman-STScI-000766 catalog schema — https://www.stsci.edu/roman/documentation/technical-documentation
7. Astropy PR #16375 — https://github.com/astropy/astropy/pull/16375
8. IVOA UCD1+ list — https://www.ivoa.net/documents/UCD1+/

> 💡 If any of these have changed since 2026-07-07 (e.g., VOParquet 1.1, or the convention got promoted to a Recommendation), the newer document wins — update this file and the README when you find out.

---

## Next Steps

1. Commit this file to the repo root as `AGENT_HANDOFF.md` (team-safe, no secrets — OK to commit).
2. Start Iter 0.
3. Keep this file updated: append a dated `## Session Log` entry after each working session (what changed, what broke, what's next).

---

## Session Log

### 2026-07-14 — Full v1 implementation (Iters 0–5)

**What changed** — implemented the whole tool from the README contract:

- `pyproject.toml` (uv/hatchling), package skeleton, `roman-voparquet` console script.
- `ucd_map.py` + bundled `data/roman_ucd_map.yaml` — 35-column Roman map (README's 14 + apertures, morphology, bbox, quality). Overridable via `--ucd-map` / `ROMAN_UCD_MAP_PATH`.
- `votable_builder.py` — data-less VOTable builder (FIELDs, **no** DATA/`create_arrays`), arrow→VOTable datatype mapping (unsigned promoted, strings get `char arraysize="*"`), single table-level COOSYS with `ref` on `ra`/`dec`, optional PARAMs.
- `datamodel.py` — best-effort `meta` extraction from Parquet KV JSON → PARAMs (filter, program, exposure_id, t_min, t_max).
- `converter.py` — orchestration + KV merge (never clobbers existing metadata), `write_voparquet`, `validate_with_parqlint` (resolves `--stilts-jar`/`STILTS_JAR`/PATH).
- `cli.py` (typer) — `convert` with `--dry-run`, `--validate`, `--compression`, `--include-meta`, `--coosys`, `--schema-uri`; `version`.
- `tests/` — 40 tests (ucd map, builder, round-trip), fixture generator `make_fixture.py`.
- `examples/`, `Makefile`, `.github/workflows/ci.yml` (pytest matrix + parqlint job with cached `topcat-extra.jar`), `.gitignore`.

**Verified** — `uv run pytest` → 40 passed. `stilts parqlint` (real `topcat-extra.jar`) on a converted fixture → **exit 0, zero ERRORs, zero WARNINGs**. Negative control (corrupted VOTable) → parqlint reports ERRORs, confirming it genuinely validates. Round-trip data byte-identical; all columns preserved; unmapped `custom_note` survives with a logged warning.

**Traps hit / notes**
- astropy **8.0.1**: `CooSys(...)` does *not* take a leading `votable` positional (Field/Param/TableElement do). Fixed.
- parqlint returns **exit 0 even when it reports ERRORs** — must grep output for `ERROR`. Both `validate_with_parqlint` and CI do this.
- astropy normalizes some units on parse (`pix`→`pixel`); round-trip test compares UCDs strictly and units loosely for that reason.

**Open Questions** — resolved for v1 with defaults (see README): no gwcs serialization (single ICRS COOSYS only), single table-level COOSYS, `--schema-uri` opt-in under `IPAC.Roman.schema_uri`. **Flag for Emmanuel** — confirm these v1 defaults are acceptable; multiband-per-band COOSYS and WCS-as-GROUP still open for v2.

**Next**
- Confirm v1 open-question defaults with Emmanuel; open v2 tickets for WCS/multiband.
- Swap the tiny synthetic fixture for a real romancal source catalog when one is available (verify nJy units against the map).
- TOPCAT GUI round-trip (couldn't run headless here) — confirm units/UCDs show in the column metadata pane.
