# AVANCE_06 — puente acotado, JSON publicado y esc1 parcial
Cierre: 2026-11-07 21:52 Bogotá (UTC-5).

## Estado real, sin confundir diseño con producción
- **Pasos de puente y n8n realizados con respaldo.** Sudoers válido (`visudo -c`); versión guardada y publicada verificada mediante API oficial.
- **Esc1 NO terminada:** prueba CPU REAL final bloqueada con **15 entradas**, frente a 18 al inicio. Video/master **ninguno (null)**. No se llegó al render de la escena.
- Piquito: diseño generado válido de **19 huesos y 40 piezas**, construido realmente en Blender CPU. Alto verificado aprox. 0.099908568m frente a altura oficial0.1m, tolerancia geométrica .001m intacta. No es certificación física, de anclaje, de expresiones ni aprobación visual.
- Luz artística: tres AREA explícitas con energía/color/transformación/tamaño/forma + World RGBA/exposición/gamma, todas de salida real Argon validada. Sustituye el perfil técnico anterior; no se afirma aprobación visual de esc1.
- Escenario vivo: respuesta PARTIAL con 23 errores semánticos/contractuales detectados; **rechazada, no aplicada**. JSON bien formado no basta.
- **Oro 23/23 idéntico**, sin alterar tolerancias ni núcleo histórico. Dieciséis pruebas adicionales pasan (7 puente/parse_ako y 9 datos/guardias/regresión). La regresión oro NO es una aprobación visual/píxel de esc1.
- No reanudé, creé, eliminé ni terminé pods. Coste GPU US$0; condición de CPU previa no cumplida.

## 1. Puente y sudoers: cambios exactos
Respaldos antes de cambios:
- `/opt/myia-motor-v9/avance06_20261107/respaldos/entrada_ssh.sh`
- `/opt/myia-motor-v9/avance06_20261107/respaldos/myia-taller-n8n` (archivo anterior de `/etc/sudoers.d/myia-taller-n8n`)
- `/opt/myia-motor-v9/avance06_20261107/respaldos/sello_pago.py`

Puente actual: `/opt/myia-taller-n8n/cajas/entrada_ssh.sh`.
Se añadió únicamente `generador_json estado`, `generador_json ejecutar ID` y la forma `generador_json adn b64.PEDIDO --ok USD --aprobado QUIEN`, con regex estricta y sin shell arbitrario. Los comandos anteriores permanecen.
Único permiso nuevo sudo: wrapper fijo root-owned `/opt/myia-motor-v9/avance06_20261107/entrega/codigo/puente_json.sh *`. No se permitió un Python arbitrario ni archivos/configuraciones elegibles por el usuario restringido. El wrapper valida comandos, IDs, argumentos, registro root-owned y rutas de imágenes autorizadas; un trabajo no registrado se rechaza. Traversal e inyección `;id` se probaron y rechazaron.
`visudo -cf` del candidato y `visudo -c` global: **PASS**, antes y después de instalar. Evidencias `puente_pruebas.json`, `visudo_c.log`; copias de antes/después incluidas en `fuentes/`.

## 2. Pago/parse_ako y publicación n8n
Workflow único `debwaH9svFMoTnOf`, 577 nodos. Respaldos completos root-only:
- `/opt/myia-motor-v9/avance06_20261107/respaldos/workflow_antes.json`
- `/opt/myia-motor-v9/avance06_20261107/respaldos/workflow_publicado.json`

Se modificaron seis nodos (preparadores y lectores ADN de PJ/OBJ/ESTILO), conservando conexiones y comportamiento antiguo por defecto. Nuevo modo explícito: `formato_adn="ako_json/v1"` en la entrada del sello. El preparador agrega `formato` al pedido, `sello_pago.py` deriva exclusivamente esa modalidad al generador nuevo; peticiones antiguas siguen exactamente la vía previa.
El JSON nuevo exige schema/id/clase y cinco bloques completos. Se valida identidad y bloques, se convierte SIN alterar contenido al texto legado y se ejecuta el `parse_ako` REAL existente. No se sustituyó ni debilitó ese parser. Pruebas con el ADN existente: texto y JSON producen el mismo documento y PASS_SELLABLE; identidad errónea y bloque ausente se rechazan.
Versión guardada/publicada: `06d22a09-e7fa-40ff-9335-d81b6222a995`; `activeVersionId` coincide con `versionId`, incluido el GET final. El PUT a un workflow activo republicó automáticamente: no se disparó una ejecución adicional de producción.
**Límite explícito:** esta modalidad hace compatible el documento ADN estructurado; no convierte un sello textual en certificación física o visual. Las llamadas pagadas de esta fase se hicieron por los trabajos acotados del nuevo generador. La nueva ruta de pago ADN en vivo conserva `pago_adn_json.off` para no autorizar otros gastos automáticos. La publicación no significa pago abierto.

## 3. Argon, validación y aplicación
Modelo real: `gemini-3-flash-preview`, Vertex/global/proyecto configurado. No se afirma Gemini4. Credencial root-only existente; nunca se incluyó su JSON ni contenido de clave en esta entrega.
- Ledger ANTES de cada llamada. Tope faseUS$10, total~US$50 y parada preventivaUS$45. Concurrencia protegida mediante flock.
- El esquema plano inicial de 19 huesos fue rechazado HTTP400 sin cargo; el esquema compacto de array tipado sí respondió. Las respuestas aceptadas usan `responseMimeType=application/json` y `responseSchema`, más revisión semántica independiente.
- Rig: 19 roles aviares completos, topología/IDs/límites/vectores/radios verificados. No se asignaron margen físico vigente, intervalos de apoyo ni anclaje métrico sin su fuente.
- Apariencia: primer intento4piezas insuficiente; nueva lista40features, corrección posterior de altura/paleta y parche Argon de sólo dos centros de copete. **No se arreglaron números a mano ni se relajó .001m.** Composición y cambios trazados en `bird_apariencia_procedencia.json`; alias `role=feature` es copia del mismo string del modelo, no contenido nuevo.
- Colores respetan la biblia/never_changes prioritaria de01 (cuerpo#FFD84D, pecho#FFF1A8, pico/patas#F2792A) cuando difiere del ADN descriptivo. No se alteró el texto original para fingir concordancia.
- Iluminación: refinada a tres emisores AREA con tamaño/forma explícitos. El adaptador de luz del motor nuevo ignoraba esos dos campos: se corrigió sólo la copia AV06, con respaldo `/opt/myia-motor-v9/avance06_20261107/respaldos/luces_blender_antes.py`. Los perfiles históricos sin esos campos conservan comportamiento, y oro volvió23/23.
- World recibió ID y alpha de otra respuesta Argon; conversión RGB→RGBA y radianes→grados documentadas. Ningún valor de diseño se inventó tras recibirlo.
- Blender CPU construyó realmente19huesos/40mallas y comprobó energía/tamaño/forma de las tres luces, World y controles de color. Artefacto `modelos/piquito_diseno_cpu.blend` es **sólo diseño estático de Piquito**, NO escena1, NO video, NO física aprobada.
- Respuesta de escenario vivo rechazada por tiempos/formato, falta de source en aserciones, bindings incorrectos, colorear toda ventana en vez de arcoíris y usar el color del libro como falsa prueba de letras temblando. No se aplicó.
- Auditoría posterior con enum estricto SOURCE/GENERATED/FALTA reconoce los datos ausentes; no se usó para declarar escenas completas.

## 4. Esc1, fuente2B y bloqueos
Candidata aislada: `/opt/myia-motor-v9/avance06_20261107/esc1_candidata/entrada_escena.json`.
Respaldos de paquete: `esc1_antes/`, `esc1_antes_aplicar06/`, `esc1_antes_alias_role/` dentro de AV06. Los originales protegidos permanecen intactos.
Aplicación: nuevo rig parcial, geometría estática validada y luz artística. Se conserva explícitamente que Piquito no tiene física/anclaje íntegros; no se asignaron aprobaciones falsas. La primera prueba detectó una discrepancia del nombre de campo feature/role; se corrigió como alias de transporte y se repitió la previa real, que termina con15bloqueos.

Se buscaron respuestas2B existentes y su procedencia. `respuesta_2b.json` de Guardianes sigue truncado (37,945 caracteres; cadena sin terminar cerca del final). El archivo histórico `respuesta_2b_ingresada.json` es JSON recuperado, pero contiene `_recovery.truncated=true` y notas explícitas de recuperación, no fuente íntegra ni aprobación. Hay52asignaciones recuperadas/reutilizadas; eso NO acredita contactos/anclas/completitud. **No se inventó ni modificó un solo valor de2B**, y los cuatro archivos de movimiento/catálogo/asignación mantienen bytes idénticos al inicio.

Bloqueos restantes completos: `15_BLOQUEOS_ESC1.csv` y `evidencias/preview_cpu_final_resultado.json`. Incluyen:
- 2B íntegro, contactos/anclas, estado/aprobación de biblioteca y programa completo.
- Reglas físicas vigentes ausentes, sin reemplazarlas por nuevas tolerancias generadas.
- Piquito: falta margen físico vigente y aún son necesarios apoyos/anclaje métrico comprobables; el diseño19/40no suple esas fuentes.
- Identidades ADN exactas del libro, ventana y visor; tipo POINT/OBJECT de Centro.
- Escenario vivo ejecutable con subpiezas/propiedades/curvas y estados correctos.
- Ejes/unidades de escena certificados. El marco local del diseño de Piquito no certifica todo el set.

Por esos bloqueos se detuvo antes de construir/renderizar esc1. No se eliminó un aviso para tapar una falta de fuente. Los dos avisos técnicos de luz se archivaron en historial sólo después de sustituir ese perfil por luz artística explícita y probar su construcción.

## Costes
- **AVANCE_06: US$0.2722640 brutos**, calculados de tokens reales recibidos a tarifas vigentes aplicadas, dentro deUS$10.
- **Acumulado conocido AV04+AV05+AV06: US$0.4765285 brutos**, dentro de~US$50.
- **Neto esperado US$0 por créditos**, sin verificación de factura/cobertura individual de cargos.
- Once intentos de API: diez con consumo y uno HTTP400 sin cargo de tokens. Prefallos locales antes de llamar no generaron gasto. Reservas pendientesUS$0.
- CPU/pruebas: sin compra nueva. GPUUS$0. Ver ledger completo y COSTES.csv; bruto calculado no equivale a una factura verificada.

## Guardias y recuperación
`generador.off`, `pago_adn_json.off`, dry_run/.off de la copia del motor se conservan al cierre. No quedan llamadas pagadas abiertas. Para continuar dentro de la autorización vigente, mantener ledger/tope de fase y reabrir sólo la guardia que corresponda a una tarea autorizada; no abrir el pago automático general por publicar un workflow.
No se tocaron /opt/video-studio, VPS prohibida, pod prohibido, T317 original,24_TRASPASO ni v9_universal_calidad_20261106. No se borraron archivos. Las únicas modificaciones externas al árbol nuevo son el puente, sudoers y dispatch de sello_pago expresamente aprobados, más el workflow nombrado.
