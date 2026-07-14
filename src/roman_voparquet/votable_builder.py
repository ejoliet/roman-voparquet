"""Build a *data-less* VOTable (FIELDs only, no DATA) from a Parquet schema.

This is the normative trick of VOParquet: a schema-valid VOTable whose first
TABLE has FIELD elements but no DATA child. The XML string it returns is what
gets embedded in the Parquet file-level KV metadata.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import pyarrow as pa
from astropy.io.votable import tree
from astropy.io.votable.tree import Field, Resource, VOTableFile

from .ucd_map import UCDMap

# Arrow logical type -> (VOTable datatype, arraysize or None).
# VOTable 1.4 datatypes: boolean, bit, unsignedByte, short, int, long,
# float, double, char, unicodeChar (+ complex variants, unused here).


@dataclass(frozen=True)
class _VOType:
    datatype: str
    arraysize: str | None = None


def arrow_to_votable_datatype(atype: pa.DataType) -> _VOType:
    """Map a pyarrow type to a VOTable ``(datatype, arraysize)``.

    VOTable has no unsigned short/int, so unsigned types are promoted to the
    next wider signed type. Variable-length strings/binary get ``arraysize='*'``.
    """
    if pa.types.is_boolean(atype):
        return _VOType("boolean")

    # unsigned
    if pa.types.is_uint8(atype):
        return _VOType("unsignedByte")
    if pa.types.is_uint16(atype):
        return _VOType("int")  # promote: no unsignedShort in VOTable
    if pa.types.is_uint32(atype):
        return _VOType("long")  # promote
    if pa.types.is_uint64(atype):
        return _VOType("long")  # best effort

    # signed int
    if pa.types.is_int8(atype):
        return _VOType("short")  # no signed byte in VOTable
    if pa.types.is_int16(atype):
        return _VOType("short")
    if pa.types.is_int32(atype):
        return _VOType("int")
    if pa.types.is_int64(atype):
        return _VOType("long")

    # float
    if pa.types.is_float16(atype) or pa.types.is_float32(atype):
        return _VOType("float")
    if pa.types.is_float64(atype):
        return _VOType("double")

    # strings / binary
    if (
        pa.types.is_string(atype)
        or pa.types.is_large_string(atype)
        or pa.types.is_string_view(atype)
    ):
        return _VOType("char", "*")
    if (
        pa.types.is_binary(atype)
        or pa.types.is_large_binary(atype)
        or pa.types.is_fixed_size_binary(atype)
    ):
        return _VOType("unsignedByte", "*")

    # temporal -> render as ISO char (readers fall back to parquet type anyway)
    if pa.types.is_temporal(atype):
        return _VOType("char", "*")

    # unknown -> safest schema-valid fallback
    return _VOType("char", "*")


@dataclass
class Param:
    """A table-level VOTable PARAM to promote from Roman ``meta``."""

    name: str
    value: str
    ucd: str | None = None
    unit: str | None = None
    datatype: str = "char"


def build_dataless_votable(
    arrow_schema: pa.Schema,
    ucd_map: UCDMap,
    *,
    coosys: str | None = "ICRS",
    params: list[Param] | None = None,
    on_unmapped=None,
) -> str:
    """Build the data-less VOTable XML for ``arrow_schema``.

    Parameters
    ----------
    arrow_schema
        The Parquet schema (column names + arrow types), authoritative order.
    ucd_map
        Roman column -> VO metadata lookup.
    coosys
        Coordinate system id/system to attach as a single table-level COOSYS.
        ``ra``/``dec`` FIELDs reference it. Pass ``None`` to omit.
    params
        Table-level PARAMs (from Roman ``meta``), or ``None``.
    on_unmapped
        Optional callback ``fn(column_name)`` invoked for each column absent
        from ``ucd_map`` (used for logging).
    """
    votf = VOTableFile()
    resource = Resource(type="results")
    votf.resources.append(resource)

    coosys_id = None
    if coosys:
        coosys_id = coosys
        system = "galactic" if coosys.upper() == "GALACTIC" else "ICRS"
        cs = tree.CooSys(ID=coosys_id, system=system, epoch="J2000")
        resource.coordinate_systems.append(cs)

    votable = tree.TableElement(votf)
    resource.tables.append(votable)

    if params:
        for p in params:
            votable.params.append(
                tree.Param(
                    votf,
                    name=p.name,
                    datatype=p.datatype,
                    arraysize="*" if p.datatype == "char" else None,
                    ucd=p.ucd,
                    unit=p.unit,
                    value=p.value,
                )
            )

    fields = []
    for name in arrow_schema.names:
        atype = arrow_schema.field(name).type
        votype = arrow_to_votable_datatype(atype)
        meta = ucd_map.get(name)
        if meta is None and on_unmapped is not None:
            on_unmapped(name)

        ref = None
        if coosys_id and meta is not None and meta.ucd:
            if meta.ucd.startswith("pos.eq.ra") or meta.ucd.startswith("pos.eq.dec"):
                ref = coosys_id

        f = Field(
            votf,
            name=name,
            datatype=votype.datatype,
            arraysize=votype.arraysize,
            ucd=(meta.ucd if meta else None),
            unit=(meta.unit if meta else None),
            ref=ref,
        )
        if meta is not None and meta.description:
            f.description = meta.description
        fields.append(f)

    votable.fields.extend(fields)

    # NO votable.create_arrays() and NO DATA element -> data-less by construction.
    buf = io.BytesIO()
    votf.to_xml(buf)
    return buf.getvalue().decode("utf-8")
