
### Corridas 3 y 4 (Kimodo ON) — 10-nov-2026, hora Bogotá

**Qué se hizo** (Ricardo t983u/t995u: Kimodo obligatorio, dentro del motor y en GPU)
- Kimodo quedó encendido en el motor de 213 (`/opt/myia-motor-unificado/v1_20261110`, `config_motor.json` → `kimodo_encendido: true`; respaldos en `respaldos/`). Los ajustes son los del lab aprobado y no se tocaron: Kimodo-SOMA-RP-v1.2, seed 7, 1 muestra, `--no-postprocess`, root2d cada 0.5 s + heading, foot-lock thr_z 0.025 / thr_v 0.15 / min_seg 3 / borde 6, con los contactos de Kimodo.
- Pesos: crecí el volumen RunPod sa3r0sj70m de **10 a 40 GB** (solo crecer, sin borrar). Cuesta **+US$2.10/mes** (total US$2.80/mes). Kimodo y los pesos (17 GB) quedaron instalados en `/workspace/myia_gpu/kimodo`. La corrida 4 los reutilizó sin bajarlos de nuevo.
- Ambas corridas se lanzaron por la misma puerta SSH de n8n (`motor_unificado correr …`). Kimodo generó 10/10 tramos: Don Caos 2 de correr; Spark, Valentina, Eco y Pintor uno de caminar y uno de girar cada uno.
- **Corrida 3** (01:20–02:05, pod ss02bynsd2dqsb, L4, terminado, **US$0.43**):
  - Tenía un error de integración. La cadera de los tramos Kimodo quedaba a otra altura que la de los clips CMU.
  - Por eso, fuera de los tramos Kimodo, los personajes **flotaban** (Spark unos 0.8 m) y la cámara los siguió: encuadre de v1 5.6 %, v6 0 %, v12 0 %.
  - Su resbale "bajo" no es válido, porque con los pies en el aire no cuentan como apoyo.
- **Arreglo** (sin tocar ajustes de Kimodo ni del foot-lock): la cadera de pie de Kimodo se iguala a la del clip quieto del mismo molde. Respaldo en `respaldos/motor_blender_antes_nivel_kimodo_*.py`.
- **Corrida 4** (02:25–02:48, pod olna3bidjammxo, RTX 4090, terminado, **US$0.34**): personajes en el piso y encuadre restaurado.

**Compuerta: corrida 2 (sin Kimodo) → corrida 4 (Kimodo ON)**

Umbrales: aceleración p99 ≤ 20, velocidad articular ≤ 900 °/s, resbale ≤ 0.05 m/cuadro, encuadre ≥ 80 %.

| Personaje | acel p99 | vel. articular °/s | resbale m/cuadro | ok |
|---|---|---|---|---|
| Don Caos | 9.74 → 9.28 | 1529.6 → 2070.5 | 0.0771 → 0.0568 | no → no |
| Spark | 7.75 → 17.11 | 397.8 → 536.2 | 0.0724 → 0.0820 | no → no |
| Valentina | 7.74 → 7.24 | 267.7 → 391.2 | 0.0700 → **0.0489** | no → **sí** |
| Eco | 8.93 → 8.48 | 336.5 → 674.9 | 0.0859 → 0.0567 | no → no |
| Pintor | 7.66 → 10.83 | 380.9 → 696.0 | 0.0550 → 0.0864 | no → no |
| Piquito | acoplado | — | — | sí → sí |

- Penetración: 0 en todos. Separación entre pares: OK.
- Encuadre:
  - Corrida 2: 11 viñetas al 100 % y v12 al 95.7 %.
  - Corrida 3: roto (v1 5.6 %, v6 0 %, v12 0 %).
  - Corrida 4: 10 viñetas al 100 %, v12 al 95.7 % y **v8 al 72.2 %** (bajo el 80 %).
- **El resbale cero todavía no se cumple.** Mejoró en Don Caos, Valentina y Eco, y empeoró en Spark y Pintor.
  - El resbale que queda está en los **6 cuadros de borde** de cada tramo Kimodo, donde se mezcla con el reposo CMU (cuadros 709–715 y 797–804), y en el giro de Spark (cuadro 1079).
  - En Don Caos, el resbale está dentro de su carrera (cuadros 400–421).
  - Don Caos tiene **2070 °/s**, por la carrera que pide el 01.
- **Velocidad de Don Caos según el 01 (el 01 no se cambió):**
  - Tramo 1: 0.45 m (≈ 0.22 m/s en la escena, 2.19 m/s a escala SOMA).
  - Tramo 2: 1.02 m en 2.5 s = **0.415 m/s**, unas 2.8× su caminata. A escala SOMA son **4.0 m/s**: una carrera rápida para un muñeco de 0.18 m.
- Siguiente paso (no hecho esta noche): que los bordes de los tramos Kimodo empiecen y terminen con los pies de Kimodo plantados, en vez de mezclarse con el reposo CMU, y revisar los contactos en el giro y en la carrera. Esto necesita el visto bueno de Ricardo, porque toca la transición.

**Dónde está**
- 213:
  - Corrida 3: `/opt/myia-motor-unificado/v1_20261110/corridas/n8n_cn-los-guardianes-de_cap01_ep-89b_esc1_20261110_071954/salida/out/`
  - Corrida 4: `…/n8n_cn-los-guardianes-de_cap01_ep-89b_esc1_20261110_082447/salida/out/`
  - Videos de cada corrida: `REVISION_GRANDE_1920x1080.mp4`, `final_camara_sb.mp4`, `revision_vista_amplia.mp4`, `revision_planta.mp4`, `cuadros/`, `kimodo/`
- Volumen GPU: el motor está en `/workspace/myia_gpu/motor/v1_20261110` y Kimodo en `/workspace/myia_gpu/kimodo`.
- Caja:
  - `fase3_10/videos_gpu_cap01_esc1/corrida3_kimodo/`
  - `fase3_10/videos_gpu_cap01_esc1/corrida4_kimodo_nivel/`

**Gasto**
- GPU de este paso: US$0.43 + US$0.34 = **US$0.77** (tope del paso US$1.5).
- GPU del motor en total (corridas 1–4): **US$1.26** (tope US$8). Argon: US$0.
- Saldo RunPod: **US$9.36**. No quedó ningún pod nuestro corriendo; el pod de Star (32soe7oh2f1gtf) no se tocó.
- Volumen: +US$2.10/mes.
- Ledger de la caja: #346 y #347 cerrados.
