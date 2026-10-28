from pathlib import Path

from ci_model import load, validate_template


yaml_files = sorted(Path(".").glob("*.yml")) + sorted(Path("templates").glob("*.yml"))
if not yaml_files:
    raise SystemExit("No se encontraron archivos YAML para validar.")

for yaml_file in yaml_files:
    load(yaml_file)
    print(f"{yaml_file}: YAML válido")

count = validate_template(load("templates/node-pnpm.yml"))
print(f"Contrato Node/pnpm válido: {count} jobs públicos, un escritor y fallback congelado")
