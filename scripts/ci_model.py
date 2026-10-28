"""Local model of the GitLab features used here; not a GitLab CI Lint replacement."""
from copy import deepcopy
from pathlib import Path

import yaml


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f"Clave YAML duplicada: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def load(path):
    document = yaml.load(Path(path).read_text(encoding="utf-8"), Loader=UniqueLoader)
    if not isinstance(document, dict):
        raise ValueError(f"{path}: la raíz debe ser un objeto YAML")
    return document


def merge(left, right):
    result = deepcopy(left)
    for key, value in right.items():
        if isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def resolve(document, name, stack=()):
    if name in stack:
        raise ValueError(f"Ciclo extends: {name}")
    job = document.get(name)
    if not isinstance(job, dict):
        raise ValueError(f"Job/parent desconocido: {name}")
    parents = job.get("extends", [])
    if isinstance(parents, str):
        parents = [parents]
    if not isinstance(parents, list) or not all(isinstance(x, str) for x in parents):
        raise ValueError(f"extends inválido: {name}")
    result = {}
    for parent in parents:
        result = merge(result, resolve(document, parent, (*stack, name)))
    result = merge(result, job)
    result.pop("extends", None)
    result["variables"] = merge(document.get("variables", {}), result.get("variables", {}))
    for key, value in document.get("default", {}).items():
        result.setdefault(key, deepcopy(value))
    return result


PUBLIC_JOBS = {"quality:format", "quality:lint", "quality:typecheck", "test:unit", "test:e2e", "build:application"}


def validate_artifact_edges(document):
    stages = document["stages"]
    jobs = {name: resolve(document, name) for name, value in document.items()
            if not name.startswith(".") and isinstance(value, dict) and "script" in value}
    for name, job in jobs.items():
        dependencies, needs = job.get("dependencies"), job.get("needs")
        assert not (dependencies is not None and needs is not None), f"Mixed needs/dependencies: {name}"
        for dependency in dependencies or []:
            assert dependency in jobs, f"Missing artifact producer: {name}/{dependency}"
            producer = jobs[dependency]
            assert stages.index(producer["stage"]) < stages.index(job["stage"]), f"Artifact stage: {name}"
            assert producer.get("artifacts", {}).get("paths"), f"Missing artifact paths: {dependency}"
        for need in needs or []:
            target = need if isinstance(need, str) else need["job"]
            assert target in jobs, f"Missing needs producer: {target}"
            assert stages.index(jobs[target]["stage"]) <= stages.index(job["stage"]), f"Needs stage: {name}"
        if "pnpm architecture:artifacts" in job["script"] and "pnpm build" not in job["script"]:
            assert dependencies == ["build:application"], f"Missing dist dependency: {name}"


def validate_template(document):
    missing = PUBLIC_JOBS.difference(document)
    if missing:
        raise ValueError(f"Faltan jobs requeridos: {sorted(missing)}")
    actual_jobs = {name for name, value in document.items() if not name.startswith(".")
                   and isinstance(value, dict) and "script" in value}
    assert actual_jobs == PUBLIC_JOBS, "Unexpected public jobs"
    expected_scripts = {"quality:format": ["pnpm format:check"], "quality:lint": ["pnpm lint"],
                        "quality:typecheck": ["pnpm typecheck"], "test:unit": ["pnpm test:unit"],
                        "test:e2e": ["pnpm test:e2e"], "build:application": ["pnpm build"]}
    writers = []
    for name in sorted(PUBLIC_JOBS):
        job = resolve(document, name)
        assert job["script"] == expected_scripts[name], f"Gate alterado: {name}"
        assert job["image"] == "node:24.21.0-bookworm-slim", "Node/image drift"
        assert job["variables"]["PNPM_VERSION"] == "12.4.2", "pnpm drift"
        assert job["before_script"] == ["corepack enable", 'corepack prepare "pnpm@${PNPM_VERSION}" --activate',
                                        'pnpm config set store-dir "${PNPM_STORE_DIR}"',
                                        "pnpm install --frozen-lockfile --prefer-offline"], "Install drift"
        assert job["cache"]["key"] == {"prefix": "node24.21.0-pnpm12.4.2-bookworm-v1", "files": ["pnpm-lock.yaml"]}
        assert job["cache"]["paths"] == [".pnpm-store/", ".corepack-cache/"]
        assert job["cache"]["policy"] == "$PNPM_CACHE_POLICY"
        policy = job["variables"]["PNPM_CACHE_POLICY"]
        assert policy in ("pull", "pull-push"), "Cache policy inválida"
        if policy == "pull-push":
            writers.append(name)
    assert writers == ["quality:format"], "Debe existir exactamente un escritor"
    assert document["test:e2e"]["rules"] == [{"exists": ["test/**/*.e2e-spec.ts"]}], "E2E selection drift"
    assert resolve(document, "build:application")["artifacts"]["paths"] == ["dist/"]
    assert resolve(document, "test:unit")["artifacts"]["paths"] == ["coverage/"]
    assert resolve(document, "test:unit")["dependencies"] == []
    assert resolve(document, "test:e2e")["dependencies"] == []
    return len(PUBLIC_JOBS)
