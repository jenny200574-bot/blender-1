# Traspaso · Planeador de storyboard (ADAPTIVE CINEMATIC DIRECTOR) · 1-nov-2026

## Qué es
La caja «SB» lee el guion de la escena y la acción del 01 (accion_v1). Con eso arma el storyboard de la escena en viñetas. Cada viñeta trae 10 campos: intención, beats visuales, secuencia, director de imagen (plano, ángulo y lente con encuadre DSL), actuación, director de cámara (movimiento en DSL), ritmo, transición, audio/narración con tiempos y continuidad. Al final un traductor gratis pasa la cámara DSL a un archivo para Blender.

Etapas:
1. **Género y tono** (Argon, pago). Divide la escena en tramos de género.
2. **Perfiles por tramo** (código, gratis).
3. **Narrativa y 4. Plano/storyboard** (Argon, pago). Una sola llamada por escena.
4. **Validador** (gratis). Si encuentra errores, hace **reparación** de las viñetas que fallaron: como máximo 2, y solo si caben en el tope.
5. **Memoria de continuidad** (gratis). Pasa a la escena siguiente lo que debe mantenerse.
6. **Traductor** DSL→Blender (gratis).

## Dónde está (VPS 213, staging)
- **Código:** `/opt/myia-taller-n8n/cajas/storyboard/` (cubo_sb.py, validador_sb.py, memoria_sb.py, selector_perfiles.py, traductor_dsl_blender.py, prompts/, config/ajustes_sb.json, pruebas/). Las pruebas pasan 22/22.
- **Entrada desde n8n:** `cajas/entrada_ssh.sh` (verbo `storyboard`) → `cajas/paso00_cadena.py` (rama `storyboard`) → `cubo_sb.n8n()`.
- **Resultados por canal y capítulo:** `trabajo/paso00_cadena/<canal>/<cap>/cubos/SB/`:
  - `esc_N.json` (el storyboard)
  - `etapa1_generos.json`
  - `memoria_continuidad.json`
  - `blender/esc_N_camara.json`
  - `respuestas/` (texto crudo de Argon)
  - `rechazadas/`
- **Costos:** ledger `/opt/myia-staging-arreglos-20261026/ledger/ledger_argon.csv`, con ids `taller-SB-…`.
- **Guarda de pago:** `cajas/HABILITAR_PAGO_SB` (JSON: tope_usd, aprobado, opcional reanudar). **Normalmente NO existe.** Sin ella no se paga nada.

## Cómo se corre
- **En n8n:** en la copia `JTYnu9oItUj6okH9` (inactiva), sección «SB · Planeador de storyboard». Son 9 nodos entre «01 · leer» y «Armar tramo»:
  - cotizar → ¿con pago? (tope > 0) → correr (pago) → validar → traducir → Armar tramo.
  - Si tope = 0, no paga: solo cotiza, valida y traduce lo que ya exista.
- **Por consola**, como el usuario restringido de n8n:
  `sudo -u n8ntaller env SSH_ORIGINAL_COMMAND="paso00_cadena storyboard <cotizar|correr|validar|traducir> --canal <canal> --capitulo 1 --escena 9" /opt/myia-taller-n8n/cajas/entrada_ssh.sh`
- **Para pagar:** pedir antes el OK de Ricardo con el precio de «cotizar». Luego crear la guarda con el tope y el texto del OK, correr y **borrar la guarda**. Hay un ejemplo con trampa de borrado automático en `/root/respaldos_inmi/20261102_024219_sb_n8n/correr_real3.sh`.

## Primera corrida real (Génesis cap 1, escena 9)
- **Resultado:** 16 viñetas en 62 s, 3 tramos de género, 0 errores después de 1 reparación.
- **Costo total US$0,6473**, dentro del tope de US$0,91 aprobado por Ricardo (t345u):
  - Etapa 1, primer intento: US$0,1048, perdido. La respuesta llegó cortada porque el razonamiento del modelo se comió el tope de 8000 tokens. **Arreglo genérico:** ahora la etapa 1 analiza solo las escenas pedidas, con un tope de 16000 + 1500 por escena.
  - Etapa 1, segundo intento: US$0,0576.
  - Etapas 3+4: US$0,3658.
  - Reparación de 4 viñetas: US$0,1191. Usaron argumentos de cámara inválidos, por ejemplo `/CRANE:UP:WS>EWS` o `/SLIDER:R`.
- **Otros arreglos genéricos de esa corrida:**
  - Si `dsl_encuadre` viene vacío, el código lo arma con plano + ángulo + lente.
  - El texto fijo de reparación ya no se modifica, porque el registro de prompts fijos lo bloqueaba.
  - Existe la opción «reanudar» desde la respuesta ya pagada, sin volver a pagar la etapa 3+4.
- **Imagen:** `/workspace/informes/storyboard_real_esc9_20261101.png`.

## Decisiones pendientes de Ricardo
1. **Tono general del canal.** El nivel 1 de Génesis es mezcla de géneros. Falta decir el tono que se quiere.
2. **Nivel 2 (categoría/estilo visual)**: está «por definir».
3. **Nivel 3 (reglamento de arte y cámara, propuesto GD-CINEMATIC-ANIME-V1)**: está «por definir». Hoy no se exige para pagar, pero el storyboard sale sin reglamento.
4. **Nombres.** El guion y el 01 dicen Elian/Lía en algunos lugares, y las fichas Gael/Sofía (ids ch-protagonista / ch-la-novia). No se renombra nada sin su decisión.
5. **Narrador «cómico».** La configuración del canal pide narrador cómico, pero la escena 9 es dramática y no tiene narrador. Hay que decidir si el narrador aplica por escena.
6. **El 01 de la escena 9 sale con fps 8** (raro; lo normal es 24). Revisar de dónde sale antes de animar.
7. **El 02N todavía NO lee `blender/esc_N_camara.json`.** Hay que conectarlo, sin inventar alturas: el traductor usa solo las alturas medidas del diseño de Blender y deja «alturas_por_medir», por ejemplo IMI.

## Respaldo
`/root/respaldos_inmi/20261102_024219_sb_n8n/` contiene:
- el workflow de antes y el de después
- el original 7yIFt4JajvV1jxmD, solo como referencia
- cajas/storyboard antes del cambio
- paso00_cadena.py y entrada_ssh.sh antes del cambio
- los registros de las 3 corridas
