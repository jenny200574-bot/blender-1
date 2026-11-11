# -*- coding: utf-8 -*-
"""[constructores_v1_20261109 · genérico] Uso: blender -b --factory-startup -P construir_render.py -- <modo> --datos DIR --escenario ID --salida DIR
(antes fijo a esc-habitacion; las cámaras eran coordenadas de la habitación, ahora son fracciones del cuarto W×D×H, idénticas para 4,5×4,0×2,8).
Blender (EEVEE): dibuja un escenario desde datos/ensamblado_<modo>.json + cuarto (muros con huecos de puerta y ventana,
zócalo, piso, techo, alfombra) y renderiza 5 vistas. Uso: blender -b --factory-startup -P construir_render.py -- <star|cajas>"""
import bpy, bmesh, json, math, sys
from mathutils import Matrix, Vector
from pathlib import Path
_A = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def _arg(k, d=None):
    return _A[_A.index(k) + 1] if k in _A else d
MODO = _A[0] if _A and not _A[0].startswith('--') else 'star'
DATOS = Path(_arg('--datos', str(Path(__file__).resolve().parents[1] / 'datos')))
ESC = _arg('--escenario')
if not ESC: raise SystemExit('falta --escenario <id>')
SALIDA = Path(_arg('--salida', str(DATOS.parent)))
PLAN = json.loads((DATOS / f'plan_{ESC}.json').read_text(encoding='utf-8'))
ENS = json.loads((DATOS / f'ensamblado_{MODO}.json').read_text(encoding='utf-8'))
W, D, H = PLAN['medidas']['ancho_m'], PLAN['medidas']['fondo_m'], PLAN['medidas']['alto_m']
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
def hx(h):
    h = h.lstrip('#'); return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
MATS = {}
def mat(rgb, rough=0.6, emis=0.0):
    k = (tuple(round(c, 3) for c in rgb), rough, emis)
    if k in MATS: return MATS[k]
    m = bpy.data.materials.new('m%d' % len(MATS)); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*k[0], 1); b.inputs['Roughness'].default_value = rough
    if emis:
        b.inputs['Emission Color'].default_value = (*k[0], 1); b.inputs['Emission Strength'].default_value = emis
    MATS[k] = m; return m
def pintar(ob, rgb, **kw):
    ob.data.materials.append(mat(rgb, **kw)); return ob
def M3(R): return Matrix(((R[0][0], R[0][1], R[0][2], 0), (R[1][0], R[1][1], R[1][2], 0), (R[2][0], R[2][1], R[2][2], 0), (0, 0, 0, 1)))
def act(): return bpy.context.active_object
def caja(n, c, s, R=None):
    bpy.ops.mesh.primitive_cube_add(size=1); o = act(); o.name = n
    o.scale = [max(v, 1e-4) for v in s]; bpy.ops.object.transform_apply(scale=True)
    o.matrix_world = Matrix.Translation(Vector(c)) @ (M3(R) if R else Matrix.Identity(4)); return o
def cil(n, a, b, r, v=24):
    a, b = Vector(a), Vector(b); d = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=v, radius=r, depth=max(d.length, 1e-4), location=(a + b) / 2); o = act(); o.name = n
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.normalized().to_track_quat('Z', 'Y'); return o
def cono(n, a, b, ra, rb):
    a, b = Vector(a), Vector(b); d = b - a
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=ra, radius2=rb, depth=max(d.length, 1e-4), location=(a + b) / 2); o = act(); o.name = n
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.normalized().to_track_quat('Z', 'Y'); return o
def esf(n, c, r):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=c, segments=24, ring_count=12); o = act(); o.name = n; return o
def toro(n, c, Rm, rm, R):
    bpy.ops.mesh.primitive_torus_add(major_radius=Rm, minor_radius=rm); o = act(); o.name = n
    o.matrix_world = Matrix.Translation(Vector(c)) @ M3(R); return o
def pol(n, vs):
    me = bpy.data.meshes.new(n); bm = bmesh.new(); vv = [bm.verts.new(v) for v in vs]
    try: bmesh.ops.convex_hull(bm, input=vv)
    except Exception: pass
    bm.to_mesh(me); bm.free(); o = bpy.data.objects.new(n, me); sc.collection.objects.link(o); return o
def pieza(p, n):
    t = p['t']
    if t == 'caja': o = caja(n, p['c'], p['s'], p['R'])
    elif t == 'cil': o = cil(n, p['a'], p['b'], p['r'])
    elif t == 'esf': o = esf(n, p['c'], p['r'])
    elif t == 'toro': o = toro(n, p['c'], p['R_'], p['r'], p['R'])
    elif t == 'cono': o = cono(n, p['a'], p['b'], p['ra'], p['rb'])
    elif t == 'pol': o = pol(n, p['v'])
    else: raise ValueError(t)
    nm = (p.get('nombre') or '').lower()
    vidrio = 'vidrio' in nm or 'cristal' in nm
    if p.get('falta'):   # FALTA en la biblioteca: caja translúcida de marcador, para que no tape (ej. cortinas sobre la ventana)
        m = bpy.data.materials.new('falta'); m.use_nodes = True; bs = m.node_tree.nodes['Principled BSDF']
        bs.inputs['Base Color'].default_value = (*p['color'], 1); bs.inputs['Alpha'].default_value = 0.35
        try: m.surface_render_method = 'BLENDED'
        except Exception: pass
        o.data.materials.append(m); o.visible_shadow = False; return o
    return pintar(o, p.get('color') or [0.7, 0.7, 0.7], rough=0.1 if vidrio else 0.6)
# ---------------- cuarto ----------------
mt = PLAN['materiales']
C_MURO, C_ZOC, C_TECHO, C_PISO = hx('#F5E6D3'), hx('#FFF8EE'), hx('#FAF3E8'), hx('#D9A773')
E = 0.1
ab = {a['tipo']: a for a in PLAN['aberturas']} if isinstance(PLAN['aberturas'], list) else {}
EXT = (PLAN.get('int_ext') or '').upper() == 'EXT'   # [10-nov-2026] exterior (jardín): sin muros ni techo, césped y cielo
if EXT:
    pintar(caja('piso', (W / 2, D / 2, -0.025), (W + 6, D + 6, 0.05)), hx('#7DB35A'), rough=0.9)
    techo = caja('techo_invisible', (W / 2, D / 2, H + 50), (0.01, 0.01, 0.01)); techo.hide_render = True
    sol = bpy.data.lights.new('sol', 'SUN'); sol.energy = 2.2; sol.color = hx('#FFF4D6')
    so = bpy.data.objects.new('sol', sol); sc.collection.objects.link(so); so.rotation_euler = (math.radians(50), 0, math.radians(30))
else:
    pintar(caja('piso', (W / 2, D / 2, -0.025), (W + 2 * E, D + 2 * E, 0.05)), C_PISO, rough=0.5)
    techo = pintar(caja('techo', (W / 2, D / 2, H + 0.025), (W + 2 * E, D + 2 * E, 0.05)), C_TECHO)
    muros = []
    def muro(n, x0, x1, y0, y1, z0, z1):
        muros.append(pintar(caja(n, ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (x1 - x0, y1 - y0, z1 - z0)), C_MURO, rough=0.85))
    VX0, VX1, VZ0, VZ1 = 2.25 - 0.8, 2.25 + 0.8, 0.9, 2.2       # ventana (4a1 aberturas: fondo, x 2.25, 1.6 × 1.3, alféizar 0.9)
    PX0, PX1, PZ1 = 0.8 - 0.45, 0.8 + 0.45, 2.1                  # puerta (4a1: frente, x 0.8, 0.9 × 2.1)
    muro('muro_fondo_a', -E, VX0, D, D + E, 0, H); muro('muro_fondo_b', VX1, W + E, D, D + E, 0, H)
    muro('muro_fondo_bajo', VX0, VX1, D, D + E, 0, VZ0); muro('muro_fondo_alto', VX0, VX1, D, D + E, VZ1, H)
    muro('muro_frente_a', -E, PX0, -E, 0, 0, H); muro('muro_frente_b', PX1, W + E, -E, 0, 0, H); muro('muro_frente_alto', PX0, PX1, -E, 0, PZ1, H)
    muro('muro_izq', -E, 0, 0, D, 0, H); muro('muro_der', W, W + E, 0, D, 0, H)
    for n, c, s in [('zoc_fondo', (W / 2, D - 0.015, 0.05), (W, 0.03, 0.1)), ('zoc_izq', (0.015, D / 2, 0.05), (0.03, D, 0.1)),
                    ('zoc_der', (W - 0.015, D / 2, 0.05), (0.03, D, 0.1)), ('zoc_frente_b', ((PX1 + W) / 2, 0.015, 0.05), (W - PX1, 0.03, 0.1)),
                    ('zoc_frente_a', (PX0 / 2, 0.015, 0.05), (PX0, 0.03, 0.1))]:
        pintar(caja(n, c, s), C_ZOC)
    alf = pintar(cil('alfombra_redonda', (W / 2, D / 2, 0.0), (W / 2, D / 2, 0.02), 1.1, v=64), hx('#E8D3B9'), rough=0.95)
    # cielo con arcoíris tras la ventana (vista de la ventana, 4a1 "vista al arcoíris")
    pintar(caja('cielo', (W / 2, D + 1.2, 1.6), (6, 0.02, 4)), hx('#8FD3FF'), emis=1.2)
    for k, c in enumerate(['#E85D56', '#F2792A', '#FFC928', '#68B872', '#2F7DE1', '#8E5BD6']):
        o = toro(f'arcoiris_{k}', (W / 2, D + 1.15, 0.6), 1.5 - k * 0.07, 0.035, [[1, 0, 0], [0, 0, -1], [0, 1, 0]])
        pintar(o, hx(c), emis=1.5)

# ---------------- objetos ----------------
for ob in ENS['objetos']:
    for k, p in enumerate(ob['piezas']):
        pieza(p, f"{ob['id'][:40]}__{k}")
# ---------------- luz moderada ----------------
def area(n, size, energy, col, loc, rot, sy=None):
    L = bpy.data.lights.new(n, 'AREA'); L.energy = energy; L.color = col; L.shape = 'RECTANGLE'; L.size = size; L.size_y = sy or size
    o = bpy.data.objects.new(n, L); sc.collection.objects.link(o); o.location = loc; o.rotation_euler = rot; return o
if not EXT: area('luz_ventana', 1.5, 320, hx('#FFF4D6'), (2.25, 3.92, 1.55), (math.radians(90), 0, math.radians(180)), sy=1.2)
area('luz_relleno_techo', 3.0, 170, hx('#FFF4D6'), (W / 2, D / 2, H - 0.05), (0, 0, 0))
P = bpy.data.lights.new('luz_lampara', 'POINT'); P.energy = 45; P.color = hx('#FFC978'); P.shadow_soft_size = 0.15
po = bpy.data.objects.new('luz_lampara', P); sc.collection.objects.link(po); po.location = (2.25, 2.0, 2.28)
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (*hx('#FFF4D6'), 1); w.node_tree.nodes['Background'].inputs[1].default_value = 0.25
if EXT: w.node_tree.nodes['Background'].inputs[0].default_value = (*hx('#8FD3FF'), 1); w.node_tree.nodes['Background'].inputs[1].default_value = 0.4
eng = [i.identifier for i in sc.render.bl_rna.properties['engine'].enum_items]
sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in eng else 'BLENDER_EEVEE'
try: sc.eevee.taa_render_samples = 32
except Exception: pass
for a in ('use_shadows', 'use_raytracing'):
    if hasattr(sc.eevee, a): setattr(sc.eevee, a, True)
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.view_settings.view_transform = 'AgX'; sc.view_settings.exposure = 0.0
try: sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception: pass
def camara(n, loc, mira, lens=16, orto=None):
    c = bpy.data.cameras.new(n); c.lens = lens; c.clip_start = 0.05
    if orto: c.type = 'ORTHO'; c.ortho_scale = orto
    o = bpy.data.objects.new(n, c); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(mira) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return o
def _f(x, y, z): return (x / 4.5 * W, y / 4.0 * D, z / 2.8 * H)   # fracciones del cuarto de referencia 4,5×4,0×2,8
VISTAS = [('cenital_sin_techo', camara('cam_cenital', (W / 2, D / 2, 9 / 2.8 * H), (W / 2, D / 2 + 1e-4, 0), orto=7.6 * max(W / 4.5, D / 4.0)), False),
          ('vista_a', camara('cam_a', _f(0.8, 0.12, 1.45), _f(2.7, 3.6, 0.75)), True),
          ('vista_b', camara('cam_b', _f(3.4, 0.9, 1.45), _f(0.9, 2.9, 0.55)), True),
          ('vista_c', camara('cam_c', _f(2.25, 0.15, 1.35), _f(2.25, 4.0, 1.25)), True),
          ('vista_d', camara('cam_d', _f(1.6, 0.35, 1.5), _f(4.2, 2.7, 0.95), lens=18), True)]
out = SALIDA / 'renders'; out.mkdir(parents=True, exist_ok=True)
for nombre, cam, con_techo in VISTAS:
    techo.hide_render = not con_techo
    sc.camera = cam; sc.render.filepath = str(out / f'{MODO}_{nombre}.png')
    bpy.ops.render.render(write_still=True); print('RENDER', sc.render.filepath, flush=True)
techo.hide_render = False
bpy.ops.wm.save_as_mainfile(filepath=str(SALIDA / f'{ESC}_{MODO}.blend'))
print('FIN', MODO, flush=True)
