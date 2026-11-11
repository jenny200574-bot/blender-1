# SB · Reglas y contrato de viñeta — edición 1

**Paso 1 aprobado por Ricardo (t894u). Sin IA, sin gasto y sin tocar n8n.**

## Qué queda fijado
Argon es el director principal. Decide la historia, emoción, sujeto, planos, lentes, altura/ángulo, movimientos y montaje. El programa entrega contexto, comprueba las decisiones y calcula la ejecución física. No inventa decisiones ni cambia las buenas por otras.

El 01 aporta acciones, tiempos, posiciones e IDs. ADN aporta identidad y apariencia aprobadas. Blender aporta medidas, anatomía, huesos y obstáculos. Si falta alguno, se identifica el responsable y se bloquea, sin fabricar datos.

**Reglas: 1.0.0. Contrato nuevo: 2.1.0. JSON Schema: draft 2020-12.** Se sube desde el ejemplo 2.0.0 porque se añaden requisitos explícitos y restricciones: no se finge que lo viejo ya cumple. Los archivos son nuevos y todavía NO están conectados al motor actual.

## Equivalencias y cuándo usar los planos
`r_head` = altura proyectada de la cabeza / altura de imagen, no fracción del cuerpo visible. No son intercambiables.

| Plano | Equivalencias antiguas | r_head | Corte | Usar | Prohibir |
|---|---|---|---|---|---|
| GPG | EWS | 5–12% | Escenario completo, figura integra pequena | Apertura, cambio de locacion, aislamiento | Dialogo intimo; mas de uno cada6 vinetas |
| PG | WS, FS | 15–22% | Pies a coronilla | Geografia, comedia fisica | Microexpresion |
| PA | MFS, COWBOY | 25–35% | Muslo/rodilla a cabeza | Manos y rostro, accion a cintura | Brazos inactivos sin desplazamiento |
| PM | MS | 38–48% | Cintura a cabeza | Dialogo expositivo | Climax de confesion |
| PMC | MCU | 52–62% | Esternon/axilas a cabeza | Tension, ojos y respiracion | Accion en piernas o entorno |
| PP | CU | 68–82% | Clavicula a cabeza | Revelacion y reaccion decisiva | Saludos triviales |
| GPP | ECU | >90% | Menton/labio a cejas | Punto de giro unico | Mas de uno por escena |
| PD | INS | No aplica; objeto ocupa 50–80% | Objeto o mano critica; objeto50–80% del cuadro | Catalizador que requiere lectura visual | Objeto casual o PD consecutivos |

CEN, PIC, CPIC y POV **no son tamaños**: son ángulos o punto de vista. CEN = cenital, solo para patrón/aislamiento y no diálogo normal. PIC/CPIC = inclinación de 20–45° para asimetría, no cuando estatus y cota son iguales sin motivo. POV exige mostrar antes al personaje mirando. Las palabras del DSL antiguo se traducen a estos códigos; no se cambia hoy su diccionario.

## Reglas cerradas
- Generales = GPG+PG. Máximo global **20%**. Solo acción/comedia con desplazamiento real mayor de 2 m permite **35% global**. Sin prueba de ese movimiento, sigue 20%.
- La ventana de cinco viñetas mantiene **máximo un general**, incluso en la excepción. Además, GPG separados al menos seis posiciones. Si una escena corta no admite un general por la razón porcentual, no se redondea el cupo al alza.
- **GPP: máximo uno por escena. PD: nunca dos seguidos.** Cada PD necesita a la vez: objeto catalizador de la trama, lectura visual indispensable y contador de PD anteriores consecutivos igual a cero; con cita justificativa. Una mano en PD sigue necesitando ese objeto/acción crítica, no un gesto decorativo.
- La cámara nace **LOCK**: sin recorrido, cambio focal ni sacudida. Mover requiere motivo narrativo verificable. **Dolly In exige Δarousal≥+0,15** comprobado contra el estado anterior; escribir REVEAL no basta. Si no hay dato anterior, se bloquea o vuelve a Argon, no se supone.
- En diálogo, escucha, duda o emoción manda el rostro/triángulo ocular: peso facial ≥0,75. El sujeto y su hueso objetivo están declarados; no se toma automáticamente al primero de la lista ni al origen de los pies. Objetos no ganan por estar cerca o mencionarse.
- 180°: conservar el lado del eje. Cambiarlo requiere cruce visible, plano neutro o acción que establezca un eje nuevo, con causa declarada; no es una excepción silenciosa.
- 30°: corte al mismo sujeto exige cambio de ángulo ≥30° o cambio relativo de escala de cabeza ≥35%. Raccord de mirada/altura recíprocos y diferencia relativa de escala de cabeza ≤8% entre planos comparables. Unión de posiciones: diferencia <0,02 m.
- Este contrato adopta pre-roll **0,8–1,5 s para cada intervención con diálogo**, como política estricta. El informe lo explicaba especialmente para confesiones críticas. Puede comenzar en la viñeta anterior; no alarga acciones del 01 sin autorización. Reacción: reactor, microacción visible y silencio medido, sin duración inventada como hecho real.
- L/J no son solo etiquetas: voz e imagen tienen pistas/tiempos independientes. El audio puede cruzar la frontera visual; no se recorta a la viñeta. El desfase debe quedar especificado y comprobarse en el contexto editorial.
- ADN inmutable: identidad por `dna_ref_id` y hash, referencias ordenadas. No redactar de nuevo colores, cara, peinado, ropa, textura ni proporciones. Solo actuación y estado transitorio autorizados. El esquema impide campos nuevos de apariencia; la prosa también necesita control semántico, no basta una lista de palabras.
- No aplicar altura ocular >0,50 m ni proporciones humanas a cualquier personaje. El fallback por 0,93/0,67 de altura queda **deshabilitado**: usar ADN/manifiesto real o bloquear. Personaje no humano/sin ojos requiere representación anatómica aprobada, no inventarle un rostro.
- Para video IA rigen además los límites del informe: giro ≤15° y traslado ≤0,40 m/s por viñeta. El género no los anula.

## Reloj de 24 fps
Base de cuadro 1 y fin inclusivo. `inicio = round_half_up(segundos_inicio×24)+1`; `fin = round_half_up(segundos_fin×24)`. Cuadros = fin−inicio+1. Ejemplo del informe: 7,5–11,5 s → cuadros 181–276, **96 cuadros = 4 s**. Visualmente se cuantiza a 1/24 s una sola vez, con error máximo de medio cuadro y registro del ajuste. La voz conserva sus muestras/segundos medidos. No cambia hoy el fps de ningún archivo del 01.

## Los 13 bloques obligatorios
1. Narrativa/emoción: beat, hecho atómico, propósito, género, emoción primaria/secundaria, activación, valencia, fuente y justificación. Δarousal obligatorio en Dolly In.
2. Acción/diálogo/reacción: IDs, texto, tono, tiempos, corte, pre-roll y reacción. Diálogo o reacción pueden ser null si realmente no existen; no crear frases para llenar campos.
3. Sujetos/jerarquía: puntuaciones, pesos normalizados y sujeto primario/secundario; secundaria puede ser null. En PD se exige prop_focus con las tres condiciones y evidencia.
4. Personajes: ID ADN/hash, prohibición de override, altura y estado transitorio de mirada/postura/manos.
5. Transformaciones espaciales: posiciones, ojos y orientación medidos, metros, Z arriba.
6. Set/tiempo: ID, bounds, luz, segundos y cuadros a 24 fps.
7. Plano/encuadre: código, región anatómica, r_head, ojos y aire de mirada.
8. Óptica/geometría: lente, altura, rig, foco, inicio/fin y posición/aim. Tórica puede ser null si otra solución física validada basta.
9. Movimiento/motivo: LOCK por defecto y parámetros verificables.
10. Continuidad/transición: eje, diferencia angular, miradas y cortes.
11. Referencias ADN: slots ordenados, roles, activos y rutas aprobadas.
12. Tolerancias/Gates: ojos visibles, cabeza dentro, márgenes y oclusiones.
13. Aceptación/corrección/bloqueo y responsable. Las fórmulas en texto son descriptivas; **jamás se ejecutan con eval**.

## Lo que comprueba el esquema y lo que necesita contexto
`contrato_vineta_v1.schema.json` es un esquema real: tipos, required, enums, rangos, tamaños de vectores, SHA256, campos extra prohibidos y restricciones condicionales para tamaño de plano, PD y Dolly In. Se valida con `jsonschema.Draft202012Validator`, no importando el motor SB.

No puede comparar por sí solo dos viñetas, leer un ADN ni lanzar un rayo contra un .blend. Esos checks cruzados se enumeran en `reglas_sb_v1.json`. La autoprueba implementa un subconjunto lógico para comprobar el diseño, no un motor de producción. **Pasar el JSON Schema no equivale a aprobar una toma.** Faltan contexto completo, checksums reales, continuidad y Gate1 de Blender antes de operar.

| Chequeo cruzado | Requisito |
|---|---|
| SB_ID_COVERAGE | IDs/ADN validos, hechos cubiertos sin duplicar ni alterar causalidad; simultaneidad declarada |
| SB_EMOTION_SOURCE | Emocion trazable; interpolacion solo con vecinos validos compatibles, no inventar extremos |
| SB_UTILITY | Pesos suman1; comprobar U y prioridad facial en dialogo/escucha/emocion, sin sustituir a Argon |
| SB_PD | Catalizador y lectura indispensable verdaderos, contador previo0 y cita del guion |
| SB_QUOTAS | 20% amplios, excepcion35% medida, ventana5 max1, GPP max1, GPG separados>=6 |
| SB_DOLLY | Delta arousal>=0.15 contra estado anterior; REVEAL no exime |
| SB_LOCK | LOCK sin trayectoria, cambio focal o sacudida; movimiento con motivo verificable |
| SB_AXIS | Semiplano 180; reestablecer solo por cruce visible/plano neutro/accion, causa declarada |
| SB_30 | Mismo sujeto al corte: >=30grados o cambio relativo de escala>=35% |
| SB_EYELINE | Reciprocidad de mirada/altura; escala relativa de cabeza entre planos comparables difiere<=8% |
| SB_AUDIO | Voz/texto fieles, pre-roll0.8–1.5s, tono/reaccion/hold, pista independiente para L/J |
| SB_CLOCK | 24fps, base1, frames inclusivos coherentes, sin huecos ni solapes |
| SB_DNA_LOCK | Ref+hash aprobados, slots ordenados, sin aspecto nuevo ni override; no confiar solo en regex |
| SB_SPATIAL | Medidas/huesos/transforms del manifiesto; no adivinar ojos ni imponer altura humana |
| SB_OPTICS | XYZ/foco derivado de elecciones de Argon y anatomia; comprobar r_head/aire de mirada |
| SB_GATE1 | Raycast y proyeccion durante recorrido, paredes/muebles>=0.25m, personajes>=0.45m, max3 rondas sin cambiar intencion |
| SB_GATE2 | Vision solo con advertencias y aprobacion; nunca aceptar por schema sin contexto/Gate1 |
| SB_PATCH | Solo fallidas; hashes de aprobadas intactos; revalidar continuidad de vecinas |

## Contradicciones resueltas
Se eligió la variante conservadora y se dejó escrita; no son supuestas capacidades del motor actual.

- **Dolly In: REVEAL sin delta:** Orden aprobada mas estricta: delta>=0.15 siempre
- **35% vs ventana20%:** 35% solo global con accion/comedia y traslado>2m; ventana5 sigue max1
- **GPG cada6 vs ventana5:** Cumplir ambas, distancia indices>=6 y ventana5 max1
- **Ejemplo inicia voz0.60s y no trae pre-roll:** Original incompatible; fixture solo de prueba usa0.8s, no modifica un capitulo
- **Payload2.0.0 usa $schema sin ser esquema:** Crear esquema real draft2020-12; payload nuevo2.1.0, sin fingir compatibilidad
- **CEN/PIC/CPIC/POV mezclados con tamanos:** Son angulos/punto de vista separados de GPG..PD
- **Alturas humanas asumidas:** Medidas ADN/manifiesto; fallback antropometrico deshabilitado y sin minimo0.50m universal
- **Formula invertida en tipografia del texto:** D=h_head*f/(r_head*sensor_h), consistente con unidades y tabla
- **Programa vs direccion de IA:** Argon decide; correcciones fisicas solo dentro de tolerancias sin cambiar intencion
- **Bloque13 culpa a01 por emocion faltante que SB puede inferir:** En contrato2.1, emocion/beat cinematografico faltante se asigna a SB_ARGON; falta de accion de entrada se distingue como MISSING_UPSTREAM_ACTION del01. Son etiquetas normativas nuevas, no codigo integrado.

Además: las tolerancias de encuadre del bloque12 y el ±8% de raccord no se confunden: el primero limita el resultado respecto a lo esperado; el segundo compara escalas de dos planos. Los campos de la muestra no prueban geometría real. La versión2.1 separa responsabilidad de emoción/beat cinematográfico (`SB_ARGON`) de falta de acción de entrada (`MISSING_UPSTREAM_ACTION`, 01).

## Ejemplos y autoprueba
- `ejemplo_informe_original.json`: copia intacta del ejemplo 2.0.0. **Es incompatible con el nuevo contrato**, y la prueba lo detecta: no se adapta a escondidas.
- `ejemplo_v1_solo_prueba.json`: fixture expresamente artificial, nunca dirección de un capítulo. Cambia versión a2.1, añade pre-roll0,8, desplaza el inicio de voz de0,60 a0,80, añade pesos a partir de los cuatro scores del ejemplo, usa Δ0,22 de un ejemplo del mismo informe y separa responsables. El contexto previo0,56 de la autoprueba es ficticio (0,78−0,22), no una medición.
- `autoprueba_offline.py`: se ejecuta **solo en el box**, no sobre el 213 ni capítulos. Requiere jsonschema. No usa IA/red, no importa cubo_sb y no escribe datos.
- Resultado: **20/20 pruebas correctas**. El original se rechaza como incompatible; el fixture adaptado cumple esquema y controles lógicos disponibles. Se detectan ADN override, apariencia añadida, arousal inválido, pre-roll corto, Dolly insuficiente, ratio de cabeza incorrecto, flags PD, cuadros, pesos, GPP/PD repetidos y cuota sin excepción probada.

## Archivos actuales y guardas
Se añaden únicamente estos documentos/esquemas/ejemplos/autoprueba dentro de `storyboard/contrato/`. No se modifica ningún código, prompt, esquema o configuración ya utilizado por SB. Su guarda de texto fijo toma el texto/esquema explícitos de los prompts actuales: no incluye automáticamente esta carpeta nueva. Se verifican hashes de todos los archivos preexistentes antes/después. No se cambia ni se desactiva la guarda; integrar este contrato en un paso posterior exigirá registro de la versión aprobada.

## Siguiente paso 2 — todavía no aprobado aquí
Redactar el prompt base y los diez bloques de género con estas reglas, manteniendo a Argon como director. El esquema nuevo y el motor actual todavía no son compatibles por sí solos: su integración, validadores y registro de prompts fijos son pasos posteriores separados. No hacer llamadas pagas ni tocar n8n en ese trabajo sin nueva orden.

## Fuentes
Informe de Ricardo (`reporte_t883/r.txt`, 1.4–1.8 y contrato; `tablas.txt`, tablas0,1,4,6). Hechos reales del SB leídos en `cubo_sb.py`, `esquemas_sb.py`, `validador_sb.py` y configuración. Las elecciones conservadoras de esta edición están rotuladas arriba, no presentadas como citas literales.
