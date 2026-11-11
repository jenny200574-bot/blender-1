"""render_motor (Blender 5.2.3, GPU por EGL) — motor unificado v1.
--modo final  : cámara del storyboard (camera_4g_master), EEVEE en GPU, PNG por cuadro.
--modo amplia : vista fija de revisión (esquina alta, todo el set), Workbench, para ver a todos los personajes moverse.
--modo planta : vista cenital ortográfica de revisión (rutas, separación, acople).
--modo lateral: [t1066u] vista fija de revisión desde el COSTADO del set (Workbench); se ocultan SOLO en esta vista los muros/paredes
                del lado de la cámara (por posición, no por nombre de canal).
Las vistas de revisión agregan SOLO una cámara de revisión (REV_*), nunca geometría.
Uso: blender -b escena_motor.blend --gpu-backend opengl -P render_motor.py -- --out DIR --modo final [--res 1280x720] [--paso 1] [--muestras 16]"""
import bpy, sys, os, json, math, time, argparse, atexit, traceback
from mathutils import Vector

_RENDER_OK = False
def _salir_por_excepcion(typ, val, tb):
    print(''.join(traceback.format_exception(typ, val, tb)), flush=True)
    os._exit(1)
def _atexit_chequeo():
    if not _RENDER_OK:
        print('RENDER_SALIDA: el render no terminó bien; se sale con código 1', flush=True)
        os._exit(1)
sys.excepthook = _salir_por_excepcion
atexit.register(_atexit_chequeo)

argv = sys.argv[sys.argv.index('--') + 1:]
ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True); ap.add_argument('--modo', default='final'); ap.add_argument('--res', default='1280x720')
ap.add_argument('--paso', type=int, default=1); ap.add_argument('--muestras', type=int, default=16); ap.add_argument('--f0', type=int, default=0); ap.add_argument('--f1', type=int, default=0)
ap.add_argument('--animacion', type=int, default=1)   # [argon_v2u] 1 = un solo render de animación (sin re-sincronizar la escena en cada cuadro)
a = ap.parse_args(argv); os.makedirs(a.out, exist_ok=True)
sc = bpy.context.scene; rx, ry = map(int, a.res.split('x'))
sc.render.resolution_x, sc.render.resolution_y = rx, ry; sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
f0 = a.f0 or sc.frame_start; f1 = a.f1 or sc.frame_end
R = {"modo": a.modo, "blender": bpy.app.version_string, "res": a.res, "f0": f0, "f1": f1, "paso": a.paso}
luces = [o for o in bpy.data.objects if o.type == 'LIGHT' and not o.hide_render]
R['luces_del_molde'] = len(luces)
def bbox_set():
    lo = Vector((1e9, 1e9, 1e9)); hi = -lo
    for o in bpy.data.objects:
        if o.type == 'MESH' and any(k in o.name.lower() for k in ('piso', 'muro', 'pared')):
            for c in o.bound_box:
                p = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
    return lo, hi
if a.modo == 'final':
    eng = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
    sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in eng else 'BLENDER_EEVEE_NEXT'
    try: sc.eevee.taa_render_samples = a.muestras
    except Exception: pass
    sc.camera = bpy.data.objects['camera_4g_master']
    # color del molde: la fábrica guarda el color en diffuse_color (color de material de Workbench/hojas). En Blender 5 el material
    # siempre usa nodos y EEVEE ignora diffuse_color -> se copia ese MISMO color al Base Color del Principled solo en esta sesión de
    # render (el archivo no se guarda; forma/cara/ropa/colores del molde no cambian).
    col = []
    for m in bpy.data.materials:
        if not m.node_tree: continue
        dc = tuple(m.diffuse_color)
        if all(abs(x - 0.8) < 1e-3 for x in dc[:3]): continue
        for nd in m.node_tree.nodes:
            if nd.type == 'BSDF_PRINCIPLED' and not nd.inputs['Base Color'].is_linked and all(abs(x - 0.8) < 1e-3 for x in nd.inputs['Base Color'].default_value[:3]):
                nd.inputs['Base Color'].default_value = dc; col.append(m.name)
    R['color_molde_desde_diffuse'] = len(col)
    if not luces:
        R['aviso'] = 'el molde de escenario no trae luces: se usa solo el mundo (no se crean luces)'
else:
    sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'MATERIAL'
    sc.display.shading.show_shadows = True
    lo, hi = bbox_set(); cen = (lo + hi) / 2
    cd = bpy.data.cameras.new('REV_cam'); cam = bpy.data.objects.new('REV_' + a.modo, cd); sc.collection.objects.link(cam); sc.camera = cam
    for o in bpy.data.objects:                                   # revisión: techo y muro del frente no tapan (solo en esta vista)
        n = o.name.lower()
        if o.type == 'MESH' and (n.startswith('techo') or n.startswith('rej_') or (a.modo == 'amplia' and n.startswith('muro_frente'))):
            o.hide_render = True
    if a.modo == 'planta':
        cd.type = 'ORTHO'; cd.ortho_scale = max(hi.x - lo.x, hi.y - lo.y) * 1.05; cam.location = (cen.x, cen.y, 6.0); cam.rotation_euler = (0, 0, 0)
        for o in bpy.data.objects:
            if o.type == 'MESH' and o.name.lower().startswith(('muro', 'techo')): o.hide_render = True
    elif a.modo == 'lateral':
        ancho = hi.x - lo.x
        for o in bpy.data.objects:
            if o.type == 'MESH' and any(k in o.name.lower() for k in ('muro', 'pared', 'zoc')):
                cx = sum((o.matrix_world @ Vector(c)).x for c in o.bound_box) / 8
                if cx < lo.x + ancho * 0.3: o.hide_render = True
        cd.lens = 18; cam.location = (lo.x - 1.4, cen.y, 2.4)
        d = Vector((cen.x, cen.y, 0.5)) - cam.location; cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        cd.clip_start = 0.05
    else:
        cd.lens = 18; cam.location = (cen.x, lo.y - 1.2, 2.6)
        d = Vector((cen.x, cen.y, 0.5)) - cam.location; cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        cd.clip_start = 0.05
t0 = time.time(); n = 0
if a.animacion:
    sc.frame_start, sc.frame_end, sc.frame_step = f0, f1, a.paso
    sc.render.filepath = f"{a.out}/f#####"; sc.render.use_file_extension = True
    try: sc.render.use_persistent_data = True
    except Exception: pass
    bpy.ops.render.render(animation=True); n = len(range(f0, f1 + 1, a.paso))
else:
  for f in range(f0, f1 + 1, a.paso):
    sc.frame_set(f); sc.render.filepath = f"{a.out}/f{f:05d}.png"; bpy.ops.render.render(write_still=True); n += 1
R['cuadros'] = n; R['s'] = round(time.time() - t0, 1); R['s_por_cuadro'] = round(R['s'] / max(1, n), 3); R['engine'] = sc.render.engine
try:
    import gpu; R['gpu'] = gpu.platform.renderer_get(); R['gpu_backend'] = gpu.platform.backend_type_get()
except Exception as ex: R['gpu'] = repr(ex)
json.dump(R, open(f"{a.out}/render.json", 'w'), indent=1)
print('RESULT_RENDER', json.dumps(R))
_RENDER_OK = True
