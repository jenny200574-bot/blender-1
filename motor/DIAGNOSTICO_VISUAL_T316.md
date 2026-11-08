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
