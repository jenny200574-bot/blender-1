# Paso 2 SB — prompts V2 inactivos, aprobados t895u

Argon sigue siendo el director principal. Se escribieron la base común, dirección y reparación localizada, diez bloques de género y una propuesta de selección. Son archivos NUEVOS: no reemplazan los textos activos, no registran hashes nuevos en la guarda ni activan llamadas. No se tocó n8n ni capítulos.

## Archivos
- `prompts/base_argon_cine_v2.txt`: reglas comunes, ADN, contexto,13 bloques y verificación.
- `prompts/etapa3y4_dirigir_storyboard_v2.txt`: plantilla que incluye base, un género y datos.
- `prompts/reparar_storyboard_v2.txt`: solo fallidas autorizadas, vecinas como contexto y hashes de aprobadas intactos.
- `prompts/generos_v2/*_v2.txt`: drama, emoción/catarsis, intriga, suspenso, terror, comedia, acción, fantasía, ternura y misterio.
- `config/perfiles_argon_cine_v2.propuesta.json`: mapa inactivo, fuentes y aliases. No se modificó `_indice.json` ni ningún perfil activo. Aventura/romance/ciencia_ficcion no se reasignan a escondidas.
- `contrato/comprobar_prompts_v2_offline.py`, `PROMPTS_V2_TOKENS.json` y `PROMPTS_V2_PRUEBAS.json`.

## Qué se aplica
Fuente: matriz original `reporte_t883/tablas.txt`, tabla0 filas1..10, y reglas del informe1.3–1.8. Cada bloque conserva literalmente su fila de la matriz y explica su aplicación. Reglas1.0.0 y contrato2.1.0 del paso1 prevalecen frente a preferencias del género. No se añaden hechos, personajes ni valores de ADN.
Queda explícito: Argon elige planos/sujeto/lente/altura/movimiento/motivo/ritmo. El programa suministra datos, valida y resuelve geometría. ADN por referencia y hash, nunca prosa nueva de apariencia. Reloj24fps. LOCK por defecto; delta>=0.15 incluso con REVEAL; cuotas generales y único GPP; no-PD consecutivos; eje/30°/miradas; pre-roll y L/J.
Conflictos de la matriz tratados sin cambiar las reglas: fantasía/suspenso/terror no obtienen cuota extra de PG; GPP de manos no crea un tamaño nuevo, se trata como PD crítico cuando corresponda; obstrucciones de intriga no pueden tapar ojos obligatorios; whip-pan de comedia y grúa/orbita siguen sujetos al límite de video IA y al espacio real; emoción no corta el quiebre solo para variar ángulo.

## Tamaños medidos, no conteo por caracteres
Conteo REAL LOCAL con Google GenAI LocalTokenizer, vocabulario Gemma3, referencia `gemini-2.5-pro`; SDK 2.28.0. El ledger llama al modelo `gemini-4-argon HIGH`: no se inventa que este alias tenga un tokenizador certificado igual. Estos números son mediciones reproducibles de texto con el tokenizador local, NO factura ni conteo certificado de Argon. No hubo countTokens remoto ni llamadas a modelos.
Base común: **2462 tokens**. Reglas compactas:2826; esquema compacto:6099. La plantilla de dirección sin expandir mide466, pero sus placeholders se reemplazan: no hay que sumar ese número como si ya estuviera expandida. Se mide el texto completo ensamblado con JSON vacío de contexto.

| Género | Bloque medido | Dirección fija completa, contexto vacío | Con contexto estimado9k–19k |
|---|---:|---:|---:|
| drama | 710 | 12471 | 21471–31471 |
| emocion | 702 | 12463 | 21463–31463 |
| intriga | 734 | 12495 | 21495–31495 |
| suspenso | 708 | 12469 | 21469–31469 |
| terror | 764 | 12525 | 21525–31525 |
| comedia | 743 | 12504 | 21504–31504 |
| accion | 754 | 12515 | 21515–31515 |
| fantasia | 772 | 12533 | 21533–31533 |
| ternura | 745 | 12506 | 21506–31506 |
| misterio | 754 | 12515 | 21515–31515 |

La parte fija incluye base+un género+envoltura+reglas+esquema. **El total esperado de entrada queda aproximadamente21.5k–31.5k tokens**, no solamente base+género. El contexto es una previsión, NO un contexto ya completo: los ocho01 compactos existentes miden5423–10776; se reservan aproximadamente3500–8200 más para guion/memoria/ADN por referencias/manifiesto/niveles. El adaptador se construirá en el paso3. No se copian aquí datos de capítulos ni su ADN.
Un manifiesto grande puede superar ese rango. Medir cada escena real antes de cotizar. No truncar entradas esenciales para encajar el presupuesto. Imágenes, audio, envoltura del proveedor, respuesta y razonamiento no están incluidos. Reparación fija ronda12.5k más contexto, fallidas/vecinas y errores; no equivale al costo final. Contratos largos pueden exigir mayor presupuesto de salida: no se reutiliza a ciegas el tope viejo de16000.
Por defecto se adjunta un género, no los diez. Una escena con mezcla debe recibir solo los bloques realmente seleccionados para sus segmentos y medir ese texto completo; no dividir/reiniciar continuidad por comodidad.

## Placeholders e interfaz futura
La plantilla recibe `BASE_COMUN_V2`, `BLOQUE_GENERO_V2`, `REGLAS_SB_V1_JSON`, `CONTRATO_VINETA_V1_SCHEMA_JSON`, `CONTEXTO_ESCENA_JSON`, `CONTEXTO_CONTINUIDAD_JSON`, `REFERENCIAS_ADN_JSON`, `MANIFIESTO_ESPACIAL_JSON` y `NIVELES_CANAL_JSON`. Reparación añade contratos fallidos/vecinas, errores y alcance autorizado. El futuro cargador debe sustituirlos de forma literal y comprobar que no quede ninguno sin resolver, sin eval ni ejecución de contenido.
La salida de éxito propuesta es un array de contratos2.1.0. El pequeño objeto de diagnóstico `blocked/code/missing_inputs/responsible_module` se declara como propuesta nueva de transporte, no como parte del contrato ni función existente del motor. No se aceptará/renderizará como éxito. Requiere integrar y probar su consumidor en otro paso. No se inventan coordenadas/hashes/mediciones para completar required. Faltan contexto y comprobación física para aceptar una toma.

## Pruebas gratis, solo box
130/130 correctas: tokens700–1000, placeholders, diez enums, fila completa de matriz contrastada con la fuente, referencias a reglas/contrato,13 bloques, ADN y rechazo de variantes rotas. Red bloqueada durante el chequeo. Sin importar motor SB, ejecutar capítulos ni escribir datos.
El filtro de instrucciones de rediseño es estático y limitado; hubo también revisión textual. No demuestra obediencia del modelo: eso necesitará pruebas aparte con aprobación de gasto y posterior validador semántico. El tokenizador se precargó en el box descargando su vocabulario público; la prueba no necesita red ni credenciales. No se instala nada en213.
Comando local: `/workspace/herramientas_sb_tokenizador_t895/bin/python .../storyboard/contrato/comprobar_prompts_v2_offline.py --contrato /workspace/REVISION_TRASPASO_20261104/contrato_SB_t894 --tablas /workspace/reporte_t883/tablas.txt`.

## Respaldo, guardas y reversión
Respaldo completo anterior: `/opt/myia-taller-n8n/respaldos/antes_prompts_SB_t895_20261106_124738_bogota` (6-nov-2026 12:47:38 America/Bogota). Contiene `storyboard/`, `MANIFIESTO.json` y `SHA256SUMS`. SHA256 del manifiesto: `de0254542f03200e5d7d0aa962157ff09e762cfd302875d30e12bcac603cda74`.
Se comparan todos los74 archivos/enlaces preexistentes y los hashes de los18 archivos nuevos. La guarda toma texto/esquema activos explícitos; sus entradas no se tocan. El mapa nuevo queda fuera de `config/perfiles/`, y los géneros nuevos no figuran en el índice activo. No se cambian permisos de archivos anteriores.
Reversión propuesta, no ejecutada: como no se activó nada, basta no activarlo; si se quiere retirar la entrega, archivar SOLO los archivos nuevos listados en la evidencia de instalación, previa aprobación y sin borrar. No restaurar a ciegas la carpeta completa sobre cambios posteriores.

## Paso3, requiere siguiente aprobación
Completar el contexto de SB: acciones completas01, mirada_id, segmentos, posiciones; ADN por referencias ordenadas y manifiesto espacial. Cargador mínimo de los bloques seleccionados, sin sustituir a Argon. Se puede preparar/probar ese adaptador gratis con datos existentes; activar prompts, modificar guarda o tocar n8n no forma parte de este paso2. Toda prueba/generación/reparación con Argon sigue requiriendo «sí, gasta», cotización y los controles existentes.

Costo de este paso2: cero llamadas a IA y cero gasto.
