# Buscador de posición de cámara

La rejilla de acimut y distancia no falla por tener pocos puntos. Falla porque varias restricciones no viven en esa rejilla.

## Por qué las seis tomas siguen bloqueadas

- La toma con `STATIC` y después `TRACK` congela el acimut del primer cuadro. Cuando el sujeto gira en el tramo `TRACK`, la cámara queda a su espalda. Mover el acimut inicial no deshace ese giro. El `TRACK` ahora vuelve a medir el frente en cada cuadro y conserva el acimut pedido respecto de ese frente.
- El factor de distancia solo toma cinco valores. Entre dos de ellos puede estar la única distancia que encuadra y a la vez queda fuera de la holgura. El buscador recorre el intervalo cerrado de esas listas; no lo amplía.
- El eje de 180° ya fijado por una toma anterior es un semiespacio. Si la ventana de ±75° alrededor de la orientación pedida no lo corta, no hay posición legal. No se cruza el eje si el storyboard no trajo `CROSSAXIS`.
- Una grúa o un paneo pedidos cambian la altura o la guiñada. Si eso saca la inclinación de su tolerancia o la cabeza del cuadro, el cruce está vacío. No se anula la orden para que pase.
- La cabeza del actor en la toma amplia y en la toma media no es el mismo fallo. Una mide solo el hueso y la otra mide malla y aun así queda fuera de cuadro. El buscador no marca esa malla como visible ni aprueba la apariencia.
- Holgura, inclinación, roll, encuadre y eje siguen siendo los de `camara_v2_config.json`. El sensor sigue en 36 mm.

## Qué hace el código

`motor/buscador_posicion_camara.py` no usa numpy ni scipy. Si la pose pedida ya cumple, la devuelve. Si no, busca dentro del intervalo. Si el cruce está vacío, el informe nombra la restricción o el par incompatible. `validar` del resolutor sigue siendo la compuerta: un candidato geométrico que el rayo del escenario rechaza queda bloqueado.

De los 13 archivos ya instalados en avance11, solo vuelve a cambiar `motor/camara_v2_blender.py`. `motor/rig_camara_coords.py` no estaba en esos 13. Entran además el buscador, la sonda y su prueba. `motor/fisica_final.py` no va en el paquete. Su hash exigido sigue siendo `3423c9a777eb0157d49eb90869f39227fb7cf834322e2705a605a37a66d418d2`.

El recibo del núcleo no incluye estos archivos. El núcleo de 1320 cuadros se puede reabrir si `compatibilidad_nucleo.json` y el legacy coinciden. No hace falta repetir esa construcción ni usar el preview viejo. Esta máquina no tiene Blender: la escena no queda resuelta aquí. El oro 23/23 no se volvió a correr.

## Instalación, solo sobre el stage que ya tiene los 13

```bash
python3 instalar_parche_buscador.py \
  --destino /opt/myia-motor-v9/avance11_20261108_pr4/runtime_1145/MOTOR_BVH08_CANDIDATO \
  --origen /ruta/del/paquete/motor \
  --manifiesto manifiesto_buscador.json
# si el seco sale 0:
python3 instalar_parche_buscador.py --aplicar \
  --destino /opt/myia-motor-v9/avance11_20261108_pr4/runtime_1145/MOTOR_BVH08_CANDIDATO \
  --origen /ruta/del/paquete/motor \
  --manifiesto manifiesto_buscador.json
```

## Constructor nuevo, mismo núcleo

Salida distinta. No se toca `rebuild_av11`.

```bash
N=/opt/myia-motor-v9/avance11_20261108_pr4/runtime_1145
M=$N/MOTOR_BVH08_CANDIDATO
test ! -e $N/rebuild_buscador
SONDA_CAMARA=1 \
SONDA_ACTOR=<id del actor de las tomas 05 y 07> \
SONDA_FRAMES=433,468,504,601,660,720 \
SONDA_SALIDA=$N/rebuild_buscador_sonda.json \
/opt/blender/actual/blender -b --disable-autoexec -t 2 --python-exit-code 17 \
  -P $M/motor/constructor_final.py -- \
  $N/preflight_av11/paquete_normalizado \
  $N/rebuild_buscador \
  $N/rebuild_av11/nucleo/escena.blend
```

Si el recibo del núcleo no coincide, el constructor se detiene y no hay que fingir el recibo. La sonda también puede correr después, sobre un `.blend` ya guardado, sin escribirlo:

```bash
/opt/blender/actual/blender -b $N/rebuild_av11/nucleo/escena.blend \
  -P $M/motor/sonda_inspeccion_camara.py -- \
  --actor <id> --frames 433,468,504,601,660,720 \
  --salida /tmp/sonda_nucleo.json \
  --config $M/motor/camara_v2_config.json
```

Cero mallas de cabeza en el núcleo no prueba que falten durante el constructor: el constructor puede agregarlas después de abrirlo. Por eso la sonda con `SONDA_CAMARA=1` corre dentro de ese proceso. `hide_viewport`, `hide_render`, `visible_get` y los vértices evaluados separan malla ausente, oculta y deformada.
