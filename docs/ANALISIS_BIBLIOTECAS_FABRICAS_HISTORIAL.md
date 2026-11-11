# Análisis A/B/C — bibliotecas que crecen, alta de formas nuevas e historial de cambios

- **Fecha:** 11 de noviembre de 2026, 08:26 America/Bogota (UTC-5)
- **Actualización:** 11 de noviembre de 2026, 08:59 America/Bogota (UTC-5) — se añade la sección D (validación del paso Argon investiga y crea).
- **Actualización:** 11 de noviembre de 2026, 09:03 America/Bogota (UTC-5) — se añade la sección E (validación del Word t88 contra código).
- **Autor:** análisis de arquitectura (solo lectura)
- **Alcance:** genérico para cualquier canal/escena; evidencia de código (`archivo:línea`); sin parches y sin cambios en el 213, n8n ni el motor.
- **Gasto de esta pasada:** US$0 (no se llamó a Argon, RunPod ni GPU).
- **Motor vivo de referencia:** `cine_v1` en `/opt/myia-motor-unificado/v1_20261110/`.
- **Fábricas:** `/opt/myia-fabricas` (worker `workers_v2_3d`).
- **Biblioteca de moldes 3D:** `/opt/myia-biblioteca`.
- **Flujo n8n de producción inspectado:** `debwaH9svFMoTnOf` (COPIA LIMPIA), volcado sanitizado en `NODOS_PRODUCCION_sanitizado.json`.
- **v9 (solo como origen de las 3 bibliotecas):** `/opt/myia-motor-v9/v9_motor_unico_20261107/MOTOR_UNICO_20261107/`.

---

## 0. Cómo leer este documento

Hay **dos bibliotecas distintas** en el 213. Confundirlas es el riesgo principal de cualquier diseño nuevo:

| Raíz | Dueño de código | Qué guarda hoy | ¿La usa cine_v1? |
| --- | --- | --- | --- |
| `/opt/myia-biblioteca` | `/opt/myia-fabricas/app/biblioteca.py` | Moldes 3D por canal (`personajes/`, `objetos/`, `objetos_usuario/`, `escenarios/`) + `_comun/recetas_star_aprendidas/`. Versionado «nunca borra, solo añade». | Sí. `m1_preparar.py` L4 carga `.../<canal>/personajes/<id>/meta.json` → último `blend`. |
| `/opt/myia-taller-n8n/trabajo/biblioteca` | `/opt/myia-taller-n8n/cajas/biblioteca.py` (orden 62) | Fichas de escenario/objeto de **investigación y pintura** (4a1–4a7), variantes de imagen, `historial/eventos.jsonl`, `estado_vigente`, comando `permanente`. | No. cine_v1 no la abre. |

No son el mismo inode (inodos 550504 vs 3195781). Comparten nombres de canal, no el contrato ni el contenido 3D.

v9 declara otras tres «bibliotecas que crecen» **solo dentro de su propio árbol**, no en `/opt/myia-biblioteca` ni en cine_v1:

1. `movimientos_aprobados`
2. `recetas_aprobadas`
3. `anatomias_propuestas` (documentada; **el archivo no existe**)

---

## A. Dónde deben vivir las 3 bibliotecas que crecen

### A.1 Qué son hoy (solo v9) y en qué estado están

El contrato está en `CONTRATO_MOTOR_UNICO.md` § «Bibliotecas que crecen» y en `motor/GUIA_BIBLIOTECAS_Y_PUENTES.md` L19, L24, L54–56, L127.

| Biblioteca v9 | Ruta actual | Escritor | Lector | Estado real en disco (11-nov-2026) |
| --- | --- | --- | --- | --- |
| Movimientos aprobados | `.../bibliotecas/movimientos_aprobados/catalogo.json` + `bvh/<sha>.bvh` | `catalogos_crecimiento.registrar()` (`catalogos_crecimiento.py` L23–38): exige `metrics.all_passed is True`, origen en `{kimodo,cmu,retarget,video,mixamo,catalogo}`, no pisa un hash ya registrado (`REUSED`). | `reusar()` / `conectar()` (L41–65): se consulta **antes** de volver a generar. `movimientos.seleccionar` (escalera semántica v9) es el consumidor de candidatos. | Schema `motion_catalog_v1`, **1 entrada**. El inventario (`INVENTARIO_CAPACIDADES.json` L166–171) avisa que los clips reales no están aprobados sin prueba técnica. |
| Recetas aprobadas | `.../bibliotecas/recetas_aprobadas.json` | `argon_automatico.py` L33, L70: alta tras validar medidas/malla, con `query_sha256` / `recipe_sha256` / origen / fecha. Mocks no entran a la biblioteca real (L3). | `recetas_proveedor.py` L102; `aplicar_cache_entorno` convierte receta aprobada en prop del constructor (GUIA L123–127). | **1 receta** en la clave `recipes`. |
| Anatomías propuestas | `.../bibliotecas/anatomias_propuestas.json` (GUIA L127; `argon_automatico.py` L33, L70 si `task=='anatomy_review'`) | Argon automático, como **propuesta**, «no sustituyen datos certificados». | Pensado para revisión de anatomía, no para sustituir la ficha sellada. | **El archivo no existe** en `bibliotecas/` (listado del 11-nov: hay `movimientos_aprobados/`, `recetas_aprobadas.json`, `star/`, `kimodo/`, etc.; no hay `anatomias_propuestas.json`). |

cine_v1 **no tiene** `catalogos_crecimiento.py`, ni `recetas_proveedor.py`, ni `argon_automatico.py`. Un `ls` de `/opt/myia-motor-unificado/v1_20261110/motor/` no muestra esos módulos. Hoy esas tres bibliotecas no participan en el pipeline de producción.

### A.2 Relación con activos que ya existen (no son lo mismo)

| Activo existente | Dónde | Qué es | Qué no es |
| --- | --- | --- | --- |
| `indice_clips.json` | cine_v1 `motor/assets/indice_clips.json` | Índice **estático** de mocap (incluye `trotar`). Lo consume `motor_blender.py` por umbral de velocidad, no un catálogo que crezca. | No es `movimientos_aprobados`. Meter un clip aquí no lo aprueba ni lo versiona. |
| Poses Piquito v004 | `/opt/myia-biblioteca/cn-los-guardianes-de-la-9fb323be/personajes/gdc-piquito/poses/v004/CANDIDATOS_motor_aptos.json` | **64 candidatos de pose** (lista; campos `id`, `entity`, `provider`, `action`, `duration_s`, `tracks`, `approval_ref`, `license_ref`). Viven ya en la biblioteca de moldes, por personaje y versión. | No es locomoción reutilizable entre canales. Es candidato de pose de un rig concreto. Encaja con «anatomía/poses del personaje», no con el catálogo común de movimientos. |
| `ficha_esqueleto` | `myia-biblioteca/<canal>/personajes/<id>/ficha_esqueleto/vNNN/` | Anatomía **certificable** del molde: la genera `generar_ficha_humana.py` (schema `ficha_esqueleto/v1`, L320) o llega por `ficha_path` (`workers_v2_3d.py` L203–216). El validador corre en el 213, US$0, antes del pod (L239–247). | No es `anatomias_propuestas`. Una propuesta no debe sustituir esta ficha hasta aprobación. |
| `recetas_star_aprendidas` | `/opt/myia-biblioteca/_comun/recetas_star_aprendidas/` (21 JSON) y fuente `/opt/myia-fabricas/assets/recetas_aprendidas/recetas/` | Recetas de objeto **ya compartidas entre canales**. `Biblioteca.buscar_aprobado` (`biblioteca.py` L51–60) las reusa como `aprobado_comun` para `objetos` / `objetos_usuario`. `importar_recetas_comun()` (L91+) las copia al iniciar el servicio (`server.py`). | Es el homólogo real, en producción, de `recetas_aprobadas` de v9. Además, cada pieza de canal puede tener `objetos/<id>/receta/vNNN/recetas_validas.json` (solo APTAS: `workers_v2_3d.py` L319–321). |
| Catálogo Star de 283 formas | `/opt/myia-fabricas/assets/biblioteca_formas.json` → clave `fichas` con **283** entradas (confirmado). `plan_escenario.py` L1–7, L45–60 decide: mapa revisado → token exacto en las 283 → si no, `FALTA`. | Catálogo **fijo** de primitivas paramétricas, no una biblioteca que crece con aprobaciones de receta. | No sustituye `recetas_aprobadas`. Cuando FALTA, la receta (Argon + revisor) es el crecimiento. |

### A.3 Casa propuesta (dentro de la arquitectura actual)

Regla de colocación: **lo genérico y reutilizable entre canales va a `_comun`; lo atado a un rig, un molde o una historia va al canal**. El molde base sigue en `/opt/myia-biblioteca/<canal>/<tipo>/<id>/`. Las tres bibliotecas de v9 no deben quedarse en el árbol de v9 si cine_v1 va a usarlas.

#### 1) `movimientos_aprobados`

- **Casa canónica:** `/opt/myia-biblioteca/_comun/movimientos_aprobados/` (`catalogo.json` + `bvh/<sha>.bvh`), mismo contrato que `catalogos_crecimiento.py` (hash, firma semántica, esqueleto, perfil, `technical_approved`, no borrar).
- **Capa por canal/personaje (opcional, no la casa principal):** `/opt/myia-biblioteca/<canal>/personajes/<id>/movimientos/vNNN/` solo cuando el clip ya está *retargeteado* a ese esqueleto (el caso Piquito es el precedente: recurso por personaje, versionado).
- **Quién escribe:** el motor cine_v1, **después** de la revisión técnica (portar `registrar()`). Origen declarado: kimodo, cmu, retarget, video, mixamo, catálogo. Argon/Kimodo pueden *proponer*; no publican solos.
- **Quién lee y en qué paso:** un selector de movimiento **antes** de generar (equivalente a `conectar()` / `reusar()`), en la etapa de locomoción (hoy: después de `m3_traductor.py` / `m3_router.py`, antes de Kimodo o de elegir clip en `motor_blender.py`). Si hay hit aprobado, no se vuelve a pagar ni a improvisar.
- **Semilla:** `indice_clips.json` se trata como archivo estático de partida. Un clip del índice **no entra** al catálogo creciente hasta pasar la misma revisión técnica (v9 ya lo exigía: `INVENTARIO_CAPACIDADES.json` L166–171).
- **No mezclar** con las 64 poses de Piquito: esas quedan en `personajes/<id>/poses/vNNN/`.

#### 2) `recetas_aprobadas`

- **Casa canónica (ya existe, no inventar una tercera):**  
  - genéricas: `/opt/myia-biblioteca/_comun/recetas_star_aprendidas/<receta>.json`  
  - de un objeto del canal: `/opt/myia-biblioteca/<canal>/objetos/<id>/receta/vNNN/recetas_validas.json`
- **No** mantener un JSON único al estilo v9 (`bibliotecas/recetas_aprobadas.json`) como fuente de verdad de producción.
- **Quién escribe:** fábricas. Flujo ya escrito: corpus vía B gratis → `argon_fabrica` (ledger antes, topes, 20 s, sin reintento) → `recetas_argon.py revisar` → se publica **solo APTAS** (`workers_v2_3d.py` L319–374, L404–407). Compuerta: `argon_enabled` y topes de `config/config.json`.
- **Quién lee y en qué paso:**  
  1. `plan_escenario.py` + `ensamblar.py` modo `star_recetas` (L68–80) al construir el escenario;  
  2. `_objetos_lote()` busca primero receta aprobada, aunque el objeto no se dibuje en el set (L119–127);  
  3. `buscar_aprobado()` en v1, US$0, antes de cualquier construcción (`workers.py` L66–72).
- Relación con Star 283: el catálogo de formas es el primer intento; la receta aprobada es el crecimiento cuando el nombre no cae en las 283.

#### 3) `anatomias_propuestas`

- **Casa de propuestas (nueva, por canal, no en `_comun`):** `/opt/myia-biblioteca/<canal>/personajes/<id>/anatomias_propuestas/vNNN/`. Una anatomía no humana o no plantilla es de ese personaje, no un bien común.
- **Casa certificada (ya existe):** `ficha_esqueleto/vNNN/`. La propuesta **nunca** sustituye la ficha hasta pasar validador + aprobación. Esto es exactamente la regla de v9 («no sustituyen datos certificados», GUIA L127).
- **Quién escribe:** fábricas. Hoy: `generar_ficha_humana.py` para humano; si no es humano, `exit 4` `NO_HUMANO_RUTA_ARGON` (`generar_ficha_humana.py` L186–190) y el worker deja `esperando_pago_argon` (`workers_v2_3d.py` L222–223). También se acepta una `ficha_path` ya investigada (L203–216). Las propuestas de Argon deberían aterrizar en `anatomias_propuestas/`, no en `ficha_esqueleto/`.
- **Quién lee y en qué paso:** el validador de esqueletos (213, US$0) antes del pod; `m1_preparar` solo carga ficha/blend en estado permitido. El motor no debe leer propuestas.

### A.4 Compuerta de aprobación y versionado

Reutilizar el contrato que **ya está** en fábricas, no inventar otro:

1. **Nunca borrar, solo añadir versiones.** `biblioteca.py` L2 y `registrar_version()` L62–91: cada artefacto (blend, receta, ficha, hoja) suma una entrada con `n`, `kind`, `path`, `sha256`, `at`. `_version()` en el worker elige `vNNN` siguiente (`workers_v2_3d.py` L42–44).
2. **Estado de pieza ≠ estado de trabajo.** Publicar deja `hoja_lista` (espera a Ricardo) o `ficha_rechazada` / `stop_altura` / `esperando_pago_argon`. El job puede quedar `listo` y la pieza **no** estar `aprobado` (`workers_v2_3d.py` L7–13, L288–297).
3. **El motor, en producción, solo carga aprobados.** `m1_preparar.py` L14: `ESTADOS_OK = ('aprobado', 'publicado', 'hoja_lista', 'listo')` — Ojo: `hoja_lista` está permitido «modo prueba». L131–136: `--solo_estado_aprobado` restringe a `aprobado`/`publicado`. L163 marca `pendiente_aprobacion` si aún no lo está. **Decisión abierta:** en producción, ¿se exige `--solo_estado_aprobado`?
4. **Revisión técnica automática + aprobación humana.** El precedente v9 es `technical_approved` + métricas (`catalogos_crecimiento.py` L27). El precedente fábricas es validador de ficha US$0 y comparación de altura ±2 % (`workers_v2_3d.py` L239–247, L260–267) **antes** de `approval_ref`. Nada entra al catálogo común ni pasa a `aprobado` sin esas dos puertas.
5. **Índice.** `_comun/indice.json` (schema `bib_comun_v1`) y `<canal>/indice.json` (`bib_canal_v1`) ya existen para localizar piezas. Los tres catálogos deben registrarse ahí, no en un JSON suelto dentro de v9.

### A.5 Qué no hacer

- No dejar las tres bibliotecas solo en el árbol de v9: cine_v1 no las ve.
- No duplicar `recetas_aprobadas` si `_comun/recetas_star_aprendidas` + `receta/vNNN` ya cumplen el rol.
- No poner anatomías de un personaje en `_comun`.
- No tratar `indice_clips.json` ni las poses de Piquito como si ya fueran el catálogo creciente.
- No usar `/opt/myia-taller-n8n/trabajo/biblioteca` como casa de estas tres (es la biblioteca de investigación/pintura, no la de moldes 3D).

---

## B. Cómo se crean hoy personajes y objetos con formas nuevas

Trazado del camino **sin molde previo**, según el código de fábricas. No hay TRELLIS ni ningún generador imagen→3D en `/opt/myia-fabricas/app`, `constructores_v1_20261109` ni cine_v1 (búsqueda sin coincidencias). v9 lo declara explícitamente como extensión futura no implementada (`CONTRATO_MOTOR_UNICO.md`: «Imagen→3D GPU es extensión futura, no ejecutada/implementada»).

### B.1 Puerta de entrada (n8n → fábricas)

**Puente de código (existe, genérico):** `/opt/myia-fabricas/scripts/encolar_desde_n8n.py`

- Lo llama la puerta SSH como `fabrica_encolar <tipo> b64.<payload>` (L2–3).
- Tipos: `personaje`, `escenario`, `objeto`, `objeto_usuario` (L13).
- Campos obligatorios, sin defaults (L14–17):
  - personaje / objeto / objeto_usuario: `canal`, `id`, `nombre`, `clase`, `version`, `sello_path`, `adn_path`
  - escenario: `canal`, `capitulo`, `episodio`, `carpeta`, `inventario_path`
- Raíces permitidas para rutas: `cubo_fijo/`, `trabajo/`, `entradas/` (L19).
- POST a `http://127.0.0.1:18750/v1/jobs/<tipo>` con timeout 5 s (`server.py` `enqueue`, puerto 18750).
- El comentario del script (L7) dice «Nunca gasta: el servicio tiene `argon_enabled=false`». **Eso no coincide con el `config/config.json` actual**, que tiene `"argon_enabled": true` (leído el 11-nov-2026). El gasto real queda sujeto a ledger, topes y autorizaciones; esta pasada no ejecutó ningún job.

**Flujo de producción `debwaH9svFMoTnOf`:** inspeccionados 594 nodos sanitizados. **No hay nodos `FAB · encolar…`.** Sí hay, y están en la cadena:

- `SELLO PJ · 4b SELLAR FIJO (cubo_fijo sellar)` y `SELLO OBJ · 4b SELLAR FIJO` → escriben ADN + sello en `cubo_fijo/` (entrada de la fábrica).
- `4a0. Reconocer en la biblioteca (gratis)` → SSH `paso00_cadena biblioteca plan --canal` (orden 62, biblioteca **vieja** de trabajo).
- `4a7 · ✋ ¿Guardar en la biblioteca?` (wait) → guardar en esa misma biblioteca de investigación/pintura.
- Ramas 4b/4c: investigan y pintan objetos (Argon + Nano Banana), no construyen el molde 3D de fábricas.

Consecuencia: en el flujo de capítulo de producción, **un sello/ADN nuevo no encola solo la construcción 3D**. El puente `fabrica_encolar` existe; no está cableado en este workflow. (La copia `d2Bwmk2j4ijX28eK` se nombró COPIA FABRICAS; no se abrió en esta pasada.)

### B.2 Personaje nuevo (sin molde previo)

```
n8n SELLO PJ (ADN 5 bloques + sello cubo_fijo)
        ↓  fabrica_encolar personaje  (si alguien lo llama)
workers_v2_3d.run_job
        ↓
v1.run_job: ¿ya hay aprobado? → reuso US$0 (workers.py L66–72)
        ↓ si no
vía B Wikipedia/corpus gratis (L74–92)
        ↓
_personaje() (workers_v2_3d.py L191–302)
```

**Entradas obligatorias** (`_personaje` L191–201):

- `canal`, `id`
- ADN: `adn_path` o, si existe, manda el sellado `cubo_fijo/adn/<id>_ako.json` (L195–197)
- Sello: `sello_path` o `cubo_fijo/personajes/<id>.json` (debe traer `altura_m`)
- Tabla de personajes del canal (colores/medidas auxiliares)

**Constructor de ficha:**

1. Si viene `ficha_path` (no humano / ya investigada): se copia, se fuerza `altura_m` y `id` del sello (L203–216).
2. Si no: `constructores_v1_20261109/personajes/generar_ficha_humana.py` (L217–221). US$0, **sin IA**. Plantilla `bipedo_humano` (4,5 cabezas). Colores/ropa/pelo se deducen del **texto** del ADN, no de un plano métrico (comentario L317).
3. Si el sello/ADN no es persona humana (ave, perro, robot, criatura, etc.): `sys.exit(4)` `NO_HUMANO_RUTA_ARGON` (L186–190) → job `esperando_pago_argon` (L222–223). **No construye.**
4. Conflictos de altura: exit ≠ 0 → `stop_altura` (L225–227).
5. Validador de esqueleto en el 213, US$0, **antes** de pagar el pod (L239–247). Si no es `apta` → `ficha_rechazada`, sin GPU.
6. Se registra `ficha_esqueleto/vNNN` con `registrar_version` (L248).

**GPU (RunPod, no TRELLIS):** `Pod(cfg).correr` (`workers_v2_3d.py` L250–257) sube constructores + ficha, corre `run_personaje_pod.sh <id> <altura_adn>` (Blender 5.2.3 EGL según el docstring L9). Siempre termina el pod. Mide altura, compara con cubo_fijo_v2, tolerancia ±2 % (L260–267). Si no cuadra o falta el `.blend` → `stop_altura` / `error_construccion`, **no publica hoja**.

**Salida publicada** (L277–297) en `/opt/myia-biblioteca/<canal>/personajes/<id>/`:

- `ficha_esqueleto/vNNN/ficha_esqueleto.json`
- `blend/vNNN/<id>.blend`
- `renders/vNNN/HOJA_<id>.png` (+ informe, medida, logs)
- `recibos/vNNN/` (gpu_estado, out.tgz)
- `meta.json`: `estado=hoja_lista`, `approval_ref=None`, `siguiente`: «Ricardo aprueba la HOJA → approval_ref + estado aprobado (el motor solo carga aprobados)» (L294)

**Qué sí funciona hoy para un personaje “nuevo”:** un humano con ADN y sello sellados puede salir de la plantilla bípeda, con color/ropa/proporción tomados del texto, pasar validador y altura, y quedar en `hoja_lista` a la espera de aprobación.

**Límites y huecos:**

- Forma **realmente nueva** (ave como Piquito, robot, anatomía inventada): la plantilla se niega (exit 4). La ruta Argon de anatomía está nombrada, no construye en automático. Se puede inyectar una `ficha_path` ya hecha.
- No hay escultura libre ni imagen→3D. La “novedad” humana es combinación de plantilla + atributos del ADN.
- El flujo de producción no encola este trabajo solo.
- Hasta que Ricardo pase `meta.estado` a `aprobado`, cine_v1 en modo estricto no debería usarlo (`--solo_estado_aprobado`).

### B.3 Objeto nuevo (sin molde previo)

```
n8n SELLO OBJ (ADN + sello cubo_fijo/objetos_pj/<id>.json)
        ↓  fabrica_encolar objeto
run_job: si construir_3d.objeto y hay id
        ↓
v1.run_job (reuso aprobado / corpus / receta aprendida por nombre)
        ↓ si no reusado
_objetos_lote() (workers_v2_3d.py L88–185)
```

**Regla escrita en el docstring (L88–91, L6):** el objeto se **extrae de un escenario ya construido y publicado** donde aparece (`ensamblado_star_recetas` > `star`), con forma Star o receta Argon aprobada. Se arma solo en Blender en un pod, se mide el alto contra la caja 4a2 ±2 %, se publica en `objetos/<id>/`. **Si en ningún escenario tiene forma/receta → FALTA (no se inventa).**

Orden de búsqueda de forma (`_objetos_lote` L119–141):

1. Receta Argon vía B aprobada en `objetos/<id>/receta/v*/recetas_validas.json` o en recetas de escenarios (prioridad, aunque el objeto vaya en la mano y no se dibuje en el set).
2. Instancia en un `ensamblado_star_recetas.json` / `ensamblado_star.json` de algún escenario del canal, casada por `ids_canal` (`_coincide_pieza`, L303–305: nunca un sufijo suelto).
3. Si el pedido trae `recetas_sueltas`: `_recetas_sueltas()` (L114–115, L319–335) arma fichas + corpus gratis → Argon (puerta `argon_fabrica`) → revisor → `recetas_validas.json` solo APTAS.
4. Si no hay plan de piezas → `stop_falta_dato` (L144–145).

**v1, si aún no hay 3D** (`workers.py` L96–119): busca receta aprendida por nombre de archivo en `recetas_aprendidas`; si hay, copia y deja `listo_parcial`; si no, `esperando_argon` / `cotizar_argon`. Tampoco inventa malla.

**Escenario (contexto necesario para muchos objetos nuevos):** `_escenario()` (L384+):

1. Exige inventario 4a1 + `4a2_entrada_blender.json` (L388–390).
2. `plan_escenario.py`: mapa → token en las **283** formas Star → si no, `FALTA` (L1–7, L45–60). Nunca se detiene por un objeto sin decisión; lo marca e informa.
3. `ensamblar.py star`; si hay `recetas_validas.json` o Argon está habilitado, reensambla en `star_recetas` (L399–407). Pieza FALTA sin receta se materializa como **caja** (`ensamblar.py` L84: `'caja (FALTA en Star)'`).
4. GPU: `run_escenario_pod.sh`. Publica blend + hoja. Si quedan piezas falta: `hoja_lista_con_faltas` (L432–437).

**Salida del objeto** (L155–185): `blend/vNNN`, `renders/vNNN`, `recibos/vNNN` (medida, piezas.json), `meta.json` con `hoja_lista` / `falta_receta` / `stop_altura`.

**Qué sí funciona para una forma “nueva” de objeto:**

- Si el nombre cae en las 283 primitivas Star (token exacto o raíz, esta última marcada `aprox=True`): se construye por catálogo, sin Argon.
- Si no cae: puede nacer una **receta** (composición de primitivas + caja + materiales) vía corpus gratis y, si la compuerta Argon está abierta y el revisor la declara APTA, se publica versionada y se reusa. Eso es “forma nueva” en el sentido del sistema: receta aprobada, no un mesh orgánico libre.
- `recetas_sueltas` cubre el caso «objeto que no aparece en ningún escenario construido» (p. ej. va en la mano), pero sigue siendo receta, no escultura.

**Límites y huecos:**

- No hay camino imagen→3D / TRELLIS / escultura libre. Una forma fuera de primitivas + receta queda FALTA o caja.
- Un objeto nuevo **antes** de que exista un escenario construido (o una receta suelta pagada y aprobada) no avanza (`stop_falta_dato`, L141).
- El matching de recetas aprendidas en v1 es por *substring del nombre de archivo* (`workers.py` L104–107): frágil, no es un id canónico.
- El flujo de producción pinta referencias 4b/4c y sella ADN; no construye solo el `.blend` de fábricas.
- `objeto_usuario` publica en `objetos_usuario/` (L62, L93), misma lógica de lote.

### B.4 Costos (solo lo que está en código/config; no se gastó nada)

Leído de `/opt/myia-fabricas/config/config.json` y `argon_fabrica.py` L3–4, L56–69. Cifras de tope, no de esta pasada:

| Compuerta | Valor en config/código |
| --- | --- |
| `argon_enabled` | `true` en config actual (el comentario de `encolar_desde_n8n.py` L7 sigue diciendo `false`) |
| `tope_usd_argon` | 3.0 |
| `argon.tope_por_llamada_usd` | 0.75 (el código recorta a ≤ 0.75) |
| `argon.tope_noche_usd` | 3.0 |
| `argon.tope_lote_usd` (lote abierto desde 2026-11-11 04:44 +01) | 1.5 |
| Precio modelo declarado | [2.0, 10.0] USD / millón tokens (`precio_usd_por_millon`) |
| GPU `tope_por_trabajo_usd` | 0.5 |
| GPU `bolsa_usd` | 50.0 |
| GPU `gastado_previo_usd` | 0.84 |
| GPU `saldo_minimo_runpod_usd` | 5.0 |
| GPU `costo_estimado_usd` / `costo_hora_max` | 0.15 / 0.9 |
| Ledger | reserva **antes** de llamar; sin reintento automático; separación 20 s |

vía B (corpus) y `generar_ficha_humana.py` son US$0. El validador de ficha es US$0. Reuso de aprobado es US$0.

---

## C. Historial de cambios / estado persistente entre escenas

Pedido: si en la historia se rompe la espada, se daña un muro o se rasga la ropa, ese cambio queda en el activo y, al reusarlo, no aparece «reparado» de golpe, salvo que el guion diga que se reparó.

### C.1 Qué existe hoy (evidencia)

**1. El cubo 01 ya piensa en historial, pero no lo persiste.**

- `cubo01_accion.py` L2–4, L23: el 01 decide «cambios de objetos» y «hechos para el historial». Chequeo `objetos_y_cambios` y `hechos`.
- Vocabulario `EV.CAMBIOS` (`eventos_o112.py` L9): `aparecer`, `desaparecer`, `romper`, `mover`, `escalar`, `comprimir`. **No existe `reparar`.** `romper` y `mover` exigen campo `objeto` (cubo01 L182–183).
- Prompt `dirigir_escena_accion.txt` L48–49, L57–58: los *hechos* «deben seguir siendo verdad DESPUÉS de esta escena» (quién lleva qué, qué se rompió, heridas).
- Validación L214–226: `hechos[]` = `{hecho, personaje, t}`. Lista vacía = aviso, no error.
- Hueco: `pedido()` (L51–79) arma THE_SET + CHARACTERS + SCENE + SCRIPT. **No inyecta los hechos ni el estado vigente de la escena anterior.** El 01 no «ve» que la espada ya estaba rota, salvo lo que el guion de esta escena cuente.

**2. cine_v1 copia los hechos y no los aplica al molde.**

- `m1_preparar.py` L148: mete `"hechos": D.get('hechos', [])` en `entrada_motor_v1`. No hay en ese archivo campos `historial`, `variante`, `estado_pieza` ni `condicion` (grep vacío).
- `sb3d_argon.py` L57 reenvía `hechos` a un guion interno. No construye variante.
- `motor_blender.py` L733–759 («escenario vivo»): solo anima piezas que la fábrica marcó con prop `vivo`, o apariciones de objetos **que ya existen** en el molde. Si el cambio nombra un objeto que no está, o no hay regla de pieza viva → `pedir_a_fabrica` (L756–758). `aparecer` solo muestra lo que ya está en el molde (L752–754). **No hay rama `romper` que sustituya malla ni que deje el daño para la escena siguiente.**

**3. v9 tiene cambios *dentro* de la escena, no un historial de historia.**

- `vivo_binding.py` L1–15: `environment.live_data.changes[]` con objeto/pieza, propiedad, intervalo, `from`/`to`/`curve`. Es binding 4a/4a4 para el reloj de **esa** escena.
- `eventos.py` L1: «continuidad verificable en cortes» = cortes de cámara, no capítulos.
- No hay línea de tiempo por episodio reutilizable en una escena posterior.

**4. Ya existe un diseño completo de cambios permanentes… en la biblioteca vieja (orden 62).**

`/opt/myia-taller-n8n/cajas/biblioteca.py` L1–52 y L564–629:

- Raíz por defecto: `/opt/myia-taller-n8n/trabajo/biblioteca` (L62).
- Por escenario: `ficha.json`, `molde/vN`, `base/vN`, `datos/vN`, `variantes/vN`, `historial/eventos.jsonl` (solo se agrega; NUNCA se borra, L17, L193–200).
- `permanente` (L566–603), modos:
  - **variante persistente** (cambia el aspecto, no la forma): la variante pasa a `estado_vigente`; el molde no cambia; las nuevas ediciones se hacen sobre esa imagen; la base original queda para recuerdos/flashbacks.
  - **versión nueva** (cambia la forma: medidas, aberturas, muros): crea `v2` (molde/base/datos), deja `v1` intacta; Blender re-arma una vez; estado `pendiente_molde_y_base`.
  - modo `auto`: si `toca_geometria` → versión; si no → variante.
- Está cableado a n8n producción: `4a0` llama `paso00_cadena biblioteca plan` (`paso00_cadena.py` L9, L1994–2001; nodo 4a0). `permanente` es acción CLI, no aparece como nodo automático tras el 01.
- En disco, esa biblioteca **sí tiene** `historial/eventos.jsonl` (p. ej. `esc-habitacion`, y objetos de otro canal como `obj-espada-energia-azul`). Una ficha real de `esc-habitacion` ya trae `estado_vigente`, `variantes` con `persistente`, `tipo_cambio`, citas del guion y justificación (p. ej. rayo que desatura la habitación; restauración en celebración). Esas variantes son sobre **imagen de base 4a5**, no sobre el `.blend` que carga cine_v1.
- `/opt/myia-biblioteca` **no** tiene `eventos.jsonl` ni `cambio_permanente.json` ni `estado_vigente` en los moldes 3D.

**5. Versionado de moldes 3D ≠ historial de historia.**

`myia-fabricas/app/biblioteca.py` versiona construcciones (v001, v002 de un blend/ficha). Un `v002` nuevo **no** significa «la espada se rompió en la escena 4». Si el motor toma `meta.actual`, un rebuild del molde sano pisaría conceptualmente el daño, aunque el archivo viejo siga en disco.

**6. ADN / sello.** No se encontró un campo canónico `estado` / `condicion` de historia en el camino de `m1_preparar` ni en la ficha de esqueleto. El ADN describe el personaje/objeto base, no su estado narrativo acumulado.

### C.2 Diagnóstico

El producto que Ricardo describe **ya fue pensado dos veces**, y las dos quedaron a medias y desconectadas:

1. El 01 escribe `hechos` + `cambio=romper`, pero nadie los graba en una línea de tiempo de activo, y la escena siguiente no los recibe.
2. La orden 62 sabe hacer «variante persistente vs versión nueva», flashbacks (madre intacta) y `estado_vigente`, pero vive en la biblioteca de **pintura** y no alimenta a `m1_preparar` ni a fábricas 3D.
3. cine_v1, si el daño no está ya en el molde como pieza `vivo` o como mesh presente, solo anota `pedir_a_fabrica` y sigue con el molde sano.

Por eso una espada rota en el guion puede «repararse sola» en la escena siguiente: el motor recarga el molde base aprobado.

### C.3 Propuesta genérica (diseño, no parche)

Principio: **el molde base se queda limpio; el estado de la historia vive al lado, por canal, versionado, solo se agrega.** Reutilizar la semántica ya escrita en orden 62 (`variante` vs `versión`, madre intacta, `estado_vigente`, `historial/` append-only), **trasladada a `/opt/myia-biblioteca`** y leída por cine_v1.

#### C.3.1 Modelo de datos

Por activo (personaje, objeto, escenario), bajo la pieza 3D ya existente:

```
/opt/myia-biblioteca/<canal>/<tipo>/<id>/
    meta.json                    # molde base, approval_ref, actual (NO se reescribe con el daño)
    blend/vNNN/                  # molde sano (o variantes 3D aprobadas, ver abajo)
    historial_historia/
        eventos.jsonl            # solo append; nunca se borra
        estado_vigente.json      # puntero actual por «línea de tiempo» (capítulo/episodio)
    variantes_historia/
        vNNN_<etiqueta>/        # p.ej. v001_rota: blend/material/ocultaciones aprobados
```

Un evento (una línea de `eventos.jsonl`):

| Campo | Rol |
| --- | --- |
| `evento_id` | estable, único |
| `schema` | p.ej. `historial_historia_v1` |
| `canal`, `activo_tipo`, `activo_id` | identidad genérica (no nombres de serie en el código) |
| `capitulo`, `episodio`, `escena`, `t_s` | cuándo ocurre en la historia |
| `causa` | `{origen: "guion"\|"hecho_01", cita, hecho}` |
| `cambio` | vocabulario cerrado (extender `CAMBIOS` con `reparar`, y tipos de aspecto: `rasgar`, `ensuciar`, `herir` si se aceptan) |
| `que` | qué parte (id de malla/pieza/material); nunca adivinar submallas (misma regla que `vivo_binding.py` L11) |
| `de` / `hacia` | estado anterior y nuevo (ids de variante o descriptores validados) |
| `toca_geometria` | bool → decide variante de aspecto vs versión 3D nueva (igual que L46–50 de cajas/biblioteca.py) |
| `reversible` | bool; `reparar` apunta al `evento_id` que cierra |
| `variante_ref` | ruta de `variantes_historia/vNNN_…` **aprobada**, o `null` si aún `pendiente_fabrica` |
| `molde_base_ref` | versión de blend/ficha que no se toca (flashback) |
| `vigente_en` | recorte de validez (lista de escenas, o «desde escena N hasta reparar») |
| `aprobado` | revisión técnica + `approval_ref` |

`estado_vigente.json` no es el archivo que crece: es un índice `{ "linea": "presente", "evento_id", "variante_ref", "desde": {capitulo,escena} }`. Para flashbacks se puede resolver otra línea (`linea: "en_escena_3"`) sin borrar el presente.

Estado de **posesión** (quién lleva la espada) va en el mismo historial, porque el 01 ya lo pide en los hechos, pero es distinto del daño de la malla.

#### C.3.2 Dónde se guarda

- **Por canal / por activo**, dentro de `/opt/myia-biblioteca`, no en `_comun` (el daño de *esta* historia no es un bien común) y no en el árbol de v9.
- **Separado del molde base** para que un rebuild o una nueva versión de fábrica no «cure» la espada.
- No reutilizar `trabajo/biblioteca` como fuente 3D; sí **migrar o espejar** la semántica y, si Ricardo lo decide, los eventos ya escritos ahí (hoy son sobre imagen 4a5).

#### C.3.3 Quién escribe

1. **Detecta (01 / Argon):** el cubo 01 ya emite `acciones[].cambio` + `hechos[]`. Eso se mantiene. Hay que **inyectar** en el pedido del 01 el `estado_vigente` y los hechos previos de los activos de la escena (hoy no se hace).
2. **Valida (código, no el modelo):** extender el validador de `cubo01_accion.py` / `eventos_o112.py`: el `objeto` debe existir en el set o en el inventario del personaje; `romper` sin pieza conocida = error, no invención; `reparar` solo si hay un evento vigente reversible; la cita debe estar en el guion (regla ya existente).
3. **Persiste (módulo de biblioteca 3D, US$0):** append a `eventos.jsonl` y actualización de `estado_vigente.json`. Equivalente a `biblioteca.py permanente`, pero sobre `/opt/myia-biblioteca`.
4. **Materializa (fábricas, con compuerta):** si `toca_geometria` o hace falta un material/visibilidad que el molde no tiene, se encola un trabajo de **variante** del molde ya aprobado (`espada_rota`, `muro_daniado`, `ropa_rasgada`), no un personaje/objeto nuevo desde cero. Misma puerta: validador, altura si aplica, `hoja_lista` → aprobación → `variantes_historia/vNNN` + `approval_ref`. Hasta que exista la variante aprobada, cine_v1 no inventa el daño (puede bloquear o, si Ricardo lo acepta, aplicar solo ocultar/mostrar piezas ya presentes).

Argon no escribe directo al historial. Propone el hecho; el código lo admite o lo rechaza.

#### C.3.4 Quién lee y cómo se aplica

`m1_preparar.py`, al armar `entrada_motor_v1`:

1. Identifica activos de la escena (personajes, objetos del set, escenario, objetos en mano).
2. Resuelve `estado_vigente` a la **línea temporal de esa escena** (presente, flashback, escena paralela).
3. Entrega al constructor, de forma explícita:
   - `molde_base` (versión aprobada intacta)
   - `variante_ref` si existe y está aprobada (swap de blend o de sub-objeto)
   - operaciones baratas que no requieren malla nueva: ocultar pieza, cambiar material ya nombrado, activar regla `vivo` que la fábrica haya marcado
4. Si el estado exige una variante que no está aprobada → faltante tipado (como `pedir_a_fabrica`, pero **antes** de GPU), no cargar el sano y callar.

`motor_blender.py` deja de ser el primer sitio que «se entera» del daño. Recibe la variante ya resuelta. Las reglas `vivo` siguen sirviendo para el cambio *durante* la escena (la espada se rompe en el segundo 12); el historial cubre *después* de la escena.

El 01 de la escena N+1 recibe ese mismo estado como contexto, para no contradecirlo.

#### C.3.5 Cómo se producen las variantes

- Partir del molde **aprobado**, no de la plantilla en blanco.
- Etiqueta estable y genérica: `<id>__<evento>` o `<id>__rota`, versionada (`v001`, `v002`).
- Dos modos, copiados de orden 62:
  - aspecto (textura, color, rasgadura UV, suciedad): variante sobre el mismo blend;
  - geometría (espada partida, muro con hueco): versión nueva de mesh, madre intacta.
- Misma compuerta A.4. El índice del canal apunta la variante; el `actual` del molde sano no se mueve.

### C.4 Casos borde (el diseño tiene que declararlos)

| Caso | Tratamiento propuesto |
| --- | --- |
| Flashback / recuerdo | Usar `molde_base_ref` o el `estado_vigente` de la escena recordada. v1/madre nunca se borra (ya en orden 62 L47–50). El 01 debe marcar la escena como flashback (hoy no hay campo dedicado). |
| Corte temporal hacia adelante | El estado vigente es el del último evento con `t` ≤ el tiempo de historia de la escena, no el de la escena con número anterior en el capítulo. |
| Escenas paralelas (mismo instante, dos sets) | El estado se indexa por tiempo de historia, no por número de escena. Dos escenas simultáneas leen el mismo evento. |
| Reparación | Nuevo evento `reparar` que cierra uno reversible. Si el guion no lo dice, el validador no deja «curar». Hace falta añadir `reparar` a `CAMBIOS`. |
| Estado desconocido (falta la escena 3, se rueda la 4) | Decisión de Ricardo (ya estaba pendiente en el motor): o se arranca desde el último evento existente, o se para. El código no inventa el hueco. |
| Varios capítulos / misma serie | `capitulo`+`episodio` van en el evento. El estado vigente es por historia del canal, no se resetea al cambiar de capítulo salvo evento explícito. |
| El mismo objeto en dos sitios | Un `activo_id` no puede estar vigente en dos lugares a la vez. El evento de posesión (`mover` / «quién lleva») es la fuente; si el 01 lo contradice, error de continuidad, no se clona el molde. |
| Dos copias (dos espadas iguales) | Son dos `activo_id` (instancias), un mismo molde base. El daño es por instancia. |
| Cambio solo intra-escena que no debe persistir (un vaso que se cae y el set se recompone entre tomas) | `vigente_en` limitado a esa escena, o `persistente: false` (el campo ya existe en variantes de orden 62). |
| Personaje herido / ropa rota | Misma tubería, casa en `personajes/<id>/historial_historia/`, variante de malla o material; no se edita la `ficha_esqueleto` base. |
| Conflicto 01 vs historial | Gana el historial ya aprobado + el guion de esta escena si el validador acepta un evento nuevo. Argon no puede «olvidar» un daño aprobado. |

### C.5 Qué no cubre esta propuesta

- No unifica por arte de magia las dos bibliotecas (hay una decisión abierta).
- No convierte las variantes de imagen 4a5 ya guardadas en `trabajo/biblioteca` en blends 3D.
- No autoriza a cine_v1 a deformar mallas «a ojo» cuando falta la variante de fábrica.

---

## Decisiones que Ricardo debe tomar

1. **Unificación de bibliotecas.** ¿Se migra la semántica (y, si aplica, los eventos) de `/opt/myia-taller-n8n/trabajo/biblioteca` hacia `/opt/myia-biblioteca`, dejando la de trabajo solo para investigación/pintura 4a? ¿O se mantienen las dos con un puente explícito? Recomendación de arquitectura: una sola fuente de estado 3D en `/opt/myia-biblioteca`.
2. **Casa de las 3 bibliotecas de v9.** ¿Se acepta la colocación del § A.3 (`movimientos` en `_comun`, `recetas` en lo que ya existe, `anatomias_propuestas` por personaje) y se deja de usar el árbol de v9 como fuente de verdad?
3. **Compuerta del motor.** ¿En producción `m1_preparar` corre siempre con `--solo_estado_aprobado` (hoy `hoja_lista` entra en el modo por defecto)?
4. **Vocabulario de cambios.** ¿Se añade `reparar` (y, si se quiere, `rasgar` / `herir` / `ensuciar`) a `CAMBIOS`, o se reduce todo a `romper` + hecho en texto?
5. **Hueco de escenas.** Si falta la escena 3 y se prepara la 4: ¿se hereda el último estado existente o se para? (Decisión ya pendiente del motor.)
6. **Variante 3D pendiente.** Si el 01 registra «espada rota» y la fábrica aún no tiene la variante aprobada: ¿se bloquea la escena, se permite un placeholder (ocultar/caja) o se espera aprobación humana siempre?
7. **Aprobación de variantes de historia.** ¿La misma regla que las hojas (`hoja_lista` → Ricardo), o revisión técnica automática para cambios menores de material/visibilidad?
8. **Cableado n8n.** El flujo de producción no encola fábricas 3D. ¿Se añade `FAB · encolar…` a la copia de trabajo (no a producción) como siguiente paso de implementación, después de estas decisiones?
9. **`argon_enabled: true` en config vs comentario «nunca gasta» de `encolar_desde_n8n.py`.** ¿Ese `true` es intencional? Esta pasada no tocó el flag. Conviene confirmarlo antes de cualquier corrida real.
10. Siguen abiertas, y no se acometen aquí, las decisiones ya pedidas sobre **correr en el motor**, arranque si falta la escena previa, y programar solo en una copia.

---

## Límites de esta pasada

- Solo lectura. No se modificó el 213, n8n, el motor ni config.
- US$0. No se lanzaron jobs, pods ni llamadas Argon.
- El flujo `d2Bwmk2j4ijX28eK` (COPIA FABRICAS) no se volvió a abrir; la afirmación «no hay nodos FAB · encolar en producción» vale para `debwaH9svFMoTnOf`.
- No se listan secretos ni autorizaciones; los topes salen de `config.json` y de `argon_fabrica.py`.
- Ejemplos de Guardianes (Piquito, `esc-habitacion`) se usan solo como evidencia de formato, no como lógica de canal en el diseño.

---

## Índice breve de evidencia

- Fábricas biblioteca (nunca borrar, `_comun`, `buscar_aprobado`, `registrar_version`): `/opt/myia-fabricas/app/biblioteca.py` L2, L15–17, L33–91
- Worker 3D (orden, personaje, objetos, escenario, Argon recetas): `/opt/myia-fabricas/app/workers_v2_3d.py` L1–13, L42–44, L62–85, L88–185, L191–302, L319–374, L384–439
- Worker v1 (reuso, corpus, receta por nombre): `/opt/myia-fabricas/app/workers.py` L52–119
- Encolar desde n8n: `/opt/myia-fabricas/scripts/encolar_desde_n8n.py` L1–20, L23–60
- Ficha humana / no humano: `/opt/myia-fabricas/constructores_v1_20261109/personajes/generar_ficha_humana.py` L2, L10, L186–190, L320
- Plan Star / FALTA: `.../escenario/codigo/plan_escenario.py` L1–7, L45–60; `ensamblar.py` L5, L68–84
- cine_v1 carga biblioteca y hechos: `m1_preparar.py` L4, L14, L131–136, L148, L163
- Escenario vivo / pedir_a_fabrica: `motor_blender.py` L11, L733–759
- 01 hechos y CAMBIOS: `cubo01_accion.py` L2–4, L23, L51–79, L182–183, L214–226; `eventos_o112.py` L9; prompt L48–58
- Orden 62 permanente: `/opt/myia-taller-n8n/cajas/biblioteca.py` L1–52, L564–629; `paso00_cadena.py` L9, L1994–2001
- v9 crecimiento: `CONTRATO_MOTOR_UNICO.md`; `GUIA_BIBLIOTECAS_Y_PUENTES.md` L19, L24, L54, L127; `catalogos_crecimiento.py` L23–65; `argon_automatico.py` L3, L33, L70
- n8n producción: `NODOS_PRODUCCION_sanitizado.json` (flujo `debwaH9svFMoTnOf`, nodos 4a0, 4a7, SELLO PJ/OBJ; ausencia de FAB · encolar)

---

## D) Paso Argon investiga y crea

**Pregunta de Ricardo:** el Inmi anterior habría fabricado un paso en el que Argon genera o investiga personajes/objetos nuevos y el sistema los construye a partir de esa investigación (para cubrir: no humanos como un ave, que hoy caen en `esperando_pago_argon`; objetos sin forma Star/receta, que hoy quedan FALTA; formas orgánicas libres). Validar con evidencia y corregir la sección B si hace falta.

**Fuentes de esta sección:** transcript `/workspace/doc_t66/doc.txt` (conversación con ese Inmi); código y salidas en el 213 (fábricas, staging, biblioteca, n8n volcado en `raw/wfs.json`). Solo lectura, US$0, sin GPU ni llamadas pagadas.

**Nota sobre un segundo documento:** se pidió convertir un docx nuevo en `/home/box/agent-data/agents/f48f7471-1219-4cd2-9785-1815db4eb4a3/attachments/a93dc985955a21824775a4a8d4112f8bcb652748acd48cd93eff40dd0cdbf38f.docx`. A las 08:59 America/Bogota ese hash **no estaba en el box** (en `attachments/` solo está el docx de t66, sha256 `f0a5a7f4…`, distinto). Las citas de «lo que dijo el Inmi anterior» salen de `doc_t66`. Si el otro archivo llega, se puede contrastar línea a línea encima de esta tabla.

### D.1 Qué dijo el Inmi anterior (citas)

En la noche del 9-nov-2026, al explicar el plan de fábricas (doc_t66, alrededor de las 22:07–22:08, hora del transcript):

> «No humanos: siguen el camino de Piquito, con investigación y poses de Argon.»
>
> «Investigación: busca gratis en Wikipedia cómo es ese animal o criatura, y Argon, con eso y el ADN, diseña el esqueleto: cuántos huesos, dónde van, sus piezas y colores. Con Piquito costó unos US$0,64.»
>
> «Construcción: la fábrica arma el molde en la GPU con ese esqueleto y lo mide.»
>
> «Poses: Argon crea las poses propias de esa criatura, como aletear, picotear o saltar, y se revisa que ninguna rompa el cuerpo. Las de Piquito costaron unos US$3,16 por 64 poses.»
>
> «Buscar: primero revisa si la pieza ya está aprobada en la biblioteca. Si no, busca gratis en Wikipedia y después investiga con Argon.»
>
> «Ficha: humano: sale sola del ADN con la plantilla de Star […]; no humano: Argon diseña el esqueleto, como con Piquito; objeto: receta de piezas; escenario: plan con medidas, formas de Star y recetas de lo que falte.»

Más temprano, el mismo Inmi había dicho otra cosa, y hay que no mezclarla:

> «Argon: sí produce el movimiento y las poses y las valida contra el escenario 3D. **No produce la forma 3D de los objetos ni el esqueleto de Piquito, porque ningún prompt se los pide.**» (19:12, diagnóstico inicial)
>
> Luego propuso añadir esos prompts (19:25): «Para Piquito, Argon tendría que devolver también su esqueleto de ave.»

Y, sobre TRELLIS, al arranque del transcript (líneas 9–17):

> «El montaje en la GPU sigue: […] estaba instalando TRELLIS.»
> «TRELLIS quedó instalado y ya creó un primer modelo 3D, pero ese no sirve todavía: el recorte tomó parte del casco en vez de la cara […]. Tampoco está conectado al motor ni tiene esqueleto todavía.»

Más tarde admitió que los primeros moldes detallados de Piquito/Valentina/habitación «los hicimos a mano en mi computador, con los constructores prototipo. No salieron del servicio de fábricas del 213» (aprox. L1560). Esa frase es anterior a la noche en que el servicio sí publicó moldes en `/opt/myia-biblioteca`.

### D.2 Veredicto por caso (y corrección a la sección B)

La sección B no mentía sobre **el servicio vivo de fábricas, hoy, si nadie le pasa una ficha a mano**: un no humano se detiene en `esperando_pago_argon`; un objeto sin Star ni receta APTA queda FALTA; no hay imagen→3D. Eso sigue siendo cierto en `workers_v2_3d.py`.

Lo que B no dejaba claro, y hay que corregir: **sí se construyó y se pagó un paso de investigación Argon**, el 9-nov-2026, en **staging**. Corrió de verdad, dejó fichas, recetas y 64 poses, y el constructor **sí sabe armar un ave** si le dan la ficha. Lo que **no** está es el cable automático: el worker no llama a esos scripts; el molde publicado de Piquito **no usó** la ficha de Argon, sino un `EJEMPLO_MANUAL`.

#### Caso 1 — Personaje no humano (ave, p. ej. Piquito)

| Pregunta | Hallazgo |
| --- | --- |
| ¿Existe el paso? | **Sí, en staging**, no dentro de `/opt/myia-fabricas/constructores_v1_20261109/personajes/` (ahí solo está `generar_ficha_humana.py`). |
| Qué es | Dos scripts de envío único, con prompt fijo, ledger y tope, que llaman a Argon y piden una `ficha_esqueleto/v1`. El constructor/validador del 213 ya acepta plantilla `ave` (y cuadrúpedo, pez, etc.). Si el job trae `ficha_path`, `_personaje()` construye en GPU. Si no, se para. |
| Código / prompts | `esq_argon.py` (`enviar`, L39–57) + `PROMPT_ARGON_piquito.md` / `PROMPT_ARGON_perro.md` en `/opt/myia-staging-arreglos-20261026/esqueletos_20261109/`. Segunda investigación, más completa: `recetas_argon.py` (`enviar`, mismo directorio `recetas_20261109/`) + `PROMPT_INVESTIGACION_piquito_C_corpus_ADN_n8n.md` (paso `investigacion_personaje_v1_corpus`): corpus + ADN → identificación + ficha + catálogo de ≥60 movimientos. Validador: `prototipo_esqueletos/validador.py` L22, L34 (`'ave': cabeza, cuello, cola, ala×2, pierna×2`). Worker: `workers_v2_3d.py` L8, L203–216 (`ficha_path`), L222–223 (`esperando_pago_argon` en exit 4). |
| ¿Cableado? | **No en el worker ni en producción.** `workers_v2_3d.py` no importa `esq_argon` ni `investigacion_personaje`. n8n producción (`debwaH9svFMoTnOf`, activo) no tiene `FAB · encolar`. **COPIA FABRICAS** `d2Bwmk2j4ijX28eK` (639 nodos, **apagada**, `active: false`) sí tiene `FAB · encolar personaje` → `fabrica_encolar personaje` → `:18750`. Eso encola el job; **no dispara la investigación de anatomía**. Los nodos `4a1/4b1/4c1 Investigar` de ambos flujos son la investigación vieja del taller (texto/prompts 4a para pintar), no la ficha de esqueleto. |
| ¿Corrió? | **Sí, el 9-nov-2026, en staging, con autorización explícita de Ricardo** (textos `AUT` en los scripts). Horas en el 213 (UTC+1) → America/Bogota (UTC-5): ficha corta Piquito `esqueleto-piquito-20261109-175524`, **US$0,2182**, salida `esqueletos_20261109/respuestas/piquito.json` (plantilla `ave`, 23 huesos, 26 piezas, `altura_m` 0,10, `origen.tipo=argon`). Perro: `175948`, **US$0,2791**. Investigación C: `investigacion-piquito-20261109-193508`, **US$0,6443** (cuadra con «unos US$0,64»), `recetas_20261109/respuestas/piquito.json`: `investigacion/v1`, ficha `ave` **29 huesos / 38 piezas / 0,18 m**, `catalogo_movimientos` de **64**, 66 datos con evidencia. Construcción GPU de Piquito: jobs `484c18fb…` y `8ea4ad94…`, estado `listo`, gasto GPU US$0,054196 y US$0,009574, **pero `ficha_path` = `EJEMPLO_piquito_ave.json`**. La ficha publicada `ficha_esqueleto/v006` (y v005) declara `origen.tipo=EJEMPLO_MANUAL`, «a mano, sin IA», 23 huesos / 17 piezas, altura forzada a 0,18 por el sello. El informe lo confirma: `REPORTE_MANANA_20261110.md` L12: «Piquito usa su ficha de ave (EJEMPLO_MANUAL)». `meta.json` acumula gasto 3,22237 (casi todo es poses, ver caso poses) y, ojo, `v2_3d.plantilla` dice `bipedo_humano` aunque la ficha es `ave` (el worker deja ese rótulo fijo). |
| Qué lo bloquea hoy | Sin `ficha_path`, el no humano no llama a Argon: queda `esperando_pago_argon` (el comentario del worker L8 todavía dice «Argon sigue apagado; se aprueba aparte»). Los prompts/scripts de investigación no son genéricos de canal: están fijados a Piquito y a un perro de prueba. La ficha Argon de 29/38 **nunca se publicó** como molde. Hace falta aprobación/pago + un puente que pase la salida de Argon a `ficha_path` y a la compuerta del validador. |

#### Caso 2 — Objeto nuevo sin forma Star / sin receta

| Pregunta | Hallazgo |
| --- | --- |
| ¿Existe el paso? | **Sí, y este sí está en fábricas vivas**, no solo en staging. |
| Qué es | Si el plan marca FALTA (nombre no cae en las 283 formas Star), se arman fichas + corpus vía B (gratis) y Argon propone una **receta de primitivas** (caja, piezas, apoyo, colores). El revisor deja solo APTAS en `recetas_validas.json`. Con eso, `ensamblar.py` modo `star_recetas` y `_objetos_lote()` pueden construir. Si no hay receta APTA, sigue FALTA / caja; **no se inventa malla**. |
| Código / prompts | Vivo: `workers_v2_3d.py` `_recetas_argon` / `_recetas_sueltas` L319–374, L404–407; `constructores_v1_20261109/escenario/via_b/recetas_argon.py` (`preparar`, `revisar`, L5–10). Staging (corrió el 9-nov): `/opt/myia-staging-arreglos-20261026/recetas_20261109/recetas_argon.py` + `PROMPT_RECETA_G1_juguetes_textiles.md` … `G4_objetos_magicos.md` (paso `receta_objetos_faltantes_v1`). |
| ¿Cableado? | **Sí, en el servicio** `/opt/myia-fabricas` (endpoint `POST /v1/jobs/escenario` u `objeto`, worker v2). Condicionado a `argon_enabled` y topes (`config.json`; el 11-nov está en `true`). n8n: COPIA FABRICAS (apagada) encola escenario/objeto; producción no encola fábricas. Los nodos 4b1/4c1 investigan para **pintar** (Nano Banana), no sustituyen esta receta 3D. |
| ¿Corrió? | **Sí.** Staging 9-nov (UTC+1, ≈13:12–14:35 America/Bogota): G1 US$0,3208; G2 US$0,4131; G3 US$0,1985; G4 US$0,3077; total **US$1,2401** (`envio.log`, `res_G*.json`). Después, con la clave ya en fábricas, el propio Inmi reportó rearmar el jardín v004 con recetas ya pagadas (21 piezas buenas, 3 FALTA: manguera, rayo, cielo). Eso confirma: el paso existe, produce recetas, y lo que no pasa el revisor sigue faltante. |
| Qué lo bloquea hoy | FALTA permanece si no hay forma Star ni receta APTA. Topes/clave/autorización. El matching v1 por nombre de archivo es frágil. No hay camino fuera de primitivas. |

#### Caso 3 — Forma orgánica libre (imagen→3D, TRELLIS)

| Pregunta | Hallazgo |
| --- | --- |
| ¿Existe el paso en fábricas / cine_v1 / n8n? | **No.** Búsqueda sin coincidencias de `TRELLIS`/`imagen3d` en `/opt/myia-fabricas` (app + constructores vivos), cine_v1 y `/opt/myia-staging-arreglos-20261026` (fuera de respaldos de repos ajenos). |
| Qué hubo | Un experimento de GPU anterior, citado en t66 L9–17: TRELLIS se instaló, sacó un primer modelo (recorte malo de un casco/cara), se dejó un script `continuar_rostro.sh` y se apagó la máquina. El mismo Inmi escribió que **no estaba conectado al motor ni tenía esqueleto**. v9 lo sigue declarando «extensión futura, no ejecutada». |
| ¿Cableado / corrió en el pipeline? | No hay nodo n8n, ni worker, ni constructor que tome una imagen y entregue un molde orgánico a `/opt/myia-biblioteca`. Las «formas nuevas» que sí existen son: primitivas Star, recetas de primitivas, y fichas de esqueleto hechas de esfera/cápsula/caja (`ficha_esqueleto_v1.schema.json`). Eso no es modelado orgánico. |
| Qué lo bloquea | Nunca se integró. Conectarlo sería trabajo nuevo, no reactivar un paso ya cableado. |

#### Caminar / correr / volar (si se afirma que «Argon lo resolvió»)

- Argon **sí** generó un **catálogo de 64 poses/movimientos** de Piquito (aleteo, etc.): script `poses_argon.py` + 8 prompts `PROMPT_POSES_polluelo_chibi_mascota_L0N_de_08.md`, staging 9-nov, tope US$5,94, gasto real **US$3,1586** (L01 falló por `ReadTimeout` y se reenvió: US$0,4727). Ese total cuadra al céntimo con `meta.json` versiones n=4: `gasto_usd_confirmado: 3.1586`, `origen: 'Argon 8 tandas 9-nov-2026 + L01 reenviada'`, publicado en `poses/v004/CANDIDATOS_motor_aptos.json`. El worker de fábricas **no** llama a `poses_argon.py`.
- La investigación C también trajo `catalogo_movimientos` de 64, junto a la ficha 29/38, que no se publicó.
- Eso **no** sustituye la locomoción del motor: caminar/correr siguen en `m3_traductor` / Kimodo / `indice_clips.json` (y `correr` se sigue traduciendo a `caminar` en cine_v1, como ya se documentó). Volar va al módulo de movimientos especiales (`m3_router`), no a TRELLIS ni a una receta de forma. Argon no «resolvió» correr/volar universales en el motor.

### D.3 Tabla de afirmaciones (claim → cita → ¿está en código? → cableado → corrió)

| Afirmación | Cita / línea (doc_t66) | ¿Existe en código? | ¿Cableado? | ¿Corrió? (evidencia) |
| --- | --- | --- | --- | --- |
| No humanos: investigación + esqueleto Argon, como Piquito | 22:08, «Argon […] diseña el esqueleto […]. Con Piquito costó unos US$0,64» | Sí, staging: `esq_argon.py`, `PROMPT_ARGON_piquito.md`, `PROMPT_INVESTIGACION_piquito_C_….md` | Staging / scripts a mano. No en `workers_v2_3d`. No en n8n producción. COPIA FABRICAS solo encola el job de construcción | Sí: US$0,2182 (ficha corta) + **US$0,6443** (investigación C, 9-nov 19:35 UTC+1 ≈ 13:35 America/Bogota). Salidas en `respuestas/piquito.json` |
| La fábrica construye el molde GPU con ese esqueleto y lo mide | 22:08, «Construcción: la fábrica arma el molde…» | Sí: `_personaje()` + `ficha_path` + validador `ave` + pod Blender | COPIA FABRICAS (apagada) `FAB · encolar personaje`; servicio `:18750`. Producción no | Sí, pero **con ficha EJEMPLO_MANUAL**, no con la de Argon. Jobs `listo`, blend/hoja v006, altura 0,18 m OK. Informe L12 |
| Argon crea 64 poses de la criatura (~US$3,16) | 22:08, «Las de Piquito costaron unos US$3,16 por 64 poses» | Sí: `poses_20261109/poses_argon.py` L1–12, 8 prompts | Staging. No lo llama el worker | Sí: **US$3,1586** exactos; 8 tandas + reenvío L01; publicados en `poses/v004/` (`estado_aprobacion`: candidato, sin `approval_ref`) |
| Buscar biblioteca → Wikipedia → Argon | 22:10, plan de fábricas | Sí el esqueleto del plan: `buscar_aprobado` + `via_b_corpus` + Argon recetas. La rama Argon de **anatomía** no está en el worker | Recetas de objeto: sí en el servicio. Anatomía: no | Corpus de Piquito sí (2 fuentes, US$0, `meta` ver 1–2). Argon anatomía solo por scripts de staging |
| Humano: plantilla gratis; no humano: Argon; objeto: receta; escenario: Star + recetas | 22:10, bloque «Ficha» | Humanos: `generar_ficha_humana.py`. No humano: exit 4, **no** llama Argon. Objeto/escenario: sí, como B y arriba | Igual que las filas anteriores | Humanos y escenarios/objetos con Star o receta: sí en fábricas 10-nov. No humano «solo» si hay `ficha_path` |
| Argon no produce forma 3D ni esqueleto de Piquito (diagnóstico temprano) | 19:12 | Era cierto **ese día**, antes de los prompts del 9-nov. Quedó desactualizado | — | Los prompts se escribieron y se pagaron después, en staging |
| TRELLIS instalado, primer modelo, no conectado al motor | L9–17 | No hay código de TRELLIS en fábricas/cine_v1/staging de este paso | No | Experimento GPU previo, fuera del pipeline de fábricas |
| Nodos FAB en n8n y fábricas encendidas | t66 ≈ L1899, L2132, L2740 | `encolar_desde_n8n.py`; nodos `FAB · encolar …` en `d2Bwmk2j4ijX28eK` | Solo COPIA FABRICAS, **apagada**. Producción sin FAB | Encolar/construcción de moldes sí ocurrió (jobs en `/opt/myia-fabricas/jobs`, biblioteca 10-nov). No hay evidencia de que el flujo de producción encolara la investigación de anatomía |
| Los primeros moldes detallados se hicieron a mano, no por el servicio | L1560 | Compatible con `EJEMPLO_MANUAL` y con que el servicio se encendió después | — | Cierto para esa etapa; luego el servicio sí publicó v006, pero reusando la ficha de ejemplo |
| Caminar/correr/volar resueltos por Argon | No hay una frase única «ya quedó resuelto»; el plan (22:10) habla de Kimodo/CMU/especiales y de recetas de movimiento | Poses de ave sí. Locomoción del motor: `m3_traductor`, Kimodo, clips, `m3_router` (vuelo) | Poses: publicadas como candidatos. Correr en cine_v1 sigue mapeado a caminar | Poses 64 sí. Correr/volar universales: no |

### D.4 Corrección explícita a lo dicho en B

- **Se mantiene:** en el servicio vivo, un personaje no humano **sin** `ficha_path` se detiene en `esperando_pago_argon` y no investiga solo. Un objeto sin forma ni receta APTA queda FALTA y no se inventa. No hay camino imagen→3D / TRELLIS en fábricas.
- **Se corrige:** no es verdad que «no exista» un paso donde Argon investigue y se construya a partir de eso. Ese paso **se programó, se autorizó y se pagó el 9-nov-2026 en `/opt/myia-staging-arreglos-20261026/`** (esqueletos, investigación con corpus, recetas de objetos, 8 tandas de poses). El constructor **puede** armar un ave a partir de una ficha válida. Lo que falta es **conectarlo**: que el worker, con la compuerta de pago, llame a la investigación genérica (no solo a Piquito), valide, publique la ficha Argon (no el ejemplo manual) y recién entonces encienda la GPU. Las recetas de objeto **ya están** en esa tubería viva.
- **Matiz sobre «formas nuevas»:** lo que el Inmi anterior entregó son primitivas y recetas/fichas de primitivas (cápsulas, esferas, cajas), más poses. No es modelado orgánico libre.

### D.5 Costos ya ocurridos (solo lecturas de logs; esta pasada no gastó)

| Lote (9-nov-2026, 213 UTC+1) | US$ real | Salida |
| --- | --- | --- |
| Ficha corta Piquito (`esq_argon`) | 0,2182 | `esqueletos_20261109/respuestas/piquito.json` |
| Ficha perro (prueba de otra especie) | 0,2791 | `…/respuestas/perro.json` |
| Investigación C Piquito (corpus+ADN+ficha+64 movs) | 0,6443 | `recetas_20261109/respuestas/piquito.json` |
| Recetas objetos G1–G4 | 1,2401 | `res_G*.json` + `respuestas/G*.json` |
| Poses Piquito 8 tandas + reenvío L01 | 3,1586 | `poses/v004/` en la biblioteca |
| GPU construcción Piquito (2 jobs, ficha de ejemplo) | 0,0638 | `blend/v006`, `renders/v006` |


---

## E) Validación del Word t88

**Pedido de Ricardo:** en la conversación del Word, el otro Inmi habría «arreglado» personajes, objetos, escenarios, poses, formas nuevas, caminar, correr y volar. Extraer cada afirmación, contrastarla con el código del 213 y n8n, y decir con claridad si **lo dijo pero no lo colocó**.

**Documento:** `/workspace/doc_t88/doc.txt`, convertido del docx `a93dc985…docx` (271 KB). El binario es **el mismo archivo** que `doc_t66/doc.docx` (sha256 `f0a5a7f4bef0204cf4ae317e85488c45cfdb1dd9ada881b7ea25e0bdf7d15b33`). La diferencia con el `doc.txt` de t66 es que ahora se extrajeron **tres tablas al final** (el formulario que el Inmi dejó como «resultado»). Las citas usan las líneas de `doc_t88`. Esta pasada: solo lectura, US$0, sin cambios.

**Cómo leer el veredicto**

- **Hecho y conectado:** está en el código del camino vivo y se ha ejecutado (o está cableado en el servicio/flujo que realmente se usa).
- **Hecho sin conectar:** hay código, prompts, salidas o una corrida, pero no está enganchado al worker, al motor vivo o al flujo de producción.
- **Solo dicho:** lo afirmó o lo dejó en un plan/tabla como «sí», y no aparece colocado, o el propio Inmi lo dejó a medias.

### E.1 Lo que el Word añade: las tres tablas finales

Son un tablero de estado, no un log de código. Hay que tratarlas como afirmaciones a verificar.

**Tabla 1** (L3662–3670) — programas de movimiento y cámara:

| Programa | Lo que dice el Word | Veredicto |
| --- | --- | --- |
| A* + RVO2 | «✅ Funciona» — rutas sin choques | **Hecho y conectado** en cine_v1: `planificador.py` L1–5, L272–296. Se usa en el motor vivo. |
| Mwni retarget | «✅ Funciona (caminar, girar, sentarse)» | **Hecho y conectado** para esos tres: `motor_blender.py` L8–11, L183; addon `assets/addons/animation_retargeting`. El propio docstring nombra caminar/girar/sentarse, **no correr ni volar**. |
| Fijar pies | «✅ Funciona» | **Hecho y conectado:** `pies_bloqueo.py`, citado en `motor_blender.py` L11. En el propio Word (L1608–1610) el Inmi admite que el resbale **no estaba en cero**. Sigue habiendo avisos de deslizamiento en pruebas posteriores. |
| Expy-Kit | «❌ Malo, lo descarto» | No forma parte del motor vivo. Coherente. |
| AnyShot + rigs + Shakify | «✅ Funciona» | **Parcial.** Shakify y la cámara calculada sí están en el motor vivo (`motor_blender.py` L13: Shakify solo si el SB lo pide; movimientos DSL STATIC/DOLLY/PAN/TRACK/CRANE). AnyShot no aparece como dependencia viva en el encabezado del motor (el diseño que sí corre es la cámara calculada propia). |
| Cámara calculada | «✅ 5 de 6 tomas exactas» | Código sí (`camara_calculada` en el paso 5). El «5 de 6» es el resultado de una prueba, no un contrato. |
| Kimodo | «⚠️ Lo dejo apagado y opcional, porque en la prueba de Ako no pasó» | **La tabla está desactualizada.** Más tarde se encendió: `config_motor.json` L4–5, `kimodo_encendido: true` (nota t983u). `correr_escena.py` L166–179 lo llama en GPU. En el mismo Word, después hay videos de Kimodo (L1612+). **Hoy está conectado**; la fila de la tabla dice lo contrario. |

**Tabla 2** (L3672–3679) — alturas. Coinciden con sellos/ADN y con lo publicado (Piquito y Don Caos 0,18 m, etc.). **Hecho y conectado** como dato.

**Tabla 3** (L3681–3690) — «¿Motor completo en n8n?»:

| Fila | Dice | Veredicto |
| --- | --- | --- |
| Fábrica de personajes / escenarios / objetos | «Sí» | **Hecho sin conectar en producción.** El servicio `/opt/myia-fabricas` existe y ha publicado moldes. En n8n, los nodos `FAB · encolar…` están en **COPIA FABRICAS** `d2Bwmk2j4ijX28eK` (639 nodos, **`active: false`**). El flujo de producción `debwaH9svFMoTnOf` **no tiene** esos nodos. El Inmi mismo lo precisó en L2740: «completos en n8n, en el flujo COPIA FABRICAS… está apagado». Decir «Sí» en la tabla, sin ese matiz, **sobra**. Además, la rama Argon de anatomía no humana **no** está en el worker (sección D). |
| ADN con Argon | «Sí» | **Hecho y conectado** (con compuerta de pago): nodos SELLO PJ/OBJ en producción y en la copia; hay ADN sellados en disco. |
| Motor de animación (Kimodo, objetos, cámara, grabación, revisión) | «Sí» | **Parcial / hecho y conectado en cine_v1**, no como un paquete perfecto: Kimodo está ON en config; el motor vivo carga moldes, planifica, retargetea, graba. Objetos «vivos» y faltantes siguen pidiendo fábrica. |
| Escena por escena y unión del capítulo | «Sí, pero todavía no se ha unido un capítulo con videos reales» | El propio Inmi, al frenar (cerca de L3640), dijo que la unión se estaba armando y **no confirmó** que hubiera entrado en COPIA LIMPIA. **A medias / solo dicho para producción.** |
| Revisión de la filmación cada 5 minutos | «Sí» | **No cuadra.** En COPIA FABRICAS hay `FAB · ⏳ esperar 5 min` para **esperar trabajos de fábrica**, no para revisar la filmación. El vigilante de GPU que él dejó es cada **30 minutos**. **Solo dicho** (o confunde dos mecanismos). |
| Cámaras escogidas por Argon | «No todavía: lo estoy terminando» | Honesto en la tabla. Más adelante en el mismo Word sí hubo corridas donde Argon eligió cámaras (escena 2). Eso es posterior a la tabla. |

### E.2 Personajes, objetos, escenarios, poses, formas nuevas

Estas afirmaciones ya se detallaron en D; aquí el juicio contra lo que **dice el Word**, que es lo que Ricardo quiere validar («¿lo dijo y no lo colocó?»).

| Afirmación | Cita (doc_t88) | ¿Está en el código? | ¿Cableado? | ¿Corrió? | Veredicto |
| --- | --- | --- | --- | --- | --- |
| Argon investiga el no humano y diseña el esqueleto; Piquito costó ~US$0,64 | L1731–1736, también L1593 | Sí, staging: `esq_argon.py`, `PROMPT_INVESTIGACION_piquito_C_….md` | Staging / a mano. **No** en `workers_v2_3d.py` (L222–223: se para en `esperando_pago_argon`) | Sí: **US$0,6443**, ficha Argon **29 huesos / 38 piezas / 0,18 m** | **Hecho sin conectar** |
| En L1586 dice que esa ficha 29/38 se usó para armar el molde (en su computador) y que las 64 poses pasaron | L1586–1588 | La ficha 29/38 existe en staging. El molde **publicado** en `/opt/myia-biblioteca/…/gdc-piquito/ficha_esqueleto/v006` es **EJEMPLO_MANUAL, 23 huesos / 17 piezas**, no la de Argon | El job de fábrica usó `ficha_path=EJEMPLO_piquito_ave.json` | GPU sí publicó v006, con **otra** ficha | **Dicho y no colocado** (la ficha Argon no es la que quedó en la biblioteca) |
| «Esos pasos los corrimos a mano y ninguno de esos archivos 3D se publicó… El servicio nunca los ejecutó» (21:10) | L1600 | Cierto **en ese momento**. Luego el servicio sí publicó, pero reusando el ejemplo manual | Servicio encendido después, sin la rama de investigación | Ver D | Él mismo reconoció que **aún no estaba colocado**; la conexión posterior quedó incompleta |
| «Así funcionaría la fábrica conectada… no humano sigue el camino de Piquito» | L1593–1598 (futuro: «funcionaría», «lo que hay que construir») | Es un **plan**, no un reporte de lo ya enganchado | El trabajador 3D se construyó; la llamada Argon de anatomía no | — | **Solo dicho como plan.** Ricardo pidió después (L1618) que todo subiera real; esa parte no se terminó de cablear |
| Poses: Argon, 64, ~US$3,16, aletear/picotear/saltar | L1736, L1586 | `poses_argon.py` + 8 prompts | Staging. Publicadas en `poses/v004/`. El worker no las genera. El motor, en un tramo temprano del Word (L894), **aún no las leía**; cine_v1 las puede usar como candidatos, sin `approval_ref` | **US$3,1586** exactos | **Hecho, publicado a medias** (candidatos, no aprobación ni pipeline automático) |
| Objeto: receta de piezas si falta forma Star | L1758–1759, L1595, L1588 (habitación US$1,24 / recetas) | Sí, fábricas vivas: `via_b/recetas_argon.py`, `_recetas_argon` | Servicio sí. n8n solo en COPIA FABRICAS apagada | Staging G1–G4 **US$1,2401**; luego jardín con faltantes | **Hecho y conectado en el servicio**; no en producción n8n. Sigue valiendo: sin receta APTA = FALTA, no se inventa |
| Escenario: plan + 283 formas Star + recetas de lo que falte | L1759, L1595 | `plan_escenario.py`, `ensamblar.py`, worker `_escenario` | Igual que objetos | Habitación y otros escenarios publicados en la biblioteca | **Hecho y conectado en el servicio** (con el mismo límite FALTA) |
| Forma 3D en «sistema de puntos de Star» al sellar ADN/objetos | L175–180, propuesta 19:25; L162 dice que entonces **ningún prompt lo pedía** | No hay, en SELLO PJ/OBJ, un campo de malla/puntos que el motor cargue como geometría nueva. Las fábricas construyen primitivas/fichas, no un ADN-de-puntos inyectado en el sello | No en los nodos de sello | TRELLIS: experimento aparte, «no conectado al motor» (L17 y contexto L9–17) | **Solo dicho / no colocado.** Forma orgánica libre: **no hay camino** |
| Humanos salen solos de la plantilla, US$0 | L1738, L1594 | `generar_ficha_humana.py` | Worker v2 sí | Valentina y los demás humanos publicados | **Hecho y conectado** (plantilla bípeda, no forma libre) |
| «Los motores están completos en n8n» (COPIA FABRICAS, 639, apagado) | L2740 | Los 639 nodos existen, incluido `FAB · encolar` | Copia **apagada**. Producción no | Construcciones se lanzaron por el servicio (a veces fuera del flujo de capítulo) | **Hecho en copia, no colocado en producción** |

### E.3 Caminar, correr, volar (foco)

El Word **nunca dice** «correr y volar ya quedaron perfectos y universales». Lo que dice, con precisión, es esto:

1. **Plan del motor de movimiento** (L1742–1746): si es normal (***caminar, girar, sentarse***), mocap o Kimodo; si es especial (***volar con o sin alas***, pelea, sin forma), módulo de especiales; si no lo conoce, Argon escribe una receta (máx. 4 intentos).
2. **Tabla 1** (L3665): Mwni funciona para ***caminar, girar, sentarse***. Kimodo, en esa tabla, apagado.
3. Video de Kimodo (L1612): Valentina ***caminando, sentándose y girando***. Otra vez: no menciona correr ni volar como hecho.

| Afirmación | Cita | Código | Cableado | Corrió | Veredicto |
| --- | --- | --- | --- | --- | --- |
| Caminar / girar / sentarse con mocap + Mwni + pies | L1744, L3665, L1612 | `m3_traductor.py` L22–23 (`LOCOMOCION`); `motor_blender.py` L8–11; `pies_bloqueo.py`; `sentarse_exacto.py` | cine_v1 vivo | Sí: videos y corridas GPU del cap. 1, con resbale residual admitido por él mismo | **Hecho y conectado** (caminar/girar/sentarse). No es «sin fallos» |
| Correr como acción propia | No hay frase «ya sabemos correr». El plan solo lista caminar como normal | **`m3_traductor.py` L22–23: `'correr': 'caminar'`.** El 01 puede escribir «correr» y el motor lo convierte en caminar. `motor_blender.py` L259, L403–408, L510 puede usar el clip `trotar` **por umbral de velocidad**, no porque la acción sea correr | El mapa a caminar está conectado (y es el problema). Kimodo, si corre, llega tarde: el segmento ya es «caminar» | Hay clip `trotar` en `indice_clips.json`; no hay locomoción «correr» de primera clase | **No lo colocó como correr.** Dicho como plan general de movimiento, implementado como caminar (a veces trote por velocidad) |
| Volar (con o sin alas) en el módulo de especiales | L1745 | `m3_router.py` L2–4, L12–15, L32–33: clasifica `vuelo_alas` / `vuelo_sin_alas` y devuelve `tipo_ejecucion='receta'` (`vuelo_alas.py`). Existe `blender/vuelo_alas.py`. `adaptar()` (L64, receta Argon con 4 intentos) **no es llamado** por nadie más | El traductor, si la acción no está en `LOCOMOCION`, enruta y puede etiquetar el segmento como `receta` (L69–71). En **acciones**, si el enrutador devuelve `receta`, **no hay rama** (L126–129 solo tratan `kimodo` y `rechazo`). `correr_escena.py` y `motor_blender.py` **no invocan** `vuelo_alas.py` | No hay evidencia de un vuelo real filmado por ese módulo en las corridas de Guardianes | **Hecho sin conectar.** El archivo y el clasificador existen; el motor vivo no ejecuta el vuelo. Si el 01 pide «volar», no hay cadena completa hasta Blender |
| «Si no lo conoce, Argon escribe una receta y el revisor la prueba, 4 intentos, se guarda» | L1746 | Eso es exactamente `m3_router.adaptar` (L64+) + topes 0,75 / 3,0 | La función está en el archivo; **ningún caller** en cine_v1 | No hay ledger de esas recetas de movimiento en el camino vivo | **Solo dicho / código huérfano** |
| Piquito aletea (poses Argon) | L1736, L1742 | 64 candidatos de pose, no un ciclo de vuelo del router | poses/v004, sin approval_ref | Las poses se pagaron; el anclaje al hombro fue un parche aparte | **Poses hechas; vuelo no** |

**Conclusión de locomoción:** el otro Inmi **sí colocó** caminar, girar y sentarse (Mwni + clips + pies +, más tarde, Kimodo). **No colocó correr** como movimiento distinto (lo traduce a caminar). **No conectó volar**: dejó el enrutador y `vuelo_alas.py` sin usarlos en la cadena viva. La tabla final no afirma que correr/volar estén listos; afirma caminar/girar/sentarse. Si la lectura de Ricardo es «en el Word dijo que ya había arreglado correr y volar», esa lectura **no está sostenida por una frase de cierre**; lo que hay es un plan (L1745) que **no se terminó de cablear**.

### E.4 Respuesta directa a «¿dijo que lo hizo y no lo colocó?»

Sí, en varios puntos concretos:

1. **Investigación Argon de personajes no humanos «como en la fábrica conectada»** — lo describió como camino de la fábrica (L1757, L1593) y lo corrió en staging, pero **no lo enganchó** al worker ni a n8n producción. Hoy un ave nueva se sigue parando en `esperando_pago_argon`.
2. **La ficha Argon de Piquito (29/38)** — la pagó y la citó como base del molde (L1586); **no es** la ficha publicada (ejemplo manual 23/17).
3. **«Motores completos en n8n» / Tabla 3 «Fábrica de … = Sí»** — están en una **copia apagada**, no en el flujo de producción.
4. **Correr y volar** — quedaron en el plan de L1745–1746; correr se implementó como caminar; volar y las recetas autónomas de Argon (`adaptar`) no están en la cadena que filma.
5. **Formas nuevas orgánicas / TRELLIS / puntos de Star en el ADN del sello** — lo habló (L9–17, L175–180) y **no lo conectó**.
6. **Unión de capítulo y revisión de filmación cada 5 minutos** — la tabla dice «Sí»; él mismo dejó la unión sin confirmar, y los 5 minutos no corresponden a una revisión de video.

Lo que **sí colocó de verdad** (código + uso): plantilla humana y construcción GPU de moldes; recetas de objeto/escenario en el servicio de fábricas; A*+RVO2; Mwni para caminar/girar/sentarse; foot-lock; Kimodo (después de la tabla que lo daba por apagado); sello de ADN; poses de Piquito pagadas y guardadas como candidatos; cámara calculada + Shakify opcional.

