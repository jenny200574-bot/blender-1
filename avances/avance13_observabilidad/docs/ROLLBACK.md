# Reversión (no autoaplicada)

El aplicador copia el original a `operaciones/respaldos_observabilidad/supervisor_oro_constructor.py.<stamp>.orig` y deja `observabilidad_cierre.off`.

## Apagar sin revertir
Dejar o recrear `operaciones/observabilidad_cierre.off`. El script usa el `run()`/`save()` originales.

## Revertir bytes
```bash
ORIG=129187406f4381fb7740e561e7835336211590e5aaf5ef2b92b1559ea5e87c85
python3 -c "import hashlib,pathlib,sys; p=pathlib.Path(sys.argv[1]); print(hashlib.sha256(p.read_bytes()).hexdigest())" \
  operaciones/respaldos_observabilidad/supervisor_oro_constructor.py.<stamp>.orig
# debe ser $ORIG
cp -a operaciones/respaldos_observabilidad/supervisor_oro_constructor.py.<stamp>.orig \
     operaciones/supervisor_oro_constructor.py
```

Copia de fábrica (repo/paquete): `original/artefactos/supervisor_oro_constructor.py` (mismo SHA).

No borrar `secuencia_estado.json` histórico. No relanzar oro/constructor como parte del rollback.
