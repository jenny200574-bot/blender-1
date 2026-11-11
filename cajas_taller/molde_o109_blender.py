# PISTA INMI (2026-10-30): orden 109 — cubo 02: arma el MOLDE 3D de cada toma desde la salida del cubo 01 (genérico: cualquier canal,
# set y personaje; nada de nombres fijos). Corre dentro de Blender con el molde.blend del escenario abierto:
#   blender -b molde.blend --factory-startup -P molde_o109_blender.py -- entrada.json salida.json
# Personaje con parametros_3d → cuerpo VRM base + parámetros (escala de huesos, colores, accesorios pegados a huesos; o105–o108).
# Personaje sin parámetros → figura gris simple a su altura. Cámara = la del molde que eligió el 01 (nunca otra).
# Por toma: render «gris» y render «color» (Workbench) + medidas (lado de la pantalla, frente/espalda, alto en pantalla, lado del accesorio).
import bpy, json, math, os, sys
from mathutils import Vector, Matrix, Quaternion
from bpy_extras.object_utils import world_to_camera_view as w2c
A_ = sys.argv[sys.argv.index('--') + 1:]; E = json.load(open(A_[0])); OUT = A_[1]
sc = bpy.context.scene
for o in bpy.data.objects:   # marcas del plano del molde (no son parte del set)
    if o.name.startswith(('marca_', 'flecha_', 'rej_')): o.hide_render = True; o.hide_viewport = True
def CC(v): return (float(v[0]), float(v[1]), float(v[2]), 1.0)
VRM_OK = False
if E.get('addons_dir'):
    try:
        import addon_utils; sys.path.insert(0, E['addons_dir']); addon_utils.enable(E.get('addon', 'VRM_Addon_for_Blender-release'), default_set=True); VRM_OK = True
    except Exception as ex: print('VRM_ADDON_FALLO', ex)
PERS = {}
def hw(A, n): return A.matrix_world @ A.data.bones[n].head_local
def figura_gris(pid, h):
    bpy.ops.object.empty_add(location=(0, 0, 0)); root = bpy.context.object; root.name = f'P_{pid}'
    r = max(0.05, h * 0.13)
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h * 0.62, location=(0, 0, h * 0.31 + h * 0.08)); c = bpy.context.object; c.parent = root
    bpy.ops.mesh.primitive_uv_sphere_add(radius=h * 0.09, location=(0, 0, h * 0.9)); s = bpy.context.object; s.parent = root
    bpy.ops.mesh.primitive_cone_add(radius1=h * 0.03, depth=h * 0.08, location=(0, -h * 0.1, h * 0.9), rotation=(math.radians(90), 0, 0)); n = bpy.context.object; n.parent = root  # nariz = hacia dónde mira
    for o in (c, s, n): o.color = CC([.55, .55, .58])
    return {'root': root, 'objs': [c, s, n], 'tipo': 'figura_gris', 'A': None}
def vrm(pid, h, K):
    antes = set(bpy.data.objects.keys()); eng = sc.render.engine; sc.render.engine = 'BLENDER_EEVEE_NEXT'
    bpy.ops.import_scene.vrm(filepath=E['vrm_base']); sc.render.engine = eng
    A = [o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name not in antes][0]; A.name = f'VRM_{pid}'
    for o in [o for o in bpy.data.objects if o.name not in antes]:
        if o.type == 'MESH' and (o.name.startswith('Body') or o.name.startswith('Face')) and len(o.data.materials) > 1:
            bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
            bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.separate(type='MATERIAL'); bpy.ops.object.mode_set(mode='OBJECT')
    nuevos = [o for o in bpy.data.objects if o.name not in antes]
    col = lambda k, d: K.get('colores.' + k) or d
    for o in nuevos:
        if o.type != 'MESH': continue
        m = (o.data.materials[0].name if o.data.materials else '').lower()
        k = 'pelo' if 'hair' in m else 'ropa_superior' if 'tops' in m else 'ropa_inferior' if 'bottoms' in m else 'zapatos' if 'shoes' in m else 'ojos' if 'eyeiris' in m else 'cara' if ('face' in o.name.lower() or '_face' in m or '_eye' in m) else 'piel'
        o.color = CC(col(k, col('piel', [.8, .7, .6]) if k != 'ojos' else [.15, .12, .1]))
        if k == 'cara' and o.data.shape_keys and K.get('expresion'):
            for kb in o.data.shape_keys.key_blocks:
                if kb.name.endswith('Fcl_ALL_' + str(K['expresion'])): kb.value = float(K.get('expresion_valor', 1.0))
        if k == 'pelo' and K.get('ocultar_pelo_base'): o.hide_render = True
    pb = A.pose.bones; g = K.get('gordura') or {}
    bpy.context.view_layer.objects.active = A; bpy.ops.object.mode_set(mode='EDIT')
    for n in ('J_Bip_C_Neck', 'J_Bip_L_Shoulder', 'J_Bip_R_Shoulder', 'J_Bip_L_UpperLeg', 'J_Bip_R_UpperLeg', 'J_Bip_L_Hand', 'J_Bip_R_Hand', 'J_Bip_L_Foot', 'J_Bip_R_Foot'):
        if n in A.data.edit_bones: A.data.edit_bones[n].inherit_scale = 'NONE'
    bpy.ops.object.mode_set(mode='OBJECT')
    for n, k in (('J_Bip_C_Spine', 'torso'), ('J_Bip_C_Hips', 'cadera'), ('J_Bip_L_UpperLeg', 'piernas'), ('J_Bip_R_UpperLeg', 'piernas'), ('J_Bip_L_UpperArm', 'brazos'), ('J_Bip_R_UpperArm', 'brazos'), ('J_Bip_C_Head', 'cara')):
        f = float(g.get(k, 1.0)); pb[n].scale = (f, 1, f)
    ACC = []; H = hw(A, 'J_Bip_C_Head')
    def pieza(o, hueso, c): o.color = CC(c); ACC.append((o, hueso))
    if K.get('gafas'):
        for sx in (-1, 1):
            bpy.ops.mesh.primitive_torus_add(major_radius=.028, minor_radius=.005, location=(H.x + sx * .033, H.y - .105, H.z + .065), rotation=(math.radians(90), 0, 0))
            o = bpy.context.object; o.scale = (1.15, 1, .8); pieza(o, 'J_Bip_C_Head', K.get('gafas_color') or [.02, .02, .02])
    pu = K.get('pulsera'); ACCN = None
    if isinstance(pu, dict):
        lado = 'L' if pu.get('muneca') == 'izquierda' else 'R'; w_ = hw(A, f'J_Bip_{lado}_Hand')
        bpy.ops.mesh.primitive_torus_add(major_radius=.042, minor_radius=.013, location=(w_.x - (.03 if lado == 'L' else -.03), w_.y, w_.z), rotation=(0, math.radians(90), 0))
        o = bpy.context.object; o.name = f'ACC_{pid}_muneca'; ACCN = o.name; pieza(o, f'J_Bip_{lado}_LowerArm', pu.get('color') or [.05, .95, 1])
    oe = K.get('orejas_puntiagudas')
    if isinstance(oe, dict):
        for sx in (-1, 1):
            bpy.ops.mesh.primitive_cone_add(radius1=.025, radius2=0, depth=float(oe.get('largo_m', .09)), location=(H.x + sx * .085, H.y, H.z + .08), rotation=(0, sx * math.radians(70), 0))
            pieza(bpy.context.object, 'J_Bip_C_Head', col('piel', [.8, .7, .6]))
    pl = K.get('pelo_largo')
    if isinstance(pl, dict):
        Ls = float(pl.get('largo_m', .7)); c_ = pl.get('color') or col('pelo', [.1, .1, .1])
        bpy.ops.mesh.primitive_cone_add(radius1=.13, radius2=.06, depth=Ls, location=(H.x, H.y + .09, H.z + .14 - Ls / 2), vertices=24); o = bpy.context.object; o.scale = (1, .45, 1); pieza(o, 'J_Bip_C_Head', c_)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=.115, location=(H.x, H.y + .06, H.z + .13)); o = bpy.context.object; o.scale = (1.02, .85, 1.0); pieza(o, 'J_Bip_C_Head', c_)
    nu = K.get('nucleo_pecho')
    if isinstance(nu, dict):
        ch = hw(A, 'J_Bip_C_UpperChest'); bpy.ops.mesh.primitive_ico_sphere_add(radius=float(nu.get('radio_m', .045)), location=(ch.x, ch.y - .17, ch.z), subdivisions=1)
        o = bpy.context.object; o.scale = (1, .4, 1.4); pieza(o, 'J_Bip_C_UpperChest', nu.get('color') or [.1, .7, 1])
    ar = K.get('armadura')
    if isinstance(ar, dict):
        for n, r, _l in (('J_Bip_C_Chest', .17, .32), ('J_Bip_L_UpperArm', .055, .24), ('J_Bip_R_UpperArm', .055, .24), ('J_Bip_L_LowerArm', .05, .22), ('J_Bip_R_LowerArm', .05, .22),
                         ('J_Bip_L_UpperLeg', .08, .38), ('J_Bip_R_UpperLeg', .08, .38), ('J_Bip_L_LowerLeg', .065, .38), ('J_Bip_R_LowerLeg', .065, .38)):
            b = A.data.bones[n]; a = A.matrix_world @ b.head_local; t = A.matrix_world @ b.tail_local
            if n == 'J_Bip_C_Chest': a = hw(A, 'J_Bip_C_Spine'); t = hw(A, 'J_Bip_C_Neck') - Vector((0, 0, .03))
            bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=(t - a).length * 1.02, location=(a + t) / 2, vertices=12)
            o = bpy.context.object; o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(t - a); pieza(o, n, ar.get('color') or [.05, .05, .07])
    ca = K.get('capa')
    if isinstance(ca, dict):
        nk = hw(A, 'J_Bip_C_UpperChest'); Lc = float(ca.get('largo_m', 1.2))
        bpy.ops.mesh.primitive_grid_add(x_subdivisions=10, y_subdivisions=12, size=1, location=(nk.x, nk.y + .16, nk.z + .08 - Lc / 2), rotation=(math.radians(90), 0, 0))
        o = bpy.context.object; o.scale = (.55, Lc, 1); o.modifiers.new('s', 'SOLIDIFY').thickness = .01; pieza(o, 'J_Bip_C_UpperChest', ca.get('color') or [.05, .05, .07])
    bpy.context.view_layer.update()
    for o, hb in ACC:
        mw = o.matrix_world.copy(); o.parent = A; o.parent_type = 'BONE'; o.parent_bone = hb; bpy.context.view_layer.update(); o.matrix_world = mw
    # brazos abajo (pose de pie): giro del brazo alrededor del eje frente-atrás del cuerpo
    for n, ang in (('J_Bip_L_UpperArm', 70), ('J_Bip_R_UpperArm', -70)):
        b = A.data.bones[n]; R = Matrix.Rotation(math.radians(ang), 3, 'Y'); Mb = b.matrix_local.to_3x3()
        pb[n].rotation_mode = 'QUATERNION'; pb[n].rotation_quaternion = (Mb.inverted() @ R @ Mb).to_quaternion()
    bpy.context.view_layer.update()
    zs = [(o.matrix_world @ Vector(cc)).z for o in nuevos if o.type == 'MESH' and not o.hide_render for cc in o.bound_box]
    alto0 = max(zs) - min(zs) if zs else 1.6
    root = A; s = h / alto0 if alto0 > 0.1 else 1.0; root.scale = (s, s, s)
    return {'root': root, 'objs': [o for o in nuevos if o.type == 'MESH'] + [o for o, _ in ACC], 'tipo': 'vrm_parametros', 'A': A, 'acc': ACCN,
            'muneca_acc': ('L' if isinstance(pu, dict) and pu.get('muneca') == 'izquierda' else 'R') if isinstance(pu, dict) else None, 'giro_base': 90}
for p in E['personajes']:
    h = float(p.get('altura') or 1.7)
    if p.get('controles') and VRM_OK and h >= 0.6:
        try: PERS[p['id']] = vrm(p['id'], h, p['controles'])
        except Exception as ex: print('VRM_FALLO', p['id'], ex); PERS[p['id']] = figura_gris(p['id'], h)
    else: PERS[p['id']] = figura_gris(p['id'], h)
    PERS[p['id']].setdefault('giro_base', 90)   # el cuerpo base mira a -Y: rot 0 del 01 (= mirar a +X) es girar +90
sh = sc.display.shading; sc.render.engine = 'BLENDER_WORKBENCH'; sh.light = 'STUDIO'; sh.show_shadows = True; sh.show_cavity = True
sc.render.resolution_x, sc.render.resolution_y = E.get('res', [960, 540]); sc.render.image_settings.file_format = 'PNG'
def uv(cam, p): q = w2c(sc, cam, p); return [round(q.x, 3), round(1 - q.y, 3), q.z > 0]
med = {}
for t in E['tomas']:
    cam = bpy.data.objects.get(t['camara_molde'])
    if not cam or cam.type != 'CAMERA': med[t['id']] = {'error': f"no existe la cámara {t['camara_molde']} en el molde"}; continue
    sc.camera = cam; vis = {}
    for pid, P in PERS.items():
        st = (t.get('estados') or {}).get(pid)
        oculto = not st or pid not in (t.get('en_cuadro') or [])
        for o in P['objs'] + ([P['root']] if P['root'].type == 'MESH' else []): o.hide_render = oculto
        if oculto: continue
        P['root'].location = Vector(st['pos']); P['root'].rotation_mode = 'XYZ'; P['root'].rotation_euler = (0, 0, math.radians(float(st.get('rot') or 0) + P['giro_base']))
    bpy.context.view_layer.update()
    for pid, P in PERS.items():
        st = (t.get('estados') or {}).get(pid)
        if not st or pid not in (t.get('en_cuadro') or []): continue
        A = P['A']; h = float(next(x for x in E['personajes'] if x['id'] == pid).get('altura') or 1.7); base = Vector(st['pos'])
        pts = [base, base + Vector((0, 0, h))]
        us = [uv(cam, x) for x in pts]; cen = uv(cam, base + Vector((0, 0, h * .55)))
        f = P['root'].matrix_world.to_3x3() @ Vector((0, -1, 0)); f.z = 0; f.normalize(); tc = (cam.matrix_world.translation - base); tc.z = 0; tc.normalize()
        c = f.dot(tc); d = {'centro_uv': cen[:2], 'delante': cen[2], 'alto_pantalla': round(abs(us[1][1] - us[0][1]), 3), 'coseno_a_camara': round(c, 3),
                           'cuerpo': 'frente' if c > .5 else 'espalda' if c < -.5 else 'perfil', 'lado_pantalla': 'izquierda' if cen[0] < .38 else 'derecha' if cen[0] > .62 else 'centro',
                           'en_cuadro': bool(cen[2] and -0.05 <= cen[0] <= 1.05), 'cuerpo_3d': P['tipo']}
        if A is not None and P.get('muneca_acc'):
            pbn = A.pose.bones; L_ = uv(cam, A.matrix_world @ pbn['J_Bip_L_Hand'].head); R_ = uv(cam, A.matrix_world @ pbn['J_Bip_R_Hand'].head)
            mi = 'izquierda' if L_[0] < R_[0] else 'derecha'
            d['lado_pantalla_accesorio'] = mi if P['muneca_acc'] == 'L' else ('derecha' if mi == 'izquierda' else 'izquierda'); d['muneca_accesorio'] = 'izquierda' if P['muneca_acc'] == 'L' else 'derecha'
        vis[pid] = d
    os.makedirs(E['salida_dir'], exist_ok=True); arch = {}
    for modo in ('gris', 'color'):
        sh.color_type = 'SINGLE' if modo == 'gris' else 'OBJECT'; sh.single_color = (.7, .7, .7)
        sc.render.filepath = os.path.join(E['salida_dir'], f"{t['id']}_{modo}.png"); bpy.ops.render.render(write_still=True); arch[modo] = sc.render.filepath
    med[t['id']] = {'camara_molde': t['camara_molde'], 'segundo': t.get('segundo'), 'personajes': vis, 'imagenes': arch}
json.dump({'ok': True, 'vrm_addon': VRM_OK, 'cuerpos': {k: v['tipo'] for k, v in PERS.items()}, 'tomas': med}, open(OUT, 'w'), indent=1, ensure_ascii=False)
print('MOLDE_O109_OK', len(med))
