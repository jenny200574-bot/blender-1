# PISTA INMI o113 (t308u): FILTRO DE CÁMARAS genérico (gratis). Dentro de Blender con el molde.blend:
#   blender -b molde.blend -P camaras_o113_blender.py -- salida.json [posiciones.json]
# Mide qué cámaras del molde ven de verdad la ZONA DE ACCIÓN (piso caminable del set, o posiciones dadas) con figuras de pie:
# en cuadro (pies y cabeza), no inclinada fuera, sin objetos que tapen. Si ninguna sirve, crea UNA cámara nivelada «auto_o113_*»
# desde la geometría del set (marcada como auto-generada). No escribe en el molde.
import bpy, json, math, sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from bpy_extras.object_utils import world_to_camera_view as w2c
A_ = sys.argv[sys.argv.index('--') + 1:]; OUT = A_[0]; POS = json.load(open(A_[1])) if len(A_) > 1 and A_[1] else None
sc = bpy.context.scene; sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
SET = [o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render and not o.name.startswith(('marca_', 'flecha_', 'rej_'))]
dg = bpy.context.evaluated_depsgraph_get(); V, F = [], []
for o in SET:
    e = o.evaluated_get(dg); m = e.to_mesh(); n = len(V); V += [o.matrix_world @ v.co for v in m.vertices]; F += [tuple(i + n for i in p.vertices) for p in m.polygons]; e.to_mesh_clear()
BV = BVHTree.FromPolygons(V, F)
xs = [v.x for v in V]; ys = [v.y for v in V]; zs = [v.z for v in V]; X0, X1, Y0, Y1, ZT = min(xs), max(xs), min(ys), max(ys), max(zs)
def hit(a, b):
    d = b - a; h = BV.ray_cast(a, d.normalized(), d.length - 0.05); return h[0] is not None
# zona de acción: posiciones dadas, o piso caminable (superficie plana más baja, con 0.4 m libres alrededor y 2 m arriba)
pts = []
if POS: pts = [Vector(p) for p in POS]
else:
    paso = max(0.5, max(X1 - X0, Y1 - Y0) / 30); zf = None; cand = []
    y = Y0 + paso / 2
    while y < Y1:
        x = X0 + paso / 2
        while x < X1:
            h = BV.ray_cast(Vector((x, y, ZT + 1)), Vector((0, 0, -1)), ZT + 50)
            if h[0] is not None and h[1].z > 0.9: cand.append(h[0])
            x += paso
        y += paso
    if cand:
        zf = min(c.z for c in cand)   # nivel del piso principal (el más bajo con superficie plana)
        for c in cand:
            if c.z > zf + 0.6: continue
            p = c + Vector((0, 0, 0.05))
            if hit(p, p + Vector((0, 0, 2.0))): continue
            if any(hit(p + Vector((0, 0, .9)), p + Vector((dx, dy, .9))) for dx, dy in ((.4, 0), (-.4, 0), (0, .4), (0, -.4))): continue
            pts.append(c)
    if len(pts) > 80: pts = pts[::max(1, len(pts) // 80)]
def medir(cam, P):
    ok = 0; detalle = []
    co = cam.matrix_world.translation
    for p in P:
        pie, pecho, cab = p + Vector((0, 0, .05)), p + Vector((0, 0, 1.0)), p + Vector((0, 0, 1.65))
        qs = [w2c(sc, cam, x) for x in (pie, cab)]
        cuadro = all(q.z > 0 and -0.02 <= q.x <= 1.02 and -0.02 <= q.y <= 1.02 for q in qs)
        libre = not hit(co, pecho) and not hit(co, cab)
        ok += cuadro and libre
    return ok / max(1, len(P))
def pitch(cam):
    d = cam.matrix_world.to_3x3() @ Vector((0, 0, -1)); return math.degrees(math.asin(max(-1, min(1, d.z))))
res = []
for c in [o for o in bpy.data.objects if o.type == 'CAMERA' and o.name != 'cam_planta']:
    s = medir(c, pts); pt = pitch(c); dentro = BV.find_nearest(c.matrix_world.translation)[3] < 0.15
    sirve = s >= 0.15 and -40 <= pt <= 12 and not dentro
    res.append({'nombre': c.name, 'puntaje': round(s, 3), 'inclinacion_grados': round(pt, 1), 'dentro_de_objeto': dentro, 'sirve': sirve,
                'por_que': 've la zona de acción' if sirve else ('dentro/pegada a un objeto' if dentro else ('mira hacia arriba/abajo' if not -40 <= pt <= 12 else 'casi no ve figuras de pie (fuera de cuadro o tapadas)'))})
auto = []
if pts and not any(r['sirve'] for r in res):   # cámara nivelada automática desde la geometría
    cen = sum(pts, Vector()) / len(pts); R = max((p - cen).length for p in pts) + 1.0; zf = min(p.z for p in pts); best = None
    for k in range(16):
        a = 2 * math.pi * k / 16; dxy = Vector((math.cos(a), math.sin(a), 0))
        for f in (1.0, 0.8, 0.6, 0.4):
            loc = cen + dxy * R * f; loc.x = min(max(loc.x, X0 + .3), X1 - .3); loc.y = min(max(loc.y, Y0 + .3), Y1 - .3); loc.z = zf + 1.6
            if BV.find_nearest(loc)[3] < 0.3: continue
            bpy.ops.object.camera_add(location=loc); c = bpy.context.object; c.data.lens = 24
            c.rotation_euler = ((cen + Vector((0, 0, 1.0))) - loc).to_track_quat('-Z', 'Y').to_euler(); bpy.context.view_layer.update()
            s = medir(c, pts); dd = c.matrix_world.to_3x3() @ Vector((0, 0, -1))
            if best is None or s > best[0]: best = (s, loc.copy(), dd.copy())
            bpy.data.objects.remove(c)
    if best:
        auto.append({'nombre': 'auto_o113_1', 'auto_generada': True, 'loc': list(best[1]), 'dir': list(best[2]), 'arriba': [0, 0, 1], 'lente_mm': 24, 'sensor_ancho_mm': 36,
                     'puntaje': round(best[0], 3), 'por_que': 'ninguna cámara del molde ve la zona de acción: cámara nivelada creada desde la geometría del set'})
json.dump({'zona_accion_puntos': len(pts), 'origen_zona': 'posiciones dadas' if POS else 'piso caminable del set', 'camaras': res, 'auto': auto,
           'sirven': [r['nombre'] for r in res if r['sirve']] + [a['nombre'] for a in auto]}, open(OUT, 'w'), indent=1, ensure_ascii=False)
print('CAMARAS_O113_OK')
