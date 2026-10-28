"""Resolve this candidate against the explicit launcher inventory, without network."""
import argparse
import json
from pathlib import Path
import subprocess
import yaml

from ci_model import UniqueLoader, load, merge, resolve, validate_artifact_edges


def published(root, file, ref="HEAD"):
    return subprocess.check_output(["git", "-C", str(root), "show", ref + ":" + file], text=True, encoding="utf-8")


def public(document):
    return [name for name, value in document.items() if not name.startswith(".") and isinstance(value, dict) and "script" in value]


def check_consumer(template, old_template, root, base_ref="HEAD"):
    current = load(root / ".gitlab-ci.yml")
    previous = yaml.load(published(root, ".gitlab-ci.yml", base_ref), Loader=UniqueLoader)
    assert current["include"] == [{"project": "opencomerix/ci-templates", "ref": "v1.2.0", "file": "/templates/node-pnpm.yml"}]
    old = merge(old_template, previous)
    new = merge(template, current)
    assert new["stages"] == ["validate", "build", "test"]
    validate_artifact_edges(new)
    name = root.name
    retired = {"frontend_quality"} if name == "web-pos" else set()
    assert set(public(old)) - set(public(new)) == retired
    assert not set(public(new)) - set(public(old)), "No new runtime jobs"
    for job_name in set(public(old)) - retired:
        before, after = resolve(old, job_name), resolve(new, job_name)
        for field in ["image", "stage", "services", "rules", "artifacts", "needs", "allow_failure"]:
            assert before.get(field) == after.get(field), f"{name}/{job_name}/{field} changed"
        expected = before["script"][:]
        if job_name == "test:architecture":
            expected.remove("pnpm build")
            assert after["dependencies"] == ["build:application"]
        if name == "gateway-bff" and job_name == "validate:production-artifacts":
            expected = ["pnpm architecture:artifacts"]
            assert after["dependencies"] == ["build:application"]
            assert after["before_script"][-1] == "pnpm install --frozen-lockfile --prefer-offline"
        if (name, job_name) in (("web-pos", "frontend_playwright"), ("identity-tenancy", "test:e2e")):
            expected = ["pnpm test:e2e:ci" if x == "pnpm test:e2e" else x for x in expected]
            assert after["dependencies"] == ["build:application"]
        if name == "sales-pos" and job_name == "test:process-authority-runtime":
            expected = ["pnpm test:process-authority-runtime:ci"]
            assert after["dependencies"] == ["build:application"]
        assert expected == after["script"], f"{name}/{job_name}/script changed"
        expected_preparation = [command.replace("pnpm install --frozen-lockfile", "pnpm install --frozen-lockfile --prefer-offline")
                                for command in before.get("before_script", [])]
        if name == "catalog-pricing" and job_name in ("test:integration", "test:e2e"):
            install = expected_preparation.index("pnpm install --frozen-lockfile --prefer-offline")
            expected_preparation.insert(install, 'pnpm config set store-dir "${PNPM_STORE_DIR}"')
        if name == "gateway-bff" and job_name == "validate:production-artifacts":
            expected_preparation = resolve(template, ".opencomerix:node-pnpm")["before_script"]
        assert expected_preparation == after.get("before_script", []), f"{name}/{job_name}/preparation changed"
        for variable, value in before.get("variables", {}).items():
            assert after["variables"].get(variable) == value, f"{name}/{job_name}/{variable} changed"
        assert not (after.get("needs") is not None and after.get("dependencies") is not None), "Do not mix needs/dependencies"
    if name == "web-pos":
        kept = {command for job in public(new) for command in resolve(new, job)["script"]}
        for command in previous["frontend_quality"]["script"]:
            assert command in kept, "Retired PWA control: " + command
    pkg = json.loads((root / "package.json").read_text(encoding="utf-8"))
    before_pkg = json.loads(published(root, "package.json", base_ref))
    before_scripts, scripts = before_pkg.pop("scripts"), pkg.pop("scripts")
    assert before_pkg == pkg, "Dependencies or other package fields changed"
    assert all(scripts[key] == value for key, value in before_scripts.items()), "Local scripts changed"
    aliases = {"web-pos": "test:e2e", "identity-tenancy": "test:e2e", "sales-pos": "test:process-authority-runtime"}
    extra = set(scripts) - set(before_scripts)
    if name in aliases:
        script = aliases[name]
        assert extra == {script + ":ci"}
        assert before_scripts[script] == "pnpm build && " + scripts[script + ":ci"], "CI alias changes the test"
    else:
        assert not extra
    assert scripts["build"] in ("nest build", "ng build"), "Unreviewed build preparation"
    assert resolve(new, "build:application")["artifacts"]["paths"] == ["dist/"]
    return {"service": name, "jobs_before": len(public(old)), "jobs_after": len(public(new)), "writer": "quality:format"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--launcher-root", type=Path, required=True)
    parser.add_argument("--base-refs", type=Path, help="JSON mapping repository name to the immutable pre-edit SHA; defaults to local HEAD")
    args = parser.parse_args()
    root = args.launcher_root.resolve()
    ci = root / "shared/ci-templates"
    refs = json.loads(args.base_refs.read_text(encoding="utf-8")) if args.base_refs else {}
    if args.base_refs:
        import re
        assert isinstance(refs, dict) and all(isinstance(value, str) and re.fullmatch("[a-f0-9]{40}", value) for value in refs.values())
    template = load(ci / "templates/node-pnpm.yml")
    old_template = yaml.load(published(ci, "templates/node-pnpm.yml", refs.get("ci-templates", "HEAD")), Loader=UniqueLoader)
    inventory = json.loads((root / "launcher.repositories.json").read_text(encoding="utf-8"))
    apps = [row for row in inventory["repositories"] if row["path"].startswith(("services/", "frontend/"))]
    assert len(apps) == 13
    if args.base_refs:
        assert set(refs) == {"ci-templates", *(row["name"] for row in apps)}, "Incomplete explicit baselines"
    results = [check_consumer(template, old_template, root / row["path"], refs.get(row["name"], "HEAD")) for row in apps]
    print(json.dumps({"consumers": results, "remote_ci_verified": False}, separators=(",", ":")))


if __name__ == "__main__":
    main()
