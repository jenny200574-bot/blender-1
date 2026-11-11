"""medir_altura.py — [constructores_v1_20261109] mide en Blender la altura real del molde (.blend) en reposo. US$0, sin IA.
Uso: blender -b MOLDE.blend --python medir_altura.py -- --salida medida.json
Mide: z_max − z_min de todas las mallas visibles en render (sin el piso ni el banco de pruebas), en metros."""
import bpy, sys, json
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
out = argv[argv.index('--salida') + 1] if '--salida' in argv else None
bpy.context.view_layer.update()
mallas = [o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render and o.name != 'piso' and '_banco_' not in o.name]
for a in [o for o in bpy.data.objects if o.type == 'ARMATURE']:
    for pb in a.pose.bones:
        pb.rotation_mode = 'XYZ'; pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)
bpy.context.view_layer.update()
pts = [(o.matrix_world @ Vector(c)) for o in mallas for c in o.bound_box]
zmin, zmax = min(p.z for p in pts), max(p.z for p in pts)
xs, ys = [p.x for p in pts], [p.y for p in pts]
r = {'blend': bpy.data.filepath, 'n_mallas': len(mallas), 'z_min_m': round(zmin, 5), 'z_max_m': round(zmax, 5),
     'altura_medida_m': round(zmax - zmin, 4), 'ancho_m': round(max(xs) - min(xs), 4), 'fondo_m': round(max(ys) - min(ys), 4),
     'n_huesos': sum(len(a.data.bones) for a in bpy.data.objects if a.type == 'ARMATURE'),
     'n_materiales': len({s.material.name for o in mallas for s in o.material_slots if s.material}),
     'blender': bpy.app.version_string, 'metodo': 'bound_box mundo de mallas visibles en reposo (sin piso/banco)'}
if out: open(out, 'w').write(json.dumps(r, ensure_ascii=False, indent=1))
print('MEDIDA', json.dumps(r, ensure_ascii=False))
