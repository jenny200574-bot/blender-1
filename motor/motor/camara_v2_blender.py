"""MOTOR · cámara v2 con RIG POR COORDENADAS (fase 4g). Dentro de Blender sobre la escena YA ARMADA (no toca personajes, objetos ni ADN):
  blender -b RUN/escena.blend -P camara_v2_blender.py -- ENTRADA SB_CAMARA SB_ESCENA|- CFG AJUSTES_SB SALIDA [COMANDOS_SB|-] [ELEV_CFG|-] [TIPOS_PLANO_05|-]
  · manifiesto_espacial: altura, cabeza/cara, frente y alturas de huesos MEDIDOS en el .blend evaluado (aviso si difiere del ADN).
  · resolver_camara: por toma lee TODOS los comandos del SB (plano, encuadre, ángulo, altura, lente, foco, composición, rig, movimiento,
    continuidad, transición) y arma tramos con extremos; rig_camara_coords.py (puerto del Estudio de cámara de mano, r2) GENERA la
    trayectoria cuadro a cuadro (One Euro, límites del set real). Los keyframes se hornean de esa trayectoria.
  · validacion_camara: lo mismo que el 05 (camaras_o113_blender / blender_camaras) pero en movimiento: en cada cuadro muestreado,
    sujeto en cuadro (pies o cabeza según plano), nada tapa (BVH ray_cast), sin inclinación/roll indebidos, lado del eje 180°.
    Reparación acotada (acimut/distancia) o toma BLOQUEADA con motivo. Ningún comando queda en silencio: cada uno tiene estado.
Interruptores .off junto a este archivo: manifiesto_espacial, resolver_camara, validacion_camara. Universal: sin canal/escena/personaje."""
import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
from bpy_extras.object_utils import world_to_camera_view as w2c
AQUI = Path(__file__).resolve().parent; sys.path.insert(0, str(AQUI))
import rig_camara_coords as RIG
from medir_objetivo_camara import puntos_de_objetivo, sensor_ancho_mm
from curvas_accion import fijar_constante
from eje_objetos import par_eje
from malla_cabeza import region_desde_hueso, marcar_malla_cabeza_visible, clasificar_medida_cabeza, estado_visual
import buscador_posicion_camara as BUS
OFF = lambda n: (AQUI / f'{n}.off').exists()
a = sys.argv[sys.argv.index('--') + 1:]
def _j(i, d=None):
    try: return json.load(open(a[i])) if len(a) > i and a[i] != '-' and Path(a[i]).is_file() else d
    except Exception: return d
E = _j(0); SBC = _j(1); SBE = _j(2); CFG = _j(3); AJ = _j(4); OUT = Path(a[5]); OUT.mkdir(parents=True, exist_ok=True)
CMDS = _j(6, {}) or {}; ELEV = _j(7, {}) or {}; TP05 = _j(8, {}) or {}
SW = {'manifiesto_espacial': not OFF('manifiesto_espacial'), 'resolver_camara': not OFF('resolver_camara'), 'validacion_camara': not OFF('validacion_camara')}
sc = bpy.context.scene; FPS = sc.render.fps / sc.render.fps_base
RX, RY = sc.render.resolution_x * sc.render.pixel_aspect_x, sc.render.resolution_y * sc.render.pixel_aspect_y; ASP = RX / RY
TABLA = AJ['encuadre_fraccion_altura_visible']; UP = Vector((0, 0, 1)); FALT = []; AVISOS = []
def F(campo, modulo, accion, mensaje, toma=None):
    x = {'campo': campo, 'modulo': modulo, 'accion': accion, 'mensaje': mensaje, 'toma': toma}
    if x not in FALT: FALT.append(x)
from seguridad import cuadro
def fr(t): return 1 + cuadro(t, FPS)
def fr_fin(t): return cuadro(t, FPS)
r3 = lambda v: [round(float(x), 4) for x in v]
# La entrada única conserva sus luces; este resolutor no modifica visibilidad del set.
CAM = sc.camera
if CAM is None or getattr(CAM, 'data', None) is None: raise ValueError('La escena no tiene cámara; no se inventa sensor ni posición')
SENSOR_W = sensor_ancho_mm((E or {}).get('camera')); CAM.data.sensor_width = SENSOR_W; CAM.data.sensor_fit = 'HORIZONTAL'
TOMA_ACTUAL = None
ACT = {o.name: o for o in bpy.data.objects if o.type == 'ARMATURE'}
def mallas(root):
    if root is None: return []
    candidatos = list(root.children_recursive)
    ya = {x.name for x in candidatos}
    for o in bpy.data.objects:
        padre = getattr(o, 'parent', None)
        if padre == root and o.name not in ya:
            candidatos.append(o); ya.add(o.name)
    return [x for x in candidatos if x.type == 'MESH' and not x.hide_render]
ACT_MESH = {pid: mallas(o) for pid, o in ACT.items()}; ACT_SET = {m.name for ms in ACT_MESH.values() for m in ms}
ENV = [o for o in sc.objects if o.type == 'MESH' and not o.hide_render and o.name not in ACT_SET]
ADN_H = {x['id']: (x.get('spec') or {}).get('altura_m') for x in E.get('actors', [])}
class _BV:
    def __init__(s, t, own): s.t = t; s.own = own
    def ray_cast(s, *q): return s.t.ray_cast(*q)
    def find_nearest(s, *q): return s.t.find_nearest(*q)
    def quien(s, i): return s.own[i] if i is not None and 0 <= i < len(s.own) else None
def bvh(objs, dg):
    V, P, own = [], [], []
    for o in objs:
        e = o.evaluated_get(dg); m = e.to_mesh(); n = len(V); mw = o.matrix_world
        V += [mw @ v.co for v in m.vertices]; P += [tuple(i + n for i in p.vertices) for p in m.polygons]; own += [o.name] * len(m.polygons); e.to_mesh_clear()
    return _BV(BVHTree.FromPolygons(V, P), own) if P else None
def verts(objs, dg):
    out = []
    for o in objs:
        e = o.evaluated_get(dg); m = e.to_mesh(); mw = o.matrix_world; out += [mw @ v.co for v in m.vertices]; e.to_mesh_clear()
    return out
def verts_eval(o, dg):
    try: e = o.evaluated_get(dg)
    except (AttributeError, RuntimeError): return []
    if getattr(e, 'type', None) != 'MESH': return []
    m = e.to_mesh()
    try: return [e.matrix_world @ v.co for v in m.vertices]
    finally: e.to_mesh_clear()
def puntos_respaldo(obj, dg, nombre, toma):
    """Sin vértices visibles: hijos con malla evaluada (depsgraph) o bounding box del mundo."""
    propios = verts_eval(obj, dg) if getattr(obj, 'type', None) == 'MESH' else []
    hijos = [pts for ch in getattr(obj, 'children_recursive', []) if getattr(ch, 'type', None) == 'MESH' for pts in [verts_eval(ch, dg)] if pts]
    try: caja = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    except (TypeError, AttributeError, ValueError): caja = []
    return [Vector(p) for p in puntos_de_objetivo(nombre, toma or TOMA_ACTUAL, propios, hijos, caja)]
def dentro_de_malla(bv, p):
    if bv is None: return None
    n = 0
    for d in (Vector((1,0,0)), Vector((-1,0,0)), Vector((0,1,0)), Vector((0,-1,0)), Vector((0,0,1)), Vector((0,0,-1))):
        h = bv.ray_cast(p, d, 1000)
        if h[0] is not None and h[1].dot(d) > 0: n += 1
    return bv.quien(bv.ray_cast(p, Vector((0,0,1)), 1000)[2]) if n >= 4 else None
# ---------------- manifiesto espacial (medido en el .blend evaluado) ----------------
CACHE = {}; ENVC = {}
def env_bvh(f, excl=frozenset()):
    k = (f, frozenset(excl))
    if k not in ENVC:
        if len(ENVC) > 6: ENVC.clear()
        sc.frame_set(f); ENVC[k] = bvh([o for o in ENV if o.name not in excl], bpy.context.evaluated_depsgraph_get())
    return ENVC[k]
def mallas_de(i):
    o = bpy.data.objects.get(i) if i and i not in ACT else None
    return frozenset(m.name for m in mallas(o)) if o else frozenset()
def medir(pid, f, toma=None):
    k = (pid, f)
    if k in CACHE: return CACHE[k]
    if pid is None: return None
    toma = toma or TOMA_ACTUAL
    sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); A = ACT.get(pid); R = CFG['roles_hueso']
    if A is None:
        o = bpy.data.objects.get(pid)
        if o is None: CACHE[k] = None; return None
        P = verts(mallas(o), dg)
        if not P: P = puntos_respaldo(o, dg, pid, toma)
        lo = Vector([min(p[i] for p in P) for i in range(3)]); hi = Vector([max(p[i] for p in P) for i in range(3)]); c = (lo + hi) / 2
        acts = [x.matrix_world.translation for x in ACT.values()]; fv = None
        if acts:
            d = sum(acts, Vector()) / len(acts) - c; d.z = 0; fv = d.normalized() if d.length > 1e-6 else None
        CACHE[k] = {'tipo': 'objeto', 'zmin': lo.z, 'zmax': hi.z, 'H': hi.z - lo.z, 'centro': c, 'cabeza': None, 'frente': fv, 'frente_cara': fv,
                    'frente_metodo': 'objeto: hacia el centro de los personajes construidos', 'puntos': P, 'huesos': {}, 'id': pid}
        return CACHE[k]
    ms = mallas(A); P = verts(ms, dg)
    if not P: P = puntos_respaldo(A, dg, pid, toma)
    zmin = min(p.z for p in P); zmax = max(p.z for p in P)
    if not SW['manifiesto_espacial'] and isinstance(ADN_H.get(pid), (int, float)): zmax = zmin + ADN_H[pid]
    cab_m = [m for m in ms if (m.parent_type == 'BONE' and m.parent_bone in R['cabeza']) or m.get('semantic_role') in {'head','face'}]; cab = None
    if cab_m:
        HP = verts(cab_m, dg)
        if not HP: cab_m = []
    if cab_m:
        lo = Vector([min(p[i] for p in HP) for i in range(3)]); hi = Vector([max(p[i] for p in HP) for i in range(3)])
        cc = (lo + hi) / 2; cab = marcar_malla_cabeza_visible({'centro': cc, 'alto': hi.z - lo.z, 'top': hi.z, 'puntos': HP, 'puntos_cara': [p for p in HP if abs(p.z - cc.z) <= (hi.z - lo.z) / 4] or HP})
    pb = A.pose.bones; mw = A.matrix_world; fv = None; metodo = None
    pies = [n for n in R['pies'] if n in pb]
    if pies:
        d = sum([(mw @ pb[n].tail) - (mw @ pb[n].head) for n in pies], Vector()); d.z = 0
        if d.length > 1e-6: fv = d.normalized(); metodo = 'huesos de pie (talón→punta)'
    if fv is None:
        d = mw.to_3x3() @ Vector((0, 1, 0)); d.z = 0; fv = d.normalized() if d.length > 1e-6 else None; metodo = 'eje +Y local del armature'
    # mirada/cara (r2 «Mirada»): eje del hueso cabeza más alineado con el frente del cuerpo, en este cuadro (sigue el giro de la cabeza)
    fc = fv; hc = next((n for n in R['cabeza'] if n in pb), None)
    if cab is None and hc:
        head = mw @ pb[hc].head; tail = mw @ pb[hc].tail
        puro = region_desde_hueso((head.x, head.y, head.z), (tail.x, tail.y, tail.z))
        if puro:
            cab = {'centro': Vector(puro['centro']), 'alto': puro['alto'], 'top': puro['top'], 'puntos': [Vector(p) for p in puro['puntos']], 'puntos_cara': [Vector(p) for p in puro['puntos_cara']], 'origen': 'hueso', 'malla_visible': False, 'valida_visual': False, 'production_approved': False}
    if hc and fv is not None:
        M3 = (mw @ pb[hc].matrix).to_3x3(); ejes = [M3 @ Vector(x) for x in ((1,0,0),(-1,0,0),(0,0,1),(0,0,-1))]
        ejes = [Vector((e.x, e.y, 0)) for e in ejes]; ejes = [e.normalized() for e in ejes if e.length > 1e-6]
        if ejes: fc = max(ejes, key=lambda e: e.dot(fv))
    hz = {}
    for nm, spec in CFG.get('alturas_hueso', {}).items():
        bs = [b for b in spec['huesos'] if b in pb]
        if not bs: continue
        if spec['punto'] == 'centro_malla': hz[nm] = cab['centro'].z if cab else None
        else: hz[nm] = sum((mw @ pb[b].head).z for b in bs) / len(bs)
    pel = mw.translation
    CACHE[k] = {'tipo': 'personaje', 'zmin': zmin, 'zmax': zmax, 'H': zmax - zmin, 'centro': Vector((pel.x, pel.y, (zmin + zmax) / 2)), 'cabeza': cab,
                'frente': fv, 'frente_cara': fc, 'frente_metodo': metodo, 'puntos': P, 'huesos': hz, 'id': pid}
    return CACHE[k]
def grupo(ids, f, principal, toma=None):
    ms = [m for m in (medir(i, f, toma) for i in ids) if m]
    if len(ms) <= 1: return medir(principal, f, toma)
    P = [p for m in ms for p in m['puntos']]; heads = [p for m in ms if m['cabeza'] for p in m['cabeza']['puntos']]
    mp = medir(principal, f, toma) or ms[0]
    cab = {'centro': sum([m['cabeza']['centro'] for m in ms if m['cabeza']], Vector()) / max(1, sum(1 for m in ms if m['cabeza'])), 'alto': max(m['cabeza']['alto'] for m in ms if m['cabeza']),
           'top': max(m['cabeza']['top'] for m in ms if m['cabeza']), 'puntos': heads, 'puntos_cara': [p for m in ms if m['cabeza'] for p in m['cabeza']['puntos_cara']]} if heads else None
    return {'tipo': 'grupo', 'zmin': min(m['zmin'] for m in ms), 'zmax': max(m['zmax'] for m in ms), 'H': max(m['H'] for m in ms),
            'centro': sum([m['centro'] for m in ms], Vector()) / len(ms), 'cabeza': cab, 'frente': mp['frente'], 'frente_cara': mp['frente_cara'],
            'puntos': P, 'huesos': mp['huesos'], 'id': principal, 'miembros': [m['id'] for m in ms]}
# ---------------- proyección propia (pinhole, sensor horizontal) ----------------
def look_rot(loc, tgt): return (tgt - loc).to_track_quat('-Z', 'Y').to_matrix()
def proyectar(p, loc, R, lens):
    c = R.transposed() @ (p - loc)
    if c.z >= -1e-6: return None
    k = lens / SENSOR_W; return (0.5 + k * c.x / -c.z, 0.5 + k * ASP * c.y / -c.z, -c.z)
def sensor_h(): return SENSOR_W / ASP
def region(m, plano):
    frac = TABLA.get(plano)
    if frac is None: return None
    Hf = frac * m['H']
    if frac >= 1 or m['tipo'] == 'objeto' or (m['tipo'] == 'grupo' and frac >= 1):
        return {'top': m['zmax'], 'bot': m['zmin'], 'xy': m['centro'], 'Hf': max(Hf, m['zmax'] - m['zmin']), 'cuerpo_entero': True}
    xy = m['cabeza']['centro'] if m['cabeza'] else m['centro']
    if m['cabeza'] and m['tipo'] != 'grupo' and Hf < m['cabeza']['alto']:   # ECU/CU más cerrado que la cabeza medida: se centra en la cara, no en la coronilla
        cz = m['cabeza']['centro'].z; return {'top': cz + Hf / 2, 'bot': cz - Hf / 2, 'xy': xy, 'Hf': Hf, 'cuerpo_entero': False, 'cara': True}
    return {'top': m['zmax'], 'bot': max(m['zmin'], m['zmax'] - Hf), 'xy': xy, 'Hf': Hf, 'cuerpo_entero': False}
def emplazar(m, plano, lens, elev, az_off, xlado, aire, fdist=1.0, frente_key='frente_cara', z_cam=None):
    """Posición inicial: distancia por proyección de la región MEDIDA + ajuste NDC con los puntos reales (alto, ancho, aire, lado)."""
    rg = region(m, plano)
    if rg is None: return None, f'plano {plano} sin fila en la tabla de encuadre'
    fv = m.get(frente_key) or m['frente']
    if fv is None: return None, 'objetivo sin frente medible'
    right = fv.cross(UP).normalized(); az = math.radians(az_off); e = math.radians(elev)
    d_h = (fv * math.cos(az) + right * math.sin(az)).normalized(); dirc = (d_h * math.cos(e) + UP * math.sin(e)).normalized()
    D = rg['Hf'] * lens / sensor_h()
    look = Vector((rg['xy'].x, rg['xy'].y, (rg['top'] + rg['bot']) / 2 if rg['cuerpo_entero'] else rg['top'] - rg['Hf'] / 2))
    ref_all = m['puntos'][::max(1, len(m['puntos']) // 400)]
    ref = (m['cabeza']['puntos'] if (not rg['cuerpo_entero'] and m['cabeza']) else ref_all)
    if rg.get('cara'): ref = m['cabeza']['puntos_cara']
    D_grupo = 0.0
    for _ in range(10):
        loc = look + dirc * D
        if z_cam is not None: loc.z = z_cam
        R = look_rot(loc, look)
        pt = proyectar(Vector((rg['xy'].x, rg['xy'].y, rg['top'])), loc, R, lens); pb_ = proyectar(Vector((rg['xy'].x, rg['xy'].y, rg['bot'])), loc, R, lens)
        if not pt or not pb_: break
        span = pt[1] - pb_[1]; want = (rg['top'] - rg['bot']) / rg['Hf'] if not rg['cuerpo_entero'] else min(1 - 2 * CFG['margen_ndc'], (rg['top'] - rg['bot']) / rg['Hf'])
        if span > 1e-6: D = max(D * span / want, D_grupo)
        qa = [q for q in (proyectar(x, loc, R, lens) for x in ref) if q]
        if m['tipo'] == 'grupo' and qa:   # grupo: que quepan todos a lo ancho (solo la región pedida: cabezas en planos cortos)
            w = max(q[0] for q in qa) - min(q[0] for q in qa)
            if w > 1 - 2 * CFG['margen_ndc']: D_grupo = D = D * min(2.0, w / (1 - 2 * CFG['margen_ndc']))
            if len(qa) < len(ref): D_grupo = D = D * 1.5   # algún miembro quedó detrás de la cámara
        loc = look + dirc * D
        if z_cam is not None: loc.z = z_cam
        R = look_rot(loc, look); qs = [q for q in (proyectar(x, loc, R, lens) for x in ref) if q]
        if not qs: break
        vt = max(q[1] for q in qs); vb = min(q[1] for q in qs); uc = (max(q[0] for q in qs) + min(q[0] for q in qs)) / 2
        if m['tipo'] == 'grupo' and vt - vb > 1 - aire - 2 * CFG['margen_ndc']:   # grupo: que quepan también a lo alto (cabezas a distinta altura)
            D_grupo = D = D * min(2.0, (vt - vb) / (1 - aire - 2 * CFG['margen_ndc'])); continue
        if rg.get('cara'): look.z = m['cabeza']['centro'].z
        elif rg['cuerpo_entero']: look.z += ((vt + vb) / 2 - 0.5) * (D * sensor_h() / lens)
        else: look.z += (vt - (1 - aire)) * (D * sensor_h() / lens)
        look -= (R @ Vector((1, 0, 0))) * (xlado - uc) * (D * SENSOR_W / lens)
    D *= fdist; loc = look + dirc * D
    if z_cam is not None: loc.z = z_cam
    return {'loc': loc, 'look': look, 'lens': lens, 'D': D}, None
# ---------------- límites del set real (r2: minY/maxY/maxDist, aquí medidos) ----------------
def limites(f, ancla, H, excl=frozenset()):
    bv = env_bvh(f, excl); hol = min(CFG['holgura_max_m'], CFG['holgura_frac_altura'] * H)
    down = bv.ray_cast(ancla + UP * 0.01, -UP, 1000) if bv else (None,)
    up = bv.ray_cast(ancla, UP, 1000) if bv else (None,)
    minZ = (down[0].z + hol) if down[0] is not None else None; maxZ = (up[0].z - hol) if up[0] is not None else None
    def max_dist(o, d):
        h = bv.ray_cast(o, d, 1000) if bv else (None,)
        return max(0.0, (h[0] - o).length - hol) if h[0] is not None else None
    return {'minZ': minZ, 'maxZ': maxZ, 'max_dist': max_dist, 'piso_z': down[0].z if down[0] is not None else None, 'techo_z': up[0].z if up[0] is not None else None}
# ---------------- revisión espacial del 05, en movimiento ----------------
def muestras(f0, f1):
    return list(range(f0,f1+1))

OTROS = {}
def otros_bvh(f, excluir):
    k = (f, tuple(sorted(excluir)))
    if k not in OTROS:
        sc.frame_set(f); OTROS[k] = bvh([m for pid, ms in ACT_MESH.items() if pid not in excluir for m in ms], bpy.context.evaluated_depsgraph_get())
    return OTROS[k]
def validar(tray, spec, f0, f1, libres_encuadre=(), libres_inclin=()):
    malos = []; P = {x['f']: x for x in tray}
    for f in muestras(f0, f1):
        x = P.get(f)
        if x is None: continue
        loc = x['loc']; R = x['quat'].to_matrix(); lens = x['lente']; m = spec['medir'](f)
        if m is None: malos.append((f, 'objetivo ausente en este cuadro', 0)); continue
        env = env_bvh(f); env_oc = env_bvh(f, spec.get('excluir_env', frozenset())); oth = otros_bvh(f, spec['excluir_oclusion'])
        D = (m['centro'] - loc).length
        hol = min(CFG['holgura_max_m'], CFG['holgura_frac_distancia'] * D, CFG['holgura_frac_altura'] * m['H'])
        if env:
            den = dentro_de_malla(env, loc); nn = env.find_nearest(loc)
            if den: malos.append((f, f'cámara dentro de geometría del escenario ({den})', 0))
            elif nn[0] is not None and nn[3] < hol: malos.append((f, f'cámara pegada a geometría del escenario ({env.quien(nn[2])})', round(nn[3], 3)))
        libre_e = any(a_ <= f <= b_ for a_, b_ in libres_encuadre)
        if not libre_e and spec.get('revisar_encuadre', True):
            rg = region(m, spec['plano_de'](f)); pts = m['puntos']
            if rg and not rg['cuerpo_entero'] and m['cabeza']:   # 05: cabeza en cuadro en planos cortos (banda de la cara; en ECU/CU se permite cortar la coronilla)
                pts = m['cabeza']['puntos_cara']
            elif rg: pts = [p for p in pts if rg['bot'] - 1e-3 <= p.z <= rg['top'] + 1e-3] or pts   # 05: pies y cabeza en planos abiertos
            pts = pts[::max(1, len(pts) // CFG['puntos_region'])]
            pr = [proyectar(p, loc, R, lens) for p in pts]; fr_in = sum(1 for q in pr if q and 0 <= q[0] <= 1 and 0 <= q[1] <= 1) / max(1, len(pr))
            req = CFG['region_en_cuadro_min']
            if rg and not rg['cuerpo_entero'] and m['cabeza'] and rg['Hf'] < m['cabeza']['alto'] / 2: req *= rg['Hf'] / (m['cabeza']['alto'] / 2)
            if fr_in < req: malos.append((f, 'sujeto fuera de cuadro (' + ('cabeza' if rg and not rg['cuerpo_entero'] else 'pies/cabeza') + ')', round(fr_in, 2)))
            tap = {}
            for p in pts:
                for bv, et in ((env_oc, 'escenario'), (oth, 'otro personaje')):
                    if bv is None: continue
                    d = p - loc; h = bv.ray_cast(loc, d.normalized(), max(0, d.length - 0.01))
                    if h[0] is not None: kk = f'{et}: {bv.quien(h[2])}'; tap[kk] = tap.get(kk, 0) + 1; break
            fv = 1 - sum(tap.values()) / max(1, len(pts))
            if fv < CFG['visibilidad_min']: malos.append((f, 'sujeto tapado (' + max(tap, key=tap.get) + ')', round(fv, 2)))
            if spec.get('cara') and m.get('frente_cara') is not None and m['tipo'] != 'objeto':
                yaw, _ = RIG.mirada_relativa(m['frente_cara'], (m['cabeza']['centro'] if m['cabeza'] else m['centro']), loc)
                if abs(math.degrees(yaw)) > CFG['max_angulo_cara_deg']: malos.append((f, 'sujeto de espaldas a cámara', round(math.degrees(yaw), 1)))
        if not any(a_ <= f <= b_ for a_, b_ in libres_inclin):   # 05 o113: inclinación indebida (aquí: respecto de lo pedido por el SB)
            d = R @ Vector((0, 0, -1)); pitch = math.degrees(math.asin(max(-1, min(1, d.z))))
            if spec.get('pitch_pedido') is not None and abs(pitch - spec['pitch_pedido']) > CFG['inclinacion_tolerancia_deg']:
                malos.append((f, f'inclinación indebida (pedido {spec["pitch_pedido"]:.0f}°)', round(pitch, 1)))
            up = R @ Vector((0, 1, 0)); right = R @ Vector((1, 0, 0)); roll = math.degrees(math.atan2(right.z, up.z))
            if abs(roll - spec.get('roll_pedido_deg', 0)) > CFG['roll_tolerancia_deg'] and abs(abs(pitch) - 90) > 10:
                malos.append((f, 'roll indebido', round(roll, 1)))
        if spec.get('eje') and spec['eje'][2] is not None:
            A_, B_, lado = spec['eje']; pa = medir(A_, f); pbb = medir(B_, f)
            if pa and pbb:
                s = (pbb['centro'].x - pa['centro'].x) * (loc.y - pa['centro'].y) - (pbb['centro'].y - pa['centro'].y) * (loc.x - pa['centro'].x)
                if (s > 0) != (lado > 0): malos.append((f, 'cámara cruza el eje de 180° del bloque', round(s, 3)))
    return malos
# ---------------- lectura de TODOS los comandos del SB de una viñeta ----------------
def orient_txt(txt):
    t = (txt or '').lower()
    for r in CFG['orientacion_a_acimut']:
        if all(c in t for c in r['contiene']): return r['grados']
    return None
def eje_par(s):
    return par_eje(s, set(ACT), set(bpy.data.objects.keys()))
def buscar_id(label, ids):
    if not label:return None
    binding=(E.get('bindings') or {}).get(str(label));target=binding.get('scene_object_id') if binding else str(label)
    return target if target in bpy.data.objects and bpy.data.objects[target].type in ('MESH','EMPTY','ARMATURE') else None
def leer_toma(v, vin, cm, tid):
    """Devuelve spec de la toma y el estado de CADA comando (ejecutado / falta_dato / no_programado / montaje / solo_revision)."""
    est = []; S = {'plano0': None, 'elev': 0.0, 'z_hueso': None, 'lens': None, 'xlado': CFG['x_por_lado'].get(str(v.get('lado_objetivo') or 'C').upper(), 0.5),
                   'aire': CFG['aire_cabeza_ndc'], 'roll_deg': 0.0, 'suav': CFG['rig_suavidad']['_defecto'], 'sacudir': 0.0, 'sujetos': [], 'ots': None, 'pov': None,
                   'orient': None, 'foco': None, 'cruce_permitido': False, 'insert': None}
    def st(c, args, estado, detalle): est.append({'comando': c, 'args': args, 'estado': estado, 'detalle': detalle})
    e_prep = (SHOTS_E.get(v['vineta']) or {}).get('elevation_deg')
    if isinstance(e_prep, (int, float)): S['elev'] = float(e_prep)   # elevación ya traducida por preparar (misma tabla de config)
    di = vin.get('director_imagen') or {}; enc = di.get('en_cuadro') or []; tgt = v.get('objetivo')
    S['plano0'] = (v.get('keyframes') or [{}])[0].get('plano') or di.get('plano'); S['lens'] = float((v.get('keyframes') or [{}])[0].get('lente_mm') or di.get('lente_mm') or 0) or None
    ang = str(v.get('angulo') or di.get('angulo') or '').upper(); S['ang'] = ang
    S['sujetos'] = [c['id'] for c in enc if c.get('id') in ACT]
    o = orient_txt(next((c.get('orientacion') for c in enc if c.get('id') == tgt), None)); S['orient'] = o
    for c, args in (cm.get('encuadre') or []):
        cat = c
        if c in TABLA: st(c, args, 'ejecutado', 'tamaño de plano: región medida del rig + ajuste NDC')
        elif c in ('SINGLE', 'TWOSHOT', 'THREESHOT', 'GROUPSHOT'):
            ids = [x for x in args.values() if x in ACT] or S['sujetos']
            S['sujetos'] = list(dict.fromkeys(([tgt] if tgt in ACT else []) + ids)); st(c, args, 'ejecutado', f'encuadre de {len(S["sujetos"])} sujeto(s) medidos: {S["sujetos"]}')
            fuera = [x['id'] for x in enc if x.get('id') not in ACT]
            if fuera: st(c, {'no_construidos': fuera}, 'falta_dato', 'sujetos del SB sin construir en la escena (ADN/rig)')
        elif c in ('OTS', 'DIRTYOTS', 'CLEANOTS'):
            rel = args.get('relation') or ''; parts = [p for p in str(rel).replace('>', ' ').split() if p]
            esc = next((p for p in parts if p in ACT and p != tgt), None) or next((x for x in S['sujetos'] if x != tgt), None)
            tp = next((t for t in (TP05.get('tipos') or []) if t['id'] == 'OTS'), None)
            if esc and tp: S['ots'] = (esc, tp); st(c, args, 'ejecutado', f'cámara detrás del hombro de {esc} (fórmula del 05 tipos_plano.json OTS con altura MEDIDA)')
            else: st(c, args, 'falta_dato', 'OTS sin quien escucha construido o sin fila OTS en tipos_plano.json del 05')
        elif c == 'POV':
            s_ = args.get('subject') or args.get('subject#0'); sid = s_ if s_ in ACT else buscar_id(s_, list(ACT))
            if sid: S['pov'] = sid; st(c, args, 'ejecutado', f'cámara en la cabeza medida de {sid} mirando a su frente/mira_a')
            else: st(c, args, 'falta_dato', 'POV sin sujeto construido')
        elif c in CFG['orientacion_dsl_deg']:
            if S['orient'] is None: S['orient'] = CFG['orientacion_dsl_deg'][c]
            st(c, args, 'ejecutado', f'acimut {S["orient"]}° alrededor del frente medido')
        elif c in ('EYELEVEL', 'LOWANGLE', 'HIGHANGLE', 'TOPDOWN', 'BIRDSEYE', 'WORMSEYE'):
            key = CFG['elevacion_extra'].get(c, c); e = (ELEV.get('sb_angulo_a_elevacion_deg') or {}).get(key)
            if e is None: st(c, args, 'falta_dato', 'sin fila en preparar config sb_angulo_a_elevacion_deg')
            else:
                k = CFG['intensidad_angulo'].get(str(args.get('angle_intensity') or '').upper(), 1.0); S['elev'] = e * k
                st(c, args, 'ejecutado', f'elevación {S["elev"]:.0f}° (config preparar' + (f', intensidad ×{k}' if k != 1 else '') + ')')
        elif c == 'DUTCH':
            g = args.get('degrees')
            if isinstance(g, (int, float)): S['roll_deg'] = g * (1 if str(args.get('dir_lr') or 'R').upper() == 'R' else -1); st(c, args, 'ejecutado', f'roll {S["roll_deg"]}°')
            else: st(c, args, 'falta_dato', 'DUTCH sin grados de roll'); F(f'camera/{v["vineta"]}/DUTCH.grados', 'SB (DSL /DUTCH:dir:grados)', 'dar grados', 'roll sin grados', tid)
        elif c in ('GROUNDLEVEL',) or c in CFG.get('alturas_hueso', {}):
            S['z_hueso'] = c; st(c, args, 'ejecutado', 'altura de cámara = medida del rig' if c != 'GROUNDLEVEL' else 'altura de cámara = piso medido + holgura')
        elif c in ('ELEVATED', 'AERIAL', 'DRONEVIEW'):
            st(c, args, 'falta_dato', 'altura en metros no está en el SB'); F(f'camera/{v["vineta"]}/{c}.altura', 'SB o 02N', 'dar altura (m) de cámara', f'{c} sin altura', tid)
        elif c == 'LENS':
            if isinstance(args.get('mm'), (int, float)): S['lens'] = float(args['mm']); st(c, args, 'ejecutado', f'lente {S["lens"]} mm')
        elif c in CFG['lente_por_clase_mm']:
            if not any(x[0] == 'LENS' for x in cm.get('encuadre') or []): S['lens'] = float(CFG['lente_por_clase_mm'][c])
            st(c, args, 'ejecutado', f'clase de lente → {CFG["lente_por_clase_mm"][c]} mm si no hay /LENS')
        elif c in ('MACRO', 'FISHEYE', 'ANAMORPHIC'): st(c, args, 'no_programado', 'óptica especial: Eevee no tiene ojo de pez/anamórfico; el render usa lente normal')
        elif c in ('SHALLOW',): S['foco'] = ('shallow', None); st(c, args, 'ejecutado', f'profundidad de campo f/{CFG["foco"]["fstop_shallow"]} sobre el sujeto')
        elif c == 'DEEPFOCUS': S['foco'] = ('deep', None); st(c, args, 'ejecutado', 'profundidad de campo desactivada')
        elif c in ('FGFOCUS', 'MGFOCUS', 'BGFOCUS'):
            sid = buscar_id(args.get('subject'), list(ACT))
            if sid: S['foco'] = ('sujeto', sid); st(c, args, 'ejecutado', f'foco en {sid}')
            else: st(c, args, 'falta_dato', 'sujeto del foco no construido')
        elif c == 'RACKFOCUS':
            rel = str(args.get('relation') or ''); ab = [buscar_id(x, list(ACT)) for x in rel.split('>')] if '>' in rel else []
            if len(ab) == 2 and all(ab): S['foco'] = ('rack', ab); st(c, args, 'ejecutado', f'cambio de foco {ab[0]}→{ab[1]} durante la toma')
            else: st(c, args, 'falta_dato', 'RACKFOCUS sin A>B construidos')
        elif c == 'SPLITDIOPTER': st(c, args, 'no_programado', 'lente partida no existe en Blender')
        elif c in ('CENTER', 'SYMMETRY'): S['xlado'] = 0.5; st(c, args, 'ejecutado', 'sujeto centrado')
        elif c == 'THIRDS': S['xlado'] = CFG['x_por_tercio'].get(str(args.get('dir_lr') or 'C').upper(), 0.5); st(c, args, 'ejecutado', f'sujeto en tercio x={S["xlado"]:.2f}')
        elif c in ('LOOKROOM', 'NEGSPACE'):
            d = str(args.get('dir_lr') or args.get('side') or '').upper()
            if d in ('L', 'R'): S['xlado'] = CFG['x_por_tercio']['R' if d == 'L' else 'L']; st(c, args, 'ejecutado', f'espacio a {d}: sujeto en x={S["xlado"]:.2f}')
            else: st(c, args, 'falta_dato', 'lado del espacio no dado')
        elif c == 'HEADROOM': S['aire'] = CFG['aire_por_nivel'].get(str(args.get('level') or 'NORMAL').upper(), S['aire']); st(c, args, 'ejecutado', f'aire {S["aire"]}')
        elif c in ('LEADLINES', 'FRAMEINFRAME', 'FGLAYER', 'DEEPSTAGING'): st(c, args, 'no_programado', 'composición que depende de elementos del set no enlazados (4a2/02N); se avisa')
        elif c in ('AXIS',): st(c, args, 'solo_revision', 'lado del eje revisado con continuidad.eje y posiciones medidas')
        elif c == 'CROSSAXIS': S['cruce_permitido'] = True; st(c, args, 'ejecutado', 'cruce de eje permitido por el SB: no bloquea')
        elif c in ('SCREEN', 'EYELINE', 'SRS'): st(c, args, 'solo_revision', 'dirección/mirada: se revisa con el lado del eje; sin cambio de cámara')
        elif c in ('MATCHACTION', 'MATCHCUT'): st(c, args, 'montaje', 'empalme del montaje: el motor respeta el corte exacto')
        elif c in ('REACTION', 'CUTAWAY'): st(c, args, 'ejecutado', 'función narrativa: el objetivo es el que da el SB')
        elif c == 'INSERT':
            oid = buscar_id(args.get('label'), [])
            if oid: S['insert'] = oid; st(c, args, 'ejecutado', f'inserto sobre {oid}')
            else: st(c, args, 'falta_dato', 'objeto del inserto sin ID en el .blend'); F(f'camera/{v["vineta"]}/INSERT.objeto', '4b/4c/SELLO OBJ + 4a2', 'construir/enlazar el objeto', f'inserto «{args.get("label")}» sin geometría', tid)
        elif c in CFG['rig_suavidad'] or c in ('DRONE', 'FPV'):
            if c in ('DRONE', 'FPV'): st(c, args, 'no_programado', 'rig aéreo: necesita trayectoria (anclas) que el SB no da')
            else:
                S['suav'] = CFG['rig_suavidad'][c]; sk = CFG['rig_sacudida'].get(c)
                if sk: S['sacudir'] = sk.get(str(args.get('intensity') or '').upper(), sk['_sin'])
                st(c, args, 'ejecutado', f'rig {c}: suavidad One Euro {S["suav"]}' + (f', sacudida {S["sacudir"]}' if S['sacudir'] else ''))
        elif c == 'CINEMATIC': st(c, args, 'solo_revision', 'estilo general sin efecto geométrico')
        else: st(c, args, 'no_programado', 'comando de encuadre sin traducción en cámara v2')
    if tgt in ACT and tgt not in S['sujetos']: S['sujetos'].insert(0, tgt)
    if S['orient'] is None and SBE is not None: AVISOS.append(f'{tid}: orientación del SB sin traducción; se usa el frente medido (0°)')
    S['estado_cmd'] = est; return S
# ---------------- armar tramos (extremos) y pedir la trayectoria al rig ----------------
def params(em, ancla):
    d = em['loc'] - em['look']; dh = Vector((d.x, d.y, 0))
    return {'az': math.atan2(d.y, d.x), 'dist': dh.length, 'altura': d.z, 'lente': em['lens'], 'roll': 0.0, 'yaw': 0.0, 'pitch': 0.0, 'lateral': 0.0, 'off': em['look'] - ancla}
def construir(v, S, cand, tid, est_mov):
    t0, t1 = map(float, v['t_abs']); f0, f1 = fr(t0), fr_fin(t1); tgt = S['insert'] or v.get('objetivo')
    medf = (lambda f: grupo(S['sujetos'], f, tgt, tid)) if len(S['sujetos']) > 1 else (lambda f: medir(tgt, f, tid))
    m0 = medf(f0)
    if m0 is None: return None, f'objetivo {tgt} no construido', None
    ancla = lambda f: (lambda m: (m['cabeza']['centro'] if m and m['cabeza'] else (m['centro'] if m else None)))(medf(f))
    lim = limites(f0, ancla(f0), m0['H'], mallas_de(tgt)); roll = math.radians(S['roll_deg'])
    z_cam = None
    if S['z_hueso'] == 'GROUNDLEVEL' and lim['piso_z'] is not None: z_cam = lim['minZ']
    elif S['z_hueso']:
        key = 'EYELEVEL_ALTURA' if S['z_hueso'] == 'EYELEVEL' else S['z_hueso']; z_cam = (m0.get('huesos') or {}).get(key)
    if S['pov']:
        mp = medir(S['pov'], f0); loc = (mp['cabeza']['centro'] if mp['cabeza'] else mp['centro']).copy()
        mira_id = next((c.get('mira_a') for c in ((SBV.get(v['vineta']) or {}).get('director_imagen') or {}).get('en_cuadro', []) if c.get('id') == S['pov']), None)
        mm = medir(mira_id, f0) if mira_id else None; look = (mm['cabeza']['centro'] if mm and mm['cabeza'] else (mm['centro'] if mm else loc + mp['frente_cara']))
        em = {'loc': loc + (look - loc).normalized() * (mp['cabeza']['alto'] * 0.6 if mp['cabeza'] else 0.05), 'look': look, 'lens': S['lens'], 'D': (look - loc).length}
    elif S['ots']:
        esc, tp = S['ots']; me = medir(esc, f0); H = me['H']; obj = ancla(f0)
        d = obj - me['centro']; d.z = 0; d.normalize(); lat = Vector((-d.y, d.x, 0))
        lado = ref_eje_lado(S, f0)
        if lado is not None:
            prueba = me['centro'] + lat
            if (lado > 0) != (eje_s(S, f0, prueba) > 0): lat = -lat
        loc = Vector((me['centro'].x, me['centro'].y, me['zmin'])) - d * tp['detras_m_en_alturas'] * H + lat * tp['lado_hombro_en_alturas'] * H; loc.z = me['zmin'] + tp['alto_camara'] * H
        em = {'loc': loc, 'look': obj, 'lens': S['lens'], 'D': (obj - loc).length}
    else:
        em, err = emplazar(m0, S['plano0'], S['lens'], S['elev'], (S['orient'] or 0) + cand[0], S['xlado'], S['aire'], cand[1], z_cam=z_cam)
        if err: return None, err, None
    base_p = params(em, ancla(f0)); base_p['roll'] = roll; base_p['mira'] = Vector((0, 0, 0))
    obj_fn = lambda f: ancla(f) + base_p['off']
    segs = v.get('segmentos') or [{'t_abs': [t0, t1], 'movimiento': 'STATIC', 'args': {}}]
    tramos = []; cur = dict(base_p); pos_fija = None; libres_e = []; libres_i = []
    az_fn_tramo = None
    for i, s in enumerate(segs):
        a0, a1 = map(float, s['t_abs']); g0 = max(f0, fr(a0)); g1 = f1 if i == len(segs) - 1 else min(f1, max(g0, fr_fin(a1))); mv = s['movimiento']; ar = dict(s.get('args') or {})
        if 'degrees' not in ar and isinstance(ar.get('giro_grados'),(int,float)):ar['degrees']=ar['giro_grados']
        if 'distance' not in ar and isinstance(ar.get('height_m'),(int,float)):
            ar['distance']=abs(ar['height_m']);ar['dir_ud']='UP' if ar['height_m']>=0 else 'DOWN'
        if 'distance' not in ar and isinstance(ar.get('metros'),(int,float)):ar['distance']=ar['metros']
        ini = dict(cur); fin = dict(cur); modo = 'seguir'; nota = None; estado = 'ejecutado'
        def falta(campo, mod, acc, msg):
            F(f'camera/{v["vineta"]}/segmentos[{i}]/{mv}.{campo}', mod, acc, msg, tid); return 'falta_dato'
        if mv in ('STATIC', 'TRIPOD'): modo = 'fijo'
        elif mv in ('DOLLYIN', 'DOLLYOUT', 'PUSH', 'PULL'):
            sr = ar.get('size_range')
            if sr:
                m1 = medf(g1); e1, err = emplazar(m1, sr[1], cur['lente'], S['elev'], (S['orient'] or 0) + cand[0], S['xlado'], S['aire'], cand[1], z_cam=z_cam)
                if not err: p1 = params(e1, ancla(g1)); fin.update(dist=p1['dist'], altura=p1['altura'], mira=p1['off'] - base_p['off']); nota = f'dolly {sr[0]}→{sr[1]} (dist {ini["dist"]:.2f}→{fin["dist"]:.2f} m)'
            elif isinstance(ar.get('distance'), (int, float)): fin['dist'] = max(0.01, cur['dist'] + (-1 if mv in ('DOLLYIN', 'PUSH') else 1) * ar['distance']); nota = f'dolly {ar["distance"]} m'
            elif isinstance(ar.get('percent'), (int, float)): fin['dist'] = cur['dist'] * (1 + (-1 if mv in ('DOLLYIN', 'PUSH') else 1) * ar['percent'] / 100); nota = f'dolly {ar["percent"]}%'
            else: estado = falta('extremo', 'SB (size_range, distance o percent)', 'dar plano final o distancia', 'dolly sin extremo'); modo = 'fijo'
        elif mv in ('ZOOMIN', 'ZOOMOUT', 'CRASHZOOM'):
            modo = 'fijo'; sr = ar.get('size_range')
            if sr and sr[0] in TABLA and sr[1] in TABLA:
                fin['lente'] = cur['lente'] * TABLA[sr[0]] / TABLA[sr[1]]; m1 = medf(g1)
                e1, err = emplazar(m1, sr[1], fin['lente'], S['elev'], (S['orient'] or 0) + cand[0], S['xlado'], S['aire'], cand[1], z_cam=z_cam)
                if not err: fin['mira'] = (e1['look'] - ancla(g1)) - base_p['off']
                nota = f'zoom {sr[0]}→{sr[1]} ({ini["lente"]:.0f}→{fin["lente"]:.0f} mm)'
            elif isinstance(ar.get('percent'), (int, float)): fin['lente'] = cur['lente'] * (1 + (1 if mv != 'ZOOMOUT' else -1) * ar['percent'] / 100); nota = f'zoom {ar["percent"]}%'
            else: estado = falta('extremo', 'SB (size_range o percent)', 'dar plano final', 'zoom sin extremo')
        elif mv in ('PAN', 'TILT', 'ROLL', 'WHIPPAN'):
            modo = 'paneo'; g = ar.get('degrees')
            anchors=ar.get('anchors',ar.get('extremos'))
            if mv in ('PAN','WHIPPAN') and not isinstance(g,(int,float)) and isinstance(anchors,list) and len(anchors)==2:
                pts=[]
                for point in anchors:
                    if isinstance(point,list) and len(point)==3 and all(isinstance(x,(int,float)) for x in point):pts.append(Vector(point))
                    else:
                        pid=buscar_id(point,list(ACT));pts.append(bpy.data.objects[pid].matrix_world.translation.copy() if pid else None)
                if all(p is not None for p in pts):
                    pos=obj_fn(g0)+Vector((math.cos(cur['az'])*cur['dist'],math.sin(cur['az'])*cur['dist'],cur['altura']));base=obj_fn(g0)-pos;aa=pts[0]-pos;bb=pts[1]-pos;ini['yaw']=cur['yaw']+RIG._wrap(math.atan2(aa.y,aa.x)-math.atan2(base.y,base.x));fin['yaw']=cur['yaw']+RIG._wrap(math.atan2(bb.y,bb.x)-math.atan2(base.y,base.x));nota='paneo entre anclas explícitas'
                else:estado=falta('anchors','SB + 02N/4a2','dar dos IDs/posiciones de ancla','anclas no construidas')
            elif mv == 'WHIPPAN' and not isinstance(g, (int, float)):
                lid = buscar_id(ar.get('label'), list(ACT))
                if lid:
                    mm = medir(lid, g1); pnt = (mm['cabeza']['centro'] if mm and mm['cabeza'] else (mm['centro'] if mm else bpy.data.objects[lid].matrix_world.translation.copy())); nota = f'WHIPPAN hacia {lid}'
                    cpos = obj_fn(g0) + Vector((math.cos(cur['az']) * cur['dist'], math.sin(cur['az']) * cur['dist'], cur['altura']))
                    d0 = obj_fn(g0) - cpos; d1 = pnt - cpos; fin['yaw'] = cur['yaw'] + RIG._wrap(math.atan2(d1.y, d1.x) - math.atan2(d0.y, d0.x))
                else: estado = falta('ancla', 'SB (label con ID) + 4a2/02N', 'enlazar el destino a un ID del .blend', 'WHIPPAN sin destino construido')
            elif isinstance(g, (int, float)):
                if mv in ('PAN','WHIPPAN'): fin['yaw'] = cur['yaw'] + math.radians(g) * (-1 if str(ar.get('dir_lr') or '').upper() == 'R' else 1)
                elif mv == 'TILT': fin['pitch'] = cur['pitch'] + math.radians(g) * (1 if str(ar.get('dir_ud') or '').upper() == 'UP' else -1)
                else: fin['roll'] = cur['roll'] + math.radians(g) * (-1 if str(ar.get('dir_rot') or '').upper() == 'CW' else 1)
                nota = f'{mv} {g}°'
            else: estado = falta('grados|anclas', 'SB (DSL /PAN:dir:grados) o 02N/4a2 (anclas inicio/fin con ID)', 'dar grados o anclas', f'{mv} sin grados ni anclas: cámara quieta en ese tramo')
            libres_e.append((g0, g1 + 1)); libres_i.append((g0, g1 + 1))
        elif mv == 'ORBIT':
            g = ar.get('degrees')
            if isinstance(g, (int, float)):
                sgn = 1 if str(ar.get('dir_orbit') or ar.get('dir_lr') or '').upper() in ('R', 'CCW') else -1
                fin['az'] = cur['az'] + math.radians(g) * sgn; nota = f'órbita {g}°'
            else: estado = falta('grados', 'SB (DSL /ORBIT:dir:grados)', 'dar amplitud y sentido', 'ORBIT sin amplitud'); modo = 'fijo'
        elif mv == 'TRUCK':
            dd = ar.get('distance')
            if isinstance(dd, (int, float)): modo = 'fijo'; fin['lateral'] = cur['lateral'] + dd * (1 if str(ar.get('dir_lr') or '').upper() == 'R' else -1); nota = f'truck {dd} m'
            else: estado = falta('distancia', 'SB (DSL /TRUCK:dir:distancia)', 'dar metros', 'TRUCK sin distancia'); modo = 'fijo'
        elif mv in ('PEDESTAL', 'CRANE', 'BOOM'):
            dd = ar.get('distance')
            ends=ar.get('anchors',ar.get('extremos'));ends=[(x[2] if isinstance(x,list) and len(x)==3 else x) for x in ends] if isinstance(ends,list) else None
            if ends is not None and len(ends)==2 and all(isinstance(x,(int,float)) for x in ends):ini['altura']=ends[0]-obj_fn(g0).z;fin['altura']=ends[1]-obj_fn(g1).z;nota=f'{mv} con alturas absolutas explícitas'
            elif isinstance(dd, (int, float)): fin['altura'] = cur['altura'] + dd * (1 if str(ar.get('dir_ud') or '').upper() == 'UP' else -1); nota = f'{mv} {dd} m'
            else: estado = falta('altura', 'SB (DSL con distancia) o 02N (alturas inicio/fin)', 'dar extremos verticales', f'{mv} sin extremos verticales (magnitud {ar.get("magnitude")} no da metros)'); modo = 'fijo'
        elif mv in ('TRACK', 'FOLLOW', 'LEAD', 'TRACKSIDE'):
            d_ = (medf(g1)['centro'] - medf(g0)['centro']); d_.z = 0
            if d_.length >= CFG['track_desplazamiento_min_m']:
                modo = 'seguir'; nota = f'{mv}: sigue al sujeto {d_.length:.2f} m (desplazamiento real del 01)'
                if mv in ('FOLLOW', 'LEAD'): fin['az'] = ini['az'] = math.atan2(-d_.y, -d_.x) if mv == 'FOLLOW' else math.atan2(d_.y, d_.x)
                elif mv in ('TRACK', 'TRACKSIDE'):
                    pedido_az = (S['orient'] or 0) + cand[0]; respaldo = cur['az']
                    def az_fn(f, _med=medf, _az=pedido_az, _fb=respaldo):
                        m = _med(f); fv = None if not m else (m.get('frente_cara') or m.get('frente'))
                        hallado = BUS.acimut_mundo(fv, _az)
                        return _fb if hallado is None else hallado
                    az_fn_tramo = az_fn
            else: estado = falta('desplazamiento', '01 (movimiento del sujeto) o SB (distancia)', 'mover al sujeto o dar recorrido', f'{mv} sin desplazamiento real del sujeto'); modo = 'fijo'
        elif mv == 'DOLLYZOOM':
            dd = ar.get('distance')
            if isinstance(dd, (int, float)): s_ = 1 if str(ar.get('dir_io') or '').upper() == 'OUT' else -1; fin['dist'] = max(0.05, cur['dist'] + s_ * dd); fin['lente'] = cur['lente'] * fin['dist'] / cur['dist']; nota = 'dolly-zoom'
            else: estado = falta('distancia', 'SB', 'dar recorrido del dolly-zoom', 'DOLLYZOOM sin recorrido'); modo = 'fijo'
        elif mv in ('HANDHELD', 'SHOULDER', 'STEADICAM', 'GIMBAL', 'SLIDER'): modo = 'fijo'; nota = f'rig {mv}'
        elif mv in ('FLYTHROUGH', 'FLYOVER', 'DRONEREVEAL'): estado = 'no_programado'; modo = 'fijo'; nota = f'{mv}: necesita trayectoria con anclas (no está en el SB)'; F(f'camera/{v["vineta"]}/segmentos[{i}]/{mv}.trayectoria', 'SB + 02N', 'dar anclas de recorrido', nota, tid)
        else: estado = 'no_programado'; modo = 'fijo'; nota = f'{mv} sin traducción'
        est_mov.append({'comando': mv, 'args': ar, 'estado': estado, 'detalle': nota or ('cámara quieta' if mv in ('STATIC', 'TRIPOD') else '')})
        tramo = {'f0': g0, 'f1': g1, 'modo': modo, 'ini': ini, 'fin': fin, 'curva': s.get('curva'), 'corte_ini': i == 0}
        if az_fn_tramo is not None: tramo['az_fn'] = az_fn_tramo
        tramos.append(tramo); az_fn_tramo = None
        cur = dict(fin)
    tray, av = RIG.trayectoria(tramos, FPS, obj_fn, lim, suavidad=S['suav'], sacudir=S['sacudir'], t_base=t0)
    for x in av[:3]: est_mov.append({'comando': 'LIMITE_SET', 'args': {}, 'estado': 'aviso', 'detalle': f'cuadro {x[0]}: {x[1]}'})
    return tray, None, {'libres_e': libres_e, 'libres_i': libres_i, 'lim': lim, 'tramos': tramos, 'medf': medf}
def ref_eje_lado(S, f): return S.get('_lado_eje')
def eje_s(S, f, p):
    A_, B_ = S['_eje'][:2]; pa = medir(A_, f)['centro']; pb_ = medir(B_, f)['centro']; return (pb_.x - pa.x) * (p.y - pa.y) - (pb_.y - pa.y) * (p.x - pa.x)
def _xyz(v):
    return None if v is None else (float(v.x), float(v.y), float(v.z))
def puntos_cuadro(m, plano):
    rg = region(m, plano)
    if rg is None: return [], None, None
    pts = m['puntos']
    if not rg['cuerpo_entero'] and m.get('cabeza'): pts = m['cabeza']['puntos_cara']
    else:
        banda = [p for p in pts if rg['bot'] - 1e-3 <= p.z <= rg['top'] + 1e-3]
        pts = banda or pts
    pts = pts[::max(1, len(pts) // CFG['puntos_region'])]
    z = (rg['top'] + rg['bot']) / 2 if rg['cuerpo_entero'] else rg['top'] - rg['Hf'] / 2
    return pts, (float(rg['xy'].x), float(rg['xy'].y), float(z)), float(rg['Hf'])
def muestras_busqueda(v, S, f0, f1, medf, plano_de):
    segs = []
    for s in (v.get('segmentos') or [{'t_abs': v['t_abs'], 'movimiento': 'STATIC', 'args': {}}]):
        segs.append({'t0': float(s['t_abs'][0]), 't1': float(s['t_abs'][1]), 'movimiento': s.get('movimiento') or 'STATIC', 'args': dict(s.get('args') or {})})
    efectos, _completo = BUS.efectos_de_segmentos(segs, f0, f1, FPS, TABLA)
    ancla = None; muestras = []
    for f in range(f0, f1 + 1):
        ef = efectos[f]; m = medf(f)
        if m is None: return None
        pts, mira, hf = puntos_cuadro(m, plano_de(f))
        frente = _xyz(m.get('frente_cara') or m.get('frente'))
        if ef['nueva_ancla'] or ancla is None: ancla = {'frente': frente, 'mira': mira, 'hf': hf}
        if ef['seguir_frente']: base_frente, base_mira, base_hf = frente, mira, hf
        else:
            base_frente = ancla['frente']
            base_mira = mira if ef['mira_sigue'] else ancla['mira']
            base_hf = hf if ef['mira_sigue'] else ancla['hf']
        eje = None
        if S.get('_eje') and S['_eje'][0] != 'ambiguo':
            pa, pb_ = medir(S['_eje'][0], f), medir(S['_eje'][1], f)
            if pa and pb_: eje = (_xyz(pa['centro']), _xyz(pb_['centro']))
        def obs(loc, f=f):
            bv = env_bvh(f)
            if bv is None: return (False, None, None)
            p = Vector(loc); den = dentro_de_malla(bv, p)
            if den: return (True, 0.0, den)
            nn = bv.find_nearest(p)
            if nn[0] is None: return (False, None, None)
            return (False, float(nn[3]), bv.quien(nn[2]))
        muestras.append({'frente': base_frente, 'mira': base_mira, 'hf': base_hf, 'puntos': [_xyz(p) for p in pts], 'centro': _xyz(m['centro']),
                         'cabeza': _xyz(m['cabeza']['centro']) if m.get('cabeza') else _xyz(m['centro']), 'frente_cara': frente, 'altura': float(m['H']),
                         'eje': eje, 'yaw': ef['yaw'], 'roll': math.radians(S['roll_deg']), 'altura_extra': ef['altura_extra'], 'dist_mul': ef['dist_mul'],
                         'libre_encuadre': ef['libre_encuadre'], 'libre_inclin': ef['libre_inclin'], 'modelado': ef['modelado'], 'obstaculo': obs})
    return muestras
# ---------------- bucle de tomas ----------------
SBV = {v['id']: v for v in (SBE or {}).get('vinetas', [])}; ELEV_TAB = ELEV
SHOTS_E = {s.get('vineta'): s for s in (E.get('camera') or {}).get('shots', [])}
tomas = []; trays = []; ref_eje = {}
def _sonda_si_pidieron():
    import os
    if os.environ.get('SONDA_CAMARA') != '1': return
    actor = os.environ.get('SONDA_ACTOR') or ''; crudos = os.environ.get('SONDA_FRAMES') or ''; salida = os.environ.get('SONDA_SALIDA') or ''
    frames = [int(x) for x in crudos.split(',') if x.strip()]
    if not actor or not frames or not salida: return
    import sonda_inspeccion_camara as sonda
    ruta = sonda.escribir(bpy.context, actor, frames, salida, AQUI / 'camara_v2_config.json')
    AVISOS.append('sonda de solo lectura escrita en ' + str(ruta))
_sonda_si_pidieron()
for n, v in enumerate(sorted(SBC['vinetas'], key=lambda v: float(v['t_abs'][0])), 1):
    tid = f'toma{n:02d}'; TOMA_ACTUAL = tid; t0, t1 = map(float, v['t_abs']); f0, f1 = fr(t0), fr_fin(t1); vin = SBV.get(v['vineta']) or {}; cm = CMDS.get(v['vineta']) or {}
    S = leer_toma(v, vin, cm, tid); tgt = S['insert'] or v.get('objetivo')
    T = {'toma': n, 'id': f'e{SBC.get("escena", "")}_t{n:02d}', 'vineta': v['vineta'], 't0': t0, 't1': t1, 'frame_ini': f0, 'frame_fin': f1, 'objetivo': tgt,
         'tipo': S['plano0'], 'estado': None, 'motivos': [], 'notas': [], 'comandos': S['estado_cmd']}
    tr = (vin.get('transicion_salida') or {}).get('tipo') or v.get('transicion_salida'); modo_tr = CFG['transiciones'].get(str(tr).upper()) if tr else None
    T['transicion'] = {'tipo': tr, 'montaje': modo_tr}
    T['comandos'].append({'comando': f'transicion:{tr}', 'args': {}, 'estado': ('ejecutado' if modo_tr in ('corte', 'fin') else ('montaje' if modo_tr else 'no_programado')),
                          'detalle': {'corte': 'corte exacto en el cuadro del SB', 'fin': 'fin de escena (corte)', 'corte_audio': 'corte de imagen exacto; el desfase de audio J/L no está en el motor (se avisa)',
                                      'fundido_cruzado': 'AVISO: encadenado va en la unión final; la unión de tomas todavía no lo aplica (sale corte)', 'fundido_negro': 'AVISO: fundido a negro va en la unión final; todavía no se aplica (sale corte)',
                                      'fundido_blanco': 'AVISO: fundido a blanco va en la unión final; todavía no se aplica (sale corte)', 'barrido': 'AVISO: barrido va en la unión final; todavía no se aplica (sale corte)'}.get(modo_tr, 'transición sin traducción')})
    if modo_tr in ('fundido_cruzado', 'fundido_negro', 'fundido_blanco', 'barrido'): AVISOS.append(f'{tid}: transición {tr} pendiente en la unión final (sale corte)')
    m0 = (medir(tgt, f0, tid) if tgt else None)
    if m0 is None:
        T['estado'] = 'bloqueada'; T['motivos'] = [f'objetivo {tgt} no construido en la escena']; F(f'camera/{v["vineta"]}/objetivo', 'ADN/objetos (4b/4c/SELLO OBJ) + motor', 'construir el objetivo', f'{tgt} no existe en el .blend', tid)
        tomas.append(T); trays.append(None); continue
    if m0.get('tipo') == 'personaje':
        clase = clasificar_medida_cabeza(m0.get('cabeza')); T['cabeza_medida'] = clase
        if not clase['valida_visual']: F(f'actors/{tgt}/rig/cabeza', 'motor (rig) / ADN', 'mostrar una malla de cabeza; el hueso solo no aprueba la apariencia', clase['mensaje'], tid)
    if SW['manifiesto_espacial']:
        T['manifiesto'] = {str(f): {'altura_m': round(x['H'], 4), 'zmin': round(x['zmin'], 4), 'cabeza': ({'centro': r3(x['cabeza']['centro']), 'alto_m': round(x['cabeza']['alto'], 4), 'origen': x['cabeza'].get('origen'), 'malla_visible': x['cabeza'].get('malla_visible'), 'valida_visual': x['cabeza'].get('valida_visual'), 'production_approved': False} if x['cabeza'] else None),
                                    'frente': r3(x['frente']) if x['frente'] is not None else None, 'frente_cara': r3(x['frente_cara']) if x.get('frente_cara') is not None else None,
                                    'frente_metodo': x.get('frente_metodo'), 'huesos_z': {k: round(z, 4) for k, z in (x.get('huesos') or {}).items() if z is not None}}
                           for f in (f0, (f0 + f1) // 2, f1) for x in [medir(tgt, f, tid)] if x}
        if m0['tipo'] == 'personaje':
            h = ADN_H.get(tgt)
            if isinstance(h, (int, float)) and abs(m0['H'] - h) / h > CFG['tolerancia_escala_adn']:
                AVISOS.append(f'{tgt}: altura medida en el .blend {m0["H"]:.3f} m vs ADN {h} m (dif {100*(m0["H"]-h)/h:+.0f}%). No se cambia el ADN; la cámara usa la medida.')
    par = eje_par((vin.get('continuidad') or {}).get('eje')); S['_eje'] = None; S['_lado_eje'] = None
    if par and par[0] == 'ambiguo':
        F(f'camera/{v["vineta"]}/continuidad.eje', 'SB + 4a2/02N (ID espacial del segundo elemento)', 'enlazar el elemento del eje a un ID del .blend', f'eje «{(vin.get("continuidad") or {}).get("eje")}» sin ID construido: no se verifica', tid)
    elif par: S['_eje'] = par; S['_lado_eje'] = ref_eje.get(par)
    if SBE is None: F(f'camera/{v["vineta"]}/orientacion', 'SB (esc_N.json)', 'pasar esc_N.json del SB', 'sin esc_N.json', tid)
    def plano_de(f, v=v):   # entre dos keyframes del SB con distinto plano (dolly/zoom) se revisa con el más cerrado de los dos
        ks = v.get('keyframes') or [{}]; t = (f - 1) / FPS
        k0 = next((k for k in reversed(ks) if float(k.get('t', 0)) <= t + 1e-6), ks[0]); k1 = next((k for k in ks if float(k.get('t', 0)) > t + 1e-6), k0)
        return min((k0.get('plano'), k1.get('plano')), key=lambda p: TABLA.get(p, 99))
    spec = {'excluir_env': mallas_de(tgt), 'plano_de': plano_de, 'excluir_oclusion': set(S['sujetos']) | ({S['ots'][0]} if S['ots'] else set()) | ({S['pov']} if S['pov'] else set()),
            'pitch_pedido': None if (S['z_hueso'] or S['ots'] or S['pov']) else -S['elev'], 'roll_pedido_deg': S['roll_deg'], 'cara': not (S['orient'] is not None and abs(S['orient']) >= 150) and not S['pov'],
            'revisar_encuadre': not S['pov']}
    if not SW['resolver_camara']:
        tray = []
        for f in range(f0, f1 + 1):
            sc.frame_set(f); mw = CAM.matrix_world; tray.append({'f': f, 'loc': mw.translation.copy(), 'quat': mw.to_quaternion(), 'lente': CAM.data.lens, 'roll': 0, 'mira': None})
        spec['medir'] = lambda f, tgt=tgt, tid=tid: medir(tgt, f, tid); spec['eje'] = (par[0], par[1], ref_eje.get(par)) if par and par[0] != 'ambiguo' and ref_eje.get(par) is not None else None
        mal = validar(tray, spec, f0, f1) if SW['validacion_camara'] else []
        T['camara'] = 'existente (resolver_camara.off)'; T['estado'] = estado_visual('pasa' if not mal else 'bloqueada', T.get('cabeza_medida')); T['motivos'] = sorted({x[1] for x in mal}); T['muestras_malas'] = mal[:8]
        if par and par[0] != 'ambiguo' and ref_eje.get(par) is None and tray: ref_eje[par] = eje_s(S | {'_eje': par}, f0, tray[0]['loc'])
        tomas.append(T); trays.append(None); continue
    intentos = []; elegido = None; medf = (lambda f: grupo(S['sujetos'], f, tgt, tid)) if len(S['sujetos']) > 1 else (lambda f: medir(tgt, f, tid))
    if S.get('pov') or S.get('ots') or not S.get('lens'):
        informe = BUS.sin_modelo('POV, OTS o toma sin lente: la posición no sale del cono de elevación')
    else:
        muestras = muestras_busqueda(v, S, f0, f1, medf, plano_de)
        if not muestras: informe = BUS.sin_modelo('El objetivo no está medido en el primer cuadro')
        else:
            informe = BUS.buscar({'sensor_mm': SENSOR_W, 'lens_mm': float(S['lens']), 'aspecto': ASP, 'elev_deg': float(S['elev']), 'orient_deg': float(S['orient'] or 0),
                                  'aire': float(S['aire']), 'xlado': float(S['xlado']), 'region_min': CFG['region_en_cuadro_min'], 'max_cara_deg': CFG['max_angulo_cara_deg'],
                                  'inclinacion_tol_deg': CFG['inclinacion_tolerancia_deg'], 'roll_tol_deg': CFG['roll_tolerancia_deg'], 'holgura_max_m': CFG['holgura_max_m'],
                                  'holgura_frac_distancia': CFG['holgura_frac_distancia'], 'holgura_frac_altura': CFG['holgura_frac_altura'], 'lado': None if S['cruce_permitido'] else S.get('_lado_eje'),
                                  'cara_exigida': spec['cara'], 'azimuts_deg': CFG['busqueda_acimut_deg'], 'factores': CFG['busqueda_factor_distancia'], 'muestras': muestras})
    T['busqueda_matematica'] = BUS.resumen(informe)
    propuestas = list(informe.get('propuestas') or [])
    if not propuestas: propuestas = [{'az_extra_deg': a, 'factor_distancia': fd} for a in CFG['busqueda_acimut_deg'] for fd in CFG['busqueda_factor_distancia']]
    vistos = set()
    for cand in propuestas:
        clave = (round(float(cand['az_extra_deg']), 4), round(float(cand['factor_distancia']), 4))
        if clave in vistos: continue
        vistos.add(clave)
        if len(intentos) >= CFG['reparaciones_max']: break
        daz, fd = clave
        em_ = []; tray, err, ex = construir(v, S, (daz, fd), tid, em_)
        if err: intentos.append({'az_extra': daz, 'fd': fd, 'error': err}); continue
        spec['medir'] = ex['medf']; lado = S['_lado_eje']
        if par and par[0] != 'ambiguo' and lado is None and not S['cruce_permitido']: lado = eje_s(S, f0, tray[0]['loc'])
        spec['eje'] = (par[0], par[1], lado) if (par and par[0] != 'ambiguo' and not S['cruce_permitido']) else None
        mal = validar(tray, spec, f0, f1, ex['libres_e'], ex['libres_i']) if SW['validacion_camara'] else []
        intentos.append({'az_extra': daz, 'fd': fd, 'fallos': len(mal), 'motivos': sorted({x[1] for x in mal}), 'muestras_malas': mal[:6]})
        if not mal: elegido = (tray, daz, fd, em_, ex, lado); break
    if elegido:
        tray, daz, fd, em_, ex, lado = elegido; T['estado'] = estado_visual('pasa', T.get('cabeza_medida')); T['reparacion'] = None if (daz == 0 and fd == 1.0) else {'acimut_extra_deg': daz, 'factor_distancia': fd, 'intentos': len(intentos)}
        if par and par[0] != 'ambiguo' and ref_eje.get(par) is None and lado is not None: ref_eje[par] = lado
    else:
        val = [i for i in intentos if 'fallos' in i]; mejor = min(val, key=lambda i: i['fallos']) if val else None
        em_ = []; tray, err, ex = construir(v, S, ((mejor or {}).get('az_extra', 0), (mejor or {}).get('fd', 1.0)), tid, em_)
        T['estado'] = 'bloqueada'; T['motivos'] = mejor['motivos'] if mejor else [i.get('error') for i in intentos][:3]; T['mejor_intento'] = mejor; T['intentos'] = len(intentos)
    T['comandos'] += em_
    if tray:
        k0 = tray[0]; T['camara'] = {'loc': r3(k0['loc']), 'mira': r3(k0['mira']), 'lente': round(k0['lente'], 2), 'sensor_ancho_mm': SENSOR_W, 'sensor_fit': 'HORIZONTAL',
                                     'de': 'rig por coordenadas (r2) desde plano/ángulo/orientación SB + manifiesto medido', 'elevacion_deg': S['elev'], 'orientacion_sb_deg': S['orient'],
                                     'distancia_m': round((k0['loc'] - k0['mira']).length, 4)}
        T['recorrido'] = [{'f': x['f'], 'loc': r3(x['loc']), 'quat': r3(x['quat']), 'lente': round(x['lente'], 3)} for x in tray[::max(1, int(FPS // 4))]]
        T['limites_set'] = {k: (round(x, 3) if isinstance(x, float) else x) for k, x in ex['lim'].items() if k != 'max_dist'}
        T['foco'] = S['foco']
    T['notas'] = [f"{c['comando']}: {c['detalle']}" for c in T['comandos'] if c.get('detalle')]
    T['sin_silencio'] = all(c['estado'] in ('ejecutado', 'falta_dato', 'no_programado', 'montaje', 'solo_revision', 'aviso') for c in T['comandos'])
    tomas.append(T); trays.append((tray, S) if tray else None)
# ---------------- hornear la trayectoria en el .blend (lo que se graba) ----------------
if SW['resolver_camara']:
    ob = CAM; cd = ob.data
    for blk in (ob, cd):
        if blk.animation_data: blk.animation_data_clear()
    ob.rotation_mode = 'QUATERNION'; dmin = 10.0
    for T, ts in zip(tomas, trays):
        if not ts:
            continue
        tray, S = ts; prevq = None
        for x in tray:
            q = x['quat'].copy()
            if prevq is not None and prevq.dot(q) < 0: q.negate()
            prevq = q; ob.location = x['loc']; ob.rotation_quaternion = q; cd.lens = x['lente']
            ob.keyframe_insert('location', frame=x['f']); ob.keyframe_insert('rotation_quaternion', frame=x['f']); cd.keyframe_insert('lens', frame=x['f'])
            if x['mira'] is not None: dmin = min(dmin, (x['loc'] - x['mira']).length)
        # foco
        fo = S['foco']
        if fo:
            cd.dof.use_dof = fo[0] != 'deep'; cd.keyframe_insert('dof.use_dof', frame=tray[0]['f'])
            if fo[0] != 'deep':
                cd.dof.aperture_fstop = CFG['foco']['fstop_shallow']
                for x in tray[::max(1, int(FPS // 6))]:
                    who = fo[1][0] if fo[0] == 'rack' and x['f'] < (tray[0]['f'] + tray[-1]['f']) / 2 else (fo[1][1] if fo[0] == 'rack' else (fo[1] or T['objetivo']))
                    mm = medir(who, x['f']); p = (mm['cabeza']['centro'] if mm and mm['cabeza'] else (mm['centro'] if mm else x['mira']))
                    cd.dof.focus_distance = (p - x['loc']).length; cd.keyframe_insert('dof.focus_distance', frame=x['f'])
        else:
            cd.dof.use_dof = False; cd.keyframe_insert('dof.use_dof', frame=tray[0]['f'])
    cd.clip_start = max(0.001, min(cd.clip_start, dmin * 0.25))
    for blk in (ob, cd):
        act = blk.animation_data.action if blk.animation_data else None
        if not act: continue
        fijar_constante(act)   # 4.4+ layers; 4.2 fcurves. Un keyframe por cuadro, sin interpolación inventada.
# verificación cruzada con la cámara REAL (world_to_camera_view, mismo método que blender_camaras.py del 05)
for T in tomas:
    if T['estado'] is None or not T.get('objetivo'): continue
    f = (T['frame_ini'] + T['frame_fin']) // 2; m = medir(T['objetivo'], f, T['toma'] if isinstance(T.get('toma'), str) else f"toma{T['toma']:02d}")
    if m: sc.frame_set(f); T['verif_blender_mitad'] = {'frame': f, 'uv': r3(w2c(sc, CAM, (m['cabeza']['centro'] if m['cabeza'] else m['centro'])))}
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'escena.blend'), copy=True)
res = {'version': CFG['version'], 'contrato': 'camara_v2', 'interruptores': SW, 'fps': FPS, 'resolucion': [sc.render.resolution_x, sc.render.resolution_y], 'sensor_ancho_mm': SENSOR_W,
       'tomas': tomas, 'faltantes': FALT, 'avisos': AVISOS, 'production_approved': False,
       'resumen': {'pasa': [t['toma'] for t in tomas if t['estado'] == 'pasa' and (t.get('cabeza_medida') or {}).get('valida_visual', True)], 'bloqueada': [t['toma'] for t in tomas if t['estado'] != 'pasa' or (t.get('cabeza_medida') or {}).get('valida_visual') is False]}}
json.dump(res, open(OUT / 'camara_v2.json', 'w'), ensure_ascii=False, indent=1, default=str)
print('CAMARA_V2_OK ' + json.dumps(res['resumen']))
