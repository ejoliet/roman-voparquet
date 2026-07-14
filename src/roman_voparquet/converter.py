"""Orchestrate: Roman Parquet in -> VOParquet 1.0 out.

Read the input Parquet (preserving its schema/data), build the data-less
VOTable, then rewrite the Parquet merging the two normative IVOA keys into the
file-level KV metadata.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from ._version import KEY_CONTENT, KEY_SCHEMA_URI, KEY_VERSION, VOPARQUET_VERSION
from .datamodel import extract_meta_dict, meta_to_params
from .ucd_map import UCDMap, load_ucd_map
from .votable_builder import build_dataless_votable

logger = logging.getLogger(__name__)

_VALID_COMPRESSION = {"snappy", "gzip", "zstd", "none"}


@dataclass
class ConversionResult:
    """Outcome of a conversion."""

    output: Path | None
    votable_xml: str
    n_columns: int
    unmapped: list[str] = field(default_factory=list)
    n_params: int = 0
    dry_run: bool = False


def _resolve_compression(compression: str | None) -> str:
    comp = (compression or os.environ.get("VOPARQUET_COMPRESSION") or "snappy").lower()
    if comp not in _VALID_COMPRESSION:
        raise ValueError(
            f"invalid compression {comp!r}; choose one of {sorted(_VALID_COMPRESSION)}"
        )
    return comp


def write_voparquet(
    table_arrow: pa.Table,
    votable_xml: str,
    out_path: str | os.PathLike,
    *,
    compression: str = "snappy",
    schema_uri: str | None = None,
) -> None:
    """Write ``table_arrow`` to ``out_path`` with the VOParquet KV metadata.

    Merges the two normative keys into any existing schema metadata (never
    clobbers). ``schema.with_metadata`` replaces the whole map, so we copy the
    existing pairs first.
    """
    existing = dict(table_arrow.schema.metadata or {})
    existing[KEY_VERSION] = VOPARQUET_VERSION.encode("utf-8")
    existing[KEY_CONTENT] = votable_xml.encode("utf-8")
    if schema_uri:
        existing[KEY_SCHEMA_URI] = schema_uri.encode("utf-8")

    new_schema = table_arrow.schema.with_metadata(existing)
    table_arrow = table_arrow.cast(new_schema)

    pq_compression = None if compression == "none" else compression
    pq.write_table(table_arrow, str(out_path), compression=pq_compression)


def convert(
    input_path: str | os.PathLike,
    output_path: str | os.PathLike | None = None,
    *,
    ucd_map: UCDMap | None = None,
    ucd_map_path: str | os.PathLike | None = None,
    include_meta: bool = True,
    coosys: str = "ICRS",
    compression: str | None = None,
    schema_uri: str | None = None,
    dry_run: bool = False,
) -> ConversionResult:
    """Convert a Roman Parquet catalog into a VOParquet 1.0 file.

    Returns a :class:`ConversionResult`. When ``dry_run`` is set, no file is
    written and ``output`` is ``None`` — the VOTable XML is still returned.
    """
    input_path = Path(input_path)
    if not input_path.is_file():
        raise FileNotFoundError(f"input Parquet not found: {input_path}")

    if ucd_map is None:
        ucd_map = load_ucd_map(ucd_map_path)

    table_arrow = pq.read_table(str(input_path))
    schema = table_arrow.schema

    unmapped: list[str] = []
    params = []
    if include_meta:
        params = meta_to_params(extract_meta_dict(schema))

    votable_xml = build_dataless_votable(
        schema,
        ucd_map,
        coosys=coosys,
        params=params,
        on_unmapped=unmapped.append,
    )

    if unmapped:
        logger.warning(
            "%d column(s) not in UCD map (written with empty ucd/unit): %s",
            len(unmapped),
            ", ".join(unmapped),
        )

    if dry_run:
        return ConversionResult(
            output=None,
            votable_xml=votable_xml,
            n_columns=len(schema.names),
            unmapped=unmapped,
            n_params=len(params),
            dry_run=True,
        )

    if output_path is None:
        raise ValueError("output_path is required unless dry_run=True")

    comp = _resolve_compression(compression)
    write_voparquet(
        table_arrow,
        votable_xml,
        output_path,
        compression=comp,
        schema_uri=schema_uri,
    )
    logger.info(
        "wrote %s (%d columns, %d params, compression=%s)",
        output_path,
        len(schema.names),
        len(params),
        comp,
    )

    return ConversionResult(
        output=Path(output_path),
        votable_xml=votable_xml,
        n_columns=len(schema.names),
        unmapped=unmapped,
        n_params=len(params),
    )


def validate_with_parqlint(
    path: str | os.PathLike,
    *,
    stilts_jar: str | os.PathLike | None = None,
) -> tuple[bool, str]:
    """Run ``stilts parqlint`` on ``path``.

    Resolution: explicit ``stilts_jar`` -> ``STILTS_JAR`` env -> ``stilts`` on
    PATH. Returns ``(ok, combined_output)``; ``ok`` is False when parqlint
    reports any ERROR or the command is unavailable/non-zero.
    """
    jar = stilts_jar or os.environ.get("STILTS_JAR")
    if jar:
        cmd = ["java", "-jar", str(jar), "-stilts", "parqlint", str(path)]
    elif shutil.which("stilts"):
        cmd = ["stilts", "parqlint", str(path)]
    else:
        return False, (
            "parqlint unavailable: no STILTS jar (set STILTS_JAR or pass "
            "--stilts-jar) and 'stilts' not on PATH"
        )

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover
        return False, f"failed to run parqlint: {exc}"

    output = (proc.stdout or "") + (proc.stderr or "")
    ok = proc.returncode == 0 and "ERROR" not in output
    return ok, output
