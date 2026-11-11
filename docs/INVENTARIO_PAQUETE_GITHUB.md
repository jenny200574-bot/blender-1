# Inventario del paquete a subir (rama fase0-motor-cine-v1-20261111)

Se **añade** al repo existente, sin borrar `motor/`, `avances/`, `escenas/` ni el resto del corte T317/avance08.

## Incluido

- `motor_cine_v1/` — código de `/opt/myia-motor-unificado/v1_20261110` (incluye `motor/blender/vuelo_alas.py`, `motor/m3_router.py`, `motor/assets/indice_clips.json`, `config_motor.json` con rutas de clave en placeholder).
- `fabricas/` — código y config redactada, constructores, scripts, assets de formas/recetas. Sin `secretos/`, informes, jobs, tmp ni recibos.
- `cajas_taller/` — prompts_01, cubo01, scripts del taller, FIJOS_TALLER, storyboard (sin vendor audit.py ni .vrm).
- `staging_argon/` — `esq_argon.py`, `poses_argon.py`, `recetas_argon.py`, prompts y esquemas del 9-nov-2026.
- `docs/` — PLAN_MOTOR_AUTONOMO, VALIDACION_BLOQUEO_MOTOR, ANALISIS_BIBLIOTECAS_FABRICAS_HISTORIAL, RECORRIDO_PRODUCCION, ROLLBACK_FASE0, TRASPASO_INMI (actualizado), SECRET_SCAN_FASE0, este inventario.
- `n8n/fase0_20261111/` — exportes sanitizados de `debwaH9svFMoTnOf` (activo, 594 nodos) y referencia `d2Bwmk2j4ijX28eK` (inactiva). Sin credenciales.
- `AGENTS.md` y `.gitignore` actualizados.

## Excluido (además de lo ya listado en el barrido)

- Binarios y corridas del motor (1,7 G de `corridas/`).
- Biblioteca 3D (personajes y .blend): se respaldó completa en el 213, no va al repo público (política del .gitignore: nada de `.blend` masivo; “small sample assets only”).
- JSON crudo de n8n (solo en el 213).
