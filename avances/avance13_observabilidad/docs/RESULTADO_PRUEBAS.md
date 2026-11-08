# Resultado pruebas 2026-11-08 (Bogotá)

## Observabilidad (hijo simulado; padre/box ya 18/18)
Suite `test_observabilidad_supervisor.py`: 18 tests. No repetida aquí como campaña. `test_14` revalidó el aplicador nuevo: OK. Supervisor parche SHA `6f942bdc739ff8d7c721edabbe2c08849d03f29c923961ce544860689c368289` intacto.

## Aplicador atómico (esta corrección)
```
python3 -B avances/avance13_observabilidad/pruebas/test_aplicar_observabilidad.py
Ran 11 tests in 0.227s
OK
```
Cobertura: hash/idempotencia/permisos, ajeno no forzar, symlink, cambio tras respaldo, rename/write fallo con original intacto, cambio pre-replace, lock cooperativo, revertir, CLI sin main de supervisor.

## No ejecutado
Main de producción, render, constructor real, GPU, APIs, n8n, VPS write, merge, quitar `.off`.
