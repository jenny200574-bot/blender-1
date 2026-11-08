## Actualización t317 (7-nov, Bogotá)

Ver [INFORME_T317_ARGON_Y_EXPOSICION.md](INFORME_T317_ARGON_Y_EXPOSICION.md). A=0 funcionales /B=24 filas,17 causas; BLOQUEADO. Luz saturada20,6610%→0%; Argon agrupado2 llamadas, cotización techoUS$1,338828/reservaUS$1,396066; sin llamadas reales, US$0. No se subió al213.

# Actualización t316

# Diagnóstico visual y transporte Argon — t316

7-nov-2026, Bogotá (UTC−5). **A funcional=0 (alcance BASE_CPU); B=24 filas/17 causas. Calidad visual NO aprobada. US$0.**

| Causa | Tipo | Evidencia | Arreglo/estado |
|---|---|---|---|
| Personajes con aspecto de cápsulas | Límite biblioteca BASE_CPU, no dato B ni malla desactivada | Mallas ADN/base sí cargadas y ligadas a huesos; volúmenes de loft/cobertura rígida estilizados, no cuerpos/ropa de alta fidelidad. | No se afirma corregida la fidelidad. Se conservan12 AVISOS de cotas de biblioteca; imagen→3D fuera de CPU. |
| Luz plana y lavada t314 | Configuración técnica + luz artística B | Cycles4 muestras; World gris .22 con Strength1; AgX exposición0; rellenos técnicos. Sombras ya estaban activadas, no era un interruptor apagado. | EEVEE CPU llvmpipe, World Star [.06,.07,.10] Strength.42, AgX contraste medio-alto, exposición0; dos rellenos técnicos650/250W derivados del cuarto medido. No se presentan como luz del SB. |
| Primera prueba EEVEE demasiado oscura | Configuración de render | EEVEE no reproduce el rebote difuso World de Cycles sin sondas/GI; luces externas quedan tapadas por el cuarto. Ensayo oscuro archivado. | Relleno técnico interior explícito por datos, sombras activas; después se bajó energía/exposición del ensayo sobreiluminado. Sin inventar iluminación artística. |
| Objetos caja / ocultos | Código no conectado para fondo + recetas/bindings B | Se importaba set.blend con moldes bbox; Star sólo se usaba en props ya resueltos. El render diagnóstico escondía los6 objetos principales no resueltos. | detalle_entorno.aplicar conectado al constructor final y al diagnóstico.5 instancias reales: puerta, almohada, armario y2 estanterías.22 decoraciones sin receta compatible se declaran en una nueva causa B. No cortina→ventana ni edredón→cama ni cojín estrella→almohada lisa. |
| Cuarto vacío / sin detalle comparable a Star | Recetas del entorno B, no falta de muebles inventados | El productor sí entregó24 elementos de ambiente y medidas/posiciones; son moldes, no recetas detalladas. No faltan esas posiciones, faltan sus equivalentes/despieces compatibles. | Usar5 fórmulas válidas con dimensiones/transformaciones fuente. No llenar el cuarto con muebles ajenos a la entrada. Star ESC6 sigue teniendo más detalle final. |
| Materiales planos / poco contraste | Biblioteca y configuración; algunos materiales B | Los materiales PBR ya existían (nodos); no es correcto afirmar que no había materiales. Predominaban colores uniformes y geometría sin detalle. | Materiales_por_formula v2 de Star con hash, color fuente por instancia, bisel técnico por preset y sombras EEVEE. Superficies/capas faltantes del ADN OBJ siguen B. |

## Argon real, preparado en seco
`motor/argon_transporte.py` reusa el cliente SB existente (`_cliente`) y su patrón de streaming, espera1800s y salida larga65536 incluyendo thoughts. Configuración fuera del código; credencial sólo por entorno/archivo existente al autenticar. La prueba seca NO abre el archivo de claves, no construye el cliente ni envía/count_tokens. Cliente/hash y tarifa existentes verificados.

Ledger antes de cada llamada, tope TOTAL3, caché hasheada, receta validada antes de alta; no límite financiero por llamada. `config/argon_envio.off` y `dry_run:true` impiden todo envío en esta tanda. Streaming probado con SDK y respuesta simulada; la respuesta real del proveedor NO se ha probado. No se copiaron los efectos laterales del cliente viejo ni su ledger de50USD.

El camino actual de Guardianes prepara **3 solicitudes**: cama, cofre y revisión anatómica/ancla del ave (sólo propuesta/FALTA, no certificación inventada). Estimación **US$1.972168**, reserva conservadora **US$1.985872**: pasa el tope3. Tarifa existente: entradaUS$2 /salida+thoughtsUS$10 por millón. Cálculo offline bytes/3; no conteo HTTP. Se presupuestan hasta65536 tokens de salida por solicitud, no es gasto real ni predicción exacta de tokens. Las22 decoraciones/bindings B todavía no determinan nuevas llamadas: esta cifra NO cotiza terminar toda la escena.

Prueba: `evidencia/ARGON_ESTIMACION_T316.json`, `evidencia/t316_unitarias_cierre.log`, `evidencia/ledger.json`. Todas las reservas secas se liquidaron a0; llamadas reales0, GPU0.

## Hoja nueva
`evidencia/contacto_guardianes_t316/hoja_contacto_REAL_DIAGNOSTICO_BLOQUEADO.png`

12 imágenes Blender EEVEE320×180,24 muestras, **llvmpipe CPU software** (Mesa, sin GPU física), con sombras; `.blend`, PNG, backend y recibos en la misma carpeta. Cinco sujetos colocados, ave omitida por datos estructurales. Cámaras t314 conservadas; **NO revalidadas con los muebles nuevos**. No es escena completa, no es video parcial.

Comparación: `evidencia/contacto_guardianes_t316/comparacion_Star_ESC6_vs_diagnostico.png`. Star es ESC6. No se pretende equivalencia visual entre escenas distintas ni solucionar la biblioteca de personajes cambiando el render.

## B sube23→24, no se oculta el fondo
Se agrega **una causa nueva**,22 elementos de ambiente cuyo productor sólo entregó molde/ubicación/texto: `environment/catalog_unresolved`. Lista completa en `resultado.json` (dato_esperado) y `evidencia/puente_entorno_t316.json`. Productor4a2/escenario vivo +catálogo/generador de formas. No se piden otra vez medidas/posiciones. Los otros23 diagnósticos/16 causas siguen iguales (2B, reglas/contactos, ave, bindings, cama/cofre, vivo, calidad técnica, ejes, luz artística, PAN/CRANE). Las5 instancias Star son bases de catálogo, no acabados ADN exactos.

## Pruebas y límites
170 regresiones previas +10 nuevas de transporte; Star22, catálogo82, cámara45; oro23/23 exactas en `evidencia/oro_t316_sellado/metricas_oro.json`; barrido0 en `evidencia/barrido_t316.json`. La reproducción completa en el213 no se hizo. No producción/n8n, no destinos prohibidos.

La copia tar t314 anterior NO incorpora esta tanda. Los archivos actuales del motor y su nuevo manifiesto son la fuente vigente.


---
# Informe histórico t314 (reemplazado en sus cuentas/configuración)

# Resultado fases 0 a 6 — motor único dev6 CPU / t314

Actualizado 2026-11-07T10:57:50.804468-05:00, Bogotá (UTC−5).

## Estado real
**Guardianes BLOQUEADO. A=0; B=23 filas /16 causas. US$0. No subido ni probado en el 213.**

| Grupo | Pendiente |
|---|---:|
| A caras/ropa (12 acabados +6 traductores antes pausados) | 0 bajo BASE_CPU autorizado t314 |
| A restantes | 0 |
| B datos de escena | 23 filas /16 causas |
| Cotas ADN ausentes | 12 AVISOS de fidelidad, no bloqueo |

Hay 14 avisos totales: 12 de cotas, uno informativo de consolidación ADN y uno de licencia personal. No se ocultan los dos adicionales.

Apariencia **base estilizada CPU ajustada al texto ADN**: mallas/materiales, pelo/gafas/prendas, mangas/enterizos, piezas ligadas a huesos y piel cubierta oculta. Cotas «de biblioteca» con procedencia/hash y ajuste al rig. Construcción 3D medida tiene prioridad si existe. No reconstruye exactamente las hojas pintadas ni promete deformación/skinning fino u ornamentos idénticos. Imagen→3D GPU es hueco futuro, no implementado/ejecutado.

Se preservan **1320 cuadros, 12 tomas, 6 entidades, 25 acciones y 35 segmentos** solicitados. **Finales aprobados: 0 cuadros, 0 tomas y 0 entidades. No master/video parcial de Guardianes.** Cuatro fixtures llegan a COMPLETO por las 16 etapas; no se confunden con la escena real.

## Qué quedó conectado
Una entrada `entrada_escena.json` +paquete con hashes; `orquestador.py` y el constructor final común. Las 16 etapas son fuentes/gasto, Argon/caché, preparar/puentes, contrato, ADN/apariencia, escenario vivo, objetos/puntos, esqueletos, movimientos, retarget/pulida/contactos, SB/4g, luz global, revisión, empaquetado, render y montaje. Sin rama por canal ni camino que fuerce una escena incompleta.

- ADN textual → BASE_CPU y geometría/materiales reales. Perfiles genéricos y puntos en huesos. Los tres catálogos nominados de Star quedan archivados; perfil activo genérico, datos originales como ejemplos. Bone_map explícito; datos articulares preservados, no remapeo AAOS automático prometido.
- ADN OBJ → receta exacta/similar con umbral/composición/proveedor/FALTA. Catálogo Star, bisagras/pivotes, puntos world/local, pieza móvil, rotación XYZ y c+IK. No bbox como acabado. Cables por polilínea nombrada o FALTA.
- Binding 4a/4a4, presencia y escenario vivo por propiedades/tiempos/estados. Arquitectura con varios huecos y exterior por datos.
- Luz por emisor sin dependencias fijas; tres canales sólo con mapa explícito. World/exposición, reloj global y apagones CONSTANT. **Corregido orden**: entorno geométrico antes de crear luces; emisor/World después. Grafo completo validado antes de partirlo. Fixture final: 2 pistas antes, 1 después.
- Movimientos aprobados → catálogo con fuente/prompt, perfil/esqueleto, duración, métricas, hash y origen; reuso antes de generar/repulir. Prueba con BVH existente y fixture, no generación externa real. Licencias AVISO personal; calidad técnica obligatoria.
- **Argon receta interfaz activa por defecto**, .off opcional, caché, ledger antes del callback, tope total US$3 y alta sólo si valida geometría/medidas/no caja/hash/origen/fecha. Mock CPU probado a través del orquestador. **Transporte HTTP real no conectado ni ejecutado**: sin proveedor real devuelve FALTA; no se acredita una llamada en vivo.
- Ingesta por lote en cuarentena con hash; copiar no aprueba. Video→mocap extractor no hecho: ingestión/puente de su resultado preparada.

Cada mejora, activa sí/no, módulo real y prueba: [MEJORAS_ACTIVAS_T314.md](MEJORAS_ACTIVAS_T314.md).

## Fases
| Fase | Resultado |
|---|---|
| 0 cotejo | Copias locales/hashes; 53 originales sin cambios. 213 TIMEOUT, cotejo remoto pendiente. |
| 1 contrato/negativos | Pasados: truncado, hash, formato, ruta, campos, duplicados, .off y compuertas. |
| 2 núcleo/bibliotecas | Integrados puntos/IK/objetos, escalera, retarget/pulida y regresiones. |
| 3 oro | **23/23 exactas**, misma referencia/tolerancias. Igualdad histórica NO aprueba calidad física antigua. |
| 4 ADN/ave/vivo/luz | Capacidades CPU probadas; escena real bloqueada por fuentes B. |
| 5 cámara/montaje | 28 movimientos/45 comprobaciones y transiciones probados; PAN/CRANE reales incompletos bloquean. |
| 6 Guardianes íntegra | **NO pasa**, por 16 causas B. |

## Hoja REAL, sólo diagnóstica
- `evidencia/contacto_guardianes_t314_definitivo/hoja_contacto_REAL_DIAGNOSTICO_BLOQUEADO.png`
- `evidencia/contacto_guardianes_t314_definitivo/diagnostico.blend`, `v1.png`…`v12.png` y `recibo.json` con hashes.
- `evidencia/contacto_guardianes_t314_definitivo/comparacion_Star_ESC6_vs_diagnostico.png` y `comparacion.json`.

12 renders Blender Cycles CPU, 320×180, cuatro muestras, uno por toma. **5/6 sujetos colocados**; ave sin rig/ancla suficiente omitida y objetos no resueltos no se presentan como finales. Posturas base/luz técnica declaradas; no ejecuta el 2B truncado. Cámaras diagnósticas bloqueadas: **v4, v5, v8, v11**. Verificación del .blend:16 checks de metadata, parentado, movimiento real de malla al mover hueso y punto anatómico en hueso. No aprueba actuación/cámara/contactos.

Star entregó **ESC6**, no ESC8: oficina con mobiliario detallado y variantes de luz. El diagnóstico de otra escena es más simple y aún carece de objetos/ave; **no acredita igual detalle final**. Comparación cualitativa lado a lado, no métricas de píxeles entre escenas distintas.

## B por causa y productor
1. **programa_2B_integro_y_contactos** — 2B/Argon + 01/Star. JSON truncado: recuperar respuesta íntegra
2. **reglas_y_manifiesto_colision** — Biblioteca reglas vigentes + 4a2/manifiesto. No están en la fuente estos parámetros: allowed_collision_pairs, bone_length_error_m, colliders, penetration_tolerance_m, reject_surface_intersections, root_accel_max_m_s2, root_speed_max_m_s
3. **perfil_anatomico:ch-piquito-030a** — ADN Maestro 03/04 + 01/Star puntos. Faltan landmarks/proporciones estructurales y límites articulares certificados; altura y cabezas no determinan longitudes de alas/patas. Faltan también apoyos/ancla explícitos cuando va acoplado. No se escala un rig de otra identidad.
4. **objeto:obj-libro-cuentos__e1-8** — ADN OBJ/SELLO + 4a2. Falta asociación exacta y única entre objeto espacial y ficha ADN; no aproximar nombres
5. **objeto:Ventana con vista al arcoíris** — ADN OBJ/SELLO + 4a2. Falta asociación exacta y única entre objeto espacial y ficha ADN; no aproximar nombres
6. **objeto:obj-cama** — ADN OBJ/SELLO + catálogo de formas. Escalera agotada sin receta compatible ni despiece medido. ADN/medidas/referencia están conservados; faltan receta/despiece/puntos de la forma descrita. Proveedor Argon por defecto activo, sin gasto real en programación.
7. **tipo_referencia:Centro de la habitación** — 4a2/manifiesto espacial. Referencia sólo usada para mirar: falta declarar POINT u OBJECT. No pedir ADN de un lugar ni ocultar un mueble como si fuera un punto. Posición/bbox ya disponibles.
8. **objeto:obj-visor-spark** — ADN OBJ/SELLO + 4a2. Falta asociación exacta y única entre objeto espacial y ficha ADN; no aproximar nombres
9. **objeto:obj-cofre-dorado** — ADN OBJ/SELLO + catálogo de formas. Escalera agotada sin receta compatible ni despiece medido. ADN/medidas/referencia están conservados; faltan receta/despiece/puntos de la forma descrita. Proveedor Argon por defecto activo, sin gasto real en programación.
10. **escenario_vivo** — 4a4 + 01 + 4a2. Sólo llegaron estados narrativos inicio/fin; faltan subpiezas/materiales/valores/curvas para cambios de letras, color y FX. Los tiempos explícitos de 01 se reutilizan; no se piden otra vez.
11. **calidad_tecnica_biblioteca** — Biblioteca de movimientos + 2B/revisor. Faltan validación/aprobación técnica comprobables de movimientos: m_aterrizar_alerta, m_bostezo_caos, m_caminar_ciclo, m_disparo_caos, m_giro_decidido, m_giro_pasos, m_hablar_alarmado, m_hablar_entusiasta, m_hablar_misterioso, m_hablar_serena, m_hablar_visor, m_mirar_sorpresa, m_reposo_base, m_risa_caos, m_senalar_tu
12. **marco_espacial** — 01/4a2. Ejes y unidades certificados ausentes
13. **iluminacion_de_variante** — 4a2/4a4 + configuración técnica. Luces CPU técnicas explícitas en entrada; no SB ni iluminación artística aprobada
14. **camera/v3/0/PAN** — SB + 02N/4a2. Faltan grados o extremos inequívocos; dir_lr y speed no determinan amplitud
15. **camera/v5/0/CRANE** — SB + 02N/4a2. Faltan metros o extremos verticales; dir_ud y speed no determinan altura
16. **camera/v7/0/PAN** — SB + 02N/4a2. Faltan grados o extremos inequívocos; dir_lr y speed no determinan amplitud

Los 23 campos exactos están en [FALTANTES_GRUPO_B.md](FALTANTES_GRUPO_B.md) y `evidencia/guardianes_t314_sellado/causas_consolidadas.json`. No volver a pedir cotas/referencia del cofre (65×42×48 cm ya disponibles): faltan receta/despiece/pivotes. Recetas son salidas del productor de formas. El centro de habitación necesita POINT u OBJECT, no ADN de un lugar. Reutilizar tiempos explícitos de 01.

### Por qué cambió B
12→26: no eran 14 causas independientes; aparecieron 12 campos de cotas y dos diagnósticos físicos. Contactos/status/provisional comparten el 2B truncado; reglas/colliders agrupan siete parámetros. Más lectores expusieron después 35 filas/22 causas. T314 pasa las 12 filas/6 causas de cotas a AVISO: quedan23 filas/16 causas. Las18 A se cerraron programando BASE_CPU, no se trasladaron a B.

## Pruebas selladas
- **170 unitarias OK**: CPU40 +t30728 +ADN16 +puentes14 +no facial35 +t31426 +dev2 11. `evidencia/*t314_sellado.log`.
- Star22, catálogo82 (41 fórmulas finalizables ×2 anclas), cámara45 (28 comandos/variantes), todas pasadas.
- Oro: `evidencia/oro_t314_sellado/metricas_oro.json`,23/23 exactas.
- Cuatro entradas COMPLETO/16 etapas: `evidencia/fixture_base_cpu_t314_sellado/`, `fixture_argon_mock_t314_sellado/`, `fixture_movimiento_t314_sellado/`, `otro_universo_t314_sellado/`.
- Otro universo/nombres nuevos, mismo motor sin editar. Barrido nombres/canales/personajes/IDs/rutas en `motor/**/*.py,json`: **0 coincidencias**, `evidencia/barrido_valores_fijos_t314_sellado.json`.
- 53 originales sin cambio: `evidencia/fuentes_originales_t314_sellado.json`.
- BVH existente: `evidencia/bvh_existente_registro_reuso_t314.json`. Alta nueva y reuso: `evidencia/fixture_movimiento_t314_cierre_nuevo/catalogo_registro.json` y `fixture_movimiento_t314_cierre_reuso/catalogo_reuso.json`. Son pruebas, no aprobación automática de los15 clips reales pendientes.
- Lotes: `evidencia/ingesta_lotes_t314.json`, dos entradas en cuarentena; hash/ruta falsos rechazados.
- Binding .blend: `evidencia/verificacion_blender_t314_definitivo.json`.
- Agregado verificable: `evidencia/aceptacion_t314.json`.

### Errores heredados descartados del camino activo
| Error | Regresión | Evidencia bajo evidencia/ |
|---|---|---|
| rot_deg ignorado | rot_deg_tres_ejes_aplicados | star_t314_sellado/regresiones.json |
| ancla_z sobrescrita | ancla_base_elevada_no_sobrescrita | star_t314_sellado/regresiones.json |
| compuesto desconocido AttributeError | falta_clara_None / falta_clara_tipo_inexistente | star_t314_sellado/regresiones.json |
| hoja sin padre | puerta_real_hoja_panel_pomo_parentados | star_t314_sellado/regresiones.json |
| alias por nombre | hoja_parentada_a_pivote_sin_alias / control_c_ik_contacto_por_cuadro | star_t314_sellado/regresiones.json |
| luz con dependencias fijas | test_lamparas_sin_dependencias | t307_t314_sellado.log |
| coordenada fija de luz | emisor_parentado_marco_world_sin_coordenada_fija | star_t314_sellado/regresiones.json |
| polish_bvh smooth/footlock | test_pulida_firma_real / test_no_silencia_excepcion_pulida | cpu_t314_sellado.log |
| PM.activo() or True | test_pulida_off_no_se_ignora | cpu_t314_sellado.log |
| orden entorno/luces | test_26_orden_entorno_luces_sin_alias + worker12 (2 pistas antes /1 después) | t314_unitarias_sellado.log; fixture_base_cpu_t314_sellado/etapas_worker.json |

Además, falso positivo de ray parity con AABB separados corregido: test explícito, sin aflojar tolerancias ni alejar el objeto del fixture para pasar.

## Gasto, respaldo y 213
**Real US$0, reserva US$0, tope total futuro US$3**, sin límite por llamada. Ledger antes del mock/caché: `evidencia/ledger.json`. Ningún Argon real ni GPU.

Dos intentos nuevos al213, separados por espera: **TIMEOUT**, 7-nov10:36 y10:39 Bogotá (UTC−5). `evidencia/213_t314_estado.json`. **No subido**, no cotejo ni CPU remotos; no está acreditado listo para pruebas en el servidor. Sin tocar producción/n8n/carpetas anteriores ni destinos prohibidos.

Respaldo/archivo antes de cada reemplazo, incluidos resultado.json y motor_unico.off anteriores. Producción y desarrollo OFF; CPU sólo por bandera explícita. El .off Argon anterior está archivado: proveedor lógico activo por defecto, puede apagarse recreando su interruptor. Manifiesto/SHA256SUMS sellan los archivos. Sin claves en informes.

## Voz/labios y continuación
T295: voz/labios los hace **Omni después**, no bloquean por falta de audio. `evidencia/guardianes_t314_sellado/tiempos_dialogo.json`:11 intervenciones, cuatro cruzan corte, hablante/texto/segundos/cuadros/toma; planificación, no alineación de grabación.

[Guía de bibliotecas y puentes](motor/GUIA_BIBLIOTECAS_Y_PUENTES.md), enlazada desde README/LEEME: rutas, formatos, lote, recetas/poses/CMU/Mixamo/video/perfiles/materiales, hashes, nuevos puentes y crecimiento universal.

Siguiente paso: completar las salidas B, volver a correr la MISMA entrada/compuertas, acreditar1320 cuadros/12 tomas/6 entidades y luego instalar/probar la carpeta nueva en213. No anunciar COMPLETO/subido mientras falte esa aceptación o la conexión remota.
