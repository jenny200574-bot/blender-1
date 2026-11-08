# Parche avance10 — import único y recibo de reuso

Base git de esta rama: `5e65c123288901682a8305ed18ddb9dfb77b9721` (head del PR #3).
Padre: `9d450d4d1032e7fae8e0a78da2206c44d7cea188` (head del PR #2).
Ancestro común con main: `8839b1c25dd5a00339355fdf8840feeb57741524`.
Main observado, no usado como base: `4a8165fc90bd0ab893a4a473a808a29aead3c481`.
PR #1 (`b22819f`, física) no entra.

No se desplegó nada. No se unieron los PR #1, #2 ni #3.

## Cotejo del manifiesto (139 archivos, solo lectura)

Detalle: `docs/cotejo_vps_avance10.csv`.

- 97 iguales entre el VPS, el PR #3, `motor/` de main y `motor_candidato_bvh08`.
- 15 iguales solo al PR #3 (el parche ya estaba en el candidato; no faltaba).
- 21 de `entrega/codigo` iguales a `avances/avance08/codigo`.
- `motor/fisica_final.py` del VPS es `3423c9a777eb0157d49eb90869f39227fb7cf834322e2705a605a37a66d418d2` (candidato de main). En esta rama sigue el hash viejo `682856ed505cd6f63d66c81dd11e64ef8db582a94528ae228f5decd1667ec7fd`. No copiar ese archivo.
- Ausentes en git: `motor/heredado/malla_cabeza.py` (copia operativa, mismo hash que `motor/malla_cabeza.py` del PR #3: `db015e6a696399e07e50f7a7d6ab9a91be0ce7e974abaae2806acdfb5902af2d`), `entrega/codigo/preview_cpu_av09.py`, `entrega/codigo/preview_cpu_av10.py`.
- Divergen y no hay contenido en el manifiesto: `cerrar_entrega_bvh08.py` (VPS `b8f81d45ee8a`, repo `ad0bf27a99e7`) y `generar_schema.py` (VPS `9067cd678ac7`, repo `2d253f0627f9`). No forman parte de este parche.

## Qué no hacer en el VPS

- No copiar el árbol entero ni `motor/fisica_final.py` de esta rama.
- No hacer otra copia completa de avance. Disco al 97 %, 3,5 GB libres.
- No borrar la copia `heredado/malla_cabeza.py`. El código nuevo no la usa.
- No relanzar `preview_cpu_av10.py` hasta rehacer preflight y núcleo. Ese wrapper vuelve a pasar el blend viejo; el constructor ahora se detiene con `REUSO_INCOMPATIBLE`.
- No tocar T317, n8n, video-studio, GPU ni APIs.

## Instalar

El paquete para copiar al box es el archivo `parche_avance10_13.tar.gz` de los artefactos de esta corrida. Trae solo los 13 archivos, `manifiesto_13.json` y `instalar_parche_avance10.py`.

Ese instalador, sin `--aplicar`, no escribe. Con `--aplicar` escribe solo si cada archivo previo tiene el hash `antes` del manifiesto y `motor/fisica_final.py` sigue en `3423c9a777eb0157d49eb90869f39227fb7cf834322e2705a605a37a66d418d2`. Si el hash previo cambió, si un archivo nuevo ya existe, o si la física no es esa, no escribe nada. No borra la copia `heredado/malla_cabeza.py`.

```bash
tar -tzf parche_avance10_13.tar.gz
cd /opt/myia-motor-v9/avance10_20261108
python3 /ruta/del/paquete/instalar_parche_avance10.py \
  --destino /opt/myia-motor-v9/avance10_20261108/MOTOR_BVH08_CANDIDATO \
  --origen /ruta/del/paquete/archivos \
  --manifiesto /ruta/del/paquete/manifiesto_13.json
# si el seco dice SECO y la física no se toca:
python3 /ruta/del/paquete/instalar_parche_avance10.py \
  --destino /opt/myia-motor-v9/avance10_20261108/MOTOR_BVH08_CANDIDATO \
  --origen /ruta/del/paquete/archivos \
  --manifiesto /ruta/del/paquete/manifiesto_13.json \
  --aplicar
```

Los hashes `antes` y `despues` están en `despliegue/manifiesto_13.json`. No se repiten aquí para no divergir.

## Comandos CPU con rutas ya vistas

No se ejecutaron aquí. El script instalado `entrega/codigo/oro_final_bvh08.py` y `entrega/codigo/preflight_bvh08.py` (hash igual al repo) apuntan a avance08. No correrlos: escribirían en avance08. El blend viejo que sí se abrió es `/opt/myia-motor-v9/avance10_20261108/preview_cpu08/nucleo/escena.blend`. No pasarlo como tercer argumento.

Oro. Entrada, binario y referencia salen del script de oro ya instalado. La salida `oro_av10_b` ya existe; `motor_unico.py` rechaza una salida existente. Comprobar los tres `test` y parar si falta alguno:

```bash
test -x /opt/blender/actual/blender
test -f /opt/myia-motor-v9/avance06_20261107/oro_av06/revisor_comparable.json
test -f /opt/myia-motor-v9/avance10_20261108/MOTOR_BVH08_CANDIDATO/paquetes/regresion_orden_explicito/entrada_escena.json
test ! -e /opt/myia-motor-v9/avance10_20261108/oro_av10_c
python3 /opt/myia-motor-v9/avance10_20261108/MOTOR_BVH08_CANDIDATO/motor_unico.py \
  /opt/myia-motor-v9/avance10_20261108/MOTOR_BVH08_CANDIDATO/paquetes/regresion_orden_explicito/entrada_escena.json \
  --salida /opt/myia-motor-v9/avance10_20261108/oro_av10_c \
  --regresion \
  --blender /opt/blender/actual/blender \
  --referencia /opt/myia-motor-v9/avance06_20261107/oro_av06/revisor_comparable.json
```

El fixture dentro del candidato no está entre los 139 hashes. Si `test -f` falla, no inventar otra entrada.

Preflight de la escena 1. La entrada que nombra el script instalado es `/opt/myia-motor-v9/avance08_20261107/esc1_bvh08/entrada_escena.json`. No está hasheada en avance10. Usar la primera que exista y no crear otra:

```bash
ENTRADA=
for c in \
  /opt/myia-motor-v9/avance10_20261108/esc1_bvh08/entrada_escena.json \
  /opt/myia-motor-v9/avance08_20261107/esc1_bvh08/entrada_escena.json
 do
  if [ -f "$c" ]; then ENTRADA=$c; break; fi
 done
test -n "$ENTRADA"
test ! -e /opt/myia-motor-v9/avance10_20261108/preflight_av10_b
python3 - "$ENTRADA" << 'PY'
import sys
sys.path.insert(0, "/opt/myia-motor-v9/avance10_20261108/MOTOR_BVH08_CANDIDATO/motor")
from orquestador import ejecutar
entrada, salida = sys.argv[1], "/opt/myia-motor-v9/avance10_20261108/preflight_av10_b"
x = ejecutar(entrada, salida, prueba_cpu=True, blender="/opt/blender/actual/blender", solo_validar=True)
assert x["production_approved"] is False
raise SystemExit(0 if x["errores"] == [] else 2)
PY
```

Núcleo y escena 1, solo si ese preflight queda sin errores. Misma entrada. Salida distinta. El orquestador construye el núcleo y no recibe el blend de `preview_cpu08`. Puede tardar lo que tardó el constructor anterior. No enciende GPU ni llama APIs de pago si `config/argon_recetas.off` sigue presente y `politica_ejecucion.json` tiene `argon_automatico` en false, que es lo que exigía el preview instalado; comprobarlo antes.

```bash
test ! -e /opt/myia-motor-v9/avance10_20261108/preview_av10_b
python3 - "$ENTRADA" << 'PY'
import sys
sys.path.insert(0, "/opt/myia-motor-v9/avance10_20261108/MOTOR_BVH08_CANDIDATO/motor")
from orquestador import ejecutar
entrada = sys.argv[1]
x = ejecutar(entrada, "/opt/myia-motor-v9/avance10_20261108/preview_av10_b", prueba_cpu=True, blender="/opt/blender/actual/blender", solo_validar=False)
assert x["production_approved"] is False
raise SystemExit(0 if x["estado"] == "COMPLETO" else 2)
PY
```

Una cabeza medida solo por el hueso deja la toma bloqueada y `production_approved` en false. No es malla visible. El oro no se afirma desde esta VM. n8n no cambia con este parche. No hubo limpieza en el PC.
