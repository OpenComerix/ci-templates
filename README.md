# Plantillas CI de OpenComerix

Plantillas versionadas de GitLab CI para los repositorios de OpenComerix. El primer contrato cubre proyectos TypeScript con Node.js `24.21.0` y pnpm `12.4.2`.

## Uso desde un proyecto

```yaml
include:
  - project: opencomerix/ci-templates
    ref: v1.0.0
    file: /templates/node-pnpm.yml
```

Los consumidores deben fijar un tag, nunca `main`, para que un cambio central no altere pipelines existentes sin revisión.

## Contrato de scripts

El proyecto consumidor declara estos scripts en `package.json`:

- `format:check`: comprueba formato sin modificar archivos;
- `lint`: ejecuta el análisis estático;
- `typecheck`: comprueba tipos sin generar artefactos;
- `test:unit`: ejecuta pruebas unitarias una sola vez;
- `build`: genera el artefacto de producción en `dist/`.

La plantilla instala con `pnpm install --frozen-lockfile`, por lo que cada repositorio debe versionar `pnpm-lock.yaml` y declarar `"packageManager": "pnpm@12.4.2"`.

## Jobs incluidos

| Etapa | Job |
| --- | --- |
| `validate` | `quality:format`, `quality:lint`, `quality:typecheck` |
| `test` | `test:unit` |
| `build` | `build:application` |

Las pruebas de integración, contratos, seguridad, publicación y despliegue se agregan en cada tipo de proyecto cuando exista su infraestructura correspondiente.

## Versionado

- Los cambios compatibles se publican con un nuevo tag menor.
- Los cambios que exijan modificar scripts o comportamiento de consumidores crean una versión principal nueva.
- Los proyectos actualizan el tag mediante merge request y validan su pipeline antes de adoptar la versión.
