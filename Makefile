# Every recipe is a plain `uv run ...` call so it behaves the same under cmd.exe, Git Bash and Linux.
.PHONY: setup test lint format run-mvp run-all run-control run-hosted run-3b run-quiet run-hosted-quiet tables-quiet run-defenses figures run-detector-langs tables-detector-langs run-detector-benign run-defenses-3b-hi tables-defenses-3b-hi demo-data demo check tables-control report check-report

# usage: make check CONFIG=configs/mvp.yaml  (exit 1 if the rows on disk do not cover the grid)
check:
	uv run aie check $(CONFIG)

tables-control:
	uv run python analysis/tables.py --inputs results/control results/hosted_control --out results/summary_control

report:
	uv run python analysis/build_report.py

check-report:
	uv run python analysis/check_report_numbers.py

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

run-control:
	uv run aie run configs/control.yaml

run-3b:
	uv run aie run configs/full_3b.yaml

run-quiet:
	uv run aie run configs/quiet_control.yaml
	uv run aie run configs/quiet.yaml

run-hosted-quiet:
	uv run aie run configs/hosted_quiet_control.yaml
	uv run aie run configs/hosted_quiet.yaml

tables-quiet:
	uv run python analysis/tables.py --inputs results/quiet results/quiet_control results/hosted_quiet results/hosted_quiet_control --attacks configs/attacks_quiet.yaml --out results/summary_quiet

run-hosted:
	uv run aie run configs/hosted_control.yaml
	uv run aie run configs/hosted.yaml

run-defenses:
	uv run aie run configs/defenses.yaml

figures:
	uv run python analysis/tables.py
	uv run python analysis/make_figures.py

run-detector-langs:
	uv run aie run configs/detector_langs.yaml

tables-detector-langs:
	uv run python analysis/tables.py --inputs results/detector_langs results/detector_benign_control --out results/summary_detector_langs

run-detector-benign:
	uv run aie run configs/detector_benign_control.yaml

run-defenses-3b-hi:
	uv run aie run configs/defenses_3b_hi.yaml

tables-defenses-3b-hi:
	uv run python analysis/tables.py --inputs results/defenses_3b_hi --out results/summary_defenses_3b_hi

demo-data:
	uv run python analysis/export_demo_data.py

demo: demo-data
	npm --prefix demo ci
	npm --prefix demo run build
	npm --prefix demo run check:dist
