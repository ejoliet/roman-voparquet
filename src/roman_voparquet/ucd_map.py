"""Roman column -> VO metadata (ucd, unit, description) map and loader.

The default map ships as bundled YAML (``data/roman_ucd_map.yaml``). It can be
overridden per-run with a path (CLI ``--ucd-map``) or the ``ROMAN_UCD_MAP_PATH``
environment variable.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

import yaml

ENV_MAP_PATH = "ROMAN_UCD_MAP_PATH"
_BUNDLED_RESOURCE = "roman_ucd_map.yaml"


@dataclass(frozen=True)
class ColumnMeta:
    """VO metadata for a single Roman column."""

    ucd: str | None = None
    unit: str | None = None
    description: str | None = None


@dataclass
class UCDMap:
    """Lookup of Roman column name -> :class:`ColumnMeta`."""

    columns: dict[str, ColumnMeta] = field(default_factory=dict)

    def get(self, name: str) -> ColumnMeta | None:
        """Return metadata for ``name``, or ``None`` if the column is unmapped."""
        return self.columns.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self.columns

    def __len__(self) -> int:
        return len(self.columns)

    @classmethod
    def from_dict(cls, doc: dict) -> "UCDMap":
        raw = (doc or {}).get("columns", {}) or {}
        columns: dict[str, ColumnMeta] = {}
        for name, entry in raw.items():
            entry = entry or {}
            columns[name] = ColumnMeta(
                ucd=entry.get("ucd"),
                unit=entry.get("unit"),
                description=entry.get("description"),
            )
        return cls(columns=columns)


def _resolve_path(path: str | os.PathLike | None) -> Path | None:
    """Resolve an explicit path, else the env override, else None (bundled)."""
    if path is not None:
        return Path(path)
    env = os.environ.get(ENV_MAP_PATH)
    if env:
        return Path(env)
    return None


def load_ucd_map(path: str | os.PathLike | None = None) -> UCDMap:
    """Load a UCD map.

    Resolution order: explicit ``path`` -> ``ROMAN_UCD_MAP_PATH`` -> bundled YAML.
    """
    resolved = _resolve_path(path)
    if resolved is not None:
        if not resolved.is_file():
            raise FileNotFoundError(f"UCD map not found: {resolved}")
        doc = yaml.safe_load(resolved.read_text(encoding="utf-8"))
        return UCDMap.from_dict(doc)

    text = (
        resources.files("roman_voparquet.data")
        .joinpath(_BUNDLED_RESOURCE)
        .read_text(encoding="utf-8")
    )
    return UCDMap.from_dict(yaml.safe_load(text))
