"""Tests for the UCD/unit map and loader."""

from __future__ import annotations

import pytest

from roman_voparquet.ucd_map import ENV_MAP_PATH, load_ucd_map


def test_bundled_map_loads():
    m = load_ucd_map()
    assert len(m) > 0
    assert "ra" in m
    assert "dec" in m


def test_known_column_metadata():
    m = load_ucd_map()
    ra = m.get("ra")
    assert ra.ucd == "pos.eq.ra;meta.main"
    assert ra.unit == "deg"
    assert "ascension" in ra.description.lower()


def test_flux_units_are_njy():
    m = load_ucd_map()
    assert m.get("aper_total_flux").unit == "nJy"
    assert m.get("segment_flux").unit == "nJy"


def test_dimensionless_column_has_no_unit():
    m = load_ucd_map()
    label = m.get("label")
    assert label.ucd == "meta.id;src"
    assert label.unit is None


def test_unknown_column_returns_none():
    m = load_ucd_map()
    assert m.get("definitely_not_a_roman_column") is None
    assert "definitely_not_a_roman_column" not in m


def test_override_via_path(tmp_path):
    p = tmp_path / "custom.yaml"
    p.write_text(
        "version: 1\ncolumns:\n  foo:\n    ucd: meta.id\n    unit: s\n    description: bar\n"
    )
    m = load_ucd_map(p)
    assert len(m) == 1
    assert m.get("foo").ucd == "meta.id"
    assert m.get("foo").unit == "s"


def test_override_via_env(tmp_path, monkeypatch):
    p = tmp_path / "env.yaml"
    p.write_text("version: 1\ncolumns:\n  baz:\n    ucd: pos\n")
    monkeypatch.setenv(ENV_MAP_PATH, str(p))
    m = load_ucd_map()
    assert "baz" in m
    assert m.get("baz").unit is None


def test_missing_path_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_ucd_map(tmp_path / "nope.yaml")
