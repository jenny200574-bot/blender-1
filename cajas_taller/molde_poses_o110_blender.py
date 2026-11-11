# o110 (t298u) — molde 3D por toma CON POSE (Blender). Reusa molde_o109_blender.py SIN modificarlo: ejecuta su código e intercala, en cada
# toma, la pose por personaje (palabra del 01) justo después de colocarlo. VRM -> aplicar_pose.py (humanoide); otro rig -> universal.py
# (por tipo de cuerpo); figura gris sin esqueleto -> solo poses de cuerpo entero. Palabra o tipo que falte -> FALTA en el informe (se deja de_pie).
import bpy, json, math, os, sys
from mathutils import Vector
A_ = sys.argv[sys.argv.index('--') + 1:]; E = json.load(open(A_[0])); OUT = A_[1]
sys.path.insert(0, E['poses_dir']); import aplicar_pose as AP, universal as UNI
LIB = json.load(open(os.path.join(E['poses_dir'], 'poses_basicas.json')))
REG = {}; ASIENTOS = {}
MARCA = "    bpy.context.view_layer.update()\n    for pid, P in PERS.items():\n        st = (t.get('estados') or {}).get(pid)\n"
def POSAR(t):
    PERS = G['PERS']; reg = REG.setdefault(t['id'], {})
    for pid, P in PERS.items():
        st = (t.get('estados') or {}).get(pid)
        if not st or pid not in (t.get('en_cuadro') or []): continue
        w = (t.get('poses') or {}).get(pid) or {}; nombre = w.get('pose') or 'de_pie'; esp = bool(w.get('espejo'))
        A = P.get('A'); r = {'pedida': nombre, 'espejo': esp}; pos = Vector(st['pos']); rz = float(st.get('rot') or 0) + P['giro_base']
        try:
            if A is not None and 'J_Bip_C_Hips' in A.pose.bones:
                pid_pose, pp = AP.aplicar(A, LIB, nombre, esp, tuple(pos), rz); r['aplicada'] = pid_pose; r['metodo'] = 'aplicar_pose (VRM)'
                AP.apoyar(A, P['objs'], pos.z)
                if pp.get('asiento'):   # pose que necesita asiento: cajón-proxy bajo la cadera (gris), avisado
                    hp = A.matrix_world @ A.pose.bones['J_Bip_C_Hips'].head; top = max(hp.z - pos.z - 0.1 * A.scale.z, 0.1)
                    b = ASIENTOS.get(pid)
                    if b is None:
                        bpy.ops.mesh.primitive_cube_add(size=1); b = bpy.context.object; b.name = f'asiento_proxy_{pid}'; b.color = (.45, .35, .25, 1); ASIENTOS[pid] = b
                    b.hide_render = False; b.scale = (0.45, 0.45, top); b.location = (hp.x, hp.y, pos.z + top / 2); r['asiento_proxy'] = True
                elif pid in ASIENTOS: ASIENTOS[pid].hide_render = True
            elif A is not None:
                R = UNI.clasificar(A); UNI.aplicar(A, R, AP._n(nombre)); r.update(aplicada=AP._n(nombre), metodo=f"universal ({R['tipo']})")
                A.location = pos; A.rotation_mode = 'QUATERNION'; AP.apoyar(A, P['objs'], pos.z)
            else:
                tilt = {'de_pie': 0, 'caminando': 0, 'acostado_boca_arriba': -90, 'acostado_boca_abajo': 90}.get(AP._n(nombre))   # caminar = de pie (el avance es la posicion)
                if tilt is None: raise AP.PoseFalta(f'pose «{nombre}» FALTA para un cuerpo sin esqueleto (figura gris)')
                ro = P['root']; ro.rotation_mode = 'XYZ'; ro.rotation_euler = (math.radians(tilt), 0, math.radians(rz)); r.update(aplicada=AP._n(nombre), metodo='figura gris: cuerpo entero')
                bpy.context.view_layer.update(); AP.apoyar(ro, [o for o in P['objs'] if o.type == 'MESH'] or [ro], pos.z)
        except (AP.PoseFalta, UNI.Falta) as ex:
            r['falta'] = str(ex); r['aplicada'] = 'de_pie'
            if A is not None and 'J_Bip_C_Hips' in A.pose.bones: AP.aplicar(A, LIB, 'de_pie', False, tuple(pos), rz); AP.apoyar(A, P['objs'], pos.z)
            elif A is None:   # figura gris: queda de pie, apoyada en el piso
                ro = P['root']; ro.rotation_mode = 'XYZ'; ro.rotation_euler = (0, 0, math.radians(rz)); bpy.context.view_layer.update()
                AP.apoyar(ro, [o for o in P['objs'] if o.type == 'MESH'] or [ro], pos.z)
        bpy.context.view_layer.update()
        objs = [o for o in P['objs'] if o.type == 'MESH' and not o.hide_render]
        if objs: r['zmin_menos_piso'] = round(AP.zmin_malla(objs) - pos.z, 4); r['piso_ok'] = abs(r['zmin_menos_piso']) < 0.01
        reg[pid] = r
src = open(E['molde_o109_blender']).read()
if src.count(MARCA) != 1: raise SystemExit('MOLDE_O109_CAMBIO: no encuentro el punto de pose en molde_o109_blender.py (no se adivina)')
src = src.replace(MARCA, "    POSAR(t)\n" + MARCA)
G = {'__name__': '__main__', 'POSAR': None}
sys.argv = ['x', '--', A_[0], OUT]
def _posar(t): return POSAR(t)
G['POSAR'] = _posar
exec(compile(src, 'molde_o109_blender(+poses o110)', 'exec'), G)
PERS = G['PERS']
d = json.load(open(OUT)); d['poses'] = REG; d['version_poses'] = 'o110'; json.dump(d, open(OUT, 'w'), indent=1, ensure_ascii=False)
print('MOLDE_POSES_O110_OK', len(REG))
