# Barrido de secretos — paquete GitHub fase 0 (11-nov-2026, America/Bogota)

Herramientas: gitleaks 8.21.2 (`detect --no-git`) y `rg` de patrones (BEGIN PRIVATE KEY, api_key, Bearer, ghp_, github_pat_, RUNPOD_API, N8N_API, CLAVES, password=). **Ningún valor secreto se copia aquí.**

## Resultado

- **No se encontraron claves reales** en el paquete destinado a GitHub (repo público).
- gitleaks reportó 38 hallazgos, todos **falsos positivos** clasificados así:
  - 20× campo `json_schema_api`: hash hex de 64 caracteres (checksum de esquema de prompt), no una API key.
  - 17× campo `capitulo` (19 caracteres, identificador de capítulo) en contratos de storyboard.
  - 1× campo `canal` en un prompt largo (`texto.txt`).
- `rg`:
  - Cero archivos con `-----BEGIN`, `PRIVATE KEY`, `api_key=`, `Bearer`, `N8N_API`, `password=`.
  - `ghp_` / `github_pat_` solo como **prefijos de 4 y 11 caracteres** en el CHANGELOG de un vendor (`camera_dsl`), no tokens.
  - `RUNPOD_API` aparece como **nombre de variable de entorno** en tres `.py` (`gpu_pod.py`, copia en el motor, `vigilante_gpu.py`).
  - `CLAVES` aparece como referencia de ruta en `paso00_resolver.py`.

## Archivos dejados fuera (duda o política)

- `cajas_taller/storyboard/vendor/camera_dsl/scripts/audit.py` — el copiador detectó texto tipo “PRIVATE KEY”; se dejó fuera.
- `cajas_taller/biblioteca_vrm/HairSample_Male.vrm` — binario de 18 MB, fuera de política.
- Directorios `secretos/` del motor y de las fábricas (claves reales; solo viven en el tarball de rollback del 213).
- `corridas/`, `tmp/`, `diagnosticos/`, `informes/`, `recibos_lotes/`, `jobs/`, `respaldos/` de cajas, `__pycache__/`, medios (`.blend`, `.bvh`, `.mp4`, `.png`, …).
- Configs: `gpu.ssh_key` y `gpu.runpod_env` se sustituyeron por `${SECRET_FILE_PATH}`. Campos cuyo nombre contiene “token” (p. ej. conteos `tokens_entrada` de ledgers) se redactaron por exceso de celo; no eran secretos.

El tarball de rollback en `/opt/myia-respaldos/20261111_fase0/` **sí** incluye `secretos/` y los JSON crudos de n8n (ids de credenciales, no la clave SSH). Ese tarball no se sube.
