from pathlib import Path

import yaml


yaml_files = sorted(Path(".").glob("*.yml")) + sorted(Path("templates").glob("*.yml"))
if not yaml_files:
    raise SystemExit("No se encontraron archivos YAML para validar.")

for yaml_file in yaml_files:
    with yaml_file.open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)
    if not isinstance(document, dict):
        raise SystemExit(f"{yaml_file}: la raíz debe ser un objeto YAML.")
    print(f"{yaml_file}: YAML válido")

template = yaml.safe_load(Path("templates/node-pnpm.yml").read_text(encoding="utf-8"))
required_jobs = {
    "quality:format",
    "quality:lint",
    "quality:typecheck",
    "test:unit",
    "test:e2e",
    "build:application",
}
missing_jobs = sorted(required_jobs.difference(template))
if missing_jobs:
    raise SystemExit(f"Faltan jobs requeridos: {', '.join(missing_jobs)}")

print(f"Contrato Node/pnpm válido: {len(required_jobs)} jobs públicos")
