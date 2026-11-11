"""entregas_origen.py — t440 (Ricardo): cada módulo de ORIGEN entrega en su salida lo que 4a1b necesita.
GRATIS, sin red, sin IA. Solo reordena/copia datos que el propio módulo ya produjo; nunca inventa.
  4a2 (Blender)  → ramas/moldes/<id>/glosario_4a2.json   (formas del molde + fondo de exteriores)
  2C (personajes)→ resultados/vestuario_por_escena.json   (ropa de cada personaje SOLO en las escenas donde aparece)
  4a4 (prompts)  → ramas/moldes/<id>/atmosfera_4a4.json   (estilo/atmósfera EN por escena, extraída de lo que 4a4 escribió)
  4a5 (imágenes) → ancla: NO se elige sola. candidatos_ancla(); la elige un humano con
                   «paso00_cadena escena ancla --escenario <ruta escenario.json> --imagen <png> --aprobado QUIEN».
Uso de relleno con datos existentes: python3 entregas_origen.py --carpeta <carpeta capítulo> [--solo 4a2,2c,4a4]
"""
import json, re, sys, unicodedata, datetime
from pathlib import Path

def _j(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))

def _w(p, d):
    Path(p).write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8"); return str(p)

def _ahora():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-5))).isoformat(timespec="seconds")

def _moldes(D):
    return sorted(p for p in (Path(D) / "ramas" / "moldes").glob("*/") if (p / "escenario.json").is_file())

def _slug(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]+", "_", t.upper()).strip("_")[:40] or "FORMA"

def _clave(n):
    n = n.lower()
    if re.search(r"suelo|piso", n): return "PISO"
    if re.search(r"pared|muro", n): return "PAREDES"
    if "fachada" in n: return "MURO_FACHADA"
    return _slug(n)

FONDO_KEYS =[REDACTED]

def _mat(nombre, mats):
    n = nombre.lower()
    for m in mats or []:
        sup = (m.get("superficie") or "").lower()
        if n in sup or any(w in sup for w in re.findall(r"[a-záéíóúñ]{5,}", n)):
            return m
    return None

# ---------------- 4a2 ----------------
def entregar_4a2(D, solo=None):
    out = []
    for d in _moldes(D):
        if solo and d.name not in solo: continue
        if not (d / "molde.json").is_file():
            out.append({"lugar": d.name, "ok": False, "falta": "molde.json (4a2 no terminó Blender)"}); continue
        esc, molde = _j(d / "escenario.json"), _j(d / "molde.json")
        mats = esc.get("materiales_texturas") or []
        formas, usadas = {}, set()
        for e in esc.get("elementos_blender") or []:
            nom = e.get("nombre") or "?"; k = _clave(nom)
            while k in usadas: k += "_2"
            usadas.add(k)
            m = _mat(nom, mats) or {}
            formas[k] = (f"{nom}. Forma: {e.get('forma')}. Tamaño: {e.get('ancho_m')}×{e.get('fondo_m')}×{e.get('alto_m')} m. "
                         f"Posición: x={e.get('x_m')}, y={e.get('y_m')}, z={e.get('z_m')}. "
                         f"Material: {m.get('material') or e.get('material') or 'FALTA'}"
                         + (f"; color: {m['color']}" if m.get("color") else "")
                         + (f"; textura: {m['textura']}" if m.get("textura") else "") + "; encima: nada inventado")
        exterior = bool(molde.get("exterior")) or (esc.get("int_ext") or "").upper() == "EXT"
        fondo = None
        if exterior:
            for m in mats:
                sup = (m.get("superficie") or "").lower()
                if any(k in sup for k in FONDO_KEYS) and not re.search(r"suelo|piso", sup):
                    fondo = {"linea": f"{m.get('superficie')}: {m.get('material')}, color {m.get('color')}, {m.get('textura') or ''}".strip(", "),
                             "origen": "4a1.materiales_texturas (superficie de fondo)"}; break
            if not fondo and molde.get("fondo_lejano_no_modelado"):
                f0 = next((f for f in molde["fondo_lejano_no_modelado"] if f.get("direccion") == "fondo"), molde["fondo_lejano_no_modelado"][0])
                fondo = {"linea": f"Fondo lejano ({f0.get('direccion')}): {f0.get('que_es')}", "origen": "4a1.ambiente_vivo.fondo_lejano (vía molde 4a2)"}
        doc = {"schema": "myia.glosario_4a2.v1", "lugar_id": d.name, "entregado_por": "4a2", "fecha": _ahora(),
               "fuente": "molde.json (Blender 4a2) + escenario.json (4a1)", "exterior": exterior, "formas": formas,
               "fondo_lejano": molde.get("fondo_lejano_no_modelado") or [], "materiales_fondo": fondo,
               "faltas": ([] if formas else ["4a1 sin elementos_blender"]) + (["exterior sin superficie de fondo en 4a1"] if exterior and not fondo else [])}
        out.append({"lugar": d.name, "ok": bool(formas), "formas": len(formas), "fondo": bool(fondo), "ruta": _w(d / "glosario_4a2.json", doc)})
    return out

# ---------------- 2C ----------------
def _mapa_biblioteca(D):
    canal = Path(D).parent.name
    pj = Path("/opt/myia-taller-n8n/trabajo/biblioteca") / canal / "personajes" / "personajes.json"
    m = {}
    if pj.is_file():
        for p in _j(pj).get("personajes") or []:
            for i in p.get("ids_mapa") or []:
                m[i] = {"id": p.get("id"), "nombre": p.get("nombre"), "nunca_cambia": p.get("nunca_cambia")}
    return m

def entregar_2c(D):
    R = Path(D) / "respuestas"
    src = next((R / f for f in ("personajes.resuelto.json", "personajes.reparado.json", "personajes.json") if (R / f).is_file()), None)
    if not src: return {"ok": False, "falta": "2C no tiene respuesta (respuestas/personajes.json)"}
    data = _j(src); bib = _mapa_biblioteca(D); por = {}
    for p in data.get("personajes") or []:
        pid = p.get("personaje_id"); b = bib.get(pid, {})
        for e in p.get("estados") or []:
            ini, fin = e.get("inicio") or {}, e.get("fin") or {}
            por.setdefault(str(e.get("escena")), []).append({
                "personaje_id": pid, "biblioteca_id": b.get("id"), "nombre": b.get("nombre") or pid,
                "ropa_inicio": ini.get("ropa") or [], "ropa_fin": fin.get("ropa") or [],
                "objetos": sorted(set((ini.get("objetos") or []) + (fin.get("objetos") or []))),
                "forma_id": fin.get("forma_id") or ini.get("forma_id"), "nunca_cambia": b.get("nunca_cambia")})
    doc = {"schema": "myia.vestuario_por_escena.v1", "entregado_por": "2C", "fecha": _ahora(), "fuente": str(src),
           "regla": "solo personajes con estado en esa escena (aparecen)", "escenas": por}
    f = _w(Path(D) / "resultados" / "vestuario_por_escena.json", doc)
    return {"ok": True, "escenas": len(por), "ruta": f}

# ---------------- 4a4 ----------------
MOOD = re.compile(r"\b(lighting|light|lights|sunlight|daylight|glow|glows|shadows?|atmosphere|mood|palette|bloom|haze|mist|fog|grayscale|monochrome|desaturated)\b", re.I)

def _frases_mood(t):
    fr = [s.strip() for s in re.split(r"(?<=[.;])\s+", t or "") if MOOD.search(s) and len(s) < 350 and not re.search(r"\bx=|\bobj-", s)]
    return " ".join(fr)[:900]

def entregar_4a4(D, solo=None):
    out = []
    R = Path(D) / "respuestas"
    for d in _moldes(D):
        if solo and d.name not in solo: continue
        src = next((R / f"prompts_escenarios__{d.name}{s}.json" for s in (".resuelto", ".reparado", "") if (R / f"prompts_escenarios__{d.name}{s}.json").is_file()), None)
        if not src: out.append({"lugar": d.name, "ok": False, "falta": "4a4 sin respuesta para este escenario"}); continue
        es = next((e for e in _j(src).get("escenarios") or [] if e.get("escenario_id") == d.name), None)
        if not es: out.append({"lugar": d.name, "ok": False, "falta": "4a4 respuesta sin este escenario"}); continue
        base = es.get("base") or {}
        por = {}
        for v in es.get("variantes") or []:
            fr = _frases_mood(v.get("prompt_edicion_en"))
            for n in v.get("escenas") or []:
                if fr: por.setdefault(str(n), []).append({"variante": v.get("variante_id"), "atmosfera_en": fr})
        doc = {"schema": "myia.atmosfera_4a4.v1", "lugar_id": d.name, "entregado_por": "4a4", "fecha": _ahora(), "fuente": str(src),
               "estilo_en": es.get("adaptacion_estilo_en") or "", "atmosfera_base_en": _frases_mood(base.get("prompt_en")),
               "por_escena": por, "nota": "frases EN escritas por 4a4 (luz/clima/color); extraídas sin traducir ni inventar"}
        ok = bool(doc["estilo_en"] or doc["atmosfera_base_en"])
        out.append({"lugar": d.name, "ok": ok, "escenas": sorted(por), "ruta": _w(d / "atmosfera_4a4.json", doc)})
    return out

# ---------------- 4a5 (ancla: solo candidatos) ----------------
def candidatos_ancla(D, lugar_id):
    I = Path(D) / "ramas" / "imagenes" / "4a5"
    return [str(p) for p in sorted(I.glob(f"{lugar_id}*.png")) if p.name == f"{lugar_id}.png" or "@base" in p.name]

def tras_paso(D, p):
    if p == "personajes": return entregar_2c(D)
    if p.startswith("prompts_escenarios"):
        eid = p.split("__", 1)[1] if "__" in p else None
        return entregar_4a4(D, {eid} if eid else None)
    return None

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--carpeta", required=True); ap.add_argument("--solo", default="4a2,2c,4a4")
    a = ap.parse_args(); s = set(a.solo.split(","))
    r = {"ok": True, "usd": 0, "ai_calls": 0}
    if "4a2" in s: r["4a2"] = entregar_4a2(a.carpeta)
    if "2c" in s: r["2c"] = entregar_2c(a.carpeta)
    if "4a4" in s: r["4a4"] = entregar_4a4(a.carpeta)
    print(json.dumps(r, ensure_ascii=False, indent=1))
