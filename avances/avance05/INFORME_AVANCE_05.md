# AVANCE_05 — reparación estructurada, aplicación parcial y prueba real
Cierre: 2026-11-07 21:13:52 Bogotá (UTC-5).

## Resultado ejecutivo
- NO se completó esc1 ni se obtuvo aprobación de producción. La previa CPU real se ejecutó y se detuvo correctamente en la barrera de entrada: **18 bloqueos**, sin video.
- Se aplicaron únicamente tres amplitudes numéricas de cámara y las recetas validadas de cama/cofre. De 23 faltantes heredados de AVANCE_04 se pasó a 20 tras cámara y a 18 tras objetos. El punto original antes de AVANCE_04 era 24.
- **Oro: 23/23 métricas idénticas**, sin relajar tolerancias. Es regresión numérica del paquete oro, NO validación visual/píxel ni de esc1.
- Ocho pruebas adicionales pasan: números originales de Argon, tiempos de cámara, identidades exactas, hashes, material por pieza, tolerancia .001 m, prohibición de pago automático y bloqueo CPU conservado.
- **n8n no fue modificado**; respaldo leído mediante API oficial y contenido idéntico al cierre de AVANCE_04. La integración productiva queda pendiente por incompatibilidad real de parser y puente SSH, explicada abajo.
- No reanudé ningún pod. No se gastó en GPU. No se modificaron los árboles protegidos ni /opt/video-studio.

## Costes reales por uso devuelto por Vertex
- Fase AVANCE_05: **US$0.1282750 brutos**, frente al tope de US$3.
- Acumulado conocido AVANCE_04 + AVANCE_05: **US$0.2042645 brutos**, dentro de ~US$50.
- Neto esperado: **US$0 por créditos**, sin verificación independiente de factura/cobertura de cada cargo.
- Reservas pendientes: US$0. Ledger ANTES de cada llamada, bloqueo de concurrencia y liquidación posterior. 17 intentos: 10 respuestas con consumo y 7 HTTP400 sin cargo de tokens conforme a política de errores no-200.
- Tarifas aplicadas: entrada texto US$0.50/M, salida (incluidos thoughts si los hubiera) US$3/M; caché US$0.05/M. Ver `COSTES.csv`, `evidencias/ledger.json` y cada `consumo.json`. No se afirma que estos cálculos sustituyan la factura.
- CPU y regresión: sin nueva compra ni llamada pagada; GPU US$0.

## Qué se corrigió del rechazo de 31 errores
El CSV `31_ERRORES_Y_ESTADO.csv` audita uno por uno. **31 errores de respuesta NO significan 31 datos de escena resueltos.**
1. Omisiones: inventario plano con las 24 claves exactas obligatorias, cada una con estado, fuente y razón. Se rechazaron 12 afirmaciones falsas SOURCE de un primer intento; el inventario final reconoce FALTA donde no hay prueba. No se convirtió FALTA en un dato inventado.
2. JSON de Vertex: `responseMimeType=application/json` + `responseSchema` en el SDK real, con gemini-3-flash-preview/global. Los esquemas anidados recibieron HTTP400; la variante plana de escalares sí funciona. La transformación posterior sólo agrupa componentes, no corrige números.
3. Cámara: tres valores reales generados (PAN v3, CRANE v5, PAN v7), verificados finitos/positivos, con procedencia GENERATED. Se conservaron las doce tomas fuente, direcciones y tiempos; no se regeneraron once tomas que ya existían.
4. Objetos: sucesivas respuestas rechazadas por ejes/dimensiones/centrado/IDs. Últimos cofre y cama pasan JSON y semántica: cinco y ocho piezas respectivamente, IDs con espacio de nombres, dimensiones oficiales, centro y límites exactos, sin BOX y con materiales completos. Se aplicaron sólo iteraciones 16/17; las rechazadas no se usaron.
5. Rig de Piquito, escenario vivo y equivalencias: se retiró la confianza en la respuesta defectuosa. NO se aplicaron huesos incompletos, `material.saturation`, estados narrativos sin curvas ni equivalencias difusas. Estos datos siguen pendientes; no existe aún un lote integral nuevo que resuelva toda la escena.

## Aplicación y prueba de esc1
- Paquete aislado VPS: `/opt/myia-motor-v9/avance05_20261107/esc1_candidata/entrada_escena.json`.
- Copias anteriores: `esc1_antes/` y `esc1_antes_objetos/`, en el mismo árbol nuevo.
- Recibos: `evidencias/aplicacion_camara.json`, `aplicacion_objetos.json`. Coordenadas de colocación tomadas del inventario medido; sólo se convierte radianes a grados, sin inventar ubicación.
- Previa real con `solo_validar=False`, `prueba_cpu=True`, Blender existente. Resultado completo: `evidencias/preview_cpu_objetos_resultado.json` y carpeta `preview_cpu_esc1_objetos/`.
- **Estado: BLOQUEADO; video/master: ninguno (null)**. No llegó al render de cuadros por los 18 faltantes. No es una previa visual aprobada.
- `argon_automatico=False`, transporte dry_run y `.off` conservados en esta copia aislada. No se eliminó ningún aviso provisional para forzar el paso.

## Bloqueos restantes (18 entradas; algunos describen el mismo origen)
- 2B truncado, programa íntegro y contactos/anclas ausentes; aprobaciones técnicas de biblioteca no acreditadas.
- Parámetros vigentes de colisión, velocidades, aceleraciones y tolerancias de física ausentes en su fuente.
- Piquito: landmarks, proporciones, límites articulares y anclaje certificados; no escalar otro rig ni afirmar que tres huesos cubren un ave.
- Vínculos ADN exactos y únicos para libro, ventana y visor. Centro de habitación necesita declaración POINT u OBJECT.
- Escenario vivo ejecutable: subpiezas, materiales, curvas, propiedades soportadas y estados esperados. Los tiempos existentes se reutilizan, no se piden de nuevo.
- Ejes/unidades certificados y luz artística base/eventos/exposición; los valores técnicos provisionales siguen marcados como tales.

## n8n: por qué no se promovió una respuesta parcial
Workflow `debwaH9svFMoTnOf`, activo, 577 nodos. El respaldo actual y AVANCE_04 tienen iguales nodos, conexiones y ajustes; evidencia en `N8N_ESTADO.json`.
- SELLO PJ y SELLO OBJ envían pedidos base64 con `extra`; el backend real `sello_pago.py` usa `json_out=False`, exige cinco bloques textuales y los parsea con `parse_ako`.
- Pedir JSON directamente en `extra` rompería el sello. Añadir instrucciones sin integrar ledger/schema en el productor activo permitiría futuras llamadas sin la protección presupuestaria nueva.
- El SSH restringido permite los comandos existentes `sello_pago`, `paso00_cadena`, `motor_v9`; no el generador nuevo. No amplié permisos, no saqué la clave al workflow y no reemplacé scripts fuera del árbol nuevo.
- No promoví una ruta de un solo canal ni un parche que pretendiera aprobar datos FALTA. La adaptación correcta necesita un puente compatible por productor, contract/schema + ledger antes de red, validación semántica, traducción al formato legado o nuevo lector, y pruebas antes de conectar al flujo activo. Ver `N8N_INTEGRACION_PENDIENTE.md`.

## Recuperación y límites
Todos los cambios de datos ocurrieron en el árbol nuevo AVANCE_05. La credencial permanece sólo en el archivo root-only de AVANCE_04, no se copia en esta entrega. No se borró nada; se preservaron respaldos. No se tocaron T317, 24_TRASPASO, v9_universal_calidad_20261106, VPS prohibida ni pod prohibido.
La copia del paquete es evidencia reproducible sobre el runtime existente del VPS; no sustituye sus dependencias ni promete un render autónomo en Windows.
