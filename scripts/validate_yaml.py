from pathlib import Path

from github_model import load, validate_action


yaml_files = sorted(Path(".github").rglob("*.yml"))
if not yaml_files:
    raise SystemExit("No se encontraron archivos YAML para validar.")

for yaml_file in yaml_files:
    load(yaml_file)
    print(f"{yaml_file}: YAML válido")

count = validate_action(load(".github/actions/node-pnpm/action.yml"))
print(f"GitHub composite válido: {count} pasos, herramientas fijadas e instalación congelada")
