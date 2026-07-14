"""Convert a Roman source catalog to VOParquet 1.0 and inspect the result.

Usage:
    uv run python examples/01_convert_source_catalog.py \
        tests/data/tiny_source_catalog.parquet /tmp/out.voparquet
"""

from __future__ import annotations

import io
import sys

import pyarrow.parquet as pq
from astropy.io.votable import parse

from roman_voparquet._version import KEY_CONTENT, KEY_VERSION
from roman_voparquet.converter import convert


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    _, inp, out = argv

    result = convert(inp, out)
    print(f"wrote {result.output}: {result.n_columns} columns, "
          f"{result.n_params} params, {len(result.unmapped)} unmapped")

    md = pq.read_metadata(out).metadata
    print("VOParquet version:", md[KEY_VERSION].decode())

    vot = parse(io.BytesIO(md[KEY_CONTENT]))
    print("\ncolumn                ucd                          unit")
    print("-" * 64)
    for f in vot.get_first_table().fields:
        print(f"{f.name:<22}{(f.ucd or ''):<29}{f.unit or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
