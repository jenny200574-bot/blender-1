# Plan: motor autónomo (guion entra, videos salen)

- **Fecha:** 11 de noviembre de 2026, 09:28 America/Bogota (UTC-5)
- **Naturaleza:** plan detallado por fases. **Esta pasada no modifica** el motor, las fábricas ni n8n.
- **Gasto Argon de esta pasada:** US$0 (el tope de US$10 no se usó: el plan se arma con la evidencia ya reunida).
- **Objetivo de Ricardo:** el programa funciona solo, para **cualquier tipo de canal** (anime, cine, caricatura, realista, animales, fantasía, ciencia ficción). Primero que funcione; el costo no es la prioridad. Nada amarrado a un canal.
- **Flujo de trabajo n8n:** solo `debwaH9svFMoTnOf` (COPIA LIMPIA, el de producción). No se crean más copias ni versiones de n8n. Lo que se añada queda **activo y validado**. Nada nuevo se deja apagado.
- **Prohibido tocar:** T317, `24_TRASPASO`, `v9_universal_calidad_20261106`, el host `217.76.52.53`, el pod/volumen Star `32soe7oh2f1gtf`.
- **Método:** respaldos antes de cada cambio, nunca borrar (solo versiones y copias de seguridad). Programación pesada por agentes Cursor en el repo `https://github.com/jenny200574-bot/blender-1`. Prueba final de cero a video, más una prueba con otro tipo de canal.

**Fuentes (ya leídas, no se reabren como trabajo nuevo):** `RECORRIDO_PRODUCCION.md`, `VALIDACION_BLOQUEO_MOTOR.md`, `ANALISIS_BIBLIOTECAS_FABRICAS_HISTORIAL.md` (secciones A–E), transcript `/workspace/doc_t88/doc.txt`, código vivo en `/opt/myia-motor-unificado/v1_20261110`, `/opt/myia-fabricas`, `/opt/myia-taller-n8n/cajas`, staging `/opt/myia-staging-arreglos-20261026/`.

---

## 0. Cómo se va a trabajar (léase antes de las fases)

### 0.1 Qué significa «autónomo»
Entrada: canal + capítulo + guion (y, si hace falta, imágenes de referencia para sellar ADN).  
Salida: videos de cada escena y, al final, el capítulo unido.  
Si falta un personaje, un objeto, un movimiento, una anatomía o un estado de la historia, el sistema **investiga** (corpus/Wikipedia gratis, luego Argon), **valida en código**, **construye** con las bases de Star (283 formas, recetas, `ficha_esqueleto` humano/ave/otras plantillas) y **guarda una versión nueva** (nunca borra). El motor carga solo lo aprobado o, en un modo que Ricardo autorice, lo que ya pasó la revisión técnica.

Esto no implica gastar sin tope: las llamadas siguen pasando por ledger, reserva antes y topes. El tope se sube para que el modelo funcione, no se quita la bitácora.

### 0.2 Dónde se cambia cada cosa (y dónde no)

| Superficie | Cómo se trabaja | Qué no se hace |
| --- | --- | --- |
| n8n `debwaH9svFMoTnOf` | Se edita **este** flujo: se exporta un respaldo JSON antes, se aplican los parches, se deja activo y se valida con una corrida seca y luego una real. | No se clona el workflow. No se deja una «COPIA 2» apagada. La COPIA FABRICAS `d2Bwmk2j4ijX28eK` se usa solo como **referencia de nodos** (FAB · encolar) para copiarlos al flujo de producción, no como lugar de trabajo. |
| Motor cine_v1 `/opt/myia-motor-unificado/v1_20261110/` | Respaldo completo de la carpeta, rama en `blender-1`, agentes Cursor, prueba CPU, luego promoción al 213. | No se toca T317 ni v9 de calidad 20261106. El interruptor `motor_escena=cine_v1` se deja como camino principal; el ramal v9/T317 del flujo **se aísla** (no se borra, no se reactiva 02N). |
| Cajas del taller `/opt/myia-taller-n8n/cajas/` (01, prompts, continuidad) | Respaldo, cambios en git/213, pruebas en seco con 01 ya guardados, luego 01 de pago cuando Ricardo lo autorice. | No se usa como banco de trabajo la copia a medias `/opt/myia-pruebas-inmi/recorrido_20261111/` (apunta a rutas de producción). |
| Fábricas `/opt/myia-fabricas` y biblioteca `/opt/myia-biblioteca` | Respaldo, agentes o programación en el 213, jobs de prueba con canal **nuevo de prueba** (no reescribir Guardianes). | No se borra ninguna versión. No se toca el volumen Star `32soe7oh2f1gtf`. |
| Staging `/opt/myia-staging-arreglos-20261026/` | **Solo se reutiliza** (prompts, `esq_argon.py`, `poses_argon.py`, `recetas_argon.py`, validador `ave`). Se generaliza y se mueve al servicio vivo. | No se vuelve a correr a mano «para Piquito/perro». |
| Host `217.76.52.53` | Fuera de alcance. | No se entra. |

### 0.3 «Nada apagado» frente a islas viejas
Ricardo no quiere más sorpresas de trabajo dejado en una copia apagada. Eso se cumple así:

- Todo lo **nuevo** (FAB en producción, bucle de escenas, bloqueo, bibliotecas, historial) queda **en `debwaH9svFMoTnOf`, activo y probado**.
- Las islas ya existentes que están desconectadas a propósito (`02N` / T317, pasos 02–10 del marco viejo) **no se reactivan** (está prohibido tocar T317). Tampoco se borran. Se etiquetan en el lienzo como «legado, fuera de la cadena» y la cadena principal no depende de ellas.
- Lo que hoy está desactivado y **sí estorba o confunde** (por ejemplo `ERR · SSH MU` que convierte un fallo en «listo ✔») se **arregla**, no se deja.

### 0.4 Orden de las fases y por qué
La cadena de producción está rota o a medias (PROM·FAIL, SB antes del 01, sin fábricas encoladas, sin bucle de escenas, falso OK). Si se empieza por las bibliotecas o el bloqueo y se prueba «de cero a video» sobre ese flujo, la prueba no mide el motor: mide el n8n roto. Por eso:

0. Respaldos y rama.  
1. Cadena n8n + motor de producción **usable de punta a punta** (sin mentir «listo», sin hardcodes de Génesis, con fábricas encoladas y bucle).  
2. Ubicaciones (bloqueo completo).  
3. Correr y volar (locomoción).  
4. Bibliotecas que crecen + Argon autónomo + formas (Star, sin TRELLIS).  
5. Historial de cambios.  
6. Huecos de adaptabilidad (poderes, agua, vehículos, muchedumbres…): programación que falte + Argon.  
7. Barrido de amarre a un canal.  
8. Prueba de aceptación: un guion de cero a video + un segundo tipo de canal.

Cada fase tiene criterios de aceptación. No se pasa a la siguiente sin cumplirlos (salvo que Ricardo autorice un solape explícito, por ejemplo 2 y 3 en paralelo después de 1).

---

## 1. Estado actual (resumen para el plan)

Lo que **ya funciona** y se reutiliza:

- Motor cine_v1: carga moldes de `/opt/myia-biblioteca`, A*+RVO2, Mwni (caminar, girar, sentarse), foot-lock, Kimodo encendido (`config_motor.json`), cámara calculada, Shakify opcional.
- Fábricas v2: humanos por plantilla; objetos/escenarios por Star 283 + recetas Argon APTAS; publicación versionada; GPU RunPod con ledger.
- Staging del 9-nov: investigación de ave, 64 poses, recetas G1–G4, **pagadas y en disco**, no enganchadas al worker.
- 01 ya emite `hechos` y `cambio` (`romper`, etc.); el motor no los aplica entre escenas.
- Orden 62 ya tiene `permanente` / `estado_vigente` / `historial/` en la biblioteca **vieja** de pintura, no en la 3D que carga cine_v1.

Lo que **impide** hoy «guion entra, videos salen» en el flujo de producción:

1. `PROM · FAIL` tumba la ejecución si la rama de sellos entra a CUBO sin ids (H1).  
2. El storyboard y el motor corren **antes** de dirigir el 01 (H2).  
3. No hay `FAB · encolar` en `debwaH9svFMoTnOf`: el sello no construye el `.blend` solo.  
4. No hay bucle de escenas en producción (H9); la unión 11–18 está vacía y ni siquiera se alcanza desde el motor.  
5. Un error SSH del MU se pinta como «listo ✔» (H5). La GPU **dentro de este flujo** no está probada (solo en `MUcineV1escena01`).  
6. Pago del SB bloqueado: falta el manifiesto `storyboard_esc<N>.json` (H6).  
7. Hardcodes: `ESC · escenario creado` fija `escena=11`, `CAM_T3` y canal Génesis (H3).  
8. Un no humano sin `ficha_path` se detiene en `esperando_pago_argon`. La ficha Argon de Piquito (29/38) no es la publicada.  
9. `correr` se traduce a `caminar`. `vuelo_alas.py` y `adaptar()` no se ejecutan.  
10. El 01 apiña en 1,0×0,5 m y no ve la escena anterior.  
11. El historial de daño no llega a `m1_preparar`.  
12. Varios nombres y valores siguen oliendo a Guardianes / Génesis / «escena 11».

---

## Fase 0 — Respaldos, rama y reglas (gratis)

**Meta:** poder cambiar y volver atrás, sin tocar lo prohibido.

**Dónde:** 213, git `blender-1`, PC (copia de este plan, ya en `recorrido_n8n_20261111`).

**Trabajo:**

- Exportar n8n `debwaH9svFMoTnOf` (JSON completo) a `/opt/myia-…/respaldos/` con fecha, y una copia en el repo o en la PC.
- Tarball de `/opt/myia-motor-unificado/v1_20261110/`, `/opt/myia-fabricas/` (código, no secretos), `/opt/myia-taller-n8n/cajas/` (prompts y cubo01), índices de `/opt/myia-biblioteca` (no hace falta clonar todos los blends si el disco es grande: sí `meta.json` + lista de versiones).
- Rama git, por ejemplo `plan/motor-autonomo-20261111`, a partir de lo que hoy corresponda a cine_v1 en `blender-1`.
- Lista de exclusión en el README de la rama: T317, 24_TRASPASO, v9_universal_calidad_20261106, 217.76.52.53, `32soe7oh2f1gtf`.
- Inventario de hardcodes (grep de `gdc-`, `guardianes`, `gnesis`, `escena=11`, `CAM_T3`, `habitacion` por defecto, prefijos de canal en código). Se completa en la fase 7, se empieza a llenar aquí.
- No se abre la copia `/opt/myia-pruebas-inmi/…` como entorno.

**Quién lo hace:** el agente en el 213 (respaldos) + un agente Cursor corto (rama e inventario en el repo).

**Aceptación:**

- Hay un respaldo fechado y un comando de rollback escrito (restaurar tarball + reimportar el JSON de n8n).
- La rama existe. Cero cambios en producción en esta fase.
- La lista de no-tocar está firmada en el plan (este apartado).

---

## Fase 1 — Cadena de producción usable (n8n `debwaH9svFMoTnOf` + enganche MU)

**Meta:** que un capítulo, en el flujo **de producción**, pueda recorrerse de Inicio a videos **sin mentiras y sin romperse**, todavía con los 01/moldes que ya existen. Es el cimiento de todas las pruebas.

**Dónde:** n8n producción (único flujo), cajas solo si hace falta un manifiesto SB, no el motor de bloqueo todavía.

**Cambios (todos sobre el flujo actual, respaldo previo):**

1. **H1 — PROM·FAIL.** Si la rama de sellos no trae ids de CUBO, no continuar a PROM 10a. Salida «ok / sin ids, sigue el Paso 00» hacia el wait de `4a6+4b3+4c3+5`. El `PROM · FAIL` no debe tumbar la cadena principal. Los pasos 11–18 (vacíos) se dejan como isla etiquetada, **no** se rellenan aún (eso es unir capítulo, fase 1 in fine y fase 8).
2. **H2 — orden 01 → SB → MU.** El storyboard y el interruptor del motor salen de `01 · revisar y guardar` (o de una compuerta «¿ya dirigida?»). Nunca de `01 · leer` en paralelo a dirigir.
3. **H5 — falso «listo ✔».** `ERR · SSH MU` (y el mismo patrón en otros SSH) va a un nodo de error visible, no a «listo». `MU · leer lanzamiento` exige `ok=true` y un `id` de corrida; si `correr` devuelve `ok:false`, se para.
4. **H3 — hardcodes.** `ESC · escenario creado` toma `escena`, cámara y canal de Entradas / del escenario de **esta** escena. Cero `11`, `CAM_T3`, `cn-gnesis-…` por defecto.
5. **H6 — SB.** Crear los manifiestos `storyboard_esc<N>.json` **genéricos** (plantilla por escena, no un manifiesto de Guardianes copiado). `SB · ¿con pago?` mira también `modo`. Si la escena ya tiene SB aprobado, reusar US$0.
6. **H4 — tope GPU.** Pasar `tope_usd` (y modo) de Entradas hasta `entrada_n8n.py` / `correr`. Añadir ✋ de precio del MU, o al menos que el tope de n8n sea el que manda si es más bajo que `config_motor.json`.
7. **FAB · encolar en producción.** Copiar desde COPIA FABRICAS (solo como plantilla) los nodos `FAB · validar/encolar/esperar estado` de personaje, escenario, objeto y objeto_usuario, y `CAP · armar pedidos FAB desde cubo`, **a `debwaH9svFMoTnOf`**, en la cadena del Paso 00 **después** de sellos y **antes** del 01. Quedan **activos**. El wait de 5 min es para trabajos de fábrica, no se vende como «revisión de filmación».
8. **Bucle de escenas.** Traer la lógica ya probada en «PRUEBA bucle cine_v1» **dentro** de este flujo: tras `ESCENA · listo` (solo si está realmente OK), siguiente escena del capítulo, hasta la última, luego un paso **real** de unión (FFmpeg, no el nodo vacío 18). No se deja el bucle en una copia.
9. **Webhook.** Autenticación o desactivar el GET abierto de cotizar, o dejarlo solo en modo cotizar con token. Decisión de Ricardo (D7).
10. **Interruptor.** `motor_escena` por defecto `cine_v1`. El ramal v9/T317 no se edita ni se borra; no es el camino de las pruebas.

**Archivos / nodos:** JSON del flujo; posiblemente `entrada_n8n.py` (tope); `cajas/ver_prepago/manifiestos/storyboard_esc*.json` (plantilla); ningún archivo T317.

**Pruebas de la fase:**

- Corrida **seca** (`modo=cotizar`, `tope_usd=0`) de Guardianes cap. 1, escenas que ya tienen 01 y moldes: no cae en PROM·FAIL; el SB no arranca antes del 01; un error SSH no termina en ✔.
- Inspección: no quedan `escena=11` / `CAM_T3` / Génesis en la cadena principal.
- FAB: un personaje ya aprobado se **reusa** (US$0, estado `reusado`), no se reconstruye.
- El bucle recorre al menos 2 escenas en seco y para al terminar (o al faltar datos), sin inventar.

**Aceptación:** una corrida seca del flujo de producción, de Inicio a «escenas listas / faltantes declarados», con log sin falso OK y sin hardcode de otro canal. Aún no se exige video nuevo (eso es fase 8).

**Rollback:** reimportar el JSON respaldado en la fase 0.

---

## Fase 2 — Ubicaciones: no apiñar, continuidad, cortes declarados

**Meta:** aplicar **entera** `PROPUESTA_BLOQUEO` + lo ya validado en `VALIDACION_BLOQUEO_MOTOR.md`. El planificador sigue siendo solo físico. El 01 decide el bloqueo estratégico.

**Dónde:** cajas 01 (taller) y dos toques mínimos del motor (`m1_preparar`, `planificador`).

**Cambio, archivo por archivo** (genérico, sin nombres de canal):

| Archivo | Qué se hace |
| --- | --- |
| `prompts_01/dirigir_escena_accion.txt` | «Stage the main action inside it» pasa a **zona sugerida**, no cárcel. Bloque STRATEGIC BLOCKING A–E: se usa todo el piso libre; las distancias salen de la emoción y de la estatura; apiñar **solo** si el guion lo pide (abrazo, pelea cuerpo a cuerpo, esconderse) y queda citado; continuidad desde `PREVIOUS_SCENE_END`; cortes con `bloqueo_corte` + cita. Quitar o adaptar «run about 4 m/s» según la decisión D1 (si en la fase 3 ya existe correr, se alinea aquí). |
| `prompts_01/dirigir_escena_esquema_accion.json` | Campos `bloqueo[]` y `bloqueo_corte` + 4 chequeos. |
| `cubo01_accion.py` `pedido()` | Inyecta `PREVIOUS_SCENE_END` (01 de la escena anterior o, si falta, la regla D2), `FREE_FLOOR`, `PHYSICAL` (misma fórmula de radio que el planificador). |
| `cubo01_accion.py` `validar()` | Salto sin beat ni corte declarado = error; distancia declarada vs real ±0,10 m, nunca bajo el mínimo físico; `bloqueo` coherente con `segmentos` y `puntos`. **Conservar** `bloqueo` en la salida (hoy `_VALIDAR_83` lo tiraría). |
| `prompts_01/reparar_accion.txt` | Reparar `SALTO_SIN_MOTIVO` y fallos de bloqueo. |
| Nuevo `cajas/continuidad_bloqueo.py` | La revisión en seco ya hecha, como herramienta de cualquier capítulo. |
| Motor `m1_preparar.py` | `E['bloqueo_01'] = D.get('bloqueo')` (informativo). |
| Motor `planificador.py` | Aviso `BLOQUEO_ALTERADO` si mueve una marca >0,15 m o rompe la proxemia. No cambia la física. |
| Opcional: prompt SB | Describe el bloqueo, no lo mueve. |

**Datos:** `SCENE.continuidad.con_anterior` y `SCENE.tipo` ya existen; el 01 hoy no los usa. Eso se conecta aquí.

**Pruebas (gratis, CPU):**

- Pedido de las escenas 1 y 2: medir tamaño del prompt (~47 k + ~8 k).
- Validador: un JSON que cumple y uno que no.
- `continuidad_bloqueo.py` sobre los 01 actuales: debe marcar los saltos ya medidos (escena 1→2: Spark 1,54 m, Pintor 2,19 m, etc., primer segmento «quieto»).
- `m1` + `m3` + planificador `--solo_cpu`.

**Aceptación:**

- Con un 01 de prueba (aunque sea sintético, US$0), nadie aparece teletransportado entre escenas del mismo set sin beat o corte citado.
- El apiñamiento 1,0×0,5 m **deja de ser obligatorio** en el prompt. Si el guion pide un abrazo, la distancia corta es válida.
- Cero nombres de Guardianes en los archivos tocados.
- Para **verlo en video** hace falta redirigir el 01 de verdad (pago). Eso se pide en la fase 8, no se cuela aquí sin OK.

**Agentes Cursor:** sí (prompts + `cubo01_accion.py` + `continuidad_bloqueo.py` + dos parches del motor).

**Dependencia:** fase 1 (si no, el SB/motor pueden correr con un 01 viejo y la prueba confunde).

---

## Fase 3 — Correr, trotar, volar

**Meta:** que una acción del 01 «correr» o «volar» / «aletea» produzca ese movimiento, no un caminar disfrazado ni un quieto.

**Dónde:** motor cine_v1 (`m3_traductor.py`, `m3_router.py`, `motor_blender.py`, `correr_escena.py`, `kimodo_pedidos.py`, `vuelo_alas.py`).

**Qué hay y qué falta:**

- Hoy `'correr': 'caminar'` en `m3_traductor.py` L22–23. El planificador avisa `VELOCIDAD_ALTA` > 1,6 m/s. Kimodo tiene `CORRER_M_S = 2.0` pero el segmento ya llegó como caminar. Hay clip `trotar` en `indice_clips.json`, usado por **umbral de velocidad**, no por la acción.
- `m3_router.py` clasifica `vuelo_alas` / `vuelo_sin_alas` y apunta a `vuelo_alas.py`. `adaptar()` (hasta 4 intentos Argon, tope 0,75 / 3,0) **no tiene caller**. En acciones, el traductor ignora `tipo_ejecucion='receta'`. Blender no llama `vuelo_alas.py`.

**Trabajo:**

1. Sacar `correr` del mapa a `caminar`. Tipo propio: clip `trotar` o `correr` si existe; si la velocidad o el 01 piden carrera, Kimodo con texto de carrera y tope de velocidad coherente (p. ej. 2,0–3,0 m/s, no 4 m/s del prompt viejo hasta que se mida). El planificador usa `VEL_MAX` acorde, o un `VEL_MAX` por tipo de segmento.
2. Registrar en `movimientos_aprobados` (fase 4) el clip que pase revisión, para no regenerar.
3. Cablear vuelo: traductor, si `enrutar` devuelve `receta`, **ejecuta** `vuelo_alas` (o pide fábrica si faltan huesos `ala`). `correr_escena` / `motor_blender` aplican la receta al molde **sin cambiar la forma**. Si la receta falla, `adaptar()` con ledger y topes; si se agotan intentos, STOP claro, no quieto silencioso.
4. Un personaje ave (Piquito o una prueba nueva) debe poder aletear usando poses aprobadas + receta de vuelo, no solo una pose estática.
5. Pruebas CPU de traductor/router con acciones sintéticas `correr` y `volar` / `aletea`, más una prueba GPU corta (un plano, un personaje) cuando Ricardo autorice el gasto.

**Aceptación:**

- Un JSON de 01 con `accion=correr` produce en `movimiento.json` tipo correr/trotar, no `mocap:caminar`.
- Un JSON con `accion=volar` o `aletea` no se ignora: o se anima con `vuelo_alas`, o STOP `pedir_a_fabrica` / rechazo tipado.
- `adaptar()` aparece en el log de una prueba (aunque sea en seco con mock hasheado, US$0) o en una llamada real autorizada.
- Cero hardcodes de Piquito en el router (ya es por roles `ala`, se mantiene así).

**Agentes Cursor:** sí, este es el núcleo del motor de movimiento.

**Dependencia:** fase 0 (rama). Puede solaparse con la 2 en el repo, pero la prueba GPU espera a la 1 si se lanza desde n8n.

---

## Fase 4 — Bibliotecas que crecen + Argon autónomo + formas (Star, sin TRELLIS)

**Meta:** si falta un movimiento, una anatomía, un personaje, un objeto, un escenario o un juego de poses, el sistema lo investiga, lo valida, lo construye con bases de Star y lo versiona. Nada se borra.

**Casa de las bibliotecas** (de la sección A, se adopta en este plan):

| Biblioteca | Dónde | Quién escribe | Quién lee |
| --- | --- | --- | --- |
| Movimientos aprobados | `/opt/myia-biblioteca/_comun/movimientos_aprobados/` + retarget por personaje si hace falta | Motor, tras revisión técnica (portar `catalogos_crecimiento.registrar` de v9) | Selector **antes** de Kimodo/Argon/clips |
| Recetas aprobadas | Ya: `_comun/recetas_star_aprendidas` + `objetos/<id>/receta/vNNN/` | Fábricas, solo APTAS | `plan_escenario`, `_objetos_lote` |
| Anatomías propuestas | `personajes/<id>/anatomias_propuestas/vNNN/` → al aprobar, `ficha_esqueleto/vNNN/` | Fábricas + Argon | Motor solo la ficha aprobada |
| Poses | `personajes/<id>/poses/vNNN/` | Fábricas / `poses_argon` generalizado | Motor, con `approval_ref` |
| Moldes PJ/objeto/escenario | ya en `<canal>/<tipo>/<id>/` | Fábricas | `m1_preparar` (estados permitidos) |

**Autonomía (el hueco de hoy):**

1. Generalizar `esq_argon.py` + `PROMPT_INVESTIGACION_*` (hoy fijados a Piquito/perro) a un paso `investigacion_personaje_v1_corpus` **con ADN + corpus vía B + esquema `ficha_esqueleto/v1`**. Plantillas del validador: `bipedo_humano`, `ave`, `cuadrupedo`, `pez`, `serpiente`, `objeto_magico`, `otro` (`validador.py` L22, L34).
2. En `workers_v2_3d._personaje`: si `generar_ficha_humana` sale exit 4, **no parar en `esperando_pago_argon` sin llamar**. Con `argon_enabled` y tope/ledger: investigar → validar (213, US$0) → si apta, seguir a GPU. Si no hay saldo o el validador rechaza, STOP tipado, no un ejemplo manual silencioso.
3. Generalizar `poses_argon.py` (8 tandas, tope, sin nombres «polluelo_chibi» en el código; el contenido sale del ADN y de la ficha).
4. Recetas de objeto: ya en el servicio; encolarlas desde n8n (fase 1) y, si FALTA, disparar `_recetas_argon` / `_recetas_sueltas` solos.
5. Publicar **la ficha Argon**, no un `EJEMPLO_MANUAL`, cuando la investigación sea la fuente.
6. Portar de v9 solo el contrato de crecimiento (hash, `technical_approved`, no pisar, reusar antes de generar). No se instala v9 como motor.

**Forma orgánica libre (sin TRELLIS), decisión de diseño de este plan:**

- Argon **no esculpe una malla**. Descompone la forma en primitivas del catálogo Star (283) y/o piezas de `ficha_esqueleto` (`esfera`, `capsula`, `cilindro`, `cono`, `caja`, `toro`), con medidas, jerarquía, colores y, si anima, huesos y límites.
- El constructor que ya arma fichas y recetas construye el molde. Eso es «crearlo con el motor de Star».
- Si la forma no se puede descomponer (una cara hiperrealista, una tela simulada, un fluido), el sistema **para y declara FALTA de tipo**, no inventa un mesh. Más programación de esa clase se lista en la fase 6 (agua, pelo dinámico, etc.).
- TRELLIS sigue fuera de alcance (experimento suelto, no se conecta en este plan, de acuerdo con Ricardo: formas con Star).

**n8n:** los nodos FAB de la fase 1 deben esperar también `esperando_pago_argon` / investigación en curso, no solo `listo`/`reusado`.

**Pruebas:**

- Personaje humano nuevo (canal de prueba, no Guardianes): plantilla, US$0 de Argon si el ADN está sellado, GPU, `hoja_lista`.
- Personaje no humano nuevo (p. ej. un cuadrúpedo de un canal de prueba): corpus + Argon + validador + GPU; la ficha publicada lleva `origen.tipo=argon`.
- Objeto cuyo nombre no está en las 283: receta APTA o FALTA explícita.
- Reuso: el segundo job del mismo id es `reusado`, US$0.
- Versiones: `v001` sigue en disco cuando sale `v002`.

**Aceptación:** los tres caminos (humano, no humano, objeto FALTA→receta) corren **desde el flujo de producción** (o al menos desde `fabrica_encolar` disparado por ese flujo), sin scripts a mano en staging, y sin palabras de Guardianes en el código nuevo.

**Agentes Cursor:** sí (worker, prompts genéricos, portar staging, contrato de catálogo). Los prompts se revisan en seco (US$0) antes de la primera llamada real.

**Gasto:** esta fase **sí** usa Argon y GPU. No se lanza hasta que Ricardo apruebe un tope de lote (propuesta en el §9).

---

## Fase 5 — Permanencia de cambios (historial)

**Meta:** si en el guion se rompe una espada, se daña un muro o se rasga la ropa, el activo queda así al reusarse, salvo que el guion diga `reparar`. Flashbacks usan la versión madre.

**Modelo (de la sección C, se adopta):**

```
/opt/myia-biblioteca/<canal>/<tipo>/<id>/
    blend/vNNN/                    # molde base, no se «cura» al reconstruir
    historial_historia/eventos.jsonl
    historial_historia/estado_vigente.json
    variantes_historia/vNNN_<etiqueta>/
```

Evento: escena, cita, `cambio`, `toca_geometria`, `reversible`, `variante_ref`, `molde_base_ref`, `vigente_en`. Vocabulario: se añade **`reparar`** a `CAMBIOS` en `eventos_o112.py`.

**Quién escribe / lee:**

- 01 detecta (`hechos`, `cambio`); el código valida (el objeto existe; `reparar` solo cierra un evento reversible; la cita está en el guion).
- Un módulo de biblioteca 3D (portar semántica de `cajas/biblioteca.py` `permanente`, **no** usar `trabajo/biblioteca` como fuente 3D) hace append-only.
- Fábricas materializan variante (`espada_rota`) si hace falta geometría o material nuevo, con la misma compuerta de la fase 4.
- `m1_preparar` resuelve el estado a la línea temporal de **esta** escena (presente, flashback, paralelo) y entrega molde + variante + ocultar/material. Si la variante no está lista: faltante tipado, no el sano en silencio.
- El 01 de la escena N+1 recibe `estado_vigente` (hoy no lo recibe).

**Casos borde** (van en tests): flashback, corte hacia adelante, escenas paralelas, reparación, escena previa faltante (D2), el mismo objeto en dos sitios, dos instancias, cambio no persistente (`persistente: false`).

**Aceptación:** test CPU con un objeto de prueba: escena 1 `romper`, escena 2 carga la variante; un `reparar` con cita vuelve al base; un flashback carga la madre. Luego un plano GPU corto en la prueba de la fase 8.

**Agentes Cursor:** sí (modelo + `cubo01` + `m1` + worker de variantes).

**Dependencia:** fase 4 (variantes de molde) y fase 2 (el 01 ya ve la escena anterior; el historial se inyecta igual que `PREVIOUS_SCENE_END`).

---

## Fase 6 — Adaptabilidad: qué va a exigir cada tipo de canal

**Meta:** enumerar las variables reales de «cualquier canal», decir qué sabe hacer hoy el motor, qué hay que programar, y cómo Argon rellena datos (nunca inventar geometría no validada).

Esto es análisis **para programar después de las fases 1–5** (o en paralelo de diseño). Lo que salga de aquí como módulo nuevo se implementa al final de esta fase, con aceptación propia, no se deja en un documento.

### 6.1 Matriz

| Variable del canal / la historia | Qué debe adaptar o crear el motor | ¿Hay código hoy? | Programación nueva | Rol de Argon |
| --- | --- | --- | --- | --- |
| Género visual (anime, cartoon, cine realista, stop-motion, 3D estilizado) | Materiales, proporción, línea, iluminación, grano | Sello de estilo del canal (SELLO ESTILO); plantilla y colores del ADN | Política de estilo versionada en `_comun` o por canal (luts, shaders, toon vs EEVEE realista) que el render lea del canal, no de Guardianes | Describe estilo en el ADN de estilo; no pinta el shader a mano |
| Tono (comedia, terror, documental, musical, educativo) | Cámaras, ritmo, distancia social, música/diálogo | 01 + SB + investigación de cámaras (tabla Star, parcial) | Ampliar tabla de cámaras (ya pedida) y reglas de proxemia por tono, en datos, no en `if canal==` | Elige bloqueo y tomas según la tabla y el guion |
| Especie / no humanoides (ave, cuadrúpedo, pez, insecto, robot, slime, dragón, de varios tamaños) | Ficha, rig, locomoción, poses | Validador con plantillas; investigación staging solo ave/perro; humanos plantilla; vuelo huérfano | Fase 3–4: investigación genérica + clips/recetas por **roles** (ala, cola, rueda). Plantillas nuevas solo si el validador no cubre un plan corporal | Investiga análogo real + ficha; no inventa huesos que el validador no pueda chequear |
| Muchedumbres / extras | Muchos agentes, LOD, no todos con Kimodo caro | RVO2 para pocos personajes de escena | Instancing / ciclo de caminar compartido, presupuesto (N héroes Kimodo, extras mocap), colisión por grupos | Describe qué hace la masa; no anima a cada extra |
| Vehículos / monturas | Caminos que no son solo piso peatonal, anclaje de conductor | Acople hueso a hombro/mano | Receta de vehículo (ruedas, riel, trayectoria), «personaje acoplado a objeto móvil», planificador con carriles | Receta de piezas + cómo se conduce; el código simula |
| Poderes / VFX / magia / rayos / portales | Efectos con tiempo, no solo un prop | `eventos_o112` tiene `efecto` (anillo_portal, rayo, partículas…); escenario `vivo` muy limitado | Sistema de efectos: id, emisor, curva, duración, no atraviesa el set si no toca; biblioteca de efectos versionada (primitivas + shaders) | Propone el efecto con cita; el revisor lo valida; no «inventa un volume» sin receta |
| Agua, fuego, humo, clima, de día/noche | Volumen, reflexiones, ciclo de luz | Luces del molde; poco más | Módulos: cielo/sol por hora (datos), agua como plano + shader o receta de vaso/río (el jardín ya sufrió FALTA en río), partículas de lluvia/fuego con tope de costo de render | Describe estado del cielo y del agua; no simula fluidos de cine si no hay módulo |
| Escala extrema (gigante vs 18 cm, macro, planetas) | Relación de tamaño, cámaras, pies, acople | Altura del ADN ±2 %; Don Caos / Piquito 0,18 m ya forzó acople | Reglas de cámara por escala (ya esbozadas: ojos/hombro del grande); colisiones y VEL_MAX por tamaño; no un solo `VEL_MAX=1.6` para todos | Pide alturas en metros (ya en ADN); no estima escalas |
| Interacción con props (agarrar, romper, vestir, soltar) | Manos, constraints, historial | Objetos en mano vía acople; `cambio=romper` no aplica malla; `pedir_a_fabrica` | Fase 5 + constraints de agarre genéricos (hueso mano ↔ objeto); vestuario como variante de personaje | Detecta el cambio en el guion; la fábrica hace la variante |
| Vestuario / damage / suciedad | Variantes de malla/material | No hay historial 3D vivo | Fase 5; slots de ropa en ficha (hoy palabras del ADN en plantilla humana) | Propone la variante; no edita la ficha base |
| Interior / exterior / sets vivos | Cambios de luz y de set en el tiempo | `vivo` solo con prop de fábrica; 4a4 no estructura bien los cambios | Lista de cambios 4a4→eventos del motor (el Inmi lo diagnosticó); historial de set (fase 5) | Escribe cambios estructurados (objeto, tipo, t), no prosa |
| Estilo de cámara (documental, anime escolar, western, found footage) | Lente, temblor, eje, cobertura | Cámara calculada + Shakify + DSL | Tablas por estilo en datos del canal; el SB las lee | Elige tomas dentro de la tabla; el motor no adivina grados |
| Diálogo denso vs acción / persecución / pelea / baile | Tiempo, boca, pelea, mocap | 01 tiempos; pelea en router (a menudo rechazo o Kimodo); baile no | Lip-sync queda en Omni **después** del motor (contrato v9); pelea: clips o Kimodo + contactos; baile: mocap dedicado | Describe el tipo de acción; no sustituye mocap de pelea si no hay receta |
| Multilenguaje / voz | Temporizado del diálogo | El motor exporta `tiempos_dialogo` en v9; cine_v1 a confirmar en implementación | Asegurar exportación genérica; no meter voces en el 213 si Omni va después | No genera audio aquí |
| Ciencia ficción (hologramas, trajes mecánicos, naves) | Rigs mixtos, FX | `objeto_magico`, recetas | Mismos ganchos de poderes + vehículos; armadura como variante / huesos extra validados | Ficha o receta; validador de huesos extra |
| Fantasía (transformación, sin forma, tentáculos) | Cambio de rig a mitad de escena | Router `sin_forma`; no hay ejecución completa | Receta `sin_forma` ejecutada (como vuelo); transformación = variante + evento de historial, no un morph libre | Receta y momento; el código cambia de molde o de visibilidad |
| Música / cliptone / videoclip | Corte al beat | No | Reloj a marcadores del guion; fuera de la MVP si no hay demanda inmediata | — |
| Multi-episodio / serie | Continuidad larga | Hechos 01 no persisten | Fase 5 a escala de capítulo/temporada | No «olvida» un daño aprobado |

### 6.2 Qué hay que programar de más (respuesta directa)

Sí, hace falta **más programación**, además del bloqueo, las bibliotecas, correr/volar y el historial:

1. **Efectos / poderes** como biblioteca versionada (no un `if` de rayo de Don Caos).  
2. **Vehículos y objetos móviles** con personaje acoplado.  
3. **Muchedumbres** (LOD, un solo ciclo, presupuesto).  
4. **Agua / fuego / clima / ciclo de día** como estados del set, no como geometría inventada.  
5. **Estilo de render por canal** (toon vs realista).  
6. **Agarre y suelta** de props, más allá del acople a un hueso.  
7. Completar **sin_forma / transformación**.  
8. **VEL_MAX y cámaras por escala**.

El patrón es siempre el mismo: **código genérico + datos/recetas que Argon llena + validador + versión**. Nunca un módulo «solo Guardianes».

**Aceptación de la fase 6:** cada ítem de prioridad 1–5 tiene o bien un módulo con test, o bien un FALTA tipado documentado («aún no hay agua volumétrica»). Nada a medias sin etiqueta.

**Agentes Cursor:** sí, un agente por módulo, contratos iguales (entrada JSON, validador, ledger).

---

## Fase 7 — Nada ligado a un canal

**Meta:** un canal nuevo no exige editar Python. Guardianes y Génesis son solo datos en la biblioteca.

**Trabajo:** barrido del inventario de la fase 0 en motor, cajas, fábricas, nodos n8n (Entradas, SELLO, ESC, CUBO, textos de formularios). Sustituir fijos por parámetros (canal, id, escena, cámara salen del pedido). Pruebas con un `canal` inventado (`cn-prueba-autonomo-…`) y nombres que no sean `gdc-*`.

**Aceptación:** `grep` de producción (motor + cajas + worker + nodos del flujo) sin `guardianes`, `gnesis`, `CAM_T3`, `escena=11` como valores por defecto. Los que queden deben estar en **datos** de un canal, no en código. Una prueba de la fase 8 arranca con el canal de prueba sin retocar esos archivos.

---

## Fase 8 — Pruebas de aceptación (cero a video + otro tipo de canal)

**Meta:** demostrar el propósito: entra un guion, salen videos, dos tipos de canal.

### 8.1 Prueba A — Capítulo ya conocido (Guardianes, para no mezclar fallos de contenido nuevo)

- Flujo: `debwaH9svFMoTnOf`, `motor_escena=cine_v1`, de Inicio (o desde 01 si el Paso 00 ya está) hasta unión.
- 01 redirigido con bloqueo (pago, OK de Ricardo).
- Criterios: no PROM·FAIL; 01 antes de SB; continuidad 1→2 sin teletransporte; errores no se pintan ✔; videos en `corridas/…/salida/`; `revision_ok` leído de verdad; gasto anotado.

### 8.2 Prueba B — Otro tipo de canal (genericidad)

Canal **nuevo**, estilo distinto (propuesta: un corto «realista de animales», un cuadrúpedo + un humano, un set exterior, un objeto que no esté en las 283, un cambio persistente —p. ej. un palo que se rompe— y una acción de correr o un tramo de vuelo/aleteo si hay ave). Guion corto: 2 escenas.

Criterios: ningún archivo de código se edita para ese canal; la fábrica investiga y construye; el historial aguanta entre las 2 escenas; el video sale por el mismo flujo.

### 8.3 Criterios transversales

- Autonomía: un faltante dispara investigación o un STOP claro, nunca un molde sano callado ni un ejemplo manual no declarado.
- Versionado: no se borra v001.
- Ledger: cada US$ de Argon y GPU tiene comprobante.
- Rollback: se puede volver al tarball de la fase 0.

---

## 9. Método, agentes Cursor, respaldos, gastos a autorizar después

### 9.1 Orden y dependencias

```
0 respaldos
 └─ 1 cadena n8n + FAB + bucle
      ├─ 2 bloqueo (01 + toques de motor)
      ├─ 3 correr / volar (motor)
      └─ 4 bibliotecas + Argon autónomo
           └─ 5 historial (usa 2 y 4)
                └─ 6 módulos de adaptabilidad (prioridad)
                     └─ 7 barrido de canal
                          └─ 8 pruebas A y B (GPU + Argon, con tope aprobado)
```

2 y 3 pueden ir en paralelo en el repo tras 0. 4 puede empezar su diseño en paralelo, pero no llama Argon/GPU hasta que 1 deje FAB activo. 8 no empieza sin 1, 2, 3, 4, 5 y 7 (6 puede dejar FALTAS etiquetadas).

### 9.2 Agentes Cursor (`blender-1`)

| Lote | Contenido | Cuándo |
| --- | --- | --- |
| C1 | Inventario de hardcodes, tests de `m3_traductor` / router (correr, volar) | Fase 0–3 |
| C2 | Bloqueo: prompts, `cubo01`, `continuidad_bloqueo`, `m1`, aviso del planificador | Fase 2 |
| C3 | Cablear `vuelo_alas` + `adaptar` + clips de correr/trotar | Fase 3 |
| C4 | Worker: investigación genérica, poses, catálogos `_comun`, sin EJEMPLO_MANUAL | Fase 4 |
| C5 | Historial 3D + `m1` aplica estado + `reparar` | Fase 5 |
| C6 | Un módulo de adaptabilidad por agente (efectos, vehículos, …) | Fase 6 |

Lo que no está en ese repo (JSON de n8n, a veces fábricas/cajas en el 213) lo hace el agente del 213 con el mismo contrato de respaldo, o se sube primero al repo si Ricardo lo autoriza.

### 9.3 Estimación de gasto **solo para la prueba final** (fase 8), a pedir después

Cifras de orden de magnitud, según costos ya vistos (01/SB ~0,2–0,75 por llamada; GPU ~0,15–0,50 por plano/escena; investigación de no humano ~0,64; poses de una criatura ~3; recetas de un grupo de objetos ~0,2–0,4). **No se gasta ahora.**

| Prueba | Argon (orden) | GPU (orden) | Nota |
| --- | --- | --- | --- |
| A. Rehacer 01 + SB + filmación de un capítulo corto (p. ej. 9 escenas ya moldeadas) | ~US$3–8 | ~US$3–8 | Depende de cuántos 01 se redirijan y de si el SB se reusa |
| B. Canal nuevo, 2 escenas, 2 personajes (1 no humano), 1 set, 1 objeto FALTA, 1 variante rota | ~US$4–10 (ficha + receta + poses + 01 + SB) | ~US$1–3 | Es la prueba cara de autonomía |
| Margen de `adaptar()` / correcciones | ~US$1–3 | — | 4 intentos × 0,75 tope teórico; en la práctica menos |

**Tope a pedir cuando se llegue a la fase 8 (propuesta):** US$20 Argon + US$15 GPU para A+B, con ledger y parada a 90 % del tope. Si Ricardo quiere solo A primero, se pide un tope menor.

Las fases 4–6, si se prueban con jobs reales antes de la 8, necesitan **topes de lote propios**, aprobados uno a uno (la fábrica ya tiene `tope_lote_usd` y `tope_por_llamada_usd=0,75`).

### 9.4 Esta pasada

Argon: **US$0**. GPU: **US$0**. Producción: **sin cambios**.

---

## 10. Decisiones que Ricardo debe tomar antes (o al arrancar cada fase)

1. **Escena previa faltante (bloqueo e historial):** ¿se hereda la última que exista (con `gap:true`) o se para? Recomendación: **parar** en producción, heredar solo en modo prueba.
2. **Correr:** la fase 3 lo implementa de verdad (recomendado; él pidió función primero). Confirmar que no se queda en el cap de 1,6 m/s.
3. **Calidad de «forma orgánica»:** se acepta el tope Star (primitivas + ficha), sin TRELLIS. Si más adelante se quiere escultura, es otro proyecto.
4. **Aprobación humana de cada hoja/variante nueva:** ¿Ricardo sigue aprobando cada `hoja_lista`, o la revisión técnica basta para personajes/objetos de prueba y él solo ve un lote? Recomendación: técnica automática en el canal de prueba; en un canal real, él aprueba hasta fiarse.
5. **Autonomía de gasto:** `argon_enabled` ya está en `true`. ¿Qué tope de lote diario se pone al dejar que el worker llame Argon solo? Recomendación: tope explícito por fase, nunca ilimitado, aunque «el costo no sea la prioridad».
6. **Webhook abierto** del flujo de producción: ¿token, o solo disparo manual?
7. **Tope GPU de n8n vs `config_motor.json`:** ¿el de Entradas manda cuando es más bajo? Recomendación: sí.
8. **Prueba B:** ¿acepta un canal sintético corto (2 escenas, animales realistas o fantasía), o quiere un canal suyo concreto?
9. **¿Arrancamos la fase 0+1 al aprobar este plan?** Sin eso no se toca el 213 ni n8n.
10. **Islas T317/02N:** se deja el recomendado (no reactivar, no borrar). Confirmar.

---

## 11. Bloqueos que hoy impiden la prueba final (para no olvidarlos)

1. PROM·FAIL en la cadena de sellos (H1).  
2. SB y motor antes del 01 (H2).  
3. Sin FAB en producción: no hay construcción 3D autónoma desde el flujo.  
4. Sin bucle ni unión reales en producción.  
5. Falso «listo ✔» y GPU de este flujo nunca probada.  
6. SB de pago bloqueado (manifiesto).  
7. Hardcodes Génesis / escena 11 / CAM_T3.  
8. Investigación de no humanos no cableada; ficha Argon de Piquito no publicada.  
9. `correr`→`caminar`; vuelo y `adaptar()` huérfanos.  
10. 01 apiña y no ve la escena anterior ni el historial.  
11. Trabajo útil dejado en copias apagadas (COPIA FABRICAS, PRUEBA bucle) — este plan lo **trae** al flujo vivo, no crea otra copia.

Cuando las fases 1–5 y 7 estén aceptadas, la fase 8 tiene sentido. Antes, «una prueba completa» mediría sobre todo los rotos de n8n, no el motor autónomo.
