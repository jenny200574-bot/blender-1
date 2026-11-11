# PROGRAMA OFICIAL · Extracción ADN MYIA · v1 · 2-nov-2026
**Ricardo t211u:** este manual ES el programa que se le da a la IA para sacar ADN de personaje, objeto/poder, escenario o molde.

## Entrada
- `clase`: personaje | objeto | poder_energia | escenario | estilo | molde_scan
- `imagenes[]`: evidencias (frente/espalda/3_4/emociones/closeup según clase)
- Si clase=molde_scan: png del molde (+ depth/Object Index si hay)

## Motor de texto
Argon vía Banco `POST /api/adn` con la instrucción de `03_INSTRUCCIONES_ARGON.md` (cabecera común + pase A/B/C/D o U estilo).
Una imagen por llamada. Costo ~US$0.005.

## Salida
JSON schema `myia.adn.v3` (`01_SCHEMA_ADN_v3.json`) o `myia.molde_scan.v1` (`01b_SCHEMA_MOLDE_SCAN.json`).

## Reglas duras
1. FIJO = identidad (quién/qué). VARIABLE = molde_scan (dónde/cómo está).
2. Poderes/campos de fuerza = objeto con ADN.
3. No ADN desde molde gris low-poly.
4. Sin edad en PJ. Manilla ≠ anillo. Entorno: skyline sí, auroras no (si no están).
5. Altura solo Blender (o provisional sin sellar).
6. Cambio de FIJO = versión nueva (no parche).
7. VER bloquea gasto si falla checklist.

## Instrucciones Argon (programa completo)
Ver archivo embebido abajo y `03_INSTRUCCIONES_ARGON.md`.

## Escáner de molde (programa geométrico)
Ver `01c_ESCANER_MOLDE.md` + schema 01b. Preferencia: Blender metros → Object Index+depth → color (prueba).

---
# EMBEBIDO: 03_INSTRUCCIONES_ARGON.md
# 03 · Instrucciones listas para `POST /api/adn`
Uso: `{"imagen": <ruta>, "instruccion": <texto del bloque>, "pase": "A|B|C|D"}`. Se manda una imagen por llamada. Respuesta: SOLO JSON.

## Cabecera común (va primero en TODAS las llamadas)
```
Eres un perito forense de identidad visual. Describes SOLO lo que es INVARIANTE del sujeto: lo que seguiría igual si cambiara la pose, la emoción, la cámara, la luz o el fondo.
PROHIBIDO incluir en el sello: pose, gesto, emoción o expresión de esta foto, ángulo o encuadre de cámara, fondo, iluminación de la toma, acción, efectos de otra escena, porcentaje del cuadro, edad o años.
Si no puedes verlo con certeza, escribe null. No inventes medidas en cm ni kg.
Los lados (IZQ/DER) son SIEMPRE del sujeto, no de quien mira. Si dudas, escribe "lado_incierto".
Colores en HEX #RRGGBB muestreados de la zona iluminada media, no de los brillos ni de las sombras.
Responde SOLO JSON válido con las claves pedidas.
```

## Personaje
**Pase A – estructura:** «Devuelve {morfologia, complexion, proporciones:{cabezas_de_alto, hombros_sobre_cadera, largo_piernas_sobre_altura, tamaño_cabeza_rel}, rostro:{forma, mandíbula, nariz, cejas, forma_ojos, orejas}, pelo:{largo, corte, textura, dirección, flequillo}, rasgos_unicos[]}. Describe la cara como si fuera una ficha policial neutra: forma, no expresión.»
**Pase B – color/material:** «Devuelve {hex:{piel, pelo, pelo_reflejo, ojos_iris, cejas, labios}, capas:[{orden (1=más cercana a la piel), pieza, hex, hex_secundario, material, textura, ajuste, detalle (costuras, logos, botones: cuántos y dónde), removible (true si es mochila, bolso, gorra, accesorio que se quita)}]}. Enumera TODAS las prendas, desde la ropa interior visible hasta el calzado.»
**Pase C – ubicaciones (OBLIGATORIO completar):** «Devuelve ubicacion_partes[] con {parte, donde, lado, forma}. Escribe frases del tipo: "los ojos están a media altura de la cabeza, separados un ojo de distancia"; "el pelo cae hasta <hombro/omóplato/cintura>"; "el emblema está en el centro del pecho a la altura del esternón"; "la manilla está en la muñeca IZQ del sujeto, 1–3 cm sobre el carpo, rodea toda la muñeca"; "las gafas apoyan sobre el puente nasal". Cubre cabeza, cara, cuello, torso, brazos, manos, cintura, piernas, pies y cada accesorio. Si una parte no se ve en esta vista: visible=false.»
**Pase D – prohibidos:** «Devuelve {no_es[], confusiones_probables[], prohibidos[]}: lo que un generador podría equivocar (ej.: manilla→anillo, hoodie→chaqueta de cuero, gafas→sin gafas, color del pelo). NO incluyas emoción ni pose.»

## Objeto / poder / campo de fuerza / energía
Cabecera extra: «CLASE = objeto. Los poderes, energías, campos de fuerza y armas de energía son OBJETOS con forma fija. Describe el objeto aislado: ignora al portador, la mano, el personaje y el fondo. Si la imagen es un recorte diminuto, borroso o con trazos sueltos, responde {"gap": "evidencia_insuficiente"}.»
- **A:** «{subclase (solido|accesorio|poder_energia|campo_fuerza|arma), morfologia, silueta (palabras geométricas: cilindro, T invertida, enrejado N×M barras…), conteo (cuántas barras, puntas, anillos), proporciones:{largo_sobre_ancho, grosor_rel}, simetria}»
- **B:** «{hex:{nucleo, borde, glow, halo}, materiales, emisivo (sí/no), opacidad (0–1), textura (circuito, grieta, partículas)}»
- **C:** «ubicacion_partes[]: "el glow está en <aristas exteriores/núcleo/líneas grabadas>, se extiende <N× grosor>"; "las aristas están en…"; "el punto de anclaje es <mango/muñeca/suelo>"; "la punta está en el extremo <superior>". Para un accesorio que se lleva puesto: en qué parte del cuerpo va y en qué lado.»
- **D:** «{no_es[] (ej. "no es un anillo", "no es una cadena", "no es humo"), prohibidos[]}»

## Escenario
Cabecera extra: «CLASE = escenario. Describe el lugar vacío. Ignora personajes y efectos de poderes. Describe el cielo y el clima permanente del lugar, no el de la toma. Si se ven edificios, debes listarlos: NUNCA niegues el skyline. No menciones auroras, sol, arcoíris ni fenómenos que no estén en la imagen.»
- **A:** «{tipo_lugar, planos:[{plano (primer/medio/fondo), elementos[]}], linea_horizonte_pct_y, geometria (pretil: altura relativa, tanque: forma)}»
- **B:** «{hex por superficie (suelo, pretil, cielo, ventanas, edificios), materiales, fuentes_luz_fijas[] (farolas, neón: color + dónde)}»
- **C:** «ubicacion_partes[]: "el tanque está en el tercio <izq/der> del plano medio"; "el skyline ocupa todo el horizonte tras el pretil"; "la luz neón está en las ventanas de las torres".»
- **D:** «{prohibidos[] (incluye siempre: auroras si no se ven, gente, vehículos), no_es[]}»

## Estilo
Cabecera extra: «CLASE = estilo. La imagen trae un personaje de ejemplo: IGNORA su identidad (pelo, ojos, ropa, colores del personaje). Describe SOLO cómo está dibujado.»
- Pase único: «{linea:{grosor, color, variacion}, sombreado (cel N tonos, degradado), paleta_global_temperatura, tratamiento_ojos_generico (tamaño relativo, número de brillos), proporciones_genericas (cabezas de alto típicas), render (2D anime, plano/pintado), glow_tratamiento, nivel_detalle, prohibidos_estilo[] (fotorrealismo, 3D low-poly, acuarela)}». VER falla si aparecen hex de pelo u ojos de un PJ.

## QC post-generación (después de T1)
«Compara Imagen A (sello) con Imagen B (resultado), solo para la entidad <id> que está en bbox <x0,y0,x1,y1 %>. Devuelve {coincide_identidad (0–1), diferencias[], lado_manilla, prohibidos_presentes[]}.»

---

# Módulo VOZ (añadido Ricardo t212u) · 2026-11-02 09:30 COT

## Qué es
La voz es **ADN FIJO del personaje**, no del motor. Se sella junto al ADN visual en el perfil PJ (`perfil_pj/v2`).
`motor = null` hasta elegir Veo / ElevenLabs / otro. Camino: Parte 1 inmi (COPIA), no la F1 vieja atada a Veo3.

## Entrada (crear PJ)
- Descripción de voz: timbre, tono, ritmo, acento, idioma, edad_voz, energía, textura, dicción
- Opcional: `audio_ref` (muestra)

## Programa Argon / extractor de voz
Cabecera: «Eres perito de identidad VOCAL. Describe SOLO rasgos invariantes de la voz del personaje. PROHIBIDO: diálogo de una toma, emoción puntual, nombre de motor TTS, letra de canción.»
Pase único (o A–D cortos):
- A estructura: género percibido, rango vocal, edad_voz (categoría, no años del PJ visual)
- B coloratura: timbre, textura (breathiness, nasal, etc.), energía base
- C ubicación en el personaje: «esta voz pertenece a <id_pj>; idioma; acento»
- D prohibidos + frase_sello_voz

Schema:
```json
{
  "schema": "myia.voz_adn/v1_universal",
  "motor": null,
  "adaptadores": {},
  "idioma": "es-CO",
  "rasgos": {
    "timbre": "",
    "tono_pitch": "",
    "ritmo": "",
    "acento": "",
    "edad_voz": "",
    "energia": "",
    "textura": "",
    "diccion": "",
    "genero_percibido": ""
  },
  "audio_ref": null,
  "frase_sello_voz": "",
  "prohibidos_voz": ["cambiar timbre entre tomas", "acento distinto al sellado", "idioma no sellado"],
  "no_incluir_en_sello": ["texto del diálogo de la toma", "emoción puntual de una línea", "motor TTS concreto"]
}

```

## Prompt ensamblado (tras sello)
```
[Character: …ADN visual…; height (Blender); outfit …]
[Voice: …frase_sello_voz / rasgos…]
[Action: …VARIABLE…]
[Dialogue: "…"]
```

## VER voz
- FAIL si falta rasgo obligatorio → no sella
- FAIL si perfil alterado tras sello (hash)
- FAIL si el prompt de video inventa otro acento/timbre
- No ligar sello a Veo3

## Relación con imagen/molde
| Capa | Fuente |
|---|---|
| Visual FIJO | hojas + programa ADN imagen |
| Voz FIJO | este módulo |
| Geometría VARIABLE | molde_scan |
| Diálogo/acción VARIABLE | guion / toma |

## Fuente Parte 1 (inmi)
Ver `/workspace/COMUN_PRUEBAS/inmi/PARTE1_VOZ_PERFIL_PJ_20261102.md` y `inmi/parte1voz/`.
