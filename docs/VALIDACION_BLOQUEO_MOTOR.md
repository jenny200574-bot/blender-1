# Revisión del motor: ¿se puede hacer PROPUESTA_BLOQUEO.md?
*11-nov-2026, alrededor de las 7:40 a. m. (hora Bogotá). Lectura del código en el 213 más una revisión en seco. US$0. No cambié nada.*

## Veredicto: SÍ se puede, y es genérico
- **Lo físico ya está resuelto en el motor.** `planificador.py` solo hace cumplir lo físico:
  - nadie se pisa: la distancia mínima es la suma de los dos radios más 2 cm, y el radio depende de la altura;
  - nadie queda dentro de un mueble;
  - las marcas tienen que ser alcanzables.
- **Hoy no fuerza ninguna separación.** En la corrida de la escena 2 (la de anoche) solo movió las marcas entre 3 y 11 cm, más 3 ajustes de separación.
- **El apiñamiento viene del 01.** El prompt del 01 obliga a meter toda la acción en `scene_area_xy`, que en la escena 2 son 1,0 × 0,5 m, y no da ninguna regla de distancias.
- **La escena anterior no llega.** El 01 no recibe cómo terminó la escena anterior.
- **El contrato del motor no cambia.** Sigue usando `puntos` y `personajes[].segmentos` (pos, rot, tipo, t). Si el 01 escribe mejores marcas, el motor las usa tal cual.

## Dónde se decide hoy cada posición (lo confirmé leyendo el código)
1. **`/opt/myia-taller-n8n/cajas/cubo01_accion.py`.**
   - La función `pedido()` arma el prompt con el texto base, THE_SET (con `scene_area_xy`, que sale de `zona_escena()`), CHARACTERS, SCENE y SCRIPT.
   - **No incluye nada de la escena anterior.**
   - El dato de cómo se conecta con la anterior **ya existe**: `SCENE.continuidad.con_anterior` (vale «continuacion» en la escena 2) y `SCENE.tipo`.
2. **`prompts_01/dirigir_escena_accion.txt`.**
   - Línea 20: «Stage the main action inside it», que es lo que encierra a todos.
   - Línea 37: «Nobody teleports», pero solo vale dentro de la misma escena.
   - Línea 54: «más de medio metro necesita un beat», también solo dentro de la escena.
3. **`validar()` en `cubo01_accion.py`.**
   - Ya revisa teletransportes y velocidades **dentro** de la escena.
   - El resultado lo arma `DI._VALIDAR_83` con campos fijos, así que **hoy un campo nuevo como `bloqueo` se borraría** al guardar.
4. **Motor, `m1_preparar.py`.** Copia del 01 al motor solo `puntos`, `segmentos`, `acciones` y `hechos`. Hoy `bloqueo` **no llegaría**; hace falta una línea para pasarlo, solo como información.
5. **`m3_traductor.py`.**
   - Convierte cada segmento en movimiento: caminar, girar, sentarse, quieto o acoplado. Lo demás va por el router o Kimodo.
   - Usa solo `pos`, `rot`, `tipo` y `porque`. No hay que tocarlo.
6. **`planificador.py`.** Usa A* y RVO2 para que nadie se pise. No hay que tocarlo, salvo para añadir un aviso nuevo, `BLOQUEO_ALTERADO`.
7. **El storyboard (SB) y la cámara** (`sb_camara.py`, `sb3d`) no mueven personajes. Las únicas que usan posiciones son `sb3d_argon.py` y `argon2b/entrada_universal.py`, y solo las leen.

## Revisión en seco (US$0, solo lectura, sobre los 01 que ya están guardados)
Comparé dónde termina cada personaje en una escena con dónde empieza en la siguiente:

| Paso | Mismo escenario | Saltos sin motivo |
|---|---|---|
| Escena 1 → 2 | Sí (habitación) | Spark 1,54 m · Pintor 2,19 m · Eco 1,75 m · Piquito 1,70 m · Valentina 1,03 m · Don Caos 0,34 m |
| Escena 6 → 7 | Sí (cocina) | entre 0,16 y 0,60 m |
| Escena 8 → 9 | Sí (habitación) | Spark 0,72 m, el resto entre 0,21 y 0,36 m |

- **El primer segmento de todos esos personajes es «quieto».** Es decir, aparecen en otro lugar sin moverse. Esto confirma el diagnóstico de la propuesta. Antes no lo había visto: a Piquito también le pasa, con 1,70 m.
- **La escena 3 no tiene 01.** Hace falta una regla para ese caso (ver la decisión 2 más abajo).
- **Cuando cambia el escenario, la comparación no vale,** porque las coordenadas son de otro set. Las escenas 4→5 y 7→8 se cuentan como corte de lugar.

## Qué archivos cambian (todo genérico: nada de canal, escena ni personaje)

| Archivo | Cambio |
|---|---|
| `prompts_01/dirigir_escena_accion.txt` | Cambiar «Stage the main action inside it» por «zona sugerida». Añadir el bloque STRATEGIC BLOCKING A–E de la propuesta. Quitar «run about 4 m/s» o adaptarlo al motor (ver los riesgos). |
| `prompts_01/dirigir_escena_esquema_accion.json` | Añadir `bloqueo[]` (beat, t, configuración, personajes con marca, rot y mira_a, relaciones con distancia y proxemia, porque) y `bloqueo_corte`. Añadir 4 chequeos de revisión. |
| `cubo01_accion.py` · `pedido()` | Añadir 3 bloques que arma el código: `PREVIOUS_SCENE_END` (sale de `cubos/01/esc_{n-1}.json` y de `SCENE.continuidad.con_anterior`; si falta, usa la última escena que exista con `gap:true`; si el escenario cambió, marca `relation=cut`), `FREE_FLOOR` (sale de THE_SET y del inventario) y `PHYSICAL` (con la misma fórmula de radio del planificador). |
| `cubo01_accion.py` · `validar()` | Añadir: que el salto contra `PREVIOUS_SCENE_END` tenga un beat que lo mueva, o `bloqueo_corte` con su cita; que la distancia declarada coincida con la real (±0,10 m) y nunca sea menor que la mínima; que `bloqueo` coincida con `segmentos` y `puntos`. Copiar `bloqueo` al resultado `C`. |
| `prompts_01/reparar_accion.txt` | Añadir que se reparen los errores `SALTO_SIN_MOTIVO` y los de bloqueo. |
| **Nuevo:** `cajas/continuidad_bloqueo.py` | La misma revisión que corrí en seco, ya como herramienta: lista los saltos de cualquier capítulo. Gratis. |
| Motor `m1_preparar.py` | Una línea: `E['bloqueo_01'] = D.get('bloqueo')`, solo como información. |
| Motor `planificador.py` | Un aviso nuevo, `BLOQUEO_ALTERADO`, cuando mueve una marca más de 0,15 m o rompe la proxemia declarada. No cambia su física. |
| `storyboard/prompts/etapa3y4_dirigir_storyboard.txt` | Que describa el bloqueo sin moverlo. Esto es opcional. |

**Cómo viajan los datos:** guion + SCENE.continuidad + 01 de la escena anterior + inventario del set → prompt del 01 → Argon escribe `bloqueo`, `puntos` y `segmentos` → `validar()` y la revisión de continuidad (si falla, una sola reparación) → `cubos/01/esc_N.json` → `m1_preparar` → `m3_traductor` → `planificador`, que solo cuida lo físico → Kimodo y Blender.

## Riesgos
1. **Las escenas dependen de la anterior.** Hay que dirigir en orden (1, 2, 3…). Si una escena anterior se rehace, las siguientes quedan desactualizadas, y la revisión de continuidad lo avisa.
2. **Correr no existe en el motor.** El prompt dice «run about 4 m/s», pero `m3_traductor` convierte «correr» en el clip de caminar, y el planificador avisa `VELOCIDAD_ALTA` por encima de 1,6 m/s. Una persecución bien planeada por Argon se vería caminando o daría aviso. Hay que decidir una de dos: añadir correr al motor, que es otro trabajo, o decirle a Argon que use como máximo unos 1,6 m/s.
3. **Prompt más largo.** Hoy son unos 47 mil caracteres en la escena 2, y suma unos 8 mil más.
4. **Las escenas que faltan (como la 3) rompen la cadena.** Hay que decidir si se usa la última que exista o si se para.
5. **Hay que volver a dirigir.** Para que la mejora se vea hay que rehacer el 01 de las escenas que se quieran mejorar, y eso es un paso de pago.

## Plan (todo en una copia, gratis hasta la prueba)
1. Respaldar los archivos de la tabla y trabajar en una copia nueva de `cajas/` y del motor. No se toca nada en vivo.
2. Programar los bloques nuevos del prompt, el esquema, los 3 bloques de datos, la validación, `continuidad_bloqueo.py`, la línea de `m1` y el aviso del planificador.
3. Pruebas en seco en las escenas 1 y 2:
   - armar el pedido y medir su tamaño;
   - validar con una respuesta de prueba que cumpla y otra que no cumpla;
   - pasar la revisión de continuidad sobre los 01 actuales (debe marcar los saltos de la tabla);
   - correr `m1`, `m3` y el planificador con solo CPU, usando el `--solo_cpu` que ya existe.
4. Ricardo decide si se rehace de verdad el 01 de las escenas 1 y 2 y después el motor. Este es el único paso que cuesta.

## Decisiones para Ricardo
1. ¿Correr de verdad en el motor (otro trabajo) o limitar a Argon a unos 1,6 m/s?
2. Si falta la escena anterior, ¿se parte de la última que exista o se para?
3. ¿Se empieza a programar en la copia?

## Nota sobre la tarea anterior (módulos de escenario), que quedó en pausa
- Empecé a crear una copia de prueba aislada en el 213, en `/opt/myia-pruebas-inmi/recorrido_20261111/myia-taller-n8n/`. Lleva copiados unos 374 MB de `cajas/`, sin archivos HABILITAR, y del trabajo de Guardianes.
- La copia quedó a medias cuando cambió la prioridad. No toqué la producción ni borré nada.
- No corrí ningún módulo todavía.
- La copia no sirve todavía: los programas apuntan con rutas fijas a `/opt/myia-taller-n8n`, así que antes de usarla hay que reescribir esas rutas dentro de la copia.
