"""roman-voparquet: convert Roman-datamodel Parquet catalogs into VOParquet 1.0.

A VOParquet 1.0 file is an ordinary Parquet file that carries a *data-less*
VOTable header in its file-level key-value metadata under two normative keys:

    IVOA.VOTable-Parquet.version   = "1.0"
    IVOA.VOTable-Parquet.content   = <data-less VOTable XML, UTF-8>

See the IVOA VOParquet 1.0 Note (2025-01-16):
https://www.ivoa.net/documents/Notes/VOParquet/20250116/NOTE-voparquet-1.0-20250116.html
"""

from ._version import (
    VOPARQUET_VERSION,
    KEY_VERSION,
    KEY_CONTENT,
)
from .ucd_map import UCDMap, load_ucd_map
from .converter import convert

__all__ = [
    "VOPARQUET_VERSION",
    "KEY_VERSION",
    "KEY_CONTENT",
    "UCDMap",
    "load_ucd_map",
    "convert",
]

__version__ = "0.1.0"
