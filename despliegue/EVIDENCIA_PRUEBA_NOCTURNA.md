# Evidencia para corrección (t598) — prueba directa PR7 en VPS aislado

Si la corrida sale **BLOQUEADA**, **negativa** o **timeout**, enviar al agente (sin credenciales ni datos sensibles del cliente):

1. `preflight_constructor.json` y `preflight_blend.json` (si existen).
2. `constructor.log`, `progreso_worker.json`, `worker_resultado.json` o equivalente.
3. `auditoria_4g/camara_v2.json` (tomas con `estado`, `motivos`, `muestras_malas`, `busqueda_matematica`).
4. Tiempos: inicio/fin, `MOTOR_CAMARA_*` si aplica, conteos `frame_set` de smoke si corrieron `probar_directa_vs_busqueda.py`.
5. SHA del paquete instalado (`manifiesto_paquete.json` → `git_commit`) y ruta `VPS_EXP`.
6. Comando exacto y rutas `PAQUETE` / `NUCLEO` / `SAL` (sin copiar JSON de entrada completa si es confidencial: basta `resumen` + hashes de assets).

**No** pedir relajar revisión, **no** tocar storyboard, **no** hardcodear canal. Correcciones solo en rama `cursor/camara-directa-sb-exp-43f7`.
