# -*- coding: utf-8 -*-
"""[constructores_v1_20261109 · 10-nov-2026] Blender: molde de UN objeto desde piezas.json (extraer_objeto.py), mismas
primitivas que construir_render.py del escenario. Guarda .blend, 4 vistas (Workbench) y medida.json (alto/ancho/fondo reales).
Uso: blender -b --factory-startup -P construir_objeto.py -- --piezas P.json --salida DIR --id ID"""
import bpy, bmesh, json, math, sys
from mathutils import Matrix, Vector
from pathlib import Path
A = sys.argv[sys.argv.index('--') + 1:]
def arg(k): return A[A.index(k) + 1]
PZ = json.load(open(arg('--piezas'), encoding='utf-8')); SAL = Path(arg('--salida')); ID = arg('--id'); SAL.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
MATS = {}
def mat(rgb, alpha=1.0):
    k = (tuple(round(c, 3) for c in rgb), alpha)
    if k in MATS: return MATS[k]
    m = bpy.data.materials.new('m%d' % len(MATS)); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*k[0], 1); b.inputs['Alpha'].default_value = alpha; m.diffuse_color = (*k[0], alpha); MATS[k] = m; return m
def M3(R): return Matrix(((R[0][0], R[0][1], R[0][2], 0), (R[1][0], R[1][1], R[1][2], 0), (R[2][0], R[2][1], R[2][2], 0), (0, 0, 0, 1)))
def act(): return bpy.context.active_object
def caja(n, c, s, R=None):
    bpy.ops.mesh.primitive_cube_add(size=1); o = act(); o.name = n; o.scale = [max(v, 1e-4) for v in s]; bpy.ops.object.transform_apply(scale=True)
    o.matrix_world = Matrix.Translation(Vector(c)) @ (M3(R) if R else Matrix.Identity(4)); return o
def _tramo(n, a, b, f):
    a, b = Vector(a), Vector(b); d = b - a; o = f(max(d.length, 1e-4), (a + b) / 2); o.name = n
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.normalized().to_track_quat('Z', 'Y'); return o
def cil(n, a, b, r): return _tramo(n, a, b, lambda L, c: (bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=r, depth=L, location=c), act())[1])
def cono(n, a, b, ra, rb): return _tramo(n, a, b, lambda L, c: (bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=ra, radius2=rb, depth=L, location=c), act())[1])
def esf(n, c, r): bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=c, segments=24, ring_count=12); o = act(); o.name = n; return o
def toro(n, c, Rm, rm, R):
    bpy.ops.mesh.primitive_torus_add(major_radius=Rm, minor_radius=rm); o = act(); o.name = n; o.matrix_world = Matrix.Translation(Vector(c)) @ M3(R); return o
def pol(n, vs):
    me = bpy.data.meshes.new(n); bm = bmesh.new(); vv = [bm.verts.new(v) for v in vs]
    try: bmesh.ops.convex_hull(bm, input=vv)
    except Exception: pass
    bm.to_mesh(me); bm.free(); o = bpy.data.objects.new(n, me); sc.collection.objects.link(o); return o
obs = []
for i, p in enumerate(PZ['piezas']):
    n = f"{ID}_{i:02d}_{(p.get('nombre') or p['t'])}"[:60]; t = p['t']
    o = (caja(n, p['c'], p['s'], p.get('R')) if t == 'caja' else cil(n, p['a'], p['b'], p['r']) if t == 'cil' else esf(n, p['c'], p['r']) if t == 'esf'
         else toro(n, p['c'], p['R_'], p['r'], p['R']) if t == 'toro' else cono(n, p['a'], p['b'], p['ra'], p['rb']) if t == 'cono' else pol(n, p['v']))
    o.data.materials.append(mat(p.get('color') or [0.7, 0.7, 0.7], 0.35 if p.get('falta') else 1.0)); obs.append(o)
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in obs for c in o.bound_box]
zmin = min(p.z for p in pts)
for o in obs: o.location.z -= zmin       # apoyado en z = 0
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in obs for c in o.bound_box]
mn = [min(p[i] for p in pts) for i in range(3)]; mx = [max(p[i] for p in pts) for i in range(3)]
med = {'id': ID, 'alto_m': round(mx[2] - mn[2], 4), 'ancho_m': round(mx[0] - mn[0], 4), 'fondo_m': round(mx[1] - mn[1], 4), 'n_mallas': len(obs),
       'n_materiales': len(MATS), 'blender': bpy.app.version_string, 'metodo': 'bound_box mundo de las mallas, apoyado en z=0'}
json.dump(med, open(SAL / 'medida.json', 'w'), ensure_ascii=False, indent=1)
# render
sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'MATERIAL'
sc.display.shading.show_shadows = True; sc.render.resolution_x = sc.render.resolution_y = 640; sc.render.film_transparent = False
w = bpy.data.worlds.new('w'); sc.world = w; w.color = (0.92, 0.92, 0.92)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cen = Vector([(mn[i] + mx[i]) / 2 for i in range(3)]); R_ = max(mx[i] - mn[i] for i in range(3)) or 0.1
cam.data.lens = 50
vistas = {'frente': (0, -1, 0.15), 'perfil': (1, 0, 0.15), 'tres_cuartos': (0.75, -0.75, 0.45), 'arriba': (0.01, -0.3, 1)}
rend = {}
for nm, d in vistas.items():
    dv = Vector(d).normalized(); cam.location = cen + dv * R_ * 2.6
    cam.rotation_euler = (cen - cam.location).to_track_quat('-Z', 'Y').to_euler()
    f = SAL / 'renders' / f'{ID}_{nm}.png'; f.parent.mkdir(exist_ok=True); sc.render.filepath = str(f); bpy.ops.render.render(write_still=True); rend[nm] = str(f)
json.dump({'renders': rend, 'medida': med, 'falta': PZ.get('falta'), 'origen': PZ.get('info')}, open(SAL / 'renders' / f'{ID}_informe.json', 'w'), ensure_ascii=False, indent=1)
(SAL / 'blend').mkdir(exist_ok=True); bpy.ops.wm.save_as_mainfile(filepath=str(SAL / 'blend' / f'{ID}.blend'))
print('MEDIDA', json.dumps(med))
