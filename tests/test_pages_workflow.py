"""Guards on the GitHub Pages workflow and the demo's base path (no network, parses the files)."""

import json
import re
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parent.parent
WORKFLOW = REPO / ".github/workflows/pages.yml"


def _workflow() -> dict[str, Any]:
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    return doc


def _triggers(doc: dict[str, Any]) -> dict[str, Any]:
    # PyYAML reads the bare key `on` as the boolean True.
    return doc.get("on") or doc[True]


def _steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    return list(job["steps"])


def test_build_runs_on_pull_requests_and_main_but_only_for_demo_changes() -> None:
    triggers = _triggers(_workflow())
    assert triggers["push"]["branches"] == ["main"]
    assert "pull_request" in triggers and "workflow_dispatch" in triggers
    for event in ("push", "pull_request"):
        assert "demo/**" in triggers[event]["paths"]


def test_deploy_only_happens_from_main_with_the_least_privilege_needed() -> None:
    doc = _workflow()
    assert doc["permissions"] == {"contents": "read"}  # the default for every job
    deploy = doc["jobs"]["deploy"]
    assert deploy["needs"] == "build"
    assert "refs/heads/main" in deploy["if"] and "pull_request" in deploy["if"]
    assert deploy["permissions"] == {"pages": "write", "id-token": "write"}
    assert deploy["environment"]["name"] == "github-pages"
    assert "permissions" not in doc["jobs"]["build"]  # the build job cannot write anything


def test_pull_requests_build_but_never_upload_or_deploy() -> None:
    steps = _steps(_workflow()["jobs"]["build"])
    for step in steps:
        uses = str(step.get("uses", ""))
        if "upload-pages-artifact" in uses or "configure-pages" in uses:
            assert "pull_request" in step["if"]


def test_build_job_checks_the_demo_end_to_end() -> None:
    runs = [s["run"] for s in _steps(_workflow()["jobs"]["build"]) if "run" in s]
    for expected in (
        "npm ci",
        "npm audit --omit=dev",
        "npm run typecheck",
        "npm test",
        "npm run build",
        "npm run check:dist",
    ):
        assert expected in runs


def test_actions_are_pinned_to_major_versions_and_no_secrets_are_used() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    uses = re.findall(r"uses:\s*(\S+)", text)
    assert uses and all(re.search(r"@v\d+$", u) for u in uses)
    assert "secrets." not in text


def test_node_version_satisfies_the_demos_engine_range() -> None:
    package = json.loads((REPO / "demo/package.json").read_text(encoding="utf-8"))
    minimum = int(re.search(r">=(\d+)", package["engines"]["node"]).group(1))  # type: ignore[union-attr]
    node = int(str(_steps(_workflow()["jobs"]["build"])[1]["with"]["node-version"]))
    assert node >= minimum


def test_vite_base_path_matches_the_repository_name() -> None:
    studies = yaml.safe_load((REPO / "configs/demo_studies.yaml").read_text(encoding="utf-8"))
    repo_name = studies["repo_url"].rstrip("/").rsplit("/", 1)[-1]
    config = (REPO / "demo/vite.config.ts").read_text(encoding="utf-8")
    assert f'base: "/{repo_name}/"' in config
    check = (REPO / "demo/scripts/check-dist.mjs").read_text(encoding="utf-8")
    assert f'const base = "/{repo_name}/"' in check


def test_demo_build_artifacts_and_dependencies_are_not_committed() -> None:
    ignore = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "node_modules/" in ignore and "dist/" in ignore
