# roman-voparquet

> Convert a Roman-datamodel Parquet file into a **VOParquet 1.0** file by attaching a data-less VOTable header — keeping every column, mapping `ucd`, `unit`, `description`, and `datatype` to VO standard.

[![VOParquet 1.0](https://img.shields.io/badge/VOParquet-1.0-blue)](https://www.ivoa.net/documents/Notes/VOParquet/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org)

---

## Overview

Roman SOC source catalogs are now distributed as **Parquet** (since `romancal` 0.18+), but native Parquet only carries column *names* and *primitive types* — no `unit`, no `UCD`, no `description`. That makes them invisible to VO clients (TOPCAT, pyvo, Aladin, Firefly, jdaviz).

This repo shows how to convert any Roman Parquet catalog into a **VOParquet 1.0** file — a normal Parquet file with a **data-less VOTable** stored in its file-level key-value metadata. VO-aware tools pick up the rich metadata; non-VO tools still read it as plain Parquet.

> 💡 **Why VOParquet?** It's the IVOA-blessed way (Note v1.0, Jan 2025) to get UCDs, units, COOSYS, and DataLink into Parquet without breaking the Parquet spec or splitting metadata into a sidecar file.

---

## Architecture

```
┌────────────────────────┐
│ Roman Parquet (in)     │
│ - ra, dec, flux_*      │
│ - meta from datamodel  │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────────────────┐
│ 1. Read with pyarrow → astropy     │
│ 2. Apply ucd/unit map              │
│    (roman_voparquet/ucd_map.py)    │
│ 3. Build data-less VOTable XML     │
│    (astropy.io.votable, no DATA)   │
│ 4. Write parquet + KV metadata:    │
│    IVOA.VOTable-Parquet.version    │
│    IVOA.VOTable-Parquet.content    │
└──────────┬─────────────────────────┘
           │
           ▼
┌────────────────────────┐
│ VOParquet 1.0 (out)    │
│ + parqlint validates   │
└────────────────────────┘
```

---

## Recommended Stack

| Layer | Chosen | Why | Rejected |
|-------|--------|-----|----------|
| Parquet I/O | `pyarrow` 17+ | Reference impl; supports schema-level KV metadata; backs `astropy` parquet | `fastparquet` (no KV metadata API) |
| VOTable build | `astropy.io.votable` | VOParquet support merged via [PR #16375](https://github.com/astropy/astropy/pull/16375); reads/writes `votmeta` natively | `pyvo` (consumer only), GAVO `votable` (heavier) |
| Roman datamodel | `roman_datamodels` | Authoritative schemas for Roman ASDF/Parquet products | hand-rolled column maps |
| Validator | `STILTS` `parqlint` | The only reference VOParquet validator today | none |
| CLI | `typer` | Type-checked, auto `--help`, well adopted at IPAC | `click`, `argparse` |

> ✅ Astropy ≥ 7.0 supports `Table.write(..., format='parquet', votmeta=True)` directly. If your astropy is older, this repo's converter does the equivalent work explicitly.

---

## Repository Layout

```
roman-voparquet/
├── README.md                    # this file
├── pyproject.toml               # uv / pip install
├── src/roman_voparquet/
│   ├── __init__.py
│   ├── ucd_map.py               # Roman column → {ucd, unit, description}
│   ├── datamodel.py             # Roman meta extraction (datamodel_meta_*)
│   ├── votable_builder.py       # Build dataless VOTable from astropy.Table
│   ├── converter.py             # Orchestrates: in.parquet → out.parquet (VO)
│   └── cli.py                   # `roman-voparquet convert ...`
├── tests/
│   ├── data/
│   │   └── tiny_source_catalog.parquet
│   ├── test_ucd_map.py
│   ├── test_votable_builder.py
│   └── test_round_trip.py
└── examples/
    ├── 01_convert_source_catalog.py
    └── 02_validate_with_parqlint.sh
```

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | matches Roman SOC stack |
| pyarrow | ≥ 17.0 | Parquet KV metadata API |
| astropy | ≥ 7.0 | for `votmeta=True`; older works via explicit path |
| roman_datamodels | latest | schemas for Roman Parquet outputs |
| Java + STILTS | optional | only for `parqlint` validation |

---

## Quick Start

```bash
# install
git clone https://github.com/<your-org>/roman-voparquet
cd roman-voparquet
uv sync                  # or: pip install -e ".[dev]"

# convert a Roman source catalog
roman-voparquet convert \
    --input  r0099101001001001001_0001_wfi01_cat.parquet \
    --output r0099101001001001001_0001_wfi01_cat.voparquet

# validate (requires STILTS topcat-extra.jar)
java -jar topcat-extra.jar -stilts parqlint \
    r0099101001001001001_0001_wfi01_cat.voparquet
```

---

## How the Conversion Works

The IVOA VOParquet Note v1.0 prescribes a 3-step write recipe (Section 2.1). Here's how each maps to code:

### Step 1 — Read the input Parquet preserving schema

```python
import pyarrow.parquet as pq
from astropy.table import Table

pf = pq.ParquetFile("input.parquet")
schema = pf.schema_arrow            # column names + arrow datatypes
tbl    = Table.read("input.parquet", format="parquet")
```

### Step 2 — Build the data-less VOTable

For every column, look up `(ucd, unit, description)` from the Roman map and apply to the astropy `Column.meta`. Then build a VOTable that has FIELD elements but **no DATA child** (allowed by VOTable schema; this is the normative trick of VOParquet).

```python
from astropy.io.votable.tree import VOTableFile, Resource, Table as VOTable, Field

def build_dataless_votable(tbl, ucd_map) -> str:
    votf = VOTableFile()
    res  = Resource(type="results")
    votf.resources.append(res)
    vot  = VOTable(votf)
    res.tables.append(vot)

    for col in tbl.colnames:
        meta = ucd_map.get(col, {})
        f = Field(
            votf,
            name=col,
            datatype=arrow_to_votable_datatype(tbl[col].dtype),
            ucd=meta.get("ucd"),
            unit=meta.get("unit"),
        )
        if meta.get("description"):
            f.description = meta["description"]
        vot.fields.append(f)

    # NO vot.create_arrays() and NO data — must be data-less
    import io
    buf = io.BytesIO()
    votf.to_xml(buf)
    return buf.getvalue().decode("utf-8")
```

### Step 3 — Write Parquet with the VOTable in file-level KV metadata

The two normative keys (Note §2.2):

| Key | Value |
|-----|-------|
| `IVOA.VOTable-Parquet.version` | `"1.0"` |
| `IVOA.VOTable-Parquet.content` | the data-less VOTable XML string (UTF-8) |

```python
import pyarrow as pa, pyarrow.parquet as pq

def write_voparquet(table_arrow, votable_xml, out_path):
    existing = dict(table_arrow.schema.metadata or {})
    existing[b"IVOA.VOTable-Parquet.version"] = b"1.0"
    existing[b"IVOA.VOTable-Parquet.content"] = votable_xml.encode("utf-8")
    new_schema = table_arrow.schema.with_metadata(existing)
    table_arrow = table_arrow.cast(new_schema)
    pq.write_table(table_arrow, out_path, compression="snappy")
```

> ⚠️ The VOTable must be **schema-valid** and the dataless TABLE must be the **first** TABLE in the document. Validate with `stilts parqlint` after every change to the builder.

---

## UCD / Unit Map for Roman

The mapping lives in `src/roman_voparquet/ucd_map.py`. Built from the Roman WFI Co-add Catalog Schema ([Roman-STScI-000766](https://www.stsci.edu/roman/documentation/technical-documentation)) and `romancal` source-catalog column definitions. Sample:

| Roman column | UCD | Unit | Description |
|--------------|-----|------|-------------|
| `label` | `meta.id;src` | — | Source label / segmentation ID |
| `ra` | `pos.eq.ra;meta.main` | `deg` | Right ascension (ICRS) |
| `dec` | `pos.eq.dec;meta.main` | `deg` | Declination (ICRS) |
| `ra_err` | `stat.error;pos.eq.ra` | `deg` | RA uncertainty |
| `dec_err` | `stat.error;pos.eq.dec` | `deg` | Dec uncertainty |
| `x_centroid` | `pos.cartesian.x;instr.det` | `pix` | X centroid in detector frame |
| `y_centroid` | `pos.cartesian.y;instr.det` | `pix` | Y centroid in detector frame |
| `aper_total_flux` | `phot.flux;em.IR` | `nJy` | Total aperture flux |
| `aper_total_flux_err` | `stat.error;phot.flux;em.IR` | `nJy` | Total aperture flux error |
| `kron_flux` | `phot.flux;em.IR;src.morph.type` | `nJy` | Kron flux |
| `segment_flux` | `phot.flux;em.IR` | `nJy` | Segmentation flux |
| `is_extended` | `src.class` | — | Extended source flag |
| `sharpness` | `src.morph.param` | — | Sharpness statistic |
| `roundness` | `src.morph.param` | — | Roundness statistic |

> 💡 **Flux units**: as of `romancal` 0.18+, source catalog fluxes are **nJy** (changed from µJy). Always read the column unit from `Field.unit`, never assume.

> ⚠️ Unknown columns get logged and written with `ucd=None`, `unit=""`. They remain in the output — VOParquet readers will fall back to the raw Parquet schema for those fields, which is the spec's prescribed behavior.

---

## Roman Datamodel Metadata → VOTable PARAM / GROUP

Roman ASDF/Parquet products carry a `meta` block (instrument, observation, target, WCS). Promote these to table-level VOTable `PARAM` so VO clients see them too:

| Roman `meta` field | VOTable target | UCD |
|--------------------|----------------|-----|
| `meta.instrument.optical_element` | `<PARAM name="filter">` | `instr.bandpass` |
| `meta.observation.program` | `<PARAM name="program">` | `meta.id;obs.proposal` |
| `meta.observation.exposure` | `<PARAM name="exposure_id">` | `meta.id;obs` |
| `meta.exposure.start_time` | `<PARAM name="t_min">` | `time.start;obs.exposure` |
| `meta.exposure.end_time` | `<PARAM name="t_max">` | `time.end;obs.exposure` |
| `meta.wcs` (CRVAL) | `<COOSYS>` | — |

Add a `<COOSYS ID="ICRS" system="ICRS" epoch="J2000"/>` and reference it on `ra`/`dec` FIELDs via `ref="ICRS"`.

---

## Configuration Reference

| Env var | Default | Purpose |
|---------|---------|---------|
| `ROMAN_UCD_MAP_PATH` | bundled YAML | Override UCD/unit map without code change |
| `VOPARQUET_COMPRESSION` | `snappy` | `snappy`, `gzip`, `zstd`, `none` |
| `VOPARQUET_LOG_LEVEL` | `INFO` | Set to `DEBUG` to log unmapped columns |

---

## CLI Reference

```
roman-voparquet convert --input <path> --output <path> [options]

  --ucd-map PATH          Override the bundled column map (YAML)
  --include-meta          Promote meta.* fields to VOTable PARAM (default: on)
  --coosys ICRS|GALACTIC  Coordinate system label (default: ICRS)
  --compression TEXT      snappy | gzip | zstd | none (default: snappy)
  --validate              Run parqlint after writing (requires STILTS)
  --dry-run               Print the VOTable XML, do not write
```

---

## Validation

Two validators are recommended:

1. **`stilts parqlint`** — runs `votlint` on the embedded VOTable, checks the KV keys, and verifies column count consistency between Parquet and VOTable.
   ```bash
   java -jar topcat-extra.jar -stilts parqlint out.voparquet
   ```
2. **TOPCAT round-trip** — open in TOPCAT, confirm column metadata pane shows units and UCDs.

> ⚠️ A `parqlint` **ERROR** report blocks release. `WARNING` and `INFO` should be triaged but do not break VOParquet 1.0 compliance.

---

## Testing

```bash
uv run pytest                    # unit + round-trip tests
uv run pytest -k round_trip      # only round-trip
make validate                    # runs parqlint over tests/data/*.voparquet
```

Round-trip test invariants:
- Every column from the input Parquet appears in the output.
- For every column with a known UCD, `astropy.io.votable.parse(out).get_first_table().fields` reports the matching `ucd` and `unit`.
- Reading the output back with `pq.read_table` returns numerically identical data.

---

## Non-Goals (v1)

- **Not** a writer for non-Roman Parquet files (see TOPCAT/STILTS for the generic case).
- **Not** a VOTable-only writer — output is always Parquet.
- **No HATS / partitioning** — single-file conversion only; HATS partitioning is downstream.
- **No DataLink injection** — service descriptors can be added later via the `--ucd-map` extension hook.
- **No FITS conversion** — Parquet in, Parquet out.

---

## Open Questions

- [ ] Should `meta.wcs` (a `gwcs.WCS` object) be serialized to a VOTable `GROUP` or just summarized as a `<PARAM name="s_region">` (ObsCore-style polygon)?
- [ ] For multiband catalogs, do we emit one COOSYS per band or a single one at the table level?
- [ ] Should the converter optionally embed the original `roman_datamodels` schema URI as a custom KV pair (e.g. `IPAC.Roman.schema_uri`)?

---

## References

1. **VOParquet 1.0 Note** (IVOA, 16 Jan 2025) — https://www.ivoa.net/documents/Notes/VOParquet/20250116/NOTE-voparquet-1.0-20250116.html
2. **Parquet in Astronomy wiki** (IVOA, current implementations) — https://wiki.ivoa.net/twiki/bin/view/IVOA/ParquetInAstronomy
3. **TOPCAT/STILTS Parquet output docs** (votmeta, kvmap) — https://www.star.bris.ac.uk/mbt/topcat/sun253/outParquet.html
4. **`stilts parqlint` reference** — https://www.star.bris.ac.uk/~mbt/stilts/sun256/parqlint.html
5. **Roman Co-add Catalog Schema** (Roman-STScI-000766) — https://www.stsci.edu/roman/documentation/technical-documentation
6. **`romancal` releases** (parquet output, nJy units) — https://github.com/spacetelescope/romancal/releases
7. **Astropy VOParquet PR #16375** — https://github.com/astropy/astropy/pull/16375
8. **IVOA UCD list** (UCDlist v1.5) — https://www.ivoa.net/documents/UCD1+/

---

## Next Steps

1. Scaffold `src/roman_voparquet/` with stubs above.
2. Generate `ucd_map.py` from Roman-STScI-000766 (parse the schema doc table once, commit as YAML).
3. Implement `votable_builder.py` with the data-less builder and one round-trip test.
4. Wire CLI; add `--validate` shelling out to `stilts parqlint`.
5. CI: pin STILTS jar in `tests/bin/`, run `parqlint` against `tests/data/*.voparquet` on every PR.
6. Open a tracking ticket for HATS-partitioning extension once single-file converter ships.
