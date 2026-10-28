"""Validate the shared GitHub action and reject duplicate YAML keys."""
import re
from pathlib import Path
import yaml

class UniqueLoader(yaml.SafeLoader):
    pass

def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f"Duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result

UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)

def load(file):
    return yaml.load(Path(file).read_text(encoding="utf-8"), Loader=UniqueLoader)

def validate_action(action):
    assert action["runs"]["using"] == "composite"
    steps = action["runs"]["steps"]
    assert len(steps) == 4
    assert len({step["name"] for step in steps}) == len(steps)
    by_name = {step["name"]: step for step in steps}
    assert by_name["Verify Node"]["run"] == 'test "$(node --version)" = v24.21.0'
    cache = by_name["Restore dependency cache"]
    assert re.fullmatch(r"actions/cache/restore@[0-9a-f]{40}", cache["uses"])
    assert cache["id"] == "restore"
    assert cache["with"]["path"].split() == [".pnpm-store/", ".corepack-cache/"]
    assert cache["with"]["key"] == "node24.21.0-pnpm12.4.2-bookworm-v1-${{ hashFiles('pnpm-lock.yaml') }}"
    assert by_name["Prepare pinned pnpm"]["run"].splitlines() == [
        "corepack enable", "corepack prepare pnpm@12.4.2 --activate",
        'test "$(pnpm --version)" = 12.4.2', "pnpm config set store-dir .pnpm-store",
    ]
    install = by_name["Install frozen dependencies"]
    assert install["env"] == {"INSTALL_MODE": "${{ inputs.install-mode }}"}
    assert install["run"].splitlines() == [
        'case "$INSTALL_MODE" in',
        "  normal) pnpm install --frozen-lockfile --prefer-offline ;;",
        "  ignore-scripts) pnpm install --frozen-lockfile --ignore-scripts --prefer-offline ;;",
        "  *) echo 'Unknown installation mode' >&2; exit 1 ;;", "esac",
    ]
    assert action["inputs"]["install-mode"]["default"] == "normal"
    assert action["outputs"]["cache-key"]["value"] == "${{ steps.restore.outputs.cache-primary-key }}"
    assert action["outputs"]["cache-hit"]["value"] == "${{ steps.restore.outputs.cache-hit }}"
    for step in steps:
        if "run" in step:
            assert step["shell"] == "bash"
        assert "continue-on-error" not in step
    return len(steps)
