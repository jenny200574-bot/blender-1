# Plan etapa 11 y constructor — arquitectura, contratos, defectos demostrados y secuencia

Fecha: 2026-11-09 (UTC). Rama `cursor/camara-etapa11-construccion-43f7`, base `3d1653a` (= cámara, buscador y sonda instalados en avance13).
Estado: **PROPUESTO. Nada instalado, nada desplegado, sin GPU ni gasto.** No acredita escena real resuelta de punta a punta.

Leyenda de cada afirmación: **[plan]** lo que dicen traspaso/guías, **[código]** lo que hace el código del repo, **[integración]** lo que se ejecutó de verdad en avance13 según los artefactos transferidos, **[prueba]** lo que corrí aquí (Blender 4.2.3 LTS oficial, CPU, SHA-256 del tar `3a64efd1…` verificado contra blender.org).

---

## 1. Arquitectura real, de la entrada a la salida

| # | Paso | Quién lo produce | Archivo / función | Estado |
|---|---|---|---|---|
| A | Guion 01, 2B (movimientos), ADN+esqueleto, SELLO OBJ, escenario 4a2/4a4, storyboard SB (cámara numérica) | n8n + Argon (productores) | `cubos/01`, `cubos/SB/blender/esc_N_camara.json`, moldes | [plan] Argon propone, motor valida, Ricardo aprueba |
| B | 02T «traducir» | puente SSH | `entrada/entrada_motor.py: paquete()` reutiliza un paquete canónico **solo** si coinciden los hashes de 01, SB y molde; `traducir()` llama `orquestador.ejecutar(solo_validar=True)` | [código] |
| C | 02 «armar» | puente SSH | `entrada_motor.py: main()` con `armar` **nunca construye**: devuelve `DATOS_BLOQUEANTES`, `PRODUCCION_APAGADA` o `EJECUTOR_GPU_PENDIENTE` | [código] El export de n8n del repo puede no ser el workflow vivo; no lo asumo |
| D | Orquestador, 16 etapas | motor | `motor/orquestador.py: ejecutar()`; etapa 3 normaliza y copia a `paquete_normalizado`; etapa 4 `contrato.validar`; etapa 13 corre núcleo y constructor con `timeout=7200`; solo sella `compatibilidad_paquete.json` si no hay errores | [código] |
| E | Núcleo humanoide | motor | `nucleo_bueno_cpu.py` → `escena.blend` + `compatibilidad_nucleo.json` (hash de `heredado/*.py` + 3 extras + huella del legacy) | [código] |
| F | Constructor (worker) | motor | `constructor_final.py`, orden real: **6, 5, 8, anclas, 7, 9, 10, 12, 11, 13, guardado (14)** | [código] coincide con [integración] |
| G | Render CPU / montaje | motor | `render_cpu.py`, `montaje_cpu.py` (fuera de este alcance) | — |

**[integración] avance13 no siguió D→F.** `supervisor_oro_constructor.py` (no está en el repo; copia bit a bit `129187…` en PR #5) corrió oro y luego `constructor_final.py` **directo**, con `preflight_av11/paquete_normalizado` y `nucleo_reutilizable/escena.blend`, sin `timeout`, `-t 2`, stdout a archivo y variables de sonda. No pasó por n8n ni por la etapa 13 del orquestador.

**Oro 23/23 no cubre esto.** [código] `motor_unico.py: regresion()` solo ejecuta `nucleo_bueno_cpu.py` y compara 23 métricas de naturalidad (`heredado/revisar.py`). No ejecuta el constructor, la cámara, la revisión 13 ni el guardado. Oro 23/23 no dice nada sobre la salida final.

### Etapas del constructor: entrada, salida y aceptación ([código])

| Etapa | Qué hace | Lee (sin defecto) | Deja | Acepta si |
|---|---|---|---|---|
| 6 | Abre núcleo o escenario, World, detalle | `environment.mode/path/events`, `clock` | recibo `6`, `detalle_entorno.json` | recibos de paquete y núcleo coinciden (`exigir_paquete/exigir_nucleo`) |
| 5/8 | Rigs (núcleo, aviar o declarativo), apariencia, puntos | `entities[].appearance.geometry.parts`, `anatomy`, `rig` | recibos `5`, `8` | humanoide solo desde núcleo |
| anclas | `anatomia_perfiles.aplicar_anclas` | perfiles | recibo `anclas` | — |
| 7 | Props, puntos, **ejes de objetos** (`eje_objetos.alias_vacio`), bisagras | `props[]` | recibo `7` | genera ejes; no crea recursos que falten |
| 9 | Selección de movimientos | `motion.requests/candidates` | recibo `9` | candidato aprobado por solicitud |
| 10 | Retarget BVH e IK de contactos | `motion.retarget_jobs`, **`contacts`** | recibo `10` | — |
| 12 | Eventos y luces | `lighting.events/exposure/view_transform` | recibo `12` | grafo de eventos sin conflictos |
| 11 | Cámara SB_4G: `puente_sb4g.construir` → `camara_v2_blender.py` | SB, `resolver_inputs` (6 archivos), `render.resolution`, sensor 36 | `auditoria_4g/{entrada,config}.json` **antes**, `camara_v2.json` y `escena.blend` de auditoría **al final**, recibo `11` | sin `no_programado`, sin `falta_dato`, sin faltantes |
| 13 | Revisión: estados, cámara, largo de huesos, velocidad, contactos, `fisica_final.revisar` | `rules.*` | `revision_final.json`, `trazas_finales.json`, recibo `13` | `errors == []`; si no, **no hay escena.blend** |
| 14 | `pack_all` + guardado | — | `escena.blend`, `worker_resultado.json` `CONSTRUIDO_REVISADO` | solo tras 13 limpia |

---

## 2. Propiedad de los datos: productor → consumidor, obligatorio o derivado

| Campo | Productor | Consumidor | Clase | Si falta |
|---|---|---|---|---|
| `clock.fps/duration_s` | 01 | todo el worker | obligatorio | bloquear |
| `assets[]` path+sha+bytes | empaquetador | etapa 1, preflight | obligatorio | bloquear |
| `compatibilidad_paquete.json` | orquestador (solo con 0 errores) | constructor etapa 6 | obligatorio | bloquear (rehacer preflight) |
| `compatibilidad_nucleo.json` | `nucleo_bueno_cpu` | constructor etapa 6 | obligatorio con núcleo | bloquear (rehacer núcleo) |
| `camera.source` + `resolver_inputs` (config, ajustes, commands, sb_scene, elevations, shot_types) | SB / 4g | `puente_sb4g`, `camara_v2_blender` | obligatorio | bloquear |
| **claves del `config` de cámara del paquete** | SB/4g | `camara_v2_blender.py` (lee `CFG[...]` del paquete, **no** `motor/camara_v2_config.json`) | obligatorio, depende de la versión del código | bloquear si falta una clave que lee la versión instalada |
| `sensor_width_mm = 36` | Ricardo (t43u) | `medir_objetivo_camara.sensor_ancho_mm` | obligatorio | bloquear |
| plano de cada viñeta ∈ tabla de encuadre | SB + ajustes | `region()/emplazar()` | obligatorio | bloquear (toma no emplazable) |
| lente | SB | buscador | recomendado | aviso: el buscador no modela y valida la rejilla fija |
| **SB `altura_m` / `keyframes[].distancia_m`** | — | **nadie** | **derivado por etapa 11** | ver §3 |
| `contacts` (IK actor→punto) | 01/2B/Star vía `puentes_fisicos.compilar` | etapas 10 y 13 | obligatorio con procedencia | ver §3 |
| `rules.*` (11 reglas) | reglas vigentes/4a2 vía `reglas_binding` | constructor 13 y `fisica_final` | obligatorio | bloquear |
| `rules.contact_pairs` | reglas/4a2 | `fisica_final` (exime superficies que se tocan) | opcional | — (no son contactos IK) |
| `_rules_bridge.locked_limits_connected` | `reglas_binding.compilar` | `fisica_final` | estado | ver §3 |
| `production_approved` | Ricardo, fuera del motor | nadie lo pone en `true` | estado | si llega `true` en la entrada: bloquear |

---

## 3. Los tres campos que reportó Coordinación

**`altura_m = null` en las 12 tomas ("por medir en 02N") — DERIVADO, no bloquea.**
- [código] `camara_v2_blender.py` no lee `altura_m` ni `distancia_m` del SB. `emplazar()` calcula la distancia con la fracción de altura visible del plano, la lente, el sensor y la altura **medida** del rig en el `.blend`; la altura sale de la elevación (`EYELEVEL…` vía `elevations`) o de un hueso (`alturas_hueso`). El resultado queda en `auditoria_4g/camara_v2.json` (`camara.loc`, `distancia_m`).
- Sí bloquea (y ya lo detecta el preflight) cuando la orden exige metros que la cámara no deriva: `ELEVATED/AERIAL/DRONEVIEW` sin altura, `PAN` sin grados/anclas, `CRANE` sin metros (`auditar_sb`).
- No se rellena a mano. Que sea null no explica un corte.

**`contacts = []` con `contact_pairs` en reglas — válido solo con procedencia; si no, bloquear.**
- Son dos contratos distintos. `contacts` = restricciones IK con hueso, punto, intervalo y tolerancia (etapa 10 las aplica, etapa 13 mide error y resbale). `rules.contact_pairs` = pares de colliders que la revisión física deja tocarse (`fisica_final.py`, conjunto `touch`). Unos no sustituyen a los otros.
- [código] `puentes_fisicos.compilar` solo crea `contacts` si el paquete no lo traía, y solo acepta una lista vacía si el programa 2B la declara completa (`status: complete` y `contacts: []`, o `anclas` con `physics_validated`). Si el paquete ya trae `contacts`, **no se vuelve a revisar su procedencia**: hueco de contrato. El preflight nuevo lo revisa: `[]` sin declaración del programa = `CONTACTOS_VACIOS_SIN_PROCEDENCIA` (BLOQUEO); `[]` declarado = AVISO (la etapa 13 no medirá resbale de manos/pies).
- Si la escena tiene apoyos o agarres en 01/2B y llegó `[]`, el dato está mal y lo corrige el productor, no el motor.

**`locked_limits_connected = false` — AVISO, no bloquea; la revisión queda más estricta.**
- [código] `reglas_binding.compilar` lo pone en `false` cuando la entrada no trae `locked_source_rules_not_yet_fully_integrated`. Entonces `fisica_final.revisar` marca `EQUILIBRIO` en **cada** cuadro fuera de `balance_margin_m`, en vez de aplicar los límites bloqueados (`equilibrio_cuadros_fuera_max`, `saltitos_max`). Puede hacer fallar la etapa 13; no la relaja. No se conectan límites inventados.

**`production_approved = false`** es el valor esperado en todos los artefactos; el motor nunca lo pone en `true`.

---

## 4. Defectos: demostrados, inferidos y no demostrados

| # | Tipo | Hallazgo | Evidencia | Estado |
|---|---|---|---|---|
| D1 | código / rendimiento | En la etapa 11, cuando la pose pedida falla, el buscador evalúa **682 candidatos** (31 acimutes × 22 factores) + bisección, y luego hasta 55 validaciones. Recorre candidato por candidato y la caché `env_bvh` guarda 6 cuadros: **reconstruye el BVH del escenario y hace `frame_set` por cada (candidato, cuadro)**. | `camara_v2_blender.py: env_bvh, validar, bucle de tomas`; `buscador_posicion_camara.py: buscar/fallos_de`. [prueba] escena sintética de 768 caras: 13 441 / 26 881 / 53 761 `frame_set` y casi igual de BVH para tomas de 12/24/48 cuadros, ≈1 120 por cuadro de toma, lineal. | **demostrado** que cuesta así; **no demostrado** que fuera lo que hacía el PID 19474 al morir |
| D2 | código / memoria | `CACHE` (todas las coordenadas de cada actor por cuadro) y `OTROS` (BVH de actores por cuadro) no tienen tope y crecen con todas las tomas. | `camara_v2_blender.py: medir, otros_bvh` | demostrado en código; tamaño real en la escena no medido |
| D3 | observabilidad | Blender ignora `PYTHONUNBUFFERED`; con salida a archivo, `print` y el propio banner quedan en búfer. Tras SIGKILL el log queda en **0 bytes**. | [prueba] Blender 4.2.3: 0 bytes con y sin `PYTHONUNBUFFERED`; 34 bytes con `line_buffering`/`flush` | **demostrado**: un log de 0 bytes no prueba que no hubo actividad |
| D4 | runtime | El supervisor quedó en `RUNNING` sin `returncode` ni `finished`: su `finally` no corrió. Un error Python del constructor habría dejado traceback, `worker_resultado.json` BLOQUEADO y `returncode`. Supervisor y constructor terminaron por señal o reinicio. | `supervisor_oro_constructor.py` + `secuencia_estado.json` (PR #5) | inferido del código; **causa NO DETERMINADA** (OOM, SIGHUP de sesión, kill o reinicio) |
| D5 | runtime | El supervisor no tiene tope de tiempo; el orquestador sí (7200 s). Disco del VPS al 97 % (3,1 GB libres) y `pack_all` + guardado pueden necesitar espacio. | supervisor; `orquestador.py` etapa 13 | demostrado en código |
| D6 | contrato | La corrida directa del constructor salta la compuerta del orquestador. El recibo del paquete prueba que hubo un `solo_validar` con 0 errores con **ese** código de compiladores ADN, pero no ata la versión de `contrato.py`, `puente_sb4g.py` ni la cámara. | `compatibilidad_artefacto.CODIGO_PAQUETE` | demostrado en código |
| D7 | contrato | El `config` de cámara viene del paquete; si es de otra versión puede faltar una clave que lee `camara_v2_blender.py` instalado (fallaría con `KeyError`, no colgaría). | `CFG[...]` | demostrado en código; el preflight lo comprueba |
| D8 | contrato | `contacts` presente no se revisa contra el programa. | `puentes_fisicos.compilar` | demostrado en código |
| D9 | despliegue | El parche `185656e` se rechazó por el preimagen de `pruebas/test_buscador_posicion_camara.py`: instalado `be6bc5b8` = versión de `1611c56`; el instalador de `3d1653a` nunca copió ese test (solo cámara, sonda y test del muestreador); el manifiesto esperaba `9b33eca0`. | hashes en git | **demostrado** |
| D10 | despliegue | La copia VPS tiene `motor/heredado/malla_cabeza.py`. `test_cargar_modulo_motor` lo rechaza a propósito. **No borrarlo a ciegas:** `archivos_nucleo()` incluye todo `heredado/*.py`, así que puede formar parte del recibo del núcleo reutilizable. | `compatibilidad_artefacto.archivos_nucleo` | demostrado en código; hay que cotejarlo con `compatibilidad_nucleo.json` |
| D11 | entorno de test | `test_malla_cabeza` lee `escenas/guardianes_esc1_candidata/entrada_escena.json`; si falta, rompe solo el test, no la entrada del constructor. | test | demostrado |

**Cámara sin salida y sin traceback no acredita la causa.** Lo que sí está acotado: el worker escribió el recibo `12` y no el `11`, así que estaba dentro de la etapa 11 (puente o `camara_v2_blender.py`) cuando lo terminaron desde fuera.

---

## 5. Cambios de esta rama, clasificados (nada declara cerrado el motor)

| Cambio | Resuelve (demostrable) | No resuelve | Evidencia |
|---|---|---|---|
| `buscador_posicion_camara.py`: `evaluar_por_cuadro`, precarga de rejilla y bisección por niveles, después repite el recorrido original sobre los resultados memorizados | D1 (buscador) sin cambiar listas, tolerancias, sensor ni desempates | causa de la muerte del proceso | `test_buscador_por_cuadro.py` (5 tests); informe idéntico al de `cec7cbe3` en 18 escenarios; los dos tests instalados (`be6bc5b8` y `9b33eca0`) pasan |
| `camara_v2_blender.py`: BVH del escenario por **firma exacta** (matriz, vértices evaluados y topología), validación de candidatos por cuadro con el mismo orden de corte, cachés por toma | D1 (validación), D2 | — | [prueba] Blender 4.2.3: `camara_v2.json` completo y todas las claves horneadas **idénticos** al instalado; 13 441→38 `frame_set` (12 cuadros), 23 390→76 (2 tomas), con escenario animado (hoja que gira + shape key) 21 074→339, idéntico |
| Bandera `motor/camara_lotes_por_cuadro.off` **presente** por defecto | regla .off del traspaso | — | con `.off` el recorrido es el instalado (mismos conteos y salida) |
| `progreso_camara.py` + puntos de progreso | D3, D5 (por toma/fase/cuadro, `progreso_camara.json` atómico, tope `MOTOR_CAMARA_LIMITE_S`, cancelación `MOTOR_CANCELAR_ARCHIVO`; las interrupciones heredan de `BaseException` para que ningún `except Exception` las trague) | — | `test_progreso_y_salida_constructor.py` |
| `constructor_final.py`: `line_buffering`, `ETAPA_INICIO/FIN`, `progreso_worker.json`, SIGTERM/SIGINT → `BLOQUEADO CANCELADO` con etapa y traceback, guardado atómico de `escena.blend` | D3, D4 (lo que se puede: SIGKILL sigue sin poder escribirse) | SIGKILL/OOM no dejan recibo | [prueba] constructor real: tope → `CAMARA_TIEMPO_AGOTADO` etapa 11, rc 17; cancelación → `CANCELADO` etapa 11; SIGTERM → `CANCELADO` etapa 6, rc 17; ninguno deja `escena.blend` |
| `preflight_constructor.py` (sin Blender) y `preflight_blend.py` (dentro de Blender, nunca guarda) | D6, D7, D8; geometría (NaN, colliders sin caras, objetos referidos ausentes) | no aprueba física ni escena | `test_preflight_constructor.py` (13 tests sobre paquete normalizado por el orquestador real); `probar_preflight_blend.py` en Blender 4.2.3 (rc 2, 5 bloqueos esperados, `.blend` con el mismo hash) |
| `validar_salida_constructor.py` | sin falsos OK: exige `CONSTRUIDO_REVISADO`, cabecera Blender y SHA del recibo, revisión sin errores, las 10 etapas y cámara sin bloqueos | — | tests + corridas reales |
| `despliegue/instalar_parche_etapa11.py` + `manifiesto_etapa11.json` | D9: preimágenes = lo instalado; **no toca** el test instalado; prohíbe física y código atado a recibos | — | `test_instalar_parche_etapa11.py` (seco, aplicar con respaldo, rechazo por hash, reversión sin borrar) |

Prueba de aceptación CPU completa: `pruebas/blender_camara/probar_constructor_sintetico.py` → orquestador `solo_validar` VALIDADO, preflight APTO, constructor real `CONSTRUIDO_REVISADO` con `escena.blend` validado, los tres cortes BLOQUEADO, y revisión/trazas/cámara **idénticas** al motor instalado (`3d1653a`).

### Límites de los fixtures sintéticos
- `fixture_4g_v5`: un ave, 16 cuadros, 2 tomas, sin núcleo humanoide. La escena del arnés de cámara: 768–12k caras, actores de ~600 vértices. No representan el costo, la memoria ni la geometría de la escena real; solo prueban equivalencia, orden y control.
- No se corrió oro, ni la escena real, ni el núcleo de avance13. Que el fixture construya no dice que la escena real pase la etapa 13.

---

## 6. Compatibilidad de versión
- Blender 4.2.3: acciones con `fcurves` (no `layers`); `curvas_accion.fijar_constante` ya cubre ambos. Lo nuevo usa `foreach_get`, `to_mesh` y `BVHTree.FromPolygons`, presentes en 4.2. Todas las pruebas de arriba son en 4.2.3.
- Python 3.11 de Blender: `sys.stdout.reconfigure` disponible.
- Preimágenes del instalador: cámara `a3962fd2…`, buscador `cec7cbe3…`, constructor `8eca43c3…`. El constructor instalado **no está cotejado** (es el «después» de `manifiesto_13.json`); si difiere, el seco lo rechaza y no escribe.
- Recibos: el parche no toca `heredado/`, `compatibilidad_artefacto.py`, `malla_cabeza.py`, `nucleo_bueno_cpu.py` ni los compiladores ADN, así que el núcleo y el paquete de avance13 siguen reutilizables.
- Linux: `ldd` de Blender 4.2.3 resuelve `libXrender.so.1`, `libXi.so.6`, `libxkbcommon.so.0`, `libSM.so.6`, `libICE.so.6`. Comprobación previa sin GPU: `ldd /opt/blender/actual/blender | grep "not found"` vacío y `blender --version` = `Blender 4.2.3 LTS`.

---

## 7. Evidencia VPS de solo lectura que falta (para acotar D1/D4 sin suponer)
1. ¿Existen `rebuild_tipoerror/auditoria_4g/entrada.json` y `config.json`? mtime (marca el inicio real de la etapa 11).
2. ¿Existe `sonda_tipoerror.json`? mtime (la cámara pasó su preámbulo y llegó al bucle de tomas).
3. ¿Existe `rebuild_tipoerror/worker_resultado.json`? (si no existe, confirma corte externo y no error Python).
4. mtime de `etapas_worker.json` (fin de la etapa 12).
5. `journalctl -k --since "2026-11-08 14:25"` filtrado por `out of memory|killed process`; `last -x reboot shutdown | head`; `uptime -s`.
6. Cómo se lanzó el supervisor (sesión SSH, `nohup`, `setsid`): SIGHUP al cerrar sesión mata a ambos.
7. SHA-256 de `motor/constructor_final.py`, `motor/puente_sb4g.py`, `motor/heredado/malla_cabeza.py`, y la lista de claves `codigo` de `nucleo_reutilizable/compatibilidad_nucleo.json`.
8. Salidas de `preflight_constructor.py` y `preflight_blend.py` sobre la entrada exacta (abajo).

---

## 8. Secuencia acotada para completar un BLEND revisado (no ejecutar sin aprobación de Ricardo)
Todo en `avance14_20261108_buscador` (copia aislada); original intacto.

```bash
A=/opt/myia-motor-v9/avance14_20261108_buscador; M=$A/MOTOR_BVH08_CANDIDATO; R=/ruta/repo/rama   # repo en esta rama
B=/opt/blender/actual/blender
ldd $B | grep "not found"; $B --version | head -1          # vacío / Blender 4.2.3 LTS
# 1) Seco del parche (no escribe)
python3 $R/despliegue/instalar_parche_etapa11.py --destino $M --origen $R/motor --manifiesto $R/despliegue/manifiesto_etapa11.json
# 2) Solo si el seco sale 0: aplicar con respaldo nuevo (la bandera .off queda puesta)
python3 $R/despliegue/instalar_parche_etapa11.py --destino $M --origen $R/motor --manifiesto $R/despliegue/manifiesto_etapa11.json --aplicar --respaldo $A/respaldo_etapa11
# 3) Tests CPU en la copia + aceptación sintética contra una copia sin parche
cd $M && for t in pruebas/test_*.py; do python3 -B "$t"; done
python3 -B pruebas/blender_camara/probar_constructor_sintetico.py --blender $B --salida $A/prueba_sintetica_1 --motor-referencia $A/<copia_sin_parche>
# 4) Preflight de la entrada exacta (solo lectura)
python3 -B motor/preflight_constructor.py $A/preflight_av11/paquete_normalizado --nucleo $A/nucleo_reutilizable/escena.blend --salida $A/preflight_constructor.json
$B -b --factory-startup --disable-autoexec $A/nucleo_reutilizable/escena.blend -P motor/preflight_blend.py -- $A/preflight_av11/paquete_normalizado --salida $A/preflight_blend.json
#    Cualquier BLOQUEO: parar y devolver al productor indicado. No completar a mano.
# 5) Con aprobación: quitar la bandera (equivalencia probada en 3) y construir en salida nueva
test ! -e $A/rebuild_etapa11
rm $M/motor/camara_lotes_por_cuadro.off   # reversible: volver a crearla
cd $A && nohup setsid timeout --signal=TERM --kill-after=120 7200 \
  $B -b --disable-autoexec -t 2 --python-exit-code 17 -P $M/motor/constructor_final.py -- \
  $A/preflight_av11/paquete_normalizado $A/rebuild_etapa11 $A/nucleo_reutilizable/escena.blend > $A/rebuild_etapa11.log 2>&1 &
#    Seguir: tail $A/rebuild_etapa11.log ; cat $A/rebuild_etapa11/progreso_worker.json $A/rebuild_etapa11/auditoria_4g/progreso_camara.json
# 6) Aceptación de la salida (lo único que puede decir BLEND revisado)
python3 -B $M/motor/validar_salida_constructor.py $A/rebuild_etapa11 --paquete $A/preflight_av11/paquete_normalizado
```
- En la copia del VPS: `test_instalar_parche_etapa11.py` se salta sin git (lo dice), `test_instalar_tipoerror.py` necesita git, y `test_preflight_constructor.py` y `probar_constructor_sintetico.py` necesitan `paquetes/fixture_4g_v5` (sintético del repo) y `jsonschema`. Un fallo por eso es de entorno, no del parche; se anota, no se ignora.
- 7200 s es el tope que ya usa el orquestador para el constructor; no es un valor nuevo. `nohup setsid` evita que cerrar la sesión SSH mate el proceso.
- Si la etapa 13 rechaza (tomas o física), el resultado válido es `BLOQUEADO` con `revision_final.json`: es una revisión verificable, no un fallo de la corrida. No se rebajan compuertas.
- Oro 23/23 se vuelve a correr aparte; no sustituye el paso 6.
- Reversión: `--revertir --respaldo $A/respaldo_etapa11` devuelve los tres previos y mueve los nuevos a `respaldo_etapa11/retirados/` sin borrar.

## 9. Qué falta para decir «resuelto de punta a punta»
- Correr 4→6 con la escena real y que el paso 6 dé `ok`; render/voz/lip-sync quedan fuera.
- Explicar D4 con la evidencia del §7.
- Revisar el workflow n8n vivo (bloqueado por ahora) antes de llamar automatizado algo corrido a mano.
