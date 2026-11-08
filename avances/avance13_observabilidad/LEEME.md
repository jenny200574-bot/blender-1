# Observabilidad de cierre — paquete operativo aislado (avance13)

**Estado: PROPUESTO, no integrado al motor canon, no aplicado en VPS.**

## Integrado vs propuesto
- **No integrado:** `motor/`, `motor_candidato_bvh08/`, n8n, contratos ADN/cámara/física. El supervisor no existía en blender-1.
- **Propuesto:** copia parchada de `supervisor_oro_constructor.py` (fuente VPS bit-idéntica SHA256 `129187406f4381fb7740e561e7835336211590e5aaf5ef2b92b1559ea5e87c85`) en `paquete_operativo/`, con interruptor `.off` y aplicador que falla ante hash ajeno.

## Qué corrige (si se aplica y se quita `.off`)
- stderr/traceback originales con timestamps y flush/fsync.
- Estado terminal: exitcode o señal, run_id, boot_id, PID/starttime.
- RUNNING de otro boot → `INTERRUMPIDO_SIN_CIERRE` sin inventar causa.
- Mismo boot y PID vivo → no se marca interrupción (sin falso positivo).
- No relanza. No reintenta. No despliega.

## Qué NO arregla
- Causa individual de salida de PIDs 19177/19474 (sigue NO DETERMINADA).
- Logs históricos de 0 bytes (no se reconstruyen).
- SIGKILL de este supervisor (no puede escribir al morir; se reconoce al recuperar).
- TypeError histórico del buscador, cámara, OOM, timeout, oro 23/23, n8n.

## Uso (Ricardo / VPS; este agente no despliega)
Ver `docs/PROTOCOLO_APLICADOR.md`. El aplicador usa temporal+`os.replace` y falla ante hash ajeno; no hay otros deploys en esa ventana.
1. `--solo-verificar` (hash original `129187406f4381fb7740e561e7835336211590e5aaf5ef2b92b1559ea5e87c85`).
2. `python3 paquete_operativo/aplicar_observabilidad.py --destino …/supervisor_oro_constructor.py` (deja `.off`).
3. **No** quitar `.off` ni invocar el `main` de producción como prueba: `.off` apaga observabilidad, **no** la construcción.
4. Recuperar huérfano: `MYIA_SUPERVISOR_SOLO_RECUPERAR=1` (no relanza).

Motor UNIVERSAL: el parche no añade términos de canal.
