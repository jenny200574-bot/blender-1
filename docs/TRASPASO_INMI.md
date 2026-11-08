# ACTUALIZACIÓN PRIORITARIA — 2026-11-08T06:52:21.459144-05:00 (Bogotá)

Esta actualización prevalece sobre el corte histórico inferior. Sensor 36 mm aprobado por Ricardo; GPU autorizada y ejecución a cargo de otro agente. No duplicarla. Ledger Argon verificado: US$0.894963 bruto; GPU pendiente de conciliación, no se certifica gasto cero. PR #1 abierto, no unido ni activado. Oro previo 23/23, física completa y dinámica pendientes de evidencia. Ver GUIA_CONTINUAR.md para pasos, copias y límites. Este paquete agrega candidato BVH y snapshot reciente; no contiene renders/binarios pesados ni credenciales.

---
# Corte histórico (conservar como historial; NO estado actual)

# Traspaso de Inmi — para quien siga con el motor de Blender

Soy Inmi, la asistente que llevó este plan hasta el 7-nov-2026 (23:00, hora de Bogotá). Te dejo todo lo necesario para seguir sin mí. Léelo completo antes de tocar nada.

> Fuentes de este documento: la conversación con Ricardo, los informes `docs/avance0X_*` y las evidencias de `avances/`. Los informes `26_*`/`27_EJECUCION_PLAN_20261107` (incluido `PLAN_CONSOLIDADO.md`) están en el PC de Ricardo y **no** venían en este paquete; pídeselos si los necesitas.

## 1. Quién es el cliente
- **Ricardo, MYIA Estudio.** Produce series animadas infantiles (p. ej. *Los Guardianes de la Ceiba*) con un flujo automático: n8n → Argon (Gemini en Vertex) → motor de Blender → render en GPU (RunPod).
- Habla español; quiere respuestas cortas y claras.

## 2. Sus 4 objetivos
1. **Escenarios 3D reales** (geometría construida en Blender, no planos ni sustitutos).
2. **Sistema de puntos de Star**: anclas y contactos ejecutables por punto.
3. **Movimiento natural**, validado por física antes de renderizar.
4. **Automatización completa con Argon** desde n8n, sin pasos a mano.

## 3. Cómo trabajar con él
- Directo, en viñetas, sin informes enormes (su cuota de uso es limitada).
- **Control estricto de costos:** anota en el ledger **antes** de cada gasto (reserva → llamada → liquidación). Tope de fase US$10; presupuesto del plan **~US$50** (parada preventiva en US$45). Gastado: ~US$0.67 bruto hasta AVANCE_07 + US$0.23 en AVANCE_08 ≈ **US$0.90 bruto**, cubierto por créditos de Google (neto esperado US$0, no conciliado con factura). GPU: US$0.
- Código de calidad de producción: con pruebas, respaldo y evidencia.

## 4. Reglas de seguridad (todas obligatorias)
- **Nunca imprimas, copies ni subas claves** (cuenta de servicio, API keys, tokens, ssh). Refiérete a ellas solo por ruta.
- **Nunca sobrescribas** T317, `24_TRASPASO` ni `v9_universal_calidad_20261106`. Trabaja siempre en carpetas nuevas `avanceNN_YYYYMMDD`.
- **Nunca toques** el otro VPS `${VPS_PROHIBIDO}` ni el pod `32soe7oh2f1gtf`.
- **Solo Ricardo aprueba** cambios, gastos y borrados.
- Pods: **stop** al terminar, **nunca terminate/delete**. Ante un 403 de RunPod, detente y avisa; no busques rodeos.
- Antes de cualquier cambio: **respaldo** + dejar la función nueva apagada con su bandera **`.off`** hasta probarla.
- **Oro 23/23 exacto, con tolerancias sin cambiar**, después de cada cambio del motor.
- **Nunca inventes valores** (física, medidas, 2B, aprobaciones). Si falta algo, el motor responde BLOQUEADO con la lista de faltantes.
- No borres `/opt/video-studio`: lo usan los nodos 3b y 4e (ver §5).

## 5. Infraestructura
- **VPS** `${VPS_HOST}` (Ricardo te da el acceso; el agente en la nube NO lo tiene). Base: `/opt/myia-motor-v9/`.
  - Motor T317 instalado: `v9_motor_unico_20261107/` (puente de entrada `entrada_motor.py/.sh`).
  - Copia de trabajo más reciente: `avance08_20261107/MOTOR_UNICO_20261107/` (es la que está en `motor/` de este repo).
  - Fases: `avance04_20261107` … `avance08_20261107`, cada una con `entrega/`, `esc1_candidata/`, respaldos `esc1_antes*`.
- **n8n:** contenedor `myia-taller-n8n`, workflow **`debwaH9svFMoTnOf`** ("COPIA LIMPIA · MYIA capítulo desde 0"), 577 nodos, activo. **Ruta única: 02T → 02**; la rama vieja 02N quedó desactivada (no borrada). Nodos clave en `n8n/`.
  - 02T: "traducir entrada T317" (SSH) → "validar esquema y faltantes" → "¿entrada completa?" → si no, "detener y reportar faltantes".
  - 02: "animar en Blender" (SSH, vía puente) → "resultado T317".
  - Nodos de pago `SELLO … sello_pago` (compuerta + tope + ledger): aceptan el JSON nuevo sin romper el formato viejo (AVANCE_06). El pago automático nuevo sigue apagado hasta la prueba final.
- **Puente SSH restringido** desde n8n: solo puede correr el motor y el generador nuevo (ampliado en AVANCE_06, respaldos en `avance06_20261107/respaldos/`).
- **Credencial de Argon:** archivo protegido en el VPS, `${VERTEX_SA_FILE}` (cuenta de servicio). En el código aparece como `${VERTEX_SA_FILE}`. Proyecto `${GCP_PROJECT_ID}` (un proyecto `gen-lang-client-…` de AI Studio, con facturación y créditos).
- **Vertex:** modelo `gemini-3-flash-preview`, ubicación `global`, esquema estricto (JSON tipado). Otros modelos no están habilitados en ese proyecto. La API de Gemini directa no acepta cuentas de servicio.
- **RunPod:** pod de render **`pul0wcedwdkwm7`** (detenido). Usar solo resume → render → copiar video → stop.
- **video-studio** (`/opt/video-studio`): el nodo **3b "Cargar mi guion"** lee `studio.db` y el nodo **4e "Aprobar precio"** usa su panel en el puerto 8602. Ricardo solo autorizó (pendiente de su sí) liberar `media` y `backups`, nunca el código ni `studio.db`.

## 6. Decisiones tomadas por Ricardo
- **Física:** Argon propone los valores físicos de cada escena y el motor los valida; si son absurdos, se rechazan y se vuelve a pedir. Tres reglas fijas de la fuente vigente: aceleración COM 20 m/s², velocidad articular 600°/s, deslizamiento de pies 0.05 m/cuadro. No importar valores de T317.
- **ADN + esqueleto en una sola llamada** de Argon.
- **Cámara del SB numérica.**
- **Capítulo 1 (T01) es la fuente de la 2B** (`escenas/fuente_capitulo1/`).
- La programación pesada pasa a agentes de Cursor en este repo; Inmi/Ricardo prueban, conectan y validan en el VPS.

## 7. Plan y estado
**Hecho**
- Respaldo de n8n original; espacio liberado en el VPS.
- Motor T317 instalado con puente restringido; 11 funciones activadas una a una (205 pruebas cada vez), oro 23/23.
- Ruta única 02T → 02 publicada; 02N desactivada.
- Argon conectado con esquema estricto.
- Puente ampliado al generador nuevo; nodo de pago adaptado al JSON.
- Esc1: cámara, recetas 3D de cama y cofre, Piquito (19 huesos, 40 piezas), 3 luces + ambiente, 4 ADN locales (libro, visor, ventana, tapete), escenario vivo (27 pistas / 59 aserciones; 54 de activos pasan).
- AVANCE_08 (en curso al cerrar este paquete): 2B completada con el capítulo 1 (52 filas, citas literales, sin ángulos nuevos inventados); física propuesta por Argon con prueba de sensatez pasada; hombro izquierdo de Eco medido; 15 movimientos admitidos para prueba CPU; preflight de datos = 0 faltantes. **Física de escena aún no aprobada.**

**Pendiente**
1. Preview CPU completa de esc1 desde los datos de AVANCE_08 y revisión de colocación en conjunto (dudas centro/esquina en ventana/tapete).
2. Aprobación técnica de los 15 movimientos y de la física de escena.
3. Meter los prompts nuevos (ADN+esqueleto, sello de objetos, escenario vivo, cámara SB, física) en los nodos de n8n.
4. Terminar 02T para que arme cualquier escena, no solo la 1.
5. Corrida de esc1 desde n8n de punta a punta; render GPU en `pul0wcedwdkwm7`; stop.
6. Escena 4 y una escena de otro canal.
7. Validación final: motor, llamadas Argon estructuradas, todas las funciones activas.
8. Respuesta pendiente del otro Ako sobre `argon_transporte`.

**Historial de carpetas AVANCE**
- AVANCE_01–03 (`27_EJECUCION_PLAN_20261107\AVANCE_0X\` en el PC de Ricardo): puente T317, activación de funciones, n8n 02T→02, bloqueo de facturación.
- AVANCE_04: credencial Vertex, primera llamada (31 errores de formato, nada aplicado), traductor 02T.
- AVANCE_05: esquema estricto; esc1 de 23 a 18 faltantes.
- AVANCE_06: puente ampliado, nodo de pago JSON, Piquito, luces; 18 → 15.
- AVANCE_07: ADN, escenario vivo, reglas físicas fijas; 15 → 7 bloqueos.
- AVANCE_08: 2B desde el capítulo 1 y física por Argon (sin informe final al empaquetar).

## 8. Cómo seguir, paso a paso
1. Lee `AGENTS.md`, `README.md`, `docs/avance07_INFORME_AVANCE_07.md`, `docs/avance07_7_BLOQUEOS_ESC1.csv` y `avances/avance08/evidencias/*.json`.
2. Corre los tests en seco (`cd motor && for t in pruebas/test_*.py; do python3 -B "$t"; done`).
3. **En el repo (agente en la nube):** generaliza 02T (`avances/avance04/codigo/traductor_02t.py`) para cualquier escena; integra los prompts/esquemas de `avances/avance0X/codigo/generar_schema.py` en el código de los nodos `n8n/nodos/*.js`; refuerza el revisor de física para validar lo que proponga Argon. Todo con tests y nada activado por defecto (`.off`).
4. **En el VPS (Ricardo o Inmi):** crear `avance09_YYYYMMDD`, respaldar, aplicar, oro 23/23, preview CPU de esc1.
5. Con preview aprobado por Ricardo: anotar en el ledger, resume del pod `pul0wcedwdkwm7`, render, copiar video, **stop**.
6. Publicar los cambios de n8n con respaldo y correr esc1 desde n8n de punta a punta.
7. Repetir con escena 4 y una escena de otro canal; validación final.
8. Informe corto a Ricardo en cada paso: hecho / falta / gasto.
