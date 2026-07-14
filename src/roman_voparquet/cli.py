"""``roman-voparquet`` command-line interface."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

import typer

from . import __version__
from .converter import convert, validate_with_parqlint

app = typer.Typer(
    add_completion=False,
    help="Convert Roman-datamodel Parquet catalogs into VOParquet 1.0.",
    no_args_is_help=True,
)


def _configure_logging() -> None:
    level = os.environ.get("VOPARQUET_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(levelname)s %(name)s: %(message)s",
    )


@app.command("convert")
def convert_cmd(
    input: Path = typer.Option(..., "--input", "-i", help="Input Roman Parquet file."),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output VOParquet file (omit with --dry-run)."
    ),
    ucd_map: Optional[Path] = typer.Option(
        None, "--ucd-map", help="Override the bundled column map (YAML)."
    ),
    include_meta: bool = typer.Option(
        True, "--include-meta/--no-include-meta", help="Promote meta.* to PARAMs."
    ),
    coosys: str = typer.Option(
        "ICRS", "--coosys", help="Coordinate system label (ICRS | GALACTIC)."
    ),
    compression: str = typer.Option(
        "snappy", "--compression", help="snappy | gzip | zstd | none."
    ),
    schema_uri: Optional[str] = typer.Option(
        None, "--schema-uri", help="Embed originating schema URI as a custom KV pair."
    ),
    validate: bool = typer.Option(
        False, "--validate", help="Run parqlint after writing (requires STILTS)."
    ),
    stilts_jar: Optional[Path] = typer.Option(
        None, "--stilts-jar", help="Path to topcat-extra.jar / stilts.jar."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print the VOTable XML; do not write."
    ),
) -> None:
    """Convert INPUT into a VOParquet 1.0 file at OUTPUT."""
    _configure_logging()

    if not dry_run and output is None:
        typer.secho("error: --output is required unless --dry-run", fg="red", err=True)
        raise typer.Exit(2)

    try:
        result = convert(
            input,
            output,
            ucd_map_path=ucd_map,
            include_meta=include_meta,
            coosys=coosys,
            compression=compression,
            schema_uri=schema_uri,
            dry_run=dry_run,
        )
    except (FileNotFoundError, ValueError) as exc:
        typer.secho(f"error: {exc}", fg="red", err=True)
        raise typer.Exit(1)

    if dry_run:
        typer.echo(result.votable_xml)
        raise typer.Exit(0)

    typer.secho(
        f"wrote {result.output}  ({result.n_columns} columns, "
        f"{result.n_params} params, {len(result.unmapped)} unmapped)",
        fg="green",
    )

    if validate:
        ok, report = validate_with_parqlint(result.output, stilts_jar=stilts_jar)
        typer.echo(report.rstrip() or "(no parqlint output)")
        if ok:
            typer.secho("parqlint: OK (no ERRORs)", fg="green")
        else:
            typer.secho("parqlint: FAILED (see report above)", fg="red", err=True)
            raise typer.Exit(1)


@app.command("version")
def version_cmd() -> None:
    """Print the tool version."""
    typer.echo(__version__)


def main() -> None:  # pragma: no cover
    app()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(app())
