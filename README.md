# CI compartida de OpenComerix

Automatización compartida en GitHub Actions para TypeScript con Node.js `24.21.0` y pnpm `12.4.2`.

## Uso

Los consumidores usan `.github/actions/node-pnpm/action.yml` fijada por SHA completo publicado y con CI verificada. El repositorio privado comparte la acción únicamente con otros repositorios de `opencomerix`.

La acción verifica Node, prepara la versión fijada de pnpm, restaura `.pnpm-store/` y `.corepack-cache/`, e instala siempre con lockfile congelado. `install-mode` admite `normal` o `ignore-scripts`; cualquier otro valor falla. Una caché vacía permite descargar dependencias, sin ocultar errores ni recurrir a una instalación sin congelar.

Cada workflow consumidor conserva sus comandos de calidad, pruebas y build, sus servicios, artefactos y orden de ejecución. El job propietario guarda la caché mediante los outputs `cache-key` y `cache-hit`; la acción compartida solo la restaura. No se cachean `node_modules`, builds ni resultados de pruebas.

## Validación y evolución

Con Python `3.13.7` y PyYAML `6.0.2`, ejecutar `python scripts/validate_yaml.py` y `python -m unittest discover -s test -p 'test_*.py'`. Se rechazan claves YAML duplicadas, versiones móviles, instalaciones sin congelar, rutas de caché ajenas y errores ignorados. El workflow propio ejecuta estos controles; la CI remota por SHA/ref exactos acredita la publicación.

Los consumidores adoptan cada cambio mediante revisión de su SHA y CI. Los tags publicados y las antiguas plantillas GitLab se conservan en la historia Git disponible en GitHub; ya no hay configuración GitLab activa que mantener. GitLab quedó archivado como evidencia histórica.
