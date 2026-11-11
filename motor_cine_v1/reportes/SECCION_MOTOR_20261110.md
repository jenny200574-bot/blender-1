
---

## MOTOR — motor unificado de animación v1 (fases 3–10), noche 9→10 nov 2026

Autorización: Ricardo t1003u/t1004u/t1005u + t1010u (plan y motores aprobados por escrito, hasta completar dentro de US$50). Horas en Bogotá (UTC-5).

### Dónde vive (lo que manda es 213 / n8n / volumen GPU; la caja es solo espejo)
| Pieza | Máquina | Ruta |
|---|---|---|
| Motor v1 (código + addons + mocap) | 213 | `/opt/myia-motor-unificado/v1_20261110/motor/` |
| Configuración (topes GPU, volumen, Kimodo) | 213 | `/opt/myia-motor-unificado/v1_20261110/config_motor.json` |
| Puerta para n8n | 213 | `/opt/myia-motor-unificado/v1_20261110/entrada_motor.sh` → `motor/entrada_n8n.py` (preparar / correr / estado). Interruptor de apagado: crear `entrada_n8n.off` en esa carpeta |
| Bloque en la caja SSH de n8n | 213 | `/opt/myia-taller-n8n/cajas/entrada_ssh.sh` (bloque `motor_unificado`; respaldo en `/opt/myia-taller-n8n/respaldos/puerta_ssh/`) + `/etc/sudoers.d/myia-motor-unificado-v1` |
| Corridas (entrada, plan, reporte, videos) | 213 | `/opt/myia-motor-unificado/v1_20261110/corridas/<id>/` (videos en `salida/out/`) |
| Librerías 213 (A* python-pathfinding + RVO2 compilado) | 213 | `/opt/myia-motor-unificado/v1_20261110/py213/` |
| Ledger GPU del motor | 213 | `/opt/myia-motor-unificado/v1_20261110/ledger_gpu_motor.json` (+ caja `/workspace/COMUN_PRUEBAS/ako/ledger.json` #343) |
| Respaldos | 213 | `/opt/myia-motor-unificado/v1_20261110/respaldos/` |
| Motor en el volumen GPU | RunPod volumen `sa3r0sj70m` (EU-RO-1) | `/workspace/myia_gpu/motor/v1_20261110/` y corridas en `/workspace/myia_gpu/motor/corridas/<id>/` |
| n8n | COPIA FABRICAS `d2Bwmk2j4ijX28eK` | rama lateral **MU ·** (10 nodos, ENCENDIDOS) colgada de «SB · leer traducción» |
| Espejo caja | caja | `/workspace/TRASPASO_20261109/motor_fases/fase3_10/motor_v1/` |

### Fase 3 — Blender 5.2.3 + GPU EGL + carpeta versionada
- Blender 5.2.3 LTS en 213 (`/opt/blender/5.2.3/blender`, CPU, para pasos livianos) y en el volumen GPU (EGL NVIDIA, `--gpu-backend opengl`).
- Carpeta versionada `/opt/myia-motor-unificado/v1_20261110/` (la v0 de la fase 2 queda intacta en `v0_fase2_20261109`).

### Fase 4 — el motor NO crea nada
- `m1_preparar.py` solo carga moldes de la biblioteca (`/opt/myia-biblioteca/<canal>/`), toma la última versión `blend` de cada `meta.json`, copia con sha256. Si falta un molde → `STOP MOLDE_FALTANTE` y dice quién arregla (fábrica). El reporte trae `crea_geometria: false` y `moldes_modificados: false`.
- Estados aceptados en prueba: aprobado / publicado / hoja_lista (marcados «pendiente aprobación Ricardo»).

### Fase 5 — ADN de altura ±2 %
- `escala_adn.py`: mide el molde y solo escala si se sale de ±2 % del ADN. Cap01: Piquito 0.1744 m → escalado a 0.18 m; Pintor y los demás dentro de tolerancia (sin escalar).

### Fase 6 — movimiento
- Traductor `m3_traductor.py`: 01 (+2B si existe) → `movimiento.json` (quieto/caminar/girar/acoplarse, gestos hablar/mirar/señalar, aparecer). Acople solo si el 01 dice `acoplarse` (Piquito → hombro_L de Eco).
- Router de movimientos especiales `m3_router.py` (vuelo con/sin alas, pelea exagerada, sin forma → Kimodo o reporte_rechazo; 4 intentos; ledger antes/después, 20 s entre llamadas, para con 429, ≤US$0.75 por llamada). Cap01 no tiene movimientos especiales → 0 llamadas Argon.
- Mocap: CMU (13_01 reposo, 02_01 caminar, **02_03 trote nuevo** para personajes pequeños cuando el 01 pide >1.6× su caminata) + 100STYLE disponibles; retarget con **Mwni animation_retargeting** sobre copia temporal de la armadura.
- **Foot-lock aprobado sin cambios** (`pies_bloqueo.py`, idéntico al del video aprobado), sobre el piso real (raycast).
- Planificador **A* (python-pathfinding) + RVO2** con obstáculos del set inflados; giros en el sitio repartidos en todo el tramo del 01.
- Kimodo: empaquetado pero **APAGADO** (`kimodo_encendido: false`): los pesos no caben en el volumen y cap01 no lo necesita.

### Fase 7 — escenario vivo y extras (solo piezas de fábrica)
- Escenario: molde de la biblioteca `esc-habitacion` v001 (`/opt/myia-biblioteca/cn-los-guardianes-de-la-9fb323be/escenarios/esc-habitacion/blend/v001/esc-habitacion_star_recetas.blend`), 454 objetos, 3 luces del molde, piso real por raycast (piso, alfombra, estantería baja como caminables).
- Apariciones del 01 con objetos que YA existen en el molde: cofre dorado + candados aparecen desde el cuadro 721.
- Reglas «vivo» (girar/flotar/fluir/ondear) listas; el escenario de cap01 no trae piezas marcadas `vivo` → 0 animadas. `pedir_a_fabrica`: vacío.
- Cocina y jardín tienen cajas FALTA: no se usaron (la prueba usa la habitación completa).

### Fase 8 — cámara = storyboard tal cual
- 12 tomas desde el SB v2 con `altura_m` (`tomas_desde_sb`), `camara_calculada` (mirar_sin_roll + quitar_roll, lado L/C/R, ángulo HIGH/LOW/EYE), movimientos STATIC/DOLLY/PAN/TRACK/CRANE, keys CONSTANT por cuadro en `camera_4g_master` + marcadores.
- `ocultar_estorbos` + `camara_sin_paredes` por toma: objetos que tapan se ocultan solo para cámara en esos cuadros (18 ocultamientos). Lo protegido no se oculta: cuando un personaje protegido tapa a otro queda como «conflicto» en el reporte (composición del SB, no se mueve la cámara).
- Avisos al storyboard (02N): v3 y v7 traen `giro_grados` = «por decidir en 02N» → se usó 0 y la panorámica sigue al objetivo.
- AnyShot, Add Camera Rigs y Shakify: empaquetados en `motor/assets/` pero NO usados en el corte (el SB ya fija cada toma y no pide temblor). Se usan solo si el SB lo pide.
- Chequeo de encuadre (centro de la cabeza del objetivo dentro del cuadro): 11 tomas 100 %, v12 95.7 % (ECU) → cámara OK.

### Fase 9 — n8n (COPIA FABRICAS `d2Bwmk2j4ijX28eK`)
- Respaldo antes: caja `/workspace/TRASPASO_20261109/motor_fases/fase3_10/n8n/copia_fabricas_antes_motor.json` y el candado guardó `/opt/myia-taller-n8n/respaldos/flujo/candado_antes_20261110_045137_c79658e5.json`.
- Guardado SOLO con `guardar_flujo.py --wid d2Bwmk2j4ijX28eK` (seco primero, luego real): 592→602 nodos, 538→547 aristas, 0 quitados. updatedAt `2026-11-10T03:51:38.738Z` (= 9-nov 22:51 Bogotá).
- Rama lateral **MU ·** desde «SB · leer traducción»: preparar (gratis) → leer → ¿moldes completos? → ▶ correr en GPU (topes del motor) → leer lanzamiento → esperar 45 min → ver estado y videos → resultado. Si faltan moldes: «✋ faltan moldes o datos» (no gasta). Todos los nodos ENCENDIDOS. Lo que recibe el motor: canal / capítulo / escena del nodo «Entradas» (validados por regex en la puerta).
- Puerta: n8n entra por SSH restringido (n8ntaller) → `entrada_ssh.sh` (bloque `motor_unificado`) → `sudo -n entrada_motor.sh` → `entrada_n8n.py`. Probado: preparar OK (6 personajes, 0 faltantes), estado OK, comando desconocido → «comando no permitido».
- Flujos prohibidos verificados sin cambios: 7yIFt4JajvV1jxmD, JTYnu9oItUj6okH9, debwaH9svFMoTnOf (último cambio 8-nov). Producción no tocada.

### Fase 10 — prueba real en GPU (Guardianes cap01, escena 1, habitación + 6 moldes nuevos de la fábrica)
- Lanzada por la MISMA puerta que usa n8n (`motor_unificado correr …` como n8ntaller), nada a mano. Corrida 1 `n8n_cn-los-guardianes-de_cap01_ep-89b_esc1_20261110_054432` (pod 1vp9z6hc75kj5t, US$0.185) mostró los personajes GRISES en EEVEE: la fábrica guarda el color en `diffuse_color` y Blender 5 lo ignora en EEVEE. Arreglo en `render_motor.py`: copia ese mismo color al Base Color solo durante el render (el molde no cambia). **Corrida 2 (la buena): `n8n_cn-los-guardianes-de_cap01_ep-89b_esc1_20261110_062724`**.
- Pod 3i2964bo5ng0w2 (L4, SECURE+volumen, US$0.59/h), 1816 s, **US$0.306**, pod TERMINADO: True; Star 32soe7oh2f1gtf: EXITED (no tocado); saldo RunPod después: US$10.17.
- Render final: BLENDER_EEVEE en NVIDIA L4/PCIe/SSE2 (OPENGL), 1280x720, 1320 cuadros, 0.336 s/cuadro, colores del molde aplicados a 56 materiales.
- **Videos** (213 `/opt/myia-motor-unificado/v1_20261110/corridas/n8n_cn-los-guardianes-de_cap01_ep-89b_esc1_20261110_062724/salida/out/` · volumen `/workspace/myia_gpu/motor/corridas/n8n_cn-los-guardianes-de_cap01_ep-89b_esc1_20261110_062724/` · caja `/workspace/TRASPASO_20261109/motor_fases/fase3_10/videos_gpu_cap01_esc1/`):
  - `REVISION_GRANDE_1920x1080.mp4` (cámara del SB + vista amplia + planta + panel con viñeta/objetivo/estado de cada personaje)
  - `final_camara_sb.mp4` (1280x720, cámara del storyboard)
  - `revision_vista_amplia.mp4`, `revision_planta.mp4`; cuadros fijos por toma en `cuadros/`.
- **Gate de revisión** (umbrales del gate viejo: acel. cadera p99 ≤20 m/s², vel. articular ≤900 °/s, resbale ≤0.05 m/cuadro, penetración 0, separación ≥0.18 m, cabeza del objetivo en cuadro ≥80 %): **CON OBSERVACIONES (ok=False)**

| personaje | acel p99 | vel art máx °/s | resbale máx m/cuadro | penetración | ok |
|---|---|---|---|---|---|
| ch-don-caos-7adf | 9.74 | 1529.6 | 0.0771 | 0 | ✗ |
| ch-spark-468e | 7.75 | 397.8 | 0.0724 | 0 | ✗ |
| ch-valentina-a9be | 7.74 | 267.7 | 0.07 | 0 | ✗ |
| ch-eco-eff3 | 8.93 | 336.5 | 0.0859 | 0 | ✗ |
| ch-pintor-bce0 | 7.66 | 380.9 | 0.055 | 0 | ✗ |
| ch-piquito-030a | 0 | 0.0 | 0.0 | 0 | ✓ (acoplado) |

  - Separación entre pares: todas OK. Cámara OK: v1 100.0%, v2 100.0%, v3 100.0%, v4 100.0%, v5 100.0%, v6 100.0%, v7 100.0%, v8 100.0%, v9 100.0%, v10 100.0%, v11 100.0%, v12 95.7%.
  - Lo que falla: (1) resbale de pie 0.055–0.086 m/cuadro en las TRANSICIONES quieto↔caminar/girar sobre la alfombra (el foot-lock aprobado planta un pie; no lo cambié por orden de Ricardo); (2) Don Caos (0.18 m) vel. articular ~1500 °/s porque el 01 le pide 1 m en 2.5 s (2.8× su caminata) → se usa trote CMU 02_03 y aun así es rápido. Arreglos ya hechos esta noche: salto de pose T del BVH (bajó acel p99 de ~60 a <10), brazo de señalar fijo, giros repartidos, rampa 0.5 s.

### Gasto de la noche (parte motor)
- GPU: corrida 1 US$0.185 + corrida 2 US$0.306 = **US$0.491** (tope motor US$8). Argon: **US$0** (cap01 no tuvo movimientos especiales; sin credencial Argon en 213). Ledger caja #343/#344; ledger 213 `/opt/myia-motor-unificado/v1_20261110/ledger_gpu_motor.json`.
- Saldo RunPod ≥ US$5 en todo momento. Volumen `sa3r0sj70m` intacto. Pods del motor: todos terminados.

### Pendiente / decisiones para Ricardo
1. Ver `REVISION_GRANDE_1920x1080.mp4` y aprobar (o no) los moldes `hoja_lista` (marcados «pendiente aprobación»).
2. Resbale en transiciones: decidir si se permite ajustar la transición (no el foot-lock) o subir el umbral del gate para personajes pequeños.
3. 01 de cap01: velocidad de Don Caos (1 m en 2.5 s) — o se acepta trote o se alarga el tramo.
4. SB 02N: `giro_grados` de v3 y v7 «por decidir».
5. Kimodo GPU apagado (pesos no caben en el volumen); AnyShot / Add Camera Rigs / Shakify listos pero no usados en este corte.
6. Fábrica: avisar que los colores van en `diffuse_color` (el motor ya lo resuelve al renderizar); cocina y jardín aún con cajas FALTA.
7. Para apagar el motor desde n8n: crear `/opt/myia-motor-unificado/v1_20261110/entrada_n8n.off`. Todo queda ENCENDIDO.
