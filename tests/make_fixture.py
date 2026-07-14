"""Generate tests/data/tiny_source_catalog.parquet.

A minimal Roman-like source catalog: known columns from the UCD map plus one
deliberately-unmapped column, several dtypes, and an embedded Roman ``meta``
JSON blob so the meta-promotion path is exercised.

Run:  uv run python tests/make_fixture.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

OUT = Path(__file__).parent / "data" / "tiny_source_catalog.parquet"

N = 5


def main() -> None:
    rng = np.random.default_rng(42)
    arrays = {
        "label": pa.array(np.arange(1, N + 1, dtype=np.int64)),
        "ra": pa.array(150.0 + rng.random(N) * 0.01, type=pa.float64()),
        "dec": pa.array(2.0 + rng.random(N) * 0.01, type=pa.float64()),
        "ra_err": pa.array(rng.random(N) * 1e-5, type=pa.float64()),
        "dec_err": pa.array(rng.random(N) * 1e-5, type=pa.float64()),
        "x_centroid": pa.array(rng.random(N) * 4000, type=pa.float32()),
        "y_centroid": pa.array(rng.random(N) * 4000, type=pa.float32()),
        "aper_total_flux": pa.array(rng.random(N) * 1000, type=pa.float64()),
        "aper_total_flux_err": pa.array(rng.random(N) * 10, type=pa.float64()),
        "segment_flux": pa.array(rng.random(N) * 1000, type=pa.float64()),
        "is_extended": pa.array(rng.integers(0, 2, N).astype(bool)),
        "sharpness": pa.array(rng.random(N), type=pa.float32()),
        "warning_flags": pa.array(rng.integers(0, 8, N, dtype=np.int32)),
        # deliberately unmapped, and a string column to exercise char/arraysize
        "custom_note": pa.array([f"src-{i}" for i in range(N)], type=pa.string()),
    }
    table = pa.table(arrays)

    meta = {
        "instrument": {"optical_element": "F158"},
        "observation": {"program": 1234, "exposure": 1},
        "exposure": {
            "start_time": "2027-05-01T00:00:00.000",
            "end_time": "2027-05-01T00:02:00.000",
        },
    }
    schema = table.schema.with_metadata({b"meta": json.dumps(meta).encode("utf-8")})
    table = table.cast(schema)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, str(OUT), compression="snappy")
    print(f"wrote {OUT} ({table.num_rows} rows, {table.num_columns} columns)")


if __name__ == "__main__":
    main()
