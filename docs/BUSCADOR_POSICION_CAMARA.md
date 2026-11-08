# Buscador de posición de cámara

## El constructor de avance12 murió antes de auditar

Blender 4.2.3 salió con código 17: `TypeError: 'list' object is not callable` en `validar`, en `for f in muestras(f0, f1)`. El bucle de tomas había guardado la lista de la búsqueda en el mismo nombre global `muestras`. No hay `camara_v2.json` nuevo. No se demostró mejora de las seis tomas.

`validar` ahora recorre `cuadros_muestra`. La lista de la búsqueda se llama `medidas`. La prueba `test_camara_validar_no_pisa_muestreador.py` compila esas dos funciones del archivo real, les pone encima una lista llamada `muestras` y llama a `validar` como el resolutor. No abre Blender. El oro 23/23 de las 13:57 no se toca ni se vuelve a correr aquí.

## Cabeza: hay malla, y el render la oculta por cuadro

La sonda de avance12, en los cuadros 433, 468, 504, 601, 660 y 720, contó 13 mallas de cabeza y 2728 vértices evaluados. No falta la geometría.

- En 433, 468 y 504 las 13 tienen `hide_render=true`, `hide_viewport=false` y `visible_get=true`. Viewport visible no es render.
- En 601, 660 y 720 doce piezas `.base.*` pasan a `hide_render=false`. La cápsula `{id}_malla_cabeza` sigue en `hide_render=true`.
- El núcleo crea esa cápsula por hueso (`heredado/rig.py`). El constructor, si la entidad trae legacy, la marca `hide_render` y `motor_preserve_hidden` (`constructor_final.py`). El comentario del código dice que la cápsula se conserva para auditoría y no es el acabado.
- `eventos.aplicar` no reescribe un objeto con `motor_preserve_hidden`. Las piezas `.base.*` sí reciben la pista `hide_render` de una aparición o desaparición (`narrativa_estructurada.py` arma la pista; `eventos.py` la hornea, recursiva, curva CONSTANT).
- `medir` ignora las mallas con `hide_render`. Por eso un cuadro oculto cae al hueso y uno ya mostrado mide la malla. No se encienden los flags a mano: cambiarlos saltaría la pista de presencia o destaparía la cápsula a propósito.

La sonda nueva escribe `motor_preserve_hidden` y las claves `hide_render` (cuadro y valor). El rayo que antes golpeaba columna o pecho era el propio actor: ahora separa golpe propio y golpe externo, y dice que eso no es la validación de la toma.

Hasta correr otra vez el constructor no se declara cámara, cabeza, física ni video resueltos.

## Por qué las seis tomas seguían bloqueadas en avance11

- La toma con `STATIC` y después `TRACK` congela el acimut del primer cuadro. Cuando el sujeto gira en el tramo `TRACK`, la cámara queda a su espalda. El `TRACK` vuelve a medir el frente en cada cuadro.
- El factor de distancia solo toma cinco valores. El buscador recorre el intervalo cerrado de esas listas; no lo amplía.
- El eje de 180° ya fijado por una toma anterior es un semiespacio. Si la ventana de ±75° no lo corta, no hay posición legal. Sin `CROSSAXIS` no se cruza.
- Una grúa o un paneo pedidos pueden sacar la inclinación de su tolerancia o la cabeza del cuadro. No se anula la orden.
- Holgura, inclinación, roll, encuadre y eje siguen en `camara_v2_config.json`. El sensor sigue en 36 mm.

## Instalación sobre avance12, que ya tiene 1611c56

```bash
python3 instalar_parche_buscador.py \
  --destino /opt/myia-motor-v9/avance12_20261108_buscador/MOTOR_BVH08_CANDIDATO \
  --origen /ruta/del/paquete/motor \
  --manifiesto manifiesto_buscador_tipoerror.json
```

Con `--aplicar` solo si el seco sale 0. No toca `fisica_final.py` (`3423c9a777eb0157d49eb90869f39227fb7cf834322e2705a605a37a66d418d2`).

## Constructor en carpeta nueva, mismo núcleo

El log abrió `/opt/myia-motor-v9/avance12_20261108_buscador/nucleo_reutilizable/escena.blend`. El paquete es el mismo que ya recibió ese constructor. La salida tiene que ser otra carpeta.

```bash
A=/opt/myia-motor-v9/avance12_20261108_buscador
M=$A/MOTOR_BVH08_CANDIDATO
test ! -e $A/rebuild_tipoerror
SONDA_CAMARA=1 \
SONDA_ACTOR=<id del actor de las tomas 05 y 07> \
SONDA_FRAMES=433,468,504,601,660,720 \
SONDA_SALIDA=$A/sonda_tipoerror.json \
/opt/blender/actual/blender -b --disable-autoexec -t 2 --python-exit-code 17 \
  -P $M/motor/constructor_final.py -- \
  <paquete_normalizado que ya usó avance12> \
  $A/rebuild_tipoerror \
  $A/nucleo_reutilizable/escena.blend
```

Si el recibo del núcleo no coincide, el constructor se detiene. No se finge el recibo ni se repite el núcleo. Esta máquina no ejecutó Blender: la prueba de `validar` no sustituye esa corrida.
