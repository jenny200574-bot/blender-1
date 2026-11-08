"""Movimiento natural UNIVERSAL (v7). Reglas en código calculadas desde el esqueleto/ADN de cada personaje,
con parámetros por personaje del catálogo 'catalogo_perfiles_movimiento' (investigados por Argon en 2B y afinados por el validador).
- fases intermedias automáticas (si dos poses clave difieren demasiado)
- curva continua Catmull-Rom entre poses clave (sin frenar en cada fase) + arranque/frenado suave
- solape humano: tronco y brazos van con retraso respecto a la cadera (segundos del perfil)
- anclaje de pies: el apoyo plantado no se mueve en el mundo mientras el otro se mueve
- equilibrio: centro de masa sobre el polígono de apoyo; si no, corrige tronco/cadera; si no alcanza, lo reporta
- no humanos: vuela (sin piso ni equilibrio), cola (contrapeso), cuadrúpedo (apoyos x4)"""
import json, math, datetime, os
from pathlib import Path
AQUI = Path(__file__).resolve().parent
def activo(nombre):
    """Interruptor universal: el cambio está ACTIVO salvo que exista <nombre>.off junto al motor.
    (Para pruebas: variable de entorno MYIA_ON / MYIA_OFF con nombres separados por coma, gana sobre el archivo.)"""
    if nombre in os.environ.get("MYIA_OFF", "").split(","): return False
    if nombre in os.environ.get("MYIA_ON", "").split(","): return True
    return not (AQUI / f"{nombre}.off").exists()
CATP = AQUI / "catalogo_perfiles_movimiento" / "catalogo_perfiles_movimiento.json"
PARAMS = {  # nombre: (defecto, min, max, explicación)
 "retraso_tronco_s": (0.06, 0, 0.3, "el tronco sigue a la cadera con este retraso"),
 "retraso_brazos_s": (0.12, 0, 0.4, "brazos/cabeza siguen al tronco con este retraso"),
 "umbral_fase_intermedia_deg": (45, 15, 120, "si dos poses clave difieren más, se inserta una intermedia"),
 "suavizado_inicio_fin": (0.25, 0, 0.5, "fracción del tramo con arranque/frenado suave"),
 "vel_max_deg_s": (240, 60, 900, "velocidad angular máxima de una articulación"),
 "anclaje_pies": (1.0, 0, 1, "1 = el pie plantado queda fijo"),
 "margen_equilibrio_m": (0.04, 0, 0.2, "tolerancia del centro de masa fuera del apoyo"),
 "correccion_equilibrio_max_deg": (12, 0, 30, "cuánto puede inclinar tronco/cadera para equilibrar"),
 "vel_vertical_max_m_s": (0.9, 0.2, 5, "velocidad vertical máx. de la cadera (evita saltitos)"),
 "masa_rel": (1.0, 0.3, 3, "masa relativa (más masa = movimientos más lentos)"),
 "temblor_deg": (0.0, 0, 6, "temblor de piernas por fatiga/miedo"),
 "vuela": (0, 0, 1, "1 = puede volar: sin piso ni equilibrio"),
 "cola_contrapeso": (0.0, 0, 1, "la cola se mueve contra el tronco para equilibrar"),
 "cuadrupedo": (0, 0, 1, "1 = camina en 4 apoyos"),
 "anclaje_excursion_max_m": (0.65, 0.1, 2.0, "cambio D: cuánto puede desplazarse en total el cuerpo para mantener fijo el apoyo plantado"),
}
def ahora(): return datetime.datetime.now().astimezone().isoformat(timespec="seconds")
def cargar(path):
    return json.loads(Path(path).read_text())
def guardar(C,path):
    target=Path(path)
    if target.exists():target.with_suffix(target.suffix+'.bak_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')).write_bytes(target.read_bytes())
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(C,ensure_ascii=False,indent=2))
def desde_adn(s):
    """Perfil base calculado solo del esqueleto/ADN (sin IA)."""
    p = {k: v[0] for k, v in PARAMS.items()}; H = s["altura_m"]; g = {"robusto": 1.25, "medio": 1.0, "delgado": 0.85}[s["complexion"]]
    p["masa_rel"] = max(1e-12, g * (H / s["altura_referencia_perfil_m"]) ** 3); p["retraso_tronco_s"] = round(0.05 * p["masa_rel"] ** 0.5, 3); p["retraso_brazos_s"] = round(0.1 * p["masa_rel"] ** 0.5, 3)
    p["vel_max_deg_s"] = round(260 / p["masa_rel"] ** 0.3); p["vuela"] = int("alas" in s["extras"]); p["cola_contrapeso"] = 0.5 if "cola" in s["extras"] else 0.0
    return p
def limpiar(p):
    out = {}
    for k, (d, lo, hi, _) in PARAMS.items():
        try: out[k] = max(lo, min(hi, float(p.get(k, d))))
        except Exception: out[k] = d
    return out
def perfil(C, pid, s):
    e = C["perfiles"].get(pid); base = desde_adn(s)
    return limpiar({**base, **(e["parametros"] if e else {})}), (e["version"] if e else 0)
def registrar(C, pid, params, origen, escena, validado, nota="", metricas=None):
    e = C["perfiles"].get(pid); hist = (e.get("historial", []) + [{k: e[k] for k in ("version", "parametros", "origen", "fecha", "metricas") if k in e}]) if e else []
    C["perfiles"][pid] = {"personaje": pid, "parametros": limpiar(params), "origen": origen, "fecha": ahora(), "escena": escena, "validado": validado,
                          "version": (e["version"] + 1) if e else 1, "nota": nota, "metricas": metricas or {}, "historial": hist}
# ---------- curvas ----------
GRUPO_RETRASO = {"pelvis": 0, "raiz": 0, "muslo": 0, "pierna": 0, "pie": 0, "columna": 1, "pecho": 1, "cola": 1, "clavicula": 2, "brazo": 2, "antebrazo": 2, "mano": 2, "cuello": 2, "cabeza": 2, "oreja": 2, "ala": 2}
def grupo(h): return h.rsplit("_", 1)[0] if h[-2:] in ("_L", "_R") else h
FASE_APOYO_OFF = AQUI / "fase_apoyo.off"
def fase_apoyo_activa(): return activo("fase_apoyo")
def _clave_apoyo(prev, a, nuevos, cadena_de, t):
    """v9 fase de apoyo: el peso sigue en los apoyos actuales (apoyos=prev) y SOLO las extremidades de los apoyos nuevos
    toman ya su ángulo final (para llegar al piso). Universal: la cadena de cada apoyo la da cadena_de(hueso) desde el esqueleto."""
    h = {k: list(v) for k, v in prev[1].items()}
    for b in nuevos:
        for k in (cadena_de(b) if cadena_de else [x for x in set(a) | set(prev[1]) if x.endswith(b[b.rfind("_"):]) and "_" in b]):
            if k in a or k in prev[1]: h[k] = list(a.get(k, prev[1].get(k, [0, 0, 0])))
    return (t, h, list(prev[2]), prev[3], 0.0, False, sorted(nuevos))
def expandir_fases(fases, poses, umbral, cadena_de=None, frac_apoyo=0.45):
    """Inserta poses intermedias (promedio) entre poses clave muy distintas. Devuelve [(t, angulos, apoyos, anclar, desp, es_intermedia[, apoyos_llegando])].
    v9: si la fase siguiente tiene MÁS apoyos, primero inserta una clave de apoyo (los apoyos nuevos bajan al piso con el peso en los actuales)
    y después transfiere el centro de masa. Se apaga con el archivo fase_apoyo.off."""
    keys = []; t0 = 0.0; prev = None; fa = fase_apoyo_activa()
    for f in fases:
        a = poses[f["pose"]]; t1 = f["t_fin_frac"]
        nuevos = set(f.get("apoyos", [])) - set(prev[2]) if prev is not None else set()
        if fa and prev is not None and len(f.get("apoyos", [])) > len(prev[2]) and nuevos:
            keys.append(_clave_apoyo(prev, a, nuevos, cadena_de, t0 + (t1 - t0) * frac_apoyo)); prev = keys[-1]; t0 = prev[0]
        if prev is not None:
            ks = set(a) | set(prev[1]); dmax = max([abs(a.get(k, [0, 0, 0])[i] - prev[1].get(k, [0, 0, 0])[i]) for k in ks for i in range(3)] or [0])
            n = int(dmax // umbral)
            for j in range(1, n + 1):
                w = j / (n + 1); keys.append((t0 + (t1 - t0) * w, {k: [prev[1].get(k, [0, 0, 0])[i] * (1 - w) + a.get(k, [0, 0, 0])[i] * w for i in range(3)] for k in ks}, prev[2], prev[3], 0.0, True))
        keys.append((t1, a, f.get("apoyos", []), f.get("anclar_apoyo", True), f.get("desplazamiento_m", 0.0), False)); prev = keys[-1]; t0 = t1
    return keys
def _cr(p0, p1, p2, p3, u):
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)
def muestrear(keys, inicio, u):
    """Catmull-Rom sobre las poses clave (inicio = pose al empezar el tramo, en u=0). Velocidad continua entre fases."""
    T = [0.0] + [k[0] for k in keys]; A = [inicio] + [k[1] for k in keys]; u = max(0.0, min(1.0, u))
    i = max(0, min(len(T) - 2, next((j for j in range(len(T) - 1) if u <= T[j + 1] + 1e-9), len(T) - 2)))
    w = (u - T[i]) / max(1e-6, T[i + 1] - T[i]); w = w * w * (3 - 2 * w) * 0.35 + w * 0.65   # leve frenado en cada clave, sin parar
    P = [A[max(0, i - 1)], A[i], A[i + 1], A[min(len(A) - 1, i + 2)]]; ks = set().union(*P)
    out = {k: [_cr(*(p.get(k, [0, 0, 0])[c] for p in P), w) for c in range(3)] for k in ks}
    slerp = activo("slerp_raiz") and "raiz" in ks
    if slerp: out["raiz"] = _slerp_raiz(P[1].get("raiz", [0, 0, 0]), P[2].get("raiz", [0, 0, 0]), w)
    # limitar el sobrepaso de Catmull-Rom al rango de las dos claves
    for k in ks:
        if slerp and k == "raiz": continue
        for c in range(3):
            lo, hi = sorted((P[1].get(k, [0, 0, 0])[c], P[2].get(k, [0, 0, 0])[c])); m = 0.08 * (hi - lo) + 1
            out[k][c] = max(lo - m, min(hi + m, out[k][c]))
    return out, keys[min(len(keys) - 1, i)]
# ---- cambio A (slerp_raiz): la raíz se interpola como rotación (cuaternión), no componente por componente ----
# Convención real del motor (armar_v9): rotation_euler XYZ = (-pitch, roll, yaw), raiz = [pitch, roll, yaw] en grados.
def _q_mul(a, b):
    w1, x1, y1, z1 = a; w2, x2, y2, z2 = b
    return (w1*w2 - x1*x2 - y1*y2 - z1*z2, w1*x2 + x1*w2 + y1*z2 - z1*y2, w1*y2 - x1*z2 + y1*w2 + z1*x2, w1*z2 + x1*y2 - y1*x2 + z1*w2)
def _raiz_a_q(r):
    a, b, c = -math.radians(r[0]), math.radians(r[1]), math.radians(r[2] if len(r) > 2 else 0)
    qx = (math.cos(a/2), math.sin(a/2), 0, 0); qy = (math.cos(b/2), 0, math.sin(b/2), 0); qz = (math.cos(c/2), 0, 0, math.sin(c/2))
    return _q_mul(qz, _q_mul(qy, qx))   # XYZ: R = Rz·Ry·Rx
def _q_a_raiz(q, ref):
    w, x, y, z = q
    sb = max(-1.0, min(1.0, 2 * (w*y - z*x)))
    a = math.atan2(2 * (w*x + y*z), 1 - 2 * (x*x + y*y)); b = math.asin(sb); c = math.atan2(2 * (w*z + x*y), 1 - 2 * (y*y + z*z))
    ra = [-math.degrees(a), math.degrees(b), math.degrees(c)]
    rb = [-math.degrees(a + math.pi), math.degrees(math.pi - b), math.degrees(c + math.pi)]   # misma rotación, otra terna
    def cerca(v, rf): return v + 360 * round((rf - v) / 360)
    ra = [cerca(ra[i], ref[i]) for i in range(3)]; rb = [cerca(rb[i], ref[i]) for i in range(3)]
    return min((ra, rb), key=lambda t: sum((t[i] - ref[i]) ** 2 for i in range(3)))
def _slerp_raiz(r0, r1, w):
    q0, q1 = _raiz_a_q(r0), _raiz_a_q(r1); d = sum(q0[i] * q1[i] for i in range(4))
    if d < 0: q1 = tuple(-v for v in q1); d = -d   # hemisferio continuo (camino corto)
    if d > 0.9995: q = tuple(q0[i] + (q1[i] - q0[i]) * w for i in range(4))
    else:
        th = math.acos(d); s0 = math.sin((1 - w) * th) / math.sin(th); s1 = math.sin(w * th) / math.sin(th); q = tuple(q0[i] * s0 + q1[i] * s1 for i in range(4))
    n = math.sqrt(sum(v * v for v in q)); q = tuple(v / n for v in q)
    r0 = list(r0) + [0] * (3 - len(r0)); r1 = list(r1) + [0] * (3 - len(r1))
    return _q_a_raiz(q, [r0[i] + (r1[i] - r0[i]) * w for i in range(3)])
def facil(u, s):   # arranque/frenado suave en los extremos del tramo (mezcla lineal + smootherstep)
    u = max(0.0, min(1.0, u)); q = u * u * u * (u * (u * 6 - 15) + 10); a = min(1.0, 2 * s); return (1 - a) * u + a * q
def con_solape(keys, inicio, u, dur, prf):
    """Cada grupo usa su propio tiempo: cadera/piernas a tiempo, tronco y brazos con retraso (overlap)."""
    base, kc = muestrear(keys, inicio, facil(u, prf["suavizado_inicio_fin"])); out = {}
    for lvl, lag in ((1, prf["retraso_tronco_s"]), (2, prf["retraso_tronco_s"] + prf["retraso_brazos_s"])):
        ul = facil(max(0.0, u - lag / max(dur, 1e-3)), prf["suavizado_inicio_fin"]); a, _ = muestrear(keys, inicio, ul)
        for k, v in a.items():
            if GRUPO_RETRASO.get(grupo(k), 0) == lvl: out[k] = v
    for k, v in base.items(): out.setdefault(k, v)
    if prf["cola_contrapeso"] > 0 and "columna" in out:
        out["cola"] = [-out["columna"][0] * prf["cola_contrapeso"], -out["columna"][1] * prf["cola_contrapeso"], 0]
    return out, kc
# ---------- equilibrio ----------
def centro_masa(A, rad):
    import bpy
    from mathutils import Vector
    M = A.matrix_world; s = Vector((0, 0, 0)); m = 0
    for pb in A.pose.bones:
        h, t = M @ pb.head, M @ pb.tail; w = rad[pb.name] ** 2 * max(0.02, (t - h).length) * (3 if pb.name == "cabeza" else 1); s += (h + t) / 2 * w; m += w
    return s / m
def puntos_contacto(A, rad, umbral=0.06, apoyos=None):
    """apoyos (cambio B, contacto_apoyos): {hueso: punto_mundo} de los apoyos DECLARADOS activos del tramo."""
    M = A.matrix_world; P = []
    for pb in A.pose.bones:
        if pb.name.startswith("pie"):   # pie apoyado = talón (bajo el tobillo) + punta
            h, t = M @ pb.head, M @ pb.tail
            uz = umbral + 0.04   # grosor de la suela
            if t.z < uz or h.z < uz * 0.5 + 0.06:
                tal = h - (t - h) * 0.3; P += [(h.x, h.y), (tal.x, tal.y)] + ([(t.x, t.y)] if t.z < uz + 0.03 else [])
            continue
        r = rad[pb.name]
        for p in (M @ pb.head, M @ pb.tail):
            if p.z - r < umbral: P.append((p.x, p.y))
    if apoyos and activo("contacto_apoyos"):
        # ---- cambio B: el polígono incluye los apoyos declarados que están en el piso (tolerancia umbral+0.03),
        # cada uno con su parche de contacto (círculo del radio real del hueso: palma/rodilla/cadera no son un punto) ----
        for nm, p in apoyos.items():
            if nm.startswith("pie"):
                pb = A.pose.bones[nm]; h, t = M @ pb.head, M @ pb.tail; uz = umbral + 0.03 + 0.04
                if t.z < uz or h.z < uz * 0.5 + 0.06:
                    tal = h - (t - h) * 0.3; P += [(h.x, h.y), (tal.x, tal.y), (t.x, t.y)]
                continue
            r = rad[nm]
            if p.z - r <= umbral + 0.03:
                rr = max(0.02, min(0.06, r))
                P += [(p.x + rr * math.cos(i * math.pi / 4), p.y + rr * math.sin(i * math.pi / 4)) for i in range(8)]
    return P
def _hull(P):
    P = sorted(set((round(x, 4), round(y, 4)) for x, y in P))
    if len(P) < 3: return P
    def cr(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in P:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]
def distancia_fuera(c, P, ancho_pie=0.05):
    """>0: cuánto queda el centro de masa fuera del polígono de apoyo (m). Pies cuentan con su ancho."""
    H = _hull(P)
    if not H: return 9.0
    def dseg(p, a, b):
        ax, ay = b[0] - a[0], b[1] - a[1]; L = ax * ax + ay * ay; t = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / L))
        return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)
    p = (c.x, c.y)
    if len(H) >= 3:
        dentro = all((H[(i + 1) % len(H)][0] - H[i][0]) * (p[1] - H[i][1]) - (H[(i + 1) % len(H)][1] - H[i][1]) * (p[0] - H[i][0]) >= 0 for i in range(len(H)))
        if dentro: return 0.0
    d = min(dseg(p, H[i], H[(i + 1) % len(H)]) for i in range(len(H))) if len(H) > 1 else math.hypot(p[0] - H[0][0], p[1] - H[0][1])
    return max(0.0, d - ancho_pie)

# ---------- IK de extremidades contra el piso (evita "patadas" y saltitos en las transiciones) ----------
CADENAS = [("muslo_{s}", "pierna_{s}"), ("brazo_{s}", "antebrazo_{s}")]
def ik_bajar(A, ang, puntos, cadena_de, aplicar, limites_fn, peso=1.0, iters=10):
    """v9 fase de apoyo: IK hacia Z=0 de los apoyos que están llegando (solo dobla su propia cadena; el resto del cuerpo no se toca).
    puntos: {hueso: función(A)->punto del mundo}. peso 0..1 = cuánto se acerca este cuadro (sube a 1 al llegar a la clave)."""
    import bpy
    vars_ = sorted({h for b in puntos for h in cadena_de(b) if h in A.pose.bones}); ang = {x: list(v) for x, v in ang.items()}
    for h in vars_: ang.setdefault(h, [0, 0, 0])
    def cost(a):
        aplicar(A, a); bpy.context.view_layer.update(); return sum(max(0.0, fn(A).z) ** 2 for fn in puntos.values())
    c0 = cost(ang); c = c0; base = {h: list(ang[h]) for h in vars_}
    for paso in (8, 4, 2, 1):
        for _ in range(iters // 3 + 1):
            mejor = False
            for h in vars_:
                for k in range(3):
                    for d in (paso, -paso):
                        a2 = {x: list(v) for x, v in ang.items()}; a2[h][k] += d; limites_fn(a2); c2 = cost(a2)
                        if c2 < c - 1e-7: ang, c, mejor = a2, c2, True
            if not mejor: break
    if peso < 1:
        for h in vars_: ang[h] = [base[h][i] + (ang[h][i] - base[h][i]) * peso for i in range(3)]
    aplicar(A, ang); bpy.context.view_layer.update(); return ang
def ik_piso(A, ang, rad, aplicar, limites_fn, suelo_fn, delta_prev=None, iters=12, apoyos=None):
    """Con la cadera a la altura objetivo, dobla rodilla/codo/cadera/hombro/tobillo de la extremidad que atraviesa el piso.
    Arranque en caliente con la corrección del cuadro anterior (continuidad) y costo por corrección grande (vuelve sola a la pose)."""
    import bpy
    vars_ = [(f.format(s=s), 0) for s in "LR" for ch in CADENAS for f in ch] + [(f"pie_{s}", 0) for s in "LR"]
    base = {x: list(v) for x, v in ang.items()}
    for h, k in vars_: base.setdefault(h, [0, 0, 0])
    ang = {x: list(v) for x, v in base.items()}
    for h, d in (delta_prev or {}).items(): ang[h][0] += d * 0.97
    limites_fn(ang)
    suave = bool(apoyos) and activo("ik_piso_suave")   # cambio C: atracción suave de dos lados al piso de los apoyos declarados
    def cost(a):
        aplicar(A, a); bpy.context.view_layer.update(); M = A.matrix_world; c = 0.0
        for pb in A.pose.bones:
            r = 0 if pb.name.startswith("pie") else rad[pb.name]
            for p in (M @ pb.head, M @ pb.tail): c += max(0.0, -(p.z - r)) ** 2
        ex = 0.0
        if suave:
            for nm, fn in apoyos.items():
                r = 0 if nm.startswith("pie") else rad[nm]; zz = fn(A).z - r
                if zz < 0.12: ex += 30 * zz * zz   # solo apoyos cerca del piso (no arrastra una mano en el aire)
            ex += 2e-4 * sum((a[h][0] - base[h][0] - (delta_prev or {}).get(h, 0)) ** 2 for h, _ in vars_)
        return ex + c * 1000 + 1e-5 * sum((a[h][0] - base[h][0]) ** 2 for h, _ in vars_) + 4e-5 * sum((a[h][0] - base[h][0] - (delta_prev or {}).get(h, 0)) ** 2 for h, _ in vars_)
    c = cost(ang)
    for paso in ((8, 4, 2, 1, 0.5, 0.25) if suave else (8, 4, 2, 1)):
        for _ in range(iters // 3):
            mejor = False
            for h, k in vars_:
                for d in (paso, -paso):
                    a2 = {x: list(v) for x, v in ang.items()}; a2[h][k] += d; limites_fn(a2); c2 = cost(a2)
                    if c2 < c - 1e-9: ang, c, mejor = a2, c2, True
            if not mejor: break
    aplicar(A, ang); bpy.context.view_layer.update()
    return ang, {h: ang[h][0] - base[h][0] for h, _ in vars_}


def aplicar_politica_entrada(solver):
    """Compatibilidad por contrato: ausencia=False; .off siempre deshabilita."""
    managed={'slerp_raiz','ik_piso_suave','piso_suave','equilibrio_memoria','fase_apoyo','anclaje_mismo_cuadro','orden_medicion'}
    off=set(filter(None,os.environ.get('MYIA_OFF','').split(',')))-managed
    on=set(filter(None,os.environ.get('MYIA_ON','').split(',')))-managed
    resolved={}
    for flag in managed:
        value=solver.get(flag,False)
        if not isinstance(value,bool):raise ValueError('Flag de solver debe ser booleano: '+flag)
        enabled=value and not (AQUI/(flag+'.off')).exists();resolved[flag]=enabled
        (on if enabled else off).add(flag)
    os.environ['MYIA_ON']=','.join(sorted(on));os.environ['MYIA_OFF']=','.join(sorted(off))
    return resolved
