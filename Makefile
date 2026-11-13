install:
	uv venv --python 3.12
	uv sync --extra docs --extra dev

dev: install
	curl -sf https://raw.githubusercontent.com/doplaydo/pdk-ci-workflow-public/main/templates/.pre-commit-config.yaml -o .pre-commit-config.yaml
	uv run pre-commit clean
	uv run pre-commit install

test:
	uv run pytest -s tests

test-notebooks:
	@fail=0; \
	for notebook in $$(find notebooks -name "*.ipynb" | sort); do \
		case "$$notebook" in \
			*hfss_*|*hfss-*|*matlab_*|*matlab-*|*_meep*|*meep_*) \
				echo "Skipping $$notebook (needs tools unavailable in CI)"; continue;; \
			esac; \
		echo "Executing $$notebook"; \
		uv run jupyter nbconvert --to notebook --execute "$$notebook" \
			--output-dir "$${TMPDIR:-/tmp}/gpdk-notebooks" \
			--ExecutePreprocessor.timeout=600 || fail=1; \
	done; \
	test "$$fail" -eq 0

test-force:
	uv run pytest -s tests --update-gds-refs --force-regen

cells-check:
	uv run python .github/generate_cells.py --check

cells-regen:
	uv run python .github/generate_cells.py --write

docs:
	uv run python .github/write_cells.py
	cp CHANGELOG.md docs/changelog.md
	cp README.md docs/index.md
	uv run --extra docs zensical build -f docs/zensical.toml

build:
	rm -rf dist
	uv build

update-pre:
	pre-commit autoupdate

.PHONY: install dev test test-force test-notebooks cells-check cells-regen docs build update-pre
