"""PISTA INMI (2026-10-29): orden 74 — script de Blender GRATIS para los cubos 05–09 (ajustes Argon 3 y 4).
Abre el molde.blend del escenario (SOLO LECTURA: nunca guarda) y:
  · exporta las cámaras del molde (lugar, hacia dónde mira, lente, sensor) → el eje de 180° y los tipos de plano se calculan con esto;
  · exporta las medidas (min/max) de cada objeto del molde;
  · para cada toma pedida pone su cámara (la del molde o una calculada) y proyecta puntos 3D con world_to_camera_view
    (u = 0 izquierda … 1 derecha; v = 0 abajo … 1 arriba; z = distancia delante de la cámara; z<0 = detrás).
Uso: blender -b molde.blend --python blender_camaras.py -- entrada.json salida.json
entrada = {"res": [ancho, alto], "medidas": true, "tomas": [{"id", "res"?, "camara": {"molde": "cam_01_esc8"} | {"loc": [x,y,z], "mira": [x,y,z], "lente": 35, "sensor_ancho_mm": 36}, "puntos": {"nombre": [x,y,z]}}]}
Genérico: no sabe de canales ni de episodios."""
import json, sys
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

a = sys.argv[sys.argv.index('--') + 1:]
E = json.load(open(a[0], encoding='utf-8'))
sc = bpy.context.scene
r3 = lambda v: [round(float(x), 4) for x in v]


def cam_info(o):
    q = o.matrix_world.to_quaternion()
    return {'nombre': o.name, 'loc': r3(o.matrix_world.translation), 'dir': r3(q @ Vector((0, 0, -1))), 'arriba': r3(q @ Vector((0, 1, 0))),
            'lente_mm': round(o.data.lens, 3), 'sensor_ancho_mm': round(o.data.sensor_width, 3), 'sensor_alto_mm': round(o.data.sensor_height, 3),
            'sensor_fit': o.data.sensor_fit, 'tipo': o.data.type}


out = {'ok': True, 'blender': bpy.app.version_string, 'archivo': bpy.data.filepath,
       'res_molde': [sc.render.resolution_x, sc.render.resolution_y],
       'camaras_molde': [cam_info(o) for o in sorted(sc.objects, key=lambda o: o.name) if o.type == 'CAMERA'], 'tomas': []}
if E.get('medidas'):
    med = {}
    for o in sc.objects:
        if o.type != 'MESH': continue
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        med[o.name] = {'min': r3([min(p[i] for p in pts) for i in range(3)]), 'max': r3([max(p[i] for p in pts) for i in range(3)])}
    out['medidas'] = med
for t in E.get('tomas') or []:
    res = t.get('res') or E.get('res')
    if res:
        sc.render.resolution_x, sc.render.resolution_y = int(res[0]), int(res[1]); sc.render.pixel_aspect_x = sc.render.pixel_aspect_y = 1
    c = t.get('camara') or {}; tmp = None
    if c.get('molde'):
        o = sc.objects.get(c['molde'])
        if o is None or o.type != 'CAMERA':
            out['tomas'].append({'id': t.get('id'), 'ok': False, 'error': f"no hay cámara {c['molde']} en el molde"}); continue
    else:
        d = bpy.data.cameras.new('toma_tmp'); d.lens = float(c.get('lente') or 35); d.sensor_width = float(c.get('sensor_ancho_mm') or 36)
        if c.get('sensor_alto_mm'): d.sensor_height = float(c['sensor_alto_mm'])
        if c.get('sensor_fit') in ('AUTO', 'HORIZONTAL', 'VERTICAL'): d.sensor_fit = c['sensor_fit']   # PISTA INMI (2026-10-29): igual que la cámara del molde
        o = tmp = bpy.data.objects.new('toma_tmp', d); sc.collection.objects.link(o)
        o.location = Vector(c['loc']); o.rotation_mode = 'QUATERNION'
        o.rotation_quaternion = (Vector(c['mira']) - Vector(c['loc'])).to_track_quat('-Z', 'Y')
        bpy.context.view_layer.update()
    uv = {k: r3(world_to_camera_view(sc, o, Vector(p))) for k, p in (t.get('puntos') or {}).items()}
    out['tomas'].append({'id': t.get('id'), 'ok': True, 'res': [sc.render.resolution_x, sc.render.resolution_y], 'camara': cam_info(o), 'uv': uv})
    if tmp is not None:
        bpy.data.objects.remove(tmp, do_unlink=True)
json.dump(out, open(a[1], 'w', encoding='utf-8'), ensure_ascii=False)
