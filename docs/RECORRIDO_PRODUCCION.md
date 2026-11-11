# Recorrido del flujo de producción n8n: `debwaH9svFMoTnOf`
**«COPIA LIMPIA · MYIA capítulo desde 0 (2-nov-2026)»**. Servidor 213, n8n `myia-taller-n8n`.

Lo hizo Inmi el 11-nov-2026, entre las 7:10 y las 8:00 a. m. (hora de Bogotá). **Solo leí:** no ejecuté, no guardé, no activé ni edité nada, y el gasto fue US$0. No abrí ni copié ninguna clave.

## 0. Datos generales
- **Estado:** el flujo está **ACTIVO**. Su última modificación fue hoy a las 5:59 a. m. (Bogotá).
- **Tamaño:** 594 piezas. De ellas, 77 son notas adhesivas y **517 son nodos que trabajan**: 167 de código, 140 SSH al 213, 61 decisiones «si/no», 17 esperas o formularios, 21 paradas de error, 59 «pasos vacíos» y otras.
- **Disparadores:** 21 entradas en total.
  - La principal es **«Inicio»**, que es manual.
  - El webhook «TEST · ▶ cotizar por webhook» entra al mismo lugar: pasa por «Entradas» y fija `modo=cotizar`.
  - Hay 3 formularios: «Cargar personajes», «Leer hoja» y «3b cargar guion».
  - Las otras 15 son ramas manuales de apoyo: FC, SELLO PJ/OBJ/ESTILO, CUBO, VAR, ADN, VER, V, 06, PROM y ESC.
- **De «Inicio» salen 296 nodos.** Ese es el camino del capítulo.
- **79 nodos no tienen ninguna entrada que los dispare** (islas). Están en la sección 3.
- **Orden de ejecución «v1»:** cuando un nodo tiene varias salidas, n8n corre primero la rama que está **más arriba en el lienzo** y la termina completa antes de pasar a la siguiente. Esto importa para varios hallazgos.
- **Ejecuciones reales de este flujo:**
  - **#56** (5-nov, 5:39 p. m.): solo corrió el formulario 3b. Salió bien.
  - **#39 a #55** (2-nov): todas terminaron en error. La última, la #55, se detuvo en «4a1b · leer ficha de escena», con este mensaje: «no hay ramas/moldes».
  - **Desde el recableado t846u (orden 9) y el enganche cine_v1 de hoy, el flujo de producción no se ha corrido de punta a punta.**
  - Los enganches se probaron en copias de prueba: #60 y #61 (hoy, 6:01 a. m.) salieron bien.
  - La copia de prueba «PRUEBA bucle cine_v1» (#63) estaba **corriendo** hoy desde las 6:22 a. m. No la toqué.
- **Compuertas del servidor (213):** hoy **no hay ningún archivo `HABILITAR_PAGO_*` abierto** en `/opt/myia-taller-n8n/cajas/`; solo quedan copias marcadas `.usado` o `.detenido`. Por eso, en este momento ningún paso de Argon ni de Nano Banana del Paso 00 puede cobrar, aunque n8n lo pida.
- **La excepción es el motor GPU**, que **no usa** archivo HABILITAR. Ver la etapa 13.

### Cómo se protege el dinero (patrón que se repite)
1. **Cotizar gratis:** el SSH corre `paso00_cadena cotizar …` y no llama a Argon.
2. **«leer cotización»:** decide la ruta, que puede ser `repetido`, `seguir` (gratis o ya hecho), `aprobar` (con `modo=pagar`) o `preaprobado` (cuando el paso aparece en `pagar_pasos` con `tope_pasos_usd`).
3. **✋ Formulario «Aprobar precio»:** n8n se detiene y espera a que Ricardo elija «Aprobar».
4. **VER⇢ chequeo pre-pago:** es un chequeo en seco con un manifiesto. Si falla, el flujo se detiene con «FAIL ⛔ no paga».
5. **▶ Llamar (pago):** el servidor vuelve a exigir el archivo HABILITAR_PAGO_* con monto, más `--ok` y `--aprobado`, y anota en el ledger antes de pagar.

---

## 1. La cadena principal, en orden

### Etapa 1 · Entrada y canal
- **Nodos:**
  - `Inicio` (o el webhook TEST)
  - `Entradas (canal, capítulo, modo)`
  - `Ruta · ¿empezar desde 01?`
- **Función:** fijar los datos del trabajo.
- **Recibe:** nada. Por el webhook puede llegar `?desde=00|01`.
- **Entrega:** estos valores fijos:
  - `canal=cn-los-guardianes-de-la-9fb323be`
  - `capitulo=1`, `escena=1`
  - `modo=cotizar`, `tope_usd=0`
  - `pagar_pasos=""`, `tope_pasos_usd=0`
  - `seguir_a_01=true`, `motor_escena=cine_v1`
  - `desde` (00 por defecto)
- **Ruta:**
  - Con `desde=01`: va a «00 · ¿hecho?» y salta el Paso 00.
  - Con `desde=00`: va a «1. Crear canal» y también a «Cargar personajes · revisar».
- **Gasto:** ninguno.
- **Estado:** probado (corrió en la #55 y en las pruebas de hoy).

### Etapa 1b · Atajo «desde 01»
- **Nodos:**
  - `00 · ¿hecho? cotizar base (gratis)`
  - `00 · ¿hecho? cotizar personajes (gratis)`
  - `00 · verificar cubo 00 hecho`
- **Función:** comprobar en el disco que el Paso 00 ya está hecho.
- **Entrega:** `cubo00_ok`, canal, capítulo y la lista de pasos hechos. Si falta algo, se detiene con un error claro.
- **Gasto:** ninguno.
- **Estado:** el código es correcto. No vi una ejecución en producción.

### Etapa 1c · Lista de avisos de personajes
- **Nodos:**
  - `Cargar personajes · revisar (gratis)`
  - `… · avisos (armar)`
  - `… · 🧍 lista de avisos`
- **Función:** revisar las imágenes que ya están cargadas. Marca las repetidas, las que no tienen imágenes y las que faltan o están sin aprobar.
- **Entrega:** una página HTML con los avisos. Es un callejón final a propósito: solo sirve para ver.
- **Gasto:** ninguno.
- **Estado:** probado (#55).

### Etapa 2 · Configurar canal y guion
- **Nodos:**
  - `1. Crear canal` y `2. Configurar canal` (pasos vacíos)
  - `2 · fijar muestra de estilo (gratis)`
  - `2 · leer estilo`
  - `3a. Planear con Argon (pago)`, que es un paso **vacío** y no llama a nadie
  - `3b. Cargar mi guion (gratis)`
- **Función:** sellar la imagen de estilo del canal y comprobar que el guion oficial existe.
- **Entrega:** si el estilo quedó apuntado y el archivo existe, y si el guion está.
- **Ojo:** 3a y 3b llegan **los dos** a «4. Mapa 00». Por eso el paso 4 se dispara dos veces; la segunda vez entra por la ruta «ya pasó en esta corrida».
- **Gasto:** ninguno.
- **Estado:** probado (#55).

### Etapa 3 · Mapa 00 base (Argon)
- **Nodos:**
  - `4. Mapa 00 (Argon, pago)`. Su nombre dice «pago», pero en realidad **solo cotiza**.
  - `4 · leer cotización` y `4 · ¿cómo sigue?`
  - `4 · ✋ Aprobar precio` y `4 · ¿aprobado?`
  - `VER⇢4 · chequeo pre-pago`, `VER⇢4 · leer` y `VER⇢4 · ¿PASS?`
  - `4 · ▶ Llamar Argon (pago)` y `4 · leer resultado`
  - `4 · listo ✔`
- **Función:** Argon lee el guion y saca la lista de personajes, lugares y objetos.
- **Entrega:** la lista base del capítulo, guardada en disco. En n8n quedan `pasos[]`, `a_pagar_peor_caso_usd` y `usd_real_total`.
- **Gasto:** Argon (Vertex).
- **Compuerta:** cotización, ✋ formulario o `pagar_pasos`, VER⇢4 (manifiesto `prepago_base_…`, que sí existe) y HABILITAR_PAGO_00 en el servidor.
- **Estado:** probado (#55). La llamada pagada corrió el 2-nov.

### Etapa 4 · Objetos (4p → 4b → 4b1 → 4c → 4c1 → juntos)
- **Nodos:**
  - `4p. Argon profundiza (pago)`, que en realidad corre `cotizar objetos` (2b), con su `leer`, su `¿cómo sigue?`, su ✋, `VER⇢4p` y `▶ Llamar`
  - `4b. Objetos de la historia` y `4b1. Investigar objetos + prompt`, con su cotización, ✋ y `VER⇢4b1`
  - `4c. Objetos del lugar` y `4c1. Investigar objetos del lugar`, con su cotización, ✋ y `VER⇢4c1`
  - `4b1+4c1 · ▶ Llamar Argon JUNTOS (pago)` y `4b1+4c1 · leer resultado`
- **Función:** estudiar cada objeto del personaje y del escenario: su forma, tamaño y material.
- **Entrega:** las fichas de los objetos en disco y el prompt de cada uno.
- **Gasto:** Argon.
- **Compuerta:**
  - 4p: cotización, ✋, VER⇢4p y HABILITAR_PAGO_00.
  - 4b1 y 4c1: cotización, ✋ y VER⇢. Después, «JUNTOS» paga solo las cajas cuyo VER⇢ corrió; si no corrió, usa `ok 0` y se salta.
- **Estado:**
  - 4p: probado (#55).
  - 4b → JUNTOS: **no probado** con el cableado actual.

### Etapa 5 · Pintar objetos en fondo blanco (Nano Banana)
- **Nodos (4b2 y 4c2 son iguales):**
  - `4b2. Pedir objetos (Nano Banana, pago)`, que en realidad **solo arma el pedido**, y `4b2 · leer`
  - `P1 cotizar pintura`, `P2 ¿pintar?`, `P3 ¿pagar pintura?`, `P4 ✋ Aprobar pintura`, `P5 ¿aprobada?`, `P6 ▶ Pintar (pago)`, `P7 leer` y `P8 pintura lista`
  - `4b3. Ver objetos` y `4b3 · leer`, con su galería 🖼
- **Función:** pintar cada objeto, con todas sus vistas, sobre fondo blanco.
- **Entrega:** imágenes en disco y una galería HTML. Además, `para_sello[]`, la lista de lo que pasa al sello.
- **Gasto:** Nano Banana.
- **Compuerta:** cotización, ✋ y HABILITAR_PAGO_4A5 en el servidor. **No hay VER⇢** antes de P6.
- **Estado:** no probado con el cableado actual.

### Etapa 6 · Sellar el ADN de lo pintado (SELLO OBJ)
- **Nodos:**
  - `00 → SELLO OBJ · lo pintado pasa al sello` y `¿modo pagar?`, más su ✋ si el modo es pagar
  - `SELLO OBJ · 1b armar pedido`
  - `2 cotizar ADN · Maestro 03` (cubo_fijo extraer) y `2a leer cotización y tope`
  - `¿ADN en disco o pago habilitado?`
  - `3▶ sello_pago adn` y `3a leer ADN`
  - `4 validar (5 bloques)` y `4a ¿pasa?`
  - `4b SELLAR FIJO` y `4c VER sellado`
  - `4d resumen`
- **Función:** fijar el ADN, que es la descripción fija, de cada objeto o escenario pintado.
- **Entrega:** el ADN sellado en `cajas/cubo_fijo/` y un resumen (`sellados`, `ids`, `versiones`).
- **Gasto:** Argon (sello_pago), unos US$0,005 por imagen.
- **Compuerta:** cotización, ✋, `habilitar_pago` de «SELLO OBJ · 1 entrada» (hoy cerrado) y HABILITAR_PAGO_ADN en el servidor. Si el ADN no está en disco y el pago está cerrado, el flujo **para a propósito** en «PARA: pago cerrado».
- **Recibe:** se dispara **3 veces**, desde `4b3 · leer`, `4c3 · leer` y `4a7 · leer`.
- **Sigue a:** `CUBO · 1 cargar catálogo` → `CUBO · 2 VER` → `CUBO · 3 ensamblar FIJOS` → `PROM 10a/10a2/10b/10c` → `11…18`. Ver el hallazgo **H1**.
- **Estado:** no probado con el cableado actual.

### Etapa 7 · Escenarios (4e → 4a → 4a0 → 4a1 → 4r)
- **Nodos:**
  - `4b3+4c3 · Merge → 4e`
  - `4e. Argon escenarios (pago)`, que en realidad **cotiza** (2a), con su `leer`, su `¿cómo sigue?`, su ✋, `VER⇢4e` y `▶ Llamar`
  - `4a. Escenarios`
  - `4a0. Reconocer en la biblioteca`, con `✋ Confirmar lugar` si hay dudas; esta parte vuelve sobre sí misma hasta resolverlas
  - `4a1. Investigar escenarios`, con su cotización, ✋, `VER⇢4a1` y `▶ Llamar`
  - `4r. Resolver dudas` y `4r · aplicar decisiones`
- **Función:** Argon diseña el lugar sin inventar muebles y ubica cada objeto en el plano. Antes se revisa si el lugar ya existe en la biblioteca del canal.
- **Entrega:** el escenario en disco (`escenario.json`, emplazamientos) y las decisiones de 4r.
- **Gasto:** Argon (4e, 4a1 y, en el futuro, 4r).
- **Compuerta:** cotización, ✋, VER⇢ (los manifiestos `prepago_escenarios_…` y `prepago_investigar_escenarios_…` existen) y HABILITAR_PAGO_00. 4r solo cotiza; su pago no está habilitado.
- **Estado:**
  - Hasta 4a1: probado (#55, 2-nov), con el orden anterior.
  - 4e y 4r: no probados con el cableado actual.

### Etapa 8 · Blender, el molde 3D (4a2 → 4a3)
- **Nodos:**
  - `4a2. Blender arma escenarios (gratis)` y `4a2 · leer`
  - `4a3. Ver moldes`, con su galería 🖼 y sus imágenes
- **Función:** armar el escenario en 3D en el 213. Ahí está el «★ Hueco Star», que todavía **no está integrado**.
- **Entrega:** el `.blend` del molde y renders de la planta y de las cámaras.
- **Gasto:** ninguno (CPU del 213).
- **Estado:** no probado con el cableado actual. La #55 se detuvo antes de llegar.
- **Ojo:** `4a2 · leer` también dispara `ESC · escenario creado`. Ver el hallazgo **H3**.

### Etapa 9 · Escenario vivo (4a4 → 4a1b → 4a5 → 4a6 → 4a7)
- **Nodos:**
  - `4a4. Prompts escenario vivo (Argon, pago)`: **solo cotiza**; el pago está cerrado sin HABILITAR_PAGO_4A4.
  - `4a1b · armar ficha de escena`, que entrega `escena_nivel2.json`.
  - `4a5. Pintar escenarios (Nano Banana)`, con los pasos P1 a P8.
  - `4a6. Ver escenarios + recorte`.
  - `4a7 · Guardar escenario aprobado` (biblioteca guardar).
- **Función:** escribir las descripciones del lugar y pintarlo con la utilería adentro, sin personajes.
- **Entrega:**
  - La ficha de escena de Nivel 2. Los campos que faltan quedan como «FALTA».
  - Las pinturas del escenario.
  - El escenario guardado en la biblioteca.
- **Gasto:** Argon (4a4, cerrado) y Nano Banana (4a5).
- **Compuerta:** 4a4 tiene HABILITAR_PAGO_4A4. 4a5 tiene ✋ y HABILITAR_PAGO_4A5, **sin VER⇢**.
- **Estado:**
  - 4a1b: **roto en la #55** («no hay ramas/moldes», porque 4a2 no había corrido antes con el orden viejo). El orden nuevo, con 4a2 primero, debería arreglarlo, pero no está probado.
  - El resto: no probado.

### Etapa 10 · Personajes (5)
- **Nodos:**
  - `5. Personajes`, que en realidad cotiza 2c
  - `5 · leer cotización`, `5 · ¿cómo sigue?`, su ✋ y `VER⇢5`
  - `5 · ▶ Llamar Argon (pago)`
  - `5 · listo ✔`
- **Función:** preparar las fichas de personajes del capítulo. Los personajes **nunca se generan**: se cargan a mano.
- **Entrega:** las fichas en disco.
- **Gasto:** Argon.
- **Compuerta:** cotización, ✋, VER⇢5 y HABILITAR_PAGO_00.
- **Estado:** probado (#55). En esa corrida quedó «ya hecho».

### Etapa 11 · Fin del Paso 00
- **Nodos:**
  - `Fin del Paso 00 · ¿seguir a 01?`
  - `Fin · pasar una sola vez`
  - `Paso 00 terminado ✔`
- **Función:** pasar a la etapa 01 **una sola vez**, cuando ya corrieron estas 4 ramas: `4a6 · leer`, `4b3 · leer`, `4c3 · leer` y `5 · listo ✔`.
- **Entrega:** `{seguir:true}`. Si falta alguna rama, no entrega nada (`[]`).
- **Gasto:** ninguno.
- **Estado:** no probado. Ver el hallazgo **H8**.

### Etapa 12 · 01, Argon dirige la escena
- **Nodos:**
  - `01. Argon dirige la escena (entrada)`
  - `01 · cotizar dirección (gratis)` (ver cubo 01) y `01 · leer`
  - De `01 · leer` salen tres ramas, que corren en este orden:
    1. `01e · dirección con eventos o112`, que solo muestra.
    2. **`SB · cotizar storyboard`**, que lleva a las etapas 13 y 14.
    3. `01 · P1 ¿dirigir? (cotización exacta)` → `P2 ✋ Aprobar dirección` → `P3 ¿aprobada?` → `P4 ▶ Dirigir (Argon, pago)` → `P5 leer dirección` → `01 · revisar y guardar (gratis)`.
- **Función:** Argon dirige cada escena: acción, beats y quién está en cuadro.
- **Entrega:**
  - La cotización: por ejemplo, 9 de 9 escenas por US$4,03 en el peor caso (dato de la #62, hoy).
  - Por cada escena: `ya_dirigida`, el escenario y los personajes en cuadro.
  - Después del pago, la dirección queda guardada.
- **Gasto:** Argon (P4).
- **Compuerta:** cotización, ✋ y HABILITAR_PAGO_01 en el servidor. **No hay VER⇢** antes de P4.
- **Estado:** la cotización está probada (#62). P4 no se probó dentro del flujo. Ver el hallazgo **H2**, sobre el orden.

### Etapa 13 · SB, el planeador de storyboard
- **Nodos:**
  - `SB · cotizar storyboard (gratis)` y `SB · leer cotización`
  - `SB · ¿con pago? (tope > 0)`. Si `tope_usd` es mayor que 0, va a `SB · ✋ Aprobar precio` → `SB · ¿aprobado?` → `VER⇢SB` → `SB · ▶ correr storyboard (pago)` → `SB · leer corrida`.
  - `SB · validar storyboard (gratis)` y `SB · leer validación`
  - `SB · traducir cámara a Blender (gratis)` y `SB · leer traducción`
- **Función:** planear las tomas de la escena (texto y JSON) y traducir las cámaras al formato de Blender.
- **Entrega:** el storyboard validado y las cámaras traducidas, en `stdout` JSON. La escena sale de `Entradas.escena`.
- **Gasto:** Argon (SB correr).
- **Compuerta:** `tope_usd>0`, ✋, VER⇢SB (manifiesto `storyboard_esc<N>.json`, **que no existe**; ver el hallazgo H6) y HABILITAR_PAGO_SB.
- **Estado:** la cotización está probada en la copia #62. La traducción aparece «stub» en las pruebas #60 y #61, así que no está probada de verdad dentro del flujo.

### Etapa 14 · Interruptor del motor de la escena
- **Nodo:** `ESCENA · ¿motor cine_v1? (interruptor)`.
- **Función:** elegir el motor.
  - Si `motor_escena` es `cine_v1` (o está vacío), va al **motor unificado** (MU).
  - Si es otra cosa, por ejemplo `v9`, va al camino viejo.
- **Estado:** probado en las copias #60 (v9) y #61 (cine_v1).

#### 14A · Motor unificado cine_v1 (MU)
Los pasos van en este orden:

1. **`MU · preparar motor unificado (gratis)`**
   - Corre `motor_unificado preparar --canal --capitulo --escena` en el 213, solo con CPU.
   - Hace los moldes, el traductor de movimiento, el inventario y el planificador A*+RVO2.
   - Entrega: `id` de la corrida, `estado=OK_sin_gpu`, `faltantes[]`, `avisos[]`, `personajes[]` y `escenario`.
   - Probado (#61): 6 personajes, 0 faltantes y 3 avisos de objetos sin molde o provisionales.
2. **`MU · leer preparación`** → **`MU · ¿moldes completos?`**
   - Exige `ok=true` y 0 faltantes.
   - Si no se cumple, va a `✋ faltan moldes o datos (no corre GPU)`.
3. **`MU · ¿se filma de verdad?`**
   - Exige que `modo` sea `real` o `pagar` **y** que `tope_usd` sea mayor que 0.
   - Si no se cumple, va a `MU · cotizar: no se lanza GPU`, con US$0. Probado (#61).
4. **`MU · ▶ correr motor en GPU (RunPod, topes del motor)`**
   - Corre `motor_unificado correr` y responde enseguida con `estado=lanzado`, `id` y `topes`.
   - El motor hace por dentro: una llamada a Argon por escena (sb3d), un pod de RunPod, Kimodo, Blender, los videos y apagar el pod.
   - Gasto: **GPU de RunPod y Argon**, unos US$0,53 por escena según la nota.
5. **`MU · leer lanzamiento`** → **`⏳ esperar 5 min`** → **`MU · ver estado y videos`** → **`MU · leer estado`** → **`¿sigue en curso? (máx 18 vueltas)`**
   - Esta parte se repite cada 5 minutos, hasta 90 minutos.
6. **`MU · resultado + videos de revisión`**
   - Entrega: `estado`, `revision_ok`, `videos[]` (REVISION_GRANDE_1920x1080.mp4, final_camara_sb.mp4, lateral, planta y amplia) y `gpu{pod_id, costo}`.
7. **`ERR · SSH MU`**
   - Recibe cualquier error de SSH de los pasos de MU y **lo manda a «listo ✔»**. Ver el hallazgo H5.
8. **`ESCENA · listo con cine_v1 ✔`**: es el final, y **no sigue a ningún otro paso**.

- **Topes reales del motor** (están en `config_motor.json` y no los pone n8n):
  - US$1,5 por trabajo y US$8 en total para el motor. Ya van US$3,37 gastados según el ledger, con 25 entradas.
  - Bolsa compartida de US$50 y saldo mínimo de RunPod de US$5.
  - Máximo 5700 segundos y hasta unos US$0,80 por hora.
  - La autorización es un texto fijo en la configuración («Ricardo t1010u…»).
- **Interruptor de apagado:** el archivo `entrada_n8n.off`, que hoy **no existe**. Es decir, el motor está encendido.
- **Estado:**
  - Preparar y la ruta de cotizar: probados (#61).
  - La ruta con GPU: probada **solo en la copia MUcineV1escena01** (#59, anoche a las 10:44 p. m.). Terminó en estado OK con `revision_ok=false`. **Dentro de producción no se ha probado.**

#### 14B · Camino viejo v9 / T317
- **Nodos:**
  - `Armar tramo de escena (gratis)` y `Armar tramo · leer`. Usan una credencial aparte, `ab_motor_ako` (usuario n8nab).
  - `02T · traducir entrada T317 (gratis)` (motor_v9 traducir)
  - `02T · validar esquema y faltantes` y `02T · ¿entrada completa?`. Si no está completa, va a `02T · detener y reportar faltantes`.
  - `02. Blender anima escenas (gratis)` (motor_v9 armar)
  - `02 · resultado T317`, que es el **final**.
- **Gasto:** ninguno (según la nota, no usa Argon ni GPU).
- **Estado:** «Armar tramo» se probó con un stub (#60). Del resto no hay prueba en producción.

### Etapa 15 · Pasos 11 a 18 (pintar, animar, unir), que hoy son pasos vacíos
- **Nodos:**
  - Lado PROM: `PROM · 10a map tira→cubo` → `10a2 CUBO FIJO + Maestros` → `10b ensamblar director` → `10c VER` → `PROM · VER ok?` → `PROM · OK → listo para 11 cotizar`
  - Pasos numerados: `11. Pintar con Nano Banana (pago)` → `12. Revisión` → `13. Aprobación de Ricardo` → `14. Argon plan de animación` → `15. Animar (pago)` → `16. Ver videos` → `17. Unir por escena` → `18. Unir todas las escenas`
- **Función que se busca:** pintar, animar y unir el capítulo.
- **Realidad:** 11, 13, 14, 15, 16, 17 y 18 son **pasos vacíos** que no hacen nada. Solo trabajan las galerías (12 y 16), `12b · animatic` y `14 · encadenado o corte`, que solo leen o cotizan.
- **Ojo:** **a esta parte solo se llega desde CUBO/PROM**, es decir, desde la rama de sellos del Paso 00. No se llega desde el motor de la escena (ver H1).
- **Gasto hoy:** ninguno.
- **Estado:** no construido.

---

## 2. Ramas de apoyo (fuera de «Inicio»)

| Rama (disparador) | Función | Entrega | Gasto y compuerta | Estado |
|---|---|---|---|---|
| **3b · formulario cargar guion** (5 nodos) | Sube un `.txt` o `.md` al 213 como guion oficial | El guion en studio.db y una página de avisos | Ninguno | **Probado (#56, 5-nov)** |
| **Cargar personajes · formulario** (49 nodos, junto con ADN crear PJ) | Subir a mano las imágenes de cada personaje y versión. Sigue a ADN PJ + voz → PUENTE → CUBO | `personajes/<pj>/<versión>/refs/`, `personajes.json` y el perfil con la voz | Ninguno (stubs) | No probado |
| **Leer hoja · formulario** (9 nodos) | La IA lee una hoja de personaje o separa sus versiones | Campos en `personajes.json`, SIN APROBAR | Argon. Compuerta: HABILITAR_PAGO_HOJA más el monto y quién aprueba | No probado |
| **SELLO PJ** (21 nodos propios) | Hoja de Fase 1 y ADN de Fase 2 del personaje, Maestro 02, y luego sellar como FIJO | ADN sellado en cubo_fijo | Argon, unos US$0,139 por PJ. Compuerta: sello_pago con HABILITAR_PAGO_ADN | Corrió fuera de n8n el 2-nov |
| **SELLO ESTILO** (17 nodos) | ADN del estilo del canal (Maestro 05) | Sello de estilo por canal | Argon, unos US$0,005. Misma compuerta | No probado aquí |
| **SELLO OBJ · Inicio** | Igual que la etapa 6, pero manual | — | Igual | — |
| **FC · fondo cubemap** (23 nodos) | Fondo 360: agrupar, cubo gris, cotizar, pintar, proyectar, profundidad, reproyectar y equirect | Las caras del cubo y la «Imagen 1 fondo» por toma | Nano Banana. Compuerta: `tope>0`, VER⇢FC y HABILITAR_PAGO_FC | **Bloqueada a propósito:** `--origen` está pendiente (nota «FC · --origen pendiente») |
| **ESC · crear escenario → FC entorno** | Cubemap gris del set permanente, solo el set | Renders grises | Ninguno | Ver H3 |
| **CUBO / VAR / PUENTE / PROM demo** | Catálogo del cubo fijo, objeto único (campo de fuerza) y prompt del director | Prompt del director con 8 secciones | Ninguno (Argon cerrado) | Funcionan en seco |
| **VER pre-gasto / VER manifiestos** | Chequeos en seco de manifiestos (sha256, orden y canal sellado) | PASS o FAIL | Ninguno | Funcionan en seco |
| **ADN · Voz**, **06 · Clasificar cámara**, **V · Propagar / Argon video prompt** | Demos en seco: voz, quieta o 3D fuerte, y prompts para Veo | Datos de demostración | Ninguno. «VER · OK Ricardo» bloquea siempre | Stubs |
| **TEST · sonda** | Sondas de reparación | — | — | Desactivado |

---

## 3. Islas: nodos que nada dispara (79)
- **Cubos 02a a 10, completos (unos 45 nodos):**
  - Nodos: `02a. Ver videos de Blender`, `03. Argon revisa coherencia (pago)`, `04. Aplicar correcciones`, `04a. Validación del usuario`, `05. Argon plan de tomas (pago)`, `06. Blender saca las tomas`, `07. Motor 1 colorea`, `08. Argon prompts por viñeta`, `09. Validador`, `09a`, `10. Armar tiras de 8`.
  - También sus nodos de lectura y de vueltas: `03 · contar vueltas`, `09 · ¿otra vuelta?` y otros.
  - Más `11 · híbrido cotizar`, `11 · ¿listo para pintar?` y `11 · PARADO`.
  - El marco «10 · Dirigir y plan de tomas (01–05)» los presenta como parte de la cadena, **pero hoy no están conectados**. De 01 se salta directo al storyboard.
- **02 viejo, o98, 02b, 02c y 02v:** el motor viejo y sus pruebas.
- **02N completo (20 nodos):** el motor de Ako, desactivado y sin entrada a propósito, según la nota «T317 · ruta única».
- **`4b1 · ▶ Llamar Argon (pago)` y `4c1 · ▶ Llamar Argon (pago)`:** los reemplazó «JUNTOS». Quedaron sueltos pero no estorban.
- **`4a7 · ✋ ¿Guardar en la biblioteca?` y `4a7 · ¿guardar?`:** desactivados. Hoy 4a7 guarda sin preguntar.
- **`MOTOR · preparar entrada` y `MOTOR · leer paquete`:** desactivados.

---

## 4. HALLAZGOS (de más grave a menos grave)

**H1. ALTO, rompe la cadena: la rama de sellos dentro del Paso 00 termina en una parada de error.**
- **Nodos:** `SELLO OBJ · 4d resumen` → `CUBO · 1` → `CUBO · 2 VER` → `CUBO · 3 ensamblar FIJOS` → `PROM · 10a` → `10c VER` → `PROM · FAIL` (que es un stopAndError).
- **El problema:**
  - En la cadena principal no corren ni `PUENTE · PJ+voz → CUBO` ni `VAR · 3`, así que `ids_pedidos` queda vacío.
  - Entonces `CUBO · 3` entrega `ok:false` («sin ids»), pero **pasa igual** a PROM 10a, porque entre los dos no hay ningún «¿ok?».
  - `10c` falla por «casting vacío» y `PROM · FAIL` **detiene toda la ejecución**.
- **Cuándo pasa:** por el orden v1, la rama del sello (`4b3 · leer` → SELLO, que está arriba en el lienzo) corre **antes** que `Merge → 4e`. Por eso, en cuanto haya algo pintado y con ADN en disco para sellar, el Paso 00 se cae antes de llegar a escenarios.
- **La misma ruta** la toman `4a7 · leer` y `ESC`.
- **Además:** esta rama empuja hasta los pasos 11 a 18 en pleno Paso 00, antes de que existan tomas.
- **Es una deducción del código; no está probado.**
- **Arreglo propuesto, que no apliqué:** cortar `SELLO OBJ · 4d` → `CUBO · 1` en la cadena principal, o poner un «¿ok?» después de CUBO · 3 que termine sin error.

**H2. ALTO, orden: el storyboard y el motor corren ANTES de que Argon dirija la escena (01).**
- **Nodo:** `01 · leer`. Sus tres salidas corren por altura en el lienzo: `01e`, después `SB · cotizar` (con toda la rama SB → interruptor → MU), y por último `01 · P1 → ✋ → P4 Dirigir`.
- **El problema:** SB, MU y la GPU usan la dirección **que ya está en disco**.
  - En un capítulo nuevo la dirección todavía no existe, así que el storyboard falla o usa datos viejos.
  - Con `modo=pagar`, la GPU podría filmar antes de aprobar y pagar la dirección.
- **Arreglo propuesto:** que SB salga de `01 · P5 leer dirección` o de `01 · revisar y guardar`, o de una compuerta «¿escena ya dirigida?». Hoy la escena 1 de Guardianes aparece como `ya_dirigida: accion_v1`, por eso no se nota.

**H3. ALTO-MEDIO, valores fijos inventados en `ESC · escenario creado`.**
- **El problema:**
  - El nodo trae fijos `escena=11` y `origen=CAM_T3`, y usa como canal de respaldo Génesis (`cn-gnesis-digital-el-de-ed178619`).
  - Lo dispara la cadena principal (`4a2 · leer` y `4a7 · leer`), así que para Guardianes cap. 1 pediría el cubemap de una escena 11 con una cámara CAM_T3 que quizá no existan.
  - Después sigue hacia `CUBO · 1` y cae en H1.
- **Contradicción:** su nota dice «no bloquea la rama principal», pero sí puede bloquearla.
- **Choca con la regla «nunca inventar valores».**

**H4. MEDIO-ALTO, el motor GPU no tiene ✋ ni pasa el tope de n8n.**
- **Nodo:** `MU · ▶ correr motor en GPU`.
- **Lo que hay:** su única compuerta en n8n es `MU · ¿se filma de verdad?`, que exige `modo` real o pagar y `tope_usd>0`.
- **Lo que falta:**
  - No hay formulario ✋ de aprobación con precio.
  - No hay VER⇢ pre-pago.
- **El tope no pasa:** `entrada_n8n.py` solo acepta `--canal`, `--capitulo`, `--escena` e `--id`. Por eso **el `tope_usd` de Entradas no llega al motor**. Si Ricardo pone `tope_usd=0.5`, el motor igual puede gastar hasta US$1,5 de GPU más Argon, que es el tope de `config_motor.json`.
- **La autorización** es un texto fijo en la configuración, no un OK por corrida.
- **Lo que sí protege:** los topes del motor (US$1,5 por trabajo, US$8 en total, saldo de US$5), el ledger antes del pod y que el pod se apaga solo.

**H5. MEDIO, se oculta el error del motor.**
- **Nodo:** `ERR · SSH MU`.
- **El problema:** recibe los errores SSH de preparar, correr y estado, y los manda a `ESCENA · listo con cine_v1 ✔`. La ejecución termina «bien» aunque el motor haya fallado. Es el mismo tipo de «falso OK» que ya se corrigió antes.
- **Un caso parecido:** `MU · leer lanzamiento` no revisa `ok`. Si `correr` responde `ok:false`, por ejemplo por un STOP de tope o porque el motor está apagado, igual espera 5 minutos y consulta el estado con un id vacío.

**H6. MEDIO, el pago del SB dentro del flujo está siempre bloqueado.**
- **Nodo:** `VER⇢SB · chequeo pre-pago`.
- **El problema:** busca el manifiesto `storyboard_esc<N>.json` y en `cajas/ver_prepago/manifiestos/` **no hay ninguno** de storyboard. Cualquier `tope_usd>0` termina en `VER⇢SB · FAIL ⛔`.
- **Riesgo:** es un bloqueo seguro, porque no gasta. Pero al mismo `tope_usd` lo usa MU, así que con `tope_usd>0` la corrida muere en el SB antes de llegar al motor.
- **Además:** `SB · ¿con pago?` mira solo `tope_usd` y no `modo`. Una escena ya hecha también pediría el pago.

**H7. MEDIO, error de copiar y pegar en 4e.**
- **Nodo:** `4e · leer cotización`.
- **El problema:** el código dice `PID='4p'` y los mensajes dicen «Caja 4p». Por eso:
  - `pagar_pasos=4e` **no funciona**.
  - Poner `4p` en `pagar_pasos` **preaprueba también los escenarios**.
  - La suma de lo gastado no cuenta el `4e · leer resultado`.
- **Lo mismo en otros dos nodos:** `VER⇢4e · FAIL` dice «VER bloquea 4p», y el formulario `4e · ✋` dice «escenarios + objetos (2a y 2b)».
- **Lo que lo contiene:** el servidor sigue exigiendo HABILITAR_PAGO_00 y VER⇢4e.

**H8. MEDIO, puede quedarse parado sin avisar.**
- **Nodo:** `Fin · pasar una sola vez`.
- **El problema:** exige que hayan corrido `4b3 · leer` y `4c3 · leer`. Si 4p sale por «ya pasó» o «rechazado», o si 4b o 4c se detienen, nunca llega a 01 y **no deja ningún aviso**: el nodo entrega `[]` y la ejecución termina «bien».

**H9. MEDIO, los pasos 02 a 10 están desconectados y 11 a 18 son pasos vacíos.**
- La cadena real hoy es: Paso 00 → 01 → SB → motor de **una sola escena** (`Entradas.escena`). Al final no se encadenan ni la pintura, ni la animación, ni la unión.
- No hay bucle por escenas en producción. Ese bucle se está probando en las copias «PRUEBA bucle cine_v1», y la #63 corría hoy.

**H10. MEDIO-BAJO, pagos sin VER⇢ previo.**
- `01 · P4 ▶ Dirigir`, `4b2/4c2/4a5 · P6 ▶ Pintar` y `MU · ▶ correr` tienen cotización y ✋ (MU no tiene ✋), más la compuerta del servidor, pero no tienen VER⇢.
- La nota «Conexiones t477u» solo pone VER⇢ en 9 pagos.

**H11. BAJO, el flujo está ACTIVO y su webhook no tiene autenticación.**
- **El problema:**
  - `TEST · ▶ cotizar por webhook` (GET `/webhook/ako-test-cotizar-30bcdb42-limpia`) y los 3 formularios están abiertos, sin clave.
  - Hoy es gratis, porque «Entradas» fija `modo=cotizar` y `tope=0`. Pero cualquiera con la URL dispara la cadena entera, con Blender y el motor en preparar.
  - Si algún día Entradas queda en `pagar` con `tope_usd>0`, la URL podría lanzar GPU sin ✋.
- **Contradicciones:**
  - Las notas «ENTREGA 2-nov» y «3b» dicen «COPIA LIMPIA inactiva / no la activamos sin tu OK», pero hoy está activa.
  - El ajuste `availableInMCP: true` también la expone.

**H12. BAJO, detalles.**
- **Nombres que dicen «pago» y solo cotizan o preparan:** «4. Mapa 00», «4p», «4e», «4a1», «4b1», «4c1», «4b2», «4c2» y «4a5». «3a. Planear con Argon (pago)» es un paso vacío.
- **«4. Mapa 00» se dispara dos veces,** desde 3a y desde 3b. La segunda vez sale por «ya pasó».
- **Si se rechaza el pago, la rama termina sin aviso.** Pasa en `01 · P3 ¿aprobada?`, que no tiene salida para el «no».
- **`Cargar personajes · revisar` arranca junto con «Crear canal»,** que está más abajo en el lienzo, así que corre al final.
- **Regla doble en `entrada_ssh.sh`:** la segunda regla de `motor_v9 preparar|armar`, la que va a `v9_universal_calidad`, nunca se usa, porque la primera ya captura esos comandos.

---

## 5. ¿El orden general es correcto?
**En el Paso 00, sí; en lo que sigue, no.**
- **El Paso 00 sigue el «Orden 9»** aprobado (t846u): base → objetos (2b + 4b1/4c1) → pintar en blanco → SELLO OBJ → escenarios (4e/4a1) → Blender 4a2 → vivo 4a4/4a5 → fin → 01. Personajes va en paralelo.
- **Ese orden se rompe en tres puntos:**
  - (a) La rama de sellos empuja CUBO/PROM y termina en un error (H1).
  - (b) Después de 01, el storyboard y el motor corren **antes** de dirigir (H2).
  - (c) Faltan, desconectados, los cubos 02 a 10, y los pasos 11 a 18 son vacíos (H9).
- **Las protecciones de dinero de Argon y Nano Banana son sólidas.** Cada pago tiene varias capas y hoy no hay ningún archivo HABILITAR abierto.
- **El punto más débil en dinero es el motor GPU (H4).**

## 6. Archivos
- Este informe:
  - En mi computadora: `/workspace/recorrido_n8n_20261111/RECORRIDO_PRODUCCION.md`
  - En tu PC: `…\03_AGENTES\inmi\recorrido_n8n_20261111\RECORRIDO_PRODUCCION.md`
- La lista de nodos, sin claves: `/workspace/recorrido_n8n_20261111/NODOS_PRODUCCION_sanitizado.json`. Son 517 nodos, con su tipo, si están activos, desde qué nodo reciben, a qué nodo entregan, el comando SSH resumido y si pertenecen a la cadena principal.
