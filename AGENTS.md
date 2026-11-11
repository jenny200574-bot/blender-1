# AGENTS.md — instrucciones para cualquier agente de Cursor

## Actualización Fase 0 — 11 de noviembre de 2026 (America/Bogota)

Esta sección prevalece cuando haya conflicto con el corte histórico de más abajo. El código **nuevo** del motor en producción (cine_v1) se añade en este repo **sin borrar** `motor/` ni `avances/` (ese es el corte T317 / avance08, no se toca).

1. **Lee primero `docs/TRASPASO_INMI.md` y `docs/PLAN_MOTOR_AUTONOMO.md`.** Luego este archivo y `README.md`.
2. **No tienes acceso al VPS.** Trabajas solo en el código y las pruebas de este repositorio, sin red ni gasto. Cualquier acción en el 213, en n8n, en Argon o en RunPod/GPU la hace Ricardo o Inmi. Entrega parches, tests e instrucciones; no los ejecutes en el servidor.
3. **Motor vivo que hay que mejorar:** `motor_cine_v1/` (copia de `/opt/myia-motor-unificado/v1_20261110`, sin corridas, secretos ni binarios). Fábricas: `fabricas/`. Prompts y cubos 01: `cajas_taller/` (sobre todo `prompts_01/`, `cubo01_accion.py`, `eventos_o112.py`). Scripts Argon de staging a reutilizar: `staging_argon/` (`esq_argon.py`, `poses_argon.py`, `recetas_argon.py` y prompts). Documentación de auditoría: `docs/PLAN_MOTOR_AUTONOMO.md`, `docs/VALIDACION_BLOQUEO_MOTOR.md`, `docs/ANALISIS_BIBLIOTECAS_FABRICAS_HISTORIAL.md`, `docs/RECORRIDO_PRODUCCION.md`, `docs/ROLLBACK_FASE0.md`.
4. **Flujo n8n de trabajo:** solo `debwaH9svFMoTnOf`. No crear copias ni versiones nuevas del workflow. Nada nuevo se deja apagado. Exportes sanitizados (sin credenciales) en `n8n/fase0_20261111/`.
5. **Prohibido tocar:** T317, `24_TRASPASO`, `v9_universal_calidad_20261106`, el host `217.76.52.53`, el pod/volumen Star `32soe7oh2f1gtf`. Nunca borrar personajes, versiones de biblioteca, fábricas ni historia de este repo: solo añadir versiones o archivos nuevos.
6. **Decisiones de Ricardo (11-nov-2026):** si falta la escena anterior, heredar el último estado y marcar `gap:true`. Ricardo aprueba a mano todo lo que cree Argon. La Prueba B usará otro guion del canal Guardianes. El webhook de n8n no se cambia hasta que él decida. El costo no es la prioridad frente a que el modelo funcione, pero toda llamada lleva ledger y tope de lote.
7. **Rama de este corte:** `fase0-motor-cine-v1-20261111`. No hagas force-push a `main`. No borres ramas.
8. **Secretos:** nunca subas `.env`, `secretos/`, claves, tokens, `runpod.env`, `argon.env`, cuentas de servicio, `.blend` masivos ni videos. En configs, las rutas de clave van como `${SECRET_FILE_PATH}`. Si un archivo te genera duda, déjalo fuera y lístalo.
9. **Fases siguientes (plan aprobado 0 y 1; esta rama es la 0):** la fase 1 repara la cadena de `debwaH9svFMoTnOf` (PROM·FAIL, orden 01→SB→MU, falso «listo ✔», hardcodes, manifiestos SB, FAB · encolar, bucle). Luego bloqueo (fase 2), correr/volar (fase 3), bibliotecas + Argon autónomo (fase 4), historial (fase 5), adaptabilidad (fase 6), barrido de canal (fase 7) y prueba cero a video (fase 8).
10. Informes cortos, en español, en viñetas. Nunca inventes medidas: si falta algo, BLOQUEADO con la lista de faltantes.

---

# Corte histórico (conservar; describe el paquete T317 / avance08 en `motor/`)

# AGENTS.md — instrucciones para cualquier agente de Cursor

1. **Lee primero `docs/TRASPASO_INMI.md`.** Ahí están las reglas de seguridad, el estado y cómo seguir. Después lee `README.md`.
2. **No tienes acceso al VPS.** Trabajas solo en el código y las pruebas de este repositorio, sin red ni gasto. Cualquier acción en el VPS (`/opt/myia-motor-v9/`), en n8n (workflow `debwaH9svFMoTnOf`), en Vertex/Argon o en RunPod/GPU la hace Ricardo o Inmi. Entrega esos pasos como instrucciones o scripts listos, nunca los ejecutes por tu cuenta.
3. Antes de entregar: `cd motor && for t in pruebas/test_*.py; do python3 -B "$t"; done` debe pasar. La regresión oro (23/23, tolerancias sin cambiar) se corre en el VPS con Blender; si tu cambio la puede afectar, dilo.
4. Nunca subas credenciales, `.env`, claves, `.blend`, renders ni videos. Las rutas sensibles van como `${VERTEX_SA_FILE}`, `${GCP_PROJECT_ID}`, `${VPS_HOST}`.
5. No inventes valores (física, medidas, 2B): si faltan, el motor debe responder BLOQUEADO con la lista de faltantes.
6. Informes cortos, en español, en viñetas.
