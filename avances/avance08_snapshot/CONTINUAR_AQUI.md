# AVANCE 08 — CONTINUAR AQUÍ
Actualizado: 2026-11-07T23:30:14.689750-05:00 (Bogotá).

## Estado comprobado, no promesas
- Base VPS: /opt/myia-motor-v9/avance08_20261107/.
- 2B completo conservado; preflight_bvh08.json: VALIDADO, 0 faltantes. Esto NO certifica ejecución completa.
- physics08_sanity_final.json pasa, con pruebas negativas. No se usa aprobación del modelo.
- movimientos08_prevalidacion_cpu.json: 15 movimientos únicos / 35 combinaciones personaje-movimiento pasan poses nativas, longitudes y soporte. NO certifica dinámica, continuidad, colisión ni equilibrio de escena.
- Margen propuesto de Piquito: 0.005 m, hombro izquierdo de Eco medido, attachment rígido; pendiente validar escena real completa. No llamarlo aprobado.
- Reglas fijas intactas: COM 20 m/s², articulaciones 600°/s, pie 0.05 m/frame.
- Colisión estática nativa BVH pasa sólo frame 1 del escenario; no extrapolar al resto.
- Oro: oro_bvh08_final/metricas_oro.json all_equal=true, 23/23. entrega/evidencias/oro_bvh08_codigo_vinculado.json vincula hashes de código; referencia intacta. El oro es regresión, no aprobación física de esc1.

## Bloqueo actual de preview CPU
preview_cpu08/resultado.json: BLOQUEADO / STAR_DATO_FALTANTE / camera/sensor_width_mm / SB/configuración cámara.
constructor.log confirma FaltaDatos: Falta sensor de cámara por dato.
Núcleo CPU existente: preview_cpu08/nucleo/escena.blend, 1320 cuadros, 24 fps; NO es preview final ni producción aprobada. Su metadata contiene avisos heredados; no usarla como certificación actual de Piquito/2B.
No inventé 36 mm ni otro sensor. No rehice llamadas Argon, no rendericé GPU y no modifiqué código.
Se observó proceso previo preview_cpu08.py (PID 48987) y constructor (PID 57475); comprobar su estado antes de lanzar otra ejecución. No dupliqué ni maté procesos.

## Siguiente agente
1. Revisar resultado.json, constructor.log, worker_resultado.json y procesos: podría haber otro ejecutor terminando; no ejecutar en paralelo sobre la misma salida.
2. Encontrar sensor_width_mm en fuente SB/cámara explícita ya aprobada; si no existe, pedir el dato o propuesta validable. No inventarlo ni ocultar el bloqueo.
3. Si requiere código, continuar con el agente Cursor existente y PR; NO unir PR #1 sin aprobación de Ricardo. Trabajar en candidata nueva con respaldo, nunca T317.
4. Con dato trazable y respaldo, repetir constructor/preview CPU por interfaz existente en salida nueva; mantener .off y gasto automático cerrado.
5. Exigir revisión física real de toda esc1: COM, articulaciones, pie, colisiones, huesos, raíces y margen de Piquito; no confundir prevalidación de 15 movimientos con aprobación dinámica.
6. Revalidar oro 23/23 sin cambiar tolerancias/hashes, y sólo después revisar preview visual. GPU NO autorizada en esta continuación; dejar listo y reportar.

## Costos comprobados
Ledger entrega/evidencias/ledger.json: AV08 US$0.225875, previo US$0.669088, total plan US$0.894963; reserva 0. Incremento de esta retomada: US$0; GPU US$0. Tope Argon AV08 US$10, plan ~US$50; asiento ANTES de cualquier gasto.

## Reglas innegociables
Sólo Ricardo aprueba. Respaldo antes de cambio; .off; no borrar. No tocar T317, 24_TRASPASO, v9_universal_calidad_20261106, ${VPS_PROHIBIDO}, pod 32soe7oh2f1gtf ni video-studio. No leer ni mostrar claves. Sólo nuevas carpetas bajo /opt/myia-motor-v9/ y flujo debwaH9svFMoTnOf con respaldo si hay cambio. No iniciar GPU; detener pods sin DELETE/terminate cuando corresponda. Nunca aceptar approved=true del modelo.
