# runtime_cpu.json — solo el stage

El rebuild no debe arrancar hasta comprobar el intérprete. Esto no declara el rebuild hecho. El oro 23/23 de las 11:57 ya quedó medido y no depende de este archivo.

## Qué hace el código

`orquestador.pulida()` lee `config/runtime_cpu.json` y toma `numeric_python` solo cuando `solo_validar` es false. El preflight sale antes de esa línea, por eso VALIDADO no miró esa ruta.

Ese valor es el argv[0] de un solo comando:

`numeric_python motor/pulida_job.py <paquete> <pulida_job_N.json> <salida>`

La salida, si corre, es `pulido.bvh` y `recibo.json`. `pulida_job.py` importa `pulida_estricta.py`, y ese módulo carga `motor/heredado/pulida.py`. Ese archivo importa, al cargarse, `numpy`, `scipy.sparse` y `scipy.sparse.linalg.splu`. No hay red ni GPU en ese worker.

El `for` de jobs está después de la lectura. Si `retarget_jobs` está vacío, el texto de la ruta se lee y no se ejecuta. Si hay un job con `raw_bvh` y el catálogo no lo tiene, sí se ejecuta. Por eso la ruta muerta del PC igual bloquea el arranque: no sabemos el contenido de la entrada del VPS más allá del preflight ya escrito.

## Oro

`motor_unico.py` en `--regresion` no menciona `runtime_cpu`. El 23/23 no hay que repetirlo por este cambio. Sigue siendo el de las 11:57, con la física intacta de ese stage. No es una aprobación de la escena ni del video.

## Diagnóstico ya medido, 11:59:46

`/usr/bin/python3` apunta a `/usr/bin/python3.12`, versión 3.12.3, entorno de sistema, no venv. `python` sin el 3 no existe. En ese intérprete hay `jsonschema`. No hay `numpy`, `scipy`, `bpy`, `mathutils`, `trimesh`, `PIL` ni `google`. No se elige por existir. El oro y el preflight usaron ese `python3` junto con Blender 4.2.3 LTS externo; eso no acredita SciPy.

`entrada/requisitos_target_blender.txt` fija `numpy==2.5.4` y `scipy==1.18.1`, y también casadi, pinocchio y crocoddyl. La instrucción de ese archivo es instalarlo como `target_blender` de Kimodo, no como `numeric_python`. No sirve para crear el entorno de la pulida. No hay otro lock en el repo. No se hace `pip` global ni un venv nuevo con versiones inventadas. No se buscan entornos de video-studio ni de T317.

## Primero, solo lectura

No cambiar la config. La sonda de las 11:59 ya rechazó `/usr/bin/python3`. No pasarlo a `--aplicar`.

```bash
S=/opt/myia-motor-v9/avance11_20261108_pr4/runtime_1145
python3 - << 'PY'
import json, os
cfg = "/opt/myia-motor-v9/avance11_20261108_pr4/runtime_1145/MOTOR_BVH08_CANDIDATO/config/runtime_cpu.json"
d = json.load(open(cfg))
print("claves", sorted(d))
print("numeric_python", d.get("numeric_python"))
print("existe", os.path.isfile(str(d.get("numeric_python"))))
print("gpu", d.get("gpu"))
PY
python3 - << 'PY'
import json
etapas = "/opt/myia-motor-v9/avance11_20261108_pr4/runtime_1145/preflight_av11/etapas.json"
d = json.load(open(etapas))
for s in d:
    if s.get("handler") == "pulida":
        print(s.get("artefacto"))
PY
command -v python3
```

El `command -v` solo muestra lo que ya está instalado. No crea un entorno ni llama a pip. Cada ruta que salga se pasa tal cual a `--candidato`, en el orden de preferencia. La primera que sea archivo regular, ejecutable, no symlink, y que importe numpy, scipy, sparse y splu, es la elegida. Si ninguna pasa, no se escribe.

## Si la pulida no tiene jobs

Leer `retarget_jobs_pending` del preflight ya escrito. Si es 0, el rebuild no ejecuta `numeric_python`: la ruta muerta se lee y el `for` no llama a nadie. En ese caso no hace falta SciPy para arrancar, y no hay que apuntar la config a `/usr/bin/python3`. El rebuild sigue siendo un `ejecutar` nuevo, sin blend viejo. Si el número no es 0, no arrancar: no hay intérprete verificado y no hay lock de esta pulida para instalar uno.

## Aplicar solo ese campo, cuando haya un intérprete que pase

No usar `/usr/bin/python3` con el diagnóstico de las 11:59. Solo un candidato que el operador pase y que la sonda acepte.

```bash
python3 /tmp/stage11_receta/configurar_runtime_cpu.py \
  --config $S/MOTOR_BVH08_CANDIDATO/config/runtime_cpu.json \
  --candidato /ruta/que/el/operador/ya/comprobo \
  --preflight-etapas $S/preflight_av11/etapas.json
```

Si imprime `SECO` y un `elegido`, repetir con `--aplicar`. Guarda `runtime_cpu.json.bak.<12 del sha>` con los bytes previos y `runtime_cpu_recibo.json` con el sha anterior y el nuevo. `source`, `gpu` y cualquier otra clave quedan iguales. No toca avance10. No hace symlink a la ruta del PC.

Si la sonda dice que falta numpy o scipy, parar. No instalar.

## Qué no hay que rehacer

Cambiar `numeric_python` no entra en el sello de `compatibilidad_artefacto.py` (ese sello hashea módulos de código y `entrada_escena.json`, no este JSON). El preflight no lee este archivo. No hace falta otro preflight para que el VALIDADO de las 11:57 siga siendo el de esa corrida.

El rebuild, cuando se lance, tiene que ser un `ejecutar` nuevo desde `entradas/escena/entrada_escena.json` hacia un directorio que no exista. Ese proceso escribe su propio `compatibilidad_paquete.json` y, al construir el núcleo, `compatibilidad_nucleo.json`. No reutiliza el paquete del preflight ni el blend de `preview_cpu08`. Esto no afirma que ese rebuild ya corrió.
