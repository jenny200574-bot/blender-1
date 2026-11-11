# -*- coding: utf-8 -*-
"""MYIA · Taller n8n · paso 2 programa de imágenes (31-oct-2026, America/Bogota).
GRATIS, sin red, sin IA. Empaqueta escenario.json (fuente=4a1) + glosario + sidecars
→ escena_nivel2.json (Nivel 2 de la plantilla) para que el cubo 11 lo lea.

Uso (entrada restringida n8ntaller):
  paso00_cadena escena armar --canal CID --capitulo N
  paso00_cadena escena armar --canal CID --capitulo N --lugar-id esc-calle-ciudad --escena-num 10
  paso00_cadena escena leer  --canal CID --capitulo N
  paso00_cadena escena armar --escenario PATH --escena-num 10 --out PATH
  paso00_cadena escena sidecar --sheet PATH --nombre N --version V --desc '...'
  paso00_cadena escena sidecar --refs-dir DIR --from-texto frente.json --nombre N --version V
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

CAJAS = Path("/opt/myia-taller-n8n/cajas")
TRABAJO = Path("/opt/myia-taller-n8n/trabajo/paso00_cadena")
ESQUEMA = CAJAS / "FIJOS_TALLER" / "escena" / "esquema_escena.json"

GLOSARIO_FORMAS_TALLER = CAJAS / "FIJOS_TALLER" / "glosario_formas.json"
DESC_ROPA_SCHEMA = "myia.desc_ropa.v1"
DESC_ROPA_FILENAME = "desc_ropa.json"

# Diccionario determinista ES→EN para atmósfera/paleta (programa, no IA).
# Frases largas primero. Si tras aplicar queda demasiado español → FALTA + estimación AI.
FRASES_ATMOSFERA_ES_EN = [
    ("cortina de lluvia fina", "fine rain curtain"),
    ("bruma suave de tarde", "soft afternoon mist"),
    ("reflejos cálidos en el pavimento mojado", "warm reflections on wet pavement"),
    ("reflejos calidos en el pavimento mojado", "warm reflections on wet pavement"),
    ("reflejos acuarelados en el suelo húmedo", "watercolor reflections on the damp ground"),
    ("reflejos acuarelados en el suelo humedo", "watercolor reflections on the damp ground"),
    ("atmósfera nostálgica de recuerdo", "nostalgic memory atmosphere"),
    ("atmosfera nostalgica de recuerdo", "nostalgic memory atmosphere"),
    ("luz suave envolvente", "soft enveloping light"),
    ("calma nocturna", "nocturnal calm"),
    ("polvo fino apenas visible", "barely visible fine dust"),
    ("penumbra quieta", "quiet gloom"),
    ("tensión creciente", "rising tension"),
    ("tension creciente", "rising tension"),
    ("oscuridad sobrecogedora", "overwhelming darkness"),
    ("luz doméstica cálida", "warm domestic light"),
    ("luz domestica calida", "warm domestic light"),
    ("venas de energía azul", "blue energy veins"),
    ("venas de energia azul", "blue energy veins"),
    ("luminiscencia azul recorriendo el cableado", "blue luminescence running along the wiring"),
    ("antes de que el cuarto tiemble", "before the room trembles"),
    ("destello súbito del monitor", "sudden monitor flash"),
    ("destello subito del monitor", "sudden monitor flash"),
    ("haz azul de los monitores", "blue monitor beam"),
    ("lluvia fina", "fine rain"),
    ("pavimento mojado", "wet pavement"),
    ("suelo húmedo", "damp ground"),
    ("suelo humedo", "damp ground"),
    ("noche fresca", "cool night"),
    ("noche despejada", "clear night"),
]
PALABRAS_ATMOSFERA_ES_EN = {
    "lluvia": "rain", "bruma": "mist", "niebla": "fog", "reflejos": "reflections",
    "cálidos": "warm", "calidos": "warm", "cálido": "warm", "calido": "warm",
    "fresca": "cool", "fresco": "cool", "suave": "soft", "fina": "fine", "fino": "fine",
    "nostálgica": "nostalgic", "nostalgica": "nostalgic", "recuerdo": "memory",
    "envolvente": "enveloping", "mojado": "wet", "mojada": "wet", "húmedo": "damp",
    "humedo": "damp", "húmeda": "damp", "humeda": "damp", "tarde": "afternoon",
    "noche": "night", "mañana": "morning", "manana": "morning", "madrugada": "pre-dawn",
    "polvo": "dust", "chispas": "sparks", "penumbra": "gloom", "calma": "calm",
    "tensión": "tension", "tension": "tension", "oscuridad": "darkness",
    "hologramas": "holograms", "pantalla": "screen", "monitores": "monitors",
    "doméstica": "domestic", "domestica": "domestic", "energía": "energy", "energia": "energy",
    "azul": "blue", "cian": "cyan", "ámbar": "amber", "ambar": "amber",
    "violeta": "violet", "dorado": "golden", "pizarra": "slate",
}
COLORES_ES_EN = {
    "azul pizarra suave": "soft slate blue",
    "azul pizarra": "slate blue",
    "ámbar dorado": "golden amber",
    "ambar dorado": "golden amber",
    "ámbar suave": "soft amber",
    "ambar suave": "soft amber",
    "ámbar cálido": "warm amber",
    "ambar calido": "warm amber",
    "ámbar urbano": "urban amber",
    "blanco cálido": "warm white",
    "blanco calido": "warm white",
    "blanco hueso": "off-white",
    "azul cian brillante": "bright cyan blue",
    "azul neón luminoso": "luminous neon blue",
    "azul neon luminoso": "luminous neon blue",
    "azul eléctrico": "electric blue",
    "azul electrico": "electric blue",
    "azul índigo tenue": "dim indigo",
    "azul indigo tenue": "dim indigo",
    "gris antracita": "anthracite gray",
    "gris cálido": "warm gray",
    "gris calido": "warm gray",
    "crema grisáceo cálido": "warm grayish cream",
    "crema grisaceo calido": "warm grayish cream",
    "roble miel cálido": "warm honey oak",
    "roble miel calido": "warm honey oak",
    "nogal medio": "medium walnut",
    "acero negro": "black steel",
    "terracota cálido": "warm terracotta",
    "terracota calido": "warm terracotta",
    "madera miel": "honey wood",
    "violeta intenso": "intense violet",
    "dorado cálido matinal": "warm morning gold",
}

FRASE_ANCLA_FIJA = (
    "De la ancla de escena copia solo el acabado de pintura de los materiales "
    "del entorno, la iluminación y el clima de esta escena. El tamaño de los "
    "personajes, la forma del set y el ángulo de la cámara salen únicamente "
    "del molde (Imagen 1). No copies poses ni encuadre de esta ancla. "
    "El vestuario manda por las hojas + la descripción en palabras."
)

PROHIBIDOS_URBANO_INTERIOR = re.compile(
    r"\b(foliage|moss|trees?|lush|vegetation|helechos?|musgo|árboles?|arboles?)\b",
    re.I,
)


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _strip_hex(s: str) -> tuple[str, list[str]]:
    found = re.findall(r"#[0-9A-Fa-f]{3,8}", s or "")
    clean = re.sub(r"\s*\(#[0-9A-Fa-f]{3,8}\)", "", s or "")
    clean = re.sub(r"\s*#[0-9A-Fa-f]{3,8}\b", "", clean)
    return clean.strip(), found


def tipo_entorno(esc: dict) -> str:
    ie = (esc.get("int_ext") or "").upper()
    nombre = (esc.get("nombre") or "").lower()
    if ie == "INT":
        return "interior"
    if any(k in nombre for k in ("parque", "bosque", "jardín", "jardin")):
        return "parque"
    if ie == "EXT":
        return "urbano"
    return "FALTA"


def pick_por_escena(lista: list, num: str) -> dict | None:
    for item in lista or []:
        if str(item.get("escena")) == str(num):
            return item
    return None


def parse_glosario_formas(md: str) -> dict:
    """Parsea un .md de glosario de escenario (legado / por lugar)."""
    formas = {}
    if not md:
        return {"formas": {}, "fuente": "FALTA glosario", "count": 0}
    for m in re.finditer(r"^\- \*\*([^*]+):\*\*\s*(.+)$", md, re.M):
        key =[REDACTED]
        if key in (
            "HORA_CLIMA", "LUZ", "LLUVIA", "LUGAR", "HORA", "CLIMA", "LUZ_BASE_4a1_esc6",
            "FONDO_LEJANO", "KAEL_COPIA", "NOVIA_COPIA", "MANILLA", "ESTILO", "KAEL #5500CC",
            "MANILLA #FF77AA", "IMI",
        ):
            continue
        if key.startswith("KAEL") or key.startswith("NOVIA") or key.startswith("MANILLA") or key.startswith("IMI"):
            continue
        if key == "ESTILO":
            continue
        formas[key] = m.group(2).strip()
    return {"formas": formas, "fuente": "glosario markdown", "count": len(formas)}


def load_glosario_formas_taller(lugar_id: str) -> dict | None:
    """Lee FIJOS_TALLER/glosario_formas.json (genérico, no por experimento)."""
    if not GLOSARIO_FORMAS_TALLER.is_file():
        return None
    try:
        data = _load_json(GLOSARIO_FORMAS_TALLER)
    except Exception:
        return None
    por = (data or {}).get("por_lugar") or {}
    block = por.get(lugar_id)
    if not block:
        # tolerar id sin prefijo esc-
        for k, v in por.items():
            if k == lugar_id or k.endswith(lugar_id) or lugar_id.endswith(k):
                block = v
                break
    if not block:
        return {
            "formas": {},
            "fuente": f"FALTA — {GLOSARIO_FORMAS_TALLER.name} sin entrada para {lugar_id}",
            "count": 0,
            "path": str(GLOSARIO_FORMAS_TALLER),
        }
    formas = block.get("formas") or {}
    return {
        "formas": dict(formas),
        "fuente": f"FIJOS_TALLER/glosario_formas.json ({block.get('fuente') or lugar_id})",
        "count": len(formas),
        "path": str(GLOSARIO_FORMAS_TALLER),
    }


def mold_tiene_lamparas_ventanas(formas: dict) -> bool:
    blob = " ".join(formas.keys()) + " " + " ".join(str(v) for v in formas.values())
    return bool(re.search(
        r"VENTANA|LAMPARA|LÁMPARA|PLAFON|PLAFÓN|MONITOR|FAROLA|VITRINA|ILUMINACION|ILUMINACIÓN",
        blob, re.I,
    ))


def materiales_dos_lineas(mats: list, tipo: str, formas: dict | None = None) -> dict:
    muro_keys =[REDACTED]
    suelo_keys =[REDACTED]
    muro = suelo = None
    hex_flags = []
    for m in mats or []:
        sup = (m.get("superficie") or "").lower()
        material = m.get("material") or ""
        color = m.get("color") or ""
        textura = m.get("textura") or ""
        desgaste = m.get("desgaste") or ""
        color_words, hexes = _strip_hex(color)
        if hexes:
            hex_flags.append({"donde": "materiales_texturas.color", "superficie": m.get("superficie"), "hex": hexes, "nota": "hex en fuente 4a1; no inventado"})
        line = f"{m.get('superficie')}: {material}"
        if color_words:
            line += f", color {color_words}"
        if textura:
            tw, _ = _strip_hex(textura)
            if tw:
                line += f", {tw}"
        if tipo == "urbano" and re.search(r"mojad|lluvia|húmed|humed", desgaste, re.I):
            line += ", mojado"
        if any(k in sup for k in muro_keys) and muro is None:
            if "fachada" in sup or "pared" in sup or "muro" in sup:
                muro = line
            elif muro is None:
                muro = line
        if any(k in sup for k in suelo_keys) and suelo is None:
            suelo = line
    if muro and ("techo" in muro.lower() or "viga" in muro.lower()):
        for m in mats or []:
            sup = (m.get("superficie") or "").lower()
            if "pared" in sup or "fachada" in sup or "muro" in sup:
                color_words, hexes = _strip_hex(m.get("color") or "")
                if hexes:
                    hex_flags.append({"donde": "materiales_texturas.color", "superficie": m.get("superficie"), "hex": hexes})
                muro = f"{m.get('superficie')}: {m.get('material')}, color {color_words}".strip(", ")
                break
    for m in mats or []:
        sup = (m.get("superficie") or "").lower()
        if "acera" in sup:
            color_words, hexes = _strip_hex(m.get("color") or "")
            if hexes:
                hex_flags.append({"donde": "materiales_texturas.color", "superficie": m.get("superficie"), "hex": hexes})
            suelo = f"{m.get('superficie')}: {m.get('material')}, color {color_words}"
            if "mojad" in (m.get("desgaste") or "").lower() or "lluvia" in (m.get("desgaste") or "").lower():
                suelo += ", mojada"
            break
    gaps = []
    if not muro:
        muro = "FALTA línea muros/fondo"
        gaps.append("MATERIALES_ESCENA.linea_muros")
    if not suelo:
        suelo = "FALTA línea suelo"
        gaps.append("MATERIALES_ESCENA.linea_suelo")
    if tipo in ("urbano", "interior"):
        muro = PROHIBIDOS_URBANO_INTERIOR.sub("", muro)
        suelo = PROHIBIDOS_URBANO_INTERIOR.sub("", suelo)
        muro = re.sub(r"\s{2,}", " ", muro).strip(" ,")
        suelo = re.sub(r"\s{2,}", " ", suelo).strip(" ,")
    fuente = "4a1.materiales_texturas"
    if formas:
        g_muro = g_suelo = None
        for k, v in formas.items():
            ku = k.upper().split()[0]
            if ku in ("MURO_FACHADA", "PAREDES", "MURO") and g_muro is None:
                g_muro = f"{ku}: {v}"
            if ku in ("ACERA", "PISO") and g_suelo is None:
                g_suelo = f"{ku}: {v}"
        if g_muro:
            clean, hx = _strip_hex(g_muro)
            if hx:
                hex_flags.append({"donde": "glosario_formas", "hex": hx, "nota": "hex en glosario; flag"})
            muro = clean
            fuente = "glosario_formas (+4a1 materiales como respaldo)"
        if g_suelo:
            clean, hx = _strip_hex(g_suelo)
            if hx:
                hex_flags.append({"donde": "glosario_formas", "hex": hx, "nota": "hex en glosario; flag"})
            suelo = clean
            fuente = "glosario_formas (+4a1 materiales como respaldo)"
        gaps = [g for g in gaps if "MATERIALES" not in g]
        if not muro:
            gaps.append("MATERIALES_ESCENA.linea_muros")
        if not suelo:
            gaps.append("MATERIALES_ESCENA.linea_suelo")
    return {
        "lineas": [muro, suelo],
        "texto": f"{muro}. {suelo}.",
        "hex_en_fuente": hex_flags,
        "gaps": gaps,
        "fuente": fuente,
    }


def estilo_fondo_ingles(mats: list, tipo: str) -> dict:
    bits = []
    for m in mats or []:
        material = (m.get("material") or "").lower()
        superficie = (m.get("superficie") or "").lower()
        if any(k in superficie for k in ("pared", "muro", "fachada", "concreto")) or "concreto" in material or "ladrillo" in material:
            if "concreto" in material or "concreto" in superficie:
                bits.append("weathered concrete")
            if "ladrillo" in material:
                bits.append("brick facade")
            if "estuco" in material:
                bits.append("painted plaster walls")
        if any(k in superficie for k in ("piso", "suelo", "acera", "calzada")):
            if tipo == "urbano" and "asfalto" in material:
                bits.append("wet asphalt")
            if tipo == "urbano" and ("loseta" in material or "concreto" in material or "adoquín" in material or "adoquin" in material):
                bits.append("wet stone pavement")
            if "madera" in material or "laminada" in material:
                bits.append("wood laminate floor")
        if tipo == "interior" and "estuco" in material:
            bits.append("painted plaster walls")
        if tipo == "interior" and "concreto" in material and "techo" in superficie:
            bits.append("painted concrete ceiling")
    if tipo == "urbano":
        bits.append("subtle damp patina")
    if tipo == "interior":
        bits = [b for b in bits if b not in ("wet asphalt", "wet stone pavement", "brick facade", "subtle damp patina")]
        if "weathered concrete" in bits and "painted plaster walls" in bits:
            bits = [b for b in bits if b != "weathered concrete"]
    seen, ordered = set(), []
    for b in bits:
        if b not in seen:
            seen.add(b)
            ordered.append(b)
    derived = ", ".join(ordered) if ordered else "FALTA"
    if tipo in ("urbano", "interior"):
        derived = PROHIBIDOS_URBANO_INTERIOR.sub("", derived)
        derived = re.sub(r"\s{2,}", " ", derived).strip(" ,")
        if not derived:
            derived = "hand-painted architectural surfaces"
    return {
        "valor": derived,
        "fuente": "derivado_script_desde_4a1_materiales",
        "nota": "4a1 no produce ESTILO_FONDO_INGLES. Script deriva palabras EN de materiales. No se inventa atmósfera/paleta.",
        "filtro_anti_moss_aplicado": tipo in ("urbano", "interior"),
    }


def _traducir_es_en_determinista(texto: str) -> tuple[str, float, list[str]]:
    """Aplica diccionario fijo ES→EN. Devuelve (en, cobertura_0_1, tokens_sin_traducir)."""
    if not texto or not str(texto).strip():
        return "", 0.0, []
    s = str(texto).strip()
    original = s
    # frases largas primero
    for es, en in sorted(FRASES_ATMOSFERA_ES_EN, key=lambda x: -len(x[0])):
        if es.lower() in s.lower():
            # case-insensitive replace
            s = re.sub(re.escape(es), en, s, flags=re.I)
    for es, en in sorted(COLORES_ES_EN.items(), key=lambda x: -len(x[0])):
        if es.lower() in s.lower():
            s = re.sub(re.escape(es), en, s, flags=re.I)
    # palabras sueltas (límites de palabra unicode-ish)
    for es, en in sorted(PALABRAS_ATMOSFERA_ES_EN.items(), key=lambda x: -len(x[0])):
        s = re.sub(rf"\b{re.escape(es)}\b", en, s, flags=re.I)
    # limpiar conectores ES frecuentes que quedaron
    s = re.sub(r"\b(de|del|la|el|los|las|y|en|con|por|un|una|al|a)\b", " ", s, flags=re.I)
    s = re.sub(r"[,:;]+", ",", s)
    s = re.sub(r"\s{2,}", " ", s).strip(" ,.")
    # cobertura: fracción de palabras del original que ya no son «claramente ES»
    tokens =[REDACTED]
    # palabras EN conocidas del diccionario (valores) + stopwords EN
    en_known = {v.lower() for v in PALABRAS_ATMOSFERA_ES_EN.values()}
    en_known |= {v.lower() for v in COLORES_ES_EN.values()}
    for _es, en in FRASES_ATMOSFERA_ES_EN:
        for w in re.findall(r"[A-Za-z]{3,}", en):
            en_known.add(w.lower())
    en_known |= {
        "warm", "soft", "fine", "cool", "damp", "wet", "rain", "mist", "fog", "night",
        "afternoon", "morning", "blue", "cyan", "amber", "golden", "slate", "gray",
        "grey", "white", "darkness", "tension", "sparks", "dust", "calm", "energy",
        "veins", "reflections", "pavement", "ground", "curtain", "memory", "nostalgic",
        "enveloping", "domestic", "overwhelming", "rising", "quiet", "gloom", "neon",
        "luminous", "monitor", "beam", "flash", "sudden", "room", "trembles", "before",
        "along", "wiring", "running", "luminescence", "honey", "oak", "cream", "walnut",
        "steel", "terracotta", "wood", "brick", "concrete", "plaster",
    }
    sospechosas = []
    for w in tokens:
        wl = w.lower()
        if wl in en_known:
            continue
        # acento → ES; terminaciones verbales/sustantivas ES comunes
        if re.search(r"[áéíóúñ]", wl) or re.search(
            r"(ción|sion|iendo|ando|mente|idad|oso|osa|able|ibles?|aje)$", wl
        ):
            sospechosas.append(w)
            continue
        # si la palabra sigue siendo una clave ES del diccionario, quedó sin traducir
        if wl in PALABRAS_ATMOSFERA_ES_EN or wl in {k.split()[0] for k in COLORES_ES_EN}:
            sospechosas.append(w)
    total_words = max(1, len(re.findall(r"[A-Za-záéíóúñÁÉÍÓÚÑ]{3,}", original)))
    # cobertura = 1 - restos/total (estricto con restos)
    cov = max(0.0, min(1.0, 1.0 - (len(sospechosas) / total_words)))
    if sospechosas:
        # cualquier resto ES claro → no dar por buena la frase
        cov = min(cov, 0.49)
    return s, cov, sospechosas


def _paleta_desde_4a1(luz: dict | None, mats: list | None) -> tuple[str | None, str]:
    """Deriva paleta EN corta desde colores de luces + materiales 4a1 (determinista)."""
    bits = []
    for fu in (luz or {}).get("fuentes") or []:
        if fu.get("encendida") is False:
            continue
        color = fu.get("color") or ""
        clean, _ = _strip_hex(color)
        if not clean:
            continue
        en, cov, _ = _traducir_es_en_determinista(clean)
        if en and cov >= 0.5:
            bits.append(en)
        elif clean:
            # si el color ya trae palabras EN o hex-only name remnants
            bits.append(en or clean)
    for m in mats or []:
        color = m.get("color") or ""
        clean, _ = _strip_hex(color)
        if not clean:
            continue
        en, cov, _ = _traducir_es_en_determinista(clean)
        piece = en if en and cov >= 0.45 else None
        if piece and piece not in bits:
            bits.append(piece)
    # dedupe preserving order
    seen, ordered = set(), []
    for b in bits:
        bl = b.lower().strip()
        if bl and bl not in seen:
            seen.add(bl)
            ordered.append(b.strip())
    if not ordered:
        return None, "FALTA — 4a1 sin colores de luz/material aprovechables"
    # limitar a 5 para prompt
    return ", ".join(ordered[:5]), "derivado_determinista_desde_4a1_luces+materiales"


def atmosfera_y_paleta(
    amb: dict | None,
    tipo: str,
    glosario_text: str,
    luz: dict | None = None,
    mats: list | None = None,
) -> dict:
    """Deriva ATMOSFERA/PALETA EN desde campos 4a1 (determinista). Sin AI. Sin inventar.

    Si la cobertura del diccionario ES→EN es baja → deja FALTA y adjunta estimación de costo AI.
    """
    atm_es = (amb or {}).get("atmosfera")
    out = {
        "ATMOSFERA_INGLES": {
            "valor": "FALTA",
            "insumo_4a1_ES": atm_es,
            "fuente": "FALTA — 4a1 no da inglés",
        },
        "PALETA_ESCENA_INGLES": {
            "valor": "FALTA",
            "fuente": "FALTA — 4a1 no produce paleta EN",
        },
        "ai_traduccion": {
            "llamada_hecha": False,
            "usd": 0,
            "nota": "US$0 aquí. Si hace falta AI, ver estimacion_por_escena (no se llama).",
        },
    }

    # 1) Determinista desde atmósfera ES de 4a1
    if atm_es:
        en, cov, left = _traducir_es_en_determinista(atm_es)
        out["ATMOSFERA_INGLES"]["cobertura_diccionario"] = round(cov, 3)
        out["ATMOSFERA_INGLES"]["restos_sin_traducir"] = left
        if tipo in ("urbano", "interior") and en:
            en = PROHIBIDOS_URBANO_INTERIOR.sub("", en)
            en = re.sub(r"\s{2,}", " ", en).strip(" ,")
        if en and cov >= 0.55 and len(en) >= 8:
            out["ATMOSFERA_INGLES"]["valor"] = en
            out["ATMOSFERA_INGLES"]["fuente"] = (
                "derivado_determinista_desde_4a1.ambiente_por_escena.atmosfera"
            )
        else:
            out["ATMOSFERA_INGLES"]["valor"] = "FALTA"
            out["ATMOSFERA_INGLES"]["fuente"] = (
                "FALTA — diccionario ES→EN no cubre bastante el texto 4a1; "
                "no se inventa ni se llama AI"
            )
            out["ATMOSFERA_INGLES"]["estimacion_ai_por_escena"] = {
                "para": "traducir atmosfera ES → frase EN corta de mood (image prompt)",
                "tokens_in_est": 120,
                "tokens_out_est": 40,
                "modelo_ref": "LLM barato tipo mini (p.ej. gpt-4o-mini / equivalente)",
                "usd_est_por_escena": 0.0002,
                "usd_est_nota": (
                    "Orden de magnitud ~US$0.0001–0.0004/escena a tarifas mini 2026; "
                    "confirmar con Ricardo antes de cablear. Cero llamadas hechas."
                ),
            }
            out["ai_traduccion"]["estimacion_por_escena_usd"] = 0.0002

    # 2) Paleta desde luces + materiales 4a1
    pal, fuente_pal = _paleta_desde_4a1(luz, mats)
    if pal:
        if tipo in ("urbano", "interior"):
            pal_f = PROHIBIDOS_URBANO_INTERIOR.sub("", pal)
            pal_f = re.sub(r"\bgreens?\b", "", pal_f, flags=re.I)
            pal_f = re.sub(r"\s{2,}", " ", pal_f).strip(" ,")
            pal = pal_f or pal
        out["PALETA_ESCENA_INGLES"]["valor"] = pal
        out["PALETA_ESCENA_INGLES"]["fuente"] = fuente_pal
    else:
        out["PALETA_ESCENA_INGLES"]["fuente"] = fuente_pal
        out["PALETA_ESCENA_INGLES"]["estimacion_ai_por_escena"] = {
            "para": "comprimir colores 4a1 ES → paleta EN de 3–6 palabras",
            "usd_est_por_escena": 0.00015,
            "nota": "Solo si faltan colores en 4a1 o el diccionario no alcanza; no llamado.",
        }

    # 3) Legado: si aún FALTA y hay glosario ESTILO EN, intentar filtrar (no inventar)
    if out["ATMOSFERA_INGLES"]["valor"] == "FALTA" and glosario_text:
        m_atm = re.search(r"visible soft brush texture,\s*([^.]*)\.\s*Lighting:", glosario_text)
        if m_atm:
            atm = m_atm.group(1).strip()
            out["ATMOSFERA_INGLES"]["valor_desde_glosario_crudo"] = atm
            if not (tipo == "interior" and re.search(r"rain|moss|foliage|greens", atm, re.I)):
                if tipo in ("urbano", "interior") and PROHIBIDOS_URBANO_INTERIOR.search(atm):
                    atm = PROHIBIDOS_URBANO_INTERIOR.sub("", atm)
                    atm = re.sub(r"\s{2,}", " ", atm).strip(" ,")
                if atm:
                    out["ATMOSFERA_INGLES"]["valor"] = atm
                    out["ATMOSFERA_INGLES"]["fuente"] = "glosario ESTILO (filtrado); respaldo si 4a1 no tradujo"
    if out["PALETA_ESCENA_INGLES"]["valor"] == "FALTA" and glosario_text:
        m_pal = re.search(r"palette of\s+([^.]+?)\s+balanced", glosario_text, re.I)
        if m_pal:
            pal = m_pal.group(1).strip()
            out["PALETA_ESCENA_INGLES"]["valor_glosario_crudo"] = pal
            if not (tipo == "interior" and re.search(r"green|moss|misty slate|foliage", pal, re.I)):
                if tipo in ("urbano", "interior") and (
                    PROHIBIDOS_URBANO_INTERIOR.search(pal) or re.search(r"\bgreens?\b", pal, re.I)
                ):
                    pal_f = re.sub(r"misty greens and grays", "misty slate grays", pal, flags=re.I)
                    pal_f = PROHIBIDOS_URBANO_INTERIOR.sub("", pal_f)
                    pal_f = re.sub(r"\s{2,}", " ", pal_f).strip(" ,")
                    out["PALETA_ESCENA_INGLES"]["valor"] = pal_f or "FALTA"
                    out["PALETA_ESCENA_INGLES"]["fuente"] = "glosario ESTILO + filtro urbano"
                else:
                    out["PALETA_ESCENA_INGLES"]["valor"] = pal
                    out["PALETA_ESCENA_INGLES"]["fuente"] = "glosario ESTILO"
    return out


def clima_y_luz(luz: dict | None, amb: dict | None, mold_tiene_luces: bool) -> dict:
    gaps = []
    if not luz:
        return {
            "valor": "FALTA — no hay luz_por_escena para este número",
            "fuente": "FALTA",
            "hex_luz_en_fuente": [],
            "gaps": ["CLIMA_Y_LUZ_ESCENA"],
            "mold_luz_fuera_de_cuadro": not mold_tiene_luces,
        }
    hora = luz.get("hora") or (amb or {}).get("hora") or "FALTA hora"
    clima = luz.get("clima") or (amb or {}).get("clima") or "FALTA clima"
    if str(clima).lower() in ("desconocido", "unknown", ""):
        clima2 = (amb or {}).get("clima")
        if clima2 and str(clima2).lower() not in ("desconocido",):
            clima = clima2
        else:
            clima = f"{clima} (4a1 marca desconocido — no inventar)"
            gaps.append("CLIMA (4a1 desconocido)")
    hex_luz, partes_luz = [], []
    for fu in luz.get("fuentes") or []:
        if fu.get("encendida") is False:
            continue
        color = fu.get("color") or ""
        hx = re.findall(r"#[0-9A-Fa-f]{3,8}", color)
        if hx:
            hex_luz.append({"tipo": fu.get("tipo"), "hex": hx, "nota": "hex de luz ya en 4a1"})
        partes_luz.append(f"{fu.get('tipo')}: {color}, intensidad {fu.get('intensidad')}")
    sombras = luz.get("sombras") or ""
    ambiente = luz.get("ambiente") or (amb or {}).get("atmosfera") or ""
    texto = (
        f"Hora: {hora}. Clima: {clima}. "
        f"Ambiente: {ambiente}. "
        f"Luces: {'; '.join(partes_luz)}. "
        f"Sombras: {sombras}."
    )
    if not mold_tiene_luces:
        texto += " Luz principal desde fuera de cuadro (el molde no muestra lámparas ni ventanas encendidas)."
    return {
        "valor": texto,
        "fuente": "4a1.luz_por_escena + ambiente_vivo.ambiente_por_escena",
        "hex_luz_en_fuente": hex_luz,
        "mold_luz_fuera_de_cuadro": not mold_tiene_luces,
        "gaps": gaps,
        "crudo": {
            "hora": hora, "clima": clima, "ambiente": ambiente,
            "fuentes": luz.get("fuentes"), "sombras": sombras,
        },
    }


def extract_desc_ropa(sidecar: dict) -> dict:
    """Lee DESC_ROPA desde sidecar estándar (desc_ropa.json) o legado (texto What the sheet says)."""
    # Estándar programa: campos dedicados
    if sidecar.get("schema") == DESC_ROPA_SCHEMA or sidecar.get("DESC_ROPA"):
        desc = (sidecar.get("DESC_ROPA") or "").strip()
        return {
            "DESC_ROPA": desc or "FALTA DESC_ROPA en sidecar",
            "nombre_en_sheet": sidecar.get("nombre"),
            "version": sidecar.get("version"),
            "fuente": sidecar.get("fuente") or ("sidecar.DESC_ROPA" if desc else "FALTA"),
            "schema": sidecar.get("schema") or DESC_ROPA_SCHEMA,
        }
    texto = sidecar.get("texto") or ""
    m = re.search(
        r"What the sheet says about this version[^:]*:\s*(.+?)\nNever changes",
        texto, re.S,
    )
    desc = m.group(1).strip() if m else None
    mv = re.search(r"Character: «([^»]+)» — version «([^»]+)»", texto)
    return {
        "DESC_ROPA": desc or "FALTA DESC_ROPA en sidecar",
        "nombre_en_sheet": mv.group(1) if mv else None,
        "version": mv.group(2) if mv else None,
        "fuente": "sidecar.texto (bloque What the sheet says…)" if desc else "FALTA",
    }


def build_desc_ropa_doc(
    *,
    nombre: str,
    version: str,
    desc_ropa: str,
    sheet_path: str | None = None,
    fuente: str,
    extra: dict | None = None,
) -> dict:
    doc = {
        "schema": DESC_ROPA_SCHEMA,
        "nombre": nombre,
        "version": version,
        "sheet_path": sheet_path,
        "DESC_ROPA": desc_ropa.strip(),
        "fuente": fuente,
    }
    if extra:
        for k, v in extra.items():
            if k not in doc and v is not None:
                doc[k] = v
    return doc


def upsert_desc_ropa_sidecar(
    sheet_or_dir: Path,
    *,
    nombre: str,
    version: str,
    desc_ropa: str,
    fuente: str,
    sheet_path: str | None = None,
    extra: dict | None = None,
) -> Path:
    """Crea/actualiza desc_ropa.json al lado de la hoja (genérico, cualquier canal/personaje)."""
    p = Path(sheet_or_dir)
    if p.is_dir():
        out = p / DESC_ROPA_FILENAME
        sheet = sheet_path
    elif p.name == DESC_ROPA_FILENAME:
        out = p
        sheet = sheet_path
    else:
        out = p.parent / DESC_ROPA_FILENAME
        sheet = sheet_path or str(p)
    doc = build_desc_ropa_doc(
        nombre=nombre,
        version=version,
        desc_ropa=desc_ropa,
        sheet_path=sheet,
        fuente=fuente,
        extra=extra,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def load_personajes_from_paths(specs: list[dict]) -> list:
    out = []
    for p in specs:
        item = {
            "nombre": p.get("nombre") or "FALTA",
            "version": p.get("version_esperada") or "FALTA",
            "sheet_path": p.get("sheet_path"),
            "sidecar_path": p.get("sidecar"),
            "DESC_ROPA": "FALTA",
            "gaps": [],
        }
        sc = Path(p["sidecar"]) if p.get("sidecar") else None
        if not sc or not sc.is_file():
            item["gaps"].append("sidecar ausente")
            item["DESC_ROPA"] = "FALTA — sidecar ausente"
            out.append(item)
            continue
        data = _load_json(sc)
        ext = extract_desc_ropa(data)
        if ext.get("nombre_en_sheet"):
            item["nombre"] = ext["nombre_en_sheet"]
        item["version"] = ext["version"] or p.get("version_esperada") or "FALTA"
        item["DESC_ROPA"] = ext["DESC_ROPA"]
        item["DESC_ROPA_fuente"] = ext["fuente"]
        # sheet_path: sidecar estándar puede traer path preferido
        if data.get("sheet_path") and Path(str(data["sheet_path"])).is_file():
            item["sheet_path"] = str(data["sheet_path"])
        elif data.get("sheet_path"):
            cand = sc.parent / Path(str(data["sheet_path"])).name
            if cand.is_file():
                item["sheet_path"] = str(cand)
        if not item.get("sheet_path"):
            item["sheet_path"] = p.get("sheet_path")
        if str(item["DESC_ROPA"]).startswith("FALTA"):
            item["gaps"].append("DESC_ROPA")
        out.append(item)
    return out


def discover_sidecars(canal: str) -> list[dict]:
    """Busca sidecars de ropa/hoja en biblioteca del canal. Prefiere desc_ropa.json.

    Layout biblioteca: personajes/<id>/<version>/refs/{desc_ropa.json,frente.json,frente.png}.
    También acepta legado *_frente.json en un solo directorio. No inventa texto.
    """
    specs = []
    roots = [
        TRABAJO.parent / "biblioteca" / canal / "personajes",
        Path("/opt/myia-taller-n8n/trabajo/biblioteca") / canal / "personajes",
    ]
    for root in roots:
        if not root.is_dir():
            continue
        seen_dirs = set()
        # 1) desc_ropa.json estándar
        for sc in sorted(root.rglob(DESC_ROPA_FILENAME)):
            refs = sc.parent
            seen_dirs.add(refs)
            data = {}
            try:
                data = _load_json(sc)
            except Exception:
                pass
            sheet = data.get("sheet_path")
            if sheet and not Path(sheet).is_file():
                # relativo al refs/
                cand = refs / Path(sheet).name
                sheet = str(cand) if cand.is_file() else sheet
            if not sheet:
                for name in (
                    "03_novia_frente_v2_ricardo.png",
                    "03_novia_frente_v2_ricardo.jpg",
                    "frente.png",
                    "frente.jpg",
                ):
                    if (refs / name).is_file():
                        sheet = str(refs / name)
                        break
            # nombre/version desde path si faltan
            try:
                version_id = refs.parent.name
                personaje_id = refs.parent.parent.name
            except Exception:
                personaje_id, version_id = sc.stem, ""
            specs.append({
                "nombre": data.get("nombre") or personaje_id,
                "version_esperada": data.get("version") or version_id,
                "sidecar": str(sc),
                "sheet_path": sheet,
            })
        # 2) frente.json legado en dirs sin desc_ropa
        for sc in sorted(root.rglob("frente.json")):
            if sc.parent in seen_dirs:
                continue
            png = sc.with_suffix(".png")
            try:
                version_id = sc.parent.parent.name
                personaje_id = sc.parent.parent.parent.name
            except Exception:
                personaje_id, version_id = "frente", ""
            specs.append({
                "nombre": personaje_id,
                "version_esperada": version_id,
                "sidecar": str(sc),
                "sheet_path": str(png) if png.is_file() else None,
            })
        # 3) legado plano *_frente.json
        for sc in sorted(root.rglob("*_frente.json")):
            if sc.name == "frente.json":
                continue
            if sc.parent in seen_dirs:
                continue
            png = sc.with_suffix(".png")
            specs.append({
                "nombre": sc.stem,
                "sidecar": str(sc),
                "sheet_path": str(png) if png.is_file() else None,
            })
        if specs:
            break
    return specs


def find_glosario(lugar_dir: Path, canal: str, lugar_id: str) -> Path | None:
    """Prioriza glosario_formas.json del taller; luego .md por lugar (legado)."""
    if GLOSARIO_FORMAS_TALLER.is_file():
        # Señal: armar_doc usará load_glosario_formas_taller; devolvemos el JSON
        # solo si el lugar está (o para que el path quede referenciado).
        return GLOSARIO_FORMAS_TALLER
    candidates = [
        lugar_dir / "GLOSARIO_ESCENARIO.md",
        lugar_dir / "glosario.md",
        lugar_dir.parent.parent.parent / "glosarios" / f"{lugar_id}.md",
        CAJAS / "FIJOS_TALLER" / "escena" / "glosarios" / f"{lugar_id}.md",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def find_ancla(lugar_dir: Path, lugar_id: str) -> str | None:
    for c in (
        lugar_dir / "ancla.png",
        lugar_dir / "ANCLA_ESCENA.png",
        CAJAS / "FIJOS_TALLER" / "escena" / "anclas" / f"{lugar_id}.png",
    ):
        if c.is_file():
            return str(c)
    return None


def carpeta_capitulo(canal: str, capitulo: str) -> Path | None:
    base = TRABAJO / canal
    if not base.is_dir():
        return None
    if str(capitulo).isdigit():
        ds = sorted(base.glob(f"cap{int(capitulo):02d}_*"))
    else:
        ds = sorted(base.glob(f"cap*_{capitulo}"))
    return ds[0] if ds else None


def armar_doc(
    esc: dict,
    path_4a1: Path,
    escena_num: str | None,
    glosario_path: Path | None,
    ancla: str | None,
    personajes_specs: list[dict],
    mold_override: bool | None = None,
) -> dict:
    fuente = esc.get("fuente")
    tipo = tipo_entorno(esc)
    glos_text = ""
    glos_formas = {"formas": {}, "fuente": "FALTA glosario", "count": 0, "path": None}
    lugar_id_tmp = esc.get("id") or ""
    # Preferir JSON taller genérico
    if glosario_path and glosario_path.is_file() and glosario_path.suffix.lower() == ".json":
        loaded = load_glosario_formas_taller(lugar_id_tmp)
        if loaded:
            glos_formas = loaded
        # .md local opcional solo para ESTILO legado (atm/paleta fallback)
        md_local = Path(glosario_path).parent / "GLOSARIO_ESCENARIO.md"
        # también buscar al lado del escenario
        for cand in (
            path_4a1.parent / "GLOSARIO_ESCENARIO.md",
            path_4a1.parent / "glosario.md",
        ):
            if cand.is_file():
                glos_text = cand.read_text(encoding="utf-8")
                break
    elif glosario_path and glosario_path.is_file():
        glos_text = glosario_path.read_text(encoding="utf-8")
        glos_formas = parse_glosario_formas(glos_text)
        glos_formas["path"] = str(glosario_path)
    else:
        loaded = load_glosario_formas_taller(lugar_id_tmp)
        if loaded:
            glos_formas = loaded
    if not glos_formas.get("formas"):
        # Respaldo: .md al lado del escenario / candidatos clásicos
        md_candidates = [
            path_4a1.parent / "GLOSARIO_ESCENARIO.md",
            path_4a1.parent / "glosario.md",
            path_4a1.parent.parent.parent / "glosarios" / f"{lugar_id_tmp}.md",
            CAJAS / "FIJOS_TALLER" / "escena" / "glosarios" / f"{lugar_id_tmp}.md",
        ]
        for cand in md_candidates:
            if cand.is_file():
                glos_text = glos_text or cand.read_text(encoding="utf-8")
                parsed = parse_glosario_formas(glos_text)
                if parsed.get("formas"):
                    glos_formas = parsed
                    glos_formas["path"] = str(cand)
                    break
    if not glos_formas.get("formas"):
        glos_formas["fuente"] = glos_formas.get("fuente") or "FALTA — no se parsearon formas (o archivo ausente)"
        if not glos_formas.get("path"):
            glos_formas["path"] = str(glosario_path) if glosario_path else None
    mold_luces = mold_tiene_lamparas_ventanas(glos_formas["formas"])
    if mold_override is not None:
        mold_luces = mold_override

    nums = []
    for x in (esc.get("luz_por_escena") or []):
        if x.get("escena") is not None and str(x.get("escena")) not in nums:
            nums.append(str(x.get("escena")))
    if not nums:
        for x in ((esc.get("ambiente_vivo") or {}).get("ambiente_por_escena") or []):
            if x.get("escena") is not None and str(x.get("escena")) not in nums:
                nums.append(str(x.get("escena")))
    if escena_num:
        primary = str(escena_num)
        if primary not in nums:
            nums = [primary] + nums
    else:
        primary = nums[0] if nums else "FALTA"

    mats = materiales_dos_lineas(esc.get("materiales_texturas") or [], tipo, glos_formas.get("formas"))
    estilo = estilo_fondo_ingles(esc.get("materiales_texturas") or [], tipo)
    por_escena = {}
    for num in nums:
        luz = pick_por_escena(esc.get("luz_por_escena") or [], num)
        amb = pick_por_escena((esc.get("ambiente_vivo") or {}).get("ambiente_por_escena") or [], num)
        atmpal = atmosfera_y_paleta(
            amb, tipo, glos_text, luz=luz, mats=esc.get("materiales_texturas") or [],
        )
        clima = clima_y_luz(luz, amb, mold_luces)
        por_escena[num] = {"ATMOSFERA_INGLES": atmpal["ATMOSFERA_INGLES"], "PALETA_ESCENA_INGLES": atmpal["PALETA_ESCENA_INGLES"], "CLIMA_Y_LUZ_ESCENA": clima}

    prim = por_escena.get(primary) or {
        "ATMOSFERA_INGLES": {"valor": "FALTA", "fuente": "FALTA"},
        "PALETA_ESCENA_INGLES": {"valor": "FALTA", "fuente": "FALTA"},
        "CLIMA_Y_LUZ_ESCENA": {"valor": "FALTA", "fuente": "FALTA", "gaps": ["CLIMA_Y_LUZ_ESCENA"]},
    }
    personajes = load_personajes_from_paths(personajes_specs) if personajes_specs else []

    ancla_obj = {
        "path": ancla if ancla else "SIN_ANCLA",
        "frase_que_copia": FRASE_ANCLA_FIJA,
        "fuente": "aprobación humana / archivo en disco" if ancla else "SIN_ANCLA (4a1/4a5 no son ancla de escena)",
    }
    if ancla and not Path(ancla).is_file():
        ancla_obj["gaps"] = ["ANCLA_ESCENA path no existe en disco"]
        ancla_obj["path_estado"] = "FALTA archivo"
    elif ancla:
        ancla_obj["path_estado"] = "existe"

    gaps = list(mats.get("gaps") or [])
    for g in (prim["CLIMA_Y_LUZ_ESCENA"].get("gaps") or []):
        gaps.append(g)
    if prim["ATMOSFERA_INGLES"].get("valor") == "FALTA":
        gaps.append("ATMOSFERA_INGLES")
    if prim["PALETA_ESCENA_INGLES"].get("valor") == "FALTA":
        gaps.append("PALETA_ESCENA_INGLES")
    if estilo.get("valor") == "FALTA":
        gaps.append("ESTILO_FONDO_INGLES")
    if not glos_formas["formas"]:
        gaps.append("GLOSARIO_FORMAS")
    if ancla_obj["path"] == "SIN_ANCLA":
        gaps.append("ANCLA_ESCENA=SIN_ANCLA")
    if not personajes:
        gaps.append("PERSONAJES (sin sidecars en biblioteca)")
    for p in personajes:
        gaps.extend([f"PERSONAJES.{p['nombre']}.{x}" for x in p.get("gaps") or []])

    doc = {
        "esquema": "Nivel 2 escena",
        "ID_ESCENA": {
            "label": f"ESCENA {primary}" if primary != "FALTA" else (esc.get("nombre") or esc.get("id")),
            "numero": primary,
            "numeros_disponibles": nums,
            "lugar_id": esc.get("id"),
            "nombre": esc.get("nombre"),
            "fuente": "4a1.id + número escena pedido",
        },
        "TIPO_ENTORNO": {
            "valor": tipo,
            "int_ext_4a1": esc.get("int_ext"),
            "fuente": "4a1.int_ext (+nombre)",
        },
        "ESTILO_FONDO_INGLES": estilo,
        "ATMOSFERA_INGLES": prim["ATMOSFERA_INGLES"],
        "PALETA_ESCENA_INGLES": prim["PALETA_ESCENA_INGLES"],
        "CLIMA_Y_LUZ_ESCENA": prim["CLIMA_Y_LUZ_ESCENA"],
        "CLIMA_Y_LUZ_POR_ESCENA": {k: v["CLIMA_Y_LUZ_ESCENA"] for k, v in por_escena.items()},
        "MATERIALES_ESCENA": mats,
        "GLOSARIO_FORMAS": glos_formas,
        "ANCLA_ESCENA": ancla_obj,
        "PERSONAJES": personajes,
        "meta": {
            "path_4a1": str(path_4a1),
            "fuente_archivo": fuente,
            "campos_top_4a1": sorted(esc.keys()),
            "filtro_estilo_urbano_interior": tipo in ("urbano", "interior"),
            "gaps": gaps,
            "usd": 0,
            "ai_calls": 0,
            "esquema_ref": str(ESQUEMA) if ESQUEMA.is_file() else None,
        },
    }
    return doc



# ---------------- t440 (Ricardo): 4a1b SOLO LEE lo que entregan los módulos de origen ----------------
# 4a2 → glosario_4a2.json · 2C → resultados/vestuario_por_escena.json · 4a4 → atmosfera_4a4.json
# 4a1 → ambiente_por_escena[].atmosfera_en (corridas nuevas) · 4a5 → candidatos de ancla; ancla solo con aprobación humana.
# Si algo falta, el gap dice QUÉ MÓDULO no lo entregó. No traduce, no inventa, no llama IA.
_armar_doc_sin_origen = armar_doc


def _quitar_gaps(gaps, prefijos):
    return [g for g in gaps if not any(str(g).startswith(p) for p in prefijos)]


def leer_entregas_origen(doc: dict, esc: dict, path_4a1: Path) -> dict:
    d = Path(path_4a1).parent
    D = d.parent.parent.parent
    ide = doc.get("ID_ESCENA") or {}
    nums = [str(n) for n in (ide.get("numeros_disponibles") or [ide.get("numero")]) if n]
    meta = doc.setdefault("meta", {})
    gaps = list(meta.get("gaps") or [])
    origen = {}
    # --- atmósfera EN: 4a1 (campo nuevo) → 4a4 ---
    gaps = _quitar_gaps(gaps, ("ATMOSFERA_INGLES", "ESTILO_FONDO_INGLES"))
    atm = doc.setdefault("ATMOSFERA_INGLES", {})
    a41 = [x.get("atmosfera_en") for x in ((esc.get("ambiente_vivo") or {}).get("ambiente_por_escena") or [])
           if str(x.get("escena")) in nums and x.get("atmosfera_en")]
    f44 = d / "atmosfera_4a4.json"
    a44 = _load_json(f44) if f44.is_file() else None
    if a41:
        atm.update(valor=" | ".join(a41), fuente="4a1.ambiente_vivo.ambiente_por_escena.atmosfera_en")
    elif a44 and a44.get("atmosfera_base_en"):
        atm.update(valor=a44["atmosfera_base_en"], fuente=f"4a4 → {f44.name} (frases de luz/clima/color del prompt base)",
                   cambios_por_escena_en={n: [y["atmosfera_en"] for y in (a44.get("por_escena") or {}).get(n, [])] for n in nums
                                          if (a44.get("por_escena") or {}).get(n)})
    else:
        atm["valor"] = "FALTA"
        gaps.append("ATMOSFERA_INGLES — no la entregó 4a1 (atmosfera_en) ni 4a4 (atmosfera_4a4.json)")
    origen["ATMOSFERA_INGLES"] = atm.get("fuente")
    est = doc.setdefault("ESTILO_FONDO_INGLES", {})
    if str(est.get("valor", "FALTA")).startswith("FALTA"):
        if a44 and a44.get("estilo_en"):
            est.update(valor=a44["estilo_en"], fuente=f"4a4 → {f44.name} (estilo_en)")
        else:
            gaps.append("ESTILO_FONDO_INGLES — no lo entregó 4a4 (atmosfera_4a4.json.estilo_en)")
    # --- glosario + materiales de fondo: 4a2 ---
    g42 = d / "glosario_4a2.json"
    g = _load_json(g42) if g42.is_file() else None
    glos = doc.setdefault("GLOSARIO_FORMAS", {})
    if not glos.get("formas"):
        gaps = _quitar_gaps(gaps, ("GLOSARIO_FORMAS",))
        if g and g.get("formas"):
            glos.update(formas=g["formas"], count=len(g["formas"]), fuente="4a2 → glosario_4a2.json", path=str(g42))
            doc["MATERIALES_ESCENA"] = materiales_dos_lineas(esc.get("materiales_texturas") or [], tipo_entorno(esc), g["formas"])
        else:
            gaps.append("GLOSARIO_FORMAS — no lo entregó 4a2 (glosario_4a2.json)")
    mat = doc.get("MATERIALES_ESCENA") or {}
    lineas = list(mat.get("lineas") or [])
    if lineas and str(lineas[0]).startswith("FALTA") and g and g.get("materiales_fondo"):
        lineas[0] = g["materiales_fondo"]["linea"]
        mat.update(lineas=lineas, texto=f"{lineas[0]}. {lineas[1] if len(lineas) > 1 else ''}.", fuente_fondo=f"4a2 → glosario_4a2.json ({g['materiales_fondo']['origen']})")
        mat["gaps"] = [x for x in (mat.get("gaps") or []) if "muros" not in x]
    gaps = _quitar_gaps(gaps, ("MATERIALES_ESCENA.linea_muros",))
    if lineas and str(lineas[0]).startswith("FALTA"):
        gaps.append("MATERIALES_ESCENA.linea_muros — no la entregó 4a1 (materiales) ni 4a2 (materiales_fondo)")
    # --- personajes/vestuario: 2C (solo los que aparecen en estas escenas) ---
    gaps = _quitar_gaps(gaps, ("PERSONAJES",))
    fv = D / "resultados" / "vestuario_por_escena.json"
    if fv.is_file():
        v = _load_json(fv); por = {}
        canal = D.parent.name
        bib = Path("/opt/myia-taller-n8n/trabajo/biblioteca") / canal / "personajes"
        refs = {}
        if (bib / "personajes.json").is_file():
            for p in _load_json(bib / "personajes.json").get("personajes") or []:
                r0 = next((r for ver in p.get("versiones") or [] for r in ver.get("refs") or [] if (bib / r).is_file()), None)
                refs[p.get("id")] = str(bib / r0) if r0 else None
        for n in nums:
            for x in (v.get("escenas") or {}).get(n, []):
                it = por.setdefault(x["personaje_id"], {"nombre": x.get("nombre"), "personaje_id": x["personaje_id"],
                                                         "sheet_path": refs.get(x.get("biblioteca_id")), "escenas": {}, "fuente": "2C → vestuario_por_escena.json"})
                it["escenas"][n] = {"ropa_inicio": x.get("ropa_inicio"), "ropa_fin": x.get("ropa_fin"), "objetos": x.get("objetos")}
        for it in por.values():
            primera = next(iter(it["escenas"].values()))
            it["DESC_ROPA"] = "; ".join(primera.get("ropa_inicio") or primera.get("ropa_fin") or []) or "FALTA"
            if not it["sheet_path"]:
                it.setdefault("gaps", []).append("sin hoja/imagen de referencia en biblioteca")
        doc["PERSONAJES"] = list(por.values())
        origen["PERSONAJES"] = "2C"
    else:
        gaps.append("PERSONAJES — no los entregó 2C (resultados/vestuario_por_escena.json)")
    # --- ancla: 4a5 candidatos + aprobación humana ---
    gaps = _quitar_gaps(gaps, ("ANCLA_ESCENA",))
    an = doc.setdefault("ANCLA_ESCENA", {})
    fa = d / "ancla_aprobada.json"
    if an.get("path") in (None, "SIN_ANCLA") and fa.is_file():
        ap = _load_json(fa)
        if Path(ap.get("imagen", "")).is_file():
            an.update(path=ap["imagen"], path_estado="existe", fuente=f"4a5 aprobada por {ap.get('aprobado')} ({ap.get('fecha')})")
    if an.get("path") in (None, "SIN_ANCLA"):
        I = D / "ramas" / "imagenes" / "4a5"
        cands = [str(p) for p in sorted(I.glob(f"{d.name}*.png")) if p.name == f"{d.name}.png" or "@base" in p.name]
        an["candidatos_4a5"] = cands
        gaps.append(f"ANCLA_ESCENA — pendiente aprobación humana entre {len(cands)} imágenes base de 4a5" if cands
                    else "ANCLA_ESCENA — 4a5 no ha pintado base para este escenario")
    meta["gaps"] = gaps
    meta["lee_de_origen"] = {"4a2": str(g42) if g else None, "2C": str(fv) if fv.is_file() else None,
                             "4a4": str(f44) if a44 else None, "ancla_aprobada": str(fa) if fa.is_file() else None}
    return doc


def armar_doc(esc, path_4a1, *args, **kw):  # noqa: F811 — envoltura t440
    return leer_entregas_origen(_armar_doc_sin_origen(esc, path_4a1, *args, **kw), esc, Path(path_4a1))


def cmd_ancla(a) -> dict:
    """Aprobación HUMANA de la ancla (t440). No elige: exige --imagen entre los candidatos 4a5 y --aprobado QUIEN."""
    if not (a.escenario and a.imagen and a.aprobado):
        return {"ok": False, "accion": "escena ancla", "error": "hace falta --escenario, --imagen y --aprobado"}
    d = Path(a.escenario).parent; D = d.parent.parent.parent
    I = D / "ramas" / "imagenes" / "4a5"
    cands = [str(p) for p in sorted(I.glob(f"{d.name}*.png")) if p.name == f"{d.name}.png" or "@base" in p.name]
    if str(Path(a.imagen)) not in cands:
        return {"ok": False, "accion": "escena ancla", "error": "la imagen no es una base de 4a5 de este escenario", "candidatos": cands}
    import datetime as _dt
    doc = {"schema": "myia.ancla_aprobada.v1", "lugar_id": d.name, "imagen": str(Path(a.imagen)), "aprobado": a.aprobado,
           "fecha": _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=-5))).isoformat(timespec="seconds"), "origen": "4a5"}
    (d / "ancla_aprobada.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"ok": True, "accion": "escena ancla", "ruta": str(d / "ancla_aprobada.json"), "usd": 0, "ai_calls": 0}


def cmd_armar(a: argparse.Namespace) -> dict:
    fichas = []
    gaps_all = []
    if a.escenario:
        path = Path(a.escenario)
        if not path.is_file():
            return {"ok": False, "accion": "escena armar", "error": f"no existe escenario: {path}"}
        esc = _load_json(path)
        glos = Path(a.glosario) if a.glosario else find_glosario(path.parent, a.canal or "", esc.get("id") or "")
        ancla = None if a.sin_ancla else (a.ancla if a.ancla is not None else find_ancla(path.parent, esc.get("id") or ""))
        specs = []
        if a.sidecar:
            for s in a.sidecar:
                specs.append({"nombre": Path(s).stem, "sidecar": s})
        elif a.canal:
            specs = discover_sidecars(a.canal)
        mold = None
        if a.mold_tiene_luces == "si":
            mold = True
        elif a.mold_tiene_luces == "no":
            mold = False
        doc = armar_doc(esc, path, a.escena_num, glos, ancla, specs, mold)
        out = Path(a.out) if a.out else (path.parent / "escena_nivel2.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        fichas.append({
            "lugar_id": esc.get("id"),
            "escena_num": doc["ID_ESCENA"]["numero"],
            "ruta": str(out),
            "gaps": doc["meta"]["gaps"],
            "tipo": doc["TIPO_ENTORNO"]["valor"],
        })
        gaps_all.extend(doc["meta"]["gaps"])
        return {
            "ok": True,
            "accion": "escena armar",
            "canal": a.canal,
            "fichas": fichas,
            "gaps": sorted(set(gaps_all)),
            "usd": 0,
            "resumen": f"1 ficha Nivel 2 en {out}",
        }

    if not a.canal or a.capitulo is None:
        return {"ok": False, "accion": "escena armar", "error": "hace falta --canal y --capitulo (o --escenario)"}
    D = carpeta_capitulo(a.canal, a.capitulo)
    if not D:
        return {"ok": False, "accion": "escena armar", "error": f"no hay carpeta de capítulo para {a.canal} cap {a.capitulo}"}
    moldes = D / "ramas" / "moldes"
    if not moldes.is_dir():
        return {"ok": False, "accion": "escena armar", "error": f"no hay ramas/moldes en {D}"}
    specs = discover_sidecars(a.canal)
    paths = sorted(moldes.glob("*/escenario.json"))
    if a.lugar_id:
        paths = [p for p in paths if p.parent.name == a.lugar_id]
    if not paths:
        return {"ok": False, "accion": "escena armar", "error": "no hay escenario.json 4a1 que coincida"}
    for path in paths:
        esc = _load_json(path)
        if esc.get("fuente") and esc.get("fuente") != "4a1":
            continue
        glos = Path(a.glosario) if a.glosario else find_glosario(path.parent, a.canal, esc.get("id") or path.parent.name)
        ancla = None if a.sin_ancla else (a.ancla if a.ancla is not None else find_ancla(path.parent, esc.get("id") or path.parent.name))
        mold = None
        if a.mold_tiene_luces == "si":
            mold = True
        elif a.mold_tiene_luces == "no":
            mold = False
        doc = armar_doc(esc, path, a.escena_num, glos, ancla, specs, mold)
        out = path.parent / "escena_nivel2.json"
        out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        # también por número si se pidió uno concreto
        if a.escena_num:
            out_n = path.parent / f"escena_nivel2_esc{a.escena_num}.json"
            out_n.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        fichas.append({
            "lugar_id": esc.get("id") or path.parent.name,
            "escena_num": doc["ID_ESCENA"]["numero"],
            "numeros_disponibles": doc["ID_ESCENA"].get("numeros_disponibles"),
            "ruta": str(out),
            "gaps": doc["meta"]["gaps"],
            "tipo": doc["TIPO_ENTORNO"]["valor"],
            "estilo_fondo": (doc.get("ESTILO_FONDO_INGLES") or {}).get("valor"),
        })
        gaps_all.extend(doc["meta"]["gaps"])
    idx_dir = D / "cubos" / "escena"
    idx_dir.mkdir(parents=True, exist_ok=True)
    idx = {"canal": a.canal, "capitulo": a.capitulo, "fichas": fichas, "usd": 0}
    (idx_dir / "indice.json").write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
    if not fichas:
        return {"ok": False, "accion": "escena armar", "error": "ningún escenario con fuente=4a1 para empaquetar", "carpeta": str(D)}
    return {
        "ok": True,
        "accion": "escena armar",
        "canal": a.canal,
        "capitulo": a.capitulo,
        "carpeta": str(D),
        "indice": str(idx_dir / "indice.json"),
        "fichas": fichas,
        "gaps": sorted(set(gaps_all)),
        "usd": 0,
        "resumen": f"{len(fichas)} ficha(s) Nivel 2 listas para que el cubo 11 las lea",
    }


def cmd_leer(a: argparse.Namespace) -> dict:
    D = carpeta_capitulo(a.canal, a.capitulo)
    if not D:
        return {"ok": False, "accion": "escena leer", "error": f"no hay carpeta de capítulo para {a.canal} cap {a.capitulo}"}
    fichas = []
    for p in sorted((D / "ramas" / "moldes").glob("*/escena_nivel2.json")):
        try:
            doc = _load_json(p)
        except Exception as ex:
            fichas.append({"ruta": str(p), "ok": False, "error": str(ex)[:200]})
            continue
        fichas.append({
            "ruta": str(p),
            "lugar_id": (doc.get("ID_ESCENA") or {}).get("lugar_id"),
            "numero": (doc.get("ID_ESCENA") or {}).get("numero"),
            "tipo": (doc.get("TIPO_ENTORNO") or {}).get("valor"),
            "gaps": (doc.get("meta") or {}).get("gaps") or [],
            "estilo_fondo": (doc.get("ESTILO_FONDO_INGLES") or {}).get("valor"),
            "ancla": (doc.get("ANCLA_ESCENA") or {}).get("path"),
        })
    return {
        "ok": True,
        "accion": "escena leer",
        "canal": a.canal,
        "capitulo": a.capitulo,
        "carpeta": str(D),
        "fichas": fichas,
        "n_fichas": len(fichas),
        "usd": 0,
        "resumen": f"{len(fichas)} ficha(s) Nivel 2 en disco",
    }


def cmd_sidecar(a: argparse.Namespace) -> dict:
    """Crea/actualiza desc_ropa.json genérico al lado de una hoja. US$0, sin AI."""
    if not a.sheet and not a.refs_dir:
        return {"ok": False, "accion": "escena sidecar", "error": "hace falta --sheet o --refs-dir"}
    if not a.desc and not a.from_texto:
        return {"ok": False, "accion": "escena sidecar", "error": "hace falta --desc o --from-texto"}
    target = Path(a.sheet) if a.sheet else Path(a.refs_dir)
    desc = a.desc
    fuente = a.fuente or "manual"
    nombre = a.nombre
    version = a.version
    extra = {}
    if a.from_texto:
        src_path = Path(a.from_texto)
        if not src_path.is_file():
            return {"ok": False, "accion": "escena sidecar", "error": f"no existe --from-texto {src_path}"}
        data = _load_json(src_path)
        ext = extract_desc_ropa(data)
        if str(ext["DESC_ROPA"]).startswith("FALTA"):
            return {"ok": False, "accion": "escena sidecar", "error": "from-texto sin bloque What the sheet says / DESC_ROPA"}
        desc = ext["DESC_ROPA"]
        nombre = nombre or ext.get("nombre_en_sheet") or src_path.stem
        version = version or ext.get("version") or "FALTA"
        fuente = a.fuente or ext.get("fuente") or "sidecar.texto (What the sheet says)"
        extra["extraido_de"] = str(src_path)
    if not nombre or not version or not desc:
        return {"ok": False, "accion": "escena sidecar", "error": "nombre, version y desc son obligatorios"}
    out = upsert_desc_ropa_sidecar(
        target,
        nombre=nombre,
        version=version,
        desc_ropa=desc,
        fuente=fuente,
        sheet_path=str(Path(a.sheet)) if a.sheet else a.sheet_path,
        extra=extra or None,
    )
    return {
        "ok": True,
        "accion": "escena sidecar",
        "ruta": str(out),
        "nombre": nombre,
        "version": version,
        "DESC_ROPA": desc,
        "fuente": fuente,
        "usd": 0,
        "ai_calls": 0,
        "resumen": f"desc_ropa.json en {out}",
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(prog="armar_escena")
    ap.add_argument("accion", choices=["armar", "leer", "sidecar", "ancla"])
    ap.add_argument("--imagen", default=None)
    ap.add_argument("--aprobado", default=None)
    ap.add_argument("--canal", default=None)
    ap.add_argument("--capitulo", default=None)
    ap.add_argument("--lugar-id", dest="lugar_id", default=None)
    ap.add_argument("--escena-num", dest="escena_num", default=None)
    ap.add_argument("--escenario", default=None, help="path directo a escenario.json")
    ap.add_argument("--glosario", default=None)
    ap.add_argument("--ancla", default=None)
    ap.add_argument("--sin-ancla", dest="sin_ancla", action="store_true")
    ap.add_argument("--sidecar", action="append", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--mold-tiene-luces", dest="mold_tiene_luces", choices=["si", "no"], default=None)
    # escena sidecar …
    ap.add_argument("--sheet", default=None, help="ruta a la hoja (png/jpg); escribe desc_ropa.json al lado")
    ap.add_argument("--refs-dir", dest="refs_dir", default=None, help="directorio refs/ donde escribir desc_ropa.json")
    ap.add_argument("--desc", default=None, help="texto DESC_ROPA (palabras; no inventar)")
    ap.add_argument("--from-texto", dest="from_texto", default=None, help="JSON legado con bloque What the sheet says")
    ap.add_argument("--nombre", default=None)
    ap.add_argument("--version", default=None)
    ap.add_argument("--fuente", default=None)
    ap.add_argument("--sheet-path", dest="sheet_path", default=None, help="sheet_path a guardar dentro del sidecar")
    a = ap.parse_args(argv)
    if a.accion == "armar":
        return cmd_armar(a)
    if a.accion == "sidecar":
        return cmd_sidecar(a)
    if a.accion == "ancla":
        return cmd_ancla(a)
    return cmd_leer(a)


if __name__ == "__main__":
    r = main()
    print(json.dumps(r, ensure_ascii=False, indent=2))
    sys.exit(0 if r.get("ok") else 2)
