# Stage avance11 — mínimo, sin tocar avance10

Preparación. No es aprobación de producción. No se instaló nada en el VPS.

El candidato de avance10 mide 1.150.233.415 bytes. De eso, `evidencia` (820.153.811) y `archivo` (274.892.549) no los abre el oro, el preflight ni la reconstrucción como catálogo. Copiar el 1,15 GB no hace falta. `respaldos` (7.600.610) tampoco: no hay ninguna lectura de esa carpeta en `motor/`.

## Qué sí abre el código

Oro (`motor_unico.py --regresion`, no el wrapper de avance08):

- `motor_unico.py` y `motor/**/*.py` (el núcleo importa `heredado/`; `empaquetar` no corre en esta entrada).
- Los `assets` de `paquetes/regresion_orden_explicito/entrada_escena.json`: `entrada.json`, `asignacion.json`, `brazalete_tecnologico.json`, `catalogo.json`, `escenario_vivo.json`, `formulas.json`, `lanza_doble_punta.json`.
- Dentro de `entrada.json`, el núcleo abre `catalog`, `assignments`, el catálogo de fórmulas y las `formula` que terminan en `.json`.
- `formulas_v2.py` solo abre `archivo` si el catálogo trae esa clave. Este catálogo no la trae. La carpeta `archivo/` histórica del paquete no se copia.
- Referencia, solo lectura, copiada byte a byte a la stage: `/opt/myia-motor-v9/avance06_20261107/oro_av06/revisor_comparable.json`. Sale del script instalado `entrega/codigo/oro_final_bvh08.py`. No ejecutar ese script: escribe en avance08.
- Si existe `config/orden_determinista.off`, el núcleo aborta. No hay que crearlo. Si está en el origen, la stage lo copia y el oro se detiene igual que allí.

Preflight (`orquestador.ejecutar`, `solo_validar=True`) añade:

- `config/*.json` y `config/*.off` de primer nivel. `politica_ejecucion.json` se lee siempre. `argon_recetas.off`, si está, evita el ledger.
- `CONTRATO_ENTRADA.schema.json` lo lee `contrato.validar`.
- Todo `bibliotecas/**/*.json`: `empaquetar()` hace `rglob` y los hashea. Los BVH de `movimientos_aprobados` solo si `catalogo.json` cita `path`.
- Cada `assets[].path` de la entrada, más cámara `source` y `resolver_inputs`, más `motion.assignments` y `retarget_jobs[].raw_bvh`.
- `evidencia/ledger.json` no se lee en preflight: con `solo_validar` el proveedor queda diferido y no llama a `Ledger.before`.

Reconstrucción (el mismo `ejecutar` con `solo_validar=False`) usa los mismos fixtures que el preflight y además:

- Lee `config/runtime_cpu.json` antes del bucle de pulida, aunque no haya jobs.
- Si hay `retarget_jobs`, abre el BVH del paquete y, si el catálogo coincide, el BVH citado. Esta entrada candidata del repo tiene `retarget_jobs` vacío; la del VPS hay que listarla con el script, no suponerla.
- Construye un núcleo nuevo en la salida. No acepta el blend de `avance10/.../preview_cpu08`. Sin `compatibilidad_nucleo.json` de este código, el constructor rechaza el reuso.
- `production_approved` queda false.

`set.blend` está en los assets de `escenas/guardianes_esc1_candidata/entrada_escena.json` y el entorno es `mode=blend`. El núcleo y el constructor lo abren. En este repo faltan ese blend y `archivo/respuesta_2b_truncada_pre08.json`. El script sale 2 y no copia si falta cualquiera. En el VPS la entrada real es la que exista: primero `avance10_20261108/esc1_bvh08/entrada_escena.json`; si no, la de avance08 que ya nombra el preflight instalado. No inventar otro blend.

Las hojas PNG bajo `/opt/myia-taller-n8n/...` van dentro del JSON y ningún módulo las abre. No copiarlas para estas tres etapas.

El resto no listado del candidato (unos 5,9 MB entre bibliotecas, config y otros, fuera de las seis carpetas medidas) lo recorre el script. No se excluye por nombre: se incluye si el código lo cita.

## Disco

Libres: 3.710.181.376. El oro de este repo, sin su `archivo/` histórico, pesa 218.586 bytes. El código `motor/` del repo pesa menos de 1 MB. La stage no duplica los 1,09 GB de evidencia y archivo. `set.blend` del VPS sí entra, del tamaño que tenga; el script lo cuenta al copiar.

Reflink no está soportado. El script copia bytes. Rechaza symlink. El destino queda con `nlink` 1. No escribe si el destino contiene `avance10`, T317 o `v9_universal_calidad`.

## Bug del stage ya creado

`runtime_1145` quedó bien en física, `set.blend` y sin enlaces, pero el instalador salió 2 porque faltaba `MOTOR_BVH08_CANDIDATO/pruebas/test_malla_cabeza.py`. Ese archivo es preimagen del manifiesto de 13 (`antes` `e3c024349fcd8294f84afd522a4a3c9a79c8163f6dce9921ff19de967fcf6f9f`). La receta solo copiaba `motor/**/*.py` y no las pruebas. Los otros dos tests del parche tienen `antes` null y no deben existir antes del instalador.

Tampoco se copió la raíz `entrada_escena.json`: no está dentro de `assets`, y `motor_unico.py` la exige por nombre. Por eso faltan `entradas/oro/entrada_escena.json` y `entradas/escena/entrada_escena.json`. La referencia sí se copió, porque iba por otro argumento. El JSON no se reescribe: se copia con el mismo hash al lado de sus assets. Las rutas de `config/*.json` se listan en el recibo y no se cambian. No se abre ningún blend de `preview_cpu08`.

No hace falta `runtime_1150`. Se completa `runtime_1145` solo con lo que falta. Si un archivo ya está y el hash coincide, no se toca. Si difiere, no se escribe nada.

## Orden en el VPS, sin hacerlo desde aquí

Completar el stage que ya existe:

```bash
tar -xzf parche_avance11_stage.tar.gz -C /tmp/stage11_receta
python3 /tmp/stage11_receta/preparar_stage_avance11.py \
  --origen-motor /opt/myia-motor-v9/avance10_20261108/MOTOR_BVH08_CANDIDATO \
  --destino /opt/myia-motor-v9/avance11_20261108_pr4/runtime_1145 \
  --entrada-oro /opt/myia-motor-v9/avance10_20261108/MOTOR_BVH08_CANDIDATO/paquetes/regresion_orden_explicito/entrada_escena.json \
  --entrada-escena /opt/myia-motor-v9/avance10_20261108/esc1_bvh08/entrada_escena.json \
  --referencia-oro /opt/myia-motor-v9/avance06_20261107/oro_av06/revisor_comparable.json \
  --copiar
```

Si `esc1_bvh08` no está bajo avance10, usar la de avance08 solo como lectura. Luego el instalador en seco, y solo si imprime `SECO` el `--aplicar`. El payload de 13 no cambia.

```bash
python3 /tmp/stage11_receta/instalar_parche_avance10.py \
  --destino /opt/myia-motor-v9/avance11_20261108_pr4/runtime_1145/MOTOR_BVH08_CANDIDATO \
  --origen /tmp/parche_avance10_13/parche_avance10_13/archivos \
  --manifiesto /tmp/parche_avance10_13/parche_avance10_13/manifiesto_13.json
# solo si imprime SECO:
python3 /tmp/stage11_receta/instalar_parche_avance10.py \
  --destino /opt/myia-motor-v9/avance11_20261108_pr4/runtime_1145/MOTOR_BVH08_CANDIDATO \
  --origen /tmp/parche_avance10_13/parche_avance10_13/archivos \
  --manifiesto /tmp/parche_avance10_13/parche_avance10_13/manifiesto_13.json \
  --aplicar
```

Si `esc1_bvh08` no está en avance10, usar la ruta de avance08 que ya nombra `entrega/codigo/preflight_bvh08.py`, solo como lectura. Si falta un asset, el script sale 2 y no copia. La física tiene que seguir en `3423c9a777eb0157d49eb90869f39227fb7cf834322e2705a605a37a66d418d2`. El paquete de los 13 no cambia: tar `a2f9ef0773d3d39a8f8ef71d170e994856da79b7a18fed709a37f206243a8441`. `--aplicar` solo después de ver `SECO`.

Salidas nuevas, que no existan, dentro de `runtime_1145`:

- Oro: `runtime_1145/oro_av11`
- Preflight: `runtime_1145/preflight_av11`
- Reconstrucción: `runtime_1145/rebuild_av11`

```bash
M=/opt/myia-motor-v9/avance11_20261108_pr4/runtime_1145/MOTOR_BVH08_CANDIDATO
S=/opt/myia-motor-v9/avance11_20261108_pr4/runtime_1145
test ! -e $S/oro_av11
python3 $M/motor_unico.py \
  $S/entradas/oro/entrada_escena.json \
  --salida $S/oro_av11 --regresion \
  --blender /opt/blender/actual/blender \
  --referencia $S/entradas/revisor_comparable.json
test ! -e $S/preflight_av11
python3 - $S/entradas/escena/entrada_escena.json << 'PY'
import sys
sys.path.insert(0, "/opt/myia-motor-v9/avance11_20261108_pr4/runtime_1145/MOTOR_BVH08_CANDIDATO/motor")
from orquestador import ejecutar
x = ejecutar(sys.argv[1], "/opt/myia-motor-v9/avance11_20261108_pr4/runtime_1145/preflight_av11", prueba_cpu=True, blender="/opt/blender/actual/blender", solo_validar=True)
assert x["production_approved"] is False
raise SystemExit(0 if not x["errores"] else 2)
PY
```

La reconstrucción solo si ese preflight no trae errores. No pasa un blend viejo. El recibo `compatibilidad_nucleo.json` lo escribe el núcleo nuevo; sin él el constructor no reutiliza.

```bash
test ! -e $S/rebuild_av11
python3 - $S/entradas/escena/entrada_escena.json << 'PY'
import sys
sys.path.insert(0, "/opt/myia-motor-v9/avance11_20261108_pr4/runtime_1145/MOTOR_BVH08_CANDIDATO/motor")
from orquestador import ejecutar
x = ejecutar(sys.argv[1], "/opt/myia-motor-v9/avance11_20261108_pr4/runtime_1145/rebuild_av11", prueba_cpu=True, blender="/opt/blender/actual/blender", solo_validar=False)
assert x["production_approved"] is False
raise SystemExit(0 if x["estado"] == "COMPLETO" else 2)
PY
```

`/opt/blender/actual/blender` es el binario escrito en los scripts de avance08 ya instalados. `runtime_cpu.json` del origen se copia tal cual; no se reescribe la ruta de Python. n8n no cambia. T317 no se toca. No hay gasto de GPU ni de API.
