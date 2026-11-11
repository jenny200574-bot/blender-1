# 05 · Módulo VOZ ADN universal

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


## Extracto informe inmi

# Parte 1 · Voz dentro del perfil del personaje (2-nov-2026, 09:24 Bogotá)

**Resumen para Ricardo:** Ya está montado en la COPIA (JTYnu9oItUj6okH9, sigue apagada) el camino que pediste:
**crear personaje → desarrollar la voz → sacar el ADN de la voz → sellarlo FIJO en el perfil → al llamar el personaje, el prompt recibe su ADN y el de su voz juntos.** Costo US$0.

## Cómo funciona (rama nueva "ADN · crear PJ · …", abajo de F1 Voz)
1. **Datos PJ + voz (captura):** se escribe el personaje y se describe su voz (timbre, tono, ritmo, acento, idioma, edad, energía, textura, dicción). También acepta una referencia de audio (`audio_ref`) para después.
2. **Extraer ADN de voz:** convierte la descripción en un ADN de voz **universal** (`voz_adn/v1_universal`). No está atado a Veo 3: `motor = null` y `adaptadores = {}`; el motor (Veo, ElevenLabs u otro) se elige después.
3. **Sellar FIJO en el perfil:** el perfil `perfil_pj/v2` guarda juntos `adn_personaje` + `voz_adn` con un sello (hash). Si falta algún rasgo de voz, **no sella** y se detiene (FAIL).
4. **Cargar módulo PJ → Ensamblar prompt:** revisa el sello (si alguien cambió la voz o el personaje, bloquea) y arma:
```
[Character: Ejemplo — young woman, dark wavy hair; height (medir en Blender); outfit white linen dress]
[Voice: young adult female voice, warm soft timbre, medium-high pitch, gentle Colombian Spanish accent, calm unhurried pace, slight breathiness, clear diction, low-medium energy; language es-CO]
[Action: walks to window]
[Dialogue: "Hola"]
```

## Pruebas (local, mismo código de los nodos)
- Ejemplo completo: sella y arma el prompt ✔
- Perfil alterado después del sello: bloquea ✔
- Voz incompleta: no sella ✔

## Seguridad
- Respaldo antes del cambio: `/opt/myia-taller-n8n/respaldos/inmi_parte1voz_20261102/bak_antes_P1.json` (y `inmi/parte1voz/`).
- 303 → 312 nodos; los 303 anteriores y sus conexiones quedaron idénticos. Sin HTTP, sin Veo, sin pintar, sin --origen, ADN de Ako sin tocar.
- Perfil de ejemplo: `/opt/myia-taller-n8n/cajas/perfiles_pj/perfil_ejemplo_STUB.json`.

## Falta (siguiente parte, con tu OK)
- Formulario real para crear PJ / describir voz (hoy usa datos de ejemplo).
- Guardar el sello en disco de verdad y leer el perfil real desde "5. Personajes".
- Conectar el ensamblador al prompt real (F3 / 08) y elegir motor de voz.
- La rama F1 vieja (voz_pj/v1 con Veo 3 primario) queda como está; la nueva universal la reemplazaría cuando lo apruebes.
