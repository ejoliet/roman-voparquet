"""Extract Roman datamodel ``meta`` and map it to table-level VOTable PARAMs.

Roman ASDF/Parquet products carry a nested ``meta`` block (instrument,
observation, exposure, target, WCS). This module pulls what it can find and
maps the well-known fields to PARAMs per the README's mapping table.

Extraction is best-effort and never raises on missing/oddly-shaped meta: a
catalog with no recoverable meta simply yields no PARAMs.
"""

from __future__ import annotations

import json
import logging

import pyarrow as pa

from .votable_builder import Param

logger = logging.getLogger(__name__)

# Roman meta dotted-path -> (PARAM name, ucd). Order defines PARAM order.
_META_TO_PARAM: list[tuple[str, str, str | None]] = [
    ("instrument.optical_element", "filter", "instr.bandpass"),
    ("observation.program", "program", "meta.id;obs.proposal"),
    ("observation.exposure", "exposure_id", "meta.id;obs"),
    ("exposure.start_time", "t_min", "time.start;obs.exposure"),
    ("exposure.end_time", "t_max", "time.end;obs.exposure"),
]


def _dig(meta: dict, dotted: str):
    """Walk a dotted path through nested dicts; return None if absent."""
    node = meta
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def extract_meta_dict(arrow_schema: pa.Schema) -> dict:
    """Best-effort recovery of a Roman ``meta`` dict from Parquet KV metadata.

    Looks for a JSON blob under the ``meta`` (or ``roman.meta``) key. Returns an
    empty dict when nothing usable is found.
    """
    kv = arrow_schema.metadata or {}
    for key in (b"meta", b"roman.meta", b"roman_meta"):
        raw = kv.get(key)
        if raw is None:
            continue
        try:
            doc = json.loads(raw.decode("utf-8"))
            if isinstance(doc, dict):
                return doc
        except (ValueError, UnicodeDecodeError):
            logger.debug("meta key %r present but not JSON-decodable", key)
    return {}


def meta_to_params(meta: dict) -> list[Param]:
    """Map a Roman ``meta`` dict to table-level VOTable PARAMs."""
    if not meta:
        return []
    params: list[Param] = []
    for dotted, pname, ucd in _META_TO_PARAM:
        value = _dig(meta, dotted)
        if value is None:
            continue
        params.append(Param(name=pname, value=str(value), ucd=ucd))
    return params
