"""PISTA INMI (2026-10-29): orden 78 — script de Blender GRATIS del cubo 02 (Blender anima escenas).
Abre el molde.blend del escenario SOLO PARA LEER (nunca guarda el .blend; los videos van a otra carpeta) y:
  · pone una figura de relleno por personaje (cuerpo + cabeza + nariz que muestra hacia dónde mira), del alto pedido;
  · la mueve por sus claves (segundo → posición y giro; lineal) y la esconde fuera de su tiempo en escena;
  · por cada toma pone su cámara (la del molde por nombre, o una con loc/mira/lente/sensor) y saca un video corto de vista previa
    (Workbench, baja resolución) + un cuadro PNG del medio.
Uso: blender -b molde.blend --factory-startup --python blender_animar.py -- entrada.json salida.json
entrada = {"res": [ancho, alto], "fps": 8, "motor": "BLENDER_WORKBENCH", "hilos": 2, "calidad": "MEDIUM",
           "figuras": [{"id", "altura", "color": [r,g,b], "radio_cuerpo", "radio_cabeza", "nariz": [x,y,z], "visible": [f0, f1],
                        "claves": [{"f": 1, "pos": [x,y,z], "rot": 0}]}],
           "tomas": [{"id", "camara": {"molde": "cam_01_esc1"} | {"loc", "mira", "lente", "sensor_ancho_mm", "sensor_alto_mm"?, "sensor_fit"?},
                      "frames": [f0, f1], "video": "/ruta/x.mp4", "cuadro": "/ruta/x.png"}]}
Genérico: no sabe de canales ni de episodios. 0° = mira a +x; el giro es a la izquierda (contra reloj, visto desde arriba)."""
import glob, json, math, os, shutil, sys, tempfile, time
import bpy, bmesh
from mathutils import Matrix, Vector

a = sys.argv[sys.argv.index('--') + 1:]
E = json.load(open(a[0], encoding='utf-8'))
sc = bpy.context.scene
out = {'ok': True, 'blender': bpy.app.version_string, 'archivo': bpy.data.filepath, 'tomas': [], 'figuras': []}


def material(nombre, color):
    m = bpy.data.materials.new(nombre); m.diffuse_color = (float(color[0]), float(color[1]), float(color[2]), 1.0); return m


def figura(f):
    H = float(f['altura']); rc = H * float(f['radio_cuerpo']); rh = H * float(f['radio_cabeza'])
    nariz = f.get('nariz')   # PISTA INMI (orden 79): None = la entrada no dice hacia dónde mira → sin nariz (no se inventa el giro)
    bm = bmesh.new(); cuerpo = H - 2 * rh
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=16, radius1=rc, radius2=rc * 0.85, depth=cuerpo,
                          matrix=Matrix.Translation((0, 0, cuerpo / 2)))
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=rh, matrix=Matrix.Translation((0, 0, H - rh)))
    n0 = len(bm.faces)
    if nariz:
        nx, ny, nz = [H * float(v) for v in nariz]
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((rh + nx / 2, 0, H - rh)) @ Matrix.Diagonal((nx, ny, nz, 1)))
    bm.faces.ensure_lookup_table()
    for i, fa in enumerate(bm.faces): fa.material_index = 1 if i >= n0 else 0
    me = bpy.data.meshes.new('fig_' + f['id']); bm.to_mesh(me); bm.free()
    me.materials.append(material('fig_' + f['id'], f['color'])); me.materials.append(material('nariz_' + f['id'], (1, 1, 1)))
    o = bpy.data.objects.new('FIG_' + f['id'], me); sc.collection.objects.link(o)
    o.rotation_mode = 'XYZ'
    prev = None
    for k in sorted(f['claves'], key=lambda k: k['f']):
        o.location = Vector(k['pos'])
        if k.get('rot') is not None:
            r = math.radians(float(k['rot']))
            if prev is not None:   # sin vueltas de 360° de más (350° → 10° gira 20°, no 340°)
                while r - prev > math.pi: r -= 2 * math.pi
                while prev - r > math.pi: r += 2 * math.pi
            prev = r; o.rotation_euler = (0, 0, r); o.keyframe_insert('rotation_euler', frame=k['f'])
        o.keyframe_insert('location', frame=k['f'])
    v0, v1 = f.get('visible') or [None, None]
    if v0 is not None:
        for fr, oculto in ((v0 - 1, True), (v0, False), (v1, False), (v1 + 1, True)):
            o.hide_render = oculto; o.hide_viewport = oculto
            o.keyframe_insert('hide_render', frame=fr); o.keyframe_insert('hide_viewport', frame=fr)
    if o.animation_data and o.animation_data.action:
        for fc in o.animation_data.action.fcurves:
            for p in fc.keyframe_points: p.interpolation = 'CONSTANT' if fc.data_path.startswith('hide') else 'LINEAR'
    return o


def camara(c):
    if c.get('molde'):
        o = sc.objects.get(c['molde'])
        if o is None or o.type != 'CAMERA': raise ValueError(f"no hay cámara {c['molde']} en el molde")
        return o
    d = bpy.data.cameras.new('toma_tmp'); d.lens = float(c.get('lente') or 35); d.sensor_width = float(c.get('sensor_ancho_mm') or 36)
    if c.get('sensor_alto_mm'): d.sensor_height = float(c['sensor_alto_mm'])
    if c.get('sensor_fit') in ('AUTO', 'HORIZONTAL', 'VERTICAL'): d.sensor_fit = c['sensor_fit']
    d.clip_start = 0.05; d.clip_end = 500
    o = bpy.data.objects.new('toma_tmp', d); sc.collection.objects.link(o)
    o.location = Vector(c['loc']); o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = (Vector(c['mira']) - Vector(c['loc'])).to_track_quat('-Z', 'Y')
    return o


def tapan(cam):   # bloques que contienen la cámara (paredes, techo): se esconden solo en esa toma, como hace el molde
    co = cam.matrix_world.translation; res = []
    for ob in sc.objects:
        if ob.type != 'MESH' or ob.name.startswith('FIG_') or ob.hide_render: continue
        bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        if all(min(v[i] for v in bb) < co[i] < max(v[i] for v in bb) for i in range(3)): res.append(ob)
    return res


R = sc.render; res = E['res']
R.engine = E.get('motor') or 'BLENDER_WORKBENCH'; R.resolution_x, R.resolution_y = int(res[0]), int(res[1]); R.resolution_percentage = 100
R.fps = int(E.get('fps') or 8); R.fps_base = 1.0; R.threads_mode = 'FIXED'; R.threads = int(E.get('hilos') or 2)
if R.engine == 'BLENDER_WORKBENCH':
    sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'; sh.show_shadows = True; sh.show_object_outline = True
sc.view_settings.view_transform = 'Standard'
for c in bpy.data.collections:   # las etiquetas de la planta no van en las tomas (igual que en el molde)
    if c.name.startswith('etiquetas'): c.hide_render = True
for f in E.get('figuras') or []:
    figura(f); out['figuras'].append(f['id'])
bpy.context.view_layer.update()
for t in E.get('tomas') or []:
    t0 = time.time(); r = {'id': t['id'], 'ok': False}
    try:
        cam = camara(t['camara']); sc.camera = cam; bpy.context.view_layer.update()
        f0, f1 = int(t['frames'][0]), int(t['frames'][1]); sc.frame_start, sc.frame_end = f0, max(f0, f1)
        ocultos = tapan(cam)
        for ob in ocultos: ob.hide_render = True
        with tempfile.TemporaryDirectory(prefix='o78_') as td:
            R.image_settings.file_format = 'FFMPEG'; R.ffmpeg.format = 'MPEG4'; R.ffmpeg.codec = 'H264'
            R.ffmpeg.constant_rate_factor = E.get('calidad') or 'MEDIUM'; R.ffmpeg.ffmpeg_preset = 'REALTIME'; R.ffmpeg.audio_codec = 'NONE'
            R.filepath = os.path.join(td, 'v_'); bpy.ops.render.render(animation=True)
            hechos = glob.glob(os.path.join(td, 'v_*'))
            if not hechos: raise RuntimeError('Blender no dejó el video')
            os.makedirs(os.path.dirname(t['video']), exist_ok=True); shutil.move(hechos[0], t['video'] + '.tmp'); os.replace(t['video'] + '.tmp', t['video'])
            if t.get('cuadro'):
                R.image_settings.file_format = 'PNG'; sc.frame_set((f0 + max(f0, f1)) // 2)
                R.filepath = os.path.join(td, 'c.png'); bpy.ops.render.render(write_still=True)
                os.makedirs(os.path.dirname(t['cuadro']), exist_ok=True); shutil.move(os.path.join(td, 'c.png'), t['cuadro'])
        for ob in ocultos: ob.hide_render = False
        if cam.name == 'toma_tmp': bpy.data.objects.remove(cam, do_unlink=True)
        r.update(ok=True, cuadros=max(f0, f1) - f0 + 1, res=[R.resolution_x, R.resolution_y], fps=R.fps, camara=cam.name if t['camara'].get('molde') else 'calculada',
                 escondidos=[o.name for o in ocultos], bytes=os.path.getsize(t['video']))
    except Exception as e:
        r['error'] = f'{type(e).__name__}: {e}'
    r['segundos'] = round(time.time() - t0, 1); out['tomas'].append(r)
out['ok'] = all(x['ok'] for x in out['tomas']) if out['tomas'] else True
json.dump(out, open(a[1], 'w', encoding='utf-8'), ensure_ascii=False)
# el .blend del molde NUNCA se guarda: queda como estaba
