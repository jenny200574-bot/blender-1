# v3_20261031+v3los: vista_general elige ángulo con línea de visión libre; +v3camfix +v3aim +v3piso
# PISTA INMI o114 (t312u/t313u): igual que o113 + poses con la escala propia de cada hueso (sin deriva) + GUARDIA DEL CUERPO en cada cuadro (guardia_o114.py): si un cuerpo se rompe la escena se RECHAZA nombrando hueso y cuadro.
# PISTA INMI o112 (t305u): igual que o111 pero lee los beats DETALLADOS de Argon (pos/ruta/rot numéricos del set, acoples, efectos de→a). o111 — cubo 02 «video gris representativo» de UNA escena (genérico). Corre dentro de Blender con el molde.blend abierto:
#   blender -b molde.blend -P video_o111_blender.py -- entrada.json salida.json
# entrada: personajes (como o109), puntos, eventos.beats (esquema eventos_o111), tomas (id, t, camara_molde, palabras), fps, duracion, res, salida_dir.
# Reusa: cuerpos de molde_o109_blender.py (VRM por parámetros / figura gris), poses de o110 (aplicar_pose.py humanoides VRM, universal.py otros rigs).
import bpy, json, math, os, sys, random
from mathutils import Vector, Matrix, Quaternion, Euler
from mathutils.bvhtree import BVHTree
A_ = sys.argv[sys.argv.index('--') + 1:]; E = json.load(open(A_[0])); OUT = A_[1]
src = open(E['molde_o109_blender']).read(); src = src[:src.index("for p in E['personajes']:")]
G = {'__name__': 'molde_o109'}; sys.argv = ['x', '--', A_[0], OUT]; exec(compile(src, 'molde_o109_blender', 'exec'), G)
# STAR maniquí con huesos (reemplaza VRM):
_man_path = E.get('maniqui_huesos') or os.path.join(os.path.dirname(E['molde_o109_blender']), 'maniqui_huesos.py')
_man_ns = {'bpy': bpy, 'math': math, 'json': json, 'Path': __import__('pathlib').Path, 'Vector': Vector, 'Matrix': Matrix, 'Quaternion': Quaternion, '__builtins__': __builtins__, '__name__': 'maniqui_huesos'}
exec(compile(open(_man_path).read(), 'maniqui_huesos', 'exec'), _man_ns)
G['maniqui'] = _man_ns['construir']
G['aplicar_limites_canal'] = _man_ns['aplicar_limites_canal']
_ART_LIB = None
_ART_LOAD_ERR = None
_art_path = E.get('articulaciones_json')
if _art_path and os.path.isfile(_art_path):
    try:
        _ART_LIB = json.load(open(_art_path))
    except Exception as _ex:
        _ART_LOAD_ERR = str(_ex)

sys.path.insert(0, E['o110_dir']); import aplicar_pose as AP, universal as UNI, guardia_o114 as GU
import importlib.util as _ilu
_acc_dir = os.path.join(os.environ.get('STAR_MOTOR_SRC', ''), 'acciones')
if _acc_dir not in sys.path: sys.path.insert(0, os.path.dirname(_acc_dir))
try:
    from acciones import sentarse as ACC_SIT
except Exception:
    ACC_SIT = None
LIB = json.load(open(E['poses_lib']))
sc = bpy.context.scene; FPS = int(E.get('fps') or 8); DUR = float(E['duracion_s']); NF = int(round(DUR * FPS)) + 1
sc.render.fps = FPS; sc.frame_start = 1; sc.frame_end = NF
for o in bpy.data.objects:
    if o.type == 'FONT' or o.name.startswith(('marca_', 'flecha_', 'rej_')): o.hide_render = o.hide_viewport = True
_CAM_AUTO_LOG = []
for x in E.get('camaras_auto') or []:   # o113 + v3c look_at
    if not bpy.data.objects.get(x['nombre']):
        bpy.ops.object.camera_add(location=x['loc']); c_ = bpy.context.object; c_.name = x['nombre']; c_.data.lens = x.get('lente_mm', 24)
        if x.get('look_at'):
            _la = Vector(x['look_at']); _d = _la - Vector(x['loc'])
            c_.rotation_euler = _d.to_track_quat('-Z', 'Y').to_euler()
        elif x.get('dir'):
            c_.rotation_euler = Vector(x['dir']).to_track_quat('-Z', 'Y').to_euler()
        _CAM_AUTO_LOG.append(f"v3c cam_auto {c_.name} loc={list(x['loc'])} look_at={x.get('look_at')}")
SET = [o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render]
for o in SET: o.color = (.55, .55, .57, 1)
avisos, faltas = [], []
if _ART_LOAD_ERR: avisos.append(f'FALTA cargar articulaciones: {_ART_LOAD_ERR}')
for _cl in (_CAM_AUTO_LOG if '_CAM_AUTO_LOG' in dir() else []): avisos.append(_cl)
# ---------- v3b: escenario paramétrico (fórmula + puntos + huesos) ----------
_PARAM_DOC = None
_PARAM_REPORT = None
if E.get('escenario_parametrico'):
    import importlib.util as _ilu2
    _ep = os.path.join(os.environ.get('STAR_MOTOR_SRC', ''), 'escenario', 'escenario_parametrico.py')
    if not os.path.isfile(_ep):
        _ep = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'escenario', 'escenario_parametrico.py')
    _spec = _ilu2.spec_from_file_location('escenario_parametrico', _ep)
    _emod = _ilu2.module_from_spec(_spec); _spec.loader.exec_module(_emod)
    _PARAM_DOC = _emod.load(E['escenario_parametrico'])
    _PARAM_REPORT = _emod.build_scene(_PARAM_DOC, hide_replaced=True)
    avisos.append(f"v3b parametrico: built={_PARAM_REPORT.get('built')} hidden={len(_PARAM_REPORT.get('hidden') or [])} puntos={len(_PARAM_REPORT.get('puntos') or [])}")
    # aplicar parámetros c iniciales (estado) del plan
    for _ps in (E.get('parametros_escenario') or []):
        _c = float(_ps.get('c') if _ps.get('c') is not None else 0)
        _hid = _ps.get('hueso') or _ps.get('id')
        for _h in (_PARAM_REPORT.get('huesos') or []):
            if _h.get('id') == _hid or _h.get('param') == _ps.get('param'):
                _emod.apply_param(_c, _h)
                break
    # re-enumerar SET tras ocultar molde y crear meshes
    SET = [o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render]

def fr(t): return 1 + t * FPS
PT = {k: Vector(v) for k, v in (E.get('puntos') or {}).items()}
# ---------- BVH del set (piso, choques, oclusión) ----------
def bvh_de(o):
    dg = bpy.context.evaluated_depsgraph_get(); e = o.evaluated_get(dg); m = e.to_mesh()
    V = [o.matrix_world @ v.co for v in m.vertices]; P = [tuple(p.vertices) for p in m.polygons]; e.to_mesh_clear()
    return BVHTree.FromPolygons(V, P) if P else None
BV = {o.name: bvh_de(o) for o in SET}; BV = {k: v for k, v in BV.items() if v}
def piso(x, y, ztop, permitir_muebles=False):
    """v3b: pies en el suelo (z≈0) salvo beat 'subir'.
    Bug v3: hit MÁS ALTO → cima silla molde 1.05 m como 'piso' → Kael de pie encima / sentado flotando.
    Ahora: 1) hits de objetos marcados es_suelo / nombre piso|alfombra|suelo; 2) si no hay, hit más BAJO
    bajo z_techo (suelo real); 3) solo si permitir_muebles=True (subir) toma el más alto caminable."""
    best_suelo = None
    best_hi = None
    best_lo = None
    z_techo = min(float(ztop) - 0.05, 2.15)
    skip = ('techo', 'cielo', 'ceiling', 'ilumin', 'luminar', 'luz_techo', 'columna del techo',
            'molde_hide_', 'monitor', 'vasos', 'libreta', 'cables', 'lampara', 'reloj', 'poster')
    suelo_kw = ('piso', 'alfombra', 'suelo', 'floor', 'param_piso', 'param_alfombra')
    for n, b in BV.items():
        nl = n.lower()
        if any(k in nl for k in skip):
            continue
        h = b.ray_cast(Vector((x, y, ztop)), Vector((0, 0, -1)), 50)
        if h[0] is None:
            continue
        z = h[0].z
        if z > z_techo or z < -0.05:
            continue
        o = bpy.data.objects.get(n)
        es_suelo = (o is not None and o.get('es_suelo')) or any(k in nl for k in suelo_kw) or z < 0.08
        if es_suelo:
            if best_suelo is None or z > best_suelo[0]:
                best_suelo = (z, n)
        if best_hi is None or z > best_hi[0]:
            best_hi = (z, n)
        if best_lo is None or z < best_lo[0]:
            best_lo = (z, n)
    if not permitir_muebles:
        if best_suelo is not None:
            return best_suelo
        # fallback: superficie más baja (suelo), no la cima del mueble
        return best_lo or (0.0, None)
    return best_hi or best_suelo or best_lo or (0.0, None)
# ---------- personajes (STAR Etapa 0: humanoide sin controles = FALTA, no figura_gris) ----------
PERS = {}; ALT = {}
def _humanoide(h):
    return 0.6 <= float(h) <= 2.3   # rango humanoide; fuera (Imi mini / jirafa) puede figura_gris
def _tiene_controles(p):
    c = p.get('controles'); return bool(c) if isinstance(c, dict) else bool(c)
# Colores molde aprobados (azotea / moldes esc6) — solo si E lo trae; si no, ficha.
_COLOR_MOLDE = E.get('colores_molde') or {}
for p in E['personajes']:
    h = float(p.get('altura') or 1.7); ALT[p['id']] = h
    ctl = p.get('controles') if isinstance(p.get('controles'), dict) else {}
    # Mini / no-humanoide sin controles → maniquí mini si hay color, si no figura_gris
    usar_maniqui = True
    if _humanoide(h) and not _tiene_controles(p) and p['id'] not in _COLOR_MOLDE:
        # IMI a veces viene con controles vacíos: aún así armamos maniquí si color_molde o altura mini
        if h >= 0.6:
            msg = f"FALTA parametros_3d de {p['id']} (humanoide h={h} sin controles; no se cae a figura_gris)"
            print(msg); raise SystemExit(msg)
    if usar_maniqui and 'maniqui' in G:
        cov = _COLOR_MOLDE.get(p['id'])
        try:
            PERS[p['id']] = G['maniqui'](p['id'], h, ctl or {}, color_override=cov)
            for _f in (PERS[p['id']].get('faltas') or []):
                avisos.append(_f)
        except Exception as ex:
            msg = f"FALTA maniqui de {p['id']}: {ex}"
            print('MANIQUI_FALLO', msg); raise SystemExit(msg)
    else:
        PERS[p['id']] = G['figura_gris'](p['id'], h)
    PERS[p['id']].setdefault('giro_base', 90)
    # v6 siluetas: NO aplastar a gris uniforme — se conservan colores de parametros_3d
    # (pelo plata / armadura negra / núcleo cian / ropa). Solo refuerza ACC pulsera cian.
    ctr = p.get('controles') if isinstance(p.get('controles'), dict) else {}
    flags = []
    if ctr.get('pelo_largo'): flags.append('pelo_largo')
    if ctr.get('armadura'): flags.append('armadura')
    if ctr.get('nucleo_pecho'): flags.append('nucleo')
    if ctr.get('orejas_puntiagudas'): flags.append('orejas')
    if flags or h:
        avisos.append(f"v6silueta {p['id']}: h={h} tipo={PERS[p['id']].get('tipo')} flags={flags or ['(sin ACC distintivo en controles)']}")
for P in PERS.values():
    for o in P['objs']:
        if P.get('acc') and o.name == P['acc']: o.color = (.1, .95, 1, 1)
        elif o.name.startswith('ACC_') and ('nucleo' in o.name.lower() or 'pecho' in o.name.lower()):
            pass  # deja color del vrm()
BEATS = sorted(E['eventos']['beats'], key=lambda b: b['t'])
ACOP = {b['actor']: {'actor': b['acoplado_actor'], 'parte': b.get('acoplado_parte')} for b in BEATS if b.get('actor') and b.get('acoplado_actor')}
LEVI = {b['actor'] for b in BEATS if b.get('accion') == 'levitar'}
HUESO = {'muneca_izquierda': 'J_Bip_L_Hand', 'muneca_derecha': 'J_Bip_R_Hand', 'mano_izquierda': 'J_Bip_L_Hand', 'mano_derecha': 'J_Bip_R_Hand', 'hombro_izquierdo': 'J_Bip_L_UpperArm', 'hombro_derecho': 'J_Bip_R_UpperArm', 'pecho': 'J_Bip_C_UpperChest', 'cabeza': 'J_Bip_C_Head'}
# línea de tiempo por actor: (t, pos, rot, pose, espejo)
def keys_actor(pid):
    """Línea de tiempo SOLO desde los beats de Argon (o112): pos/ruta/rot en coordenadas del set. Sin pos inicial = no se inventa."""
    K = []; pos = None; rot = 0.0; pose = 'de_pie'
    for b in BEATS:
        if b.get('actor') != pid: continue
        t0 = float(b['t']); d = float(b.get('dur') or 0); r_ = float(b.get('rot', -1)); r_ = None if r_ < 0 else r_
        ruta = [Vector(x['pos']) for x in (b.get('ruta') or []) if x.get('pos')]; fin = Vector(b['pos']) if b.get('pos') else (ruta[-1] if ruta else None)
        pz = b.get('pose') or pose; esp = bool(b.get('espejo'))
        if pos is None:
            if fin is None: continue
            pos = (ruta[0] if ruta else fin).copy(); rot = r_ if r_ is not None else rot; K.append([0.0, pos.copy(), rot, pz if not ruta else 'de_pie', esp])
        if b['accion'] in ('caminar', 'correr') and (ruta or fin):
            pts = [pos] + [p for p in (ruta or [fin]) if (p - pos).length > 1e-3 or True]
            if fin is not None and (pts[-1] - fin).length > 1e-3: pts.append(fin)
            seglen = [(pts[i + 1] - pts[i]).length for i in range(len(pts) - 1)]; tot = sum(seglen) or 1e-6
            paso = 0.5 if b['accion'] == 'caminar' else 0.3; n = max(1, int(d / paso))
            K.append([t0, pos.copy(), K[-1][2], 'caminando', False])
            for i in range(1, n + 1):
                u = tot * i / n; acc = 0; k = 0
                while k < len(seglen) - 1 and acc + seglen[k] < u: acc += seglen[k]; k += 1
                f_ = 0 if seglen[k] == 0 else (u - acc) / seglen[k]; p = pts[k].lerp(pts[k + 1], min(1, f_)); v = pts[k + 1] - pts[k]; v.z = 0
                hd = math.degrees(math.atan2(v.y, v.x)) if v.length > 1e-3 else K[-1][2]
                K.append([t0 + d * i / n, p, hd, 'caminando' if i < n else pz, (i % 2 == 1) if i < n else esp])
            pos = K[-1][1].copy(); rot = r_ if r_ is not None else K[-1][2]
            if r_ is not None: K[-1][2] = r_
            pose = pz; continue
        if d > 0: K.append([t0, K[-1][1].copy(), K[-1][2], K[-1][3], K[-1][4]])
        if fin is not None: pos = fin.copy()
        if r_ is not None: rot = r_
        pose = pz; K.append([t0 + d, pos.copy(), rot, pose, esp])
    if not K: avisos.append(f'{pid}: sin beats con posición (no se inventa; queda oculto)')
    K.sort(key=lambda k: k[0]); return K
def objs_visibles(P): return [o for o in P['objs'] if o.type == 'MESH' and not o.name.startswith('ACC_')]
ASIENTOS = {}
TL = {}; LEV_OFF = {}; GUARD = {}
for pid, P in PERS.items():
    if pid in ACOP:
        for o in P['objs'] + ([P['root']] if P['root'].type == 'MESH' else []): o.hide_render = o.hide_viewport = True
        continue
    K = keys_actor(pid)
    if not K:
        for o in P['objs'] + ([P['root']] if P['root'].type == 'MESH' else []): o.hide_render = o.hide_viewport = True
        continue
    TL[pid] = K; A = P['A']; lev = 1.0 if pid in LEVI else 0.0
    for k in K:
        fz0, _ = piso(k[1].x, k[1].y, k[1].z + 3)
        if k[1].z - fz0 > .3: lev = max(lev, k[1].z - fz0)   # Argon lo pone en el aire (suspendido)
    LEV_OFF[pid] = lev
    if A is not None:   # o114: medida de referencia del cuerpo DE PIE (sus proporciones reales) para la guardia
        sc.frame_set(1); p0 = K[0][1]; AP.aplicar(A, LIB, 'de_pie', False, tuple(p0), K[0][2] + P['giro_base'])
        fz0, _ = piso(p0.x, p0.y, p0.z + 3); AP.apoyar(A, objs_visibles(P), fz0 + lev)
        GUARD[pid] = GU.Guardia(A, pid, GU.roles(A, LIB=LIB), objs_visibles(P), fz0 + lev)
    for t, pos, rot, pose, esp in K:
        f = fr(t); sc.frame_set(int(round(f)))
        if A is not None:   # humanoide VRM -> biblioteca o110
            try: pid_pose, pp = AP.aplicar(A, LIB, pose, esp, tuple(pos), rot + P['giro_base'])
            except AP.PoseFalta as ex: faltas.append(f'{pid} t={t}: {ex}'); pid_pose, pp = AP.aplicar(A, LIB, 'de_pie', False, tuple(pos), rot + P['giro_base'])
            fz, _ = piso(pos.x, pos.y, pos.z + 3); AP.apoyar(A, objs_visibles(P), fz + lev)
            if pp.get('asiento') and pid not in ASIENTOS and not E.get('silla'):   # silla molde → sin proxy
                hp = A.matrix_world @ A.pose.bones['J_Bip_C_Hips'].head; top = hp.z - fz - 0.12
                bpy.ops.mesh.primitive_cube_add(location=(hp.x, hp.y, fz + top / 2)); s = bpy.context.object; s.scale = (.25, .22, max(.05, top / 2)); s.color = (.5, .45, .4, 1)
                s.name = f'proxy_asiento_{pid}'; s.scale = (0, 0, 0); s.keyframe_insert('scale', frame=1); s.keyframe_insert('scale', frame=max(1, f - FPS)); s.scale = (.25, .22, max(.05, top / 2)); s.keyframe_insert('scale', frame=f); ASIENTOS[pid] = s
            for pb in A.pose.bones: pb.keyframe_insert('rotation_quaternion', frame=f); pb.keyframe_insert('location', frame=f)   # o114: escala NO se anima: aplicar() la deja siempre en la base del personaje (claves de escala en cientos de huesos hacían el render 4x más lento)
            A.keyframe_insert('location', frame=f); A.keyframe_insert('rotation_euler', frame=f)
        else:   # cuerpo sin esqueleto (figura gris): solo poses de cuerpo entero; el resto FALTA
            R = P['root']; R.rotation_mode = 'XYZ'; fz, _ = piso(pos.x, pos.y, pos.z + 3)
            tilt = {'de_pie': 0, 'caminando': 0, 'acostado_boca_arriba': -90, 'acostado_boca_abajo': 90}.get(pose)
            if tilt is None: faltas.append(f'{pid} t={t}: pose «{pose}» FALTA para un cuerpo sin esqueleto'); tilt = 0
            R.location = (pos.x, pos.y, fz + lev + (ALT[pid] * 0.13 if tilt else 0)); R.rotation_euler = (math.radians(tilt), 0, math.radians(rot + P['giro_base']))
            R.keyframe_insert('location', frame=f); R.keyframe_insert('rotation_euler', frame=f)

# ---------- v3: acción paramétrica sentarse/pararse (c∈[0,1]) ----------
# Solo si hay beats con accion sentarse/pararse. No inventa: lee fases_c / c0/c1 del beat.
_SIT_VALID = {'ok_frames': 0, 'bad_frames': 0, 'fallas': [], 'actores': []}
if ACC_SIT is not None:
    _sit_beats = [b for b in BEATS if b.get('accion') in ('sentarse', 'pararse')]
    for _sb in _sit_beats:
        _pid = _sb.get('actor')
        if not _pid or _pid not in PERS or PERS[_pid].get('A') is None:
            faltas.append(f"sentarse: actor {_pid} FALTA VRM")
            continue
        _P = PERS[_pid]; _A = _P['A']
        _pos = _sb.get('pos') or [0, 0, 0]
        _xy = (_pos[0], _pos[1])
        _rot = float(_sb.get('rot') if _sb.get('rot') is not None and float(_sb.get('rot')) >= 0 else 0)
        _asz = float(_sb.get('asiento_z') or 0.45)
        _fases = _sb.get('fases_c')
        if not _fases:
            if _sb.get('accion') == 'sentarse':
                _fases = ACC_SIT.fases_sentarse(float(_sb['t']), float(_sb.get('dur') or 3.0))
            else:
                _fases = ACC_SIT.fases_pararse(float(_sb['t']), float(_sb.get('dur') or 2.5))
        _objs = objs_visibles(_P)
        try:
            _ST, _SI, _FL0, _FR0, _ = ACC_SIT.preparar_extremos(
                _A, LIB, AP, _xy, _rot, _asz, giro_base=_P.get('giro_base') or 0.0, objs_mesh=_objs)
        except Exception as _ex:
            faltas.append(f"sentarse preparar {_pid}: {_ex}")
            continue
        # v3b: target por nombre silla.asiento (Empty paramétrico); fallback silla.xy del plan
        _sit_xy = None
        _asz_from_pt = None
        for _pn in (_sb.get('punto_asiento'), 'silla.asiento', (E.get('silla') or {}).get('punto')):
            if not _pn: continue
            _eo = bpy.data.objects.get(_pn)
            if _eo is not None:
                _lw = _eo.matrix_world.translation
                _sit_xy = (float(_lw.x), float(_lw.y))
                _asz_from_pt = float(_lw.z)
                break
        if _sit_xy is None and _sb.get('silla_id'):
            for _o in bpy.data.objects:
                if _o.name.startswith('param_silla') and _o.type == 'MESH' and 'asiento' in _o.name:
                    _bb = [ _o.matrix_world @ Vector(c) for c in _o.bound_box ]
                    _sit_xy = (sum(p.x for p in _bb)/8, sum(p.y for p in _bb)/8)
                    _asz_from_pt = max(p.z for p in _bb)
                    break
        if _sit_xy is None and isinstance(E.get('silla'), dict) and E['silla'].get('xy'):
            _sit_xy = tuple(E['silla']['xy'])
        if _asz_from_pt is not None:
            _asz = _asz_from_pt
            # re-preparar extremos con asiento real del punto
            try:
                _ST, _SI, _FL0, _FR0, _ = ACC_SIT.preparar_extremos(
                    _A, LIB, AP, _xy, _rot, _asz, giro_base=_P.get('giro_base') or 0.0, objs_mesh=_objs)
            except Exception as _ex:
                faltas.append(f"sentarse re-preparar {_pid}: {_ex}")
                continue
        # rango temporal = unión beat + fases_c (cubre quieto sentado c=1)
        _t0 = float(_sb['t']); _t1 = _t0 + float(_sb.get('dur') or 0)
        if _fases:
            _t0 = min(_t0, min(float(f['t0']) for f in _fases))
            _t1 = max(_t1, max(float(f['t1']) for f in _fases))
        _nf = max(1, int(round((_t1 - _t0) * FPS)))
        # espalda = opuesto a rot (0=+x, 90=+y): respaldo detrás del asiento
        _respaldo_y = None
        if _sit_xy is not None:
            import math as _m
            _back = _m.radians(_rot + (_P.get('giro_base') or 0.0) + 180.0)
            # en coords mundo el root rot de VRM usa giro_base; para silla molde usamos rot del beat
            _fwd_y = _m.sin(_m.radians(_rot))  # rot 90 → +1
            _respaldo_y = _sit_xy[1] - 0.22 * (1 if _fwd_y >= 0 else -1)
            # si mira +Y, respaldo en -Y respecto al centro
        for _i in range(_nf + 1):
            _t = _t0 + (_t1 - _t0) * _i / max(1, _nf)
            _c, _fid = ACC_SIT.c_at(_t, _fases)
            _f = fr(_t); sc.frame_set(int(round(_f)))
            # re-aplicar rot del beat (frame_set puede dejar rot de otra clave)
            _A.rotation_mode = 'XYZ'
            _A.rotation_euler = (__import__('math').radians(0), 0,
                                 __import__('math').radians(_rot + (_P.get('giro_base') or 0.0)))
            ACC_SIT.aplicar_c(_A, _c, _ST, _SI, _FL0, _FR0, _asz, AP,
                             respaldo_y=_respaldo_y, sit_root_xy=_sit_xy)
            for _pb in _A.pose.bones:
                _pb.keyframe_insert('rotation_quaternion', frame=_f)
                _pb.keyframe_insert('location', frame=_f)
            _A.keyframe_insert('location', frame=_f); _A.keyframe_insert('rotation_euler', frame=_f)
            _fails = ACC_SIT.validar_frame(_A, _c, _FL0, _FR0, _asz, respaldo_y=_respaldo_y, sit_root_xy=_sit_xy, stand_root_xy=_xy)
            if _fails:
                _SIT_VALID['bad_frames'] += 1
                if len(_SIT_VALID['fallas']) < 40:
                    _SIT_VALID['fallas'].append({'t': round(_t, 3), 'c': round(_c, 3), 'fails': _fails})
            else:
                _SIT_VALID['ok_frames'] += 1
        _SIT_VALID['actores'].append(_pid)
        avisos.append(f"v3 sentarse/pararse aplicado a {_pid} t={_t0}-{_t1} asiento_z={_asz}")
        # si hay silla del molde, eliminar proxy_asiento (claves de escala lo dejaban visible)
        if _pid in ASIENTOS or E.get('silla') or any(b.get('silla_id') for b in _sit_beats):
            for _nm in list(bpy.data.objects.keys()):
                if _nm.startswith(f'proxy_asiento_{_pid}') or _nm.startswith('proxy_asiento_'):
                    _o = bpy.data.objects.get(_nm)
                    if _o is not None:
                        try:
                            bpy.data.objects.remove(_o, do_unlink=True)
                        except Exception:
                            pass
            ASIENTOS.pop(_pid, None)
CHK_SIT = _SIT_VALID
# ---------- v3b: animar huesos del escenario (c∈[0,1] en el tiempo) ----------
if _PARAM_DOC is not None and E.get('anim_escenario'):
    def _find_bone_obj(_hid):
        cmap = {
            'puerta.bisagra': ['param_puerta_principal_hinge', 'puerta.bisagra'],
            'puerta_bano.bisagra': ['param_puerta_bano_hinge'],
            'silla.giro': ['param_silla_root'],
            'colchon.hundimiento': ['param_cama_colchon'],
            'cortina.hueso_0': ['param_cortina_hueso_0'],
            'cortina.hueso_1': ['param_cortina_hueso_1'],
            'cortina.hueso_2': ['param_cortina_hueso_2'],
            'cortina.hueso_3': ['param_cortina_hueso_3'],
            'cortina.hueso_4': ['param_cortina_hueso_4'],
            'lampara.articulacion_1': ['param_lampara_art1'],
            'lampara.articulacion_2': ['param_lampara_art2'],
            'armario.puerta_izq': ['param_armario'],
            'armario.puerta_der': ['param_armario'],
            'luz.intensidad': ['param_luz_intensidad', 'param_iluminacion', 'luz.intensidad'],
            'monitor_1.encendido': ['param_monitor_1'],
            'monitor_2.encendido': ['param_monitor_2'],
            'computador.encendido': ['param_computador'],
            'cables.corriente': ['param_cables'],
        }
        for n in cmap.get(_hid, []) + [_hid, _hid.replace('.', '_'), f"param_{_hid.split('.')[0]}"]:
            o = bpy.data.objects.get(n)
            if o is not None:
                return o
        return None
    for _ae in E['anim_escenario']:
        _hid = _ae.get('hueso') or _ae.get('id')
        _hs = next((h for h in (_PARAM_REPORT.get('huesos') or []) if h.get('id') == _hid or h.get('param') == _ae.get('param')), None)
        if _hs is None:
            avisos.append(f"anim_escenario: hueso {_hid} FALTA en report")
            continue
        _ob = _find_bone_obj(_hid)
        if _ob is None:
            avisos.append(f"anim_escenario: objeto de {_hid} FALTA")
            continue
        _ta0 = float(_ae.get('t0') or 0); _ta1 = float(_ae.get('t1') or DUR)
        _c0 = float(_ae.get('c0') if _ae.get('c0') is not None else 0)
        _c1 = float(_ae.get('c1') if _ae.get('c1') is not None else 1)
        _nfa = max(1, int(round((_ta1 - _ta0) * FPS)))
        for _ia in range(_nfa + 1):
            _ua = _ia / max(1, _nfa)
            _ca = _c0 + (_c1 - _c0) * _ua
            _ta = _ta0 + (_ta1 - _ta0) * _ua
            _fa = fr(_ta); sc.frame_set(int(round(_fa)))
            _emod.apply_param(_ca, _hs)
            try:
                _ob.keyframe_insert('rotation_euler', frame=_fa)
            except Exception:
                pass
            try:
                _ob.keyframe_insert('location', frame=_fa)
            except Exception:
                pass
            try:
                _ob.keyframe_insert('color', frame=_fa)
            except Exception:
                pass
            # v4: keyframe luces si es luz.intensidad
            if _hid == 'luz.intensidad':
                for _lo in bpy.data.objects:
                    if _lo.type == 'LIGHT':
                        try:
                            _lo.data.keyframe_insert('energy', frame=_fa)
                        except Exception:
                            pass
        avisos.append(f"v4 anim_escenario {_hid} c {_c0}→{_c1} t={_ta0}-{_ta1} obj={_ob.name}")

# ---------- v5 poderes / eventos_escenario (1ª versión simple visible) ----------
_V5_EFX = []
def _v5_emisivo(nombre, loc, radio, color, t0, t1, tipo='esfera'):
    import bpy
    from mathutils import Vector
    if tipo == 'rayo':
        bpy.ops.mesh.primitive_cylinder_add(radius=max(0.02, radio*0.15), depth=max(0.3, radio*2), location=loc)
    else:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=max(0.05, radio), location=loc)
    o = bpy.context.object
    o.name = nombre
    o.color = (*color[:3], 1.0)
    try:
        o.display_type = 'SOLID'
    except Exception:
        pass
    # keyframe visibility/scale (frame_set exige int)
    fa0 = int(round(fr(t0))); fa1 = int(round(fr(t1)))
    o.scale = (0.01, 0.01, 0.01)
    o.keyframe_insert('scale', frame=max(1, fa0-1))
    sc.frame_set(fa0); o.scale = (1,1,1); o.keyframe_insert('scale', frame=fa0)
    sc.frame_set(fa1); o.scale = (1.2,1.2,1.2); o.keyframe_insert('scale', frame=fa1)
    sc.frame_set(fa1+2); o.scale = (0.01,0.01,0.01); o.keyframe_insert('scale', frame=fa1+2)
    _V5_EFX.append(o.name)
    avisos.append(f"v5 poder/efecto {nombre} t={t0}-{t1}")
    return o

for _pw in (E.get('poderes') or []):
    try:
        _col = _pw.get('color') or '#88aaff'
        _NAM = {'azul_cian':(0.3,0.85,1.0),'azul_blanco':(0.6,0.8,1.0),'cian':(0.2,0.95,1.0),
                'rojo':(1,0.2,0.15),'verde':(0.2,1,0.3),'morado':(0.6,0.2,0.9),'blanco':(1,1,1)}
        if isinstance(_col, str) and _col.startswith('#') and len(_col) >= 7:
            _rgb = (int(_col[1:3],16)/255, int(_col[3:5],16)/255, int(_col[5:7],16)/255)
        elif isinstance(_col, str) and _col.lower() in _NAM:
            _rgb = _NAM[_col.lower()]
        else:
            _rgb = (0.5, 0.7, 1.0)
        _tam = float(_pw.get('tamano_m') or 0.4)
        _td = float(_pw.get('t_disparo') or _pw.get('t_carga') or 0)
        _ti = float(_pw.get('t_impacto') or (_td + 0.5))
        # origen: near lanzador chest
        _loc = Vector((2.0, 3.0, 1.2))
        _lan = _pw.get('lanzador')
        if _lan in PERS:
            _P = PERS[_lan]
            try:
                if _P.get('A') is not None:
                    _loc = _P['A'].matrix_world @ _P['A'].pose.bones['J_Bip_C_UpperChest'].head
                else:
                    _loc = _P['root'].matrix_world.translation + Vector((0,0, ALT.get(_lan,1.7)*0.6))
            except Exception:
                _loc = _P['root'].matrix_world.translation + Vector((0,0,1.0))
        _tray = (_pw.get('trayectoria') or 'esfera')
        _tipo = 'rayo' if _tray in ('recta','arco') else 'esfera'
        _v5_emisivo(f"v5_poder_{_pw.get('id') or len(_V5_EFX)}", _loc, _tam, _rgb, _td, _ti, _tipo)
        # mover hacia objetivo (persona / xyz / objeto.punto)
        _objn = _pw.get('objetivo'); _tgt = None
        if isinstance(_objn, dict) and _objn.get('xyz'):
            _tgt = Vector([float(x) for x in _objn['xyz']])
        elif isinstance(_objn, str) and _objn in PERS:
            _tgt = PERS[_objn]['root'].matrix_world.translation + Vector((0,0,1.0))
        elif isinstance(_objn, str) and '.' in _objn:
            _oid = _objn.split('.',1)[0]
            for _bo in bpy.data.objects:
                if _bo.name in (f'param_{_oid}', _oid) or _bo.name.endswith(_oid):
                    _tgt = _bo.matrix_world.translation + Vector((0,0,1.0)); break
        if _tgt is not None and _V5_EFX:
            _o = bpy.data.objects.get(_V5_EFX[-1])
            if _o is not None:
                try:
                    _ftd=int(round(fr(_td))); _fti=int(round(fr(_ti)))
                    sc.frame_set(_ftd); _o.location = _loc; _o.keyframe_insert('location', frame=_ftd)
                    sc.frame_set(_fti); _o.location = _tgt; _o.keyframe_insert('location', frame=_fti)
                except Exception as _ex:
                    avisos.append(f"v5 poder traj: {_ex}")
    except Exception as _ex:
        avisos.append(f"v5 poder FALTA: {_ex}")

for _ev in (E.get('eventos_escenario') or []):
    try:
        _tipo = _ev.get('tipo')
        _t0 = float(_ev.get('t0') or 0); _t1 = float(_ev.get('t1') or (_t0+1))
        if _tipo == 'temblor':
            _amp = float(_ev.get('amplitud_m') or 0.03)
            _freq = float(_ev.get('frecuencia_hz') or 5)
            # shake param objects / roots slightly
            _targets = [o for o in bpy.data.objects if o.name.startswith('param_') and o.type in ('EMPTY','MESH')]
            _targets = _targets[:40]
            _n = max(2, int(round((_t1-_t0)*FPS)))
            import math as _math
            for _i in range(_n+1):
                _u = _i/max(1,_n); _t = _t0 + (_t1-_t0)*_u; _f = fr(_t)
                _dx = _amp * _math.sin(2*_math.pi*_freq*_u)
                _dy = _amp * _math.cos(2*_math.pi*_freq*_u)
                sc.frame_set(int(round(_f)))
                for _o in _targets:
                    try:
                        if not hasattr(_o, '_v5_base_loc'):
                            _o['_v5_base'] = list(_o.location)
                        _b = _o.get('_v5_base') or list(_o.location)
                        _o.location = (_b[0]+_dx, _b[1]+_dy, _b[2])
                        _o.keyframe_insert('location', frame=int(round(_f)))
                    except Exception:
                        pass
            avisos.append(f"v5 temblor amp={_amp} f={_freq} t={_t0}-{_t1}")
        elif _tipo in ('explosion', 'portal', 'deformacion'):
            _c = _ev.get('centro_xyz') or [2.5, 3.0, 1.0]
            _r = float(_ev.get('radio_m') or 1.0)
            _col = (1.0, 0.5, 0.1) if _tipo=='explosion' else ((0.6,0.2,0.9) if _tipo=='portal' else (0.4,0.8,1.0))
            _v5_emisivo(f"v5_evt_{_tipo}_{len(_V5_EFX)}", Vector(_c), _r, _col, _t0, _t1, 'esfera')
        elif _tipo == 'luz':
            for _lo in bpy.data.objects:
                if _lo.type == 'LIGHT':
                    _c0 = float(_ev.get('c0') or 0); _c1 = float(_ev.get('c1') or 1)
                    _ft0=int(round(fr(_t0))); _ft1=int(round(fr(_t1)))
                    sc.frame_set(_ft0); _lo.data.energy = 50*(1-_c0)+5; _lo.data.keyframe_insert('energy', frame=_ft0)
                    sc.frame_set(_ft1); _lo.data.energy = 50*(1-_c1)+5; _lo.data.keyframe_insert('energy', frame=_ft1)
            avisos.append(f"v5 evento luz t={_t0}-{_t1}")
    except Exception as _ex:
        avisos.append(f"v5 evento FALTA: {_ex}")

# pelea: simple knockback on receptor root
for _pe in (E.get('pelea') or []):
    try:
        _obj = _pe.get('objetivo'); _ti = float(_pe.get('t_impacto') or 0)
        _re = _pe.get('reaccion') or {}
        if _obj in PERS and _re:
            _root = PERS[_obj]['root']
            _dist = float(_re.get('distancia_m') or 0.8)
            _fti=int(round(fr(_ti)))
            sc.frame_set(_fti)
            _base = _root.location.copy()
            _root.keyframe_insert('location', frame=_fti)
            _t1 = float(_re.get('t1') or (_ti+0.8))
            # push mostly in +Y as simple visible reaction
            _ft1=int(round(fr(_t1)))
            sc.frame_set(_ft1)
            _root.location = (_base.x, _base.y + _dist, _base.z)
            _root.keyframe_insert('location', frame=_ft1)
            avisos.append(f"v5 pelea knockback {_obj} d={_dist} t={_ti}")
    except Exception as _ex:
        avisos.append(f"v5 pelea FALTA: {_ex}")

# ---------- efectos y cambios de objetos ----------
def color(o, c): o.color = (*c, 1)
CIAN = (.1, .95, 1)
def centro_de(ref, f):
    sc.frame_set(f)
    if ref in PERS:
        P = PERS[ref]; A = P['A']
        if ref in ACOP:
            h = PERS[ACOP[ref]['actor']]; hb = HUESO.get(ACOP[ref]['parte'] or '', 'J_Bip_C_UpperChest')
            if h['A'] is not None: return h['A'].matrix_world @ h['A'].pose.bones[hb].head
            return h['root'].matrix_world.translation + Vector((0, 0, ALT[ACOP[ref]['actor']] * .5))
        if A is not None: return A.matrix_world @ A.pose.bones['J_Bip_C_UpperChest'].head
        return P['root'].matrix_world.translation + Vector((0, 0, ALT[ref] * .5))
    if ref in EFX: return EFX[ref].matrix_world.translation.copy()
    if ref in PT: return PT[ref] + Vector((0, 0, 1))
    # v4: aliases molde→param (molde oculto tras escenario_parametrico)
    _alias = {
        'obj-escritorio-muebles-apartamento': ['param_escritorio', 'escritorio.superficie'],
        'amb-esc-habitacion-protagonista-regleta-enchufes': ['param_regleta', 'cables.trazo'],
        'amb-esc-habitacion-protagonista-silla-ergonomica': ['param_silla_asiento', 'silla.asiento'],
    }
    for _n in [ref] + list(_alias.get(ref) or []) + ([f'param_{ref}'] if ref else []):
        if _n in PT:
            return PT[_n] + Vector((0, 0, 0.05))
        o = bpy.data.objects.get(_n)
        if o is not None and not o.hide_render:
            return o.matrix_world.translation.copy()
        if o is not None:
            return o.matrix_world.translation.copy()
    # puntos nombrados del parametrico
    for _cand in (ref, (ref or '').replace('obj-', '').replace('amb-esc-habitacion-protagonista-', '')):
        o = bpy.data.objects.get(_cand)
        if o is not None:
            return o.matrix_world.translation.copy()
    return None
EFX = {}; HECHOS = []
def mano(pid, f):
    # Si «de» es objeto/ambiente (no actor), cae a centro_de — rayos objeto→objeto.
    sc.frame_set(f)
    if pid not in PERS:
        return centro_de(pid, f)
    A = PERS[pid]['A']
    return (A.matrix_world @ A.pose.bones['J_Bip_R_Hand'].head) if A is not None else centro_de(pid, f)
paso = 1
for b in BEATS:
    ef = b.get('efecto'); f0 = int(fr(float(b['t']))); f1 = int(fr(float(b['t']) + float(b.get('dur') or 0)))
    if ef and ef.get('tipo'):
        tp = ef['tipo']; de = ef.get('de')
        if tp == 'prision':
            c = centro_de(de, f0); r = ALT.get(de, 1.7) * .7
            bpy.ops.mesh.primitive_ico_sphere_add(radius=r, subdivisions=2, location=c); o = bpy.context.object; o.name = ef['id']
            w = o.modifiers.new('w', 'WIREFRAME'); w.thickness = .03; color(o, CIAN)
            o.scale = (0, 0, 0); o.keyframe_insert('scale', frame=max(1, f0)); o.scale = (1, 1, 1); o.keyframe_insert('scale', frame=max(f1, f0 + 1)); EFX[ef['id']] = o
        elif tp == 'anillo_portal':
            c = centro_de(de, f0) or Vector((0, 0, 1)); r = ALT.get(de, 1.7) * 1.1
            bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=.06, location=c, rotation=(math.radians(90), 0, 0)); o = bpy.context.object; o.name = ef['id']; color(o, CIAN)
            o.scale = (0, 0, 0); o.keyframe_insert('scale', frame=max(1, f0)); o.scale = (1, 1, 1); o.keyframe_insert('scale', frame=max(f1, f0 + 1))
            o.rotation_mode = 'XYZ'; o.keyframe_insert('rotation_euler', frame=1); o.rotation_euler.y = math.radians(360 * DUR / 6); o.keyframe_insert('rotation_euler', frame=NF)
            for fc in o.animation_data.action.fcurves:
                if fc.data_path == 'rotation_euler':
                    for k in fc.keyframe_points: k.interpolation = 'LINEAR'
            EFX[ef['id']] = o
        elif tp == 'pulso':
            bpy.ops.mesh.primitive_uv_sphere_add(radius=.07); o = bpy.context.object; o.name = ef['id']; color(o, CIAN)
            for f in range(1, NF + 1, paso):
                c = centro_de(de, f)
                if c is None: continue
                o.location = c; o.keyframe_insert('location', frame=f); s = 1 + .6 * max(0, math.sin(f / FPS * 2 * math.pi)); o.scale = (s, s, s); o.keyframe_insert('scale', frame=f)
            EFX[ef['id']] = o
        elif tp == 'particulas':
            for k in range(14):
                bpy.ops.mesh.primitive_ico_sphere_add(radius=.03, subdivisions=1); o = bpy.context.object; o.name = f"{ef['id']}_{k}"; color(o, CIAN)
                ph = random.Random(k).random() * 6.28
                for f in range(max(1, f0), min(NF, f1 + 4 * FPS) + 1, 2):
                    c = centro_de(de, f); tt = (f - f0) / FPS
                    if c is None:
                        continue
                    o.location = c + Vector((math.cos(ph + tt * 2) * .5, math.sin(ph + tt * 2) * .5, (tt * .4 + k * .05) % 1.2 - .4)); o.keyframe_insert('location', frame=f)
        elif tp == 'rayo':
            bpy.ops.mesh.primitive_cylinder_add(radius=.025, depth=1, vertices=8); o = bpy.context.object; o.name = ef['id']; color(o, CIAN); o.rotation_mode = 'QUATERNION'
            HECHOS.append(('rayo', o, de, ef.get('a'), f0, f1))
    cam = b.get('cambio')
    if cam and b.get('objeto'):
        o = EFX.get(b['objeto']) or bpy.data.objects.get(b['objeto'])
        if o is None: avisos.append(f"cambio «{cam}»: el objeto {b['objeto']} no está en el molde (no se inventa)"); continue
        if cam == 'comprimir':
            for f in range(f0, f1 + 1, 2 * FPS):
                s = 1 - .25 * ((f - f0) / max(1, f1 - f0)) + .05 * math.sin(f); o.scale = (s, s, s); o.keyframe_insert('scale', frame=f)
        elif cam in ('aparecer', 'desaparecer') and o.name not in EFX:
            s0 = o.scale.copy(); o.scale = (0, 0, 0) if cam == 'aparecer' else s0; o.keyframe_insert('scale', frame=max(1, f0))
            o.scale = s0 if cam == 'aparecer' else (0, 0, 0); o.keyframe_insert('scale', frame=max(f1, f0 + 1))
            if cam == 'aparecer': o.scale = (0, 0, 0); o.keyframe_insert('scale', frame=1)
        elif cam == 'mover' and b.get('pos'):
            o.keyframe_insert('location', frame=f0); d = Vector(b['pos']); o.location = (d.x, d.y, o.location.z); o.keyframe_insert('location', frame=max(f1, f0 + 1))
        elif cam == 'romper':   # el objeto se oculta y salen trozos con caída balística hasta el piso
            dims = o.dimensions.copy(); c = o.matrix_world.translation.copy(); o.keyframe_insert('scale', frame=f0); s0 = o.scale.copy(); o.scale = (0, 0, 0); o.keyframe_insert('scale', frame=f0 + 1)
            rnd = random.Random(7)
            for k in range(10):
                bpy.ops.mesh.primitive_cube_add(size=1); q = bpy.context.object; q.name = f'trozo_{o.name}_{k}'; q.scale = (dims.x / 3, dims.y / 3, dims.z / 3); q.color = o.color
                p0 = c + Vector(((rnd.random() - .5) * dims.x, (rnd.random() - .5) * dims.y, (rnd.random() - .5) * dims.z)); v = (p0 - c).normalized() * 2 + Vector((0, 0, 2))
                q.hide_render = True; q.keyframe_insert('hide_render', frame=1); q.hide_render = False; q.keyframe_insert('hide_render', frame=f0 + 1)
                fz, _ = piso(p0.x, p0.y, p0.z + 0.01)
                for f in range(f0 + 1, min(NF, f0 + 3 * FPS) + 1):
                    tt = (f - f0) / FPS; p = p0 + v * tt + Vector((0, 0, -4.9 * tt * tt)); p.z = max(p.z, fz + q.scale.z / 2)
                    q.location = p; q.keyframe_insert('location', frame=f); q.rotation_euler = (tt * 3, tt * 2, 0); q.keyframe_insert('rotation_euler', frame=f)
            HECHOS.append(('roto', o.name, f0))
for kind, o, de, a, f0, f1 in [h for h in HECHOS if h[0] == 'rayo']:
    for f in range(1, NF + 1):
        vis = f0 <= f <= f1
        if vis:
            p, q = mano(de, f), centro_de(a, f)
            if p is not None and q is not None:
                v = q - p; o.location = (p + q) / 2; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(v); o.scale = (1 + .5 * (f % 2), 1 + .5 * (f % 2), v.length)
        else: o.scale = (0, 0, 0)
        o.keyframe_insert('location', frame=f); o.keyframe_insert('rotation_quaternion', frame=f); o.keyframe_insert('scale', frame=f)



# ---------- STAR_IK_CONTACTOS_v1c: CCD solo Upper+LowerArm + lean + root XY (sin snap) ----------
_HAND_MAP = {
    'mano_R': ('J_Bip_R_UpperArm', 'J_Bip_R_LowerArm', 'J_Bip_R_Hand'),
    'mano_L': ('J_Bip_L_UpperArm', 'J_Bip_L_LowerArm', 'J_Bip_L_Hand'),
    'mano_derecha': ('J_Bip_R_UpperArm', 'J_Bip_R_LowerArm', 'J_Bip_R_Hand'),
    'mano_izquierda': ('J_Bip_L_UpperArm', 'J_Bip_L_LowerArm', 'J_Bip_L_Hand'),
}
if _PARAM_REPORT and isinstance(_PARAM_REPORT.get('puntos'), dict):
    for _k, _v in _PARAM_REPORT['puntos'].items():
        if _k not in PT:
            try: PT[_k] = Vector(_v)
            except Exception: pass

def _star_tip(A, hand_name, lo_name):
    hb = A.pose.bones.get(hand_name)
    blo = A.pose.bones.get(lo_name)
    if hb is not None:
        return A.matrix_world @ hb.head
    if blo is not None:
        return A.matrix_world @ blo.tail
    return None

def _star_ik_ccd(A, names, target_w, iters=40):
    up, lo, hand = names
    chain = [n for n in (up, lo) if A.pose.bones.get(n) is not None]
    for n in chain:
        A.pose.bones[n].rotation_mode = 'QUATERNION'
    for _ in range(iters):
        bpy.context.view_layer.update()
        for bn in reversed(chain):
            b = A.pose.bones[bn]
            tip = _star_tip(A, hand, lo)
            if tip is None: return False
            origin = A.matrix_world @ b.head
            to_tip = tip - origin
            to_tgt = target_w - origin
            if to_tip.length < 1e-6 or to_tgt.length < 1e-6: continue
            q = to_tip.normalized().rotation_difference(to_tgt.normalized())
            q = Quaternion((1,0,0,0)).slerp(q, 0.85)
            Mw = A.matrix_world @ b.matrix
            Rnew = q.to_matrix().to_4x4() @ Mw
            b.matrix = A.matrix_world.inverted() @ Rnew
    bpy.context.view_layer.update()
    return True

def _star_lean_chest(A, target_w, amount=0.22):
    chest = A.pose.bones.get('J_Bip_C_Chest') or A.pose.bones.get('J_Bip_C_UpperChest')
    if chest is None: return
    chest.rotation_mode = 'QUATERNION'
    bpy.context.view_layer.update()
    origin = A.matrix_world @ chest.head
    forward = Vector((target_w.x - origin.x, target_w.y - origin.y, 0.0))
    if forward.length < 1e-4: return
    # lean: rotate chest so local +Y tips toward target (mild)
    cur = Vector((0, 1, 0))
    q = cur.rotation_difference(Vector((forward.x, forward.y, 0.6)).normalized())
    q = Quaternion((1,0,0,0)).slerp(q, amount)
    # apply in pose space additive-ish via matrix
    Mw = A.matrix_world @ chest.matrix
    Rnew = q.to_matrix().to_4x4() @ Mw
    # clamp: only keep if chest head stays reasonable
    chest.matrix = A.matrix_world.inverted() @ Rnew
    bpy.context.view_layer.update()
    ch = A.matrix_world @ chest.head
    if ch.z > 2.2 or ch.z < 0.3:
        chest.rotation_quaternion = (1,0,0,0)
        bpy.context.view_layer.update()

def _star_resolve_punto(nombre):
    if nombre in PT: return PT[nombre].copy()
    o = bpy.data.objects.get(nombre)
    if o is not None:
        return o.matrix_world.translation.copy()
    oid = nombre.split('.', 1)[0]
    for cand in (f'param_{oid}',):
        o = bpy.data.objects.get(cand)
        if o is not None:
            return o.matrix_world.translation.copy()
    return None

_IK_MED = {'ok': [], 'faltas': [], 'dists': []}
CHK_IK = _IK_MED
for _ct in (E.get('contactos') or []):
    try:
        _actor = _ct.get('actor'); _parte = _ct.get('parte_cuerpo') or ''
        _pto = _ct.get('objeto_punto'); _t0 = float(_ct.get('t0') or 0); _t1 = float(_ct.get('t1') or (_t0+0.5))
        _dmax = float(_ct.get('dist_max_m') or 0.03)
        if _actor not in PERS:
            faltas.append(f"IK contacto: actor {_actor} FALTA"); continue
        A = PERS[_actor].get('A')
        if A is None:
            faltas.append(f"IK contacto: {_actor} sin armature FALTA"); continue
        names = _HAND_MAP.get(_parte)
        if not names:
            faltas.append(f"IK contacto: parte {_parte} desconocida FALTA"); continue
        tgt0 = _star_resolve_punto(_pto)
        if tgt0 is None:
            faltas.append(f"IK contacto: punto {_pto} FALTA"); continue
        f0 = max(1, int(round(fr(_t0)))); f1 = min(NF, int(round(fr(_t1))))
        _ds = []
        sc.frame_set(f0); bpy.context.view_layer.update()
        _base_loc = Vector(A.location)
        for f in range(f0, f1 + 1):
            sc.frame_set(f)
            bpy.context.view_layer.update()
            # reset arm bones to keyed pose first (frame_set already did)
            tgt = tgt0.copy()
            tip0 = _star_tip(A, names[2], names[1])
            if tip0 is not None:
                flat = Vector((tgt.x - _base_loc.x, tgt.y - _base_loc.y, 0))
                # stand closer if horizontal reach gap large
                reach = Vector((tgt.x - tip0.x, tgt.y - tip0.y, 0))
                if reach.length > 0.35:
                    step = flat.normalized() * min(0.12, reach.length - 0.25)
                    A.location = (_base_loc.x + step.x, _base_loc.y + step.y, _base_loc.z)
                    A.keyframe_insert('location', frame=f)
                    bpy.context.view_layer.update()
            _star_lean_chest(A, tgt, 0.2)
            chest = A.pose.bones.get('J_Bip_C_Chest') or A.pose.bones.get('J_Bip_C_UpperChest')
            if chest is not None:
                chest.keyframe_insert('rotation_quaternion', frame=f)
            _star_ik_ccd(A, names, tgt, iters=40)
            tip = _star_tip(A, names[2], names[1])
            d = (tip - tgt).length if tip is not None else 999.0
            # sanity: if tip exploded, revert arm keys from rest pose of this frame by skipping keyframe
            if tip is not None and (tip.z > 2.5 or tip.z < -0.2 or d > 2.0):
                # do not keyframe broken IK; keep original pose
                avisos.append(f"IK revertido frame {f} d={d:.2f} (explosion)")
                A.location = _base_loc
                A.keyframe_insert('location', frame=f)
                _ds.append(d)
                continue
            _ds.append(d)
            for bn in names[:2]:
                pb = A.pose.bones.get(bn)
                if pb is None: continue
                pb.keyframe_insert('rotation_quaternion', frame=f)
            A.keyframe_insert('location', frame=f)
        dmin = min(_ds) if _ds else 999.0
        dmed = (sum(_ds)/len(_ds)) if _ds else 999.0
        # filter exploded frames for ok_3cm using best non-exploded
        _ds_ok = [x for x in _ds if x < 2.0]
        dmin_r = min(_ds_ok) if _ds_ok else dmin
        dmed_r = (sum(_ds_ok)/len(_ds_ok)) if _ds_ok else dmed
        _IK_MED['dists'].append({'punto': _pto, 'parte': _parte, 't0': _t0, 't1': _t1,
                                 'd_min_m': round(dmin_r, 4), 'd_med_m': round(dmed_r, 4),
                                 'ok_3cm': bool(dmin_r <= _dmax)})
        if dmin_r <= _dmax:
            _IK_MED['ok'].append(f"{_parte}->{_pto} dmin={dmin_r:.3f}")
            avisos.append(f"IK OK {_parte}->{_pto} t={_t0}-{_t1} dmin={dmin_r:.3f}m")
        else:
            msg = f"IK parcial {_parte}->{_pto} dmin={dmin_r:.3f}m (objetivo <={_dmax}m) FALTA"
            avisos.append(msg)
            faltas.append(msg)
    except Exception as _ex:
        faltas.append(f"IK contacto FALTA: {_ex}")
        avisos.append(f"IK contacto FALTA: {_ex}")
avisos.append(f"STAR_IK_CONTACTOS_v1c n={len(E.get('contactos') or [])} ok={len(_IK_MED['ok'])}")

# ---------- STAR_ACCIONES_PUNTOS_v3: canales + IK a punto_actor (universal, sin poses nombradas) ----------
_CANAL_BONE = {
    'torso': 'J_Bip_C_Spine', 'espina': 'J_Bip_C_Spine', 'pecho': 'J_Bip_C_Chest',
    'cabeza': 'J_Bip_C_Head', 'cadera': 'J_Bip_C_Hips',
    'hombro_L': 'J_Bip_L_UpperArm', 'hombro_R': 'J_Bip_R_UpperArm',
    'codo_L': 'J_Bip_L_LowerArm', 'codo_R': 'J_Bip_R_LowerArm',
    'rodilla_L': 'J_Bip_L_LowerLeg', 'rodilla_R': 'J_Bip_R_LowerLeg',
    'mano_L': 'J_Bip_L_Hand', 'mano_R': 'J_Bip_R_Hand',
}
_INCL = {'atras': Vector((0,-1,0.2)), 'adelante': Vector((0,1,0.2)), 'izq': Vector((-1,0,0.1)), 'der': Vector((1,0,0.1))}
_ACC_MED = {'canales': 0, 'ik_actor': 0, 'faltas': []}
for _ac in (E.get('acciones_puntos') or []):
    try:
        _suj = _ac.get('sujeto') or ''
        if not str(_suj).startswith('ch-'):
            continue
        if _suj not in PERS:
            continue
        A = PERS[_suj].get('A')
        if A is None: continue
        _pto = _ac.get('punto') or ''
        _t0 = float(_ac.get('t_ini') or _ac.get('t0') or 0)
        _t1 = float(_ac.get('t_fin') or _ac.get('t1') or (_t0+0.5))
        _c0 = float(_ac.get('c0') or 0); _c1 = float(_ac.get('c1') or 1)
        _canal = _ac.get('canal'); _valor = _ac.get('valor')
        _dest = _ac.get('destino')
        f0 = max(1, int(round(fr(_t0)))); f1 = min(NF, int(round(fr(_t1))))
        if f1 < f0: continue
        # canal local (inclinacion / subir / flexion / giro)
        if _canal and _pto in _CANAL_BONE:
            bn = _CANAL_BONE[_pto]
            pb = A.pose.bones.get(bn)
            if pb is None:
                _ACC_MED['faltas'].append(f'canal hueso FALTA {_pto}->{bn}'); continue
            pb.rotation_mode = 'QUATERNION'
            for f in range(f0, f1+1):
                u = 0.0 if f1==f0 else (f-f0)/(f1-f0)
                c = _c0 + (_c1-_c0)*u
                c = max(0.0, min(1.0, c))  # clamp hoja
                _ang_lim = None
                if '_ART_LIB' in dir() and _ART_LIB is not None and 'aplicar_limites_canal' in G:
                    c, _ang_lim = G['aplicar_limites_canal'](pb, bn, _canal, c, _ART_LIB)
                sc.frame_set(f); bpy.context.view_layer.update()
                if _canal == 'inclinacion':
                    d = _INCL.get(_valor or 'atras', _INCL['atras'])
                    q = Vector((0,0,1)).rotation_difference(d.normalized())
                    q = Quaternion((1,0,0,0)).slerp(q, min(1.0, max(0.0, c))*0.55)
                    pb.rotation_quaternion = q
                elif _canal == 'subir':
                    # mild raise: rotate upper arm up
                    axis = Vector((1,0,0)) if '_L' in bn else Vector((-1,0,0))
                    ang = math.radians(25.0 * min(1.0, max(0.0, c)))
                    pb.rotation_quaternion = Quaternion(axis, ang)
                elif _canal == 'flexion':
                    axis = Vector((1,0,0))
                    if _ang_lim is not None:
                        ang = abs(_ang_lim)
                    else:
                        ang = math.radians(50.0 * min(1.0, max(0.0, c)))
                    # knees bend backward in local
                    if 'LowerLeg' in bn:
                        axis = Vector((1,0,0))
                        ang = -ang
                    pb.rotation_quaternion = Quaternion(axis, ang)
                elif _canal == 'giro':
                    sign = 1.0 if (_valor or 'der') == 'der' else -1.0
                    ang = math.radians(30.0 * min(1.0, max(0.0, c)) * sign)
                    pb.rotation_quaternion = Quaternion(Vector((0,0,1)), ang)
                else:
                    continue
                pb.keyframe_insert('rotation_quaternion', frame=f)
            _ACC_MED['canales'] += 1
        # IK hacia punto_actor (p.ej. mano → pecho)
        if isinstance(_dest, dict) and _dest.get('punto_actor') and _pto in _HAND_MAP:
            target_bn = _CANAL_BONE.get(_dest['punto_actor'])
            if target_bn is None:
                _ACC_MED['faltas'].append(f'ik punto_actor FALTA {_dest}'); continue
            names = _HAND_MAP[_pto]
            for f in range(f0, f1+1):
                u = 0.0 if f1==f0 else (f-f0)/(f1-f0)
                c = _c0 + (_c1-_c0)*u
                sc.frame_set(f); bpy.context.view_layer.update()
                tb = A.pose.bones.get(target_bn)
                if tb is None: continue
                tgt = A.matrix_world @ tb.head
                # blend toward chest
                tip0 = _star_tip(A, names[2], names[1])
                if tip0 is None: continue
                tgt_b = tip0.lerp(tgt, min(1.0, max(0.0, c)))
                _star_ik_ccd(A, names, tgt_b, iters=30)
                tip = _star_tip(A, names[2], names[1])
                if tip is not None and tip.z < 2.5 and tip.z > -0.2:
                    for bn in names[:2]:
                        pb = A.pose.bones.get(bn)
                        if pb is not None:
                            pb.keyframe_insert('rotation_quaternion', frame=f)
            _ACC_MED['ik_actor'] += 1
    except Exception as _ex:
        _ACC_MED['faltas'].append(f'acciones_puntos FALTA: {_ex}')
        faltas.append(f'acciones_puntos FALTA: {_ex}')
avisos.append(f"STAR_ACCIONES_PUNTOS_v3 canales={_ACC_MED['canales']} ik_actor={_ACC_MED['ik_actor']} faltas={len(_ACC_MED['faltas'])}")
CHK_ACC = _ACC_MED

# Temblor escenario: reaccion rodillas si no vino en acciones (c ∝ amplitud)
for _ev in (E.get('eventos_escenario') or []):
    if (_ev.get('tipo') or '') != 'temblor':
        continue
    _amp = float(_ev.get('amplitud_m') or 0.03)
    _c_ev = float(_ev.get('c1') or _ev.get('c') or min(1.0, _amp/0.05))
    _t0 = float(_ev.get('t0') or 0); _t1 = float(_ev.get('t1') or (_t0+1))
    f0 = max(1, int(round(fr(_t0)))); f1 = min(NF, int(round(fr(_t1))))
    for _aid, _P in PERS.items():
        A = _P.get('A')
        if A is None: continue
        for _kn, _sign in (('J_Bip_L_LowerLeg', -1.0), ('J_Bip_R_LowerLeg', -1.0)):
            pb = A.pose.bones.get(_kn)
            if pb is None: continue
            pb.rotation_mode = 'QUATERNION'
            for f in range(f0, f1+1):
                u = 0.0 if f1==f0 else (f-f0)/(f1-f0)
                c = _c_ev * (0.5 + 0.5*u)
                sc.frame_set(f)
                ang = math.radians(45.0 * c) * _sign
                pb.rotation_quaternion = Quaternion(Vector((1,0,0)), ang)
                pb.keyframe_insert('rotation_quaternion', frame=f)
    avisos.append(f"temblor escenario.temblor c={_c_ev} t={_t0}-{_t1} → rodillas.flexion")


for _ev in (E.get('eventos_escenario') or []):
    if (_ev.get('tipo') or '') != 'temblor':
        continue
    _ar = _ev.get('actor_reaccion')
    if not _ar or _ar not in PERS:
        continue
    try:
        _amp = float(_ev.get('amplitud_m') or 0.03)
        _freq = float(_ev.get('frecuencia_hz') or 5)
        _t0 = float(_ev.get('t0') or 0); _t1 = float(_ev.get('t1') or (_t0+1))
        _root = PERS[_ar]['A'] or PERS[_ar]['root']
        _n = max(2, int(round((_t1-_t0)*FPS)))
        sc.frame_set(int(round(fr(_t0)))); _base = list(_root.location)
        for _i in range(_n+1):
            _u = _i/max(1,_n); _t = _t0 + (_t1-_t0)*_u; _f = int(round(fr(_t)))
            _dx = _amp * math.sin(2*math.pi*_freq*_u)
            _dy = _amp * math.cos(2*math.pi*_freq*_u)
            sc.frame_set(_f)
            _root.location = (_base[0]+_dx, _base[1]+_dy, _base[2])
            _root.keyframe_insert('location', frame=_f)
        avisos.append(f"temblor actor {_ar} amp={_amp} t={_t0}-{_t1}")
    except Exception as _ex:
        avisos.append(f"temblor actor FALTA: {_ex}")

# ---------- corrección automática de pies + chequeos por cuadro ----------
CHK = {'pies': {}, 'choques': {}, 'lado': [], 'oclusion': []}
CHK['acciones_puntos'] = CHK_ACC if 'CHK_ACC' in dir() else {}
def zmin(P): return AP.zmin_malla(objs_visibles(P)) if P['A'] is not None else min((o.matrix_world @ Vector(c)).z for o in P['objs'] for c in o.bound_box)
def mover_z(P, f, dz):
    R = P['A'] or P['root']; R.location.z += dz; R.keyframe_insert('location', index=2, frame=f)
corr = {pid: 0 for pid in TL}
# v3b: no corregir Z en ventanas de sentarse/pararse (pisa el snap a silla.asiento)
_sit_windows = []
for _sb in BEATS:
    if _sb.get('accion') not in ('sentarse', 'pararse'):
        continue
    _a0 = float(_sb['t']); _a1 = _a0 + float(_sb.get('dur') or 0)
    for _fc in (_sb.get('fases_c') or []):
        _a0 = min(_a0, float(_fc['t0'])); _a1 = max(_a1, float(_fc['t1']))
    _sit_windows.append((_a0, _a1, _sb.get('actor')))
def _en_sit(pid, t):
    for a0, a1, act in _sit_windows:
        if act and act != pid: continue
        if a0 - 1e-6 <= t <= a1 + 1e-6: return True
    return False
for f in range(1, NF + 1):
    sc.frame_set(f); _tcorr = (f - 1) / FPS
    for pid in TL:
        if _en_sit(pid, _tcorr):
            continue  # asiento manda
        P = PERS[pid]; R = P['A'] or P['root']; x, y = R.matrix_world.translation.x, R.matrix_world.translation.y
        fz, _ = piso(x, y, R.matrix_world.translation.z + 2.5); d = zmin(P) - (fz + LEV_OFF.get(pid, 0))
        if abs(d) > 0.01: mover_z(P, f, -d); corr[pid] += 1
CHK['correcciones_auto_de_pies'] = corr
avisos.append(f"v3b skip_corr_pies_en_sit windows={_sit_windows}")
# v6: pegar pie (hueso Foot) al piso en de_pie quieto si flota 0.12–0.28 m (antes/después documentado)
_pie_peg = {pid: 0 for pid in TL}
def _pose_en_tmp(K, t):
    i = max([j for j, k in enumerate(K) if k[0] <= t + 1e-6] or [0]); k = K[i]
    quieta = i == len(K) - 1 or K[i + 1][3] == k[3] or abs(t - k[0]) < 1e-6
    return k[3], quieta
for f in range(1, NF + 1):
    sc.frame_set(f); t = (f - 1) / FPS
    for pid in TL:
        P = PERS[pid]; A = P.get('A')
        if A is None: continue
        pz, q = _pose_en_tmp(TL[pid], t)
        if (not q) or pz != 'de_pie': continue
        R = A; x, y = R.matrix_world.translation.x, R.matrix_world.translation.y
        fz, _ = piso(x, y, R.matrix_world.translation.z + 2.5); base = fz + LEV_OFF.get(pid, 0)
        zs = []
        for bn in ('J_Bip_L_Foot', 'J_Bip_R_Foot'):
            pb = A.pose.bones.get(bn)
            if pb is None: continue
            W = A.matrix_world
            zs.append(min((W @ pb.head).z, (W @ pb.tail).z) - base)
        if not zs: continue
        d = max(zs)  # el pie más alto (de_pie exige ambos cerca)
        if 0.12 <= d <= 0.28:
            need = d - 0.04
            # no hundir malla: solo bajar lo que la suela permita
            zmesh = zmin(P) - base
            dz = min(need, max(0.0, zmesh + 0.02))
            if dz > 0.005:
                mover_z(P, f, -dz); _pie_peg[pid] += 1
CHK['v6_pegar_pie_de_pie'] = _pie_peg
avisos.append(f"v6pegar_pie: {_pie_peg}")
# ---------- o114 GUARDIA DEL CUERPO: TODOS los cuadros, todos los actores con esqueleto ----------
def pose_en(K, t):
    i = max([j for j, k in enumerate(K) if k[0] <= t + 1e-6] or [0]); k = K[i]
    quieta = i == len(K) - 1 or K[i + 1][3] == k[3] or abs(t - k[0]) < 1e-6   # en transición entre dos poses no se pide contacto
    return k[3], quieta
for f in range(1, NF + 1):
    sc.frame_set(f); t = (f - 1) / FPS
    for pid, g in GUARD.items():
        A = PERS[pid]['A']; x, y = A.matrix_world.translation.x, A.matrix_world.translation.y
        fz, _ = piso(x, y, A.matrix_world.translation.z + 2.5); pz, q = pose_en(TL[pid], t)
        g.revisar(f, pz, fz, quieta=q, elev=LEV_OFF.get(pid, 0))
GFALLAS = [x for g in GUARD.values() for x in g.fallas]
CHK['guardia'] = {'ok': not GFALLAS, 'n_fallas': len(GFALLAS), 'actores': sorted(GUARD), 'cuadros': NF, 'primeras': GFALLAS[:40]}
print('GUARDIA_O114', 'OK' if not GFALLAS else f'RECHAZADA {len(GFALLAS)} fallas; primera: {GFALLAS[0]}')
def tris_mundo(P):
    dg = bpy.context.evaluated_depsgraph_get(); V, F = [], []
    for o in objs_visibles(P) if P['A'] is not None else P['objs']:
        e = o.evaluated_get(dg); m = e.to_mesh(); n = len(V); V += [o.matrix_world @ v.co for v in m.vertices]; F += [tuple(i + n for i in p.vertices) for p in m.polygons]; e.to_mesh_clear()
    return BVHTree.FromPolygons(V, F), V
for f in range(1, NF + 1, 2):
    sc.frame_set(f)
    for pid in TL:
        P = PERS[pid]; zz = zmin(P); R = P['A'] or P['root']; x, y = R.matrix_world.translation.x, R.matrix_world.translation.y
        fz, fn = piso(x, y, R.matrix_world.translation.z + 2.5); d = zz - (fz + LEV_OFF.get(pid, 0))
        if abs(d) > 0.03: CHK['pies'].setdefault(pid, []).append([round((f - 1) / FPS, 2), round(d, 3)])
        if f % 4 == 1:
            bt, V = tris_mundo(P); lo = Vector((min(v.x for v in V), min(v.y for v in V), min(v.z for v in V))); hi = Vector((max(v.x for v in V), max(v.y for v in V), max(v.z for v in V)))
            for n, b in BV.items():
                o = bpy.data.objects[n]; bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
                if n == fn or any(min(c[i] for c in bb) > hi[i] or max(c[i] for c in bb) < lo[i] for i in range(3)): continue
                if bt.overlap(b): CHK['choques'].setdefault(pid, {}).setdefault(n, []).append(round((f - 1) / FPS, 2))
# ---------- cámaras: las del molde + una de vista general automática ----------
from bpy_extras.object_utils import world_to_camera_view as w2c
pts_all = []
for pid in TL:
    for k in TL[pid]: pts_all.append(k[1])
cen = sum(pts_all, Vector()) / max(1, len(pts_all)); rad = max([(p - cen).length for p in pts_all] + [2]) + 2.5
# v3camfix: auto_o113_* u otros nombres ausentes → cámaras reales del molde (cíclico; excluye planta)
_avail = [o.name for o in bpy.data.objects if o.type == 'CAMERA' and 'planta' not in o.name.lower() and 'vista_general' not in o.name.lower()]
if not _avail:
    _avail = [o.name for o in bpy.data.objects if o.type == 'CAMERA' and 'planta' not in o.name.lower()]
_remap_i = 0
for _t in E['tomas']:
    _cm = _t.get('camara_molde')
    if _cm and bpy.data.objects.get(_cm):
        continue
    if not _avail:
        avisos.append(f"toma {_t.get('id')}: sin cámaras en molde para remapear {_cm!r}")
        continue
    _new = _avail[_remap_i % len(_avail)]; _remap_i += 1
    avisos.append(f"v3camfix: toma {_t.get('id')} {_cm!r} → {_new}")
    _t['camara_molde'] = _new
cams_molde = [c for c in dict.fromkeys(t['camara_molde'] for t in E['tomas']) if bpy.data.objects.get(c) and c != 'cam_planta']
# v3: mira centro de acción a altura pecho (~1.2 m); evita plano gris vacío / personaje cortado arriba
look = Vector((cen.x, cen.y, cen.z + 1.2))
if cams_molde:
    c0 = bpy.data.objects[cams_molde[0]].matrix_world.translation
else:
    c0 = cen + Vector((0, -max(4.0, rad), 1.6))
dirv = (c0 - cen); dirv.z = 0; dirv = dirv.normalized() if dirv.length > 1e-3 else Vector((0, -1, 0))
dist_h = min(max(rad * 0.85, 3.5), 7.0)
alt = min(max(rad * 0.55, 1.8), 3.2)
# v3los: probar 4 rumbos (hacia mold-cam, opuesto, y laterales); elegir el más libre hasta look
_side = Vector((-dirv.y, dirv.x, 0))
_cands = []
for _d in (dirv, -dirv, _side, -_side):
    if _d.length < 1e-6: continue
    _d = _d.normalized()
    _cands.append(Vector((cen.x, cen.y, 0)) + _d * dist_h + Vector((0, 0, alt)))
# BVH ambiente para oclusión
_vs, _fs, _n = [], [], 0
for _o in bpy.data.objects:
    if _o.type != 'MESH' or not _o.name.startswith('amb-'): continue
    _m = _o.matrix_world; _me = _o.data
    _vs.extend([_m @ v.co for v in _me.vertices])
    for _p in _me.polygons:
        _fs.append(tuple(i + _n for i in _p.vertices))
    _n = len(_vs)
_bvh = BVHTree.FromPolygons(_vs, _fs) if _fs else None
def _clearance(loc):
    if _bvh is None: return 99.0
    v = look - loc; L = v.length
    if L < 1e-4: return 0.0
    h = _bvh.ray_cast(loc, v.normalized(), L - 0.15)
    if h[0] is None: return L
    return h[1]  # distancia al hit (menor = peor)
_best = max(_cands, key=_clearance)
bpy.ops.object.camera_add(location=_best); ov = bpy.context.object; ov.name = 'cam_vista_general_o111'
ov.rotation_euler = (look - ov.location).to_track_quat('-Z', 'Y').to_euler(); ov.data.lens = 28
# v3aim: cámaras del plan miran al centro de acción (pecho); si están <2.8 m horizontales, se alejan
for _cn in cams_molde:
    _cam = bpy.data.objects.get(_cn)
    if not _cam: continue
    _loc = _cam.matrix_world.translation.copy()
    _dxy = Vector((_loc.x - cen.x, _loc.y - cen.y, 0.0))
    if _dxy.length < 2.8:
        _dir = _dxy.normalized() if _dxy.length > 1e-3 else Vector((0, -1, 0))
        _loc = Vector((cen.x, cen.y, 0)) + _dir * 3.2 + Vector((0, 0, max(_loc.z, 1.35)))
        _cam.location = _loc
    _cam.rotation_euler = (look - _cam.matrix_world.translation).to_track_quat('-Z', 'Y').to_euler()
    if getattr(_cam.data, 'lens', 50) > 40:
        _cam.data.lens = 35  # evita close-up extremo del molde
for t in E['tomas']:
    cam = bpy.data.objects.get(t['camara_molde'])
    if not cam: avisos.append(f"toma {t['id']}: la cámara {t['camara_molde']} no está en el molde"); continue
    for tt in (t['t'][0] + .25, (t['t'][0] + t['t'][1]) / 2, t['t'][1] - .25):
        f = int(round(fr(tt))); sc.frame_set(f)
        for x in (t.get('palabras') or {}).get('por_personaje') or []:
            pid = x['id']
            if pid not in PERS: continue
            c = centro_de(pid, f); q = w2c(sc, cam, c); u = q.x
            lado = 'izquierda' if u < .38 else 'derecha' if u > .62 else 'centro'
            ok = lado == x.get('lado_pantalla') ; suave = not ({lado, x.get('lado_pantalla')} == {'izquierda', 'derecha'})
            CHK['lado'].append({'toma': t['id'], 'seg': round(tt, 2), 'actor': pid, 'palabras': x.get('lado_pantalla'), 'blender': lado, 'u': round(u, 3), 'igual': ok, 'sin_cruce': suave and q.z > 0})
            if pid in ACOP: continue
            P = PERS[pid]; A = P['A']
            mues = [A.matrix_world @ A.pose.bones[n].head for n in ('J_Bip_C_Head', 'J_Bip_C_UpperChest', 'J_Bip_C_Hips', 'J_Bip_L_Hand', 'J_Bip_R_Hand')] if A is not None else [P['root'].matrix_world.translation + Vector((0, 0, ALT[pid] * k)) for k in (.2, .5, .9)]
            co = cam.matrix_world.translation; tap = []
            for m in mues:
                v = m - co; dist = v.length
                for n, b in BV.items():
                    h = b.ray_cast(co, v.normalized(), dist - .05)
                    if h[0] is not None: tap.append(n); break
            if tt == (t['t'][0] + t['t'][1]) / 2: CHK['oclusion'].append({'toma': t['id'], 'actor': pid, 'tapado': round(len(tap) / len(mues), 2), 'por': sorted(set(tap))})

# ---------- v5encuadre: QC + variedad (≥2 cams distintas, ángulo≥25° / tipo plano) ----------
_enc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else E.get('_motor_src') or '.', 'encuadre_cams_v4.py')
if not os.path.isfile(_enc_path):
    for _cand in (
        os.path.join(os.environ.get('STAR_MOTOR_SRC', ''), 'encuadre_cams_v4.py'),
        '/workspace/STAR_MOTOR_UNIVERSAL_v6_20261031/src/encuadre_cams_v4.py',
    ):
        if _cand and os.path.isfile(_cand):
            _enc_path = _cand; break
_enc_ns = {'__name__': 'encuadre_cams_v4'}
with open(_enc_path, 'r', encoding='utf-8') as _ef:
    exec(compile(_ef.read(), _enc_path, 'exec'), _enc_ns)
_eval_cam = _enc_ns['evaluar_camara']
_crear_cam = _enc_ns['crear_camara_encuadre']
_crear_vg = _enc_ns.get('crear_camara_vista_general') or _crear_cam
_tiempos_m = _enc_ns['tiempos_muestra']
_bvh_amb = _enc_ns['_bvh_ambiente']
_cams_distintas = _enc_ns['cams_suficientemente_distintas']
_sig_tipo = _enc_ns['siguiente_tipo']
_beats_e = (E.get('eventos') or {}).get('beats') or []
_tiempos = _tiempos_m(E, _beats_e)
bpy.context.view_layer.update()
_bvh_e = _bvh_amb(bpy, PERS)
CHK['encuadre_v4'] = {'tiempos': _tiempos, 'cams': {}, 'reemplazos': [], 'variedad': []}
_new_cams = []
_rep_i = 0
_tipos_ok = []

def _obj(nm):
    return bpy.data.objects.get(nm)

def _registrar(nm, r, **extra):
    CHK['encuadre_v4']['cams'][nm] = {'ok': r['ok'], 'ratio': r['ratio'], 'tipo': r.get('tipo'),
                                      'alto_med': r.get('alto_med'), **extra,
                                      'muestras': [{'t': m['t'], 'ok': m['ok'], 'n_ok': m['n_ok'],
                                                    'alto_max': m.get('alto_max'), 'pitch': m.get('pitch'),
                                                    'tipo': m.get('tipo')} for m in r.get('muestras') or []]}

def _avoid_objs(nombres):
    return [o for o in (_obj(n) for n in nombres) if o is not None]

for _cn in list(cams_molde):
    _cam = _obj(_cn)
    if not _cam:
        continue
    bpy.context.view_layer.update()
    _r = _eval_cam(sc, _cam, PERS, ALT, ACOP, w2c, fr, _tiempos, bvh=_bvh_e, bpy=bpy)
    _registrar(_cn, _r)
    if _r['ok']:
        # ¿demasiado parecida a una ya aceptada?
        _dup = False
        for _prev in _new_cams:
            _po = _obj(_prev)
            if _po and not _cams_distintas(_cam, _po):
                _dup = True
                avisos.append(f"v5encuadre: {_cn} ok pero ~idéntica a {_prev} (ángulo<25°) → se omite del set")
                CHK['encuadre_v4']['variedad'].append({'omitida': _cn, 'cerca_de': _prev})
                break
        if not _dup:
            _new_cams.append(_cn)
            if _r.get('tipo'):
                _tipos_ok.append(_r['tipo'])
        continue
    # falla → crear auto con tipo distinto y ángulo lejos de las ya buenas
    _rep_i += 1
    _pref = _sig_tipo(_tipos_ok)
    _nn = f'auto_v4_encuadre_{_rep_i}'
    avisos.append(f"v5encuadre: {_cn} falla (ratio={_r['ratio']}) → {_nn} tipo={_pref}")
    _nc = _crear_cam(bpy, Vector, BVHTree, __import__('math'), sc, PERS, ALT, ACOP, w2c, fr, _tiempos, _nn,
                     bvh=_bvh_e, avoid_cams=_avoid_objs(_new_cams), prefer_tipo=_pref)
    if _nc is None:
        avisos.append(f"v5encuadre: no se pudo crear reemplazo para {_cn}; se mantiene (fuera de ok/avoid)")
        # v2c: NO meter cams fallidas en _new_cams — contaminaban 180°/ángulo y hacían
        # reemplazar un VG bueno por "duplicada_angulo" contra una cam a la pared.
        continue
    for _t in E['tomas']:
        if _t.get('camara_molde') == _cn:
            _t['camara_molde'] = _nc.name
    CHK['encuadre_v4']['reemplazos'].append({'de': _cn, 'a': _nc.name, 'ratio_prev': _r['ratio'], 'tipo': _pref})
    _r2 = _eval_cam(sc, _nc, PERS, ALT, ACOP, w2c, fr, _tiempos, bvh=_bvh_e, bpy=bpy)
    _registrar(_nc.name, _r2, reemplazo_de=_cn)
    if not _r2['ok']:
        avisos.append(f"v5encuadre: {_nc.name} aún débil (ratio={_r2['ratio']}); se usa igual")
    _new_cams.append(_nc.name)
    if _r2.get('tipo'):
        _tipos_ok.append(_r2['tipo'])

cams_molde = list(dict.fromkeys(_new_cams))

# vista general: si falla O si es casi idéntica a alguna del plan → reemplazar con tipo distinto
_r_vg = _eval_cam(sc, ov, PERS, ALT, ACOP, w2c, fr, _tiempos, bvh=_bvh_e, bpy=bpy, require_all=True)
_registrar(ov.name, _r_vg, require_all=True)
_vg_dup = False
# v2c: solo comparar ángulo contra cams que PASARON QC (no contra fallidas)
_ok_para_dup = [nm for nm in cams_molde if (CHK['encuadre_v4']['cams'].get(nm) or {}).get('ok')]
for _prev in _ok_para_dup:
    _po = _obj(_prev)
    if _po and not _cams_distintas(ov, _po):
        _vg_dup = True
        break
# v2c: SIEMPRE intentar VG nueva (o111 geométrico mentía a través de muros).
# Conservar original solo si original ok CON los (ratio) y nuevo no mejora.
_rep_i += 1
_nn = 'auto_v4_encuadre_vg'
_motivo = 'falla' if not _r_vg['ok'] else ('duplicada_angulo' if _vg_dup else 'probar_mejor_los')
avisos.append(f"v2encuadre: {ov.name} {_motivo} → {_nn} tipo=general (trayectoria+LOS)")
_nc = _crear_vg(bpy, Vector, BVHTree, __import__('math'), sc, PERS, ALT, ACOP, w2c, fr, _tiempos, _nn,
                bvh=_bvh_e, avoid_cams=_avoid_objs(cams_molde))
if _nc is not None:
    _r_vg2 = _eval_cam(sc, _nc, PERS, ALT, ACOP, w2c, fr, _tiempos, bvh=_bvh_e, bpy=bpy, require_all=True)
    _orig_ok = bool(_r_vg.get('ok'))
    _new_ok = bool(_r_vg2.get('ok'))
    _orig_r = float(_r_vg.get('ratio') or 0)
    _new_r = float(_r_vg2.get('ratio') or 0)
    _usar_nueva = False
    if _new_ok and (not _orig_ok):
        _usar_nueva = True
    elif _new_ok and _new_r + 0.02 >= _orig_r:
        _usar_nueva = True
    elif (not _orig_ok) and _new_r > _orig_r:
        _usar_nueva = True
    if _usar_nueva:
        try: bpy.data.objects.remove(ov, do_unlink=True)
        except Exception: pass
        ov = _nc
        _registrar(ov.name, _r_vg2, reemplazo_de='cam_vista_general_o111', require_all=True)
        CHK['encuadre_v4']['reemplazos'].append({'de': 'cam_vista_general_o111', 'a': ov.name, 'motivo': _motivo, 'tipo': 'general'})
        if _r_vg2.get('ok') and _r_vg2.get('tipo'):
            _tipos_ok.append(_r_vg2['tipo'])
    else:
        avisos.append(f"v2encuadre: {_nn} no mejora (r={_new_r:.2f} vs {_orig_r:.2f} ok={_new_ok}/{_orig_ok}) → se conserva {ov.name}")
        try: bpy.data.objects.remove(_nc, do_unlink=True)
        except Exception: pass
        if _r_vg.get('tipo'):
            _tipos_ok.append(_r_vg['tipo'])
elif _r_vg.get('ok'):
    if _r_vg.get('tipo'):
        _tipos_ok.append(_r_vg['tipo'])
    avisos.append(f"v2encuadre: no se pudo crear {_nn}; se conserva {ov.name} (ok={_r_vg.get('ok')})")
else:
    avisos.append(f"v2encuadre: {_nn} no creada y original falla ratio={_r_vg.get('ratio')}")

# garantizar ≥2 cámaras distintas que pasen QC (plan + vg cuentan)
def _ok_names():
    out = []
    for nm in list(cams_molde) + [ov.name]:
        info = CHK['encuadre_v4']['cams'].get(nm) or {}
        if info.get('ok') and nm not in out:
            out.append(nm)
    return out

_ok = _ok_names()
# filtrar pares casi idénticos en ok set
_ok_filt = []
for nm in _ok:
    o = _obj(nm)
    if o is None:
        continue
    if any(not _cams_distintas(o, _obj(p)) for p in _ok_filt if _obj(p)):
        avisos.append(f"v5encuadre: {nm} casi idéntica a una ok previa → fuera del cupo variedad")
        continue
    _ok_filt.append(nm)
_ok = _ok_filt

_intentos_var = 0
while len(_ok) < 2 and _intentos_var < 3:
    _intentos_var += 1
    _rep_i += 1
    _pref = _sig_tipo(_tipos_ok)
    _nn = f'auto_v4_encuadre_var{_intentos_var}'
    avisos.append(f"v5encuadre: solo {len(_ok)} cam(s) ok distintas → crea {_nn} tipo={_pref}")
    _nc = _crear_cam(bpy, Vector, BVHTree, __import__('math'), sc, PERS, ALT, ACOP, w2c, fr, _tiempos, _nn,
                     bvh=_bvh_e, avoid_cams=_avoid_objs(_ok), prefer_tipo=_pref)
    if _nc is None:
        break
    _rv = _eval_cam(sc, _nc, PERS, ALT, ACOP, w2c, fr, _tiempos, bvh=_bvh_e, bpy=bpy)
    _registrar(_nc.name, _rv, variedad=True)
    CHK['encuadre_v4']['variedad'].append({'creada': _nc.name, 'ok': _rv['ok'], 'tipo': _rv.get('tipo')})
    if _nc.name not in cams_molde:
        cams_molde.append(_nc.name)
        # asignar a alguna toma si hace falta
        if E.get('tomas'):
            # mitad de tomas al nuevo si había solo 1 cam
            if len(_ok) == 1:
                for _i, _t in enumerate(E['tomas']):
                    if _i % 2 == 1:
                        _t['camara_molde'] = _nc.name
    if _rv['ok']:
        _ok.append(_nc.name)
        if _rv.get('tipo'):
            _tipos_ok.append(_rv['tipo'])
    else:
        avisos.append(f"v5encuadre: {_nc.name} no pasó QC; se deja igual para no vaciar")
        if _nc.name not in _ok:
            _ok.append(_nc.name)  # cuenta para no loop infinito visual

if not cams_molde:
    _rep_i += 1
    _nn = f'auto_v4_encuadre_{_rep_i}'
    _nc = _crear_cam(bpy, Vector, BVHTree, __import__('math'), sc, PERS, ALT, ACOP, w2c, fr, _tiempos, _nn,
                     bvh=_bvh_e, prefer_tipo='medio')
    if _nc is not None:
        for _t in E['tomas']:
            _t['camara_molde'] = _nc.name
        cams_molde = [_nc.name]
        avisos.append(f"v5encuadre: ninguna del plan servía → única {_nc.name}")

CHK['encuadre_v4']['ok_distintas'] = _ok
CHK['encuadre_v4']['tipos'] = list(_tipos_ok)

# v6: cámaras para clusters secundarios (p.ej. ch-jirafa a >4.5 m del grupo humano)
_pids_clusters = _enc_ns.get('pids_clusters')
CHK['encuadre_v4']['clusters'] = []
if callable(_pids_clusters):
    _cls = _pids_clusters(PERS, ALT, ACOP, max_spread=4.5)
    CHK['encuadre_v4']['clusters'] = [list(c) for c in _cls]
    avisos.append(f"v6clusters: {_cls}")
    _primary = set(_cls[0]) if _cls else set()
    _sec_i = 0
    for _ci, _cl in enumerate(_cls[1:] if len(_cls) > 1 else []):
        if not _cl:
            continue
        for _pref in ('general', 'medio'):
            _sec_i += 1
            _nn = f'auto_v6_cast_{_sec_i}'
            avisos.append(f"v6cast: cluster{_ci+2} {_cl} → {_nn} tipo={_pref}")
            _nc = _crear_cam(bpy, Vector, BVHTree, __import__('math'), sc, PERS, ALT, ACOP, w2c, fr, _tiempos, _nn,
                             bvh=_bvh_e, avoid_cams=_avoid_objs(list(cams_molde) + [ov.name] + _ok),
                             prefer_tipo=_pref, pids_override=list(_cl))
            if _nc is None:
                avisos.append(f"v6cast: no se pudo crear {_nn} para {_cl}")
                continue
            _rv = _eval_cam(sc, _nc, PERS, ALT, ACOP, w2c, fr, _tiempos, bvh=_bvh_e, bpy=bpy)
            # re-eval con pids del cluster: medir_frame acepta pids
            try:
                _mids = _enc_ns['medir_frame']
                sc.frame_set(int(round(fr(_tiempos[len(_tiempos)//2] if _tiempos else 0.5))))
                _m = _mids(sc, _nc, PERS, ALT, ACOP, w2c, pids=list(_cl), bvh=_bvh_e, bpy=bpy)
                _rv = dict(_rv); _rv['ok'] = bool(_m.get('ok')); _rv['n_ok_cluster'] = _m.get('n_ok'); _rv['alto_cluster'] = _m.get('alto_max')
            except Exception as _ex:
                avisos.append(f"v6cast: medir cluster fallo {_ex}")
            _registrar(_nc.name, _rv, cluster=list(_cl), variedad=True)
            if _nc.name not in cams_molde:
                cams_molde.append(_nc.name)
            # asignar a tomas cuyo en_cuadro intersecta el cluster
            for _t in E.get('tomas') or []:
                _enq = set(((_t.get('palabras') or {}).get('en_cuadro') or []))
                if _enq & set(_cl):
                    # si la toma es SOLO del cluster (sin primary), forzar esta cam
                    if not (_enq & _primary) or _enq <= set(_cl):
                        _t['camara_molde'] = _nc.name
            if _rv.get('ok') and _nc.name not in _ok:
                _ok.append(_nc.name)
            CHK['encuadre_v4']['variedad'].append({'creada': _nc.name, 'cluster': list(_cl), 'ok': _rv.get('ok'), 'tipo': _pref})

    # v6: si alguna toma pide personajes de DOS clusters, cámara ancha con todos esos pids
    _span_pids = set()
    for _t in E.get('tomas') or []:
        _enq = [x for x in ((_t.get('palabras') or {}).get('en_cuadro') or []) if x in PERS and x not in ACOP]
        _hits = set()
        for _ci, _cl in enumerate(_cls):
            if set(_enq) & set(_cl):
                _hits.add(_ci)
        if len(_hits) >= 2:
            _span_pids |= set(_enq)
    if _span_pids:
        for _pref in ('general', 'medio'):
            _sec_i += 1
            _nn = f'auto_v6_cast_{_sec_i}'
            avisos.append(f"v6cast: toma multi-cluster {_span_pids} → {_nn} tipo={_pref}")
            _nc = _crear_cam(bpy, Vector, BVHTree, __import__('math'), sc, PERS, ALT, ACOP, w2c, fr, _tiempos, _nn,
                             bvh=_bvh_e, avoid_cams=_avoid_objs(list(cams_molde) + [ov.name] + _ok),
                             prefer_tipo=_pref, pids_override=sorted(_span_pids))
            if _nc is None:
                avisos.append(f"v6cast: no se pudo crear ancha {_nn}")
                continue
            try:
                _mids = _enc_ns['medir_frame']
                sc.frame_set(int(round(fr(_tiempos[len(_tiempos)//2] if _tiempos else 0.5))))
                _m = _mids(sc, _nc, PERS, ALT, ACOP, w2c, pids=sorted(_span_pids), bvh=_bvh_e, bpy=bpy)
                _rv = {'ok': bool(_m.get('ok')), 'ratio': 1.0 if _m.get('ok') else 0.0, 'tipo': _pref,
                       'alto_med': _m.get('alto_max'), 'muestras': [], 'n_ok_cluster': _m.get('n_ok')}
            except Exception as _ex:
                _rv = {'ok': False, 'ratio': 0.0, 'tipo': _pref, 'alto_med': 0, 'muestras': []}
                avisos.append(f"v6cast ancha medir: {_ex}")
            _registrar(_nc.name, _rv, cluster=sorted(_span_pids), variedad=True)
            if _nc.name not in cams_molde:
                cams_molde.append(_nc.name)
            for _t in E.get('tomas') or []:
                _enq = set(((_t.get('palabras') or {}).get('en_cuadro') or []))
                if len(_enq & _span_pids) >= 2 and (_enq & _primary) and (_enq - _primary):
                    _t['camara_molde'] = _nn
            if _nc.name not in _ok:
                _ok.append(_nc.name)
            CHK['encuadre_v4']['variedad'].append({'creada': _nc.name, 'cluster': sorted(_span_pids), 'ok': _rv.get('ok'), 'tipo': _pref, 'ancha': True})


    # v6: si algún cluster secundario quedó sin cam OK, forzar 2 cams desde el cluster primario
    _fallidos = [x for x in (CHK['encuadre_v4'].get('variedad') or [])
                 if x.get('cluster') and not x.get('ok') and not x.get('ancha')]
    _clust_fail = []
    for _x in _fallidos:
        _cl = tuple(_x['cluster'])
        if _cl not in _clust_fail and _cl and set(_cl) != set(_primary):
            _clust_fail.append(_cl)
    for _cl in _clust_fail:
        # centroides
        def _cen_of(pids_):
            pts_ = []
            for _pid in pids_:
                if _pid not in PERS or _pid in ACOP:
                    continue
                pts_.extend(_enc_ns['puntos_actor'](PERS[_pid], ALT.get(_pid), _pid, ACOP))
            if not pts_:
                return None
            return sum(pts_, Vector()) / len(pts_)
        _c_or = _cen_of(_cl)
        _c_pr = _cen_of(_primary) or _c_or
        if _c_or is None:
            continue
        _dir = Vector((_c_pr.x - _c_or.x, _c_pr.y - _c_or.y, 0.0))
        if _dir.length < 0.3:
            _dir = Vector((0.0, -1.0, 0.0))
        _dir.normalize()
        _h = max(1.0, float(ALT.get(_cl[0], 1.7) or 1.7))
        for _si, (_dist_f, _ez_f, _lens, _tag) in enumerate((
            (2.2, 0.35, 28, 'frente'),
            (1.4, 0.55, 24, '3cuartos'),
        )):
            _sec_i += 1
            _nn = f'auto_v6_orfano_{_sec_i}'
            _dist = max(3.5, _h * _dist_f)
            _loc = Vector((_c_or.x, _c_or.y, 0.0)) + _dir * _dist + Vector((0, 0, _h * _ez_f))
            # lateral offset for 3cuartos
            if _tag == '3cuartos':
                _side = Vector((-_dir.y, _dir.x, 0.0))
                _loc = _loc + _side * (_h * 0.45)
            try:
                _clamp = _enc_ns.get('_clamp_loc')
                _bounds = _enc_ns.get('_set_bounds')
                if callable(_bounds) and callable(_clamp):
                    _loc = _clamp(_loc, _bounds(bpy, PERS))
            except Exception:
                pass
            _look = Vector((_c_or.x, _c_or.y, _c_or.z))
            bpy.ops.object.camera_add(location=_loc)
            _nc = bpy.context.object
            _nc.name = _nn
            _nc.data.lens = _lens
            _nc.rotation_euler = (_look - _loc).to_track_quat('-Z', 'Y').to_euler()
            bpy.context.view_layer.update()
            try:
                _m = _enc_ns['medir_frame'](sc, _nc, PERS, ALT, ACOP, w2c, pids=list(_cl), bvh=_bvh_e, bpy=bpy)
                _rv = {'ok': bool(_m.get('ok')), 'ratio': 1.0 if _m.get('ok') else 0.0,
                       'tipo': 'general', 'alto_med': _m.get('alto_max'), 'muestras': [],
                       'n_ok_cluster': _m.get('n_ok'), 'detalle': _m.get('detalle')}
            except Exception as _ex:
                _rv = {'ok': False, 'ratio': 0.0, 'tipo': 'general', 'alto_med': 0, 'muestras': []}
                avisos.append(f"v6orfano medir: {_ex}")
            avisos.append(f"v6orfano: {_cl} → {_nn} tag={_tag} ok={_rv.get('ok')} alto={_rv.get('alto_med')}")
            _registrar(_nn, _rv, cluster=list(_cl), variedad=True)
            if _nn not in cams_molde:
                cams_molde.append(_nn)
            # asignar a tomas SOLO del orfano
            for _t in E.get('tomas') or []:
                _enq = set(((_t.get('palabras') or {}).get('en_cuadro') or []))
                if _enq and _enq <= set(_cl):
                    _t['camara_molde'] = _nn
            if _rv.get('ok') and _nn not in _ok:
                _ok.append(_nn)
            CHK['encuadre_v4']['variedad'].append({'creada': _nn, 'cluster': list(_cl), 'ok': _rv.get('ok'),
                                                   'tipo': 'general', 'orfano': True, 'tag': _tag})



# v2: filtrar cámaras con tapa/oclusión entre personajes en mayoría de muestras
_ok2 = []
for _nm in list(_ok):
    _info = CHK['encuadre_v4']['cams'].get(_nm) or {}
    _mals = 0
    _tot = 0
    for _mu in _info.get('muestras') or []:
        _tot += 1
        # re-check stored ok flag; detalle no siempre está en muestras resumidas
        if not _mu.get('ok'):
            _mals += 1
    if _tot and _mals / _tot > 0.5 and _nm.startswith('auto_v4_encuadre_') and 'vg' not in _nm:
        avisos.append(f"v2filtro: {_nm} mayoría muestras mal → fuera de ok_distintas")
        continue
    _ok2.append(_nm)
_ok = _ok2
CHK['encuadre_v4']['ok_distintas'] = _ok
# si tras filtro <2, intentar una más lateral
if len(_ok) < 2:
    for _pref in ('medio', 'ots', 'general'):
        _nn = f'auto_v2_extra_{_pref}'
        if _nn in cams_molde or bpy.data.objects.get(_nn):
            continue
        avisos.append(f"v2extra: solo {len(_ok)} ok → {_nn} tipo={_pref}")
        if _pref == 'general':
            _nc = _crear_vg(bpy, Vector, BVHTree, __import__('math'), sc, PERS, ALT, ACOP, w2c, fr, _tiempos, _nn,
                            bvh=_bvh_e, avoid_cams=_avoid_objs(_ok + [ov.name]))
        else:
            _nc = _crear_cam(bpy, Vector, BVHTree, __import__('math'), sc, PERS, ALT, ACOP, w2c, fr, _tiempos, _nn,
                             bvh=_bvh_e, avoid_cams=_avoid_objs(_ok + [ov.name]), prefer_tipo=_pref)
        if _nc is None:
            continue
        _rv = _eval_cam(sc, _nc, PERS, ALT, ACOP, w2c, fr, _tiempos, bvh=_bvh_e, bpy=bpy,
                        require_all=(_pref == 'general'))
        _registrar(_nc.name, _rv, variedad=True, v2extra=True)
        if _nc.name not in cams_molde:
            cams_molde.append(_nc.name)
        CHK['encuadre_v4']['variedad'].append({'creada': _nc.name, 'ok': _rv.get('ok'), 'tipo': _pref, 'v2extra': True})
        if _rv.get('ok'):
            _ok.append(_nc.name)
            if _rv.get('tipo'):
                _tipos_ok.append(_rv['tipo'])
            break
CHK['encuadre_v4']['ok_distintas'] = _ok
print('V2ENCUADRE', CHK['encuadre_v4']['reemplazos'], 'cams_final', cams_molde, '+', ov.name, 'ok_distintas', _ok, 'tipos', _tipos_ok)
try:
    CHK['sentarse'] = CHK_SIT
except NameError:
    CHK['sentarse'] = {'ok_frames': 0, 'bad_frames': 0, 'fallas': [], 'actores': [], 'nota': 'sin ACC_SIT o sin beats'}



# ---------- render ----------
sh = sc.display.shading; sc.render.engine = 'BLENDER_WORKBENCH'; sh.light = 'STUDIO'; sh.color_type = 'OBJECT'; sh.show_shadows = True; sh.show_cavity = True
sc.display.render_aa = 'FXAA'; sh.cavity_type = 'SCREEN'  # o116 item6: 1 pasada en vez de 8
sc.render.resolution_x, sc.render.resolution_y = E.get('res', [480, 270]); sc.render.resolution_percentage = 100

# ---------- v4/v3c: forzar cámaras que VEAN personaje+objetos ----------
# Preferir cam_v4_* de camaras_auto (escritorio/monitores); si no, fallback v3c→silla/actor
_v4_auto = [x for x in (E.get('camaras_auto') or []) if str(x.get('nombre') or '').startswith('cam_v4_')]
if _v4_auto:
    _names = []
    for _x in _v4_auto:
        _cn = _x['nombre']
        _c = bpy.data.objects.get(_cn)
        if _c is None:
            bpy.ops.object.camera_add(location=_x['loc']); _c = bpy.context.object; _c.name = _cn
            _c.data.lens = _x.get('lente_mm', 24)
        else:
            _c.location = Vector(_x['loc'])
            if _x.get('lente_mm'):
                _c.data.lens = _x['lente_mm']
        if _x.get('look_at'):
            _la = Vector(_x['look_at']); _c.rotation_euler = (_la - Vector(_x['loc'])).to_track_quat('-Z', 'Y').to_euler()
        _c.data.clip_start = 0.05; _c.data.clip_end = 50
        _names.append(_cn)
    if _names and E.get('tomas'):
        for _i, _t in enumerate(E['tomas']):
            _t['camara_molde'] = _names[_i % len(_names)]
        avisos.append(f"v4 forzar cams tomas→{_names}")
    cams_molde = [n for n in _names if bpy.data.objects.get(n)]
else:
    _v3c_cams = [o for o in bpy.data.objects if o.type == 'CAMERA' and o.name.startswith('cam_v3c_')]
    _look = None
    _se = bpy.data.objects.get('silla.asiento')
    _act = None
    for _o in bpy.data.objects:
        if _o.type == 'ARMATURE' and 'protagonista' in _o.name.lower():
            _act = _o; break
    if _se is not None:
        _look = _se.matrix_world.translation.copy(); _look.z = max(_look.z, 0.7)
    elif _act is not None:
        _look = _act.matrix_world.translation.copy(); _look.z += 0.9
    if _look is not None:
        _presets = {
            'cam_v3c_front': Vector((_look.x, max(0.6, _look.y - 2.15), 1.05)),
            'cam_v3c_side': Vector((max(0.45, _look.x - 1.0), _look.y + 0.2, 1.0)),
            'cam_v3c_3q': Vector((max(0.5, _look.x - 0.9), max(0.8, _look.y - 1.7), 1.35)),
        }
        for _cn, _loc in _presets.items():
            _c = bpy.data.objects.get(_cn)
            if _c is None:
                bpy.ops.object.camera_add(location=_loc); _c = bpy.context.object; _c.name = _cn; _c.data.lens = 24
                _v3c_cams.append(_c)
            _c.location = _loc
            _c.rotation_euler = (_look - _loc).to_track_quat('-Z', 'Y').to_euler()
            _c.data.clip_start = 0.05; _c.data.clip_end = 50
        _names = [n for n in ('cam_v3c_front', 'cam_v3c_side', 'cam_v3c_3q') if bpy.data.objects.get(n)]
        if _names and E.get('tomas'):
            for _i, _t in enumerate(E['tomas']):
                _t['camara_molde'] = _names[_i % len(_names)]
            avisos.append(f"v3c forzar cams tomas→{_names}")
        cams_molde = [c for c in dict.fromkeys(t['camara_molde'] for t in E.get('tomas') or []) if bpy.data.objects.get(c)]
        if not cams_molde and _names:
            cams_molde = list(_names)
sc.render.image_settings.file_format = 'FFMPEG'; sc.render.ffmpeg.format = 'MPEG4'; sc.render.ffmpeg.codec = 'H264'; sc.render.ffmpeg.constant_rate_factor = 'MEDIUM'
os.makedirs(E['salida_dir'], exist_ok=True); videos = {}
# o116 item6: cámaras en paralelo (procesos blender -b sobre un .blend listo), máx 2 a la vez
import subprocess, time as _t
_bl = os.path.join(E['salida_dir'], '_listo_o116.blend'); bpy.ops.wm.save_as_mainfile(filepath=_bl, compress=False, copy=True)
_N = max(1, min(int(os.environ.get('O116_PROC', '2')), len(cams_molde) + 1)); _cola = list(cams_molde + [ov.name]); _vivos = []
_env = dict(os.environ, LP_NUM_THREADS=str(max(1, (os.cpu_count() or 2) // _N)))
while _cola or _vivos:
    while _cola and len(_vivos) < _N:
        cn = _cola.pop(0); fp = os.path.join(E['salida_dir'], f'{cn}.mp4'); videos[cn] = fp
        ex = f"import bpy;sc=bpy.context.scene;sc.camera=bpy.data.objects[{cn!r}];sc.render.filepath={fp!r};bpy.ops.render.render(animation=True)"
        _vivos.append((cn, subprocess.Popen([bpy.app.binary_path, '-b', _bl, '--python-expr', ex], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=_env)))
    _t.sleep(0.5)
    for x in list(_vivos):
        if x[1].poll() is not None:
            _vivos.remove(x)
            if x[1].returncode != 0 or not os.path.exists(videos[x[0]]): raise SystemExit(f'O116_RENDER_FALLO {x[0]} rc={x[1].returncode}')
try: os.remove(_bl)
except OSError: pass
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(E['salida_dir'], 'escena_animada.blend'), copy=True)
json.dump({'ok': not GFALLAS, 'rechazada_por_guardia': bool(GFALLAS), 'guardia': CHK['guardia'], 'frames': NF, 'fps': FPS, 'videos': videos, 'faltas_pose': faltas, 'avisos': avisos, 'chequeos': CHK, 'ik_contactos': (CHK_IK if "CHK_IK" in dir() else {}),
           'cuerpos': {k: ('acoplado' if k in ACOP else v['tipo']) for k, v in PERS.items()}, 'efectos': sorted(EFX) + [h[1].name for h in HECHOS if h[0] == 'rayo'], 'roturas': [h[1] for h in HECHOS if h[0] == 'roto']},
          open(OUT, 'w'), indent=1, ensure_ascii=False)
print('VIDEO_O111_OK', len(videos))
