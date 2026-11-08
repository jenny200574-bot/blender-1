"""MOTOR · cámara v2 (fase 4g). Se corre DENTRO de Blender sobre la escena YA ARMADA (no cambia animación de personajes ni ADN):
  blender -b RUN/escena.blend -P camara_v2_blender.py -- ENTRADA.json SB_CAMARA.json SB_ESCENA.json|- CFG.json AJUSTES_SB.json SALIDA_DIR
Funciones (cada una con su interruptor .off junto a este archivo):
  manifiesto_espacial  mide en el .blend evaluado altura, cabeza, frente y región del plano por actor y tiempo (avisa si difiere del ADN).
  resolver_camara      emplaza la cámara desde plano/ángulo/orientación del SB, del lado de la cara, distancia por proyección + ajuste NDC,
                       eje A-B real cuando es identificable; PAN/ORBIT/TILT/TRACK/CRANE solo con datos reales (si no: faltante).
  validacion_camara    revisión gratis por muestras: dentro de geometría, oclusión (BVH ray_cast), región en cuadro, cara visible, eje;
                       reparación acotada; si no hay solución la toma queda BLOQUEADA con su motivo.
Si resolver_camara.off: se valida la cámara existente (CAMARA_ENTRADA) sin cambiarla.
Universal: sin nombres de canal, escena ni personaje; todo sale de los datos y de camara_v2_config.json."""
import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector, Matrix, Euler
from mathutils.bvhtree import BVHTree
from bpy_extras.object_utils import world_to_camera_view as w2c

AQUI = Path(__file__).resolve().parent
OFF = lambda n: (AQUI / f'{n}.off').exists()
a = sys.argv[sys.argv.index('--') + 1:]
E = json.load(open(a[0])); SBC = json.load(open(a[1])); SBE = json.load(open(a[2])) if a[2] != '-' and Path(a[2]).is_file() else None
CFG = json.load(open(a[3])); AJ = json.load(open(a[4])); OUT = Path(a[5]); OUT.mkdir(parents=True, exist_ok=True)
SW = {'manifiesto_espacial': not OFF('manifiesto_espacial'), 'resolver_camara': not OFF('resolver_camara'), 'validacion_camara': not OFF('validacion_camara')}
sc = bpy.context.scene; FPS = sc.render.fps / sc.render.fps_base
RX, RY = sc.render.resolution_x * sc.render.pixel_aspect_x, sc.render.resolution_y * sc.render.pixel_aspect_y; ASP = RX / RY
TABLA = AJ['encuadre_fraccion_altura_visible']; UP = Vector((0, 0, 1))
FALT = []; AVISOS = []
def F(campo, modulo, accion, mensaje, toma=None): FALT.append({'campo': campo, 'modulo': modulo, 'accion': accion, 'mensaje': mensaje, 'toma': toma})
def fr(t): return 1 + round(float(t) * FPS)
def fr_fin(t): return round(float(t) * FPS)
r3 = lambda v: [round(float(x), 4) for x in v]
# visibilidades de render del paquete (las mismas que usa el render)
for name, vis in (E.get('environment') or {}).get('visibility', {}).items():
    o = bpy.data.objects.get(name)
    if o: o.hide_render = not vis
CAM = sc.camera
if CAM is None: raise SystemExit('sin cámara en la escena')
SENSOR_W = float(CAM.data.sensor_width)
ACT = {o.name: o for o in bpy.data.objects if o.type == 'ARMATURE'}
def mallas(root):
    return [x for x in [root] + list(root.children_recursive) if x.type == 'MESH' and not x.hide_render]
ACT_MESH = {pid: mallas(o) for pid, o in ACT.items()}
ACT_SET = {m.name for ms in ACT_MESH.values() for m in ms}
ENV = [o for o in sc.objects if o.type == 'MESH' and not o.hide_render and o.name not in ACT_SET]
class _BV:
    def __init__(s, t, own): s.t = t; s.own = own
    def ray_cast(s, *a): return s.t.ray_cast(*a)
    def find_nearest(s, *a): return s.t.find_nearest(*a)
    def quien(s, idx): return s.own[idx] if idx is not None and 0 <= idx < len(s.own) else None
def bvh(objs, dg):
    V, P, own = [], [], []
    for o in objs:
        e = o.evaluated_get(dg); m = e.to_mesh(); n = len(V); mw = o.matrix_world
        V += [mw @ v.co for v in m.vertices]; P += [tuple(i + n for i in p.vertices) for p in m.polygons]; own += [o.name] * len(m.polygons); e.to_mesh_clear()
    return _BV(BVHTree.FromPolygons(V, P), own) if P else None
def dentro_de_malla(bv, p):
    """Punto dentro de un volumen cerrado: en la mayoría de 6 direcciones lo primero que se toca es una cara vista por detrás."""
    if bv is None: return None
    n = 0
    for d in (Vector((1,0,0)), Vector((-1,0,0)), Vector((0,1,0)), Vector((0,-1,0)), Vector((0,0,1)), Vector((0,0,-1))):
        h = bv.ray_cast(p, d, 1000)
        if h[0] is not None and h[1].dot(d) > 0: n += 1
    return bv.quien(bv.ray_cast(p, Vector((0,0,1)), 1000)[2]) if n >= 4 else None
def verts(objs, dg, cada=1):
    out = []
    for o in objs:
        e = o.evaluated_get(dg); m = e.to_mesh(); mw = o.matrix_world
        out += [mw @ v.co for v in m.vertices[::cada]]; e.to_mesh_clear()
    return out
# ---------------- manifiesto espacial ----------------
CACHE = {}
def medir(pid, f):
    k = (pid, f)
    if k in CACHE: return CACHE[k]
    sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); A = ACT.get(pid)
    if A is None:   # objetivo objeto: caja real
        o = bpy.data.objects.get(pid)
        if o is None: CACHE[k] = None; return None
        ms = mallas(o); P = verts(ms, dg)
        if not P: CACHE[k] = None; return None
        lo = Vector([min(p[i] for p in P) for i in range(3)]); hi = Vector([max(p[i] for p in P) for i in range(3)])
        c = (lo + hi) / 2; acts = [x.matrix_world.translation for x in ACT.values()]; fv = None
        if acts:
            d = sum(acts, Vector()) / len(acts) - c; d.z = 0
            if d.length > 1e-6: fv = d.normalized()
        CACHE[k] = {'tipo': 'objeto', 'zmin': lo.z, 'zmax': hi.z, 'H': hi.z - lo.z, 'centro': c, 'cabeza': None, 'frente': fv,
                    'frente_metodo': 'objeto: hacia el centro de los personajes construidos (no tiene cara)' if fv else None, 'puntos': P, 'mallas': [m.name for m in ms]}
        return CACHE[k]
    ms = ACT_MESH[pid]; P = verts(ms, dg); R = CFG['roles_hueso']
    zmin = min(p.z for p in P); zmax = max(p.z for p in P)
    cab_m = [m for m in ms if m.parent_type == 'BONE' and m.parent_bone in R['cabeza']]
    cab = None
    if cab_m:
        HP = verts(cab_m, dg); lo = Vector([min(p[i] for p in HP) for i in range(3)]); hi = Vector([max(p[i] for p in HP) for i in range(3)])
        cab = {'centro': (lo + hi) / 2, 'alto': hi.z - lo.z, 'top': hi.z, 'puntos': HP}
    fr_v = None; metodo = None; pb = A.pose.bones
    pies = [n for n in R['pies'] if n in pb]
    if CFG.get('frente_rig') == 'pies' and pies:
        d = sum([(A.matrix_world @ pb[n].tail) - (A.matrix_world @ pb[n].head) for n in pies], Vector()); d.z = 0
        if d.length > 1e-6: fr_v = d.normalized(); metodo = 'huesos de pie (talón→punta)'
    if fr_v is None:
        d = A.matrix_world.to_3x3() @ Vector((0, 1, 0)); d.z = 0
        if d.length > 1e-6: fr_v = d.normalized(); metodo = 'eje +Y local del armature'
    pel = A.matrix_world.translation
    if not SW['manifiesto_espacial'] and isinstance(ADN_H.get(pid), (int, float)): zmax = zmin + ADN_H[pid]   # camino anterior: altura ADN
    CACHE[k] = {'tipo': 'personaje', 'zmin': zmin, 'zmax': zmax, 'H': zmax - zmin, 'centro': Vector((pel.x, pel.y, (zmin + zmax) / 2)), 'cabeza': cab,
                'frente': fr_v, 'frente_metodo': metodo, 'puntos': P, 'mallas': [m.name for m in ms]}
    return CACHE[k]
# ---------------- SB ----------------
SBV = {v['id']: v for v in (SBE or {}).get('vinetas', [])}
SHOTS_E = {s.get('vineta'): s for s in (E.get('camera') or {}).get('shots', [])}
ADN_H = {x['id']: (x.get('spec') or {}).get('altura_m') for x in E.get('actors', [])}
def orient_deg(txt):
    t = (txt or '').lower()
    for r in CFG['orientacion_a_acimut']:
        if all(c in t for c in r['contiene']): return r['grados']
    return None
def eje_par(s):
    if not s: return None
    for A_ in sorted(ACT, key=len, reverse=True):
        if s.startswith(A_ + '-'):
            B_ = s[len(A_) + 1:]
            return (A_, B_) if B_ in ACT else ('ambiguo', A_, B_)
    return ('ambiguo', None, s)
# ---------------- cámara: proyección propia (pinhole, sensor horizontal) ----------------
def look_rot(loc, tgt):
    return (tgt - loc).to_track_quat('-Z', 'Y').to_matrix()
def proyectar(p, loc, R, lens):
    c = R.transposed() @ (p - loc)
    if c.z >= -1e-6: return None
    k = lens / SENSOR_W
    return (0.5 + k * c.x / -c.z, 0.5 + k * ASP * c.y / -c.z, -c.z)
def sensor_h(): return SENSOR_W / ASP
def region(m, plano):
    """Región anatómica MEDIDA que debe caber para el plano: (top, bottom, centro_xy, alto_cuadro)."""
    frac = TABLA.get(plano)
    if frac is None: return None
    Hf = frac * m['H']
    if frac >= 1 or m['tipo'] == 'objeto':
        return {'top': m['zmax'], 'bot': m['zmin'], 'xy': m['centro'], 'Hf': max(Hf, m['H']), 'cuerpo_entero': True}
    xy = m['cabeza']['centro'] if m['cabeza'] else m['centro']
    return {'top': m['zmax'], 'bot': max(m['zmin'], m['zmax'] - Hf * (1 - CFG['aire_cabeza_ndc'])), 'xy': xy, 'Hf': Hf, 'cuerpo_entero': False}
def emplazar(m, plano, lens, elev, az_off, xlado, fdist=1.0):
    """Cámara que encuadra la región del plano: distancia inicial por proyección y ajuste NDC (3 iteraciones)."""
    rg = region(m, plano)
    if rg is None: return None, f'plano {plano} sin fila en la tabla de encuadre'
    fv = m['frente']
    if fv is None: return None, 'objetivo sin frente medible'
    right = fv.cross(UP).normalized(); az = math.radians(az_off); e = math.radians(elev)
    d_h = (fv * math.cos(az) + right * math.sin(az)).normalized()
    dirc = (d_h * math.cos(e) + UP * math.sin(e)).normalized()
    D = rg['Hf'] * lens / sensor_h()
    look = Vector((rg['xy'].x, rg['xy'].y, (rg['top'] + rg['bot']) / 2 if rg['cuerpo_entero'] else rg['top'] - rg['Hf'] / 2))
    for _ in range(4):
        loc = look + dirc * D; R = look_rot(loc, look)
        pt = proyectar(Vector((rg['xy'].x, rg['xy'].y, rg['top'])), loc, R, lens); pb_ = proyectar(Vector((rg['xy'].x, rg['xy'].y, rg['bot'])), loc, R, lens)
        if not pt or not pb_: break
        span = pt[1] - pb_[1]
        want = (rg['top'] - rg['bot']) / rg['Hf'] if not rg['cuerpo_entero'] else m['H'] / rg['Hf']
        if span > 1e-6: D *= span / want
        # vertical y horizontal con los PUNTOS MEDIDOS (perspectiva real): cabeza en planos cortos, cuerpo en planos abiertos
        loc = look + dirc * D; R = look_rot(loc, look)
        ref = (m['cabeza']['puntos'] if (not rg['cuerpo_entero'] and m['cabeza']) else m['puntos'])[::max(1, len(m['puntos']) // 300)]
        qs = [q for q in (proyectar(x, loc, R, lens) for x in ref) if q]
        if not qs: break
        vt = max(q[1] for q in qs); vb = min(q[1] for q in qs); uc = (max(q[0] for q in qs) + min(q[0] for q in qs)) / 2
        if rg['cuerpo_entero']: look.z += ((vt + vb) / 2 - 0.5) * (D * sensor_h() / lens)
        else: look.z += (vt - (1 - CFG['aire_cabeza_ndc'])) * (D * sensor_h() / lens)
        look -= (R @ Vector((1, 0, 0))) * (xlado - uc) * (D * SENSOR_W / lens)
    D *= fdist
    loc = look + dirc * D
    return {'loc': loc, 'look': look, 'lens': lens, 'D': D, 'az_off': az_off, 'elev': elev, 'dir': dirc}, None
# ---------------- validación por muestras ----------------
def muestras(f0, f1):
    n = max(2, int((f1 - f0 + 1) / FPS * CFG['muestras_por_s']) + 1)
    return sorted({f0, f1} | {round(f0 + (f1 - f0) * i / (n - 1)) for i in range(n)})
CTX = {}
def ctx_frame(f, tgt):
    k = (f, tgt)
    if k in CTX: return CTX[k]
    sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
    otros = [m for pid, ms in ACT_MESH.items() if pid != tgt for m in ms]
    m = medir(tgt, f)
    CTX[k] = {'env': bvh(ENV, dg), 'otros': bvh(otros, dg), 'm': m}
    return CTX[k]
def bloqueado_rayo(bv, a_, b_):
    if bv is None: return False
    d = b_ - a_; h = bv.ray_cast(a_, d.normalized(), max(0, d.length - 0.01))
    return h[0] is not None
def pose_en(keys, f):
    if f <= keys[0]['f']: k = keys[0]; return k['loc'], k['R'], k['lens']
    for k0, k1 in zip(keys, keys[1:]):
        if k0['f'] <= f <= k1['f']:
            u = (f - k0['f']) / max(1, k1['f'] - k0['f'])
            e0 = k0['R'].to_euler('XYZ'); e1 = k1['R'].to_euler('XYZ', e0)
            e = Euler([e0[i] + (e1[i] - e0[i]) * u for i in range(3)], 'XYZ')
            return k0['loc'].lerp(k1['loc'], u), e.to_matrix(), k0['lens'] + (k1['lens'] - k0['lens']) * u
    k = keys[-1]; return k['loc'], k['R'], k['lens']
def validar(keys, tgt, plano_de, f0, f1, orient_pedida, eje_ref, libres=()):
    """libres = rangos de cuadros de PAN/TILT pedidos por el SB: ahí la cámara puede dejar al objetivo a propósito (solo se revisa geometría)."""
    malos = []; peor = {}
    for f in muestras(f0, f1):
        c = ctx_frame(f, tgt); m = c['m']; loc, R, lens = pose_en(keys, f)
        libre = any(a_ <= f <= b_ for a_, b_ in libres)
        D = (m['centro'] - loc).length
        hol = min(CFG['holgura_max_m'], CFG['holgura_frac_distancia'] * D, CFG['holgura_frac_altura'] * m['H'])
        if c['env']:
            nn = c['env'].find_nearest(loc); den = dentro_de_malla(c['env'], loc)
            if den: malos.append((f, f'cámara dentro de geometría del escenario ({den})', 0))
            elif nn[0] is not None and nn[3] < hol: malos.append((f, f'cámara pegada a geometría del escenario ({c["env"].quien(nn[2])})', round(nn[3], 3)))
        rg = region(m, plano_de(f)); pts = m['puntos']
        if rg and not rg['cuerpo_entero'] and m['cabeza']:
            # planos cortos: lo que DEBE verse es la cabeza dentro de la franja visible del plano (hombros/brazos pueden salir del cuadro)
            pts = [p for p in m['cabeza']['puntos'] if p.z >= rg['top'] - rg['Hf']] or m['cabeza']['puntos']
        elif rg: pts = [p for p in pts if rg['bot'] - 1e-3 <= p.z <= rg['top'] + 1e-3] or pts
        paso = max(1, len(pts) // CFG['puntos_region']); pts = pts[::paso]
        pr = [proyectar(p, loc, R, lens) for p in pts]
        dentro = [q for q in pr if q and 0 <= q[0] <= 1 and 0 <= q[1] <= 1]
        fr_in = len(dentro) / max(1, len(pr)); req = CFG['region_en_cuadro_min']
        if rg and not rg['cuerpo_entero'] and m['cabeza'] and rg['Hf'] < m['cabeza']['alto']: req *= rg['Hf'] / m['cabeza']['alto']   # plano más cerrado que la cabeza
        if fr_in < req and not libre: malos.append((f, 'región del plano fuera de cuadro', round(fr_in, 2)))
        tap = {}
        for p in pts:
            for bv, et in ((c['env'], 'escenario'), (c['otros'], 'otro personaje')):
                if bv is None: continue
                d = p - loc; h = bv.ray_cast(loc, d.normalized(), max(0, d.length - 0.01))
                if h[0] is not None: k_ = f'{et}: {bv.quien(h[2])}'; tap[k_] = tap.get(k_, 0) + 1; break
        fv = 1 - sum(tap.values()) / max(1, len(pts))
        if fv < CFG['visibilidad_min'] and not libre:
            malos.append((f, 'objetivo tapado (' + max(tap, key=tap.get) + ')', round(fv, 2)))
        if m['frente'] is not None and (orient_pedida is None or abs(orient_pedida) < 150):
            v = loc - (m['cabeza']['centro'] if m['cabeza'] else m['centro']); v.z = 0
            if v.length > 1e-6:
                ang = math.degrees(m['frente'].angle(v.normalized()))
                if ang > CFG['max_angulo_cara_deg']: malos.append((f, 'objetivo de espaldas a cámara', round(ang, 1)))
        if eje_ref:
            A_, B_, lado = eje_ref; pa = medir(A_, f)['centro']; pbb = medir(B_, f)['centro']
            s = (pbb.x - pa.x) * (loc.y - pa.y) - (pbb.y - pa.y) * (loc.x - pa.x)
            if lado and (s > 0) != (lado > 0): malos.append((f, 'cámara cruza el eje A-B del bloque', round(s, 3)))
    return malos
# ---------------- construcción por toma ----------------
def lens_de(v, t):
    ks = v.get('keyframes') or []; best = None
    for k in ks:
        if float(k['t']) <= t + 1e-6: best = k
    return float((best or ks[0])['lente_mm']) if ks else None
def plano_de_t(v, t):
    ks = v.get('keyframes') or []; best = None
    for k in ks:
        if float(k['t']) <= t + 1e-6: best = k
    return (best or ks[0])['plano'] if ks else None
def construir(v, cand, tgt, toma_id, notas):
    """Keyframes de la toma con los segmentos del SB. cand = (az_off, fdist). Movimientos solo con datos reales."""
    t0, t1 = map(float, v['t_abs']); f0, f1 = fr(t0), fr_fin(t1); keys = []
    elev = (SHOTS_E.get(v['vineta']) or {}).get('elevation_deg')
    xl = CFG['x_por_lado'].get(str(v.get('lado_objetivo') or 'C').upper(), CFG['x_por_lado']['C'])
    segs = v.get('segmentos') or [{'t_abs': [t0, t1], 'movimiento': 'STATIC', 'args': {}}]
    for i, s in enumerate(segs):
        a0, a1 = map(float, s['t_abs']); g0, g1 = max(f0, fr(a0)), min(f1, max(fr(a0), fr_fin(a1))); mv = s['movimiento']; ar = s.get('args') or {}
        if i == len(segs) - 1: g1 = f1
        m0 = medir(tgt, g0); p0 = plano_de_t(v, a0); L0 = lens_de(v, a0)
        if not keys:
            em, err = emplazar(m0, p0, L0, elev, cand[0], xl, cand[1])
            if err: return None, err
            keys.append({'f': g0, 'loc': em['loc'], 'R': look_rot(em['loc'], em['look']), 'lens': L0, 'look': em['look'], 'em': em})
        k = keys[-1]; loc, R, lens = k['loc'].copy(), k['R'].copy(), k['lens']
        if mv in ('DOLLYIN', 'DOLLYOUT') and ar.get('size_range'):
            m1 = medir(tgt, g1); em1, err = emplazar(m1, ar['size_range'][1], lens, elev, cand[0], xl, cand[1])
            if err: return None, err
            loc, R = em1['loc'], look_rot(em1['loc'], em1['look'])
        elif mv in ('ZOOMIN', 'ZOOMOUT', 'CRASHZOOM') and ar.get('size_range'):
            lens = lens * TABLA[ar['size_range'][0]] / TABLA[ar['size_range'][1]]
        elif mv in ('PAN', 'TILT', 'WHIPPAN'):
            g = ar.get('degrees')
            if isinstance(g, (int, float)):
                sgn = -1 if str(ar.get('dir_lr') or ar.get('dir_ud') or '').upper() in ('R', 'UP') else 1
                ax = UP if mv != 'TILT' else (R @ Vector((1, 0, 0)))
                if mv == 'TILT': sgn = -sgn
                n_ = max(1, math.ceil(abs(g) / 90)); R0 = R.copy()   # pasos ≤ 90° para no tomar el camino corto en cruces de ±180°
                for j in range(1, n_):
                    keys.append({'f': g0 + round((g1 - g0) * j / n_), 'loc': loc.copy(), 'R': Matrix.Rotation(math.radians(g) * sgn * j / n_, 3, ax) @ R0, 'lens': lens, 'look': k['look']})
                R = Matrix.Rotation(math.radians(g) * sgn, 3, ax) @ R0; notas.append(f'{mv} {g}° ejecutado (dato SB)')
            else:
                F(f'camera/{v["vineta"]}/segmentos[{i}]/{mv}.grados|anclas', 'SB (DSL /PAN:dir:grados) o 02N/4a2 (ancla inicial y final con ID espacial)',
                  'dar grados en el DSL o anclas inicio/fin enlazadas a IDs del .blend', f'{mv} sin grados ni anclas: no se ejecuta (cámara fija en ese tramo)', toma_id)
                notas.append(f'{mv} NO ejecutado: faltan grados/anclas')
        elif mv == 'ORBIT':
            g = ar.get('degrees')
            if isinstance(g, (int, float)):
                piv = k['look']; sgn = 1 if str(ar.get('dir_lr') or '').upper() == 'R' else -1   # registro: ORBIT:R = antihorario visto desde arriba
                n_ = max(1, math.ceil(abs(g) / 45)); L0, R0 = loc.copy(), R.copy()
                for j in range(1, n_):
                    Q = Matrix.Rotation(math.radians(g) * sgn * j / n_, 3, UP); keys.append({'f': g0 + round((g1 - g0) * j / n_), 'loc': piv + Q @ (L0 - piv), 'R': Q @ R0, 'lens': lens, 'look': k['look']})
                Q = Matrix.Rotation(math.radians(g) * sgn, 3, UP); loc = piv + Q @ (L0 - piv); R = Q @ R0; notas.append(f'ORBIT {g}° ejecutado (dato SB)')
            else:
                F(f'camera/{v["vineta"]}/segmentos[{i}]/ORBIT.grados', 'SB (DSL /ORBIT:dir:grados)', 'dar amplitud y sentido de la órbita', 'ORBIT sin amplitud: no se ejecuta', toma_id)
                notas.append('ORBIT NO ejecutado: falta amplitud')
        elif mv in ('TRACK', 'TRUCK'):
            m1 = medir(tgt, g1); dsp = m1['centro'] - m0['centro']; dsp.z = 0
            if dsp.length >= CFG['track_desplazamiento_min_m']:
                loc = loc + dsp; dr = (R @ Vector((1, 0, 0))).dot(dsp)
                pedido = str(ar.get('screen') or '').upper()
                if pedido in ('L2R', 'R2L') and ((dr > 0) != (pedido == 'L2R')): AVISOS.append(f'{toma_id}: TRACK pide {pedido} pero el objetivo se mueve al otro lado en pantalla (datos 01)')
                notas.append(f'TRACK ejecutado con el desplazamiento real del objetivo ({dsp.length:.2f} m)')
            else:
                F(f'camera/{v["vineta"]}/segmentos[{i}]/TRACK.desplazamiento', '01 (movimiento del sujeto) o SB (distancia del travelling)', 'dar recorrido lateral o mover al sujeto en el 01',
                  f'TRACK sin desplazamiento: el objetivo se mueve {dsp.length:.3f} m y el SB no da recorrido', toma_id); notas.append('TRACK NO ejecutado: falta recorrido')
        elif mv in ('CRANE', 'PEDESTAL', 'BOOM'):
            hgt = ar.get('meters') or ar.get('height_m')
            if isinstance(hgt, (int, float)):
                sgn = 1 if str(ar.get('dir_ud') or '').upper() == 'UP' else -1; loc = loc + UP * hgt * sgn; R = look_rot(loc, k['look']); notas.append(f'{mv} {hgt} m ejecutado')
            else:
                F(f'camera/{v["vineta"]}/segmentos[{i}]/{mv}.altura', 'SB (DSL con metros/encuadre final) o 02N (altura inicial y final)', 'dar extremos verticales del movimiento',
                  f'{mv} sin extremos verticales: no se ejecuta', toma_id); notas.append(f'{mv} NO ejecutado: faltan extremos')
        elif mv not in ('STATIC',):
            notas.append(f'{mv}: sin traducción en v2 (cámara fija en ese tramo)')
        keys.append({'f': g1, 'loc': loc, 'R': R, 'lens': lens, 'look': k['look']})
    return keys, None
def escribir(keys_por_toma):
    ob = CAM; cd = ob.data
    for blk in (ob, cd):
        if blk.animation_data: blk.animation_data_clear()
    ob.rotation_mode = 'XYZ'; prev = None; corte = set()
    for keys in keys_por_toma:
        for k in keys:
            e = k['R'].to_euler('XYZ', prev) if prev else k['R'].to_euler('XYZ'); prev = e
            ob.location = k['loc']; ob.rotation_euler = e; cd.lens = k['lens']
            ob.keyframe_insert('location', frame=k['f']); ob.keyframe_insert('rotation_euler', frame=k['f']); cd.keyframe_insert('lens', frame=k['f'])
        corte.add(keys[-1]['f'])
    for blk in (ob, cd):
        act = blk.animation_data.action
        for layer in act.layers:
            for strip in layer.strips:
                for slot in act.slots:
                    bag = strip.channelbag(slot)
                    if bag:
                        for fc in bag.fcurves:
                            for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT' if round(kp.co.x) in corte else 'LINEAR'
    dmin = min(min((k['loc'] - k['look']).length for k in ks) for ks in keys_por_toma)
    cd.clip_start = max(0.001, min(cd.clip_start, dmin * 0.25))
def keys_existentes(f0, f1):
    keys = []
    for f in sorted({f0, f1} | set(muestras(f0, f1))):
        sc.frame_set(f); mw = CAM.matrix_world
        keys.append({'f': f, 'loc': mw.translation.copy(), 'R': mw.to_3x3().normalized(), 'lens': CAM.data.lens, 'look': mw.translation + mw.to_3x3() @ Vector((0, 0, -1))})
    return keys
# ---------------- bucle de tomas ----------------
tomas = []; todas_keys = []; ref_eje = {}; manif = {}
for n, v in enumerate(sorted(SBC['vinetas'], key=lambda v: float(v['t_abs'][0])), 1):
    tid = f'toma{n:02d}'; t0, t1 = map(float, v['t_abs']); f0, f1 = fr(t0), fr_fin(t1); tgt = v.get('objetivo'); notas = []
    T = {'toma': n, 'vineta': v['vineta'], 't0': t0, 't1': t1, 'frame_ini': f0, 'frame_fin': f1, 'objetivo': tgt, 'estado': None, 'motivos': [], 'notas': notas}
    m0 = medir(tgt, f0) if tgt else None
    if m0 is None:
        T['estado'] = 'bloqueada'; T['motivos'].append(f'objetivo {tgt} no construido en la escena'); F(f'camera/{v["vineta"]}/objetivo', 'ADN/objetos (4b/4c/SELLO OBJ) + motor', 'construir el objetivo', f'{tgt} no existe en el .blend', tid)
        k0 = keys_existentes(f0, f1); todas_keys.append(k0); tomas.append(T); continue
    # manifiesto
    if SW['manifiesto_espacial']:
        mm = {}
        for f in (f0, (f0 + f1) // 2, f1):
            x = medir(tgt, f); mm[f] = {'altura_m': round(x['H'], 4), 'zmin': round(x['zmin'], 4), 'zmax': round(x['zmax'], 4),
                                       'cabeza': ({'centro': r3(x['cabeza']['centro']), 'alto_m': round(x['cabeza']['alto'], 4)} if x['cabeza'] else None),
                                       'frente': r3(x['frente']) if x['frente'] is not None else None, 'frente_metodo': x.get('frente_metodo')}
        T['manifiesto'] = mm
        if m0['tipo'] == 'personaje':
            if m0['cabeza'] is None: F(f'actors/{tgt}/rig/cabeza', 'motor (rig) / ADN', 'mapear rol cabeza en el rig', 'rig sin hueso/malla de cabeza: región de planos cortos no medible', tid)
            h_adn = ADN_H.get(tgt)
            if isinstance(h_adn, (int, float)) and abs(m0['H'] - h_adn) / h_adn > CFG['tolerancia_escala_adn']:
                AVISOS.append(f'{tgt}: altura medida en el .blend {m0["H"]:.3f} m vs ADN {h_adn} m (dif {100*(m0["H"]-h_adn)/h_adn:+.0f}%). No se cambia el ADN; la cámara usa la medida.')
    vin = SBV.get(v['vineta']) or {}; enc = ((vin.get('director_imagen') or {}).get('en_cuadro') or [])
    ori_txt = next((c.get('orientacion') for c in enc if c.get('id') == tgt), None); ori = orient_deg(ori_txt)
    if SBE is None: F(f'camera/{v["vineta"]}/orientacion', 'SB (esc_N.json)', 'pasar esc_N.json del SB', 'sin esc_N.json: no hay orientación pedida; se usa el frente medido', tid)
    elif ori is None: AVISOS.append(f'{tid}: orientación SB «{ori_txt}» sin traducción en la tabla; se usa el frente medido (0°)')
    par = eje_par((vin.get('continuidad') or {}).get('eje')); eje_ref = None
    if par and par[0] == 'ambiguo':
        F(f'camera/{v["vineta"]}/continuidad.eje', 'SB + 4a2/02N (ID espacial del segundo elemento del eje)', 'enlazar el elemento del eje a un ID del .blend',
          f'eje «{(vin.get("continuidad") or {}).get("eje")}»: el segundo elemento no es un ID construido; el eje no se verifica', tid)
    elif par:
        eje_ref = (par[0], par[1], ref_eje.get(par))
    plano_de = lambda f, v=v: plano_de_t(v, (f - 1) / FPS)
    if not SW['resolver_camara']:
        keys = keys_existentes(f0, f1); T['camara'] = 'existente (resolver_camara.off)'
        T['revision'] = validar(keys, tgt, plano_de, f0, f1, ori, eje_ref) if SW['validacion_camara'] else []
        T['estado'] = 'pasa' if not T['revision'] else 'no_pasa'; T['motivos'] = sorted({x[1] for x in T['revision']}); todas_keys.append(keys); tomas.append(T); continue
    base = ori if ori is not None else 0; intentos = []; elegido = None
    for daz in CFG['busqueda_acimut_deg']:
        for fd in CFG['busqueda_factor_distancia']:
            if len(intentos) >= CFG['reparaciones_max']: break
            keys, err = construir(v, (base + daz, fd), tgt, tid, [])
            if err: intentos.append({'az': base + daz, 'fd': fd, 'error': err}); continue
            # eje: el primer plano válido de un bloque fija el lado
            er = eje_ref
            if er and er[2] is None:
                pa, pbb = medir(er[0], f0)['centro'], medir(er[1], f0)['centro']; l = keys[0]['loc']
                er = (er[0], er[1], (pbb.x - pa.x) * (l.y - pa.y) - (pbb.y - pa.y) * (l.x - pa.x))
            libres = [(fr(float(sg['t_abs'][0])), fr_fin(float(sg['t_abs'][1])) + 1) for sg in (v.get('segmentos') or []) if sg['movimiento'] in ('PAN', 'TILT', 'WHIPPAN') and isinstance((sg.get('args') or {}).get('degrees'), (int, float))]
            mal = validar(keys, tgt, plano_de, f0, f1, ori, er, libres) if SW['validacion_camara'] else []
            intentos.append({'az': base + daz, 'fd': fd, 'fallos': len(mal), 'motivos': sorted({x[1] for x in mal}), 'muestras_malas': mal[:6]})
            if not mal: elegido = (keys, daz, fd, er); break
            if daz == 0 and fd == 1.0: primero = (keys, mal)
        if elegido or len(intentos) >= CFG['reparaciones_max']: break
    if elegido:
        keys, daz, fd, er = elegido; notas.clear(); keys, _ = construir(v, (base + daz, fd), tgt, tid, notas)
        if er and par and ref_eje.get(par) is None: ref_eje[par] = er[2]
        T['estado'] = 'pasa'; T['reparacion'] = None if (daz == 0 and fd == 1.0) else {'acimut_extra_deg': daz, 'factor_distancia': fd, 'intentos': len(intentos)}
    else:
        construir(v, (base, 1.0), tgt, tid, notas)  # registra faltantes de movimiento una vez
        val = [i for i in intentos if 'fallos' in i]
        mejor = min(val, key=lambda i: i['fallos']) if val else None
        if mejor: keys, _ = construir(v, (mejor['az'], mejor['fd']), tgt, tid, [])
        else: keys = keys_existentes(f0, f1)
        T['estado'] = 'bloqueada'; T['motivos'] = mejor['motivos'] if mejor else [i.get('error') for i in intentos][:3]; T['mejor_intento'] = mejor
        T['intentos'] = len(intentos)
    seen = set(); FALT[:] = [x for x in FALT if not (json.dumps(x, sort_keys=True) in seen or seen.add(json.dumps(x, sort_keys=True)))]
    k0 = keys[0]; T['camara'] = {'loc': r3(k0['loc']), 'lente_mm': round(k0['lens'], 2), 'acimut_orientacion_sb_deg': ori, 'orientacion_sb': ori_txt,
                                  'elevacion_deg': (SHOTS_E.get(v['vineta']) or {}).get('elevation_deg'), 'distancia_m': round((k0['loc'] - k0['look']).length, 4)}
    todas_keys.append(keys); tomas.append(T)
if SW['resolver_camara']: escribir(todas_keys)
# verificación cruzada con la cámara REAL de Blender (world_to_camera_view, mismo método que blender_camaras.py del paso 05)
for T, keys in zip(tomas, todas_keys):
    f = (T['frame_ini'] + T['frame_fin']) // 2; sc.frame_set(f); m = medir(T['objetivo'], f) if T['objetivo'] in ACT or bpy.data.objects.get(T['objetivo'] or '') else None
    if m:
        p = (m['cabeza']['centro'] if m['cabeza'] else m['centro']); q = w2c(sc, CAM, p); T['verif_blender_mitad'] = {'frame': f, 'uv_cabeza_o_centro': r3(q)}
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'escena.blend'), copy=True)
res = {'version': CFG['version'], 'contrato': 'camara_v2', 'interruptores': SW, 'fps': FPS, 'resolucion': [sc.render.resolution_x, sc.render.resolution_y],
       'sensor_ancho_mm': SENSOR_W, 'tomas': tomas, 'faltantes': FALT, 'avisos': AVISOS,
       'resumen': {'pasa': [t['toma'] for t in tomas if t['estado'] == 'pasa'], 'bloqueada': [t['toma'] for t in tomas if t['estado'] in ('bloqueada', 'no_pasa')]}}
json.dump(res, open(OUT / 'camara_v2.json', 'w'), ensure_ascii=False, indent=1, default=str)
print('CAMARA_V2_OK ' + json.dumps(res['resumen']))
