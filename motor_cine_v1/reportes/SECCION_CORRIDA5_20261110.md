
### Corrida 5 (Kimodo ON, arreglo de bordes) — 10-nov-2026, 03:36–04:06 hora Bogotá

- **Hallazgo**:
  - Kimodo siempre arranca con rumbo canónico (−90°) y gira hacia la restricción durante su primer 0.5 s de relleno.
  - Después de la última restricción, el rumbo deriva. Por ejemplo, el giro de Spark terminaba en −132° en vez de −90°.
  - Esto, más la mezcla de 6 cuadros con el reposo CMU, era lo que hacía resbalar los pies en los bordes.
- **Arreglo en el motor** (sin tocar ajustes de Kimodo, del foot-lock ni el 01):
  - En los rellenos de pie se usa la pose de Kimodo congelada en la primera y la última restricción.
  - Dentro del tramo, Kimodo va puro.
  - La transición al reposo CMU va fuera del tramo, con un borde adaptivo: al menos 6 cuadros, y si hay giro, a 45°/s o menos, como el planificador.
  - Respaldos: `respaldos/motor_blender_antes_*` en 213 y `fase3_10/respaldo_motor_blender_*` en la caja.
- Primero lo probé en la CPU de 213 con las salidas Kimodo de la corrida 4, en 4 pruebas: `corridas/dev_kimodo_bordes`. Una variante con reparto de residuo de raíz no ganó nada y se descartó.
- La corrida 5 pasó por la puerta SSH de n8n. Pod zrgsz1hm0x23v7 (RTX 4090), terminado, **US$0.39**.

| Personaje | resbale m/cuadro (4 → 5) | acel p99 | vel. articular °/s | ok |
|---|---|---|---|---|
| Don Caos | 0.0568 → 0.0568 | 9.28 → 6.54 | 2070.5 → 2070.5 | no → no |
| Spark | 0.0820 → **0.0604** | 17.11 → 9.21 | 536.2 → 494.9 | no → no |
| Valentina | 0.0489 → 0.0491 | 7.24 → 7.24 | 391.2 → 426.7 | sí → sí |
| Eco | 0.0567 → **0.0929** | 8.48 → 7.37 | 674.9 → 497.7 | no → no |
| Pintor | 0.0864 → **0.0371** | 10.83 → 7.66 | 696.0 → 511.0 | no → **sí** |

- Penetración: 0. Encuadre igual que en la corrida 4: 10 viñetas al 100 %, v8 al 72.2 % y v12 al 95.7 %.
- Ahora pasan 2 de 5, antes 1 de 5. El giro de Spark (cuadro 1079) quedó resuelto.
- Todavía no se cumple el resbale cero:
  - **Eco empeoró**: el resbale está en el primer cuadro de salida (805).
  - Spark: borde de entrada del giro (1042) y caminata (729).
  - Don Caos: dentro de su carrera (cuadros 400–421).
- Don Caos según el 01, que no se cambió: tramo 2 de 1.02 m en 2.5 s = **0.415 m/s** (unas 2.8× su caminata, 4.0 m/s a escala SOMA). Por eso tiene 2070 °/s.
- **Dónde está**:
  - 213: `/opt/myia-motor-unificado/v1_20261110/corridas/n8n_cn-los-guardianes-de_cap01_ep-89b_esc1_20261110_093635/salida/out/` (videos, `cuadros/`, `kimodo/`).
  - Caja: `fase3_10/videos_gpu_cap01_esc1/corrida5/`.
  - Volumen GPU: el motor en `/workspace/myia_gpu/motor/v1_20261110` y Kimodo en `/workspace/myia_gpu/kimodo`.
- **Gasto**:
  - GPU del motor, corridas 1–5: **US$1.65** (tope US$8). Argon: US$0.
  - Saldo RunPod: **US$8.91**.
- `gpu.tope_por_trabajo_usd` volvió a 1.5. Kimodo queda encendido. Ledger de la caja #348 cerrado.
