# Cierre t317 — Argon automático y exposición CPU

Fecha: 2026-11-07T11:29:27.770403-05:00 (Bogotá).

## Estado real
**BLOQUEADO: A funcionales=0; B=24 filas /17 causas.** Alcance BASE_CPU aproximado autorizado: no significa caras/ropa de fidelidad final ni escena aprobada. Persisten 12 AVISOS de cotas de biblioteca. Hay 0/1320 cuadros finales aprobados, 0/12 tomas aprobadas y 0/6 entidades certificadas. La hoja contiene 12 renders reales de diagnóstico con 5/6 sujetos colocados, posturas base y cámaras con bloqueos. No hay video parcial.

## Argon universal, sin enviar
Conectado al camino real de la etapa3 del orquestador. Detecta 29 entradas: **25 preparables** (24 objetos, incluidos cama, cofre y 22 decoraciones, más 1 revisión anatómica del ave), y **4 que necesitan asociación/tipo de referencia de origen**. No puede adivinar esos cuatro datos. Los objetos ya resueltos no se solicitan otra vez.

| Modalidad | Llamadas iniciales | Elementos por grupo | Estimación de techo de salida | Reserva prudente |
|---|---:|---|---:|---:|
| Sin agrupar | 25 | uno | US$16.435126 | US$16.550122 |
| Agrupado | 2 | 24 geometrías +1 anatomía | US$1.338828 | US$1.396066 |

Tarifa existente de noviembre: US$2 entrada /US$10 salida por millón de tokens, pensamientos incluidos. **No es factura ni predicción del consumo final**: usa aproximación offline bytes/3 y el máximo de 65536 tokens de salida por llamada. No se consultó count_tokens ni servicio alguno. Agrupar cabe en US$3; sin agrupar, ese techo no cabe. Reparaciones añaden llamadas y están sujetas al mismo presupuesto.

Único ajuste financiero: `config/politica_ejecucion.json → presupuesto_total_usd`, actualmente3. Sin límite de cantidad ni de dólares por llamada. `max_workers=8` es concurrencia de recursos, no tope de llamadas: todos los grupos se encolan. Reserva atómica antes de cada envío; consumo desconocido conserva reserva; no se inventa costo cero tras fallo real. Caché y escrituras de biblioteca protegidas; hash/origen/fecha y medidas verificadas; cajas rechazadas. Recetas de mock nunca se cargan en la escena real. La anatomía generada es una propuesta, no certifica anclas/datos ausentes.

Pruebas: mock aislado de los 25 pedidos, 2 llamadas simultáneas +1 reparación sólo del objeto inválido; 25 resultados guardados sólo en biblioteca temporal (incluye propuesta anatómica no certificada), después eliminada como temporal propio. Otra prueba con 40 nombres nuevos acredita 3 workers concurrentes y reutilización con 0 llamadas. Fallos de transporte/JSON se reintentan; repetición sin progreso produce FALTA; presupuesto agotado también. `argon_automatico.off` y `argon_recetas.off` detienen generación; `argon_envio.off` impide red. Sigue `dry_run:true`: **0 llamadas reales, US$0**.

## Luz y medida de saturación
AgX Base Contrast (contraste técnico neutro/medio), World ×0,5, emisores técnicos ×0,5, sombras activas, emisión limitada a1 por configuración. Es un preset técnico declarado, no una iluminación artística inventada. Exposición automática global basada en las 12 tomas, no ajuste distinto por canal o toma. El histograma midió y aceptó **0EV**, no fue necesario bajarlo más al quitar emisiones excesivas y usar el nuevo look. Si no pasa, baja por pasos de0,5EV hasta −8EV o bloquea.

Definición reproducible: píxel saturado si **algún canal RGB del PNG sRGB es ≥250/255**; no incluye rótulos de la hoja. Umbral técnico configurable X=0,5% por toma. Probes CPU de80×45 propios; finales320×180/16muestras. Gate definitivo en las imágenes finales y en todos los cuadros del render productivo; ningún clip se codifica antes de superar todas las tomas.

| Medida | t316 | t317 |
|---|---:|---:|
| Píxeles saturados del conjunto | 20.661024% | 0.000000% |
| Peor toma | 75.177083% | 0.000000% |

Gate: PASA. Se corrigió el deslumbramiento medido, **no la fidelidad geométrica**: siguen cuerpos base rígidos, caras de biblioteca, decoraciones sin receta, ave ausente y cámaras no aprobadas. Comparar con Star ESC6 no acredita equivalencia; es otra escena.

## Mejoras activas
| Mejora | Activa | Prueba |
|---|---|---|
| Descubrimiento y agrupación universal | Sí, etapa3 | `guardianes_t317_final/argon_descubrimiento.json`, plan y ejecución secos |
| Paralelo sin límite total de llamadas | Sí; envío real apagado por esta orden | `argon_mock_paralelo_t317.json`; tests02/13 |
| Reparación por elemento y transporte | Sí | tests03/04/11/14 |
| Caché validada y puente de decoraciones al constructor | Sí | tests02/09/16; nunca mocks en escena real |
| Único presupuesto y ledger previo | Sí | tests06/07 y reservas de ejecución seca |
| Apagadores | Sí | tests05/15, transporte t316 |
| Exposición global y gate antes de clips | Sí, render real y diagnóstico | PNG+histogramas, test12 |
| Catálogo Star, puntos, bisagras, rotaciones y cámara | Sí; sin cambios de identidad | Star22, catálogo82, cámara45 y suite completa |

## B que siguen pendientes
No se añadieron B por la luz técnica. Las 24 filas se consolidan en17 causas; ver `FALTANTES_GRUPO_B.md` y `resultado.json`. La reconstrucción de 2B/contactos, reglas/colliders, datos espaciales/ejes, estados narrativos y de luz por toma, parámetros PAN/CRANE, asociaciones ADN, recetas y anatomía/ancla del ave siguen sin acreditarse. Luz técnica corregida no sustituye estados artísticos de4a2/4a4. Omni hace voz/labios después; no son bloqueos del motor.

## Evidencias y seguridad
- Hoja: `evidencia/contacto_guardianes_t317/hoja_contacto_REAL_DIAGNOSTICO_BLOQUEADO.png`.
- Antes/después: `evidencia/contacto_guardianes_t317/comparacion_t316_vs_t317.png`.
- Star: `evidencia/contacto_guardianes_t317/comparacion_Star_ESC6_vs_diagnostico.png`.
- Histogramas: `evidencia/contacto_guardianes_t317/histogramas_antes_despues.json`.
- Argon: `evidencia/ARGON_ESTIMACION_T317.json`, `evidencia/argon_mock_paralelo_t317.json`.
- Resultado: `resultado.json` y `evidencia/guardianes_t317_final/resultado.json`.
- Suite: `evidencia/suite_t317_definitiva.log` (197/197); `t317_paralelo_regresiones.log` (16/16).
- Oro: `evidencia/oro_t317_definitivo/metricas_oro.json` (23 exactas; confirmar en acta de aceptación).
- Barrido nombres/IDs/rutas: `evidencia/barrido_t317.json`, cero coincidencias.
- 53 originales intactos: `evidencia/originales_t317.json`.

US$0, CPU llvmpipe, sin GPU física. No se guardó otro blend de diagnóstico, ni tar/copia pesada. Respaldo de código pequeño y `.off` de desarrollo: `respaldos/t317_codigo_20261107_112212/`, `config/t317_desarrollo.off`; switches específicos opcionales y envío real apagado. Sólo se eliminaron temporales propios (862190 bytes de bytecode y probes/fixtures temporales). Cambios observados en el espacio libre del box compartido no se atribuyen a esta limpieza.

**213: no subido en esta tanda; no se intentó conexión nueva.** El último cotejo registrado seguía en timeout. No se tocó producción/n8n, carpetas remotas ni destinos prohibidos. No se promete listo para pruebas remotas ni COMPLETO.

### Precisión del ledger
La verificación final detectó un residuo de coma flotante de −1,11×10⁻¹⁶ USD en reservas, sin ningún cargo ni reserva abierta. Se corrigió con aritmética Decimal y recálculo desde entradas abiertas/liquidadas, no ajustando dinero a mano. Prueba17 añadida; suite definitiva197/197.
