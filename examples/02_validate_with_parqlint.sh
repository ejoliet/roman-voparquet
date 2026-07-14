#!/usr/bin/env bash
# Validate a VOParquet file with the reference validator (STILTS parqlint).
#
# parqlint needs the parquet libraries on the classpath, which many plain
# STILTS distributions omit. Use topcat-extra.jar (bundles them):
#
#   curl -L -o topcat-extra.jar https://www.star.bris.ac.uk/~mbt/topcat/topcat-extra.jar
#   ./examples/02_validate_with_parqlint.sh out.voparquet [path/to/topcat-extra.jar]
#
# Only ERROR reports break VOParquet 1.0 compliance; WARNING/INFO are advisory.
set -euo pipefail

FILE="${1:?usage: 02_validate_with_parqlint.sh <file.voparquet> [stilts.jar]}"
JAR="${2:-${STILTS_JAR:-topcat-extra.jar}}"

if [[ -f "$JAR" ]]; then
    java -jar "$JAR" -stilts parqlint "$FILE"
elif command -v stilts >/dev/null 2>&1; then
    stilts parqlint "$FILE"
else
    echo "error: no STILTS jar at '$JAR' and 'stilts' not on PATH" >&2
    echo "download: https://www.star.bris.ac.uk/~mbt/topcat/topcat-extra.jar" >&2
    exit 1
fi
