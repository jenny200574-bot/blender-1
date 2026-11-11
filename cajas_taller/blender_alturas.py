"""Corre DENTRO de Blender (sin ventana): por cada objeto raíz con la propiedad de escala del maniquí devuelve su escala
y la caja (z mín/máx) en el primer cuadro. Uso: blender -b X.blend --factory-startup --python blender_alturas.py -- salida.json propiedad"""
import bpy, json, sys, mathutils
a = sys.argv[sys.argv.index('--') + 1:]; out, prop = a[0], (a[1] if len(a) > 1 else 'escala')
sc = bpy.context.scene; sc.frame_set(sc.frame_start)
def desc(o):
    r = [o]
    for c in o.children: r += desc(c)
    return r
res = []
for o in bpy.data.objects:
    if o.parent is not None or o.get(prop) is None: continue
    zs = [(m.matrix_world @ mathutils.Vector(v)).z for m in desc(o) if m.type == 'MESH' for v in m.bound_box]
    try: e = float(o.get(prop))
    except Exception: continue
    res.append({'objeto': o.name, 'escala': e, 'z_min': round(min(zs), 3) if zs else None, 'z_max': round(max(zs), 3) if zs else None})
json.dump({'archivo': bpy.data.filepath, 'frame': sc.frame_start, 'maniquies': res}, open(out, 'w'))
