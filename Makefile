.PHONY: help sync test fixture convert validate lint clean

STILTS_JAR ?= topcat-extra.jar
FIXTURE    := tests/data/tiny_source_catalog.parquet
OUT        := tests/data/tiny_source_catalog.voparquet

help:
	@echo "targets: sync test fixture convert validate clean"

sync:
	uv sync --extra dev

fixture:
	uv run python tests/make_fixture.py

test:
	uv run pytest

convert: fixture
	uv run roman-voparquet convert -i $(FIXTURE) -o $(OUT)

# Validate every *.voparquet under tests/data with parqlint.
validate:
	@command -v java >/dev/null || { echo "java not found"; exit 1; }
	@for f in tests/data/*.voparquet; do \
		echo "=== parqlint $$f ==="; \
		java -jar $(STILTS_JAR) -stilts parqlint "$$f"; \
	done

clean:
	rm -f tests/data/*.voparquet /tmp/*.voparquet
