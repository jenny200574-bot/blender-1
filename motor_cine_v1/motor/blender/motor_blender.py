"""motor_blender — MOTOR UNIFICADO v1 (Blender 5.2.3, GPU) [10-nov-2026]. Código propio MYIA.
NO CREA NADA: abre el molde de escenario publicado y añade (append) los moldes de personaje publicados; no hay esqueleto
genérico, ni mallas armadas, ni escenario propio, ni caminata en línea recta, ni piso fijo en 0.
Pasos (todo medido y reportado en reporte_motor.json):
  1 escenario: copia del molde (nunca se sobrescribe el original) + piso real por raycast a las superficies caminables.
  2 personajes: append del armature + sus mallas (sin CAM/piso/banco del molde), nombres de la escena = ids del 01 (ch-...),
    escala ADN ±2% (escala_adn.escalar, el molde original no se toca).
  3 movimiento: clips CMU/100STYLE -> Mwni animation_retargeting 2.4.0 (headless) -> ciclo medido (período y zancada) ->
    composición por cuadro sobre la ruta A*+RVO2 (fase del ciclo = metros caminados) + capa de gestos (mirar/señalar/hablar)
    + foot-lock APROBADO (pies_bloqueo.py, sin cambios) + acople (personaje pequeño al hueso del portador hallado por nombre/sinónimo/geometría, cita del 01).
  4 escenario vivo: SOLO piezas que la fábrica marcó (prop 'vivo') y apariciones de objetos que ya existen en el molde.
  5 cámara: storyboard v2 (altura_m) -> camara_calculada (encuadre/lado/altura sin roll) por viñeta, movimientos DSL
    (STATIC/DOLLYIN/DOLLYOUT/PAN/TRACK/CRANE), Shakify solo si el SB lo pide; ocultar_estorbos + camara_sin_paredes por toma.
  6 revisión (umbrales del gate viejo fisica_final) y guardado. El render lo hace render_motor.py (GPU EEVEE).
Uso: blender -b --factory-startup -P motor_blender.py -- --corrida DIR --motor DIR [--sin_ocultar] [--frames N]"""
import bpy, sys, os, json, math, time, argparse, re, atexit, traceback
from mathutils import Vector, Matrix, Quaternion, Euler
from mathutils.bvhtree import BVHTree

AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
import escala_adn as ESC
import pies_bloqueo as PIES
import camara_calculada as CC
import numeros_json as NJ
import relaciones_blender as RB   # [argon_v2] relaciones físicas genéricas (hueso por rig, apoyo en superficie)

T0 = time.time(); LOG = []; _MOTOR_OK = False
def log(*a):
    s = f"[{time.time() - T0:7.1f}s] " + " ".join(str(x) for x in a); print(s, flush=True); LOG.append(s)

def _escribir_reporte_parcial(typ=None, val=None, tb=None):
    """Si el script muere a media corrida, deja reporte_motor.json con el error (nunca un OK silencioso)."""
    try:
        rep = globals().get('R')
        if not isinstance(rep, dict):
            return
        if typ is not None:
            msg = ''.join(traceback.format_exception(typ, val, tb)) if tb is not None else f"{getattr(typ, '__name__', typ)}: {val}"
            rep['estado'] = 'FALLO'
            rep['error'] = f"{getattr(typ, '__name__', typ)}: {val}"
            rep['traceback'] = msg[-8000:]
        rep['segundos'] = round(time.time() - T0, 1)
        cor = globals().get('COR')
        if cor:
            json.dump(rep, open(f'{cor}/reporte_motor.json', 'w'), indent=1, ensure_ascii=False, default=str)
            log('reporte_parcial', f'{cor}/reporte_motor.json')
    except Exception as ex:
        print('no se pudo escribir reporte_motor parcial:', ex, flush=True)

def _salir_por_excepcion(typ, val, tb):
    msg = ''.join(traceback.format_exception(typ, val, tb))
    print(msg, flush=True)
    try:
        log('EXCEPCION_FATAL', getattr(typ, '__name__', typ), val)
    except Exception:
        pass
    _escribir_reporte_parcial(typ, val, tb)
    os._exit(1)

def _atexit_chequeo():
    # Blender -P a veces sale 0 aunque el script haya abortado: si no se guardó el blend, forzamos código 1.
    if not _MOTOR_OK:
        try:
            print('MOTOR_SALIDA: no se completó el guardado de escena_motor.blend; se sale con código 1', flush=True)
        except Exception:
            pass
        os._exit(1)

sys.excepthook = _salir_por_excepcion
atexit.register(_atexit_chequeo)

argv = sys.argv[sys.argv.index('--') + 1:]
ap = argparse.ArgumentParser(); ap.add_argument('--corrida', required=True); ap.add_argument('--motor', required=True)
ap.add_argument('--sin_ocultar', action='store_true'); ap.add_argument('--frames', type=int, default=0); ap.add_argument('--paso_ocultar', type=int, default=2)
A = ap.parse_args(argv)
COR = A.corrida; MOT = A.motor
E = json.load(open(f'{COR}/entrada_motor.json')); M = json.load(open(f'{COR}/movimiento.json')); PL = json.load(open(f'{COR}/plan.json'))
IDX = json.load(open(f'{MOT}/assets/indice_clips.json'))
# Kimodo ON (Ricardo t983u/t995u): tramos generados en GPU por pod/kimodo_gen.py (pedidos de kimodo/kimodo_pedidos.py)
KIMP = {}
try:
    _kp = json.load(open(f'{COR}/kimodo/pedidos.json')); _kg = {x['nombre']: x for x in json.load(open(f'{COR}/kimodo/gen.json'))['pedidos']}
    for _p in _kp['pedidos']:
        if _kg.get(_p['nombre'], {}).get('ok'): KIMP.setdefault(_p['personaje'], []).append(_p)
except Exception as _ex:
    KIMP = {}
FPS = E['fps']; N = A.frames or E['N']
R = {"contrato": "reporte_motor_v1", "blender": bpy.app.version_string, "corrida": COR, "N": N, "fps": FPS, "pasos": {}, "personajes": {}, "avisos": list(E.get('avisos', [])),
     "crea_geometria": False, "moldes_modificados": False}

# ---------------------------------------------------------------- 1 escenario
esc = E['escenario']
bpy.ops.wm.open_mainfile(filepath=f"{COR}/{esc['blend']}")
sc = bpy.context.scene; sc.render.fps = FPS; sc.frame_start = 1; sc.frame_end = N
for o in list(bpy.data.objects):
    if o.type == 'CAMERA': o.hide_render = True                      # cámaras del molde: no se usan (manda el SB)
sys.path.insert(0, AQUI)
import inventario_set as INV
cam_names = []; caminables = []; set_meshes = []
for o in bpy.data.objects:
    if o.type != 'MESH': continue
    lo, hi = INV.bbox_mundo(o); c = INV.clasificar(o, lo, hi); set_meshes.append(o)
    if c == 'caminable': caminables.append(o)
dg = bpy.context.evaluated_depsgraph_get()
def bvh_de(objs):
    V = []; F = []
    for o in objs:
        oe = o.evaluated_get(dg); me = oe.to_mesh(); mw = oe.matrix_world; b = len(V)
        V += [mw @ v.co for v in me.vertices]; F += [tuple(b + i for i in p.vertices) for p in me.polygons]; oe.to_mesh_clear()
    return BVHTree.FromPolygons(V, F) if F else None
PISO = bvh_de(caminables)
def piso_z(x, y, desde=1.5):
    if PISO is None: return 0.0
    hit = PISO.ray_cast(Vector((x, y, desde)), Vector((0, 0, -1)), 5.0)
    return hit[0].z if hit[0] is not None else 0.0
# [argon_v2] centro del set medido (antes piso_z(2.25, 2.0): coordenadas de UN cuarto escritas a mano)
_bx = [v for o in set_meshes for v in (INV.bbox_mundo(o)[0][0], INV.bbox_mundo(o)[1][0])] or [0.0]; _by = [v for o in set_meshes for v in (INV.bbox_mundo(o)[0][1], INV.bbox_mundo(o)[1][1])] or [0.0]
_centro_set = ((min(_bx) + max(_bx)) / 2, (min(_by) + max(_by)) / 2)
R['pasos']['1_escenario'] = {"molde": esc['origen'], "fuente": esc['fuente'], "caminables": [o.name for o in caminables],
                             "piso_z_centro": round(piso_z(*_centro_set), 4), "objetos_set": len(set_meshes)}
log('escenario', esc['fuente'], 'caminables', len(caminables))

# ---------------------------------------------------------------- 2 personajes (append de moldes, sin crear)
EXCLUIR = ('cam', 'piso', 'floor')   # [argon_v2] quitado 'banco_sentada' (objeto de una escena de laboratorio)
def cargar_personaje(p):
    path = f"{COR}/{p['blend']}"
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = list(src.objects)
    arm = next((o for o in dst.objects if o and o.type == 'ARMATURE'), None)
    if arm is None: raise RuntimeError(f"MOLDE_INVALIDO sin armature {p['id']}")
    keep = {arm.name} | {c.name for c in arm.children_recursive}
    for o in dst.objects:
        if o is None: continue
        if o.name in keep: sc.collection.objects.link(o)
        else: bpy.data.objects.remove(o, do_unlink=True)
    pid = p['id']; orig = arm.name; arm.name = pid; arm.data.name = pid + '_esq'
    for c in arm.children_recursive:
        base = c.name.split('.')[0]; c.name = f"{pid}.{base}"
    return arm, orig

def frente_rest(arm):
    """ángulo (grados desde +X) hacia donde mira el molde en reposo; los moldes de fábrica miran -Y."""
    b = arm.data.bones
    if 'femur_L' in b and 'femur_R' in b:
        v = b['femur_R'].head_local - b['femur_L'].head_local; f = Vector((0, 0, 1)).cross(v)
        return math.degrees(math.atan2(f.y, f.x))
    return -90.0

PJ = {}
for p in E['personajes']:
    arm, orig = cargar_personaje(p)
    info = {"molde": p['blend_origen'], "version": p['version'], "estado_molde": p['estado_molde'], "pendiente_aprobacion": p['pendiente_aprobacion'],
            "armature_molde": orig, "mallas": len([c for c in arm.children_recursive if c.type == 'MESH'])}
    H0, z0, z1 = ESC.medir(arm); info['altura_medida_m'] = round(H0, 4); alt = p.get('altura_m')
    if alt:
        dif = H0 / float(alt) - 1; info['altura_adn_m'] = alt; info['dif_pct'] = round(dif * 100, 2)
        if abs(dif) > ESC.TOL:
            info['escala'] = ESC.escalar(arm, float(alt) / H0); H1, _, _ = ESC.medir(arm); info['altura_tras_escala_m'] = round(H1, 4)
            info['escala_estado'] = 'OK_ESCALADO' if abs(H1 / float(alt) - 1) <= 0.005 else 'STOP_ESCALA_FALLIDA'
        else: info['escala_estado'] = 'OK_SIN_ESCALAR'
    else: info['escala_estado'] = 'STOP_FALTA_DATO (sin altura_m en ADN)'
    info['frente_rest_deg'] = round(frente_rest(arm), 1)
    PJ[p['id']] = {"arm": arm, "p": p, "info": info, "alt": float(alt or H0)}
    R['personajes'][p['id']] = info
    log('personaje', p['id'], info['escala_estado'], info['altura_medida_m'])

# ---------------------------------------------------------------- 3 movimiento
import addon_utils
sys.path.insert(0, f'{MOT}/assets/addons')
try:
    addon_utils.enable('animation_retargeting', default_set=True)
except Exception as ex: log('addon_utils', ex)
import animation_retargeting
try: animation_retargeting.register()
except Exception: pass
from animation_retargeting import alignment, baking, drivers

def activar(o):
    for x in bpy.context.selected_objects: x.select_set(False)
    o.select_set(True); bpy.context.view_layer.objects.active = o

def retarget(arm0, clip, alt):
    """Mwni: BVH del clip -> COPIA temporal del armature del molde (contexto Mwni limpio por clip, como en el lab aprobado).
    Devuelve muestras por cuadro (basis por hueso + puntos clave). La copia se borra; el molde no se toca."""
    arm = arm0.copy(); arm.data = arm0.data.copy(); arm.name = f"TMP_{arm0.name}_{clip}"; sc.collection.objects.link(arm)
    arm.animation_data_clear(); arm.location = (0, 0, 0); arm.rotation_euler = (0, 0, 0)
    try:
        return _retarget(arm, clip, alt)
    finally:
        d = arm.data; bpy.data.objects.remove(arm, do_unlink=True)
        try: bpy.data.armatures.remove(d)
        except Exception: pass

def _retarget(arm, clip, alt):
    c = IDX['clips'][clip]; mapa_src = IDX['perfiles_huesos'][c['perfil']]
    bpy.ops.import_anim.bvh(filepath=os.path.join(f"{MOT}/assets", c['archivo']), use_fps_scale=True, update_scene_duration=False)
    S = bpy.context.object; S.name = f"SRC_{clip}"
    fr0, fr1 = S.animation_data.action.frame_range
    if c.get('rango_s'): fr1 = min(fr1, fr0 + c['rango_s'][1] * FPS); fr0 = fr0 + c['rango_s'][0] * FPS
    S.data.pose_position = 'REST'; bpy.context.view_layer.update()
    hz = [(S.matrix_world @ b.tail_local).z for b in S.data.bones]; lz = [(S.matrix_world @ b.head_local).z for b in S.data.bones]
    span = max(hz) - min(lz); k = alt / span if span > 1e-6 else 1.0; S.scale = (k, k, k); S.data.pose_position = 'POSE'; bpy.context.view_layer.update()
    names = {b.name for b in S.data.bones}; tb = {b.name for b in arm.data.bones}
    MAP = {a: b for a, b in mapa_src.items() if a in names and b in tb}
    if len(MAP) < 10: bpy.data.objects.remove(S, do_unlink=True); return None, f"mapa insuficiente {len(MAP)}"
    INVm = {v: k2 for k2, v in MAP.items()}
    ALIGN = [v for v in MAP.values() if v.split('_')[0] in ('femur', 'tibia', 'brazo', 'antebrazo')]
    def src_dir(n):
        b = S.data.bones[n]; mw = S.matrix_world; return ((mw @ b.tail_local) - (mw @ b.head_local)).normalized()
    activar(arm); ctx = arm.retargeting_context; ctx.mappings.clear(); ctx.selected_source = S
    for a2, b2 in MAP.items():
        m = ctx.mappings.add(); m.source = a2; m.target = b2
    alignment.enter_alignment_mode(ctx)
    S.data.pose_position = 'REST'; bpy.context.view_layer.update()
    for b in arm.data.bones:                                       # auto_align (igual que en el lab aprobado)
        if b.name not in ALIGN: continue
        pb = arm.pose.bones[b.name]; bpy.context.view_layer.update()
        Mw = arm.matrix_world @ pb.matrix; q = Mw.col[1].xyz.normalized().rotation_difference(src_dir(INVm[b.name]))
        h = pb.matrix.translation.copy(); pb.matrix = Matrix.Translation(h) @ (q.to_matrix() @ pb.matrix.to_3x3()).to_4x4()
    bpy.context.view_layer.update(); S.data.pose_position = 'POSE'
    alignment.store_alignments(ctx); alignment.leave_alignment_mode(ctx)
    activar(arm); baking.transfer_anim(ctx); ctx.setting_disable_drivers = True; drivers.update_drivers(ctx)
    try: bpy.ops.object.mode_set(mode='OBJECT')
    except Exception: pass
    act = arm.animation_data.action
    sc.frame_set(int(fr0)); bpy.context.view_layer.update()
    out = {"basis": [], "cad": [], "fL": [], "fR": [], "pL": [], "pR": []}
    bones = [b.name for b in arm.pose.bones]
    for fr in range(int(fr0), int(fr1) + 1):
        sc.frame_set(fr)
        out['basis'].append({n: (arm.pose.bones[n].matrix_basis.to_translation(), arm.pose.bones[n].matrix_basis.to_quaternion()) for n in bones})
        P = arm.pose.bones
        out['cad'].append(P['cadera'].head.copy()); out['fL'].append(P['femur_L'].head.copy()); out['fR'].append(P['femur_R'].head.copy())
        out['pL'].append(min(P['pie_L'].head, P['pie_L'].tail, key=lambda v: v.z).copy()); out['pR'].append(min(P['pie_R'].head, P['pie_R'].tail, key=lambda v: v.z).copy())
    arm.animation_data.action = None
    try: bpy.data.actions.remove(act)
    except Exception: pass
    for a3 in [x for x in bpy.data.actions if x.name.startswith('SRC_') or x.name.startswith(S.name)]:
        try: bpy.data.actions.remove(a3)
        except Exception: pass
    bpy.data.objects.remove(S, do_unlink=True)
    return out, {"mapa": len(MAP), "cuadros": len(out['basis']), "fuente": c['fuente'], "archivo": c['archivo'], "licencia": c['licencia'], "k_escala": k}

def ang(v): return math.degrees(math.atan2(v.y, v.x))
def wrap(a): return (a + 180) % 360 - 180

def preparar_clip(arm, S, tipo, frente_deg):
    """Alinea el clip para que mire como el molde en reposo (-Y), mide ciclo (período, zancada) y quita el avance de la cadera."""
    n = len(S['basis']); Z = Vector((0, 0, 1))
    fac = [ang(Z.cross(S['fR'][i] - S['fL'][i])) for i in range(n)]
    sx = sum(math.cos(math.radians(a)) for a in fac); sy = sum(math.sin(math.radians(a)) for a in fac)
    a_clip = math.degrees(math.atan2(sy, sx)); rot = wrap(frente_deg - a_clip)
    Rz = Matrix.Rotation(math.radians(rot), 4, 'Z'); Rz3 = Rz.to_3x3()
    cad = [Rz3 @ v for v in S['cad']]; pL = [Rz3 @ v for v in S['pL']]; pR = [Rz3 @ v for v in S['pR']]
    fw = Vector((math.cos(math.radians(frente_deg)), math.sin(math.radians(frente_deg)), 0))
    s = [v.dot(fw) for v in cad]
    info = {"giro_alineacion_deg": round(rot, 1), "cuadros": n}
    i0, P = 0, n
    if tipo in ('caminar', 'trotar'):
        sp = [(s[min(n - 1, i + 1)] - s[max(0, i - 1)]) * FPS / 2 for i in range(n)]
        top = sorted(sp)[int(n * 0.8)]; ok = [x > 0.6 * top for x in sp]
        best = None
        feat = lambda i: [c for v in ((pL[i] - cad[i]), (pR[i] - cad[i])) for c in v]
        for Pc in (range(int(0.7 * FPS), int(1.6 * FPS) + 1) if tipo == 'caminar' else range(int(0.4 * FPS), int(1.0 * FPS) + 1)):
            for i in range(0, n - Pc):
                if not (ok[i] and ok[i + Pc]): continue
                e = sum((a - b) ** 2 for a, b in zip(feat(i), feat(i + Pc)))
                if best is None or e < best[0]: best = (e, i, Pc)
        if best is None: return None, {"error": "sin ciclo de caminata en el clip"}
        _, i0, P = best
        D = s[i0 + P] - s[i0]; info.update(ciclo_inicio=i0, periodo_cuadros=P, zancada_ciclo_m=round(D, 4), vel_clip_m_s=round(D / P * FPS, 3), error_cierre=round(best[0], 6))
    else:
        # reposo: se saltan cuadros iniciales de referencia del BVH (CMU suele traer una pose T/rara en el cuadro 0)
        feat = lambda i: [c for v in ((pL[i] - cad[i]), (pR[i] - cad[i])) for c in v]
        dif = [sum((a - b) ** 2 for a, b in zip(feat(i), feat(i + 1))) ** 0.5 for i in range(n - 1)]
        med = sorted(dif)[len(dif) // 2] if dif else 0
        i0 = 0
        while i0 < min(6, n - 3) and dif[i0] > max(5 * med, 0.01): i0 += 1
        D = 0.0; P = n - i0; info.update(periodo_cuadros=P, cuadros_saltados_inicio=i0)
    L = arm.data.bones['cadera'].matrix_local.to_3x3(); Li = L.inverted(); rest_head = arm.data.bones['cadera'].head_local
    rng = range(i0, i0 + P)
    lat = [cad[i] - fw * cad[i].dot(fw) for i in rng]; latm = sum(lat, Vector()) / max(1, len(lat)); latm.z = 0
    poses = []
    for k in range(P + (1 if tipo in ('caminar', 'trotar') else 0)):
        i = i0 + k
        B = dict(S['basis'][i]); t, q = B['cadera']
        # rotación de alineación aplicada a la cadera en espacio armature: basis' = L^-1 Rz L basis
        q2 = (Li @ Rz3 @ L).to_quaternion() @ q
        head = Rz3 @ S['cad'][i]
        prog = (s[i0] + D * k / P) if tipo in ('caminar', 'trotar') else sum(s[i0:]) / max(1, n - i0)
        dev = head - fw * prog - latm                                     # quita el avance y el desvío lateral del clip (in place), conserva vaivén
        t2 = Li @ (Vector((rest_head.x + dev.x, rest_head.y + dev.y, head.z)) - rest_head)
        B['cadera'] = (t2, q2); poses.append(B)
    return {"poses": poses, "P": P, "D": D}, info

KIM_PASO = 15   # 0.5 s a 30 fps = relleno de pie y paso de restricciones de kimodo_pedidos
BORDE_K = 12   # cuadros de transición reposo CMU <-> pose de pie de Kimodo, fuera del tramo
# [t518 10-nov-2026] Kimodo NO decide dónde está el personaje: en tramos girar/quieto la raíz queda CLAVADA en el plan A*+RVO2
# (que ya no pisa muebles); en caminar se permite como mucho KIM_DESVIO_MAX_M de diferencia con el plan. Si la raíz de Kimodo
# se va más de KIM_DERIVA_RECHAZO_M (caso real: personajes 1,5–2,9 m fuera del cuarto), el tramo se RECHAZA y se usan los clips.
KIM_DESVIO_MAX_M = 0.10
KIM_DERIVA_RECHAZO_M = 0.60
RAMPA = 12   # 0.5 s: transición quieto<->caminar sin resbale de pies

def slerp_pose(A1, B1, u):
    out = {}
    for n in A1:
        ta, qa = A1[n]; tb, qb = B1.get(n, A1[n])
        if qa.dot(qb) < 0: qb = -qb
        out[n] = (ta.lerp(tb, u), qa.slerp(qb, u))
    return out

def muestra(C, x):
    """pose del clip en fase continua x (en cuadros, con vuelta)."""
    P = C['P']; x = x % P; i = int(x); u = x - i
    return slerp_pose(C['poses'][i], C['poses'][(i + 1) % len(C['poses'])], u)

QUIETO_LENTO = 2.5    # bailecito (t1013u): el reposo era 1 s de CMU 13_01 en ida y vuelta (vaivén de cadera ~7 cm a 0.5-1 Hz, con tirón al dar la vuelta)
QUIETO_AMORT = 0.35   # -> ida y vuelta 2.5x más lenta y con frenado suave en los extremos (coseno), y amplitud al 35 % alrededor de la pose media
def quieto_en(C, f):
    """reposo calmo: ida y vuelta lenta y suave sobre el clip de pie, amortiguada hacia su pose central (sin tirones)."""
    P = C['P']
    if P <= 1: return C['poses'][0]
    x = (P - 1) * 0.5 * (1 - math.cos(math.pi * f / (QUIETO_LENTO * (P - 1))))
    i = min(P - 2, int(x)); u = x - i
    pose = slerp_pose(C['poses'][i], C['poses'][i + 1], u)
    return slerp_pose(C['poses'][(P - 1) // 2], pose, QUIETO_AMORT)

def escribir_fcurves(obj, datos, interp='LINEAR'):
    """datos: {(data_path, index): [valores por cuadro 1..N]} -> fcurves (layered actions de Blender 5)."""
    ad = obj.animation_data_create()
    act = ad.action or bpy.data.actions.new(f"MOTOR|{obj.name}"); ad.action = act
    for (dp, ix), vals in datos.items():
        fc = act.fcurve_ensure_for_datablock(obj, dp, index=ix)
        fc.keyframe_points.add(len(vals)); co = []
        for f, v in enumerate(vals, start=1): co += [f, v]
        fc.keyframe_points.foreach_set('co', co)
        for k in fc.keyframe_points: k.interpolation = interp
        fc.update()
    return act

OBJ_POR_NOMBRE = {o.name: o for o in bpy.data.objects}
def punto_mirada(nombre):
    if not nombre: return None
    o = OBJ_POR_NOMBRE.get(nombre) or next((x for x in bpy.data.objects if x.name.startswith(nombre)), None)
    if o is None:
        base = re.sub(r'__.*$', '', nombre); o = next((x for x in bpy.data.objects if x.name.startswith(base)), None)
    if o is None: return None
    if o.type == 'ARMATURE' and 'cabeza' in o.pose.bones: return o.matrix_world @ o.pose.bones['cabeza'].head
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]; return sum(pts, Vector()) / 8

eje_frente_cache = {}
def eje_frente_local(arm, bname):
    """eje local del hueso que en reposo apunta al frente del molde (-Y)."""
    k = (arm.name, bname)
    if k not in eje_frente_cache:
        M3 = arm.data.bones[bname].matrix_local.to_3x3()
        cands = [Vector(v) for v in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0), (0, -1, 0))]
        eje_frente_cache[k] = max(cands, key=lambda v: (M3 @ v).dot(Vector((0, -1, 0))))
    return eje_frente_cache[k]

def clip_desde_reposo(arm, cuadros=None):
    """Clip base del PROPIO esqueleto en pose de reposo (matrix_basis identidad).
    Universal: cualquier plantilla sin clip retargeteable (animal, huesos no mapeables a CMU,
    retarget incompleto) obtiene quieto/caminar válidos. caminar con D=0: el personaje se
    desplaza por la ruta del plan sin ciclo de zancada (no se inventa mocap ni se frena con STOP).
    No hay nombres de personaje, canal ni capítulo en este camino."""
    cuadros = cuadros or max(1, int(round(FPS)))
    bones = [b.name for b in arm.pose.bones]
    poses = [{n: (Vector(), Quaternion()) for n in bones} for _ in range(cuadros)]
    info = {"fuente": "reposo_del_molde", "cuadros": cuadros, "periodo_cuadros": cuadros, "zancada_ciclo_m": 0.0}
    return {"poses": poses, "P": cuadros, "D": 0.0}, info

def animar_personaje(pid, D):
    arm = D['arm']; P = M['personajes'][pid]; plan = PL['personajes'].get(pid); info = D['info']
    if plan is None: info['movimiento'] = 'sin plan'; return
    bones = [b.name for b in arm.pose.bones]
    acoplado = P.get('acople') is not None
    humano = all(b in bones for b in ('cadera', 'femur_L', 'femur_R', 'pie_L', 'pie_R'))
    clips = {}
    if humano and not acoplado:
        fr = info['frente_rest_deg']
        for nombre, tipo in (('quieto', 'quieto'), ('caminar', 'caminar')):
            S, inf = retarget(arm, nombre, D['alt'])
            if S is None: info.setdefault('clips', {})[nombre] = {"error": inf}; continue
            C, ci = preparar_clip(arm, S, tipo, fr)
            info.setdefault('clips', {})[nombre] = dict(inf, **ci); log('clip', pid, nombre, json.dumps(info['clips'][nombre], default=str)[:300])
            if C: clips[nombre] = C
    # trote: si el 01 pide más de 1.6x la velocidad de la caminata del molde en un tramo, ese tramo usa el clip de trote
    trote = [False] * (N + 2)
    if 'caminar' in clips and not acoplado:
        vc = clips['caminar']['D'] / clips['caminar']['P'] * FPS if clips['caminar']['P'] else 0
        f = 1; tramos = []
        while f <= N:
            if plan[f - 1][4] == 'caminar':
                g = f
                while g < N and plan[g][4] == 'caminar': g += 1
                v = (plan[g - 1][3] - plan[f - 1][3]) / max(1, g - f) * FPS
                if vc > 1e-4 and v > 1.6 * vc: tramos.append((f, g, round(v, 3), round(v / vc, 2)))
                f = g + 1
            else: f += 1
        if tramos:
            S, inf = retarget(arm, 'trotar', D['alt'])
            Ct, ci = preparar_clip(arm, S, 'trotar', info['frente_rest_deg']) if S is not None else (None, {"error": inf})
            info.setdefault('clips', {})['trotar'] = dict(inf if isinstance(inf, dict) else {"error": inf}, **ci, tramos=tramos)
            log('clip', pid, 'trotar', json.dumps(info['clips']['trotar'], default=str)[:300])
            if Ct:
                clips['trotar'] = Ct
                for f0, g0, _, _ in tramos:
                    for k in range(f0, g0 + 1): trote[k] = True
    if acoplado:
        info['movimiento'] = 'acoplado (reposo del molde, hijo del hueso del portador)'; return
    if 'quieto' not in clips or 'caminar' not in clips:
        C0, ci0 = clip_desde_reposo(arm)
        for nombre in ('quieto', 'caminar'):
            if nombre not in clips:
                clips[nombre] = C0
                info.setdefault('clips', {})[nombre] = dict(ci0, motivo='plantilla sin clip retargeteable; se usa reposo del propio esqueleto')
        motivo = 'esqueleto no humano (huesos distintos al mapa CMU/Mwni)' if not humano else 'retarget de quieto/caminar incompleto'
        aviso = f"{pid}: plantilla sin clip retargeteable ({motivo}): se usa reposo del propio esqueleto como clip base (no STOP)"
        if aviso not in R['avisos']:
            R['avisos'].append(aviso)
        info['movimiento'] = 'reposo_del_molde+plan'
    # ---- Kimodo: cada tramo de movimiento (caminar/girar/correr) viene de Kimodo GPU; Mwni lo pasa al molde
    import numpy as np
    kimf = {}; kborde = {}; kim_contact = {'pie_L': [False] * N, 'pie_R': [False] * N}; kinfo = []
    if clips and not acoplado and humano:
        L3 = arm.data.bones['cadera'].matrix_local.to_3x3(); L3i = L3.inverted(); rest_h = arm.data.bones['cadera'].head_local
        fr_rad = math.radians(info['frente_rest_deg'])
        for kp in KIMP.get(pid, []):
            nm = kp['nombre']; IDX['clips'][nm] = {"fuente": "Kimodo-SOMA-RP-v1.2", "archivo": f"{COR}/kimodo/{nm}.bvh", "perfil": "KIMODO_SOMA", "licencia": "NVIDIA Open Model License"}
            S, inf = retarget(arm, nm, D['alt'])
            if S is None: kinfo.append({"tramo": nm, "error": inf}); continue
            z = np.load(f"{COR}/kimodo/{nm}.npz"); root = z['smooth_root_pos']; hd = z['global_root_heading']; fc = z['foot_contacts']; nz = len(root)
            kk = inf['k_escala'] * 100.0                      # metros Kimodo -> unidades del armature (BVH en cm, escalado Mwni)
            nb = len(S['basis']); f0, f1 = kp['f0'], kp['f1']
            # nivel: la cadera de pie de Kimodo (cuadro 0, de pie) se iguala a la del clip quieto del mismo molde -> mismo piso que el resto
            tq = quieto_en(clips['quieto'], f0)['cadera'][0]; dz = (L3 @ Vector(tq)).z - (S['cad'][0].z - rest_h.z)
            # Kimodo arranca siempre con rumbo canónico (~-90°) y gira hasta la restricción en los primeros 0.5 s, y tras la última
            # restricción deriva: en los relleno de pie (0.5 s a cada lado) se usa la pose de Kimodo congelada en la 1.ª / última restricción
            jA = min(nz - 1, KIM_PASO); jB = max(jA, min(nz - 1, int(kp.get('n30', nz)) - 1 - KIM_PASO))
            # [t518] deriva de la raíz Kimodo vs el plan, ANTES de usar el tramo
            der = 0.0
            for f in range(f0, f1 + 1):
                jr = int(round((f - f0) * 30.0 / FPS)); j = min(jB, max(jA, jr))
                der = max(der, math.hypot(kp['p0'][0] + root[j][0] * kk - plan[f - 1][0], kp['p0'][1] - root[j][2] * kk - plan[f - 1][1]))
            if der > KIM_DERIVA_RECHAZO_M:
                kinfo.append({"tramo": nm, "rechazado": f"KIMODO_DERIVA {der:.2f} m > {KIM_DERIVA_RECHAZO_M} m: se usan clips + plan"})
                R['avisos'].append(f"{pid}: tramo Kimodo {nm} rechazado (raíz se fue {der:.2f} m del plan)"); continue
            clavar = kp.get('tipo') in ('girar', 'quieto')
            for f in range(f0, f1 + 1):
                jr = int(round((f - f0) * 30.0 / FPS)); j = min(jB, max(jA, jr))
                i = min(nb - 1, int(round(j * FPS / 30.0)))
                rx, ry = root[j][0] * kk, -root[j][2] * kk
                yk = math.atan2(-hd[j][0], hd[j][1]); dl = yk - fr_rad
                Rm = Matrix.Rotation(-dl, 3, 'Z')
                B = dict(S['basis'][i]); t, q = B['cadera']; head = S['cad'][i]
                dev = Rm @ (head - Vector((rx, ry, 0.0)))
                B['cadera'] = (L3i @ (Vector((rest_h.x + dev.x, rest_h.y + dev.y, head.z + dz)) - rest_h), (L3i @ Rm @ L3).to_quaternion() @ q)
                u = 1.0   # dentro del tramo: Kimodo puro (empieza y termina con sus propios pies plantados)
                kx_, ky_ = kp['p0'][0] + rx, kp['p0'][1] + ry; px_, py_ = plan[f - 1][0], plan[f - 1][1]
                if clavar: kx_, ky_ = px_, py_                      # [t518] girar/quieto: en su marca, sin deslizar
                else:
                    dd_ = math.hypot(kx_ - px_, ky_ - py_)
                    if dd_ > KIM_DESVIO_MAX_M: kx_, ky_ = px_ + (kx_ - px_) * KIM_DESVIO_MAX_M / dd_, py_ + (ky_ - py_) * KIM_DESVIO_MAX_M / dd_
                kimf[f] = (B, kx_, ky_, dl, u)
                ch = fc[j]; nh = len(ch) // 2
                kim_contact['pie_L'][f - 1] = bool(any(ch[:nh])); kim_contact['pie_R'][f - 1] = bool(any(ch[nh:]))
            # bordes FUERA del tramo: 6 cuadros del reposo CMU a la pose de pie congelada de Kimodo (cuadro f0 / f1), en el sitio y rumbo de Kimodo,
            # con ambos pies marcados en apoyo para que el foot-lock aprobado los mantenga fijos durante la mezcla
            # largo del borde: 6 cuadros, o más si hay que girar (el rumbo del plan fuera del tramo vs el de Kimodo) a ≤ 45°/s como el planificador
            for bf, fk in (('in', f0), ('out', f1)):
                fp = max(1, f0 - 1) if bf == 'in' else min(N, f1 + 1)
                dyaw = abs((math.degrees(kimf[fk][3]) - (plan[fp - 1][2] - info['frente_rest_deg']) + 180) % 360 - 180)
                nb_ = max(BORDE_K, int(math.ceil(dyaw / 45.0 * FPS)))
                rng = range(max(1, f0 - nb_), f0) if bf == 'in' else range(f1 + 1, min(N, f1 + nb_) + 1)
                for f in rng:
                    if f in kimf: continue
                    w = (f - (f0 - nb_ - 1)) / (nb_ + 1.0) if bf == 'in' else ((f1 + nb_ + 1) - f) / (nb_ + 1.0)
                    w = w * w * (3 - 2 * w)
                    if f not in kborde or w > kborde[f][4]: kborde[f] = (kimf[fk][0], kimf[fk][1], kimf[fk][2], kimf[fk][3], w)
            kinfo.append({"tramo": nm, "cuadros": [f0, f1], "prompt": kp['prompt'], "tipo": kp['tipo'], "vel_plan_m_s": kp['vel_plan_m_s'],
                          "vel_soma_m_s": kp['vel_soma_m_s'], "mapa": inf['mapa'], "cuadros_kimodo": nz, "nivel_cadera_dz": round(dz, 4), "kimodo_usado_j": [jA, jB],
                          "deriva_raiz_max_m": round(der, 3), "raiz": "clavada al plan" if clavar else f"plan ± {KIM_DESVIO_MAX_M} m"})
        if kinfo: info['kimodo'] = kinfo; log('kimodo', pid, json.dumps(kinfo, default=str)[:300])
    # gestos por cuadro
    gest = [None] * (N + 1)
    for g in P.get('gestos', []):
        for f in range(max(1, g['f0']), min(N, g['f1']) + 1): gest[f] = g
    # ---- composición por cuadro
    curv = {}; loc = []; rotz = []; tips = {'pie_L': [], 'pie_R': []}; floor = []
    def put(dp, ix, f, v): curv.setdefault((dp, ix), [0.0] * N)[f - 1] = v
    w_walk = 0.0; fase = 0.0; prev_d = 0.0; prev_r = None; prevq = {}
    for f in range(1, N + 1):
        x, y, rumbo, dist, modo = plan[f - 1]
        yaw = math.radians(rumbo - info['frente_rest_deg'])
        kk_ = kimf.get(f) or kborde.get(f)
        if kk_:
            _B, kx, ky, kdl, ku = kk_
            while kdl - yaw > math.pi: kdl -= 2 * math.pi
            while kdl - yaw < -math.pi: kdl += 2 * math.pi
            x, y, yaw = x + (kx - x) * ku, y + (ky - y) * ku, yaw + (kdl - yaw) * ku
        if prev_r is not None:
            while yaw - prev_r > math.pi: yaw -= 2 * math.pi
            while yaw - prev_r < -math.pi: yaw += 2 * math.pi
        dd = dist - prev_d; dr = abs(yaw - prev_r) if prev_r is not None else 0.0; prev_d = dist; prev_r = yaw
        tgt = 1.0 if modo in ('caminar', 'girar') else 0.0
        w_walk += max(-1 / RAMPA, min(1 / RAMPA, tgt - w_walk))   # rampa quieto<->caminar (cuadros)
        if clips:
            Cw = clips['trotar'] if (trote[f] and 'trotar' in clips) else clips['caminar']; Cq = clips['quieto']
            if modo == 'caminar': fase += dd / Cw['D'] * Cw['P'] if Cw['D'] > 1e-4 else 0
            elif modo == 'girar': fase += (dr * 0.10) / Cw['D'] * Cw['P'] if Cw['D'] > 1e-4 else 0
            pose = slerp_pose(quieto_en(Cq, f), muestra(Cw, fase), w_walk * w_walk * (3 - 2 * w_walk))
            if f in kimf or f in kborde:
                _B, _, _, _, ku = kimf.get(f) or kborde[f]
                pose = slerp_pose(quieto_en(Cq, f), {n: _B[n] for n in pose if n in _B}, ku) if ku < 1.0 else {n: _B[n] for n in pose if n in _B}
        else:
            pose = {n: (Vector(), Quaternion()) for n in bones}
        g = gest[f]
        if g and g['gesto'] == 'hablar':
            t = f / FPS; a = math.radians(3.5) * math.sin(2 * math.pi * 2.1 * t) * (0.6 + 0.4 * math.sin(2 * math.pi * 0.37 * t))
            for bn, k in (('cabeza', 1.0), ('cuello', 0.5)):
                if bn in pose:
                    ax = eje_frente_local(arm, bn).cross(Vector((0, 1, 0))); ax = ax if ax.length > 0.1 else Vector((1, 0, 0))
                    t0_, q0 = pose[bn]; pose[bn] = (t0_, q0 @ Quaternion(ax.normalized(), a * k))
        for n, (t, q) in pose.items():
            if n in prevq and prevq[n].dot(q) < 0: q = -q
            prevq[n] = q
            pb = arm.pose.bones[n]; pb.rotation_mode = 'QUATERNION'
            for i in range(4): put(f'pose.bones["{n}"].rotation_quaternion', i, f, q[i])
            if n == 'cadera':
                for i in range(3): put(f'pose.bones["{n}"].location', i, f, t[i])
        z = piso_z(x, y)
        _zs, _con = SOPORTES.z(pid, f, x, y) if SOPORTES else (None, None)   # [argon_v2] sentado_en / acostado_en: apoyo en el mueble
        if _zs is not None: z = _zs
        floor.append(z)
        loc.append(Vector((x, y, z))); rotz.append(yaw)
    # escribir capa base y medir pies sobre el piso real para el foot-lock aprobado
    for i in range(3): curv[('location', i)] = [v[i] for v in loc]
    curv[('rotation_euler', 2)] = rotz
    arm.rotation_mode = 'XYZ'
    escribir_fcurves(arm, curv)
    vis0 = P.get('visible_desde', 1)
    # mirar / señalar (exactos, con la pose de los padres evaluada): se corrigen sobre la capa base
    corr = {}; lado_gesto = {}
    if not acoplado and any(gest[1:]):
        for f in range(1, N + 1):
            g = gest[f]
            if not g or g['gesto'] not in ('mirar', 'senalar'): continue
            tgt = punto_mirada(g.get('mirada') or g.get('objeto') or '')
            if tgt is None: continue
            sc.frame_set(f); mw = arm.matrix_world; mwi = mw.inverted()
            # rampa de 5 cuadros al entrar/salir
            u = min(1.0, (f - g['f0'] + 1) / 5, (g['f1'] - f + 1) / 5)
            if 'cabeza' in arm.pose.bones:
                pb = arm.pose.bones['cabeza']; ax = eje_frente_local(arm, 'cabeza')
                cur = (pb.matrix.to_3x3() @ ax).normalized(); want = (mwi @ tgt - pb.head).normalized()
                qd = cur.rotation_difference(want); axis, angd = qd.to_axis_angle(); angd = min(angd, math.radians(55)) * u
                Mn = Matrix.Translation(pb.head) @ (Quaternion(axis, angd).to_matrix() @ pb.matrix.to_3x3()).to_4x4()
                pb.matrix = Mn; corr.setdefault('cabeza', {})[f] = pb.matrix_basis.to_quaternion()
            if g['gesto'] == 'senalar':
                kg = (g['f0'], g['f1'], g['gesto'])
                if kg not in lado_gesto: lado_gesto[kg] = 'R' if (mwi @ tgt).x < 0 else 'L'   # el brazo se elige 1 vez por gesto (sin saltar de brazo)
                lado = lado_gesto[kg]
                bn = f'brazo_{lado}'
                if bn in arm.pose.bones:
                    bpy.context.view_layer.update(); pb = arm.pose.bones[bn]
                    cur = (pb.tail - pb.head).normalized(); want = (mwi @ tgt - pb.head).normalized()
                    qd = cur.rotation_difference(want); axis, angd = qd.to_axis_angle(); angd *= u
                    pb.matrix = Matrix.Translation(pb.head) @ (Quaternion(axis, angd).to_matrix() @ pb.matrix.to_3x3()).to_4x4()
                    corr.setdefault(bn, {})[f] = pb.matrix_basis.to_quaternion()
                    ab = f'antebrazo_{lado}'
                    if ab in arm.pose.bones:
                        q0 = arm.pose.bones[ab].matrix_basis.to_quaternion(); corr.setdefault(ab, {})[f] = q0.slerp(Quaternion(), 0.8 * u)
        act = arm.animation_data.action
        for bn, fs in corr.items():
            for i in range(4):
                fc = act.fcurve_ensure_for_datablock(arm, f'pose.bones["{bn}"].rotation_quaternion', index=i)
                vals = [0.0] * (2 * len(fc.keyframe_points)); fc.keyframe_points.foreach_get('co', vals)
                for f, q in fs.items():
                    vals[2 * (f - 1) + 1] = q[i]
                fc.keyframe_points.foreach_set('co', vals); fc.update()
        info['gestos_mirar_senalar_cuadros'] = {k: len(v) for k, v in corr.items()}
    # foot-lock aprobado (raíz plantada) sobre el piso real — solo si el esqueleto trae pie_L/pie_R
    # (no se inventa un mapeo de patas/garras; no se retoca el algoritmo aprobado)
    pies_ok = all(p in arm.pose.bones for p in ('pie_L', 'pie_R'))
    if clips and pies_ok:
        for f in range(1, N + 1):
            sc.frame_set(f); mw = arm.matrix_world
            for p in ('pie_L', 'pie_R'):
                pb = arm.pose.bones[p]; h = mw @ pb.head; t = mw @ pb.tail; tip = h if h.z <= t.z else t
                tips[p].append(Vector((tip.x, tip.y, tip.z - floor[f - 1])))
        delta, w, primary, finfo = PIES.strong_foot_lock_plan(tips, N, kim=(kim_contact if kimf else None), fps=FPS)   # contactos Kimodo como en el lab aprobado
        act = arm.animation_data.action
        for i in range(2):
            fc = act.fcurve_ensure_for_datablock(arm, 'location', index=i)
            vals = [0.0] * (2 * N); fc.keyframe_points.foreach_get('co', vals)
            for f in range(N): vals[2 * f + 1] += delta[f][i]
            fc.keyframe_points.foreach_set('co', vals); fc.update()
        # suelo: la suela más baja del cuadro toca el piso real (sin hundirse)
        fcz = act.fcurve_ensure_for_datablock(arm, 'location', index=2)
        vals = [0.0] * (2 * N); fcz.keyframe_points.foreach_get('co', vals)
        zmin_rel = [min(tips['pie_L'][f].z, tips['pie_R'][f].z) for f in range(N)]
        # quitar el offset del clip (mediana de la suela en apoyo) sin perseguir cada paso
        base_off = sorted(zmin_rel)[len(zmin_rel) // 20]
        for f in range(N): vals[2 * f + 1] -= base_off
        fcz.keyframe_points.foreach_set('co', vals); fcz.update()
        finfo['offset_suela_m'] = round(base_off, 4)
        info['foot_lock'] = finfo
    elif clips and not pies_ok:
        info['foot_lock'] = {"omitido": "esqueleto sin pie_L/pie_R; no se aplica el foot-lock aprobado"}
    info['visible_desde_cuadro'] = vis0
    info['movimiento'] = info.get('movimiento', 'mocap+plan+foot-lock' if clips else ('acoplado' if acoplado else 'reposo'))

def visibilidad(objs, f_on, f_off=None):
    for o in objs:
        o.hide_render = f_on > 1; o.keyframe_insert('hide_render', frame=1)
        if f_on > 1: o.hide_render = False; o.keyframe_insert('hide_render', frame=f_on)
        if f_off: o.hide_render = True; o.keyframe_insert('hide_render', frame=f_off)
        o.hide_viewport = False
        ad = o.animation_data
        if ad and ad.action:
            for L in ad.action.layers:
                for s in L.strips:
                    cb = s.channelbag(ad.action_slot)
                    if cb:
                        for fc in cb.fcurves:
                            if fc.data_path == 'hide_render':
                                for k in fc.keyframe_points: k.interpolation = 'CONSTANT'

try:
    SOPORTES = RB.Soportes(sc, bpy.context.evaluated_depsgraph_get(), M.get('relaciones') or PL.get('relaciones'), FPS)
    R['pasos']['3_relaciones'] = {"relaciones": M.get('relaciones') or [], "soportes": {k: [x[5] for x in v] for k, v in SOPORTES.items.items()},
                                  "fisicas_plan": PL.get('relaciones_fisicas'), "anclados_plan": PL.get('anclados')}
except Exception as _ex:
    SOPORTES = None; R['avisos'].append(f"relaciones: {_ex!r}")
t_mov = time.time()
orden = sorted(PJ, key=lambda k: M['personajes'].get(k, {}).get('acople') is not None)   # portadores antes que acoplados
for pid in orden:
    animar_personaje(pid, PJ[pid]); log('animado', pid, PJ[pid]['info'].get('movimiento'))
# acople: hijo del hueso del portador (cita del 01). Se coloca sobre la superficie del hombro (raycast a la malla del portador).
for pid in orden:
    ac = M['personajes'].get(pid, {}).get('acople')
    if not ac: continue
    arm = PJ[pid]['arm']; host = PJ.get(ac['host'])
    # [argon_v2] hueso GENÉRICO: nombre de la fábrica -> sinónimos/sufijos de lado -> posición en el molde (cualquier rig)
    _hp = ac.get('hueso') or ''
    _parte = ac.get('parte') or re.sub(r'_[LR]$', '', _hp or 'hombro')
    _lado = ac.get('lado') or (_hp[-1] if _hp[-2:] in ('_L', '_R') else None)
    hn, hmet = RB.hueso(host['arm'], _parte, _lado) if host is not None else (None, 'sin portador')
    if host is None or hn is None:
        R['avisos'].append(f"{pid}: acople a {ac} imposible ({hmet}) -> pedir_a_fabrica"); continue
    H = host['arm']; f0 = M['personajes'][pid].get('visible_desde', 1); sc.frame_set(f0)
    bpy.context.view_layer.update(); dgh = bpy.context.evaluated_depsgraph_get()
    P_ap, pmet = RB.punto_apoyo(H, hn, dgh)
    yaw = H.matrix_world.to_euler().z
    Mw = Matrix.Translation(P_ap) @ Matrix.Rotation(yaw, 4, 'Z')
    arm.parent = H; arm.parent_type = 'BONE'; arm.parent_bone = hn; bpy.context.view_layer.update()
    arm.matrix_world = Mw; bpy.context.view_layer.update()
    PJ[pid]['info']['acople'] = {"host": ac['host'], "hueso": hn, "hueso_metodo": hmet, "pedido": ac.get('hueso'), "relacion": ac.get('relacion'),
                                 "superficie_z": round(P_ap.z, 4), "apoyo": pmet, "cita_01": ac.get('cita'), "metodo": "parent BONE (sigue al portador)"}
    log('acople', pid, '->', ac['host'], hn, hmet)
for pid, D in PJ.items():
    vis0 = M['personajes'].get(pid, {}).get('visible_desde', 1)
    visibilidad([c for c in D['arm'].children_recursive if c.type == 'MESH'], vis0)

# ---------------------------------------------------------------- 3b objetos y props (Ricardo t1027u): append de la biblioteca, hijo del hueso del portador
def _bvh_de(arm, dg):
    V = []; F = []
    for o in [c for c in arm.children_recursive if c.type == 'MESH']:
        oe = o.evaluated_get(dg); me = oe.to_mesh(); mw = oe.matrix_world; b = len(V)
        V += [mw @ v.co for v in me.vertices]; F += [tuple(b + i for i in p.vertices) for p in me.polygons]; oe.to_mesh_clear()
    return BVHTree.FromPolygons(V, F) if F else None

t_obj = time.time(); OBJ = {"cargados": [], "omitidos": []}
for ob in E.get('objetos', []):
    ped = ob['pedido']; port = ob.get('portador') if ob.get('portador') in PJ else None
    en_set = [o for o in bpy.data.objects if o.type == 'MESH' and not o.get('prop_motor') and (o.name == ped or re.match(re.escape(ped) + r'[._#]', o.name))]
    if en_set and (not port or ob.get('subclase') != 'portado'):
        OBJ['omitidos'].append({"pedido": ped, "id": ob['id'], "motivo": f"ya está en el escenario ({en_set[0].name})"}); continue
    if not port:
        OBJ['omitidos'].append({"pedido": ped, "id": ob['id'], "motivo": "sin portador y sin lugar en el escenario -> pedir_a_fabrica/escenario"}); continue
    with bpy.data.libraries.load(f"{COR}/{ob['blend']}", link=False) as (src, dst):
        dst.objects = list(src.objects)
    mallas = [o for o in dst.objects if o and o.type == 'MESH']
    for o in dst.objects:
        if o is not None and o.type != 'MESH': bpy.data.objects.remove(o, do_unlink=True)
    if not mallas:
        OBJ['omitidos'].append({"pedido": ped, "id": ob['id'], "motivo": "MOLDE_OBJETO_SIN_MALLA"}); continue
    for o in mallas:
        sc.collection.objects.link(o); mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
        o.name = f"{ped}.{o.name.split('.')[0]}"; o['prop_motor'] = ob['id']
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in mallas for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))); hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    cen = (lo + hi) / 2; dims = hi - lo
    emp = bpy.data.objects.new(f"PROP_{ped}", None); sc.collection.objects.link(emp); emp.location = cen; emp['prop_motor'] = ob['id']
    bpy.context.view_layer.update()
    for o in mallas:
        mw = o.matrix_world.copy(); o.parent = emp; o.matrix_parent_inverse = emp.matrix_world.inverted(); o.matrix_world = mw
    H = PJ[port]['arm']; hu = ob.get('hueso') or 'mano_R'
    if hu not in H.pose.bones: hu = next((h for h in ('mano_R', 'mano_L', 'cabeza') if h in H.pose.bones), None)
    if hu is None:
        OBJ['omitidos'].append({"pedido": ped, "id": ob['id'], "motivo": f"portador {port} sin hueso mano/cabeza -> pedir_a_fabrica"}); continue
    f0 = M['personajes'].get(port, {}).get('visible_desde', 1); sc.frame_set(f0); bpy.context.view_layer.update()
    pb = H.pose.bones[hu]; Bm = H.matrix_world @ pb.matrix @ H.data.bones[hu].matrix_local.inverted()
    fr = math.radians(PJ[port]['info']['frente_rest_deg']); fw = (Bm.to_3x3() @ Vector((math.cos(fr), math.sin(fr), 0))); fw.z = 0
    fw = fw.normalized() if fw.length > 1e-6 else Vector((0, -1, 0))
    yaw = math.atan2(fw.y, fw.x) + math.pi / 2
    if hu == 'cabeza':     # delante de la cara: rayo desde el centro de la cabeza hacia el frente, contra la malla del portador
        c = (H.matrix_world @ pb.head).lerp(H.matrix_world @ pb.tail, 0.45)
        ojos = [m for m in H.children_recursive if m.type == 'MESH' and not m.get('prop_motor') and re.search(r'(^|[_.])(ojo|eye)s?(_[LR])?$', m.name.split('.', 1)[-1], re.I)]
        if ojos:    # a la altura de los ojos del molde (visor/gafas sobre el puente nasal), no en la frente
            oc = [sum(((m.matrix_world @ Vector(k)) for k in m.bound_box), Vector()) / 8 for m in ojos]
            c.z = sum(v.z for v in oc) / len(oc); metodo_ojos = f'altura de {len(ojos)} ojo(s) del molde'
        else: metodo_ojos = '45 % del hueso cabeza'
        bv = _bvh_de(H, bpy.context.evaluated_depsgraph_get()); hit = bv.ray_cast(c + fw * 0.6, -fw, 0.8) if bv else (None,)
        sup = hit[0] if hit[0] is not None else c + fw * 0.1
        pos = sup + fw * (min(dims.x, dims.y) / 2 + 0.005); metodo = f'cabeza: superficie de la cara ({metodo_ojos}) + medio fondo'
    else:
        pos = (H.matrix_world @ pb.head).lerp(H.matrix_world @ pb.tail, 0.6); metodo = f'{hu}: 60 % del hueso'
    emp.parent = H; emp.parent_type = 'BONE'; emp.parent_bone = hu; bpy.context.view_layer.update()
    emp.matrix_world = Matrix.Translation(pos) @ Matrix.Rotation(yaw, 4, 'Z'); bpy.context.view_layer.update()
    visibilidad(mallas, f0)
    OBJ['cargados'].append({"pedido": ped, "id": ob['id'], "origen": ob.get('origen'), "estado": ob.get('estado'), "portador": port, "hueso": hu,
                            "hueso_fuente": ob.get('hueso_fuente'), "metodo": metodo, "mallas": len(mallas), "medidas_m": [round(v, 3) for v in dims],
                            "pos_f%d" % f0: [round(v, 3) for v in pos]})
    log('objeto', ped, '->', port, hu)
OBJ['s'] = round(time.time() - t_obj, 1); R['pasos']['3b_objetos'] = OBJ
R['pasos']['3_movimiento'] = {"s": round(time.time() - t_mov, 1), "planificador": {"astar": PL.get('astar'), "rvo2": PL.get('rvo2'), "avisos": PL.get('avisos', [])[:20]},
                             "router": M.get('router', [])[:60], "rechazos": M.get('rechazos', [])}

# ---------------------------------------------------------------- 4 escenario vivo (solo lo que la fábrica preparó / lo que ya existe)
vivo = {"piezas_vivas_fabrica": [], "apariciones": [], "pedir_a_fabrica": []}
for o in bpy.data.objects:
    if o.get('vivo'):
        try: regla = json.loads(o['vivo']) if isinstance(o['vivo'], str) else dict(o['vivo'])
        except Exception: regla = {"tipo": str(o['vivo'])}
        tipo = regla.get('tipo'); vel = float(regla.get('vel', 1.0)); amp = float(regla.get('amp', 0.05))
        base_l = o.location.copy(); base_r = o.rotation_euler.copy()
        for f in range(1, N + 1, 2):
            t = f / FPS
            if tipo == 'girar': o.rotation_euler.z = base_r.z + vel * t; o.keyframe_insert('rotation_euler', index=2, frame=f)
            elif tipo in ('flotar', 'fluir'): o.location.z = base_l.z + amp * math.sin(2 * math.pi * vel * t); o.keyframe_insert('location', index=2, frame=f)
            elif tipo == 'ondear': o.rotation_euler.x = base_r.x + amp * math.sin(2 * math.pi * vel * t); o.keyframe_insert('rotation_euler', index=0, frame=f)
        vivo['piezas_vivas_fabrica'].append({"objeto": o.name, "regla": regla})
for av in M.get('avisos', []):
    if av.get('aviso') != 'accion_de_objeto': continue
    nombre = av.get('objeto') or ''; cambio = (av.get('cambio') or '').lower()
    objs = [o for o in bpy.data.objects if o.type == 'MESH' and (o.name == nombre or o.name.startswith(nombre))]
    base = re.sub(r'^obj-|-dorado$|__.*$', '', nombre).split('-')[0]
    if objs and cambio == 'aparecer':
        dep = [o for o in bpy.data.objects if o.type == 'MESH' and o not in objs and base and base in o.name and o.name.startswith('obj-')]
        visibilidad(objs + dep, av['f0']); vivo['apariciones'].append({"objetos": [o.name for o in objs + dep], "desde_cuadro": av['f0']})
    elif not objs:
        vivo['pedir_a_fabrica'].append({"objeto": nombre, "cambio": cambio, "motivo": "la pieza no existe en el molde de escenario"})
    else:
        vivo['pedir_a_fabrica'].append({"objeto": nombre, "cambio": cambio, "motivo": "cambio sin regla de pieza viva marcada por la fábrica"})
R['pasos']['4_escenario_vivo'] = vivo

# ---------------------------------------------------------------- 5 cámara del storyboard
SB = json.load(open(f"{COR}/{E['storyboard']}")) if E.get('storyboard') else None
CV = json.load(open(f"{COR}/{E['camara_v2'] or E['camara_v1']}"))
_avisos_num = []
try:
    CV, _avisos_num = NJ.normalizar_camara(CV)
except NJ.ValorNoNumerico as ex:
    raise NJ.ValorNoNumerico(f"cámara JSON: {ex}") from ex
for _av in _avisos_num:
    if _av not in R['avisos']:
        R['avisos'].append(f"camara_numerica: {_av}")
sensor = CV.get('sensor_mm') or [36.0, 20.25]
sensor = [float(sensor[0]), float(sensor[1] if len(sensor) > 1 and sensor[1] else sensor[0] * 9 / 16)]
ASP = float(E['aspecto'][0]) / float(E['aspecto'][1])
SENSOR_H = sensor[1]
camd = bpy.data.cameras.new('camera_4g_master'); cam = bpy.data.objects.new('camera_4g_master', camd); sc.collection.objects.link(cam)
camd.sensor_fit = 'HORIZONTAL'; camd.sensor_width = sensor[0]; camd.clip_start = 0.02; camd.clip_end = 60; sc.camera = cam
ELEV = {'HIGHANGLE': 22.0, 'LOWANGLE': -14.0, 'EYELEVEL': 0.0, 'OVERHEAD': 70.0}
APUNTE = {'ECU': 0.92, 'CU': 0.88, 'MCU': 0.82, 'MS': 0.70, 'MLS': 0.6, 'MWS': 0.55, 'FS': 0.5, 'WS': 0.5, 'LS': 0.5, 'EWS': 0.5}
LADO = {'L': -1 / 3, 'C': 0.0, 'R': 1 / 3}
_cache = {}
def _eval(pid, f):
    k = (pid, f)
    if k not in _cache:
        a = PJ[pid]['arm'] if pid in PJ else bpy.data.objects.get(pid)
        if a is None: _cache[k] = None
        else:
            if sc.frame_current != f: sc.frame_set(f)
            cz = (a.matrix_world @ a.pose.bones['cabeza'].tail).z if a.type == 'ARMATURE' and 'cabeza' in a.pose.bones else None
            b = a.matrix_world.translation.copy(); b.z = piso_z(b.x, b.y)            # base = piso real bajo el personaje (no el origen del armature)
            _cache[k] = (b, a.matrix_world.to_euler().z if a.type == 'ARMATURE' else 0.0, cz)
    return _cache[k]
def pos_sujeto(pid, f):
    r = _eval(pid, f)
    return (None, None) if r is None else (r[0], r[1])
def interp_kf(kfs, t):
    kfs = sorted(kfs, key=lambda k: NJ.a_numero(k['t'], 't', obligatorio=True))
    t0 = NJ.a_numero(kfs[0]['t'], 't', obligatorio=True)
    if t <= t0: return kfs[0], kfs[0], 0.0
    for a, b in zip(kfs, kfs[1:]):
        ta = NJ.a_numero(a['t'], 't', obligatorio=True); tb = NJ.a_numero(b['t'], 't', obligatorio=True)
        if ta <= t <= tb: return a, b, (t - ta) / max(1e-6, tb - ta)
    return kfs[-1], kfs[-1], 0.0
avisos_sb = []
def num_giro(k, v):
    g = k.get('giro_grados', 0)
    if isinstance(g, (int, float)): return float(g)
    msg = f"{v['vineta']}: giro_grados no numérico en el SB («{g}») -> 0 y la panorámica sigue al objetivo (reportar al storyboard 02N)"
    if msg not in avisos_sb: avisos_sb.append(msg)
    return 0.0
camreg = []; tomas = []
locs = {}; rots = {}; lens = {}
# ---- distancia mínima y aire sobre la cabeza (Ricardo t1015u/t1016u): el SB fija plano, lente y movimiento; el motor sólo ALEJA
#      la cámara sobre su mismo eje cuando hace falta para que la cabeza completa del objetivo quepa con aire y para no meterse en la cara.
import encuadre_cabeza as ECAB
CAJA_CAB = {}
for _pid, _D in PJ.items():
    try: CAJA_CAB[_pid] = ECAB.caja_cabeza(_D['arm']) if 'cabeza' in _D['arm'].pose.bones else None
    except Exception as _ex: CAJA_CAB[_pid] = None; log('caja cabeza', _pid, _ex)
ALT_PJ = {p: float(D.get('alt') or 1.0) for p, D in PJ.items()}
CAM_DMIN_ALTURAS = 0.35      # distancia mínima cámara->centro de la cabeza = 0.35 x altura del personaje
CAM_DMIN_CARA_M = 0.12       # piso absoluto para personajes chicos (~0,17–0,18 m)
CAM_MARGEN_X, CAM_MARGEN_Y = 0.97, 0.92   # NDC: la cabeza completa dentro, con aire arriba/abajo
CAM_K_MAX = 8.0
CAM_K_OCLUSION = 1.6
CAM_Z_MIN = 0.05                    # la cámara nunca bajo el piso
CAM_OCL_MIN_CUADROS = 12            # si otro tapa >= 0.5 s sin salida alejándose, se prueba girar
CAM_GIROS_ESQUIVE = (15, -15, 30, -30, 45, -45)   # para esquivar a otro personaje que tapa se aleja como mucho 1.6x más; si no alcanza queda el aviso
_cab_cache = {}
def cab_mundo(pid, f):
    k = (pid, f)
    if k not in _cab_cache:
        caja = CAJA_CAB.get(pid)
        if caja is None: _cab_cache[k] = None
        else:
            if sc.frame_current != f: sc.frame_set(f)
            E = ECAB.esquinas(PJ[pid]['arm'], caja); _cab_cache[k] = (E, sum(E, Vector()) / 8)
    return _cab_cache[k]
def dmin_de(pid): return max(CAM_DMIN_ALTURAS * ALT_PJ.get(pid, 1.0), CAM_DMIN_CARA_M)
def _dist_seg(P, A, B):
    AB = B - A; t = max(0.0, min(1.0, (P - A).dot(AB) / max(1e-9, AB.length_squared))); return (A + AB * t - P).length
def _tapa(Ck, pid, ctr_obj, f):
    """otro personaje (cuerpo = segmento pies->centro de cabeza, radio 0.22 x altura) con la cámara adentro o entre la cámara y la cabeza del objetivo"""
    cm = cab_mundo(pid, f)
    if cm is None or PJ[pid]['info'].get('movimiento', '').startswith('acoplado'): return False
    ctr = cm[1]; H = ALT_PJ.get(pid, 1.0); A = ctr - Vector((0, 0, 0.9 * H)); r = 0.22 * H   # cuerpo entero, piernas incluidas
    if _dist_seg(Ck, A, ctr) < r: return True
    for i in range(1, 10):          # muestras sobre la línea cámara -> cabeza del objetivo (sin el último tramo junto al objetivo)
        Q = Ck + (ctr_obj - Ck) * (i / 10.0)
        if _dist_seg(Q, A, ctr) < r * 0.8: return True
    return False
def k_necesario(C, Rm, Pv, lente, obj, f):
    """menor factor k (>=1) para C_k = Pv + (C - Pv) k: cabeza completa del objetivo dentro con aire, ninguna cabeza a menos de su distancia
    mínima y (si se puede) sin otro personaje tapando o con la cámara metida en él. Devuelve (k, ocluido)."""
    k = 1.0; primero_ok = None
    cm_o = cab_mundo(obj, f)
    for _ in range(54):
        Ck = Pv + (C - Pv) * k; ok = True
        for pid in PJ:
            cm = cab_mundo(pid, f)
            if cm is None or PJ[pid]['arm'].hide_render: continue
            E, ctr = cm
            pc = CC.proyectar(Ck, Rm, ctr, lente, sensor[0], ASP)
            if pid != obj and (pc is None or abs(pc[0]) > 1.2 or abs(pc[1]) > 1.2): continue
            if (ctr - Ck).length < dmin_de(pid): ok = False; break
            if pid == obj:
                for e in E:
                    pe = CC.proyectar(Ck, Rm, e, lente, sensor[0], ASP)
                    if pe is None or abs(pe[0]) > CAM_MARGEN_X or abs(pe[1]) > CAM_MARGEN_Y: ok = False; break
                if not ok: break
        if ok:
            if primero_ok is None: primero_ok = k
            if Ck.z < CAM_Z_MIN: pass          # bajo el piso: no sirve, se sigue buscando
            elif cm_o is None or not any(_tapa(Ck, pid, cm_o[1], f) for pid in PJ if pid != obj and cab_mundo(pid, f) and not PJ[pid]['arm'].hide_render):
                return min(k, CAM_K_MAX), False
        if k >= CAM_K_MAX or (primero_ok is not None and k >= primero_ok * CAM_K_OCLUSION): break   # no alejar sin límite sólo por un tapón
        k *= 1.04
    return min(primero_ok or CAM_K_MAX, CAM_K_MAX), True
def calc_vineta(v, kf, gf=None):
    gf = gf or {}
    out = {}
    t0 = NJ.a_numero(v['t_abs'][0], 't_abs', obligatorio=True)
    t1 = NJ.a_numero(v['t_abs'][1], 't_abs', obligatorio=True)
    f0 = int(round(t0 * FPS)) + 1; f1 = min(N, int(round(t1 * FPS)))
    obj = v['objetivo']
    h_raw = NJ.a_numero(v.get('altura_m'), 'altura_m')
    h = float(h_raw if h_raw not in (None, 0) else PJ.get(obj, {}).get('alt', 1.0))
    el = math.radians(ELEV.get(v.get('angulo'), 0.0)); sx = LADO.get(v.get('lado_objetivo'), 0.0)
    fijo = {}
    for f in range(f0, f1 + 1):
        t = (f - 1) / FPS
        seg = next((s for s in v['segmentos'] if s['t_abs'][0] - 1e-6 <= t <= s['t_abs'][1] + 1e-6), v['segmentos'][-1])
        mov = seg.get('movimiento', 'STATIC'); sf0 = int(round(seg['t_abs'][0] * FPS)) + 1
        a, b, u = interp_kf(v['keyframes'], t); u2 = u * u * (3 - 2 * u)
        lente_a = NJ.a_numero(a.get('lente_mm'), 'lente_mm', obligatorio=True)
        lente_b = NJ.a_numero(b.get('lente_mm'), 'lente_mm', obligatorio=True)
        da = NJ.a_numero(a.get('distancia_m'), 'distancia_m')
        db = NJ.a_numero(b.get('distancia_m'), 'distancia_m')
        if da is None:
            da = NJ.distancia_desde_plano(a.get('plano'), lente_a, h, SENSOR_H)
            msg = (f"cámara {v['vineta']}: distancia_m no numérica en el keyframe "
                   f"(«{a.get('distancia_m')}»); se calcula por plano+lente+altura = {da:.3f} m")
            if msg not in avisos_sb: avisos_sb.append(msg)
        if db is None:
            db = NJ.distancia_desde_plano(b.get('plano'), lente_b, h, SENSOR_H)
            msg = (f"cámara {v['vineta']}: distancia_m no numérica en el keyframe "
                   f"(«{b.get('distancia_m')}»); se calcula por plano+lente+altura = {db:.3f} m")
            if msg not in avisos_sb: avisos_sb.append(msg)
        dist = da + (db - da) * u2; lente = lente_a + (lente_b - lente_a) * u2
        dist *= kf.get(f, 1.0)
        ga, gb = num_giro(a, v), num_giro(b, v)
        giro = math.radians(ga + (gb - ga) * u2 + gf.get(f, 0.0))
        apunte = APUNTE.get(a.get('plano'), 0.7) + (APUNTE.get(b.get('plano'), 0.7) - APUNTE.get(a.get('plano'), 0.7)) * u2
        ref_f = f if mov in ('TRACK', 'PAN') else sf0                    # STATIC/DOLLY/CRANE: el sujeto de referencia queda en el inicio del segmento
        base, yaw = pos_sujeto(obj, ref_f)
        if base is None: R['avisos'].append(f"cámara {v['vineta']}: objetivo {obj} no está en escena"); break
        if obj in PJ and _eval(obj, ref_f)[2] is not None:
            hz = _eval(obj, ref_f)[2] - base.z; h_real = max(h * 0.8, hz)
        else: h_real = h
        Pt = base + Vector((0, 0, h_real * apunte))
        frente = yaw + math.radians(PJ[obj]['info']['frente_rest_deg']) if obj in PJ else -math.pi / 2
        e = el
        if mov == 'CRANE':
            d_ud = (seg.get('args', {}).get('dir_ud') or 'UP').upper(); us = (t - seg['t_abs'][0]) / max(1e-6, seg['t_abs'][1] - seg['t_abs'][0])
            e = el + math.radians(18) * (us if d_ud == 'UP' else -us)
        dirc = Vector((math.cos(frente + giro) * math.cos(e), math.sin(frente + giro) * math.cos(e), math.sin(e)))
        C = Pt + dirc * max(0.05, dist)
        if mov == 'STATIC' and seg['t_abs'][0] in fijo: C = fijo[seg['t_abs'][0]]
        elif mov == 'STATIC': fijo[seg['t_abs'][0]] = C.copy()
        if mov == 'PAN':
            key =[REDACTED]
            if key not in fijo: fijo[key] = C.copy()
            C = fijo[key]
        Pv = (base if mov in ('TRACK', 'PAN') else pos_sujeto(obj, f)[0]) + Vector((0, 0, h_real * apunte))
        Rm = CC.quitar_roll(C, CC.mirar_sin_roll(C, Pv), Pv, Pv, (sx, 0.0), (sx, 0.0), lente, sensor[0], ASP)
        out[f] = (C, Rm, lente, Pv, mov, seg['t_abs'][0])
    return f0, f1, obj, out
def suavizar_k(kn, fr, movs, segs):
    """k por cuadro: máximo móvil ±12 y promedio ±6 (nunca queda por debajo de lo necesario); en STATIC/PAN un solo k por segmento
    (la cámara fija no se mueve); en los bordes con un segmento fijo, rampa de 12 cuadros para no saltar."""
    n = len(fr); km = [max(kn[max(0, i - 12):i + 13]) for i in range(n)]
    ks = [sum(km[max(0, i - 6):i + 7]) / len(km[max(0, i - 6):i + 7]) for i in range(n)]
    grupos = {}
    for i in range(n): grupos.setdefault(segs[i], []).append(i)
    for sg, ii in grupos.items():
        if movs[ii[0]] in ('STATIC', 'PAN'):
            K = max(kn[i] for i in ii)
            for i in ii: ks[i] = K
    for i in range(n):          # rampas hacia/desde segmentos fijos
        if movs[i] in ('STATIC', 'PAN'): continue
        for j in range(max(0, i - 12), min(n, i + 13)):
            if movs[j] in ('STATIC', 'PAN') and segs[j] != segs[i]:
                w = 1 - abs(i - j) / 13.0; ks[i] = max(ks[i], ks[j] * w + ks[i] * (1 - w))
    return ks
cam_ajuste = {}
for v in CV['vinetas']:
    f0 = int(round(v['t_abs'][0] * FPS)) + 1
    if f0 > N: continue
    f0, f1, obj, o1 = calc_vineta(v, {})
    if not o1: continue
    fr = sorted(o1); kr = [k_necesario(o1[f][0], o1[f][1], o1[f][3], o1[f][2], obj, f) for f in fr]; kn = [x[0] for x in kr]; ocl = sum(1 for x in kr if x[1])
    gf = {}; dg_ok = 0
    if ocl >= CAM_OCL_MIN_CUADROS:      # otro personaje tapa y alejarse no basta: girar un poco alrededor del objetivo (mismo plano y mismo movimiento)
        mejor = (ocl, 0, kr)
        for dg in CAM_GIROS_ESQUIVE:
            g_ = {f: float(dg) for f in fr}; _, _, _, od = calc_vineta(v, {}, g_)
            if sorted(od) != fr: continue
            krd = [k_necesario(od[f][0], od[f][1], od[f][3], od[f][2], obj, f) for f in fr]; ocd = sum(1 for x in krd if x[1])
            if ocd < mejor[0] and ocd <= ocl * 0.5: mejor = (ocd, dg, krd)   # sólo se gira si baja al menos a la mitad
            if ocd == 0: break
        ocl, dg_ok, kr = mejor; kn = [x[0] for x in kr]
        if dg_ok: gf = {f: float(dg_ok) for f in fr}
    ks = suavizar_k(kn, fr, [o1[f][4] for f in fr], [o1[f][5] for f in fr])
    kf = dict(zip(fr, ks))
    _, _, _, o2 = calc_vineta(v, kf, gf) if (max(ks) > 1.0001 or gf) else (None, None, None, o1)
    for f, (C, Rm, lente, Pv, mov, sg) in o2.items():
        locs[f] = C; rots[f] = Rm.to_euler('XYZ'); lens[f] = lente
    cam_ajuste[v['vineta']] = {"k_max": round(max(ks), 2), "k_medio": round(sum(ks) / len(ks), 2), "cuadros_alejados": sum(1 for k in ks if k > 1.0001), "cuadros_con_otro_tapando_sin_salida": ocl, "giro_esquive_deg": dg_ok}
    tomas.append({"vineta": v['vineta'], "frame_ini": f0, "frame_fin": f1, "objetivo": obj, "angulo": v.get('angulo'), "lado": v.get('lado_objetivo'),
                  "movimientos": [s.get('movimiento') for s in v['segmentos']], "altura_m": v.get('altura_m'), "alejamiento": cam_ajuste[v['vineta']]})
fr_cam = sorted(locs)
datos = {('location', i): [locs.get(f, locs[fr_cam[0]])[i] for f in range(1, N + 1)] for i in range(3)}
eul = []; prev = None
for f in range(1, N + 1):
    e = rots.get(f, rots[fr_cam[0]]).copy()
    if prev is not None: e.make_compatible(prev)
    eul.append(e); prev = e
for i in range(3): datos[('rotation_euler', i)] = [e[i] for e in eul]
escribir_fcurves(cam, datos, 'CONSTANT')
escribir_fcurves(camd, {('lens', 0): [lens.get(f, 35.0) for f in range(1, N + 1)]}, 'CONSTANT')
for t_ in tomas: sc.timeline_markers.new(t_['vineta'], frame=t_['frame_ini'])
shake = [v for v in (SB or {}).get('vinetas', []) if re.search(r'SHAKE|HANDHELD|TEMBL', json.dumps(v.get('director_camara', {}), ensure_ascii=False).upper())]
R['pasos']['5_camara'] = {"tomas": tomas, "metodo": "camara_calculada (mirar_sin_roll + quitar_roll, lado del SB) + DSL del SB v2 con altura_m",
                         "shakify": "no pedido por el SB" if not shake else [v['id'] for v in shake], "anyshot": "instalado, no usado en el corte (el SB ya fija cada toma)",
                         "avisos_storyboard": avisos_sb}
log('camara', len(tomas), 'tomas')
# chequeo: sujeto principal en cuadro y roll
from bpy_extras.object_utils import world_to_camera_view
chk = []
for t_ in tomas:
    dentro = 0; tot = 0; completa = 0; dmin_c = 99.0
    for f in range(t_['frame_ini'], t_['frame_fin'] + 1, 2):
        sc.frame_set(f); a = PJ.get(t_['objetivo'], {}).get('arm')
        if a is None: continue
        pbc = a.pose.bones.get('cabeza')   # centro de la cabeza (mitad del hueso), no la base del cuello: en ECU el mentón puede salir
        p = a.matrix_world @ ((pbc.head + pbc.tail) * 0.5) if pbc else a.matrix_world.translation
        q = world_to_camera_view(sc, cam, p); tot += 1; dentro += (0 <= q.x <= 1 and 0 <= q.y <= 1 and q.z > 0)
        caja = CAJA_CAB.get(t_['objetivo'])
        if caja:
            qs = [world_to_camera_view(sc, cam, e_) for e_ in ECAB.esquinas(a, caja)]
            completa += all(0 <= x.x <= 1 and 0 <= x.y <= 1 and x.z > 0 for x in qs)
            dmin_c = min(dmin_c, (a.matrix_world @ ((pbc.head + pbc.tail) * 0.5) - cam.matrix_world.translation).length)
    chk.append({"vineta": t_['vineta'], "cabeza_objetivo_en_cuadro_pct": round(100 * dentro / max(1, tot), 1),
                "cabeza_completa_pct": round(100 * completa / max(1, tot), 1) if CAJA_CAB.get(t_['objetivo']) else None,
                "dist_min_cabeza_m": round(dmin_c, 3), "dist_min_requerida_m": round(dmin_de(t_['objetivo']), 3)})
R['pasos']['5_camara']['chequeo_encuadre'] = chk

# ---------------------------------------------------------------- ocultar_estorbos + camara_sin_paredes (por toma, paso 2)
blend_out = f'{COR}/escena_motor.blend'
if not A.sin_ocultar:
    import ocultar_estorbos as OE
    def objetos_reales(noms):
        # el SB nombra 'obj-libro-cuentos__e1-8'; la fábrica publica 'obj-libro-cuentos#1__0..n' -> se protegen las piezas reales
        out = []
        for nom in noms:
            base = re.sub(r'__.*$', '', nom)
            hits = [o.name for o in bpy.data.objects if o.type == 'MESH' and (o.name == nom or o.name.startswith(base + '#') or o.name.startswith(base + '_') or o.name.startswith(base + '.'))]
            out += hits or [nom]
        # props que lleva un personaje protegido (visor, pistola...) se protegen con él
        out += [o.name for o in bpy.data.objects if o.type == 'MESH' and o.get('prop_motor') and o.parent and o.parent.parent and o.parent.parent.name in noms]
        return out
    oc = []
    # [t1066u] N0 universal (sb3d_niveles): personajes, piso, soporte/contacto, props y lo que nombra el guion -> nunca se ocultan
    N0_MALLAS = None
    try:
        import sb3d_niveles as NV
        _ents = NV.entidades(); _mc = {}
        def _med(p, f):
            if (p, f) not in _mc:
                sc.frame_set(f); _mc[(p, f)] = NV.medir_personaje(bpy.data.objects[p], bpy.context.evaluated_depsgraph_get(), _ents[p])
            return _mc[(p, f)]
        _frs = sorted({x for t_ in tomas for x in (t_['frame_ini'], (t_['frame_ini'] + t_['frame_fin']) // 2, t_['frame_fin'])})
        _niv, _int, _gr = NV.clasificar(E, SB, _frs, sc, _med, _ents)
        N0_MALLAS = sorted(NV.mallas_de_nivel(_niv, 'N0'))
        R['pasos']['5_camara']['niveles_n0'] = sorted(e for e, d in _niv.items() if d['nivel'] == 'N0')
    except Exception as ex:
        R['avisos'].append(f"niveles N0 no calculados ({ex}); ocultar_estorbos protege solo lo del SB")
    for t_ in tomas:
        vsb = next((x for x in (SB or {}).get('vinetas', []) if x.get('id') == t_['vineta']), {})
        di = vsb.get('director_imagen', {})
        toma = {"contrato": "toma_ocultar_v1", "toma_id": f"esc{E['escena']}_{t_['vineta']}", "vineta": t_['vineta'], "frame_ini": t_['frame_ini'], "frame_fin": t_['frame_fin'],
                "camara": cam.name, "objetivo": t_['objetivo'], "en_cuadro": [x['id'] for x in di.get('en_cuadro', []) if x.get('id')],
                "debe_verse": vsb.get('debe_verse', []), "objetos_sb": objetos_reales([x['nombre'] for x in di.get('objetos', []) if x.get('nombre')]), "paso_frames": A.paso_ocultar}
        if N0_MALLAS is not None: toma['n0'] = N0_MALLAS
        try:
            Es = OE.Escena(toma); frames = list(range(toma['frame_ini'], toma['frame_fin'] + 1, toma['paso_frames']))
            an0 = Es.analizar(frames); pu, mot = Es.decidir(an0)
            sim = {o.name: fs for u, fs in pu.items() for o in Es.objetos_de_unidad(u)}
            an1 = Es.analizar(frames, ocultar_simulado=sim); Es.aplicar(pu)
            R0, R1 = OE.resumen(an0, Es), OE.resumen(an1, Es)
            oc.append({"vineta": t_['vineta'], "ocultados": [{"unidad": u, "cuadros": len(fs), "motivo": mot.get(u)} for u, fs in pu.items()],
                       "antes_muestras_tapadas": R0['muestras_tapadas'], "despues_muestras_tapadas": R1['muestras_tapadas'],
                       "camara_dentro_antes": R0['cuadros_camara_dentro'], "camara_dentro_despues": R1['cuadros_camara_dentro'],
                       "no_encontrados": Es.no_encontrados, "conflictos": R1['conflictos']})
            log('ocultar', t_['vineta'], 'tapadas', R0['muestras_tapadas'], '->', R1['muestras_tapadas'])
        except Exception as ex:
            oc.append({"vineta": t_['vineta'], "error": repr(ex)}); log('ocultar error', t_['vineta'], ex)
    R['pasos']['5_camara']['ocultar_estorbos'] = oc

# ---------------------------------------------------------------- 6 revisión (umbrales del gate viejo fisica_final)
UMB = {"com_accel_max_m_s2": 20.0, "joint_speed_max_deg_s": 900.0, "slip_max_m_per_frame": 0.05, "penetration_tolerance_m": 0.02, "separacion_min_m": 0.18}
rev = {"umbrales": UMB, "personajes": {}, "pares": []}
pos_all = {pid: [] for pid in PJ}
acum = {pid: {"hips": [], "feet": {'pie_L': [], 'pie_R': []}, "jmax": 0.0, "prev": None, "pen": 0,
              "names": [b for b in ('cabeza', 'brazo_L', 'brazo_R', 'antebrazo_L', 'antebrazo_R', 'femur_L', 'femur_R', 'tibia_L', 'tibia_R') if b in D['arm'].pose.bones],
              "vis0": M['personajes'].get(pid, {}).get('visible_desde', 1), "acop": bool(M['personajes'].get(pid, {}).get('acople'))} for pid, D in PJ.items()}
for f in range(1, N + 1):
    sc.frame_set(f)
    for pid, D in PJ.items():
        arm = D['arm']; G = acum[pid]; mw = arm.matrix_world
        c = mw @ arm.pose.bones['cadera'].head if 'cadera' in arm.pose.bones else mw.translation
        G['hips'].append(c.copy()); pos_all[pid].append(c.copy())
        cur = {n: (mw.to_quaternion() @ arm.pose.bones[n].matrix.to_quaternion()) for n in G['names']}
        if G['prev'] and f > G['vis0']:
            for n in G['names']:
                q0 = G['prev'][n]; q1 = cur[n]
                ang_ = q1.rotation_difference(q0).angle; ang_ = min(ang_, 2 * math.pi - ang_)
                G['jmax'] = max(G['jmax'], math.degrees(ang_) * FPS if not G['acop'] else 0)
        G['prev'] = cur
        for p in G['feet']:
            if p in arm.pose.bones:
                pb = arm.pose.bones[p]; h = mw @ pb.head; t = mw @ pb.tail; tip = h if h.z <= t.z else t; G['feet'][p].append(tip)
                if f >= G['vis0'] and not G['acop'] and tip.z < piso_z(tip.x, tip.y) - UMB['penetration_tolerance_m']: G['pen'] += 1
for pid, D in PJ.items():
    G = acum[pid]; hips = G['hips']; vis0 = G['vis0']
    acc = [((hips[i + 1] - 2 * hips[i] + hips[i - 1]) * FPS * FPS).length for i in range(max(2, vis0), N - 1)] if not G['acop'] else []
    slip = 0.0
    for p, tl in G['feet'].items():
        if G['acop']: break
        for i in range(max(1, vis0), len(tl)):
            if tl[i].z - piso_z(tl[i].x, tl[i].y) < 0.015 and tl[i - 1].z - piso_z(tl[i - 1].x, tl[i - 1].y) < 0.015:
                slip = max(slip, math.hypot(tl[i].x - tl[i - 1].x, tl[i].y - tl[i - 1].y))
    accs = sorted(acc); pen = G['pen']
    r = {"acel_cadera_max_m_s2": round(accs[-1], 2) if accs else 0, "acel_cadera_p99_m_s2": round(accs[int(len(accs) * .99)], 2) if accs else 0,
         "vel_articular_max_deg_s": round(G['jmax'], 1), "resbale_pie_max_m_cuadro": round(slip, 4), "penetracion_cuadros": pen, "acoplado": G['acop']}
    r['ok'] = (r['acel_cadera_p99_m_s2'] <= UMB['com_accel_max_m_s2'] and r['vel_articular_max_deg_s'] <= UMB['joint_speed_max_deg_s']
               and r['resbale_pie_max_m_cuadro'] <= UMB['slip_max_m_per_frame'] and pen == 0)
    rev['personajes'][pid] = r
ids = list(PJ)
for i in range(len(ids)):
    for j in range(i + 1, len(ids)):
        a, b = ids[i], ids[j]
        if M['personajes'].get(a, {}).get('acople', {}) and M['personajes'][a]['acople'].get('host') == b: continue
        if M['personajes'].get(b, {}).get('acople', {}) and M['personajes'][b]['acople'].get('host') == a: continue
        va = M['personajes'].get(a, {}).get('visible_desde', 1); vb = M['personajes'].get(b, {}).get('visible_desde', 1)
        dmin = min((math.hypot(pos_all[a][f].x - pos_all[b][f].x, pos_all[a][f].y - pos_all[b][f].y) for f in range(max(va, vb) - 1, N)), default=9)
        _rad = PL.get('radios_m') or {}
        _min = (float(_rad[a]) + float(_rad[b])) * 0.9 if a in _rad and b in _rad else UMB['separacion_min_m']   # [argon_v2] por tamaño real
        rev['pares'].append({"a": a, "b": b, "dist_min_m": round(dmin, 3), "minimo_m": round(_min, 3), "ok": dmin >= _min})
# [t518] choque cuerpo<->mueble (los personajes no pueden quedar dentro de muebles) + cadera fuera de rango (hundida o volando)
try:
    import choques_muebles as CHM
    _inv = json.load(open(f'{COR}/inventario.json'))
    # [argon_v2] sin excepciones salvo relación física declarada: sentado/acostado SOBRE un mueble o debajo cuando el hueco lo permite
    _exc = {p: sorted({x.split('__')[0] for x in v}) for p, v in (PL.get('exentos') or {}).items()}
    rev['choques_muebles'] = CHM.medir(sc, _inv, paso=4, ids=set(PJ), excluir=_exc)
except Exception as ex:
    rev['choques_muebles'] = {"error": repr(ex)}
for pid in PJ:
    hz = [h.z - piso_z(h.x, h.y) for h in acum[pid]['hips']]
    if hz and not acum[pid]['acop']:
        ref = sorted(hz)[len(hz) // 2]; alt_ = PJ[pid].get('alt') or 1.0
        dv = max(abs(z - ref) for z in hz[max(0, acum[pid]['vis0'] - 1):])
        rev['personajes'][pid]['cadera_desvio_altura_max_m'] = round(dv, 3)
        if dv > 0.35 * alt_: rev['personajes'][pid]['ok'] = False; rev['personajes'][pid]['cadera_fuera_de_rango'] = True
rev['muebles_ok'] = all(v.get('ok', False) for v in rev['choques_muebles'].values()) if isinstance(rev.get('choques_muebles'), dict) and 'error' not in rev['choques_muebles'] else False
rev['camara_ok'] = all(c['cabeza_objetivo_en_cuadro_pct'] >= 80 and (c.get('cabeza_completa_pct') is None or c['cabeza_completa_pct'] >= 100.0) for c in chk)   # t1016u: cabeza COMPLETA 100 %
rev['ok'] = all(r['ok'] for r in rev['personajes'].values()) and all(p['ok'] for p in rev['pares']) and rev['camara_ok'] and rev['muebles_ok']
R['pasos']['6_revision'] = rev
log('revision ok=', rev['ok'])
bpy.ops.wm.save_as_mainfile(filepath=blend_out); R['blend'] = blend_out
if not (os.path.isfile(blend_out) and os.path.getsize(blend_out) > 1024):
    raise RuntimeError(f"FALLO_SIN_BLEND: no se escribió {blend_out}")
R['estado'] = 'OK'
R['segundos'] = round(time.time() - T0, 1); R['log'] = LOG[-60:]
json.dump(R, open(f'{COR}/reporte_motor.json', 'w'), indent=1, ensure_ascii=False, default=str)
print('RESULT_MOTOR', json.dumps({"ok": rev['ok'], "blend": blend_out, "s": R['segundos']}))
_MOTOR_OK = True
