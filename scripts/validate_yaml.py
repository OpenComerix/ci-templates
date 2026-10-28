from pathlib import Path

from ci_model import load, validate_template


yaml_files = (sorted(Path(".").glob("*.yml")) + sorted(Path("templates").glob("*.yml"))
              + sorted(Path(".github").rglob("*.yml")))
if not yaml_files:
    raise SystemExit("No se encontraron archivos YAML para validar.")

for yaml_file in yaml_files:
    load(yaml_file)
    print(f"{yaml_file}: YAML válido")

count = validate_template(load("templates/node-pnpm.yml"))
print(f"Contrato Node/pnpm válido: {count} jobs públicos, un escritor y fallback congelado")

action = load(".github/actions/node-pnpm/action.yml")
assert action["runs"]["using"] == "composite"
steps = action["runs"]["steps"]
install = next(step for step in steps if step.get("name") == "Install frozen dependencies")
assert "--frozen-lockfile" in install["run"]
assert "--ignore-scripts" in install["run"]
assert "exit 1" in install["run"]
assert all("@" in step["uses"] and len(step["uses"].split("@")[-1]) == 40
           for step in steps if "uses" in step)
print("GitHub composite válido: instalación congelada y acciones fijadas por SHA")
