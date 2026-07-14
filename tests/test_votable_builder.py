"""Tests for the data-less VOTable builder."""

from __future__ import annotations

import io

import pyarrow as pa
import pytest
from astropy.io.votable import parse

from roman_voparquet.ucd_map import load_ucd_map
from roman_voparquet.votable_builder import (
    Param,
    _VOType,
    arrow_to_votable_datatype,
    build_dataless_votable,
)


@pytest.mark.parametrize(
    "atype,expected",
    [
        (pa.bool_(), _VOType("boolean")),
        (pa.int8(), _VOType("short")),
        (pa.int16(), _VOType("short")),
        (pa.int32(), _VOType("int")),
        (pa.int64(), _VOType("long")),
        (pa.uint8(), _VOType("unsignedByte")),
        (pa.uint16(), _VOType("int")),
        (pa.uint32(), _VOType("long")),
        (pa.float32(), _VOType("float")),
        (pa.float64(), _VOType("double")),
        (pa.string(), _VOType("char", "*")),
        (pa.large_string(), _VOType("char", "*")),
        (pa.binary(), _VOType("unsignedByte", "*")),
    ],
)
def test_arrow_datatype_mapping(atype, expected):
    assert arrow_to_votable_datatype(atype) == expected


def _schema():
    return pa.schema(
        [
            ("ra", pa.float64()),
            ("dec", pa.float64()),
            ("aper_total_flux", pa.float64()),
            ("custom_note", pa.string()),
        ]
    )


def test_dataless_votable_has_no_data():
    xml = build_dataless_votable(_schema(), load_ucd_map())
    # The normative trick: FIELDs present, DATA absent.
    assert "<FIELD" in xml
    assert "<DATA" not in xml
    assert "<TABLEDATA" not in xml


def test_votable_is_schema_valid_and_reparses():
    xml = build_dataless_votable(_schema(), load_ucd_map())
    vot = parse(io.BytesIO(xml.encode("utf-8")))  # raises on invalid
    table = vot.get_first_table()
    names = [f.name for f in table.fields]
    assert names == ["ra", "dec", "aper_total_flux", "custom_note"]


def test_fields_carry_ucd_and_unit():
    xml = build_dataless_votable(_schema(), load_ucd_map())
    table = parse(io.BytesIO(xml.encode("utf-8"))).get_first_table()
    by_name = {f.name: f for f in table.fields}
    assert by_name["ra"].ucd == "pos.eq.ra;meta.main"
    assert by_name["ra"].unit == "deg"
    assert by_name["aper_total_flux"].unit == "nJy"


def test_string_field_has_char_arraysize():
    xml = build_dataless_votable(_schema(), load_ucd_map())
    table = parse(io.BytesIO(xml.encode("utf-8"))).get_first_table()
    note = {f.name: f for f in table.fields}["custom_note"]
    assert note.datatype == "char"
    assert note.arraysize == "*"


def test_unmapped_columns_are_reported():
    seen = []
    build_dataless_votable(_schema(), load_ucd_map(), on_unmapped=seen.append)
    assert seen == ["custom_note"]


def test_coosys_present_and_referenced():
    xml = build_dataless_votable(_schema(), load_ucd_map(), coosys="ICRS")
    assert 'ID="ICRS"' in xml
    table = parse(io.BytesIO(xml.encode("utf-8"))).get_first_table()
    by_name = {f.name: f for f in table.fields}
    assert by_name["ra"].ref == "ICRS"
    assert by_name["dec"].ref == "ICRS"
    # a non-position field is not tied to the coordinate system
    assert by_name["aper_total_flux"].ref is None


def test_coosys_can_be_omitted():
    xml = build_dataless_votable(_schema(), load_ucd_map(), coosys=None)
    assert "<COOSYS" not in xml


def test_params_promoted():
    params = [Param(name="filter", value="F158", ucd="instr.bandpass")]
    xml = build_dataless_votable(_schema(), load_ucd_map(), params=params)
    table = parse(io.BytesIO(xml.encode("utf-8"))).get_first_table()
    pnames = {p.name: p for p in table.params}
    assert "filter" in pnames
    assert pnames["filter"].value == "F158"
