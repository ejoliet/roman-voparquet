"""Normative VOParquet 1.0 constants (Note §2.2).

These strings are case-sensitive and fixed by the IVOA VOParquet 1.0 Note.
They are stored as bytes because pyarrow schema metadata is a bytes->bytes map.
"""

#: VOParquet convention version this tool emits.
VOPARQUET_VERSION = "1.0"

#: File-level KV key carrying the convention version.
KEY_VERSION = b"IVOA.VOTable-Parquet.version"

#: File-level KV key carrying the data-less VOTable XML (UTF-8).
KEY_CONTENT = b"IVOA.VOTable-Parquet.content"

#: Optional, namespaced custom KV key for the originating Roman schema URI.
#: Non-standard keys are legal per the Note; keep them namespaced.
KEY_SCHEMA_URI = b"IPAC.Roman.schema_uri"
