from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from ci_model import load, merge, resolve, validate_template, validate_artifact_edges

ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.template = load(ROOT / "templates/node-pnpm.yml")

    def test_current_contract(self):
        self.assertEqual(validate_template(self.template), 6)

    def test_consumer_overrides_keep_cache_and_merge_variables(self):
        consumer = {"test:unit": {"script": ["pnpm test:cov"]},
                    "test:e2e": {"variables": {"BUILD_STARTUP_TLS": "true"}}}
        resolved = merge(self.template, consumer)
        unit = resolve(resolved, "test:unit")
        self.assertEqual(unit["script"], ["pnpm test:cov"])
        self.assertEqual(unit["variables"]["PNPM_CACHE_POLICY"], "pull")
        e2e = resolve(resolved, "test:e2e")
        self.assertEqual(e2e["variables"]["BUILD_STARTUP_TLS"], "true")
        self.assertEqual(e2e["variables"]["PNPM_VERSION"], "12.4.2")

    def test_cache_miss_does_not_force_offline_or_remove_frozen_install(self):
        for name in ["quality:format", "test:unit", "build:application"]:
            commands = resolve(self.template, name)["before_script"]
            self.assertEqual(commands[-1], "pnpm install --frozen-lockfile --prefer-offline")
            self.assertFalse(any("--offline" in x or "|| true" in x for x in commands))

    def test_retired_gate_second_writer_or_artifact_drift_are_rejected(self):
        cases = [lambda x: x.pop("test:unit"),
                 lambda x: x["quality:lint"].update({"variables": {"PNPM_CACHE_POLICY": "pull-push"}}),
                 lambda x: x["build:application"]["artifacts"].update({"paths": ["other/"]}),
                 lambda x: x["test:e2e"].update({"rules": [{"when": "never"}]}),
                 lambda x: x[".opencomerix:node-pnpm"].update({"before_script": ["pnpm install"]})]
        for mutate in cases:
            changed = deepcopy(self.template)
            mutate(changed)
            with self.assertRaises((AssertionError, ValueError)):
                validate_template(changed)

    def test_duplicate_yaml_keys_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="opencomerix-ci-yaml-") as folder:
            file = Path(folder) / "duplicate.yml"
            file.write_text("job:\n  script: first\n  script: second\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicada"):
                load(file)

    def test_artifact_consumers_require_an_existing_earlier_producer(self):
        candidate = merge(self.template, {"stages": ["validate", "build", "test"],
            "test:architecture": {"extends": ".opencomerix:node-pnpm", "stage": "test",
                                  "dependencies": ["build:application"], "script": ["pnpm architecture:artifacts"]}})
        validate_artifact_edges(candidate)
        for mutate in [lambda x: x["test:architecture"].pop("dependencies"),
                       lambda x: x["test:architecture"].update({"dependencies": ["missing"]}),
                       lambda x: x["test:architecture"].update({"needs": ["build:application"]}),
                       lambda x: x.update({"stages": ["validate", "test", "build"]}),
                       lambda x: x["build:application"].pop("artifacts")]:
            changed = deepcopy(candidate)
            mutate(changed)
            with self.assertRaises(AssertionError):
                validate_artifact_edges(changed)

    def test_missing_parent_and_cycles_are_rejected(self):
        with self.assertRaises(ValueError):
            resolve({"job": {"extends": "absent"}}, "job")
        with self.assertRaisesRegex(ValueError, "Ciclo"):
            resolve({"a": {"extends": "b"}, "b": {"extends": "a"}}, "a")


if __name__ == "__main__":
    unittest.main()
