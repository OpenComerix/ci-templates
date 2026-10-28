# Plantillas CI de OpenComerix

Automatización compartida de OpenComerix en GitHub Actions, con plantillas GitLab históricas preservadas. Cubre proyectos TypeScript con Node.js `24.21.0` y pnpm `12.4.2`.

## GitHub Actions

`.github/actions/node-pnpm/action.yml` conserva las versiones fijadas, restaura solo las cachés de dependencias e instala siempre con lockfile congelado. Los consumidores fijan un SHA publicado completo; el escritor de caché sigue siendo el job propietario. Los workflows propios y consumidores conservan sus comandos, servicios y dependencias de artefactos. El acceso compartido del repositorio privado está limitado a otros repositorios del usuario `opencomerix`. La CI por SHA/ref exactos acredita cada publicación.

Las secciones siguientes documentan las plantillas GitLab preservadas, cuyos tags y bytes publicados no se modifican durante el traslado.

## Uso desde un proyecto

```yaml
include:
  - project: opencomerix/ci-templates
    ref: v1.2.0
    file: /templates/node-pnpm.yml
```

Los consumidores deben fijar un tag, nunca `main`, para que un cambio central no altere pipelines existentes sin revisión.

## Contrato de scripts

El proyecto consumidor declara estos scripts en `package.json`:

- `format:check`: comprueba formato sin modificar archivos;
- `lint`: ejecuta el análisis estático;
- `typecheck`: comprueba tipos sin generar artefactos;
- `test:unit`: ejecuta pruebas unitarias una sola vez;
- `test:e2e`: ejecuta las pruebas de extremo a extremo cuando el repositorio contiene `test/**/*.e2e-spec.ts`;
- `build`: genera el artefacto de producción en `dist/`.

La plantilla instala con `pnpm install --frozen-lockfile`, por lo que cada repositorio debe versionar `pnpm-lock.yaml` y declarar `"packageManager": "pnpm@12.4.2"`.

## Jobs incluidos

| Etapa | Job |
| --- | --- |
| `validate` | `quality:format`, `quality:lint`, `quality:typecheck` |
| `test` | `test:unit`, `test:e2e` cuando existen pruebas E2E |
| `build` | `build:application` |

Las pruebas que requieren infraestructura adicional, los contratos, la seguridad, la publicación y el despliegue se agregan en cada tipo de proyecto cuando exista su infraestructura correspondiente.

La versión `v1.1.0` incorpora el job E2E condicional. Debe publicarse el tag antes de integrar en los consumidores los cambios que actualizan su referencia.

## v1.2.0 — preparación y caché

Mantiene los seis jobs, comandos de calidad/pruebas/build y artefactos de v1.1.0. Se conserva la instalación congelada en cada job, con `--prefer-offline`: reutiliza paquetes disponibles y descarga los faltantes si la caché está vacía. No se cachean `node_modules`, builds ni resultados de pruebas.

La clave separa Node 24.21.0, pnpm 12.4.2 y Bookworm, además del hash del lockfile. El almacén pnpm y Corepack quedan dentro del proyecto. `quality:format` es el único escritor (`pull-push`); los demás jobs leen (`pull`). En una primera ejecución fría puede haber descargas paralelas antes de que termine el escritor; no se agrega una etapa de preparación ni se exige que la caché exista. GitLab conserva su separación entre proyectos y referencias protegidas.

El propio pipeline de plantillas reutiliza la caché de pip con Python/PyYAML fijados. `scripts/validate_yaml.py`, `scripts/ci_model.py` y `test/test_pipeline.py` verifican YAML sin claves duplicadas, herencia usada por estos consumidores, scripts preservados, escritor único y fallback congelado. El modelo local no sustituye CI Lint ni acredita el runner remoto.

La adopción de v1.2.0 requiere auditoría y verificación de la plantilla y su tag antes de integrar referencias consumidoras. Los tags publicados anteriores no se mueven.

Para reutilizar el build, los consumidores ordenan `validate → build → test`: producen `dist/` una vez antes de las comprobaciones que lo requieren y declaran `dependencies: [build:application]`. Unitarias y E2E basadas en fuentes no descargan artefactos ajenos por defecto. PWA/Identity/Sales conservan sus comandos locales que construyen y prueban; las entradas `:ci` ejecutan exactamente la misma prueba sobre el artefacto de ese pipeline. Una compilación temprana no acredita el pipeline completo: todas las pruebas siguen siendo obligatorias.

El job compuesto `frontend_quality` se retira conservando sus seis comandos en los jobs propietarios. Las comprobaciones de artefactos de backend reutilizan `dist/`. Los preparadores de dependencias externas de Catalog, sus compilaciones internas y las pruebas reales SQL/broker mantienen sus fuentes y configuración propias.

`python scripts/validate_consumers.py --launcher-root <launcher>` compone localmente la plantilla y las 13 CI explícitas del inventario, contrasta gates/preparación/servicios/variables/artefactos y las entradas `:ci` contra HEAD previo a editar. Para repetir la comparación después de crear commits, `--base-refs <json>` recibe un mapa completo de los 14 propietarios a sus SHA completos anteriores. Es un comparador de esta migración, fuera del pipeline propio; no consulta ni acredita el tag candidato remoto.

## Versionado

- Los cambios compatibles se publican con un nuevo tag menor.
- Los cambios que exijan modificar scripts o comportamiento de consumidores crean una versión principal nueva.
- Los proyectos actualizan el tag mediante merge request y validan su pipeline antes de adoptar la versión.
