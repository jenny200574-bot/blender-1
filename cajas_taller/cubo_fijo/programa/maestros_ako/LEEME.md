# Maestros Ako · OFICIALES del taller n8n · v1 (2-nov-2026)

**Origen:** Ako, «Reporte completo · Proceso para armar el prom (imagen) · 2-nov-2026 COT» (prueba V1 esc11, ledger **#418** acción v2, **#419** auditoría, **#420–#421** generación V1, US$0.134). Orden de Ricardo: estos son los comprobados y pasan a ser los OFICIALES, adaptados a cualquier canal.

**Copiado byte a byte** desde los bloques de código del reporte (sección 4 plantilla, 5.1–5.5 Maestros). Las fuentes .txt de Ako (`/workspace/COMUN_PRUEBAS/ako/CERO_20261102_moldes_guiones/…`) no estaban en este disco; el texto es el del reporte. Los originales sin tocar están en `ORIGINAL_AKO/`.

## Archivos
| archivo | Maestro | cambios vs Ako |
|---|---|---|
| 00_PLANTILLA_DIRECTOR.txt | Plantilla de campos del prom director (01_PAPEL…08_PROHIBICIONES) | 3 (ver abajo) |
| 01_MAESTRO_ACCION_v2.txt | Bloque de Acción v2 (molde) | ninguno (idéntico) |
| 02_MAESTRO_PERSONAJE_HOJA_ADN.txt | Personaje: hoja (FASE 1) + ADN 5 bloques (FASE 2) | 3 (ver abajo) |
| 03_MAESTRO_OBJETOS.txt | Objetos fijos (props), 5 bloques | ninguno (idéntico) |
| 04_MAESTRO_ESCENARIOS.txt | Escenarios, 5 bloques | ninguno (idéntico) |
| 05_MAESTRO_ESTILO.txt | Estilo del canal («4 bloques» + 5 Prompt Compacto, tal cual Ako) | ninguno (idéntico) |
| overrides.json | reglas fijas canal+escena (lo que salió de 08_PROHIBICIONES) | nuevo |

## Cambios exactos (SOLO variables; lógica, reglas y formato de salida intactos)
**02_MAESTRO_PERSONAJE_HOJA_ADN.txt**
1. línea 2: `# Canal: Anime (variable según canal) · Génesis / Luna y Kiko` → `# Canal: {ESTILO_CANAL} (variable según canal) · {CANAL}`
2. ROL: `(Anime — este es contenido variable según canal)` → `({ESTILO_CANAL} — este es contenido variable según canal)`
3. FASE 1: `(estilo Anime — variable según canal — limpio` → `(estilo {ESTILO_CANAL} — variable según canal — limpio`
   (Turnaround, regla de limpieza, cuadrícula de 5 expresiones y los 5 bloques de FASE 2: sin cambio.)

**00_PLANTILLA_DIRECTOR.txt**
1. 05_ADN_PERSONAJES_FIJO: `[ADN_KAEL]` `[ADN_NOVIA]` `[ADN_ALIEN]` → `{ADN_PERSONAJES_LISTA}` (un bloque ADN por cada personaje del casting de la toma, en orden). `(casting: exactly [N] characters: [NOMBRES])` sigue igual.
2. 06_ADN_OBJETOS_FIJO: `[ADN_MANILLA]` `[ADN_PRISION]` `[ADN_LANZA]` → `{ADN_OBJETOS_LISTA}` (un bloque por objeto/prop que llevan los personajes de la toma). `(+ otros props: [ADN_PROPS_EXTRA])` sigue igual.
3. 08_PROHIBICIONES: `SIN mochila (Kael esc11) · SIN auroras · NO anillo de dedo` → `{PROHIBICIONES_CANAL_ESCENA}` (sale de `overrides.json` por canal+escena). Quedan fijas y universales: `Sin texto en imagen` · `NO low-poly del molde como material final` · `Emoción solo en VARIABLE`.
   En overrides.json (canal cn-gnesis…, escena 11) se guardaron las 3 de Ako; «SIN auroras» queda en `desactivadas` por la propia lección #419 de Ako (auroras permitidas si están en Imagen 1).

Los demás huecos (`[FONDO_REF]`, `[MOLDE_REF]`, `[HOJAS_LISTA]`, `[ESTILO_REF]`, `[ADN_ESCENARIO]`, `[ADN_ESTILO]`, `[N]`, `[NOMBRES]`, `[BLOQUE_ACCION_MOLDE]`, `[GUION_PEDAZO]`, `[PLAN_TOMA]`, `[SCAN_UTIL]`, `[ADN_PROPS_EXTRA]`, y los `[Pegar aquí…]` del Maestro de acción) ya eran variables de Ako: se llenan en el momento, no se cambian en el archivo.

## Formato ADN guardado (cubo_fijo.py v2)
`adn/<adn_id>_ako.json` · schema `myia.adn.ako/v1`: `bloques` (1…5 con título de Ako), `inyeccion` (= bloque 5 «Prompt Compacto de Inyección» en objetos/escenario/estilo; en personaje Ako no trae párrafo 6 → el director usa los 5 bloques), `maestro` + `maestro_sha256`, `status` PASS_SELLABLE/FAIL.
El ADN forense A–D viejo (`adn/<id>_v3.json`, programa anterior) queda como histórico/control; el director NO lo usa.

## Respaldo del programa anterior
`/opt/myia-taller-n8n/respaldos/inmi_maestros_ako_20261102/` (copia íntegra de `programa/` forense A–D y de `cubo_fijo.py` v1 antes de este cambio). Los archivos forenses siguen además en su sitio (`programa/*.md|json`): no se borró nada; quedan como histórico/control.

## Variables del canal
`{ESTILO_CANAL}` y `{CANAL}` salen del pedido (`estilo_canal`) o de `cajas/cubo_fijo/canales/<canal>.json` (copiado de la ficha del canal: `style_fijo.nombre` + nombre). Si no hay, el pedido sale con `faltan_variables` (no se inventa).
