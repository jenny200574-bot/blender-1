# Resultado pruebas 2026-11-08 (Bogotá)

## Observabilidad (hijo simulado, CPU, sin VPS)
```
python3 -B avances/avance13_observabilidad/pruebas/test_observabilidad_supervisor.py
Ran 18 tests in 0.505s
OK
```
Cobertura: éxito, stderr/traceback, exit≠0, SIGTERM, hijo silencioso, boot distinto, mismo boot vivo/muerto, evidencia histórica, fallo de registro sin éxito falso, `.off`, script completo simulado, guarda física, aplicar/hash ajeno, recuperar CLI, contratos, concurrentes.

## Motor canon (`cd motor && for t in pruebas/test_*.py`)
Árbol `motor/` y `motor_candidato_bvh08/` **sin cambios de fuente** (orquestador blob git idéntico a HEAD `4a8165f`). Fallos observados: entorno (p. ej. `PIL` ausente en `test_t317.test12`), no introducidos por este paquete. No se corrió oro 23/23 ni Blender.

## No ejecutado
Render, constructor real, GPU, APIs, n8n, SSH, reboot, merge a main, despliegue VPS.
