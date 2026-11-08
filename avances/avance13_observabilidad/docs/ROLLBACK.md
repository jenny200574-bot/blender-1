# Reversión (no autoaplicada)

El aplicador escribe el original a `operaciones/respaldos_observabilidad/supervisor_oro_constructor.py.<stamp>.orig` (temporal + `os.replace`) y deja `observabilidad_cierre.off`.

## Apagar observabilidad sin revertir bytes
Dejar o recrear `operaciones/observabilidad_cierre.off`. Eso **no** impide que el `main` de producción lance oro/constructor. No usar el main como prueba.

## Revertir bytes (mismo aplicador; no `cp` sobre el destino)
```bash
ORIG=129187406f4381fb7740e561e7835336211590e5aaf5ef2b92b1559ea5e87c85
python3 paquete_operativo/aplicar_observabilidad.py \
  --destino operaciones/supervisor_oro_constructor.py \
  --revertir --respaldo operaciones/respaldos_observabilidad/supervisor_oro_constructor.py.<stamp>.orig
```
El respaldo debe hashear `$ORIG`. Si el destino ya no es original ni parche, el aplicador no fuerza.

Copia de fábrica: `original/artefactos/supervisor_oro_constructor.py` (mismo SHA).

No borrar `secuencia_estado.json` histórico. No relanzar oro/constructor como parte del rollback.
