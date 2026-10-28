import copy
import sys
import unittest
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from github_model import load, UniqueLoader, validate_action

class SharedActionTests(unittest.TestCase):
    def setUp(self):
        self.action = load(Path(__file__).resolve().parents[1] / ".github/actions/node-pnpm/action.yml")

    def test_shared_action(self):
        self.assertEqual(validate_action(self.action), 4)

    def test_duplicate_yaml_keys(self):
        with self.assertRaisesRegex(ValueError, "Duplicate YAML key"):
            yaml.load("runs:\n  using: composite\n  using: node24\n", Loader=UniqueLoader)

    def test_drift_is_rejected(self):
        mutations = [
            lambda a: a["runs"]["steps"].pop(),
            lambda a: a["runs"]["steps"][0].update(run='echo latest'),
            lambda a: a["runs"]["steps"][1].update(uses='actions/cache/restore@main'),
            lambda a: a["runs"]["steps"][1]["with"].update(path='node_modules/'),
            lambda a: a["runs"]["steps"][1]["with"].update(key='shared'),
            lambda a: a["runs"]["steps"][2].update(run='corepack prepare pnpm@latest --activate'),
            lambda a: a["runs"]["steps"][3].update(run='pnpm install --no-frozen-lockfile'),
            lambda a: a["runs"]["steps"][3].update(run=a["runs"]["steps"][3]["run"].replace('exit 1', 'exit 0')),
            lambda a: a["runs"]["steps"][3].update({'continue-on-error': True}),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                action = copy.deepcopy(self.action)
                mutate(action)
                with self.assertRaises(AssertionError):
                    validate_action(action)

if __name__ == "__main__":
    unittest.main()
