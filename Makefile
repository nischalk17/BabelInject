# Every recipe is a plain `uv run ...` call so it behaves the same under cmd.exe, Git Bash and Linux.
.PHONY: setup test lint format run-mvp run-all run-defenses figures

setup:
	uv sync
	uv run pre-commit install

test:
	uv run pytest -q

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src

format:
	uv run ruff check --fix .
	uv run ruff format .

run-mvp:
	uv run aie run configs/mvp.yaml

run-all:
	uv run aie run configs/full.yaml

run-defenses:
	uv run aie run configs/defenses.yaml

figures:
	uv run python analysis/make_figures.py
