# Paso3 · Entradas completas para SB — versión inactiva

Aprobado por Ricardo t896u; prueba con ambos canales conforme t898u. Universal: no hay IDs de canales/personajes/capítulos fijados en el módulo. **Es un ensamblador de contexto; NO dirige cámaras, no llama a Argon y todavía NO está conectado a SB activo.**

## Archivos nuevos
- `cajas/storyboard/entradas_sb_v2.py`: biblioteca estándar, solo lectura. API `assemble(taller, canal, capitulo, escena, manifest=None)`. CLI imprime JSON a stdout; no ofrece opción de guardar ni importar módulos activos.
- `cajas/storyboard/contrato/probar_entradas_sb_v2_offline.py`: pruebas gratuitas, solo box.
- `ENTRADAS_SB_V2_COBERTURA.json`, `ENTRADAS_SB_V2_PRUEBAS.json` y este informe, dentro de `contrato/`.
- Copia de datos, hashes y salidas completas de prueba SOLO en el box: `/workspace/REVISION_TRASPASO_20261104/entradas_SB_t896/` (`datos/`, `SNAPSHOT_SHA256.json`, `salidas/`). Se cotejaron los188 archivos del snapshot con los originales remotos. No se suben estas salidas a capítulos.

## Qué recibe el SB futuro
1. El JSON01 por escena, conservando acciones enteras, puntos/posiciones, todos los segmentos, rotaciones, pose, citas, emoción cualitativa, objeto/cambio, hechos y campos adicionales. Las tomas/cámaras viejas del01 se conservan como antecedente, NO mandato: SB decide las cámaras.
2. Enriquecimiento separado, sin cambiar la fuente: actor/nombres; mirada_id original y texto original; resolución solo por ID exacto o nombre exacto único, sin buscar coincidencias aproximadas ni adivinar huesos. Se mantienen gesto/manos si existen, no se fabrican cuando faltan.
3. Intervalos de acción/habla y segmentos convertidos a24fps con ROUND_HALF_UP, base1 y fin inclusivo. Duración en segundos y fps8 originales permanecen intactos. La conversión no multiplica duración ni finge voz medida. Diálogo del guion se conserva por separado, incluidos tono/acotaciones; si no hay correspondencia inequívoca no se inventa un timing de voz.
4. ADN de personajes por dna_ref_id, SHA256, imagen/ruta/vista verificadas y orden estable. Prioridad de la hoja aprobada del sello; en biblioteca, versión aprobada y hashes de imágenes. Cambio de forma ambiguo o imagen alterada bloquean. IDs de actores nunca se renombran para encajar.
5. Referencias de set/props inventariadas por ID exacto, con ficha o sello si existe. Ficha aprobada sin imagen/hash no se convierte en referencia visual. Sellado lógico + imagen generada tampoco se inventa como aprobación humana: los candidatos quedan rotulados; el catálogo aprobado visual se mantiene separado.
6. Manifiesto espacial si hay uno en ubicaciones canónicas bajo cubos02/02N/escena/SB, o ruta explícita dentro de cubos del capítulo. Si falta: estado literal **«falta manifiesto»**, data=null y bloqueo del paso4. Si existe, se conserva sin certificar geometría. Nunca se convierten los puntos planificados01 ni un molde antiguo en manifiesto Blender medido.

## ADN sin texto de apariencia
Se retiran del contexto los bloques version_personaje/never_changes/nunca_cambia, referencias antiguas opacas y la respuesta original opaca del01. Del bloque parametros_3d se separan colores/gordura/pelo/ropa y controles no acreditados como transitorios; sí se preservan expresión/valor, pose, mirada, gesto y manos cuando existen. Las rutas excluidas quedan auditadas. El archivo01 completo sigue intacto y tiene SHA256: no se borra ni altera el original.
El checksum de sello es SHA256 de sus bytes completos. El de biblioteca es SHA256 del JSON canónico del registro personaje+versión; se documenta el ámbito, no se finge que fuera un checksum preexistente. La prosa de apariencia se usa internamente solo para calcular el hash del registro, no se copia al prompt. Guion y citas literales pueden mencionar colores/rasgos como hechos narrativos: se conservan como datos, no instrucciones de ADN.
Orden de imágenes: character_id ascendente; forma inicial y después final si cambia; vistas según sin_lado del sistema, otras por nombre; fallback refs en su orden declarado. Los slots según sujeto primario/secundario/prop se decidirán por viñeta después de que Argon elija sujeto. Las entidades solo voz no requieren imagen ni se ponen automáticamente en cuadro.

## Identificadores y fuentes
Acepta número entero/string numérico de capítulo, ep-ID o nombre completo de carpeta. Debe resolver exactamente UNA carpeta: ante dos coincidencias se bloquea, nunca toma la primera. No acepta booleanos, decimales tipo1.0, rutas o globs. La escena acepta número o ID seguro, por ejemplo POSCREDITOS. Rutas protegidas, recorrido .. y symlinks que salen del taller se rechazan.
Guion: usa el pedido base.txt del que procede el mapa, no el primer recorte de investigación. Si falta ese pedido, solo acepta una variante única entre los demás. Soporta cabeceras ESCENA y títulos numerados que coinciden literalmente con el mapa; un emparejamiento ambiguo queda sin resolver. Diálogos inline y multilínea se conservan sin convertir acotaciones en voz.

## Cobertura por escena
Guardianes:8 salidas guardadas,206 acciones y183 segmentos preservados. ADN visual de todos sus personajes verificado en las8 escenas; falta01 de escena3. Génesis:5 archivos01 existentes; solo escena9 es accion_v1 (21 acciones);4/7/8/10 son formatos antiguos sin acciones, y quedan señalados sin regenerarlos.

| Canal | Escena | Acciones | Segmentos | Puntos | Mirada_id preservados / objetivos resueltos | ADN personajes verificados/solicitados | Diálogos del guion | Manifiesto |
|---|---|---:|---:|---:|---|---|---:|---|
| Génesis | 4 | 0 | 16 | 0 | 0 / 0 | 2/6 | 8 | falta |
| Génesis | 7 | 0 | 29 | 0 | 0 / 0 | 4/4 | 31 | falta |
| Génesis | 8 | 0 | 0 | 0 | 0 / 0 | 3/4 | 27 | falta |
| Génesis | 9 | 21 | 11 | 4 | 0 / 13 | 4/4 | 17 | falta |
| Génesis | 10 | 0 | 15 | 0 | 0 / 0 | 2/2 | 7 | falta |
| Guardianes | 1 | 25 | 35 | 11 | 14 / 4 | 6/6 | 8 | falta |
| Guardianes | 2 | 16 | 20 | 9 | 2 / 2 | 6/6 | 8 | falta |
| Guardianes | 4 | 42 | 38 | 15 | 30 / 17 | 5/5 | 13 | falta |
| Guardianes | 5 | 26 | 12 | 6 | 0 / 2 | 2/2 | 12 | falta |
| Guardianes | 6 | 18 | 12 | 10 | 0 / 6 | 6/6 | 10 | falta |
| Guardianes | 7 | 25 | 12 | 8 | 0 / 16 | 6/6 | 9 | falta |
| Guardianes | 8 | 26 | 28 | 12 | 12 / 6 | 6/6 | 11 | falta |
| Guardianes | 9 | 28 | 26 | 7 | 14 / 13 | 6/6 | 5 | falta |

Los objetivos resueltos también incluyen nombres únicos de acciones SIN mirada_id: no son un subconjunto del contador de IDs. El resto permanece con su ID/texto fuente, sin inventarle entidad u ojos. No hay huesos oculares medidos, arousal/valence numéricos ni estado de manos explícito garantizado; las poses y actuación disponibles sí se conservan. Los pasos posteriores deben completar/validar lo que toca a Argon y al manifiesto, no rellenarlo a cero.
Génesis escena4:ADN visual2/6; escena8:3/4. Faltan referencias aprobadas/resolubles para algunos personajes secundarios o formas; el programa no las diseña ni aprueba. Los otros archivos01 de su mapa faltan para1,2,3,5,6,11,12,13,14 y POSCREDITOS. No se evaluaron como salidas01 existentes.
En ambos canales hay candidatos de set/utilería, pero no referencias visuales que cumplan todos los requisitos estrictos de aprobación+hash para enviarlas como aprobadas. Se detallan en las salidas de prueba. Esto no significa que no existan imágenes: significa que no se inventa su aprobación ni una correspondencia de ID. El contrato por viñeta determinará cuáles son necesarias.

## Trece bloques: entradas no equivalen a contrato terminado
`contract_input_coverage` contiene los13 bloques por CADA escena (JSON de cobertura). Narrativa/emoción: acciones/citas disponibles, decisión numérica pendiente Argon; acción/audio:parcial; sujetos/U:Argon; ADN/estado:parcial por manos/rig; transforms:posiciones01, no mediciónBlender; set/tiempo:reloj24, bounds faltantes; plano:Argon; óptica/geometría:manifiesto/solver pendientes; movimiento:Argon; continuidad:fuente01, validación pendiente; referencias:parcial por set/props/ADN faltante; Gates:pendientes; aceptación:bloqueos explícitos. No se declara aprobado un contrato ni un fotograma.

## Pruebas y límites
**181/181 correctas**,13 escenas reales de ambos canales. Red bloqueada durante pruebas; solo importaciones estándar, ninguna llamada al motor, pago o Blender. Verificado que todos los archivos del snapshot real permanecen idénticos después. Casos artificiales rotulados se crearon en carpetas temporales del box y se conservaron, sin borrados.
Incluye tiempos/fracciones/NaN/bool, intervalos inválidos, capítulos ambiguos, ep equivalente a entero, rutas protegidas/symlink exterior, conservación exacta de acciones/segmentos/puntos/miradas, ADN sin prosa, SHA de imagen alterado, diferenciación de aprobación visual, ausencia/duplicidad de manifiesto, guion de ambos formatos y controles transitorios frente a aspecto. Son pruebas de ensamblaje, NO prueba de dirección IA ni solver físico.
Comando local: `python3 -B .../storyboard/contrato/probar_entradas_sb_v2_offline.py --datos .../datos/opt/myia-taller-n8n`. No ejecutar contra capítulos para guardar nada: el módulo imprime stdout y las pruebas escriben solo casos artificiales fuera de ellos.

## Respaldo y guarda
Respaldo anterior completo: `/opt/myia-taller-n8n/respaldos/antes_entradas_SB_t896_20261106_130359_bogota` (6-nov-2026 13:03:59 America/Bogota), con MANIFIESTO.json y SHA256SUMS. SHA256 del manifiesto: `b486cd1b786876c9dfe9370f0421de843388f1f66562dfea4ae580c25e9bdd4d`.
Se verifica que los92 archivos/enlaces anteriores del SB siguen iguales por hash y permisos; solo se agregan estos5 archivos. cubo_sb.py, selector_perfiles.py, prompts/config activos y guarda de texto fijo no se modifican. n8n y datos de capítulos no se escriben. Este módulo no entra automáticamente en ninguna importación activa.
Reversión, no ejecutada: no activarlo basta para dejar todo como estaba. Si se pide retirar los5 archivos nuevos, archivarlos sin borrar y sin restaurar a ciegas la carpeta completa sobre cambios posteriores.

## Siguiente paso4
Exportar o reutilizar, desde Blender/Ako, el manifiesto real de rigs/huesos/ojos/alturas/transforms y paredes/obstáculos antes de pedir cámaras. No inventarlo con coordenadas del01. Es trabajo local gratuito si se usa el cómputo ya disponible; requiere nueva aprobación. Activación de este adaptador, cambio de guarda/n8n y pruebas con Argon quedan para pasos separados; cualquier llamada IA requiere «sí, gasta».

Costo de este paso3: cero llamadas IA, cero gasto y ninguna escena regenerada.
