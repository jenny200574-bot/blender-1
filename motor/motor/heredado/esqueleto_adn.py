"""Esqueleto adaptable desde el ADN del personaje (sin Blender): estatura, cabezas, complexión, extremidades, partes extra y límites.
Devuelve una especificación de huesos en metros (posición de reposo, mira +Y, z arriba, pelvis en z=alto_pelvis)."""
import re, math
LIMITES = {   # grados: (min,max) por eje [flex, abd, giro]; genéricos humanos, se pueden ampliar por ADN
 "columna": [(-30, 70), (-30, 30), (-35, 35)], "pecho": [(-20, 40), (-20, 20), (-30, 30)], "cuello": [(-40, 60), (-30, 30), (-70, 70)], "cabeza": [(-30, 40), (-20, 20), (-40, 40)],
 "clavicula": [(-15, 15), (-10, 30), (-10, 10)], "brazo": [(-60, 180), (-30, 180), (-90, 90)], "antebrazo": [(0, 150), (-5, 5), (-90, 90)], "mano": [(-70, 70), (-30, 30), (-10, 10)],
 "muslo": [(-30, 125), (-30, 50), (-40, 40)], "pierna": [(0, 155), (-5, 5), (-10, 10)], "pie": [(-45, 30), (-15, 15), (-15, 15)],
 "cola": [(-60, 60), (-60, 60), (-30, 30)], "ala": [(-60, 100), (-20, 120), (-30, 30)], "oreja": [(-20, 20), (-20, 20), (-10, 10)]}
def leer_adn(texto, nombre):
    t = texto.lower(); m_ = re.search(r"## 1\..*?(?=\n## )", t, re.S); f = m_.group(0) if m_ else t
    H = float(re.search(r"estatura\s*~?\s*([0-9]+[.,][0-9]+)", t).group(1).replace(",", ".")) if re.search(r"estatura\s*~?\s*([0-9]+[.,][0-9]+)", t) else None
    cab = re.search(r"~?\s*([0-9]+(?:[.,][0-9]+)?)\s*cabezas", t); cab = float(cab.group(1).replace(",", ".")) if cab else None
    if H is None or cab is None: raise ValueError("ADN sin medidas explícitas")
    comp = "robusto" if re.search(r"robust|corpulent", f) else ("delgado" if re.search(r"delgad|esbelt", f) else "medio")
    atl = bool(re.search(r"atletic|musculad|hombros anchos", f)) and "no atletico" not in f
    extras = []
    if re.search(r"orejas? largas|orejas? puntiagud", t): extras.append("orejas_largas")
    if re.search(r"\bcola\b", t): extras.append("cola")
    if re.search(r"\balas\b", t): extras.append("alas")
    return {"id": nombre, "altura_m": H, "cabezas": cab, "complexion": comp, "atletico": atl, "extras": extras,
            "citas": {"altura": f"Estatura ~{H} m", "cabezas": f"~{cab} cabezas", "complexion": comp}}
def huesos(p):
    """Lista de huesos (nombre, padre, cabeza, cola, radio, grupo_limites). Proporciones en función de cabezas (canon) y complexión."""
    H = p["altura_m"]; hc = H / p["cabezas"]                      # alto de la cabeza
    pierna = H * (0.47 + 0.012 * (p["cabezas"] - 7.5))             # cadera→tobillo; canon de más cabezas = piernas más largas
    tob = H * 0.045; pel = pierna + tob
    cuello_z = H - hc - 0.035 * H; hombro_ancho = H * (0.13 if p["atletico"] else (0.12 if p["complexion"] == "robusto" else 0.105))
    cad_ancho = H * (0.06 if p["complexion"] != "delgado" else 0.052)
    brazo, antebrazo, mano = 0.186 * H, 0.150 * H, 0.105 * H
    g = {"robusto": 1.2, "medio": 1.0, "delgado": 0.85}[p["complexion"]] * (1.08 if p["atletico"] else 1)
    tronco = cuello_z - 0.02 * H - pel; B = []
    def b(n, pa, h, t, r, grp): B.append({"nombre": n, "padre": pa, "cabeza": [round(x, 4) for x in h], "cola": [round(x, 4) for x in t], "radio": round(r, 4), "grupo": grp})
    b("pelvis", None, (0, 0, pel), (0, 0, pel + tronco * 0.3), 0.085 * H * g, "columna")
    b("columna", "pelvis", (0, 0, pel + tronco * 0.3), (0, 0, pel + tronco * 0.62), 0.075 * H * g, "columna")
    b("pecho", "columna", (0, 0, pel + tronco * 0.62), (0, 0, cuello_z - 0.02 * H), 0.085 * H * g, "pecho")
    b("cuello", "pecho", (0, 0, cuello_z - 0.02 * H), (0, 0, H - hc), 0.03 * H * g, "cuello")
    b("cabeza", "cuello", (0, 0, H - hc), (0, 0, H), hc * 0.42, "cabeza")
    hz = cuello_z - 0.035 * H
    for s, sg in (("L", -1), ("R", 1)):
        b(f"clavicula_{s}", "pecho", (sg * 0.02 * H, 0, hz), (sg * hombro_ancho, 0, hz), 0.03 * H * g, "clavicula")
        b(f"brazo_{s}", f"clavicula_{s}", (sg * hombro_ancho, 0, hz), (sg * hombro_ancho, 0, hz - brazo), 0.033 * H * g, "brazo")
        b(f"antebrazo_{s}", f"brazo_{s}", (sg * hombro_ancho, 0, hz - brazo), (sg * hombro_ancho, 0, hz - brazo - antebrazo), 0.027 * H * g, "antebrazo")
        b(f"mano_{s}", f"antebrazo_{s}", (sg * hombro_ancho, 0, hz - brazo - antebrazo), (sg * hombro_ancho, 0, hz - brazo - antebrazo - mano), 0.022 * H, "mano")
        b(f"muslo_{s}", "pelvis", (sg * cad_ancho, 0, pel), (sg * cad_ancho, 0, pel - pierna * 0.5), 0.05 * H * g, "muslo")
        b(f"pierna_{s}", f"muslo_{s}", (sg * cad_ancho, 0, pel - pierna * 0.5), (sg * cad_ancho, 0, tob), 0.038 * H * g, "pierna")
        b(f"pie_{s}", f"pierna_{s}", (sg * cad_ancho, 0, tob), (sg * cad_ancho, 0.14 * H, 0.012 * H), 0.025 * H, "pie")
        if "orejas_largas" in p["extras"]:
            b(f"oreja_{s}", "cabeza", (sg * hc * 0.38, 0, H - hc * 0.5), (sg * hc * 0.95, -hc * 0.25, H - hc * 0.05), 0.012 * H, "oreja")
        if "alas" in p["extras"]:
            b(f"ala_{s}", "pecho", (sg * 0.05 * H, -0.06 * H, hz - 0.05 * H), (sg * 0.45 * H, -0.12 * H, hz + 0.2 * H), 0.02 * H, "ala")
    if "cola" in p["extras"]:
        b("cola", "pelvis", (0, -0.06 * H, pel), (0, -0.4 * H, pel * 0.4), 0.025 * H, "cola")
    return B
