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
sys.path.insert(0, E['o110_dir']); import aplicar_pose as AP, universal as UNI, guardia_o114 as GU
LIB = json.load(open(E['poses_lib']))
sc = bpy.context.scene; FPS = int(E.get('fps') or 8); DUR = float(E['duracion_s']); NF = int(round(DUR * FPS)) + 1
sc.render.fps = FPS; sc.frame_start = 1; sc.frame_end = NF
for o in bpy.data.objects:
    if o.type == 'FONT' or o.name.startswith(('marca_', 'flecha_', 'rej_')): o.hide_render = o.hide_viewport = True
for x in E.get('camaras_auto') or []:   # o113: cámaras niveladas auto-generadas por el filtro del 01
    if not bpy.data.objects.get(x['nombre']):
        bpy.ops.object.camera_add(location=x['loc']); c_ = bpy.context.object; c_.name = x['nombre']; c_.data.lens = x.get('lente_mm', 24)
        c_.rotation_euler = Vector(x['dir']).to_track_quat('-Z', 'Y').to_euler()
SET = [o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render]
for o in SET: o.color = (.55, .55, .57, 1)
avisos, faltas = [], []
def fr(t): return 1 + t * FPS
PT = {k: Vector(v) for k, v in (E.get('puntos') or {}).items()}
# ---------- BVH del set (piso, choques, oclusión) ----------
def bvh_de(o):
    dg = bpy.context.evaluated_depsgraph_get(); e = o.evaluated_get(dg); m = e.to_mesh()
    V = [o.matrix_world @ v.co for v in m.vertices]; P = [tuple(p.vertices) for p in m.polygons]; e.to_mesh_clear()
    return BVHTree.FromPolygons(V, P) if P else None
BV = {o.name: bvh_de(o) for o in SET}; BV = {k: v for k, v in BV.items() if v}
def piso(x, y, ztop):
    best = None
    for n, b in BV.items():
        h = b.ray_cast(Vector((x, y, ztop)), Vector((0, 0, -1)), 50)
        if h[0] is not None and (best is None or h[0].z > best[0]): best = (h[0].z, n)
    return best or (0.0, None)
# ---------- personajes ----------
PERS = {}; ALT = {}
for p in E['personajes']:
    h = float(p.get('altura') or 1.7); ALT[p['id']] = h
    if p.get('controles') and G['VRM_OK'] and h >= 0.6:
        try: PERS[p['id']] = G['vrm'](p['id'], h, p['controles'])
        except Exception as ex: print('VRM_FALLO', p['id'], ex); PERS[p['id']] = G['figura_gris'](p['id'], h)
    else: PERS[p['id']] = G['figura_gris'](p['id'], h)
    PERS[p['id']].setdefault('giro_base', 90)
    for o in PERS[p['id']]['objs']: o.color = (.82, .82, .84, 1) if not o.name.startswith('ACC_') else (.1, .95, 1, 1)
for P in PERS.values():   # acc de la pulsera de color vivo; resto gris
    for o in P['objs']:
        if P.get('acc') and o.name == P['acc']: o.color = (.1, .95, 1, 1)
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
            if pp.get('asiento') and pid not in ASIENTOS:   # pose que necesita asiento: el programa pone un cajón-proxy bajo la cadera
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
    o = bpy.data.objects.get(ref); return o.matrix_world.translation.copy() if o else None
EFX = {}; HECHOS = []
def mano(pid, f):
    sc.frame_set(f); A = PERS[pid]['A']
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
# ---------- corrección automática de pies + chequeos por cuadro ----------
CHK = {'pies': {}, 'choques': {}, 'lado': [], 'oclusion': []}
def zmin(P): return AP.zmin_malla(objs_visibles(P)) if P['A'] is not None else min((o.matrix_world @ Vector(c)).z for o in P['objs'] for c in o.bound_box)
def mover_z(P, f, dz):
    R = P['A'] or P['root']; R.location.z += dz; R.keyframe_insert('location', index=2, frame=f)
corr = {pid: 0 for pid in TL}
for f in range(1, NF + 1):
    sc.frame_set(f)
    for pid in TL:
        P = PERS[pid]; R = P['A'] or P['root']; x, y = R.matrix_world.translation.x, R.matrix_world.translation.y
        fz, _ = piso(x, y, R.matrix_world.translation.z + 2.5); d = zmin(P) - (fz + LEV_OFF.get(pid, 0))
        if abs(d) > 0.01: mover_z(P, f, -d); corr[pid] += 1
CHK['correcciones_auto_de_pies'] = corr
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
cams_molde = [c for c in dict.fromkeys(t['camara_molde'] for t in E['tomas']) if bpy.data.objects.get(c)]
c0 = bpy.data.objects[cams_molde[0]].matrix_world.translation if cams_molde else cen + Vector((0, -10, 0))
dirv = (c0 - cen); dirv.z = 0; dirv = dirv.normalized() if dirv.length > 1e-3 else Vector((0, -1, 0))
bpy.ops.object.camera_add(location=cen + dirv * rad * 0.9 + Vector((0, 0, rad * 1.5))); ov = bpy.context.object; ov.name = 'cam_vista_general_o111'
ov.rotation_euler = (cen - ov.location).to_track_quat('-Z', 'Y').to_euler(); ov.data.lens = 24
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
# ---------- render ----------
sh = sc.display.shading; sc.render.engine = 'BLENDER_WORKBENCH'; sh.light = 'STUDIO'; sh.color_type = 'OBJECT'; sh.show_shadows = True; sh.show_cavity = True
sc.render.resolution_x, sc.render.resolution_y = E.get('res', [480, 270]); sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'FFMPEG'; sc.render.ffmpeg.format = 'MPEG4'; sc.render.ffmpeg.codec = 'H264'; sc.render.ffmpeg.constant_rate_factor = 'MEDIUM'
os.makedirs(E['salida_dir'], exist_ok=True); videos = {}
for cn in cams_molde + [ov.name]:
    sc.camera = bpy.data.objects[cn]; sc.render.filepath = os.path.join(E['salida_dir'], f'{cn}.mp4'); bpy.ops.render.render(animation=True); videos[cn] = sc.render.filepath
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(E['salida_dir'], 'escena_animada.blend'), copy=True)
json.dump({'ok': not GFALLAS, 'rechazada_por_guardia': bool(GFALLAS), 'guardia': CHK['guardia'], 'frames': NF, 'fps': FPS, 'videos': videos, 'faltas_pose': faltas, 'avisos': avisos, 'chequeos': CHK,
           'cuerpos': {k: ('acoplado' if k in ACOP else v['tipo']) for k, v in PERS.items()}, 'efectos': sorted(EFX) + [h[1].name for h in HECHOS if h[0] == 'rayo'], 'roturas': [h[1] for h in HECHOS if h[0] == 'roto']},
          open(OUT, 'w'), indent=1, ensure_ascii=False)
print('VIDEO_O111_OK', len(videos))
