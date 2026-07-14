"""Round-trip tests: convert then read back and compare."""

from __future__ import annotations

import io

import pyarrow.parquet as pq
from astropy.io.votable import parse

from roman_voparquet._version import KEY_CONTENT, KEY_SCHEMA_URI, KEY_VERSION
from roman_voparquet.converter import convert
from roman_voparquet.ucd_map import load_ucd_map


def test_convert_writes_normative_keys(tiny_catalog, tmp_path):
    out = tmp_path / "out.voparquet"
    result = convert(tiny_catalog, out)
    assert result.output == out
    md = pq.read_metadata(str(out)).metadata
    assert md[KEY_VERSION] == b"1.0"
    assert KEY_CONTENT in md
    assert md[KEY_CONTENT].startswith(b"<?xml")


def test_data_is_numerically_identical(tiny_catalog, tmp_path):
    out = tmp_path / "out.voparquet"
    convert(tiny_catalog, out)
    src = pq.read_table(str(tiny_catalog))
    dst = pq.read_table(str(out))
    assert src.column_names == dst.column_names
    assert src.equals(dst, check_metadata=False)


def test_every_column_preserved(tiny_catalog, tmp_path):
    out = tmp_path / "out.voparquet"
    convert(tiny_catalog, out)
    src_cols = pq.read_table(str(tiny_catalog)).column_names
    md = pq.read_metadata(str(out)).metadata
    vot = parse(io.BytesIO(md[KEY_CONTENT]))
    field_names = [f.name for f in vot.get_first_table().fields]
    assert field_names == src_cols


def test_known_ucds_and_units_match_map(tiny_catalog, tmp_path):
    out = tmp_path / "out.voparquet"
    convert(tiny_catalog, out)
    md = pq.read_metadata(str(out)).metadata
    vot = parse(io.BytesIO(md[KEY_CONTENT]))
    fields = {f.name: f for f in vot.get_first_table().fields}
    umap = load_ucd_map()
    for name, field in fields.items():
        meta = umap.get(name)
        if meta is None:
            continue
        assert field.ucd == meta.ucd
        # astropy normalizes some unit strings (e.g. pix -> pixel); compare loosely
        if meta.unit in (None, ""):
            assert field.unit in (None, "")


def test_unmapped_columns_survive_with_warning(tiny_catalog, tmp_path, caplog):
    out = tmp_path / "out.voparquet"
    with caplog.at_level("WARNING"):
        result = convert(tiny_catalog, out)
    assert "custom_note" in result.unmapped
    assert any("custom_note" in r.message for r in caplog.records)
    # still present in output
    assert "custom_note" in pq.read_table(str(out)).column_names


def test_meta_promoted_to_params(tiny_catalog, tmp_path):
    out = tmp_path / "out.voparquet"
    result = convert(tiny_catalog, out, include_meta=True)
    assert result.n_params >= 1
    md = pq.read_metadata(str(out)).metadata
    vot = parse(io.BytesIO(md[KEY_CONTENT]))
    pnames = {p.name for p in vot.get_first_table().params}
    assert "filter" in pnames


def test_no_meta_when_disabled(tiny_catalog, tmp_path):
    out = tmp_path / "out.voparquet"
    result = convert(tiny_catalog, out, include_meta=False)
    assert result.n_params == 0


def test_schema_uri_embedded_when_requested(tiny_catalog, tmp_path):
    out = tmp_path / "out.voparquet"
    convert(tiny_catalog, out, schema_uri="asdf://roman/schema/wfi_catalog-1.0")
    md = pq.read_metadata(str(out)).metadata
    assert md[KEY_SCHEMA_URI] == b"asdf://roman/schema/wfi_catalog-1.0"


def test_dry_run_writes_nothing(tiny_catalog, tmp_path):
    out = tmp_path / "should_not_exist.voparquet"
    result = convert(tiny_catalog, out, dry_run=True)
    assert result.dry_run is True
    assert result.output is None
    assert not out.exists()
    assert result.votable_xml.startswith("<?xml")


def test_existing_metadata_preserved(tiny_catalog, tmp_path):
    # the fixture carries a b"meta" JSON blob; conversion must not drop it
    out = tmp_path / "out.voparquet"
    convert(tiny_catalog, out)
    md = pq.read_metadata(str(out)).metadata
    assert b"meta" in md
    assert KEY_VERSION in md


def test_compression_options(tiny_catalog, tmp_path):
    for comp in ("snappy", "gzip", "zstd", "none"):
        out = tmp_path / f"out_{comp}.voparquet"
        convert(tiny_catalog, out, compression=comp)
        dst = pq.read_table(str(out))
        assert "ra" in dst.column_names
