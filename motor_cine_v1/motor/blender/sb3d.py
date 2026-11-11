"""sb3d — «STORYBOARD DESPUÉS DEL 3D» (Blender 5.2.3, código propio MYIA) [Ricardo t1066u, 10-nov-2026].
UNIVERSAL: cualquier canal, capítulo, escena, personaje u objeto; nada fijo en el código. Trabaja sobre la escena YA ARMADA
(escena_motor.blend del motor: escenario + personajes + Kimodo + props) y el guion/SB de la corrida.
  --modo paquete : mide la escena 3D real y exporta corrida/sb3d/: paquete.json (posiciones, alturas, cajas, ojos, frente,
                   grafo de soporte, eje 180°, niveles N0–N3, 4–6 cámaras candidatas por viñeta con su validación 3D),
                   hojas de contacto (miniaturas Workbench 384x216 de inicio y fin de cada candidata) y planta.
  --modo aplicar : lee la decisión de Argon (sb3d/sb_argon.json; si falta, la mejor candidata del motor), arma plano/ángulo/
                   lente/movimiento (STATIC, DOLLYIN, DOLLYOUT, PAN, TILT, TRACK, ORBIT, CRANE, PEDESTAL, ZOOMIN, ZOOMOUT,
                   STEADICAM, HANDHELD, WHIPPAN, CRASHZOOM) y VALIDA en 3D cuadro a cuadro: cámara fuera de muros y muebles,
                   protagonista ≥90 % visible, 180° y 30°, movimiento que se note, nada N0 oculto. Si una viñeta falla pasa a la
                   siguiente candidata. Solo entonces escribe la cámara, oculta SOLO N3 que tapa (ocultar_estorbos con N0
                   protegido), recorta N2 solo con la cámara fuera de ese muro, y guarda escena_motor.blend (respaldo antes).
Uso: blender -b COR/escena_motor.blend -P sb3d.py -- --corrida COR --modo paquete|aplicar [--miniaturas 1] [--paso_val 4]"""
import bpy, sys, os, json, math, time, argparse, re, shutil, traceback, atexit
from mathutils import Vector, Matrix
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
import sb3d_niveles as NV
import camara_calculada as CC
import camara_sin_paredes as CSP
import encuadre_cabeza as ECAB
import numeros_json as NJ
import numpy as np

_OK = False
def _exc(t, v, tb):
    print(''.join(traceback.format_exception(t, v, tb)), flush=True)
    try:
        json.dump({"estado": "FALLO", "error": f"{t.__name__}: {v}", "traceback": ''.join(traceback.format_exception(t, v, tb))[-6000:]},
                  open(os.path.join(SAL, f'sb3d_{A.modo}_error.json'), 'w'), indent=1, ensure_ascii=False)
    except Exception: pass
    os._exit(1)
def _fin():
    if not _OK: print('SB3D_SALIDA: no terminó bien', flush=True); os._exit(1)
sys.excepthook = _exc; atexit.register(_fin)
T0 = time.time()
def log(*a): print(f"[sb3d {time.time() - T0:6.1f}s]", *a, flush=True)

argv = sys.argv[sys.argv.index('--') + 1:]
ap = argparse.ArgumentParser(); ap.add_argument('--corrida', required=True); ap.add_argument('--modo', required=True, choices=['paquete', 'aplicar', 'validar', 'video'])
ap.add_argument('--miniaturas', type=int, default=1); ap.add_argument('--paso_val', type=int, default=4); ap.add_argument('--res_min', default='384x216')
ap.add_argument('--max_candidatas', type=int, default=6); ap.add_argument('--guardar', type=int, default=1)
ap.add_argument('--v2', type=int, default=0); ap.add_argument('--stills', type=int, default=0); ap.add_argument('--res_still', default='640x360')
ap.add_argument('--etiqueta_val', default='1'); ap.add_argument('--res_video', default='560x316'); ap.add_argument('--fps_video', type=float, default=1.0)
A = ap.parse_args(argv)
COR = A.corrida; SAL = os.path.join(COR, 'sb3d'); os.makedirs(SAL, exist_ok=True)
CFG = {}
try: CFG = (json.load(open(os.path.join(COR, 'sb3d_config.json'))) or {})
except Exception: CFG = {}
UMB = {"vis_min": float(CFG.get('vis_protagonista_min', 0.90)), "vis_frame_min": float(CFG.get('vis_cuadro_min', 0.60)),
       "cabeza_en_cuadro_min": float(CFG.get('cabeza_en_cuadro_min', 0.95)), "holgura_m": float(CFG.get('holgura_camara_m', 0.08)),
       "mov_desplaz_m": float(CFG.get('mov_desplazamiento_min_m', 0.35)), "mov_escala": float(CFG.get('mov_cambio_escala_min', 0.12)),
       "mov_giro_deg": float(CFG.get('mov_giro_min_deg', 8.0)), "regla30_deg": float(CFG.get('regla_30_deg', 30.0)),
       "regla30_escala": float(CFG.get('regla_30_escala', 1.4))}

E = json.load(open(f'{COR}/entrada_motor.json')); FPS = E['fps']; N = E['N']
SB = json.load(open(f"{COR}/{E['storyboard']}")) if E.get('storyboard') else {"vinetas": []}
CV = json.load(open(f"{COR}/{E.get('camara_v2') or E.get('camara_v1')}"))
try: CV, _ = NJ.normalizar_camara(CV)
except Exception as ex: log('aviso normalizar_camara', ex)
SBV = {v.get('id'): v for v in SB.get('vinetas', [])}
sc = bpy.context.scene; sc.frame_start = 1; sc.frame_end = N
sensor = CV.get('sensor_mm') or [36.0, 20.25]; SW = float(sensor[0]); SH = float(sensor[1] if len(sensor) > 1 and sensor[1] else SW * 9 / 16)
ASP = float(E['aspecto'][0]) / float(E['aspecto'][1])
CAM = bpy.data.objects.get('camera_4g_master')

# ---------------------------------------------------------------- catálogo (IDs de Star / REGLAS_SB_v1; universal)
COB = {'GPG': 4.5, 'PG': 2.2, 'PE': 1.2, 'PA': 0.95, 'PM': 0.70, 'PMC': 0.55, 'PP': 0.40, 'PPP': 0.28, 'GPP': 0.28, 'PD': 0.28, 'OTS': 0.70}
ESCALA = ['GPG', 'PG', 'PE', 'PA', 'PM', 'PMC', 'PP', 'PPP']
DE_SB = {'EWS': 'GPG', 'LS': 'GPG', 'WS': 'PG', 'MWS': 'PE', 'FS': 'PE', 'MLS': 'PA', 'MS': 'PM', 'MCU': 'PMC', 'CU': 'PP', 'ECU': 'PPP'}
LENTE = {'GPG': 18, 'PG': 24, 'PE': 28, 'PA': 35, 'PM': 35, 'PMC': 50, 'PP': 50, 'PPP': 85, 'GPP': 85, 'PD': 85, 'OTS': 35}
ELEV = {'NORM': 0.0, 'PIC': 30.0, 'CPIC': -14.0, 'CEN': 72.0, 'NAD': -40.0, 'DUTCH': 0.0, 'POV': 0.0}
ANG_SB = {'EYELEVEL': 'NORM', 'HIGHANGLE': 'PIC', 'LOWANGLE': 'CPIC', 'OVERHEAD': 'CEN', 'DUTCH': 'DUTCH'}
MOVS = ['STATIC', 'LOCK', 'DOLLYIN', 'DOLLYOUT', 'PAN', 'TILT', 'TRACK', 'ORBIT', 'CRANE', 'PEDESTAL', 'ZOOMIN', 'ZOOMOUT',
        'STEADICAM', 'HANDHELD', 'WHIPPAN', 'CRASHZOOM', 'TRAYECTO']
SIGUE = {'TRACK', 'ORBIT', 'CRANE', 'STEADICAM', 'DOLLYIN', 'DOLLYOUT'}   # la cámara acompaña al sujeto si se desplaza

# ---------------------------------------------------------------- reset de despejes previos (visible_camera) — nunca se borra geometría
def _channelbags(o):
    ad = o.animation_data
    if not ad or not ad.action: return []
    out = []
    for L in ad.action.layers:
        for s in L.strips:
            cb = s.channelbag(ad.action_slot) if ad.action_slot else None
            if cb: out.append(cb)
    return out
def reset_ocultos():
    n = 0
    for o in bpy.data.objects:
        if o.type != 'MESH': continue
        for cb in _channelbags(o):
            for fc in [fc for fc in cb.fcurves if fc.data_path == 'visible_camera']:
                cb.fcurves.remove(fc); n += 1
        o.visible_camera = True
    return n
N_RESET = reset_ocultos(); log('despejes previos quitados (visible_camera):', N_RESET)

# ---------------------------------------------------------------- entidades, medidas y niveles
ENTS = NV.entidades(); PJ = [e for e, v in ENTS.items() if v['tipo'] == 'personaje']
ARM = {p: bpy.data.objects[p] for p in PJ}
OBJ_ENT = {m: e for e, v in ENTS.items() for m in v['mallas']}
_med = {}
def med(pid, f):
    k = (pid, f)
    if k not in _med:
        if sc.frame_current != f: sc.frame_set(f)
        _med[k] = NV.medir_personaje(ARM[pid], bpy.context.evaluated_depsgraph_get(), ENTS[pid])
    return _med[k]
CAJA_CAB = {}
for p in PJ:
    try: CAJA_CAB[p] = ECAB.caja_cabeza(ARM[p]) if ECAB.hueso_cabeza(ARM[p]) in ARM[p].pose.bones else None   # [argon_v2] hueso de cabeza de cualquier rig
    except Exception: CAJA_CAB[p] = None
def cab_esq(p, f):
    if CAJA_CAB.get(p) is None: return None
    if sc.frame_current != f: sc.frame_set(f)
    return ECAB.esquinas(ARM[p], CAJA_CAB[p])

VIN = []
for v in CV.get('vinetas', []):
    t0 = NJ.a_numero(v['t_abs'][0], 't_abs', obligatorio=True); t1 = NJ.a_numero(v['t_abs'][1], 't_abs', obligatorio=True)
    f0 = int(round(t0 * FPS)) + 1; f1 = min(N, int(round(t1 * FPS)))
    if f0 > N: continue
    s = SBV.get(v['vineta'], {}); di = s.get('director_imagen', {})
    enc = [x.get('id') for x in di.get('en_cuadro', []) if x.get('id') in ARM]
    obj = v.get('objetivo') if v.get('objetivo') in ARM else (next((a.get('quien') for a in s.get('audio', []) or [] if a.get('quien') in ARM), None) or (enc[0] if enc else PJ[0]))
    if obj not in enc: enc = [obj] + enc
    VIN.append({"id": v['vineta'], "t": [t0, t1], "f0": f0, "f1": f1, "obj": obj, "en_cuadro": enc, "cv": v, "sb": s})
log('viñetas', len(VIN), 'personajes', len(PJ))
FR_MUESTRA = sorted({x for v in VIN for x in (v['f0'], (v['f0'] + v['f1']) // 2, v['f1'])})
NIV, INT, GRAFO = NV.clasificar(E, SB, FR_MUESTRA, sc, med, ENTS)
N0 = {e for e, d in NIV.items() if d['nivel'] == 'N0'}; N2 = {e for e, d in NIV.items() if d['nivel'] == 'N2'}; N3 = {e for e, d in NIV.items() if d['nivel'] == 'N3'}
log('niveles N0', len(N0), 'N2', len(N2), 'N3', len(N3), 'interior', [round(x, 2) for x in INT['lo']], [round(x, 2) for x in INT['hi']])
CAJA_MALLA = {}
for o in bpy.data.objects:
    if o.type == 'MESH' and OBJ_ENT.get(o.name) not in PJ and ENTS.get(OBJ_ENT.get(o.name), {}).get('tipo') == 'set':
        lo, hi = CSP.aabb_mundo(o); CAJA_MALLA[o.name] = (lo, hi)

# ---------------------------------------------------------------- eje 180° (del SB si nombra a dos personajes; si no, objetivo -> compañero más cercano)
def eje_de(V):
    ej = str((V['sb'].get('continuidad') or {}).get('eje') or '')
    for a in PJ:
        for b in PJ:
            if a != b and ej == f"{a}-{b}": return a, b, 'SB'
    o = V['obj']; fm = (V['f0'] + V['f1']) // 2; Mo = med(o, fm)
    otros = [p for p in V['en_cuadro'] if p != o and med(p, fm) is not None]
    if Mo and otros:
        b = min(otros, key=lambda p: (med(p, fm)['cabeza'] - Mo['cabeza']).length); return o, b, 'cercano'
    return None, None, 'sin_eje'
def pos2(p, f):
    M = med(p, f); return Vector((M['cabeza'].x, M['cabeza'].y)) if M else None
def lado(C, a, b, f):
    if a is None: return 0
    A2, B2 = pos2(a, f), pos2(b, f)
    if A2 is None or B2 is None or (B2 - A2).length < 1e-4: return 0
    d = B2 - A2; r = Vector((C.x, C.y)) - A2; c = d.x * r.y - d.y * r.x
    return 1 if c > 0 else -1
LADO_ESC = {}
for V in VIN:
    a, b, fu = eje_de(V); V['eje'] = (a, b, fu); fm = (V['f0'] + V['f1']) // 2
    if a is None: V['lado_escena'] = 0; continue
    k = (a, b) if a < b else (b, a)
    # el lado de la escena = hacia donde miran los personajes del cuadro (el público está delante). Se mide POR VIÑETA: si los
    # personajes se reacomodan (otro frente), el lado cambia con ellos; dentro de la viñeta y entre viñetas seguidas con la misma
    # puesta se conserva (regla 180°). Mismo orden (a, b) para el lado de la escena y el de cada cámara.
    fs = [med(p, fm)['frente'] for p in V['en_cuadro'] if med(p, fm)]
    fmed = sum(fs, Vector()) / max(1, len(fs)); Ma = med(a, fm) or med(b, fm)
    if Ma is None: V['lado_escena'] = 0; continue
    P0 = Ma['cabeza'] + fmed * 1.0
    V['lado_escena'] = lado(P0, k[0], k[1], fm) or 1; V['eje_k'] = k
    LADO_ESC.setdefault(k, []).append((V['id'], V['lado_escena']))

def nombre_corto(p):
    """nombre legible de un id de personaje (ch-<nombre>-<hash>) sin escribir nombres a mano."""
    m = re.match(r'^ch-(.+?)(?:-[0-9a-f]{4})?$', p); return (m.group(1) if m else p).replace('-', ' ')

# ---------------------------------------------------------------- cámara: pose desde (az, el, dist, lente, punto de mira)
def mirar(C, T, sx=0.0, lente=35.0, roll=0.0):
    R = CC.quitar_roll(C, CC.mirar_sin_roll(C, T), T, T, (sx, 0.0), (sx, 0.0), lente, SW, ASP)
    if abs(roll) > 1e-6: R = R @ Matrix.Rotation(math.radians(roll), 3, 'Z')
    return R
def dir_az_el(az, el):
    a, e = math.radians(az), math.radians(el)
    return Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)))
def ang_de(v): return math.degrees(math.atan2(v.y, v.x))
def tam_sujeto(M):
    return max(M['altura'], 0.6 * max(M['hi'].x - M['lo'].x, M['hi'].y - M['lo'].y)) if M['acostado'] else M['altura']
def mira_y_dist(V, plano, lente, f):
    """punto de mira y distancia por plano (cobertura de la altura real medida) o encuadre de grupo en planos abiertos."""
    o = V['obj']; M = med(o, f); H = tam_sujeto(M); cov = COB.get(plano, 0.7) * H
    if plano in ('GPG', 'PG', 'PE', 'PA'):
        T = Vector(((M['lo'].x + M['hi'].x) / 2, (M['lo'].y + M['hi'].y) / 2, M['lo'].z + 0.5 * (M['hi'].z - M['lo'].z)))
        Ms = [med(p, f) for p in V['en_cuadro']]; Ms = [x for x in Ms if x]
        if plano in ('GPG', 'PG', 'PE') and len(Ms) > 1:   # plano de grupo: se mira al CENTRO del grupo del cuadro (no solo al objetivo)
            lo = Vector((min(x['lo'].x for x in Ms), min(x['lo'].y for x in Ms), min(x['lo'].z for x in Ms)))
            hi = Vector((max(x['hi'].x for x in Ms), max(x['hi'].y for x in Ms), max(x['hi'].z for x in Ms)))
            T = (lo + hi) / 2; H = max(H, hi.z - lo.z); cov = COB.get(plano, 0.7) * H
    else:
        # planos cortos: cobertura según la CABEZA medida (personajes animados = cabeza grande), aire arriba de la coronilla
        E8 = cab_esq(o, f)   # caja REAL de la cabeza (con pelo/orejas) si el molde tiene hueso 'cabeza'
        cz = [p.z for p in E8] if E8 else ([p.z for p in M['cab']] if M.get('cab') else [])
        if cz and not M['acostado']:
            ht, hb = max(cz), min(cz); hh = max(0.04, ht - hb)
            hw = (max(max(p.x for p in E8) - min(p.x for p in E8), max(p.y for p in E8) - min(p.y for p in E8)) / ASP) if E8 else 0.0
            mult = {'PM': 2.0, 'OTS': 2.0, 'PMC': 1.6, 'PP': 1.3}.get(plano)
            if mult: cov = max(cov, hh * mult, hw * mult); T = M['ojos'].copy(); T.z = ht + 0.12 * cov - cov / 2
            else: T = M['ojos'].copy()
        else:
            T = M['ojos'] - Vector((0, 0, cov / 6.0))
        T.z = max(T.z, M['lo'].z + 0.05 * H)
    d = cov * lente / SH
    return T, max(d, 0.35 * M['altura'], 0.12), cov
def grupo(V, f, C, R, lente):
    pts = []
    for p in V['en_cuadro']:
        M = med(p, f)
        if M: pts += [M['lo'], M['hi'], Vector((M['lo'].x, M['hi'].y, M['hi'].z)), Vector((M['hi'].x, M['lo'].y, M['lo'].z))]
    return CC.encuadre_grupo(C, R, pts, lente, SW, ASP, margen=0.1) if len(pts) >= 8 else C

def punto_mira(c, f):
    """punto al que mira una cámara de Argon en el cuadro f: un personaje (ojos|pecho|centro|pies) o coordenadas."""
    pj = c.get('mira_pj')
    if pj and pj in ARM:
        M = med(pj, f)
        if M:
            k = c.get('punto') or 'ojos'
            if k == 'centro': return (M['lo'] + M['hi']) / 2
            if k == 'pies': return Vector(((M['lo'].x + M['hi'].x) / 2, (M['lo'].y + M['hi'].y) / 2, M['lo'].z + 0.05))
            return (M['pecho'] if k == 'pecho' else M['ojos']).copy()
    return Vector(c['mira_xyz']) if c.get('mira_xyz') else None
def pose_base(V, c, f):
    """pose de la cámara candidata c en el cuadro f (sin movimiento). c: plano, angulo, az_off, lente, dz.
    c['fija'] = cámara decidida por Argon: posición absoluta + punto de mira (personaje o xyz)."""
    if c.get('fija'):
        fm = (V['f0'] + V['f1']) // 2; T = punto_mira(c, f)
        if T is None: return None
        C = Vector(c['C'])
        if c.get('seguir_dueno') and c.get('dueno') in ARM:   # [cine_v1] POV/OTS: la cámara va con los ojos/hombro de su dueño
            a_, b_ = med(c['dueno'], f), med(c['dueno'], fm)
            if a_ and b_: C = C + (a_['ojos'] - b_['ojos'])
        elif c.get('seguir') and c.get('mira_pj') in ARM:     # la cámara acompaña el desplazamiento del sujeto (misma distancia)
            Tm = punto_mira(c, fm)
            if Tm is not None: C = C + Vector((T.x - Tm.x, T.y - Tm.y, 0))
        v = C - T; d = max(1e-3, v.length)
        return {"C": C, "T": T, "az": ang_de(v), "el": math.degrees(math.asin(max(-1, min(1, v.z / d)))), "d": d, "lente": c['lente'],
                "sx": 0.0, "roll": 12.0 if c.get('angulo') == 'DUTCH' else 0.0, "cov": 0.0}
    o = V['obj']; M = med(o, f)
    if M is None: return None
    fr = M['frente']
    if c['plano'] in ('GPG', 'PG', 'PE', 'PA') and len(V['en_cuadro']) > 1:
        fs = [med(p, f)['frente'] for p in V['en_cuadro'] if med(p, f)]; fr = (sum(fs, Vector()) / len(fs)); fr = fr.normalized() if fr.length > 1e-4 else M['frente']
    az = ang_de(fr) + c['az_off']; el = c['el'] if c.get('el') is not None else ELEV.get(c['angulo'], 0.0) + c.get('del_el', 0.0)
    T, d, cov = mira_y_dist(V, c['plano'], c['lente'], f)
    d *= c.get('k', 1.0)
    C = T + dir_az_el(az, el) * d
    if c.get('el') is None and c['angulo'] in ('NORM', 'DUTCH', 'POV', 'OTS') and c['plano'] not in ('GPG', 'PG'): C.z = M['ojos'].z + c.get('dz', 0.0)
    R = mirar(C, T, 0.0, c['lente'])
    if c['plano'] in ('GPG', 'PG', 'PE') and len(V['en_cuadro']) > 1:
        C2 = grupo(V, f, C, R, c['lente'])
        if (C2 - T).length > (C - T).length: C = C2; R = mirar(C, T, 0.0, c['lente'])
    # aire de mirada: el sujeto en el tercio opuesto a donde mira (solo planos de un sujeto)
    sx = 0.0
    if c['plano'] not in ('GPG', 'PG') and len(V['en_cuadro']) <= 2:
        right = R @ Vector((1, 0, 0)); sx = -0.22 if M['frente'].dot(right) > 0.2 else (0.22 if M['frente'].dot(right) < -0.2 else 0.0)
    roll = 12.0 if c['angulo'] == 'DUTCH' else 0.0
    C.z = min(max(C.z, INT['lo'][2] + 0.06), INT['hi'][2] - 0.12)
    return {"C": C, "T": T, "az": az, "el": el, "d": (C - T).length, "lente": c['lente'], "sx": sx, "roll": roll, "cov": cov}

# ---------------------------------------------------------------- movimiento (DSL ejecutable) — la pose base queda en la mitad del recorrido
def suave(s): s = max(0.0, min(1.0, s)); return s * s * (3 - 2 * s)
def pose_mov(V, base_c, mov, f, ref):
    """ref: pose base en el cuadro de referencia (mitad de la viñeta). Devuelve (C, R, lente)."""
    if base_c.get('ruta'): return pose_ruta(V, base_c, mov, f)   # [cine_v1] RETIRADA / PASE_CARAS
    mv = (mov.get('movimiento') or 'STATIC').upper(); u = max(0.0, min(1.0, float(mov.get('intensidad', 0.5) or 0.5)))
    dirn = (mov.get('direccion') or '').upper(); sg = -1.0 if dirn in ('IZQ', 'ABAJO', 'AFUERA', 'L', 'DOWN', 'OUT') else 1.0
    esp = max(0.0, float(mov.get('espera_s', 0.0) or 0.0)); f0, f1 = V['f0'], V['f1']; fe = min(f1 - 1, f0 + int(esp * FPS))
    s = (f - fe) / max(1, f1 - fe) if f > fe else 0.0
    frac = {'LENTA': 1.0, 'MEDIA': 0.6, 'RAPIDA': 0.3, 'RÁPIDA': 0.3}.get(str(mov.get('velocidad') or '').upper(), 1.0)
    s = min(1.0, s / frac)
    if mv == 'WHIPPAN': s = min(1.0, s / 0.3)
    if mv == 'CRASHZOOM': s = min(1.0, s / 0.25)
    s = suave(s); m = s - 0.5
    sigue = mv in SIGUE
    cur = pose_base(V, base_c, f) if sigue else ref
    if cur is None: cur = ref
    T = cur['T']; C = cur['C'].copy(); lente = ref['lente']; az, el, d = cur['az'], cur['el'], cur['d']
    if mv in ('STATIC', 'LOCK', 'HANDHELD'):
        C = ref['C'].copy(); T = ref['T'].copy()
        if mv == 'HANDHELD':
            t = f / FPS; a = 0.006 + 0.01 * u
            C += Vector((a * math.sin(2.1 * t * 6.28), a * math.sin(1.37 * t * 6.28 + 1), 0.7 * a * math.sin(1.73 * t * 6.28 + 2)))
    elif mv in ('DOLLYIN', 'DOLLYOUT'):
        k = 0.25 + 0.35 * u; dd = d * (1 - k * m) if mv == 'DOLLYIN' else d * (1 + k * m)
        C = T + dir_az_el(az, el) * max(dd, 0.12, float(base_c.get('d_min') or 0))   # [cine_v1] nunca más cerca que d_min
    elif mv in ('PAN', 'WHIPPAN'):
        C = ref['C'].copy(); fov = 2 * math.degrees(math.atan(SW / 2 / lente)); g = (0.15 + 0.15 * u) * fov * (2.0 if mv == 'WHIPPAN' else 1.0)
        Rz = Matrix.Rotation(math.radians(-g * m * sg), 3, 'Z')
        cur2 = pose_base(V, base_c, f)   # si el sujeto se desplaza, la panorámica lo sigue
        T = C + Rz @ ((cur2['T'] if cur2 else ref['T']) - C)
    elif mv == 'TILT':
        C = ref['C'].copy(); fov_v = 2 * math.degrees(math.atan(SH / 2 / lente)); g = (0.15 + 0.15 * u) * fov_v
        v_ = ref['T'] - C; ax = v_.cross(Vector((0, 0, 1))).normalized(); Rx = Matrix.Rotation(math.radians(g * m * sg), 3, ax); T = C + Rx @ v_
    elif mv == 'TRACK':
        right = (T - C).cross(Vector((0, 0, 1))).normalized(); L = (0.25 + 0.55 * u) * max(0.4, min(d, 2.0))
        C = C + right * (L * m * sg)
    elif mv == 'ORBIT':
        th = 15 + 35 * u; C = T + dir_az_el(az + th * m * sg, el) * d
    elif mv == 'CRANE':
        de = 8 + 22 * u; C = T + dir_az_el(az, max(-30, min(80, el + de * m * sg))) * d
    elif mv == 'PEDESTAL':
        dz = (0.15 + 0.45 * u) * max(0.3, d * 0.5) * m * sg; C = ref['C'] + Vector((0, 0, dz)); T = ref['T'] + Vector((0, 0, dz))
    elif mv in ('ZOOMIN', 'ZOOMOUT', 'CRASHZOOM'):
        C = ref['C'].copy(); T = ref['T'].copy(); z = 1.25 + 0.5 * u
        lente = ref['lente'] * (z ** (m if mv != 'ZOOMOUT' else -m))
    elif mv == 'STEADICAM':
        dd = max(d * (1 - (0.1 + 0.2 * u) * m), float(base_c.get('d_min') or 0)); C = T + dir_az_el(az + 6 * m * sg, el) * dd
    C.z = min(max(C.z, INT['lo'][2] + 0.06), INT['hi'][2] - 0.12)
    return C, mirar(C, T, ref['sx'], lente, ref['roll']), lente, T

# ---------------------------------------------------------------- validación 3D de una pose en el cuadro actual
N3_MALLAS = set(NV.mallas_de_nivel(NIV, 'N3')); N2_MALLAS = set(NV.mallas_de_nivel(NIV, 'N2')); N0_MALLAS = set(NV.mallas_de_nivel(NIV, 'N0'))
def n2_recortables(C):
    """muros (y lo pegado a ellos) del lado por el que la cámara está FUERA del recinto: se recortan solo en ese cuadro."""
    fuera = NV.lado_fuera(C, INT, 0.0)
    if not fuera: return set()
    out = set()
    for e in N2:
        lo, hi = NIV[e]['lo'], NIV[e]['hi']
        for a, sgn in fuera:
            if a == 2 and lo[2] >= INT['hi'][2] - 0.05: out.update(NIV[e]['mallas'])
            elif a < 2 and ((sgn < 0 and hi[a] <= INT['lo'][a] + 0.25) or (sgn > 0 and lo[a] >= INT['hi'][a] - 0.25)): out.update(NIV[e]['mallas'])
    return out
def holgura(C, dg, recort, f):
    """None si la cámara está libre; si no, (entidad, nivel, motivo)."""
    m = UMB['holgura_m']
    if C.z < INT['lo'][2] + 0.04: return ('piso', 'N0', 'bajo el piso')
    if INT['tiene_techo'] and C.z > INT['hi'][2] - 0.05 and not NV.lado_fuera(C, INT): return ('techo', 'N2', 'pegada al techo')
    for n, (lo, hi) in CAJA_MALLA.items():
        if not all(lo[i] - m <= C[i] <= hi[i] + m for i in range(3)): continue
        o = bpy.data.objects[n]
        if o.hide_render: continue
        ok, mot, dd = CSP.dentro_de(o, C, dg, m)
        if ok: e = OBJ_ENT.get(n, n); return (e, NIV.get(e, {}).get('nivel'), mot)
    for p in PJ:
        M = med(p, f)
        if M and all(M['lo'][i] - 0.04 <= C[i] <= M['hi'][i] + 0.04 for i in range(3)): return (p, 'N0', 'dentro de un personaje')
    return None
def rayo(dg, C, P, propias, ignorar, pasados=None):
    """('libre'|'propio'|'tapado', quien). Atraviesa lo ignorable (N3 / N2 recortado) y lo anota en 'pasados'."""
    d = P - C; L = d.length
    if L < 1e-6: return 'libre', None
    d /= L; O = C.copy()
    for _ in range(30):
        rem = L - (O - C).length
        if rem <= 0.02: return 'libre', None
        hit, loc, nor, idx, ob, mx = sc.ray_cast(dg, O, d, distance=rem)
        if not hit: return 'libre', None
        if (loc - C).length >= L - 0.03: return 'libre', None
        n = ob.name
        if n in propias: return 'propio', None
        if n in ignorar or not bpy.data.objects.get(n, ob).visible_camera:
            if pasados is not None and n in ignorar: pasados.add(n)
            O = loc + d * 1e-4; continue
        return 'tapado', n
    return 'libre', None
def medir_pose(V, C, R, lente, f, ref_T=None, plano=None):
    """métricas en el cuadro f (escena ya en f)."""
    dg = bpy.context.evaluated_depsgraph_get(); o = V['obj']; M = med(o, f)
    rec = n2_recortables(C); r = {"f": f}
    if M is None:
        return {"f": f, "choque": None, "vis": 0.0, "vis_cab": None, "vis_cue": None, "cabeza_en_cuadro": False, "oclusor": None,
                "oclusor_nivel": None, "tapan": {}, "n3_que_tapan": [], "n2_recortados": sorted(rec), "lado": 0, "alto_cabeza": 0.0}
    h = holgura(C, dg, rec, f); r['choque'] = h
    prop = set(ENTS[o]['mallas'])
    ign = N3_MALLAS | rec
    vc = tc = vb = tb = 0; tapa = {}; pas = set()
    for es_c, P in [(True, p) for p in M['cab']] + [(False, p) for p in M['cue']]:
        pr = CC.proyectar(C, R, P, lente, SW, ASP)
        if pr is None or abs(pr[0]) > 1 or abs(pr[1]) > 1: continue
        est, quien = rayo(dg, C, P, prop, ign, pas)
        if est == 'propio': continue
        if est == 'libre':
            if es_c: vc += 1
            else: vb += 1
        else:
            if es_c: tc += 1
            else: tb += 1
            e = OBJ_ENT.get(quien, quien); tapa[e] = tapa.get(e, 0) + 1
    r['vis_cab'] = vc / (vc + tc) if vc + tc else None; r['vis_cue'] = vb / (vb + tb) if vb + tb else None
    w = 2 * (vc + tc) + (vb + tb); r['vis'] = (2 * vc + vb) / w if w else 0.0
    if vc + tc == 0: r['vis'] = 0.0
    E8 = cab_esq(o, f)
    if plano in ('PP', 'PPP', 'GPP', 'PD'):   # PP/PPP/GPP/PD: el plano cerrado PUEDE cortar la coronilla; se exige ojos (y cara) en cuadro
        po = CC.proyectar(C, R, M['ojos'], lente, SW, ASP); ok = po is not None and abs(po[0]) <= 0.9 and abs(po[1]) <= 0.85
    elif E8:
        ok = all((lambda p: p is not None and abs(p[0]) <= 0.97 and abs(p[1]) <= 0.92)(CC.proyectar(C, R, e8, lente, SW, ASP)) for e8 in E8)
    else:
        p = CC.proyectar(C, R, M['cabeza'], lente, SW, ASP); ok = p is not None and abs(p[0]) <= 0.95 and abs(p[1]) <= 0.9
    r['cabeza_en_cuadro'] = bool(ok)
    r['oclusor'] = max(tapa, key=tapa.get) if tapa else None; r['oclusor_nivel'] = NIV.get(r['oclusor'], {}).get('nivel') if r['oclusor'] else None
    r['tapan'] = tapa; r['n3_que_tapan'] = sorted(n for n in pas if n in N3_MALLAS); r['n2_recortados'] = sorted(rec)
    k_ = V.get('eje_k')   # MISMO orden (a, b) con que se fijó el lado de la escena
    r['lado'] = lado(C, k_[0], k_[1], f) if k_ else 0
    # tamaño proyectado de la cabeza (para «movimiento que se note»)
    if E8:
        ps = [CC.proyectar(C, R, e8, lente, SW, ASP) for e8 in E8]
        ps = [p for p in ps if p]; r['alto_cabeza'] = (max(p[1] for p in ps) - min(p[1] for p in ps)) if ps else 0.0
    else: r['alto_cabeza'] = 0.0
    return r

def evaluar(V, intentos, frames):
    """evalúa varios intentos (candidata + movimiento) recorriendo los cuadros UNA vez. Devuelve métricas por intento."""
    res = [{"poses": {}, "m": []} for _ in intentos]
    fm = (V['f0'] + V['f1']) // 2
    refs = [pose_base(V, it['c'], fm) for it in intentos]
    for f in frames:
        sc.frame_set(f)
        for i, it in enumerate(intentos):
            if refs[i] is None: continue
            C, R, lente, T = pose_mov(V, it['c'], it['mov'], f, refs[i])
            res[i]['poses'][f] = (C, R, lente)
            res[i]['m'].append(medir_pose(V, C, R, lente, f, plano=it['c']['plano']))
    return refs, res

def veredicto(V, it, ref, R_, prev):
    m = R_['m']
    if not m or ref is None: return {"ok": False, "fallas": ["sin pose"]}
    fallas = []; notas = []
    ch = [x['choque'] for x in m if x['choque']]
    if ch: fallas.append(f"cámara dentro/pegada a {ch[0][0]} ({ch[0][1]}, {ch[0][2]}) en {len(ch)}/{len(m)} cuadros")
    vis = [x['vis'] for x in m]; vm = sum(vis) / len(vis)
    if vm < UMB['vis_min']: fallas.append(f"protagonista visible {vm:.0%} < {UMB['vis_min']:.0%} (tapa {m[[x['vis'] for x in m].index(min(vis))]['oclusor']})")
    if min(vis) < UMB['vis_frame_min']: fallas.append(f"un cuadro con protagonista visible {min(vis):.0%}")
    ce = sum(1 for x in m if x['cabeza_en_cuadro']) / len(m)
    if ce < UMB['cabeza_en_cuadro_min']: fallas.append(f"cabeza en cuadro {ce:.0%}")
    ls = V.get('lado_escena', 0)
    if ls and (it['mov'].get('movimiento') or '').upper() != 'ORBIT':
        mal = sum(1 for x in m if x['lado'] and x['lado'] != ls)
        if mal and V.get('aviso_eje') and mal == sum(1 for x in m if x['lado']):
            notas.append('toda la toma del otro lado del eje 180°: no existe cámara válida del lado de la escena (cruce justificado)')
        elif mal: notas.append(f"cruza el eje 180° en {mal}/{len(m)} cuadros")
    elif ls:
        if m[0]['lado'] and m[0]['lado'] != ls: notas.append("la órbita empieza del otro lado del eje 180°")
    mv = (it['mov'].get('movimiento') or 'STATIC').upper(); fs = sorted(R_['poses'])
    C0, Rr0, l0 = R_['poses'][fs[0]]; C1, Rr1, l1 = R_['poses'][fs[-1]]
    desp = max((R_['poses'][f][0] - C0).length for f in fs)
    giro = math.degrees(math.acos(max(-1, min(1, (Rr0 @ Vector((0, 0, -1))).dot(Rr1 @ Vector((0, 0, -1)))))))
    a0 = m[0]['alto_cabeza'] or 1e-6; a1 = m[-1]['alto_cabeza'] or 1e-6; esc = abs(a1 / a0 - 1) if a0 > 1e-5 else 0.0
    mov_info = {"desplazamiento_m": round(desp, 3), "giro_deg": round(giro, 1), "cambio_escala": round(esc, 3), "zoom": round(l1 / l0, 3)}
    if mv not in ('STATIC', 'LOCK'):
        if not (desp >= UMB['mov_desplaz_m'] or esc >= UMB['mov_escala'] or giro >= UMB['mov_giro_deg'] or abs(l1 / l0 - 1) >= UMB['mov_escala']):
            notas.append(f"movimiento casi no se nota (desplaz {desp:.2f} m, giro {giro:.1f}°, escala {esc:.0%})")
    if prev and prev.get('obj') == V['obj'] and prev.get('C_fin') is not None and med(V['obj'], V['f0']):
        S = med(V['obj'], V['f0'])['cabeza']; a = (prev['C_fin'] - S).normalized(); b = (C0 - S).normalized()
        dang = math.degrees(math.acos(max(-1, min(1, a.dot(b)))))
        s0 = prev['escala_fin']; s1 = l0 / max(1e-3, (C0 - S).length); rs = max(s0, s1) / max(1e-6, min(s0, s1))
        if dang < UMB['regla30_deg'] and rs < UMB['regla30_escala']: notas.append(f"regla 30°: {dang:.0f}° y escala x{rs:.2f} respecto a la viñeta anterior")
    return {"ok": not fallas, "fallas": fallas, "notas": notas, "vis_media": round(vm, 3), "vis_min": round(min(vis), 3), "cabeza_en_cuadro": round(ce, 3),
            "mov": mov_info, "oclusores_n0": sorted({x['oclusor'] for x in m if x['oclusor'] and x['oclusor_nivel'] == 'N0'}),
            "n3_a_ocultar": sorted({n for x in m for n in x['n3_que_tapan']}), "n2_recortados": sorted({n for x in m for n in x['n2_recortados']})}

# ---------------------------------------------------------------- candidatas por viñeta
def plano_sb(V):
    kf = V['cv'].get('keyframes') or [{}]; p = (kf[0].get('plano') or (V['sb'].get('director_imagen') or {}).get('plano') or 'MS').upper()
    return DE_SB.get(p, p if p in COB else 'PM')
def angulo_sb(V): return ANG_SB.get((V['cv'].get('angulo') or (V['sb'].get('director_imagen') or {}).get('angulo') or 'EYELEVEL').upper(), 'NORM')
def mov_sb(V):
    for s in V['cv'].get('segmentos', []):
        mv = (s.get('movimiento') or 'STATIC').upper()
        if mv not in ('STATIC', 'LOCK'): return mv
    return 'STATIC'
def paso_plano(p, k):
    if p not in ESCALA: return p
    i = max(0, min(len(ESCALA) - 1, ESCALA.index(p) + k)); return ESCALA[i]
def candidatas(V):
    p0 = plano_sb(V); a0 = angulo_sb(V)
    crudas = []
    for pl in dict.fromkeys([p0, paso_plano(p0, 1), paso_plano(p0, -1)]):
        for an in dict.fromkeys([a0, 'NORM', 'PIC', 'CEN' if pl in ('GPG', 'PG', 'PE', 'PA', 'PM') else 'CPIC']):
            for off in (0, 30, -30, 55, -55, 80, -80):
                crudas.append({"plano": pl, "angulo": an, "az_off": off, "lente": LENTE.get(pl, 35)})
    fm = (V['f0'] + V['f1']) // 2; sc.frame_set(fm)
    ev = []; rech = {}; cruzan = []
    def _r(k): rech[k] = rech.get(k, 0) + 1
    def _ang(el): return 'CEN' if el >= 55 else ('PIC' if el >= 12 else ('CPIC' if el <= -8 else 'NORM'))
    def rescate():   # el sujeto queda tapado desde las cámaras «de manual»: búsqueda en anillo (todo azimut, varias alturas y distancias)
        out = []
        for pl in dict.fromkeys([p0, paso_plano(p0, 1)]):
            for off in range(-150, 181, 30):
                for el in (-12, 4, 20, 38, 58):
                    for k in (0.8, 1.25):
                        out.append({"plano": pl, "angulo": _ang(el), "az_off": off, "lente": LENTE.get(pl, 35), "el": el, "k": k, "rescate": True})
        return out
    pend = list(crudas); hecho_rescate = False
    while True:
      if not pend:
          if not hecho_rescate and (max([x[3]['vis'] for x in ev] or [0]) < UMB['vis_min']):
              hecho_rescate = True; extra = rescate(); crudas += extra; pend += extra
          else: break
      c = pend.pop(0)
      if True:
            P = pose_base(V, c, fm)
            if P is None: _r('sin_pose'); continue
            R = mirar(P['C'], P['T'], P['sx'], c['lente'], P['roll'])
            m = medir_pose(V, P['C'], R, c['lente'], fm, plano=c['plano'])
            if m['choque']: _r('choque:' + str(m['choque'])[:40]); continue
            if not m['cabeza_en_cuadro']: _r('cabeza_fuera'); continue
            cruza = bool(V.get('lado_escena') and m['lado'] and m['lado'] != V['lado_escena'])
            if cruza: _r('lado_eje'); cruzan.append((m['vis'] - 0.3, c, P, m)); continue
            sc_ = (m['vis'] - 0.04 * abs(c['az_off']) / 30 - (0.05 if c['plano'] != p0 else 0) - (0.03 if c['angulo'] != a0 else 0)
                   - (0.10 if c['angulo'] in ('CEN', 'NAD') and a0 not in ('CEN', 'NAD') else 0))
            ev.append((sc_, c, P, m))
    if len(ev) < 2 and cruzan:   # sin cámaras de este lado del eje: se ofrecen las del otro lado, marcadas (cruce justificado)
        for x in cruzan: x[3]['cruza_eje'] = True
        ev += cruzan; V['aviso_eje'] = 'sin candidatas del lado del eje: se ofrecen cámaras que cruzan (marcadas cruza_eje)'
    ev.sort(key=lambda x: -x[0]); el = []
    for s_, c, P, m in ev:
        if any(c['plano'] == e[1]['plano'] and c['angulo'] == e[1]['angulo'] and abs(c['az_off'] - e[1]['az_off']) < 25 for e in el): continue
        el.append((s_, c, P, m))
        if len(el) >= (2 * A.max_candidatas if A.v2 else A.max_candidatas): break   # [argon_v2] el doble: la re-medición elige con variedad
    out = []
    for i, (s_, c, P, m) in enumerate(el):
        out.append(dict(c, id=f"C{i + 1}", score=round(s_, 3), pos=[round(x, 2) for x in P['C']], mira=[round(x, 2) for x in P['T']],
                        dist_m=round(P['d'], 2), az_deg=round(P['az'], 1), el_deg=round(P['el'], 1),
                        vis_mitad=round(m['vis'], 3), oclusor=m['oclusor'], oclusor_nivel=m['oclusor_nivel'],
                        fuera_recinto=bool(NV.lado_fuera(P['C'], INT)), n3_tapan=[OBJ_ENT.get(x, x) for x in m['n3_que_tapan']][:6],
                        cruza_eje=bool(m.get('cruza_eje')), rescate=bool(c.get('rescate'))))
    V['rechazos'] = dict(sorted(rech.items(), key=lambda x: -x[1])[:12])
    return out, len(crudas), len(ev)

def ocultar_temporal(nombres):
    prev = {}
    for n in nombres:
        o = bpy.data.objects.get(n)
        if o is not None: prev[n] = o.visible_camera; o.visible_camera = False
    return prev
def restaurar(prev):
    for n, v in prev.items(): bpy.data.objects[n].visible_camera = v

# ================================================================= MODO PAQUETE
def modo_paquete():
    t0 = time.time(); paq = {"contrato": "sb3d_paquete_v1", "corrida": COR, "escena": E.get('escena'), "fps": FPS, "N": N,
                             "aspecto": E['aspecto'], "sensor_mm": [SW, SH], "despejes_previos_quitados": N_RESET,
                             "interior": {"lo": [round(x, 2) for x in INT['lo']], "hi": [round(x, 2) for x in INT['hi']], "tiene_techo": INT['tiene_techo']},
                             "umbrales": UMB}
    censo = {}
    for e, d in NIV.items():
        x = {"nivel": d['nivel'], "tipo": d['tipo'], "por_que": d['motivo'][:2]}
        if d['nivel'] in ('N0',) or d['tipo'] != 'set': x.update(caja_min=d['lo'], caja_max=d['hi'])
        if d['portador']: x['portador'] = d['portador']
        censo[e] = x
    for p in PJ:
        porv = {}
        for V in VIN:
            M = med(p, (V['f0'] + V['f1']) // 2)
            if M: porv[V['id']] = {"base": [round(M['lo'].x / 2 + M['hi'].x / 2, 2), round(M['lo'].y / 2 + M['hi'].y / 2, 2), round(M['lo'].z, 2)],
                                   "altura_m": round(M['altura'], 3), "ojos": [round(v, 2) for v in M['ojos']], "pecho": [round(v, 2) for v in M['pecho']],
                                   "mira_hacia_deg": round(ang_de(M['frente']), 0), "acostado": M['acostado']}
        censo[p]['por_vineta'] = porv
    paq['censo'] = censo; paq['grafo_soporte'] = GRAFO
    paq['niveles'] = {k: sorted(e for e, d in NIV.items() if d['nivel'] == k) for k in ('N0', 'N2', 'N3')}
    vinetas = []; mini = []
    for V in VIN:
        if CINE: cands, ncr, nval = candidatas_cine(V)   # [cine_v1] familias de Ricardo (ya validadas en toda la viñeta)
        else:
            cands, ncr, nval = candidatas(V)
            if A.v2: cands = validar_candidatas(V, cands)   # [argon_v2] cada candidata medida en TODA la viñeta; solo se ofrecen las que pasan
        V['cands'] = cands
        s = V['sb']; di = s.get('director_imagen', {})
        vinetas.append({"id": V['id'], "t": V['t'], "cuadros": [V['f0'], V['f1']], "objetivo": V['obj'], "en_cuadro": V['en_cuadro'],
                        "objetos_sb": [x.get('nombre') for x in di.get('objetos', [])], "intencion": s.get('intencion_narrativa'),
                        "accion": s.get('beats_visuales'), "dialogo": [f"{a.get('quien')}: {a.get('texto')}" for a in s.get('audio', []) or []],
                        "emocion": (s.get('justificacion') or {}).get('emocion_buscada'), "ritmo_s": (s.get('ritmo') or {}).get('duracion_s'),
                        "sb_original": {"plano": plano_sb(V), "angulo": angulo_sb(V), "movimiento": (s.get('director_camara') or {}).get('dsl_movimiento')},
                        "eje_180": {"a": V['eje'][0], "b": V['eje'][1], "fuente": V['eje'][2], "lado_escena": V.get('lado_escena')},
                        "candidatas": cands, "crudas_probadas": ncr, "crudas_validas": nval, "rechazos": V.get('rechazos'), "aviso_eje": V.get('aviso_eje'),
                        "descartadas_3d": V.get('descartadas'), "rescate": V.get('rescate'), "sin_candidata_valida": bool(A.v2 and not cands),
                        "disparadores": V.get('disparadores'), "familias_activas": V.get('familias_activas'), "beats_tabla": V.get('tabla_reglas'), "tabla_specs": V.get('tabla_specs'),
                        "sb_tabla": {k: (V['sb'].get('camara_tabla') or {}).get(k) for k in ('beat', 'plano', 'angulo', 'colocacion', 'movimiento', 'reglas_aplicadas')} if V['sb'].get('camara_tabla') else None})
        log('candidatas', V['id'], len(cands), 'de', ncr, 'validas', nval, V.get('rechazos'))
    paq['vinetas'] = vinetas
    if A.v2: paq['contrato'] = 'sb3d_paquete_v2'
    if CINE: paq['cine'] = {"familias": FAM_PATH, "tabla_decision": TABLA_PATH, "patron": FAM.get('patron'), "distancia": FAM.get('distancia')}
    if A.stills:
        try: paq['stills'] = stills_candidatas()
        except Exception as ex: paq['stills'] = {"error": repr(ex), "traceback": traceback.format_exc()[-1500:]}; log('stills ERROR', ex)
    # miniaturas Workbench (inicio y fin de cada candidata) + hojas de contacto + planta
    if A.miniaturas:
        rx, ry = map(int, A.res_min.split('x'))
        sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'MATERIAL'
        sc.display.shading.show_shadows = True
        sc.render.resolution_x, sc.render.resolution_y = rx, ry; sc.render.resolution_percentage = 100
        sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
        r = sc.render
        for k in dir(r):
            if k.startswith('use_stamp_') and k != 'use_stamp_note':
                try: setattr(r, k, False)
                except Exception: pass
        try: r.use_stamp = True; r.use_stamp_note = True; r.stamp_font_size = 13
        except Exception: pass
        cd = bpy.data.cameras.new('SB3D_cand'); cc = bpy.data.objects.new('SB3D_cand', cd); sc.collection.objects.link(cc)
        cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = SW; cd.clip_start = 0.02; cd.clip_end = 60; cam_prev = sc.camera; sc.camera = cc
        md = os.path.join(SAL, 'miniaturas'); os.makedirs(md, exist_ok=True)
        for V in VIN:
            for c in V['cands']:
                for tag, f in (('ini', V['f0']), ('fin', V['f1'])):
                    sc.frame_set(f); P = pose_base(V, c, f)
                    if P is None: continue
                    R = mirar(P['C'], P['T'], P['sx'], c['lente'], P['roll'])
                    m = medir_pose(V, P['C'], R, c['lente'], f, plano=c['plano'])
                    cc.matrix_world = Matrix.Translation(P['C']) @ R.to_4x4(); cd.lens = c['lente']
                    pv = ocultar_temporal(set(m['n3_que_tapan']) | set(m['n2_recortados']))
                    r.stamp_note_text = f"{V['id']} {c['id']} {tag} {c['plano']} {c['angulo']} az{c['az_off']:+d} {c['lente']}mm vis{m['vis']:.0%}"
                    fp = os.path.join(md, f"{V['id']}_{c['id']}_{tag}.png"); r.filepath = fp
                    bpy.ops.render.render(write_still=True); restaurar(pv); mini.append((V['id'], c['id'], tag, fp))
        # planta (cenital ortográfica del recinto, sin techo)
        cd2 = bpy.data.cameras.new('SB3D_planta'); cp = bpy.data.objects.new('SB3D_planta', cd2); sc.collection.objects.link(cp)
        lo, hi = INT['lo'], INT['hi']; w = max(0.5, hi[0] - lo[0]); h = max(0.5, hi[1] - lo[1])
        # cámara cenital DEBAJO del techo (y se ocultan solo en esta vista las mallas a la altura del techo): ve el cuarto por dentro
        cd2.type = 'ORTHO'; cd2.ortho_scale = max(w, h) * 1.08; cp.location = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, hi[2] - 0.04); cp.rotation_euler = (0, 0, 0)
        cd2.clip_start = 0.01; cd2.clip_end = hi[2] + 5
        sc.camera = cp; sc.render.resolution_x = 1024; sc.render.resolution_y = int(1024 * min(1.0, h / w)) if w >= h else 1024
        if h > w: sc.render.resolution_x = int(1024 * w / h)
        techo = [m for e in NIV for m in NIV[e]['mallas'] if NIV[e]['nivel'] != 'N0' and NIV[e]['lo'][2] > INT['hi'][2] - 0.3]
        pv = ocultar_temporal(techo); sc.frame_set(VIN[0]['f0'] if VIN else 1)
        r.stamp_note_text = f"PLANTA: x→derecha [{lo[0]:.1f},{hi[0]:.1f}] m · y↑arriba [{lo[1]:.1f},{hi[1]:.1f}] m"
        r.filepath = os.path.join(SAL, 'planta.png'); bpy.ops.render.render(write_still=True); restaurar(pv)
        sc.camera = cam_prev
        bpy.data.objects.remove(cc, do_unlink=True); bpy.data.objects.remove(cp, do_unlink=True)
        hojas = componer_hojas(mini, rx, ry)
        paq['hojas_contacto'] = hojas; paq['planta'] = 'planta.png'
        try: paq['planta_jpg'] = png_a_jpg(os.path.join(SAL, 'planta.png'), os.path.join(SAL, 'planta.jpg'))
        except Exception as ex: log('planta jpg', ex)
        paq['miniaturas'] = len(mini)
    paq['segundos'] = round(time.time() - t0, 1)
    json.dump(paq, open(os.path.join(SAL, 'paquete.json'), 'w'), indent=1, ensure_ascii=False, default=str)
    log('PAQUETE listo', os.path.join(SAL, 'paquete.json'), 'miniaturas', len(mini))
    print('RESULT_SB3D_PAQUETE', json.dumps({"ok": True, "vinetas": len(VIN), "miniaturas": len(mini), "s": paq['segundos']}))

def _px(path):
    im = bpy.data.images.load(path); w, h = im.size; a = np.empty(w * h * 4, dtype=np.float32); im.pixels.foreach_get(a)
    bpy.data.images.remove(im); return a.reshape(h, w, 4)
def _guardar(arr, path, fmt='JPEG'):
    h, w = arr.shape[:2]; im = bpy.data.images.new('SB3D_tmp', w, h, alpha=False)
    im.pixels.foreach_set(arr.astype(np.float32).ravel()); im.filepath_raw = path; im.file_format = fmt
    try: im.save(filepath=path, quality=88)
    except TypeError: im.save()
    bpy.data.images.remove(im); return os.path.basename(path)
def png_a_jpg(src, dst): return _guardar(_px(src), dst)
def componer_hojas(mini, rx, ry):
    """hojas de 6 columnas (candidatas) x 6 filas (3 viñetas × inicio/fin) de 384x216 → JPEG."""
    porv = {}
    for v, c, tag, fp in mini: porv.setdefault(v, {})[(c, tag)] = fp
    vids = [V['id'] for V in VIN if V['id'] in porv]; hojas = []; G = 2
    for i in range(0, len(vids), 3):
        grupo_v = vids[i:i + 3]; H = 6 * ry + G * 7; W = 6 * rx + G * 7
        S = np.full((H, W, 4), 0.08, dtype=np.float32); S[..., 3] = 1
        for j, v in enumerate(grupo_v):
            cs = [c['id'] for V in VIN if V['id'] == v for c in V['cands']]
            for k, cid in enumerate(cs[:6]):
                for t, tag in enumerate(('ini', 'fin')):
                    fp = porv[v].get((cid, tag))
                    if not fp or not os.path.exists(fp): continue
                    px = _px(fp); fila = j * 2 + t; y0 = H - G - (fila + 1) * (ry + G) + G; x0 = G + k * (rx + G)
                    S[y0:y0 + px.shape[0], x0:x0 + px.shape[1], :] = px[:, :, :4]
        hojas.append(_guardar(S, os.path.join(SAL, f"hoja_contacto_{len(hojas) + 1:02d}.jpg")))
    return hojas

# ================================================================= MODO VIDEO (t1077u): video de revisión barato para Argon
def modo_video():
    """Workbench a baja resolución de TODA la escena animada: PLANTA (cenital, bajo el techo) + VISTA AMPLIA, lado a lado, con el
    nombre de cada personaje sobre su cabeza, marcas de coordenadas en el piso y contador cuadro/segundo/viñeta. Solo en esta
    sesión (no se guarda el .blend). Salida: sb3d/revision_argon.mp4 (+ planta_rev.jpg)."""
    import subprocess
    t0 = time.time(); rx, ry = map(int, A.res_video.split('x')); paso = max(1, int(round(FPS / A.fps_video)))
    sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'MATERIAL'
    sc.display.shading.show_shadows = False   # CPU: sin sombras ni cavidad (lentas); el contorno + colores por objeto dan el contraste
    for k_, v_ in (('show_object_outline', True), ('show_cavity', False), ('object_outline_color', (0, 0, 0))):
        try: setattr(sc.display.shading, k_, v_)
        except Exception: pass
    sc.render.resolution_x, sc.render.resolution_y = rx, ry; sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
    r = sc.render
    for k in dir(r):
        if k.startswith('use_stamp_') and k != 'use_stamp_note':
            try: setattr(r, k, False)
            except Exception: pass
    try: r.use_stamp = True; r.use_stamp_note = True; r.stamp_font_size = 14
    except Exception: pass
    lo, hi = INT['lo'], INT['hi']; cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2; w = hi[0] - lo[0]; h = hi[1] - lo[1]
    # material de rótulos (amarillo) y textos
    mt = bpy.data.materials.new('REV_rotulo'); mt.diffuse_color = (1.0, 0.85, 0.05, 1.0)
    mt2 = bpy.data.materials.new('REV_coord'); mt2.diffuse_color = (1.0, 0.25, 0.25, 1.0)
    def texto(nombre, cuerpo, tam, mat):
        cu = bpy.data.curves.new(nombre, 'FONT'); cu.body = cuerpo; cu.size = tam; cu.align_x = 'CENTER'; cu.extrude = 0.005
        ob = bpy.data.objects.new(nombre, cu); sc.collection.objects.link(ob); ob.data.materials.append(mat); ob.show_in_front = True; return ob
    corto = {p: nombre_corto(p) for p in PJ}   # [argon_v2] antes split('-')[1] cortaba nombres compuestos
    rot = {p: texto(f'REV_lbl_{p}', corto[p], 0.22, mt) for p in PJ}
    marcas = []
    mt3 = bpy.data.materials.new('REV_mueble'); mt3.diffuse_color = (0.1, 0.9, 1.0, 1.0)
    for e, d in NIV.items():   # rótulos de muebles/objetos de historia (N0/N1 que no son personajes) para que Argon los ubique
        if d['nivel'] in ('N0', 'N1') and e not in ARM and d.get('tipo') != 'personaje' and d.get('lo') is not None:
            l_, h_ = d['lo'], d['hi']
            if (h_[0] - l_[0]) > 0.6 * w and (h_[1] - l_[1]) > 0.6 * h: continue      # piso/alfombra enorme: no rotular
            nm = NV.base_nombre(e).replace('obj-', '').replace('amb-esc-', '')[:18]
            ob = texto(f'REV_obj_{e}'[:60], nm, 0.12, mt3); ob.location = ((l_[0] + h_[0]) / 2, (l_[1] + h_[1]) / 2, h_[2] + 0.03); marcas.append(ob)
    for x in (lo[0], cx, hi[0]):
        for y in (lo[1], cy, hi[1]):
            ob = texto(f'REV_xy_{x:.1f}_{y:.1f}', f"({x:.1f},{y:.1f})", 0.11, mt2); ob.location = (x + (0.25 if x == lo[0] else (-0.25 if x == hi[0] else 0)), y + (0.08 if y == lo[1] else (-0.15 if y == hi[1] else 0)), lo[2] + 0.02); marcas.append(ob)
    # cámaras
    cdp = bpy.data.cameras.new('REV_planta'); cp = bpy.data.objects.new('REV_planta', cdp); sc.collection.objects.link(cp)
    cdp.type = 'ORTHO'; cdp.ortho_scale = max(w * 1.06, h * 1.06 * rx / ry); cp.location = (cx, cy, hi[2] - 0.04); cp.rotation_euler = (0, 0, 0)
    cdp.clip_start = 0.01; cdp.clip_end = hi[2] + 5
    cda = bpy.data.cameras.new('REV_amplia'); ca = bpy.data.objects.new('REV_amplia', cda); sc.collection.objects.link(ca)
    cda.lens = 13; cda.sensor_width = SW; cda.clip_start = 0.05; ca.location = (cx, lo[1] + 0.06, hi[2] - 0.12)   # DENTRO, borde alto del frente
    dv = Vector((cx, cy + 0.1 * h, 0.4)) - ca.location; ca.rotation_euler = dv.to_track_quat('-Z', 'Y').to_euler()
    techo = set(); frente = set()
    for e in NIV:                       # por MALLA (una entidad puede agrupar varios muros). Solo vista de revisión: no se guarda.
        if e in ARM: continue
        for m in NIV[e]['mallas']:
            ob = bpy.data.objects.get(m)
            if ob is None or ob.type != 'MESH': continue
            l_, h_ = CSP.aabb_mundo(ob)
            if l_[2] > hi[2] - 0.3 and NIV[e]['nivel'] != 'N0': techo.add(m)
            elif h_[1] < lo[1] + 0.12 * h and h_[2] > 0.5: frente.add(m)     # mueble alto pegado al frente: tapa la vista amplia
    dvid = os.path.join(SAL, 'video_rev'); os.makedirs(dvid, exist_ok=True)
    def vin_de(f): return next((V['id'] for V in VIN if V['f0'] <= f <= V['f1']), '-')
    n = 0; frs = list(range(1, N + 1, paso))
    for i, f in enumerate(frs):
        sc.frame_set(f)
        for p, ob in rot.items():
            M = med(p, f)
            if M is None: ob.hide_render = True; continue
            ob.hide_render = False; ob.location = (M['cabeza'].x, M['cabeza'].y, M['hi'].z + 0.12)
        nota = f"cuadro {f}/{N}  t={(f - 1) / FPS:5.2f}s  viñeta {vin_de(f)}"
        for vista, cam_, ocultos in (('planta', cp, techo), ('amplia', ca, techo | frente)):
            for ob in list(rot.values()) + marcas: ob.rotation_euler = (0, 0, 0) if vista == 'planta' else (math.radians(90), 0, 0)
            pv = ocultar_temporal(ocultos); sc.camera = cam_
            sc.display.shading.color_type = 'RANDOM' if vista == 'planta' else 'MATERIAL'   # planta: un color por objeto (contraste)
            r.stamp_note_text = f"{'PLANTA (x→der, y↑)' if vista == 'planta' else 'VISTA AMPLIA (desde y<0)'}  {nota}"
            r.filepath = os.path.join(dvid, f"{vista}_{i:05d}.png"); bpy.ops.render.render(write_still=True); restaurar(pv)
        n += 1
        if i == len(frs) // 2:
            try: png_a_jpg(os.path.join(dvid, f"planta_{i:05d}.png"), os.path.join(SAL, 'planta_rev.jpg'))
            except Exception as ex: log('planta_rev', ex)
    ff = os.environ.get('FFMPEG') or 'ffmpeg'; out = os.path.join(SAL, 'revision_argon.mp4')
    cmd = [ff, '-y', '-loglevel', 'error', '-framerate', str(FPS / paso), '-i', os.path.join(dvid, 'planta_%05d.png'), '-framerate', str(FPS / paso),
           '-i', os.path.join(dvid, 'amplia_%05d.png'), '-filter_complex', 'hstack=inputs=2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '30', out]
    rr = subprocess.run(cmd, capture_output=True, text=True)
    info = {"ok": rr.returncode == 0 and os.path.exists(out), "video": out, "cuadros": n, "fps_video": FPS / paso, "res": f"{2 * rx}x{ry}",
            "bytes": os.path.getsize(out) if os.path.exists(out) else 0, "s": round(time.time() - t0, 1), "ffmpeg_err": rr.stderr[-300:]}
    json.dump(info, open(os.path.join(SAL, 'revision_argon.json'), 'w'), indent=1)
    print('RESULT_SB3D_VIDEO', json.dumps(info))

# ================================================================= MODO APLICAR
MAP_PLANO = {'WS': 'PG', 'MS': 'PM', 'CU': 'PP', 'FS': 'PE', 'MCU': 'PMC', 'ECU': 'PPP', 'EWS': 'GPG', 'MLS': 'PA'}
def _vec3(x):
    try:
        v = [float(t) for t in x][:3]
        return v if len(v) == 3 and all(math.isfinite(t) for t in v) else None
    except Exception: return None
def norm_decision(d, V):
    """[t1077u] decisión LIBRE de Argon (posición + mira + plano + ángulo + lente + movimiento con cantidad y velocidad).
    Solo se normaliza contra el catálogo/DSL; lo inválido se reporta. Devuelve (intento | None, avisos)."""
    av = []; cam = d.get('camara') or {}
    pos = _vec3(cam.get('pos') or d.get('pos'))
    if pos is None: return None, ['sin camara.pos válida']
    lo, hi = INT['lo'], INT['hi']
    pos[2] = min(max(pos[2], lo[2] + 0.05), hi[2] + 3.0)
    mira = cam.get('mira') if 'mira' in cam else d.get('mira')
    mira_pj = None; mira_xyz = None; punto = str(cam.get('punto') or d.get('punto') or 'ojos').lower()
    if isinstance(mira, str) and mira in ARM: mira_pj = mira
    elif isinstance(mira, dict) and mira.get('personaje') in ARM: mira_pj = mira['personaje']; punto = str(mira.get('punto') or punto).lower()
    else: mira_xyz = _vec3(mira) if mira is not None else None
    obj = d.get('objetivo') if d.get('objetivo') in ARM else (mira_pj or V['obj'])
    if mira_pj is None and mira_xyz is None: mira_pj = obj; av.append('mira inválida -> objetivo')
    pl = str(d.get('plano') or 'PM').upper(); pl = MAP_PLANO.get(pl, DE_SB.get(pl, pl))
    if pl not in COB: av.append(f"plano «{pl}» fuera de catálogo -> PM"); pl = 'PM'
    an = str(d.get('angulo') or 'NORM').upper(); an = ANG_SB.get(an, an)
    if an not in ELEV: av.append(f"ángulo «{an}» fuera de catálogo -> NORM"); an = 'NORM'
    mvd = d.get('movimiento') or {}
    if isinstance(mvd, str): mvd = {"tipo": mvd}
    mv = str(mvd.get('tipo') or 'STATIC').upper().replace(' ', '').replace('_', '').replace('-', '')
    if mv not in MOVS: av.append(f"movimiento «{mv}» fuera del DSL -> STATIC"); mv = 'STATIC'
    try: le = float(str(d.get('lente_mm') or LENTE.get(pl, 35)).upper().lstrip('L'))
    except Exception: le = LENTE.get(pl, 35)
    le = max(12.0, min(135.0, le))
    try: u = max(0.0, min(1.0, float(mvd.get('intensidad', 0.5))))
    except Exception: u = 0.5
    c = {"fija": True, "C": pos, "mira_pj": mira_pj, "mira_xyz": mira_xyz, "punto": punto if punto in ('ojos', 'pecho', 'centro', 'pies') else 'ojos',
         "seguir": bool(d.get('seguir_sujeto')), "plano": pl, "angulo": an, "lente": le, "id": "ARGON", "az_off": 0}
    mov = {"movimiento": mv, "intensidad": u, "direccion": mvd.get('direccion'), "espera_s": mvd.get('espera_s', 0), "velocidad": mvd.get('velocidad')}
    return {"c": c, "mov": mov, "obj": obj, "nunca_ocultar": [x for x in (d.get('nunca_ocultar') or []) if isinstance(x, str)],
            "motivo": d.get('motivo')}, av

def leer_decisiones():
    """sb_argon.json (llamada principal) + sb_argon_correccion.json (ronda única de corrección: reemplaza esas viñetas)."""
    dec = {}; fuente = 'motor (sin Argon)'; av = []; corr = set()
    for nombre in ('sb_argon.json', 'sb_argon_correccion.json'):
        p = os.path.join(SAL, nombre)
        if not os.path.exists(p): continue
        try:
            J = json.load(open(p)); dd = J.get('decision') or J
            for x in dd.get('vinetas', []):
                if x.get('id'):
                    dec[x['id']] = x
                    if 'correccion' in nombre: corr.add(x['id'])
            if dec: fuente = 'Argon' + (' + corrección' if corr else '')
        except Exception as ex: av.append(f"{nombre} ilegible: {ex}")
    return dec, fuente, av, corr

# [t518 10-nov-2026] caso real: una candidata «de grupo» miraba al centro de dos personajes (uno ya fuera del cuarto) y quedó
# pegada al piso detrás de un mueble: 29 % del objetivo visible y aun así se APLICÓ (FALLO_VALIDACION). Ahora: (1) si nada pasa, rescate determinista
# centrado SOLO en el objetivo (anillo de posiciones fijas mirando a sus ojos, distancia según su altura real);
# (2) jamás se aplica una cámara con el objetivo visible < VIS_MIN_APLICAR: queda STOP_CAMARA_SIN_SUJETO y correr_escena
# no paga el render de esa escena.
VIS_MIN_APLICAR = 0.60
RESCATE_AZ = 24; RESCATE_EL = (5.0, 20.0, 45.0, 65.0); RESCATE_DIST = (0.6, 1.0, 1.5); RESCATE_MAX = 288   # [argon_v2] anillo más fino (15°), 3 distancias (la corta pasa entre quienes rodean al sujeto) y 2 cenitales (por encima de quien tapa)

def candidatas_rescate(V):
    """posiciones fijas alrededor del OBJETIVO (no del grupo): azimut cada 30°, 2 elevaciones, distancia para que el sujeto
    ocupe ~45 % del alto de cuadro con 35 mm (PM) — para un personaje de 0,18 m queda a ~0,5 m, no a 3 m."""
    fm = (V['f0'] + V['f1']) // 2; M_ = med(V['obj'], fm)
    if not M_: return []
    alto = max(0.12, float(M_.get('altura') or 0.5)); T = M_['ojos']
    fov_v = 2 * math.atan(0.5 * SH / 35.0)      # [argon_v2] alto de sensor REAL de la cámara de la escena (antes 24 mm fijo), lente 35
    d = max(0.35, alto / 0.45 / (2 * math.tan(fov_v / 2)))
    out = []; lo, hi = INT['lo'], INT['hi']
    for el, fd, k in [(el, fd, k) for fd in RESCATE_DIST for el in RESCATE_EL for k in range(RESCATE_AZ)]:
            az = math.radians(k * 360.0 / RESCATE_AZ); dd = d * fd
            C = Vector((T.x + dd * math.cos(az) * math.cos(math.radians(el)), T.y + dd * math.sin(az) * math.cos(math.radians(el)), T.z + dd * math.sin(math.radians(el))))
            if not (lo[0] + 0.1 < C.x < hi[0] - 0.1 and lo[1] + 0.1 < C.y < hi[1] - 0.1 and lo[2] + 0.12 < C.z < hi[2] - 0.15): continue
            out.append({"c": {"fija": True, "C": [C.x, C.y, C.z], "mira_pj": V['obj'], "mira_xyz": None, "punto": "ojos", "seguir": True,
                              "plano": "PM", "angulo": "CEN" if el > 55 else ("PIC" if el > 15 else "NORM"), "lente": 35.0, "id": f"R{len(out) + 1}", "az_off": 0},
                        "mov": {"movimiento": "STATIC"}, "obj": V['obj'], "origen": f"rescate determinista centrado en {V['obj']} (az {k * 360 // RESCATE_AZ}°, el {el:.0f}°, d {dd:.2f} m)"})
    # [argon_v2] por ENCIMA de todos: cenital alto (la cámara sube sobre el más alto de los que están en cuadro + holgura),
    # lente según la distancia resultante. Sirve cuando el sujeto está rodeado (nadie se esconde: solo se sube la cámara).
    altos = [((med(p, fm) or {}).get('hi') or Vector((0, 0, 0))).z for p in V.get('en_cuadro') or [] if p != V['obj']]
    z_min = max([T.z] + altos) + 0.35
    for el in (65.0, 80.0):
        dd = max(d, (z_min - T.z) / math.sin(math.radians(el)))
        lente = max(18.0, min(85.0, 35.0 * dd / d)) if d > 0 else 35.0   # lente largo: desde arriba el sujeto sigue llenando el cuadro
        for k in range(0, RESCATE_AZ, 2):
            az = math.radians(k * 360.0 / RESCATE_AZ)
            C = Vector((T.x + dd * math.cos(az) * math.cos(math.radians(el)), T.y + dd * math.sin(az) * math.cos(math.radians(el)), T.z + dd * math.sin(math.radians(el))))
            if not (lo[0] + 0.1 < C.x < hi[0] - 0.1 and lo[1] + 0.1 < C.y < hi[1] - 0.1 and lo[2] + 0.12 < C.z < hi[2] - 0.15): continue
            out.append({"c": {"fija": True, "C": [C.x, C.y, C.z], "mira_pj": V['obj'], "mira_xyz": None, "punto": "ojos", "seguir": True,
                              "plano": "PM", "angulo": "CEN", "lente": round(lente, 1), "id": f"R{len(out) + 1}", "az_off": 0},
                        "mov": {"movimiento": "STATIC"}, "obj": V['obj'], "origen": f"rescate cenital sobre los vecinos de {V['obj']} (az {k * 360 // RESCATE_AZ}°, el {el:.0f}°, d {dd:.2f} m)"})
    return out[:RESCATE_MAX + 2 * RESCATE_AZ]

def modo_aplicar():
    t0 = time.time()
    paq = json.load(open(os.path.join(SAL, 'paquete.json')))
    cands = {v['id']: v['candidatas'] for v in paq['vinetas']}
    for V in VIN:
        pv = next((v for v in paq['vinetas'] if v['id'] == V['id']), {})
        if pv.get('aviso_eje'): V['aviso_eje'] = pv['aviso_eje']
    dec, fuente, avisos_dec, corregidas = leer_decisiones()
    solo_val = A.modo == 'validar'; val_rows = []
    # Argon puede PROMOVER a N0 (nunca bajar de nivel)
    promov = set()
    for x in dec.values():
        for i in x.get('nunca_ocultar') or []:
            b = NV.base_nombre(str(i))
            for e in NIV:
                if (e == b or e.startswith(b + '_') or e == i) and NIV[e]['nivel'] != 'N0': NIV[e]['nivel'] = 'N0'; NIV[e]['motivo'] = ['Argon: nunca ocultar']; promov.add(e)
    if promov:
        global N3_MALLAS, N0_MALLAS
        N3_MALLAS = set(NV.mallas_de_nivel(NIV, 'N3')); N0_MALLAS = set(NV.mallas_de_nivel(NIV, 'N0'))
    tabla = []; locs = {}; rots = {}; lens = {}; prev = None; tomas = []
    for V in VIN:
        cs = cands.get(V['id']) or []
        frames = sorted(set(list(range(V['f0'], V['f1'] + 1, max(1, A.paso_val))) + [V['f1']]))
        intentos = []; avis = []; Vs = []
        if V2_ON and V['id'] not in dec:
            avis = ['Argon no decidió esta viñeta']
        if V['id'] in dec and V2_ON:
            D, avis = norm_decision_v2(dec[V['id']], V, cs)
            if D:
                og = 'Argon v2 (corrección)' if V['id'] in corregidas else 'Argon v2'
                intentos.append(dict(D, origen=og)); Vs.append(V)
        elif V['id'] in dec:
            D, avis = norm_decision(dec[V['id']], V)
            if D:
                VA = dict(V, obj=D['obj'], en_cuadro=list(dict.fromkeys([D['obj']] + V['en_cuadro'])))
                og = 'Argon (corrección)' if V['id'] in corregidas else 'Argon'
                intentos.append(dict(D, origen=og)); Vs.append(VA)
                if not solo_val:
                    u = float(D['mov'].get('intensidad') or 0.5)
                    if D['mov']['movimiento'] not in ('STATIC', 'LOCK'):
                        intentos.append(dict(D, mov=dict(D['mov'], intensidad=u * 0.5), origen=og + ' · movimiento al 50 %')); Vs.append(VA)
                        intentos.append(dict(D, mov={"movimiento": "STATIC"}, origen=og + ' · misma cámara fija')); Vs.append(VA)
        if solo_val:
            if not intentos: val_rows.append({"vineta": V['id'], "ok": False, "fallas": ["Argon no decidió esta viñeta"] + avis}); continue
            refs, res = evaluar_x(Vs[0], intentos, frames)
            ver = veredicto_x(Vs[0], intentos[0], refs[0], res[0], prev)
            if not ver['ok'] and V2_ON:
                alt = mov_medido(Vs[0], intentos[0], frames, prev)
                if alt:
                    avis = list(avis) + [f"movimiento {intentos[0]['mov'].get('movimiento')} no pasó ({'; '.join(ver['fallas'][:1])}): misma cámara con el movimiento medido {alt[0]['mov']['movimiento']}"]
                    intentos[0], refs, res, ver = alt[0], alt[1], alt[2], alt[3]
            val_rows.append({"vineta": V['id'], "ok": ver['ok'], "fallas": ver['fallas'], "notas": ver.get('notas'), "vis_media": ver.get('vis_media'),
                             "vis_min": ver.get('vis_min'), "oclusores_n0": ver.get('oclusores_n0'), "mov": ver.get('mov'), "avisos_decision": avis,
                             "objetivo": intentos[0]['obj'], "camara": intentos[0]['c'].get('id'),
                             "pos": [round(x, 2) for x in (intentos[0]['c']['C'] if intentos[0]['c'].get('fija') else (refs[0]['C'] if refs[0] else [0, 0, 0]))]})
            log('validar', V['id'], 'OK' if ver['ok'] else 'FALLA', ver['fallas'][:2], ver.get('notas', [])[:1])
            if ver['ok'] and res[0]['poses']:
                fs_ = sorted(res[0]['poses']); Cf_ = res[0]['poses'][fs_[-1]][0]; Mf_ = med(intentos[0]['obj'], V['f1'])
                if Mf_: prev = {"obj": intentos[0]['obj'], "C_fin": Cf_, "escala_fin": res[0]['poses'][fs_[-1]][2] / max(1e-3, (Cf_ - Mf_['cabeza']).length)}
            continue
        if V2_ON and not RESPALDO_V2:
            # [argon_v2] ESTRICTO: solo la elección de Argon (ya re-medida). Si falla -> STOP_CAMARA_SIN_SUJETO: nunca se filma una
            # viñeta que no pasó, ni se cambia en silencio por otra cámara del motor.
            if not intentos:
                tabla.append({"vineta": V['id'], "estado": "STOP_CAMARA_SIN_SUJETO", "origen": "sin decisión válida de Argon", "avisos_decision": avis,
                              "objetivo": V['obj'], "validacion": {"ok": False, "fallas": avis or ['sin candidata válida']}, "camara_pos": None})
                log('viñeta', V['id'], 'STOP (sin decisión válida)', avis[:2]); continue
            refs, res = evaluar_x(Vs[0], intentos[:1], frames)
            vers = [veredicto_x(Vs[0], intentos[0], refs[0], res[0], prev)]
            if not vers[0]['ok']:
                alt = mov_medido(Vs[0], intentos[0], frames, prev)
                if alt:
                    avis = list(avis) + [f"movimiento {intentos[0]['mov'].get('movimiento')} no pasó ({'; '.join(vers[0]['fallas'][:1])}): misma cámara con el movimiento medido {alt[0]['mov']['movimiento']}"]
                    intentos[0] = alt[0]; refs, res, vers = alt[1], alt[2], [alt[3]]
            k = 0; estado = 'OK' if vers[0]['ok'] else 'STOP_CAMARA_SIN_SUJETO'
            if not res[0]['poses']:
                tabla.append({"vineta": V['id'], "estado": "STOP_CAMARA_SIN_SUJETO", "origen": intentos[0]['origen'], "objetivo": V['obj'],
                              "validacion": vers[0], "camara_pos": None, "avisos_decision": avis}); continue
            intentos = intentos[:1]; Vs = Vs[:1]
        else:
          # respaldo (solo si lo de Argon no pasa): la mejor opción válida del motor
          mv0 = (intentos[0]['mov'] if intentos else {"movimiento": mov_sb(V), "intensidad": 0.5})
          for c in cs:
              cc = {"plano": c['plano'], "angulo": c['angulo'], "az_off": c['az_off'], "lente": c['lente'], "id": c['id'], "el": c.get('el'), "k": c.get('k', 1.0)}
              intentos.append({"c": cc, "mov": dict(mv0), "obj": V['obj'], "origen": f"respaldo: candidata {c['id']} del motor"}); Vs.append(V)
          for c in cs[:3]:
              cc = {"plano": c['plano'], "angulo": c['angulo'], "az_off": c['az_off'], "lente": c['lente'], "id": c['id'], "el": c.get('el'), "k": c.get('k', 1.0)}
              intentos.append({"c": cc, "mov": {"movimiento": "STATIC"}, "obj": V['obj'], "origen": f"respaldo: candidata {c['id']} fija"}); Vs.append(V)
          intentos = intentos[:14]; Vs = Vs[:14]
          refs, res, vers = [None] * len(intentos), [None] * len(intentos), [None] * len(intentos)
          grupos = {}
          for i, vv in enumerate(Vs): grupos.setdefault(id(vv), (vv, []))[1].append(i)
          for vv, idx in grupos.values():
              r_, s_ = evaluar(vv, [intentos[i] for i in idx], frames)
              for j, i in enumerate(idx): refs[i], res[i] = r_[j], s_[j]
          vers = [veredicto(Vs[i], it, refs[i], res[i], prev) for i, it in enumerate(intentos)]
          k = next((i for i, x in enumerate(vers) if x['ok']), None)
          estado = 'OK'
          if k is None:   # [t518] rescate determinista centrado en el objetivo antes de rendirse
              resc = candidatas_rescate(V)
              if resc:
                  r_, s_ = evaluar(V, resc, frames)
                  vr = [veredicto(V, it, r_[i], s_[i], prev) for i, it in enumerate(resc)]
                  intentos += resc; Vs += [V] * len(resc); refs += r_; res += s_; vers += vr
                  k = next((i for i, x in enumerate(vers) if x['ok']), None)
                  if k is not None: log('rescate determinista OK', V['id'], intentos[k]['origen'])
          if k is None:
              _dentro = lambda v: any('cámara dentro' in str(x) for x in v['fallas'])   # [t518] cámara metida en mueble/muro = peor que cualquier otra
              k = max(range(len(vers)), key=lambda i: (vers[i].get('vis_media', 0) or 0) - 0.5 * len(vers[i]['fallas']) * 0.01 - (1.0 if _dentro(vers[i]) else 0.0)) if vers else None
              estado = 'FALLO_VALIDACION'
              if k is not None and ((vers[k].get('vis_media') or 0) < VIS_MIN_APLICAR or _dentro(vers[k])):
                  estado = 'STOP_CAMARA_SIN_SUJETO'   # [t518] no se filma una toma donde el objetivo casi no se ve o la cámara está dentro de algo
        if k is None: continue
        V0 = V; V = Vs[k]
        it = intentos[k]; ver = vers[k]; ps = res[k]['poses']
        # cámara por cuadro (todos los cuadros de la viñeta)
        for f in range(V['f0'], V['f1'] + 1):
            if f in ps: C, R, l = ps[f]
            else:
                sc.frame_set(f); C, R, l, _ = pose_mov(V, it['c'], it['mov'], f, refs[k])
            locs[f] = C.copy(); rots[f] = R.to_euler('XYZ'); lens[f] = l
        fs = sorted(ps); Mf = med(V['obj'], V['f1']) or med(V['obj'], fs[-1]); Cf = ps[fs[-1]][0]
        S = Mf['cabeza'] if Mf else refs[k]['T']
        prev = {"obj": V['obj'], "C_fin": Cf, "escala_fin": ps[fs[-1]][2] / max(1e-3, (Cf - S).length)}
        fila = {"vineta": V['id'], "estado": estado, "origen": it['origen'], "intento": k + 1, "intentos": len(intentos),
                "candidata": it['c']['id'], "camara_pos": [round(x, 2) for x in (it['c']['C'] if it['c'].get('fija') else refs[k]['C'])],
                "mira": it['c'].get('mira_pj') or it['c'].get('mira_xyz'), "velocidad": it['mov'].get('velocidad'), "plano": it['c']['plano'], "angulo": it['c']['angulo'], "lente_mm": round(it['c']['lente'], 1),
                "movimiento": it['mov'].get('movimiento'), "intensidad": it['mov'].get('intensidad'), "direccion": it['mov'].get('direccion'),
                "objetivo": V['obj'], "validacion": ver, "fallas_intentos_previos": [{"intento": i + 1, "origen": intentos[i]['origen'], "fallas": vers[i]['fallas']} for i in range(k)],
                "avisos_decision": avis, "motivo_argon": (dec.get(V['id']) or {}).get('motivo') or (dec.get(V['id']) or {}).get('justificacion'),
                "corregida_por_argon": V['id'] in corregidas, "argon_v2": {k_: (dec.get(V['id']) or {}).get(k_) for k_ in ('camara', 'tipo_plano', 'angulo', 'ritmo', 'rechazo')} if V2_ON else None}
        tabla.append(fila); V0['eleccion'] = fila; V0['obj_usado'] = V['obj']; V0['en_cuadro_usado'] = V['en_cuadro']
        log('viñeta', V['id'], estado, it['origen'], it['c']['plano'], it['c']['angulo'], it['mov'].get('movimiento'), 'vis', ver.get('vis_media'), ver['fallas'][:2])
        tomas.append({"vineta": V['id'], "frame_ini": V['f0'], "frame_fin": V['f1'], "objetivo": V['obj'], "angulo": it['c']['angulo'],
                      "lado": f"eje {V.get('lado_escena')}", "movimientos": [it['mov'].get('movimiento')], "altura_m": round((med(V['obj'], (V['f0'] + V['f1']) // 2) or {"altura": 0})['altura'], 3),
                      "plano": it['c']['plano'], "lente_mm": round(it['c']['lente'], 1), "sb3d": {"estado": estado, "origen": it['origen'], "candidata": it['c']['id']}})
    if solo_val:
        out = {"contrato": "sb3d_validacion_argon_v1", "ronda": A.etiqueta_val, "fuente": fuente, "umbrales": UMB, "vinetas": val_rows,
               "fallan": [r['vineta'] for r in val_rows if not r['ok']], "avisos_decision": avisos_dec}
        json.dump(out, open(os.path.join(SAL, f"validacion_argon_{A.etiqueta_val}.json"), 'w'), indent=1, ensure_ascii=False, default=str)
        print('RESULT_SB3D_VALIDAR', json.dumps({"ok": True, "ronda": A.etiqueta_val, "vinetas": len(val_rows), "fallan": out['fallan']}))
        return
    # ---- escribir la cámara (CONSTANT por cuadro, como el motor)
    cam = CAM; camd = cam.data
    bk = os.path.join(COR, 'escena_motor_antes_sb3d.blend')
    cam.animation_data_clear(); camd.animation_data_clear()
    fr = sorted(locs); prevE = None
    for f in (range(1, N + 1) if fr else []):   # [argon_v2] si todas las viñetas quedaron STOP no hay cámara que escribir
        g = f if f in locs else (fr[0] if f < fr[0] else max(x for x in fr if x <= f))
        cam.location = locs[g]; e = rots[g].copy()
        if prevE is not None: e.make_compatible(prevE)
        cam.rotation_euler = e; prevE = e; camd.lens = lens[g]
        cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f); camd.keyframe_insert('lens', frame=f)
    for idb in (cam, camd):
        for cb in _channelbags(idb):
            for fc in cb.fcurves:
                for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
    sc.camera = cam
    # ---- N2: recorte solo con la cámara FUERA de ese muro (keyframes CONSTANT por cuadro)
    rec_por = {}
    for f in range(1, N + 1):
        if f in locs:
            for n in n2_recortables(locs[f]): rec_por.setdefault(n, set()).add(f)
    for n, fs in rec_por.items():
        o = bpy.data.objects[n]
        for f in range(1, N + 1):
            v = f not in fs
            if f == 1 or (v != ((f - 1) not in fs)): o.visible_camera = v; o.keyframe_insert('visible_camera', frame=f)
        for cb in _channelbags(o):
            for fc in cb.fcurves:
                if fc.data_path == 'visible_camera':
                    for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
    # ---- ocultar_estorbos con N0 protegido: SOLO N3 puede ocultarse
    import ocultar_estorbos as OE
    oc = []; n0m = sorted(N0_MALLAS); n2m = sorted(N2_MALLAS)
    pide_ocultar = {vid for vid, x in dec.items() if x.get('ocultar') and x.get('motivo_ocultar')}
    for V in VIN:
        if 'eleccion' not in V: continue
        if CINE and V['id'] not in pide_ocultar:   # [cine_v1 · Ricardo t552u] no se esconde nada si la toma no lo amerita
            oc.append({"vineta": V['id'], "ocultados": [], "omitido": "regla de Ricardo: no se oculta nada (la decisión no lo pidió con motivo)"}); continue
        toma = {"contrato": "toma_ocultar_v1", "toma_id": f"esc{E['escena']}_{V['id']}", "vineta": V['id'], "frame_ini": V['f0'], "frame_fin": V['f1'],
                "camara": cam.name, "objetivo": V.get('obj_usado', V['obj']), "en_cuadro": V.get('en_cuadro_usado', V['en_cuadro']), "debe_verse": [], "objetos_sb": [],
                "n0": n0m, "n2_protegido": n2m, "paso_frames": 6}
        try:
            Es = OE.Escena(toma); frames = list(range(V['f0'], V['f1'] + 1, 6)); t_oe = time.time()
            an0 = Es.analizar(frames); pu, mot = Es.decidir(an0)
            sim = {o.name: fs for u, fs in pu.items() for o in Es.objetos_de_unidad(u)}
            an1 = Es.analizar(frames, ocultar_simulado=sim); Es.aplicar(pu)
            R0, R1 = OE.resumen(an0, Es), OE.resumen(an1, Es)
            oc.append({"vineta": V['id'], "ocultados": [{"unidad": u, "nivel": NIV.get(u, {}).get('nivel'), "cuadros": len(fs), "motivo": mot.get(u)} for u, fs in pu.items()],
                       "antes_muestras_tapadas": R0['muestras_tapadas'], "despues_muestras_tapadas": R1['muestras_tapadas'],
                       "conflictos_n0": R1['conflictos'], "no_encontrados": Es.no_encontrados})
            log('ocultar_estorbos', V['id'], 'ocultados', len(pu), f"{time.time() - t_oe:.0f}s")
        except Exception as ex:
            oc.append({"vineta": V['id'], "error": repr(ex)}); log('ocultar error', V['id'], ex)
    # ---- comprobación final: ningún N0 quedó con visible_camera=False en ningún cuadro
    n0_ocultos = []
    for n in n0m:
        o = bpy.data.objects.get(n)
        if o is None: continue
        for cb in _channelbags(o):
            for fc in cb.fcurves:
                if fc.data_path == 'visible_camera' and any(kp.co[1] < 0.5 for kp in fc.keyframe_points): n0_ocultos.append(n)
    # ---- actualizar reporte_motor.json (respaldo antes) y guardar la escena
    pr = os.path.join(COR, 'reporte_motor.json'); R = json.load(open(pr))
    if not os.path.exists(os.path.join(COR, 'reporte_motor_antes_sb3d.json')): shutil.copy(pr, os.path.join(COR, 'reporte_motor_antes_sb3d.json'))
    from bpy_extras.object_utils import world_to_camera_view
    chk = []
    for t_ in tomas:
        dentro = tot = 0
        for f in range(t_['frame_ini'], t_['frame_fin'] + 1, 2):
            sc.frame_set(f); a = ARM[t_['objetivo']]; pbc = a.pose.bones.get(ECAB.hueso_cabeza(a))
            p = a.matrix_world @ ((pbc.head + pbc.tail) * 0.5) if pbc else a.matrix_world.translation
            q = world_to_camera_view(sc, cam, p); tot += 1; dentro += (0 <= q.x <= 1 and 0 <= q.y <= 1 and q.z > 0)
        chk.append({"vineta": t_['vineta'], "cabeza_objetivo_en_cuadro_pct": round(100 * dentro / max(1, tot), 1)})
    viejo = R['pasos'].get('5_camara')
    R['pasos']['5_camara'] = {"tomas": tomas, "metodo": f"sb3d: storyboard después del 3D ({fuente}) + validación 3D", "chequeo_encuadre": chk,
                              "ocultar_estorbos": oc, "camara_antes_sb3d": "reporte_motor_antes_sb3d.json"}
    rev = R['pasos'].get('6_revision', {})
    rev['camara_ok'] = all(x['estado'] == 'OK' for x in tabla) and not n0_ocultos
    rev['ok'] = all(r.get('ok') for r in rev.get('personajes', {}).values()) and all(p.get('ok') for p in rev.get('pares', [])) and rev['camara_ok']
    R['pasos']['6_revision'] = rev
    R['pasos']['5b_sb_despues_3d'] = {"fuente": fuente, "vinetas_ok": sum(1 for x in tabla if x['estado'] == 'OK'), "vinetas": len(tabla),
                                      "fallos": [x['vineta'] for x in tabla if x['estado'] != 'OK'], "n0_ocultos": n0_ocultos,
                                      "promovidos_a_n0_por_argon": sorted(promov), "segundos": round(time.time() - t0, 1)}
    json.dump(R, open(pr, 'w'), indent=1, ensure_ascii=False, default=str)
    val = {"contrato": "sb3d_validacion_v1", "fuente_decision": fuente, "avisos_decision": avisos_dec, "umbrales": UMB, "tabla": tabla,
           "ocultar_estorbos": oc, "n0_ocultos": n0_ocultos, "n2_recortes": {n: len(fs) for n, fs in rec_por.items()},
           "promovidos_a_n0_por_argon": sorted(promov), "segundos": round(time.time() - t0, 1)}
    json.dump(val, open(os.path.join(SAL, 'sb3d_validacion.json'), 'w'), indent=1, ensure_ascii=False, default=str)
    if A.guardar:
        src = os.path.join(COR, 'escena_motor.blend')
        if os.path.exists(src) and not os.path.exists(bk): shutil.copy(src, bk)
        bpy.ops.wm.save_as_mainfile(filepath=src)
    log('APLICAR listo', fuente, 'OK', sum(1 for x in tabla if x['estado'] == 'OK'), '/', len(tabla), 'N0 ocultos', len(n0_ocultos))
    print('RESULT_SB3D_APLICAR', json.dumps({"ok": True, "fuente": fuente, "vinetas_ok": sum(1 for x in tabla if x['estado'] == 'OK'), "vinetas": len(tabla),
                                             "n0_ocultos": len(n0_ocultos), "s": round(time.time() - t0, 1)}))

# ================================================================= [argon_v2] candidatas medidas, stills legibles y decisión por id
PAQ0 = {}
try: PAQ0 = json.load(open(os.path.join(SAL, 'paquete.json'))) if A.modo != 'paquete' else {}
except Exception: PAQ0 = {}
V2_ON = bool(A.v2 or PAQ0.get('contrato') == 'sb3d_paquete_v2')
RESPALDO_V2 = bool(CFG.get('respaldo_motor_v2', False))

def _c_motor(c):
    if c.get('fija'): return {k: c.get(k) for k in ('fija', 'C', 'mira_pj', 'mira_xyz', 'punto', 'seguir', 'plano', 'angulo', 'lente', 'id', 'az_off',
                                                     'familia', 'claves', 'dueno', 'seguir_dueno', 'ruta', 'miras', 'lentes', 'd_min') if k in c}
    return {"plano": c['plano'], "angulo": c['angulo'], "az_off": c['az_off'], "lente": c['lente'], "id": c['id'], "el": c.get('el'), "k": c.get('k', 1.0)}

def _resumen(ver, rs=None):
    x = {k: ver.get(k) for k in ('ok', 'fallas', 'notas', 'vis_media', 'vis_min', 'cabeza_en_cuadro', 'oclusores_n0', 'tam_sujeto')}
    x['n3_a_ocultar'] = len(ver.get('n3_a_ocultar') or []); return x

# [argon_v2 · traído del trabajo paralelo inmiB] filtros de encuadre: cuadro casi vacío y primer plano tapado
def frac_personajes(V, C, R, lente, f):
    """fracción aproximada del cuadro ocupada por los personajes del cuadro (cajas proyectadas, recortadas) + quiénes entran."""
    tot = 0.0; quienes = []
    for p in V['en_cuadro']:
        M = med(p, f)
        if not M: continue
        lo, hi = M['lo'], M['hi']
        pts = [CC.proyectar(C, R, Vector((x, y, z)), lente, SW, ASP) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
        pts = [q for q in pts if q]
        if len(pts) < 8: continue
        x0, x1 = max(-1, min(q[0] for q in pts)), min(1, max(q[0] for q in pts)); y0, y1 = max(-1, min(q[1] for q in pts)), min(1, max(q[1] for q in pts))
        if x1 > x0 and y1 > y0:
            a = (x1 - x0) * (y1 - y0) / 4.0; tot += 0.6 * a     # 0,6 = la caja sobreestima la silueta
            pc = CC.proyectar(C, R, M['cabeza'], lente, SW, ASP)
            if pc and abs(pc[0]) <= 1 and abs(pc[1]) <= 1: quienes.append(p)
    return min(1.0, tot), quienes
def tapon_cercano(C, R, lente, dist_sujeto, nx=12, ny=7):
    """fracción del cuadro tapada por algo MUY cerca de la cámara (brazo/cuerpo de otro personaje o mueble pegado al lente):
    rejilla de rayos; cuenta los que pegan a < max(0,35 m, 60 % de la distancia al sujeto)."""
    dg = bpy.context.evaluated_depsgraph_get(); tx = (SW / 2) / lente; ty = tx / ASP; lim = max(0.35, 0.6 * dist_sujeto); n = k = 0
    for i in range(nx):
        for j in range(ny):
            x = (2 * (i + 0.5) / nx - 1) * tx; y = (2 * (j + 0.5) / ny - 1) * ty
            d = (R @ Vector((x, y, -1.0))).normalized(); n += 1
            hit, loc, nor, idx, ob, mx = sc.ray_cast(dg, C, d, distance=lim)
            if hit and (ob.name not in N3_MALLAS) and bpy.data.objects.get(ob.name, ob).visible_camera: k += 1
    return k / max(1, n)

TAM_SUJETO_MIN = {'GPG': 0.04, 'PG': 0.06, 'PE': 0.09, 'PA': 0.10}; TAM_SUJETO_DEF = 0.12   # [argon_v2] fracción mínima del lado mayor del cuadro que ocupa el objetivo, según plano (si no, «se ve» pero no se lee)
def frac_sujeto_cuadro(pid, C, R, lente, f):
    M = med(pid, f)
    if not M: return None
    lo, hi = M['lo'], M['hi']
    pts = [CC.proyectar(C, R, Vector((x, y, z)), lente, SW, ASP) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
    pts = [q for q in pts if q]
    if len(pts) < 8: return None
    return max(max(q[0] for q in pts) - min(q[0] for q in pts), max(q[1] for q in pts) - min(q[1] for q in pts)) / 2.0
def filtros_encuadre(V, rf, rs, ver, plano=None):
    """añade al veredicto las fallas de encuadre (cuadro medio de la toma). No cambia umbrales de visibilidad."""
    if not ver.get('ok') or not rs.get('poses') or rf is None: return ver
    fs = sorted(rs['poses']); f = fs[len(fs) // 2]; C, Rr, l = rs['poses'][f]; sc.frame_set(f)
    fp, _ = frac_personajes(V, C, Rr, l, f); tp = tapon_cercano(C, Rr, l, (C - rf['T']).length)
    fl = []; ts = frac_sujeto_cuadro(V['obj'], C, Rr, l, f)
    tmin = TAM_SUJETO_MIN.get(plano or '', TAM_SUJETO_DEF)
    if ts is not None and ts < tmin: fl.append(f"sujeto demasiado chico en cuadro: {ts:.0%} (mínimo {tmin:.0%} para {plano})")
    if fp < 0.03: fl.append(f"cuadro casi vacío: personajes {fp:.0%} del cuadro")
    if tp > 0.20: fl.append(f"primer plano tapado: {tp:.0%} del cuadro con algo pegado a la cámara")
    if fl: ver = dict(ver, ok=False, fallas=list(ver.get('fallas') or []) + fl)
    return dict(ver, frac_personajes=round(fp, 3), tapon=round(tp, 3), tam_sujeto=None if ts is None else round(ts, 3))

def validar_candidatas(V, cands):
    """re-mide cada candidata (fija) en TODOS los cuadros de la viñeta con los umbrales de siempre; si quedan < 2 válidas se
    suma el anillo de rescate centrado en el objetivo (posiciones fijas según su altura real). Solo las válidas van a Argon."""
    frames = sorted(set(list(range(V['f0'], V['f1'] + 1, max(1, A.paso_val))) + [V['f1']]))
    its = [{"c": _c_motor(c), "mov": {"movimiento": "STATIC"}, "obj": V['obj']} for c in cands]; out = []
    if its:
        refs, res = evaluar(V, its, frames)
        for c, it, rf, rs in zip(cands, its, refs, res):
            c.update(c_motor=it['c'], val3d=_resumen(filtros_encuadre(V, rf, rs, veredicto(V, it, rf, rs, None), it['c'].get('plano')))); out.append(c)
    objetivo_ok = max(2, min(A.max_candidatas, 4))
    if sum(1 for c in out if c['val3d']['ok']) < 2:
        resc = candidatas_rescate(V)
        if resc:
            refs, res = evaluar(V, resc, frames)
            diag = {}
            for it, rf, rs in zip(resc, refs, res):
                if rf is None: diag['sin pose'] = diag.get('sin pose', 0) + 1; continue
                ver = filtros_encuadre(V, rf, rs, veredicto(V, it, rf, rs, None), it['c'].get('plano'))
                if not ver['ok']:
                    k_ = re.sub(r'[0-9.]+ ?%?', '#', (ver['fallas'] or ['?'])[0])[:70]; diag[k_] = diag.get(k_, 0) + 1; continue
                mid = rs['m'][len(rs['m']) // 2] if rs['m'] else {}
                out.append({"plano": it['c']['plano'], "angulo": it['c']['angulo'], "az_off": 0, "lente": it['c']['lente'], "rescate": True, "origen": it.get('origen'),
                            "pos": [round(x, 2) for x in it['c']['C']], "mira": [round(x, 2) for x in rf['T']], "dist_m": round(rf['d'], 2), "az_deg": round(rf['az'], 1),
                            "el_deg": round(rf['el'], 1), "vis_mitad": round(mid.get('vis', 0), 3), "oclusor": mid.get('oclusor'), "fuera_recinto": bool(NV.lado_fuera(Vector(it['c']['C']), INT)),
                            "c_motor": dict(it['c']), "val3d": _resumen(ver), "id": it['c']['id']})
                if sum(1 for c in out if c['val3d']['ok']) >= objetivo_ok: break
            V['rescate'] = {"probadas": len(resc), "fallas": diag}; log('rescate', V['id'], len(resc), json.dumps(diag, ensure_ascii=False)[:600])
    val = [c for c in out if c['val3d']['ok']]
    val.sort(key=lambda c: -((c['val3d'].get('vis_media') or 0) + (0.0 if c.get('rescate') else 0.02)))
    # [argon_v2] variedad: como mucho la mitad de las ofrecidas con el mismo ángulo (si hay otras válidas), para que Argon escoja de verdad
    tope_ang = max(2, A.max_candidatas // 2); el_, cuenta = [], {}
    for c in val:
        if cuenta.get(c['angulo'], 0) < tope_ang: el_.append(c); cuenta[c['angulo']] = cuenta.get(c['angulo'], 0) + 1
        if len(el_) >= A.max_candidatas: break
    val = (el_ + [c for c in val if c not in el_])[:A.max_candidatas]
    V['descartadas'] = [{"id_motor": c.get('id'), "plano": c.get('plano'), "fallas": (c['val3d'].get('fallas') or [])[:2]} for c in out if not c['val3d']['ok']]
    for i, c in enumerate(val):
        c['id_motor'] = c.get('id'); c['id'] = f"C{i + 1}"; c['c_motor']['id'] = c['id']
    log('candidatas v2', V['id'], 'válidas', len(val), 'descartadas', len(V['descartadas']))
    return val

def norm_decision_v2(d, V, cs):
    """decisión de Argon v2: escoge UNA candidata por id (no inventa xyz) + tipo de plano, ángulo y ritmo/movimiento."""
    av = []; cid = str(d.get('camara') or d.get('camara_elegida') or '').strip().upper()
    c = next((x for x in cs if x['id'] == cid), None)
    if c is None: return None, [f"cámara «{cid}» no es candidata válida de {V['id']} (válidas: {[x['id'] for x in cs]})"]
    mvd = d.get('movimiento') or {}
    if isinstance(mvd, str): mvd = {"tipo": mvd}
    mv = str(mvd.get('tipo') or 'STATIC').upper().replace(' ', '').replace('_', '').replace('-', '')
    if mv not in MOVS: av.append(f"movimiento «{mv}» fuera del DSL -> STATIC"); mv = 'STATIC'
    try: u = max(0.0, min(1.0, float(mvd.get('intensidad', 0.4))))
    except Exception: u = 0.4
    pl = str(d.get('tipo_plano') or c['plano']).upper(); pl = MAP_PLANO.get(pl, DE_SB.get(pl, pl))
    if pl != c['plano']: av.append(f"Argon llamó {pl} a {cid} (geometría {c['plano']}): manda la geometría medida")
    cm = dict(c['c_motor'])
    if cm.get('fija') and isinstance(cm.get('C'), list): cm['C'] = list(cm['C'])
    if cm.get('ruta'):   # [cine_v1] RETIRADA / PASE_CARAS: el movimiento ES la familia
        if mv not in ('TRAYECTO', 'STATIC'): av.append(f"{cid} es {cm.get('familia')}: su movimiento es el trayecto medido (se ignora {mv})")
        mv = 'TRAYECTO'
    mov = {"movimiento": mv, "intensidad": u, "direccion": mvd.get('direccion'), "espera_s": mvd.get('espera_s', 0), "velocidad": mvd.get('velocidad') or d.get('ritmo')}
    return {"c": cm, "mov": mov, "obj": V['obj'], "nunca_ocultar": [x for x in (d.get('nunca_ocultar') or []) if isinstance(x, str)],
            "motivo": d.get('justificacion') or d.get('motivo'), "mov_medidos": list(c.get('movimientos_validos') or ['STATIC'])}, av

def mov_medido(V, it, frames, prev):
    """[cine_v1 11-nov] la MISMA cámara que eligió Argon con el movimiento que el motor ya midió en el paquete (no otra cámara).
    Se usa solo si el movimiento pedido por Argon no pasa; queda anotado en origen/avisos."""
    mm = [m for m in (it.get('mov_medidos') or []) if m != (it.get('mov') or {}).get('movimiento')]
    for m in mm:
        it2 = dict(it, mov={"movimiento": m, "intensidad": 0.2 if m == 'STEADICAM' else 0.4}, origen=str(it.get('origen', '')) + f' · movimiento medido {m}')
        r2, s2 = evaluar_x(V, [it2], frames); v2 = veredicto_x(V, it2, r2[0], s2[0], prev)
        if v2['ok']: return it2, r2, s2, v2
    return None

def stills_candidatas():
    """[argon_v2] una foto CLARA por candidata (cuadro central de la viñeta, Workbench iluminado, rótulo grande + nombre de cada
    personaje sobre su cabeza) + hoja por viñeta (lo que ve Argon) + hoja general. Solo esta sesión: no se guarda el .blend."""
    rx, ry = map(int, A.res_still.split('x')); r = sc.render
    sc.render.engine = 'BLENDER_WORKBENCH'; sh = sc.display.shading
    sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'; sh.show_shadows = False
    for k_, v_ in (('show_object_outline', True), ('show_cavity', True), ('cavity_type', 'WORLD'), ('object_outline_color', (0, 0, 0)), ('show_specular_highlight', True)):
        try: setattr(sh, k_, v_)
        except Exception: pass
    try: sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = 0.35
    except Exception: pass
    r.resolution_x, r.resolution_y = rx, ry; r.resolution_percentage = 100
    r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGB'
    for k in dir(r):
        if k.startswith('use_stamp_') and k != 'use_stamp_note':
            try: setattr(r, k, False)
            except Exception: pass
    try: r.use_stamp = True; r.use_stamp_note = True; r.stamp_font_size = max(16, ry // 16); r.stamp_background = (0, 0, 0, 0.75)
    except Exception: pass
    cd = bpy.data.cameras.new('SB3D_still'); cc = bpy.data.objects.new('SB3D_still', cd); sc.collection.objects.link(cc)
    cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = SW; cd.clip_start = 0.02; cd.clip_end = 80; cam_prev = sc.camera; sc.camera = cc
    mt = bpy.data.materials.new('SB3D_rotulo'); mt.diffuse_color = (1.0, 0.9, 0.1, 1.0)
    rot = {}
    for p in PJ:
        cu = bpy.data.curves.new(f'SB3D_lbl_{p}', 'FONT'); cu.body = nombre_corto(p); cu.align_x = 'CENTER'; cu.extrude = 0.002
        ob = bpy.data.objects.new(f'SB3D_lbl_{p}', cu); sc.collection.objects.link(ob); ob.data.materials.append(mt); ob.show_in_front = True; rot[p] = ob
        ob.visible_shadow = False
    sd = os.path.join(SAL, 'stills'); os.makedirs(sd, exist_ok=True); fotos = {}
    for V in VIN:
        fm = (V['f0'] + V['f1']) // 2; sc.frame_set(fm)
        for c in V.get('cands') or []:
            cm_ = c['c_motor']; ruta_ = bool(cm_.get('ruta'))
            tomas_ = [('', fm)] if not ruta_ else [('ini', V['f0'] + 1), ('fin', V['f1'])]
            for tag_, f_ in tomas_:
                sc.frame_set(f_); P = pose_base(V, cm_, fm if not ruta_ else f_)
                if P is None: continue
                if ruta_:
                    C_, R_, le_, T_ = pose_ruta(V, cm_, {"movimiento": "TRAYECTO"}, f_); P = dict(P, C=C_)
                else: R_ = mirar(P['C'], P['T'], P['sx'], cm_['lente'], P['roll']); le_ = cm_['lente']
                cc.matrix_world = Matrix.Translation(P['C']) @ R_.to_4x4(); cd.lens = le_
                for p, ob in rot.items():
                    M_ = med(p, f_)
                    if M_ is None: ob.hide_render = True; continue
                    dcam = (M_['cabeza'] - P['C']).length; ob.data.size = max(0.02, 0.045 * dcam * 35.0 / max(12.0, cd.lens))
                    ob.location = (M_['cabeza'].x, M_['cabeza'].y, M_['hi'].z + 0.25 * ob.data.size); ob.rotation_euler = R_.to_euler(); ob.hide_render = False
                vv = c.get('val3d') or {}
                if CINE:   # [cine_v1] la foto muestra la escena TAL CUAL (no se esconde nada)
                    pv = {}
                    r.stamp_note_text = (f"{V['id']} · {c['id']} {tag_} · {c.get('familia')} {c['plano']} {c['angulo']} {le_:.0f}mm · "
                                         f"{'desde ' + nombre_corto(cm_['dueno']) + ' → ' if cm_.get('dueno') else ''}{nombre_corto(cm_.get('mira_pj') or V['obj']) if cm_.get('mira_pj') else 'grupo'}")
                else:
                    m = medir_pose(V, P['C'], R_, cm_['lente'], f_, plano=c['plano'])
                    pv = ocultar_temporal(set(m['n3_que_tapan']) | set(m['n2_recortados']))
                    r.stamp_note_text = (f"{V['id']} · {c['id']} · {c['plano']} {c['angulo']} {cm_['lente']:.0f}mm · objetivo {nombre_corto(V['obj'])} "
                                         f"· visible {100 * (vv.get('vis_media') or m['vis']):.0f}%")
                fp = os.path.join(sd, f"{V['id']}_{c['id']}{('_' + tag_) if tag_ else ''}.png"); r.filepath = fp
                bpy.ops.render.render(write_still=True); restaurar(pv); fotos.setdefault(V['id'], []).append((c['id'] + tag_, fp))
    for ob in rot.values(): bpy.data.objects.remove(ob, do_unlink=True)
    sc.camera = cam_prev; bpy.data.objects.remove(cc, do_unlink=True)
    hojas = {}; G = 6
    for vid, fs in fotos.items():   # hoja por viñeta: 3 columnas
        n = len(fs); cols = min(3, n); filas = (n + cols - 1) // cols
        H = filas * ry + G * (filas + 1); W = cols * rx + G * (cols + 1)
        S = np.full((H, W, 4), 0.1, dtype=np.float32); S[..., 3] = 1
        for k, (cid, fp) in enumerate(fs):
            px = _px(fp); fi, co = divmod(k, cols); y0 = H - (fi + 1) * (ry + G); x0 = G + co * (rx + G)
            S[y0:y0 + px.shape[0], x0:x0 + px.shape[1], :] = px[:, :, :4]
        hojas[vid] = _guardar(S, os.path.join(SAL, f"hoja_{vid}.jpg"))
    # hoja general (todas las viñetas, mitad de tamaño)
    if fotos:
        hx, hy = rx // 2, ry // 2; cols = max(len(v) for v in fotos.values()); filas = len(fotos)
        H = filas * hy + G * (filas + 1); W = cols * hx + G * (cols + 1)
        S = np.full((H, W, 4), 0.1, dtype=np.float32); S[..., 3] = 1
        for fi, V in enumerate([V for V in VIN if V['id'] in fotos]):
            for co, (cid, fp) in enumerate(fotos[V['id']]):
                px = _px(fp)[::2, ::2, :4]; y0 = H - (fi + 1) * (hy + G); x0 = G + co * (hx + G)
                S[y0:y0 + px.shape[0], x0:x0 + px.shape[1], :] = px
        hojas['_general'] = _guardar(S, os.path.join(SAL, "hoja_contacto_general.jpg"))
    return {"hojas": hojas, "fotos": {k: [c for c, _ in v] for k, v in fotos.items()}, "res": A.res_still}


# ================================================================= [cine_v1 · Ricardo t552u, 10-nov-2026] FAMILIAS DE CÁMARA
# Reglas de Ricardo: (1) cámara PRINCIPAL frente al personaje, a la altura de sus ojos, distancia prudente por plano con
# acercamiento mínimo d_min (50 cm o proporcional a su altura); si algo tapa la cara se mueve en ARCO o se acerca dentro del límite;
# nunca se esconden objetos ni se salta a cenital. (2) GENERAL estratégico (inicio / cambio de acción o lugar). (3) POV / OTS desde
# otro personaje. (4) RETIRADA de escala (cerca -> techo o pared). (5) PAISAJE cuando el guion lo pide. (6) PASE de caras.
# Validación: lente fuera de muros/muebles/cuerpos + elemento clave (cara) en cuadro y no tapado del todo (primer término parcial OK).
# Todos los números en motor/sb3d/catalogo/familias_camara.json; tabla de decisión opcional tabla_decision_camara.json (enchufable).
CAT_DIR = os.path.join(os.path.dirname(AQUI), 'sb3d', 'catalogo')
def _cargar_json(nombre):
    for d in (CAT_DIR, os.path.join(COR, 'sb3d')):
        pth = os.path.join(d, nombre)
        if os.path.exists(pth):
            try: return json.load(open(pth)), pth
            except Exception as ex: log('json ilegible', pth, ex)
    return None, None
FAM, FAM_PATH = _cargar_json('familias_camara.json'); FAM = FAM or {}
TABLA, TABLA_PATH = _cargar_json('tabla_decision_camara.json')
CINE = bool(int(CFG.get('cine', 1 if FAM else 0)))
FV = FAM.get('validacion') or {}
def _pl(pl): return (FAM.get('planos') or {}).get(pl) or {"alturas": COB.get(pl, 0.7), "lente": LENTE.get(pl, 35)}

def d_minimo(p, f):
    """[Ricardo] acercamiento máximo 50 cm, o proporcional al personaje: d_min = max(min_abs, 0,50 × min(1, H/H_ref)),
    H = altura medida del personaje, H_ref = 1,70 m (constantes_distancia de la tabla). Para 1,70 m -> 0,50 m; 18 cm -> 0,06 m (mínimo)."""
    D = dict(FAM.get('distancia') or {}); M = med(p, f)
    cd = (TABLA or {}).get('constantes_distancia') if isinstance(TABLA, dict) else None
    if cd: D.update(altura_referencia_m=cd.get('altura_referencia_m', D.get('altura_referencia_m')), acercamiento_max_m=cd.get('acercamiento_maximo_ref_m', D.get('acercamiento_max_m')))
    href = float(D.get('altura_referencia_m') or 1.70); H = tam_sujeto(M) if M else href
    return max(float(D.get('minimo_absoluto_m', 0.06)), float(D.get('acercamiento_max_m', 0.5)) * min(1.0, H / href))

def dentro_cuarto(C):
    m = float(FAM.get('margen_pared_m', 0.08)); lo, hi = INT['lo'], INT['hi']
    return lo[0] + m <= C.x <= hi[0] - m and lo[1] + m <= C.y <= hi[1] - m and lo[2] + 0.04 <= C.z <= hi[2] - 0.10

def holgura_cine(C, dg, f, excl=()):
    """None si el lente está libre; si no (quién, nivel, motivo). No mira dentro del cuerpo del dueño (POV/OTS)."""
    m = UMB['holgura_m']
    if not FV.get('permitir_fuera_del_cuarto', False) and not dentro_cuarto(C): return ('recinto', 'N2', 'fuera del cuarto / dentro de un muro')
    for n, (lo, hi) in CAJA_MALLA.items():
        if not all(lo[i] - m <= C[i] <= hi[i] + m for i in range(3)): continue
        o = bpy.data.objects[n]
        if o.hide_render: continue
        ok, mot, dd = CSP.dentro_de(o, C, dg, m)
        if ok: e = OBJ_ENT.get(n, n); return (e, NIV.get(e, {}).get('nivel'), mot)
    for q in PJ:
        if q in excl: continue
        M = med(q, f)
        if M and all(M['lo'][i] - 0.03 <= C[i] <= M['hi'][i] + 0.03 for i in range(3)):   # caja = aviso; la MALLA deformada decide
            for n in ENTS[q]['mallas']:
                o = bpy.data.objects.get(n)
                if o is None or o.type != 'MESH': continue
                ok, mot, dd = CSP.dentro_de(o, C, dg, 0.03)
                if ok: return (q, 'N0', 'dentro de un personaje')
    return None

def _mallas(pids): return {m for q in pids for m in ENTS.get(q, {}).get('mallas', [])}
def cara_libre(dg, C, R, lente, p, f, excl=()):
    """(en_cuadro, libre, frac_muestras_libres) de la cara de p. Libre = rayo a los ojos limpio o ≥ cara_libre_muestras_min de las
    muestras de la cabeza limpias. N3 NO se ignora (no se esconde nada); solo se atraviesa el cuerpo del dueño de la cámara."""
    M = med(p, f)
    if not M: return False, False, 0.0
    po = CC.proyectar(C, R, M['ojos'], lente, SW, ASP)
    en = po is not None and abs(po[0]) <= 0.95 and abs(po[1]) <= 0.92
    prop = set(ENTS[p]['mallas']); ign = _mallas(excl)
    e_ok = rayo(dg, C, M['ojos'], prop, ign)[0] != 'tapado'
    pts = (M.get('cab') or [])[::3]; lib = sum(1 for P in pts if rayo(dg, C, P, prop, ign)[0] != 'tapado')
    fr = lib / len(pts) if pts else (1.0 if e_ok else 0.0)
    return en, bool(e_ok or fr >= float(FV.get('cara_libre_muestras_min', 0.34))), fr

def mirar_pts(C, pts, margen=1.1):
    """lente que encuadra todos los puntos desde C mirando a su centro."""
    T = sum(pts, Vector()) / len(pts); R = mirar(C, T, 0.0, 35.0); tmax = 1e-3
    for P in pts:
        q = R.transposed() @ (P - C)
        if q.z >= -1e-3: return T, None
        tmax = max(tmax, abs(q.x / q.z), abs(q.y / q.z) * ASP)
    return T, (SW / 2) / (tmax * margen)

# ---------------------------------------------------------------- disparadores (todo medido o leído del SB) y tabla de decisión
def _txt(V):
    s = V['sb']; return ' '.join(str(x) for x in (s.get('intencion_narrativa'), s.get('secuencia'), s.get('beats_visuales'), (s.get('justificacion') or {}).get('emocion_buscada'))).lower()
def disparadores(i):
    V = VIN[i]; D = FAM.get('disparadores') or {}; out = {'siempre'}; fm = (V['f0'] + V['f1']) // 2
    if i == 0: out.add('inicio_escena')
    if i > 0:
        P_ = VIN[i - 1]['sb']
        if V['sb'].get('beat_narrativo') != P_.get('beat_narrativo'): out.add('cambio_beat')
        if V['sb'].get('segmento_genero') != P_.get('segmento_genero'): out.add('cambio_segmento')
        fp = (VIN[i - 1]['f0'] + VIN[i - 1]['f1']) // 2
        for q in PJ:
            a, b = med(q, fp), med(q, fm)
            if a and b and (Vector((a['cabeza'].x - b['cabeza'].x, a['cabeza'].y - b['cabeza'].y)).length > float(D.get('desplazamiento_x_altura', 0.8)) * max(0.2, b['altura'])):
                out.add('desplazamiento'); break
    if plano_sb(V) in ('GPG', 'PG'): out.add('plano_sb_abierto')
    if i >= 2 and all(plano_sb(VIN[i - k]) in ('PP', 'PPP', 'PMC') for k in (1, 2)): out.add('muchos_cercanos_seguidos')
    n = len([q for q in V['en_cuadro'] if med(q, fm)])
    if n >= 2: out.add('dos_o_mas')
    if n >= 3: out.add('tres_o_mas')
    hs = [med(q, fm)['altura'] for q in V['en_cuadro'] if med(q, fm)]
    if len(hs) >= 2 and max(hs) / max(1e-3, min(hs)) >= float(D.get('contraste_tamano_min', 2.0)): out.add('contraste_tamano')
    t = _txt(V)
    for k, nm in (('palabras_establecimiento', 'sb_pide_establecimiento'), ('palabras_tamano', 'sb_pide_tamano'), ('palabras_pov', 'sb_pide_pov')):
        if any(w in t for w in D.get(k) or []): out.add(nm)
    return out
# [cine_v1] lector ÚNICO de la tabla (mismo módulo que el creador de storyboard motor/sb_camara.py)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'sb3d'))
import tabla_camara as TCAM
_BEATS = TCAM.beats_tabla(TABLA) if isinstance(TABLA, dict) and TABLA.get('familias') else {}
def spec_de_beat(bid):
    sp = TCAM.spec(TABLA, FAM, bid); sp['familias'] = set(sp['familias'])
    if sp['plano'] not in COB: sp['plano'] = 'PM'
    return sp
def reglas_tabla(V, disp):
    """[cine_v1] tabla de decisión COMO DATOS: si el storyboard ya trae camara_tabla (paso sb_camara del creador de SB) se usan sus
    beats y su colocación; si no, se buscan los verbos del SB en el índice de la tabla (fallback por familia)."""
    res = {"familias": set(), "reglas": [], "specs": [], "sb": None}
    if not _BEATS: return res
    ct = V['sb'].get('camara_tabla') or {}
    if ct.get('beats'): beats = [b for b in ct['beats'] if b in _BEATS]; res['sb'] = ct
    else:
        d2 = set(disp) | ({'dialogo'} if V['sb'].get('audio') and 'dos_o_mas' in disp else set()) | ({'cambio_lugar'} if 'cambio_beat' in disp else set())
        beats = TCAM.buscar_beats(TABLA, FAM, V['sb'], d2)
    for bid in beats:
        sp = spec_de_beat(bid)
        if ct and bid == ct.get('beat'):   # el SB manda plano/ángulo/colocación finales (ya con reglas de secuencia)
            sp.update(plano=ct.get('plano') if ct.get('plano') in COB else sp['plano'], angulo=ct.get('angulo') or sp['angulo'], origen_sb=True)
            azc = (FAM.get('tabla') or {}).get('colocacion_az_deg') or {}
            if ct.get('colocacion') in azc: sp['az'] = azc[ct['colocacion']]
        res['specs'].append(sp); res['familias'] |= sp['familias']; res['reglas'].append(bid)
        res['familias'] |= {nm for nm, cf in (FAM.get('familias') or {}).items() if f'beat:{bid}' in (cf.get('cuando') or [])}
    return res

# ---------------------------------------------------------------- generadores por familia (cuadro medio de la viñeta)
def _cand(fam, C, plano, angulo, lente, mira_pj=None, mira_xyz=None, claves=None, dueno=None, ruta=None, miras=None, lentes=None, extra=None):
    c = {"fija": True, "C": [C.x, C.y, C.z], "mira_pj": mira_pj, "mira_xyz": [mira_xyz.x, mira_xyz.y, mira_xyz.z] if mira_xyz is not None else None,
         "punto": "ojos", "seguir": mira_pj is not None, "plano": plano, "angulo": angulo, "lente": round(float(lente), 1), "id": "", "az_off": 0,
         "familia": fam, "claves": claves or ([mira_pj] if mira_pj else []), "dueno": dueno, "seguir_dueno": bool(dueno)}
    if extra and extra.get('beat'): c['beat'] = extra['beat']
    if ruta: c.update(ruta=[[p.x, p.y, p.z] for p in ruta], miras=miras, lentes=lentes)
    if extra: c.update(extra)
    return c

def cam_principal(V, p, plano, angulo, f, d_alturas=None, lente=None, excl=(), az_pref=None, dz_H=0.0):
    """frente a p, a la altura de sus ojos; búsqueda en arco y acercamiento (manteniendo el encuadre con lente más angular)."""
    M = med(p, f)
    if not M: return None, 'sin medida'
    D = FAM.get('distancia') or {}; dg = bpy.context.evaluated_depsgraph_get()
    le0 = float(lente or _pl(plano)['lente'])
    VV = dict(V, obj=p, en_cuadro=(V['en_cuadro'] if plano in ('GPG', 'PG') else [p]))   # PE..PPP: el plano es del PERSONAJE (no del grupo)
    T, d, cov = mira_y_dist(VV, plano, le0, f)
    if d_alturas: d = float(d_alturas) * tam_sujeto(M)
    dmin = d_minimo(p, f)
    if d < dmin:   # [research t552u] el plano pide acercarse más que d_min: se queda en d_min y se ALARGA la lente
        le0 = min(float(D.get('lente_max_mm', 135)), le0 * dmin / max(1e-3, d)); d = dmin
    el = float((FAM.get('angulos_deg') or {}).get(angulo, ELEV.get(angulo, 0.0)))
    fr = M['frente']; az0 = ang_de(fr); respaldo = None; motivos = {}
    arco = list(FAM.get('arco_busqueda_deg') or [0, 30, -30, 60, -60, 90, -90])
    if az_pref:   # colocación de la tabla (lado, tres cuartos, detrás): se busca primero alrededor de esa colocación
        arco = sorted({round(a0 + o_) for a0 in az_pref for o_ in arco if abs(o_) <= 60}, key=lambda x: min(abs(x - a0) for a0 in az_pref)) + arco
    for off in list(dict.fromkeys(arco)):
        probadas = set()
        for k in D.get('pasos_acercar') or [1.0, 0.7, 0.5]:
            dd = max(dmin, d * k)
            if round(dd, 3) in probadas: continue
            probadas.add(round(dd, 3))
            le = max(float(D.get('lente_min_mm', 14)), le0 * dd / d)
            a = math.radians(az0 + off); C = Vector((T.x + dd * math.cos(a), T.y + dd * math.sin(a), M['ojos'].z))
            if dz_H == 'piso': C.z = INT['lo'][2] + 0.05
            elif dz_H: C.z = M['ojos'].z + float(dz_H) * M['altura']
            if angulo not in ('NORM', 'DUTCH'): C.z = C.z + dd * math.tan(math.radians(el))
            C.z = min(max(C.z, INT['lo'][2] + 0.05), INT['hi'][2] - 0.12)
            h = holgura_cine(C, dg, f, excl)
            if h: motivos[h[2][:30]] = motivos.get(h[2][:30], 0) + 1; continue
            R = mirar(C, T, 0.0, le); en, libre, fr_ = cara_libre(dg, C, R, le, p, f, excl)
            if not en: motivos['cara fuera de cuadro'] = motivos.get('cara fuera de cuadro', 0) + 1; continue
            if not libre: motivos['cara tapada'] = motivos.get('cara tapada', 0) + 1; continue
            # la viñeta entera (el personaje y los demás se mueven): la misma cámara, siguiendo al sujeto, en 4 cuadros más
            malo = None
            for fq in V.get('_fq') or []:
                Mq = med(p, fq)
                if not Mq: continue
                Cq = C + Vector((Mq['ojos'].x - M['ojos'].x, Mq['ojos'].y - M['ojos'].y, 0)); Tq = T + (Mq['ojos'] - M['ojos'])
                sc.frame_set(fq); dgq = bpy.context.evaluated_depsgraph_get()
                hq = holgura_cine(Cq, dgq, fq, excl)
                if hq: malo = hq[2][:30]; break
                enq, lq, _ = cara_libre(dgq, Cq, mirar(Cq, Tq, 0.0, le), le, p, fq, excl)
                if not enq: malo = 'cara fuera de cuadro (otro cuadro)'; break
            if sc.frame_current != f: sc.frame_set(f)
            if malo: motivos[malo + ' (viñeta)'] = motivos.get(malo + ' (viñeta)', 0) + 1; continue
            info = {"arco_deg": off, "dist_m": round(dd, 3), "d_min_m": round(dmin, 3), "acercada": k < 1.0, "frac_cara_libre": round(fr_, 2)}
            ls = V.get('lado_escena'); k_ = V.get('eje_k')
            if ls and k_ and lado(C, k_[0], k_[1], f) not in (0, ls):
                if respaldo is None: respaldo = (C, le, dict(info, cruza_eje=True))
                continue
            return (C, le, info), motivos
    return respaldo, motivos

def gen_principal(V, f, disp, tab):
    out = []; p = V['obj']; pl0 = tab.get('plano') or plano_sb(V); an0 = tab.get('angulo') or angulo_sb(V)
    if an0 in ('CEN', 'NAD'): an0 = 'PIC' if an0 == 'CEN' else 'CPIC'   # [Ricardo] nada de saltar a cenital: el ángulo se aplica desde la cámara de frente
    combos = [(pl0, an0)]
    if an0 != 'NORM': combos.append((pl0, 'NORM'))
    base = (FAM.get('familias', {}).get('PRINCIPAL', {}).get('plano_base') or 'PM')
    if pl0 != base: combos.append((base, 'NORM'))   # [Ricardo] la cámara base: frente al personaje, a la altura de sus ojos
    for k in (FAM.get('familias', {}).get('PRINCIPAL', {}).get('planos_vecinos') or [1, -1]): combos.append((paso_plano(pl0, k), an0))
    for pl, an in dict.fromkeys(combos):
        r, mot = cam_principal(V, p, pl, an, f)
        if r:
            C, le, info = r; out.append(_cand('PRINCIPAL', C, pl, an, le, mira_pj=p, extra={"busqueda": info, "d_min": info['d_min_m'], "origen": "storyboard" if (pl, an) == (pl0, an0) else "regla base / plano vecino"}))
        else: V.setdefault('rech_cine', {})[f'PRINCIPAL {pl} {an}'] = mot
    for sp in tab.get('specs') or []:   # [research t552u] beat del SB -> plano/colocación/altura/distancia/lente/movimiento de la tabla
        r, mot = cam_principal(V, p, sp['plano'], sp['angulo'], f, sp.get('d_alturas'), sp.get('lente'), az_pref=[a for a in sp['az'] if a] or None, dz_H=sp.get('dz_H') or 0.0)
        if r:
            C, le, info = r
            out.append(_cand('PRINCIPAL', C, sp['plano'], sp['angulo'], le, mira_pj=p, extra={"busqueda": info, "d_min": info['d_min_m'], "beat": sp['beat'], "origen": f"tabla: {sp['beat']} ({sp['familia_tabla']})", "movimiento_tabla": sp['movimiento'], "colocacion": sp['colocacion']}))
        else: V.setdefault('rech_cine', {})[f"TABLA {sp['beat']} {sp['plano']}"] = mot
    sec = [q for q in V['en_cuadro'] if q != p and med(q, f)]
    if sec and 'dos_o_mas' in disp:   # el que escucha / reacciona (plano de reacción) con el mismo plano
        r, mot = cam_principal(V, sec[0], pl0 if pl0 not in ('GPG', 'PG', 'PE') else 'PM', 'NORM', f)
        if r:
            C, le, info = r; out.append(_cand('PRINCIPAL', C, pl0 if pl0 not in ('GPG', 'PG', 'PE') else 'PM', 'NORM', le, mira_pj=sec[0], extra={"busqueda": info, "d_min": info['d_min_m'], "reaccion": True}))
    return out

def _puntos_pared(z):
    lo, hi = INT['lo'], INT['hi']; m = 0.25; xs = (lo[0] + m, (lo[0] + hi[0]) / 2, hi[0] - m); ys = (lo[1] + m, (lo[1] + hi[1]) / 2, hi[1] - m)
    return [Vector((x, y, z)) for x in xs for y in ys if not (x == xs[1] and y == ys[1])]
def gen_general(V, f, fam='GENERAL'):
    cfg = FAM['familias'][fam]; dg = bpy.context.evaluated_depsgraph_get()
    pres = [q for q in (V['en_cuadro'] if fam == 'GENERAL' else PJ) if med(q, f)]
    if fam == 'GENERAL':   # «dónde está cada uno»: todos los presentes dentro del cuarto
        pres = list(dict.fromkeys(pres + [q for q in PJ if med(q, f) and dentro_cuarto(Vector((med(q, f)['cabeza'].x, med(q, f)['cabeza'].y, INT['lo'][2] + 0.5)))]))
    if not pres: return []
    ojo_max = max(med(q, f)['ojos'].z for q in pres)
    alts = cfg.get('altura_x_ojos_mas_alto'); alts = alts if isinstance(alts, list) else [alts]
    pts = []
    for q in pres:
        M = med(q, f); pts += [M['ojos'], Vector(((M['lo'].x + M['hi'].x) / 2, (M['lo'].y + M['hi'].y) / 2, M['lo'].z))]
    if fam == 'PAISAJE':
        lo, hi = INT['lo'], INT['hi']; pts = [Vector((x, y, z)) for x in (lo[0] + 0.3, hi[0] - 0.3) for y in (lo[1] + 0.3, hi[1] - 0.3) for z in (lo[2] + 0.05, lo[2] + 0.6 * (hi[2] - lo[2]))]
    cands = []
    for a in alts:
        z = min(INT['hi'][2] - 0.15, max(INT['lo'][2] + 0.3, float(a) * (ojo_max - INT['lo'][2]) + INT['lo'][2]))
        for C in _puntos_pared(z):
            if holgura_cine(C, dg, f): continue
            ptsC = [P for P in pts if (P - C).length > 0.3]
            if len(ptsC) < 2: continue
            T, le = mirar_pts(C, ptsC)
            if le is None: continue
            rng = cfg.get('lente_rango_mm') or [cfg.get('lente_mm', 16)] * 2
            if fam == 'PAISAJE': le = min(le, float(cfg.get('lente_mm', 16)))
            le = max(float(rng[0]), min(float(rng[1]), le))
            v = C - T; el = math.degrees(math.asin(max(-1, min(1, v.z / max(1e-3, v.length)))))
            if el > float(cfg.get('elev_max_deg', 32)): continue
            R = mirar(C, T, 0.0, le); vis = 0; enc = 0
            for q in pres:
                en, lib, _ = cara_libre(dg, C, R, le, q, f); enc += en; vis += (en and lib)
            if fam == 'GENERAL' and (vis < max(1, len(pres) // 2)): continue
            ls = V.get('lado_escena'); k_ = V.get('eje_k'); cruza = bool(ls and k_ and lado(C, k_[0], k_[1], f) not in (0, ls))
            cands.append((vis - 0.5 * cruza - 0.01 * el, C, T, le, {"caras_libres": vis, "caras_en_cuadro": enc, "presentes": len(pres), "cruza_eje": cruza}))
    cands.sort(key=lambda x: -x[0]); out = []
    for sc_, C, T, le, info in cands:
        if any((C - Vector(o['C'])).length < 0.8 for o in out): continue
        out.append(_cand(fam, C, 'GPG' if fam == 'PAISAJE' else 'PG', 'NORM' if (C - T).z < 0.25 * (C - T).length else 'PIC', le, mira_xyz=T, claves=pres if fam == 'GENERAL' else pres[:], extra={"busqueda": info}))
        if len(out) >= int(cfg.get('max_candidatas', 2)): break
    return out

def _hombro(q, hacia):
    """hueso de hombro del rig (sinónimos/geometría, relaciones_blender.hueso) del lado de AFUERA (más lejos del objetivo)."""
    try:
        import relaciones_blender as RB
        arm = ARM[q]; mejor = None
        for ld in ('L', 'R'):
            hn, _ = RB.hueso(arm, 'hombro', ld)
            if hn and hn in arm.pose.bones:
                P = arm.matrix_world @ arm.pose.bones[hn].head; dd = (Vector((hacia.x, hacia.y)) - Vector((P.x, P.y))).length
                if mejor is None or dd > mejor[1]: mejor = (P, dd)
        return mejor[0] if mejor else None
    except Exception: return None
def gen_pov_ots(V, f, disp):
    out = []; dg = bpy.context.evaluated_depsgraph_get(); p = V['obj']; Mp = med(p, f)
    if not Mp: return out
    otros = [q for q in V['en_cuadro'] if q != p and med(q, f)]
    if not otros: return out
    cP = FAM['familias'].get('POV', {}); cO = FAM['familias'].get('OTS', {})
    pares = [(q, [p]) for q in otros] + [(p, otros)]   # desde otro mirando al objetivo, y desde el objetivo mirando a los demás
    pares.sort(key=lambda x: -abs(math.log(med(x[0], f)['altura'] / max(1e-3, sum(med(t, f)['altura'] for t in x[1]) / len(x[1])))))
    n_pov = n_ots = 0
    for q, objs in pares:
        Mq = med(q, f); Hq = Mq['altura']; caras = [med(t, f)['ojos'] for t in objs]
        Tc = sum(caras, Vector()) / len(caras); u = (Tc - Mq['ojos']); u = u.normalized() if u.length > 1e-4 else Mq['frente']
        if n_pov < int(cP.get('max_candidatas', 2)):
            C = Mq['ojos'] + u * max(0.03, float(cP.get('adelante_x_altura', 0.1)) * Hq)
            if not holgura_cine(C, dg, f, excl=(q,)):
                pts = [P for t in objs for P in (med(t, f)['ojos'], med(t, f)['hi'] if len(objs) > 1 else med(t, f)['ojos'])]
                T, le = mirar_pts(C, pts, 1.25) if len(objs) > 1 else (caras[0], float(cP.get('lente_mm', 24)))
                if le:
                    le = max(14.0, min(50.0, le)); R = mirar(C, T, 0.0, le); ok = [cara_libre(dg, C, R, le, t, f, excl=(q,)) for t in objs]
                    if sum(1 for en, lb, _ in ok if en and lb) >= max(1, len(objs) // 2):
                        v = T - C; el = math.degrees(math.asin(max(-1, min(1, v.z / max(1e-3, v.length)))))
                        out.append(_cand('POV', C, 'PM' if len(objs) == 1 else 'PE', 'CPIC' if el > 8 else ('PIC' if el < -8 else 'NORM'), le,
                                         mira_pj=objs[0] if len(objs) == 1 else None, mira_xyz=None if len(objs) == 1 else T, claves=objs, dueno=q,
                                         extra={"busqueda": {"desde": q, "mira_a": objs, "elev_mirada_deg": round(el, 1), "escala": round(Hq / max(1e-3, sum(med(t, f)['altura'] for t in objs) / len(objs)), 2)}}))
                        n_pov += 1
        if n_ots < int(cO.get('max_candidatas', 1)) and len(objs) == 1:
            S = _hombro(q, caras[0]) or (Mq['ojos'] - Vector((0, 0, 0.15 * Hq)))
            side = Vector((-u.y, u.x, 0)); side = side.normalized() if side.length > 1e-4 else Vector((1, 0, 0))
            if (S - Mq['cabeza']).dot(side) < 0: side = -side
            uh = Vector((u.x, u.y, 0)); uh = uh.normalized() if uh.length > 1e-4 else Mq['frente']
            C = S - uh * float(cO.get('atras_x_altura', 0.22)) * Hq + side * float(cO.get('afuera_x_altura', 0.14)) * Hq + Vector((0, 0, float(cO.get('arriba_x_altura', 0.06)) * Hq))
            if not holgura_cine(C, dg, f, excl=(q,)):
                le = float(cO.get('lente_mm', 40)); R = mirar(C, caras[0], 0.0, le); en, lb, fr_ = cara_libre(dg, C, R, le, objs[0], f, excl=(q,))
                if en and lb:
                    out.append(_cand('OTS', C, 'PM', 'NORM', le, mira_pj=objs[0], claves=objs, dueno=q, extra={"busqueda": {"hombro_de": q, "mira_a": objs[0], "frac_cara_libre": round(fr_, 2)}}))
                    n_ots += 1
    return out

def gen_retirada(V, f, disp=()):
    """empieza en la cámara de frente (PP) del personaje y se aleja SUBIENDO hasta el techo o una pared (lo que se cruce primero),
    probando varios azimutes/elevaciones; gana el recorrido libre más largo con la cara aún visible al final. Con contraste de tamaño
    el personaje es el MÁS CHICO del cuadro (el que se quiere mostrar pequeño); si no, el objetivo."""
    cfg = FAM['familias']['RETIRADA']; dg = bpy.context.evaluated_depsgraph_get()
    pres = [q for q in V['en_cuadro'] if med(q, f)]
    p = min(pres, key=lambda q: med(q, f)['altura']) if ('contraste_tamano' in disp and pres) else V['obj']
    M = med(p, f)
    if not M: return []
    for pl0 in cfg.get('planos_inicio') or ['PP', 'PMC', 'PM']:   # si una salida choca en la viñeta, se prueba desde un plano más abierto
        res_ = _retirada_desde(V, f, p, M, pl0, cfg, dg)
        if res_: return res_
    return []

def _ruta_libre(V, p, C0, C1, fm):
    """la ruta C0->C1 (como la mueve pose_ruta: suave + acompaña al sujeto) revisada en los cuadros de búsqueda de la viñeta."""
    f0, f1 = V['f0'], V['f1']; Mm = med(p, fm); ok_ = True
    for fq in V.get('_fq') or []:
        Mq = med(p, fq)
        if not Mq or not Mm: continue
        sq = suave((fq - f0) / max(1, f1 - f0)); Cq = C0.lerp(C1, sq) + Vector((Mq['ojos'].x - Mm['ojos'].x, Mq['ojos'].y - Mm['ojos'].y, 0))
        sc.frame_set(fq); dgq = bpy.context.evaluated_depsgraph_get()
        if holgura_cine(Cq, dgq, fq): ok_ = False; break
    if sc.frame_current != fm: sc.frame_set(fm)
    return ok_

def _retirada_desde(V, f, p, M, pl0, cfg, dg):
    r, _ = cam_principal(dict(V, obj=p), p, pl0, 'NORM', f)
    if not r: return []
    C0, le0, info0 = r; E = M['ojos']; u0 = Vector((C0.x - E.x, C0.y - E.y, 0)); u0 = u0.normalized() if u0.length > 1e-4 else M['frente']
    d0 = (C0 - E).length; mejor = None; lf = float(cfg.get('lente_fin_mm', 24))
    for off in cfg.get('arco_deg') or [0, 30, -30, 60, -60, 90, -90]:
        a = math.radians(off); u = Vector((u0.x * math.cos(a) - u0.y * math.sin(a), u0.x * math.sin(a) + u0.y * math.cos(a), 0))
        for el in cfg.get('elev_fin_deg') or [35, 50, 65]:
            dvec = (u * math.cos(math.radians(el)) + Vector((0, 0, math.sin(math.radians(el))))).normalized()
            hit, loc, nor, idx, ob, mx = sc.ray_cast(dg, E + dvec * 0.02, dvec, distance=30.0)
            L = ((loc - E).length if hit else 30.0) - 0.2; C1 = E + dvec * max(0.0, L)
            for _ in range(60):
                if dentro_cuarto(C1) or (C1 - E).length < 0.05: break
                C1 = E + (C1 - E) * 0.93
            if (C1 - E).length < float(cfg.get('dist_fin_x_inicio', 2.5)) * d0: continue
            if holgura_cine(C1, dg, f): continue
            mid = C0.lerp(C1, 0.5)
            if holgura_cine(mid, dg, f): continue
            R1 = mirar(C1, E, 0.0, lf); en, lb, _ = cara_libre(dg, C1, R1, lf, p, f)
            if not en or not lb: continue
            rec = (C1 - C0).length
            if mejor is None or rec > mejor[1]:
                if _ruta_libre(V, p, C0, C1, f): mejor = (C1, rec, el, off)
                dg = bpy.context.evaluated_depsgraph_get()
    if not mejor: return []
    C1, rec, el, off = mejor
    return [_cand('RETIRADA', C0, pl0, 'NORM', le0, mira_pj=p, ruta=[C0, C1], miras=[p, p], lentes=[le0, lf], claves=[p],
                  extra={"busqueda": dict(info0, recorrido_m=round(rec, 2), elev_fin_deg=el, az_fin_deg=off, personaje=p,
                                          termina_en='techo' if C1.z > INT['hi'][2] - 0.4 else 'pared')})]

def gen_pase_caras(V, f):
    cfg = FAM['familias']['PASE_CARAS']; dg = bpy.context.evaluated_depsgraph_get(); pl = cfg.get('plano', 'PMC'); le = float(cfg.get('lente_mm', 50))
    qs = [q for q in V['en_cuadro'] if med(q, f)]
    if len(qs) < 2: return []
    fs = [med(q, f)['frente'] for q in qs]; fb = sum(fs, Vector()); fb = fb.normalized() if fb.length > 1e-3 else fs[0]
    ax = Vector((0, 0, 1)).cross(fb).normalized(); qs.sort(key=lambda q: med(q, f)['ojos'].dot(ax))
    ruta = []; miras = []
    for q in qs:
        r, _ = cam_principal(dict(V, en_cuadro=[q]), q, pl, 'NORM', f, lente=le)
        if not r: continue
        C, l_, info = r; ruta.append(C); miras.append(q)
    if len(ruta) < 2: return []
    ext = (ruta[-1] - ruta[0]).normalized() * 0.15 * (ruta[-1] - ruta[0]).length
    ruta = [ruta[0] - ext] + ruta + [ruta[-1] + ext]; miras = [miras[0]] + miras + [miras[-1]]
    ruta = [C if dentro_cuarto(C) else ruta[i + 1 if i == 0 else i - 1] for i, C in enumerate(ruta)]
    return [_cand('PASE_CARAS', ruta[0], pl, 'NORM', le, mira_pj=miras[0], ruta=ruta, miras=miras, lentes=[le] * len(ruta), claves=miras[1:-1],
                  extra={"busqueda": {"caras": miras[1:-1], "recorrido_m": round(sum((ruta[i + 1] - ruta[i]).length for i in range(len(ruta) - 1)), 2)}})]

# ---------------------------------------------------------------- movimiento por ruta (RETIRADA / PASE_CARAS) y seguimiento del dueño
def pose_ruta(V, c, mov, f):
    f0, f1 = V['f0'], V['f1']; s = suave((f - f0) / max(1, f1 - f0)); pts = [Vector(x) for x in c['ruta']]; n = len(pts) - 1
    x = s * n; i = min(n - 1, int(x)); t = x - i; C = pts[i].lerp(pts[i + 1], t)
    miras = c.get('miras') or [c.get('mira_pj')] * len(pts); fm = (f0 + f1) // 2
    def ojo(q, fr): M = med(q, fr); return M['ojos'] if M else None
    Ta, Tb = ojo(miras[i], f), ojo(miras[min(i + 1, len(miras) - 1)], f)
    T = Ta.lerp(Tb, t) if (Ta is not None and Tb is not None) else (Ta if Ta is not None else Tb)
    if T is None: T = pts[-1]
    if c.get('seguir') and c.get('mira_pj'):
        a, b = ojo(c['mira_pj'], f), ojo(c['mira_pj'], fm)
        if a is not None and b is not None: C = C + Vector((a.x - b.x, a.y - b.y, 0))
    ls = c.get('lentes') or [c['lente']] * len(pts); le = ls[i] + (ls[min(i + 1, len(ls) - 1)] - ls[i]) * t
    C.z = min(max(C.z, INT['lo'][2] + 0.05), INT['hi'][2] - 0.10)
    return C, mirar(C, T, 0.0, le), le, T

# ---------------------------------------------------------------- validación de Ricardo (reemplaza vis_min 0,9 del cuerpo)
def claves_en(c, V, f, T=None):
    if c.get('familia') == 'PASE_CARAS' and T is not None:
        qs = [q for q in (c.get('claves') or []) if med(q, f)]
        return [min(qs, key=lambda q: (med(q, f)['ojos'] - T).length)] if qs else []
    return [q for q in (c.get('claves') or [V['obj']]) if med(q, f)]
def evaluar_cine(V, intentos, frames):
    res = [{"poses": {}, "m": []} for _ in intentos]; fm = (V['f0'] + V['f1']) // 2
    refs = [pose_base(V, it['c'], fm) for it in intentos]
    for f in frames:
        sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
        for i, it in enumerate(intentos):
            if refs[i] is None: continue
            C, R, le, T = pose_mov(V, it['c'], it['mov'], f, refs[i]); res[i]['poses'][f] = (C, R, le)
            c = it['c']; ex = (c['dueno'],) if c.get('dueno') else ()
            h = holgura_cine(C, dg, f, ex); ks = claves_en(c, V, f, T); cs = [cara_libre(dg, C, R, le, q, f, ex) for q in ks]
            res[i]['m'].append({"f": f, "choque": h, "claves": ks, "en": [x[0] for x in cs], "libre": [x[1] for x in cs], "frac": [round(x[2], 2) for x in cs],
                                "lado": lado(C, V['eje_k'][0], V['eje_k'][1], f) if V.get('eje_k') else 0,
                                "d": [round((C - med(q, f)['ojos']).length, 3) for q in ks], "dmin": [round(d_minimo(q, f), 3) for q in ks],
                                "el": math.degrees(math.asin(max(-1, min(1, (C - T).z / max(1e-3, (C - T).length)))))})
    return refs, res
def veredicto_cine(V, it, ref, R_, prev=None):
    m = R_['m']; c = it['c']
    if not m or ref is None: return {"ok": False, "fallas": ["sin pose"]}
    fallas = []; notas = []; n = len(m)
    ch = [x['choque'] for x in m if x['choque']]
    if ch: fallas.append(f"lente dentro/pegado a {ch[0][0]} ({ch[0][2]}) en {len(ch)}/{n} cuadros")
    grupo_ = c.get('familia') in ('GENERAL', 'PAISAJE') or (c.get('familia') == 'POV' and len(c.get('claves') or []) > 1)
    if grupo_:
        fe = [sum(x['en']) / max(1, len(x['en'])) for x in m]; fl = [sum(1 for e, l in zip(x['en'], x['libre']) if e and l) for x in m]
        gmin = float(FV.get('grupo_cabezas_en_cuadro_min', 0.5))
        if sum(fe) / n < gmin: fallas.append(f"solo {sum(fe) / n:.0%} de las caras del grupo en cuadro (mínimo {gmin:.0%})")
        if sum(1 for x in fl if x >= 1) / n < float(FV.get('cara_libre_frac_cuadros_min', 0.85)): fallas.append("ninguna cara del grupo libre en muchos cuadros")
        en_f = sum(fe) / n; lib_f = sum(1 for x in fl if x >= 1) / n
    else:
        en_f = sum(1 for x in m if x['en'] and x['en'][0]) / n; lib_f = sum(1 for x in m if x['libre'] and x['libre'][0]) / n
        if en_f < float(FV.get('cara_en_cuadro_frac_min', 0.95)): fallas.append(f"cara clave en cuadro {en_f:.0%}")
        if lib_f < float(FV.get('cara_libre_frac_cuadros_min', 0.85)): fallas.append(f"cara clave tapada del todo en {1 - lib_f:.0%} de los cuadros")
    # [t559u] más cerca que d_min de la clave (tolerancia de FV['d_min_tolerancia'], por defecto 0,9)
    tol = float(FV.get('d_min_tolerancia', 0.9))
    cerca = [x for x in m if any(d < tol * dm for d, dm in zip(x.get('d') or [], x.get('dmin') or []))]
    if cerca:
        x0 = cerca[0]; fallas.append(f"cámara a {min(x0['d']):.2f} m de la clave, más cerca que d_min {min(x0['dmin']):.2f} m en {len(cerca)}/{n} cuadros")
    # [t559u] eje 180°: falla si cruza en la mayoría de cuadros SIN motivo (sin alternativa del lado bueno, POV subjetivo, movimiento orbital o motivo_cruce)
    ls = V.get('lado_escena')
    if ls:
        mal = sum(1 for x in m if x['lado'] and x['lado'] != ls)
        if mal:
            motivo = ('sin cámara posible del lado del eje' if (c.get('cruza_eje') or (c.get('busqueda') or {}).get('cruza_eje') or V.get('aviso_eje')) else
                      'POV subjetivo' if c.get('familia') == 'POV' else 'movimiento orbital' if str(it.get('mov') or '').upper().startswith(('ORBIT', 'ARC')) else
                      (it.get('motivo_cruce') or c.get('motivo_cruce')))
            if mal / n > float(FV.get('eje_frac_max', 0.5)) and not motivo: fallas.append(f"cruza el eje 180° sin motivo en {mal}/{n} cuadros")
            else: notas.append(f"cruza el eje 180° en {mal}/{n} cuadros" + (f" (motivo: {motivo})" if motivo else ''))
    elm = [x['el'] for x in m]
    return {"ok": not fallas, "fallas": fallas, "notas": notas, "cara_en_cuadro": round(en_f, 3), "cara_libre": round(lib_f, 3),
            "vis_media": round(lib_f, 3), "vis_min": round(min((min(x['frac']) if x['frac'] else 0) for x in m), 3), "cabeza_en_cuadro": round(en_f, 3),
            "elev_deg": [round(min(elm), 1), round(max(elm), 1)], "oclusores_n0": [], "n3_a_ocultar": [], "n2_recortados": []}
def evaluar_x(V, intentos, frames):
    return evaluar_cine(V, intentos, frames) if CINE and intentos and intentos[0]['c'].get('familia') else evaluar(V, intentos, frames)
def veredicto_x(V, it, ref, R_, prev):
    return veredicto_cine(V, it, ref, R_, prev) if CINE and it['c'].get('familia') else veredicto(V, it, ref, R_, prev)

# ---------------------------------------------------------------- candidatas por viñeta (familias) + validación en TODA la viñeta
def candidatas_cine(V):
    i = VIN.index(V); fm = (V['f0'] + V['f1']) // 2; disp = disparadores(i); tab = reglas_tabla(V, disp)
    _all = list(range(V['f0'], V['f1'] + 1, max(1, A.paso_val))) + [V['f1']]; _nq = int(FAM.get('cuadros_busqueda', 0)) or len(_all)   # [cine_v1] búsqueda = validación (0 = todos los cuadros que se validan)
    _nq = min(_nq, len(_all))
    V['_fq'] = sorted({_all[int(round(j * (len(_all) - 1) / max(1, _nq - 1)))] for j in range(_nq)} - {fm}); sc.frame_set(fm)
    fams = FAM.get('familias') or {}; activas = set(tab['familias'])
    for nm, cf in fams.items():
        if set(cf.get('cuando') or []) & disp: activas.add(nm)
    V['disparadores'] = sorted(disp); V['familias_activas'] = sorted(activas); V['tabla_reglas'] = tab['reglas']
    V['tabla_specs'] = [{k: v for k, v in sp.items() if k != 'familias'} | {"familias": sorted(sp['familias'])} for sp in tab.get('specs') or []]
    crudas = []
    if 'PRINCIPAL' in activas: crudas += gen_principal(V, fm, disp, tab)
    if 'GENERAL' in activas: crudas += gen_general(V, fm, 'GENERAL')
    if 'PAISAJE' in activas: crudas += gen_general(V, fm, 'PAISAJE')
    if 'POV' in activas or 'OTS' in activas: crudas += [c for c in gen_pov_ots(V, fm, disp) if c['familia'] in activas]
    if 'RETIRADA' in activas: crudas += gen_retirada(V, fm, disp)
    if 'PASE_CARAS' in activas: crudas += gen_pase_caras(V, fm)
    frames = sorted(set(list(range(V['f0'], V['f1'] + 1, max(1, A.paso_val))) + [V['f1']]))
    mv_sb = mov_sb(V); out = []; desc = []
    for k, c in enumerate(crudas):
        c['id'] = f"K{k + 1}"
        # [cine_v1] si el sujeto se desplaza, la cámara base lo ACOMPAÑA (STEADICAM suave: misma distancia, sigue al sujeto); si no, fija
        base_mv = 'TRAYECTO' if c.get('ruta') else ('STEADICAM' if ('desplazamiento' in disp and c.get('seguir') and not c.get('dueno')) else 'STATIC')
        mov = {"movimiento": base_mv, "intensidad": 0.2}
        it = {"c": c, "mov": mov, "obj": V['obj']}; refs, res = evaluar_cine(V, [it], frames); ver = veredicto_cine(V, it, refs[0], res[0])
        if not ver['ok']: desc.append({"familia": c['familia'], "plano": c['plano'], "fallas": ver['fallas'][:2]}); continue
        rf = refs[0]; mid = res[0]['m'][len(res[0]['m']) // 2]
        sug = c.get('movimiento_tabla') or (None if c.get('ruta') else mv_sb); mov_ok = [base_mv]
        if sug and not c.get('ruta') and str(sug).upper() not in ('STATIC', 'TRAYECTO', base_mv):   # el movimiento sugerido también se mide
            it2 = {"c": c, "mov": {"movimiento": str(sug).upper(), "intensidad": 0.5}, "obj": V['obj']}; r2_, s2_ = evaluar_cine(V, [it2], frames)
            v2_ = veredicto_cine(V, it2, r2_[0], s2_[0])
            if v2_['ok']: mov_ok.append(str(sug).upper())
            else: desc.append({"familia": c['familia'], "plano": c['plano'], "movimiento": sug, "fallas": v2_['fallas'][:1]}); sug = None
        if base_mv == 'STEADICAM' and not sug: sug = 'STEADICAM'
        out.append({"movimientos_validos": mov_ok, "plano": c['plano'], "angulo": c['angulo'], "az_off": 0, "lente": c['lente'], "familia": c['familia'], "pos": [round(x, 2) for x in c['C']],
                    "mira": [round(x, 2) for x in rf['T']], "dist_m": round(rf['d'], 2), "az_deg": round(rf['az'], 1), "el_deg": round(mid['el'], 1),
                    "elev_rango_deg": ver['elev_deg'], "movimiento_sb": mv_sb, "trayecto": bool(c.get('ruta')), "dueno": c.get('dueno'), "claves": c.get('claves'),
                    "busqueda": c.get('busqueda'), "cruza_eje": bool((c.get('busqueda') or {}).get('cruza_eje')), "fuera_recinto": False,
                    "beat": c.get('beat'), "origen": c.get('origen'), "movimiento_sugerido": sug,
                    "c_motor": c, "val3d": _resumen(ver) | {"cara_en_cuadro": ver['cara_en_cuadro'], "cara_libre": ver['cara_libre'], "elev_deg": ver['elev_deg']}})
    # variedad: al menos una de cada familia disponible, luego PRINCIPAL; tope por viñeta
    mx = int(FAM.get('max_candidatas_por_vineta', 8)); el_ = []
    for fam in ('PRINCIPAL', 'GENERAL', 'POV', 'RETIRADA', 'PASE_CARAS', 'OTS', 'PAISAJE'):
        x = next((c for c in out if c['familia'] == fam and c not in el_), None)
        if x: el_.append(x)
    for c in out:   # POV/OTS: también la mirada del otro lado del par (p. ej. el chico mirando hacia arriba al grande)
        if c['familia'] in ('POV', 'OTS') and c not in el_ and not any(e['familia'] == c['familia'] and e.get('dueno') == c.get('dueno') for e in el_):
            el_.append(c)
    for c in out:   # al menos una candidata por cada beat de la tabla
        if c.get('beat') and c not in el_ and not any(e.get('beat') == c['beat'] for e in el_): el_.append(c)
    el_ += [c for c in out if c not in el_]; el_ = el_[:mx]
    for j, c in enumerate(el_): c['id_motor'] = c['c_motor']['id']; c['id'] = f"C{j + 1}"; c['c_motor']['id'] = c['id']
    V['descartadas'] = desc; V['rechazos'] = V.get('rech_cine')
    log('cine', V['id'], 'disparadores', sorted(disp), 'familias', sorted(activas), 'crudas', len(crudas), 'válidas', len(out), 'ofrecidas', len(el_), ('descartadas ' + json.dumps(desc, ensure_ascii=False)[:900]) if not el_ else '')
    return el_, len(crudas), len(out)

if A.modo == 'paquete': modo_paquete()
elif A.modo == 'video': modo_video()
else: modo_aplicar()
_OK = True
