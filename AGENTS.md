# AGENTS.md — instrucciones para cualquier agente de Cursor

1. **Lee primero `docs/TRASPASO_INMI.md`.** Ahí están las reglas de seguridad, el estado y cómo seguir. Después lee `README.md`.
2. **No tienes acceso al VPS.** Trabajas solo en el código y las pruebas de este repositorio, sin red ni gasto. Cualquier acción en el VPS (`/opt/myia-motor-v9/`), en n8n (workflow `debwaH9svFMoTnOf`), en Vertex/Argon o en RunPod/GPU la hace Ricardo o Inmi. Entrega esos pasos como instrucciones o scripts listos, nunca los ejecutes por tu cuenta.
3. Antes de entregar: `cd motor && for t in pruebas/test_*.py; do python3 -B "$t"; done` debe pasar. La regresión oro (23/23, tolerancias sin cambiar) se corre en el VPS con Blender; si tu cambio la puede afectar, dilo.
4. Nunca subas credenciales, `.env`, claves, `.blend`, renders ni videos. Las rutas sensibles van como `${VERTEX_SA_FILE}`, `${GCP_PROJECT_ID}`, `${VPS_HOST}`.
5. No inventes valores (física, medidas, 2B): si faltan, el motor debe responder BLOQUEADO con la lista de faltantes.
6. Informes cortos, en español, en viñetas.
