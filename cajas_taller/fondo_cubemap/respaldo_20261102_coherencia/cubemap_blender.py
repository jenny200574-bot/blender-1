"""FC · fondo cubemap (Blender, GRATIS, sin red). Uso:
blender -b ESCENA.blend --python cubemap_blender.py -- cubo  --salida DIR [--origen CAM] [--res 1024] [--quitar a,b]
blender -b ESCENA.blend --python cubemap_blender.py -- molde --salida DIR [--cuadros 1,93]
cubo : 1) clona la escena SOLO con el set permanente (sin personajes, Prision_*/Campo_*/poderes/props de escena; ver fc_entorno_fijo.json) (fondo_sin_personajes.blend; el original no se toca)
       2) desde el origen de la cámara, 6 renders grises F/B/L/R/U/D (cubemap, FOV 90) + caras.json (convención de ejes)
molde: por cámara y cuadro, render gris CON personajes (Imagen 2) + camaras.json (matriz, lente, sensor) para proyectar."""
import bpy, sys, json, os, argparse, math
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('modo', choices=['cubo', 'molde']); ap.add_argument('--salida', required=True)
ap.add_argument('--origen', default=''); ap.add_argument('--res', type=int, default=1024)
ap.add_argument('--quitar', default=''); ap.add_argument('--cuadros', default='')
a = ap.parse_args(argv)
os.makedirs(a.salida, exist_ok=True)
S = bpy.context.scene

# Caras: Blender Z arriba. forward/up/right en mundo (la proyección usa exactamente esto).
CARAS = {'F': ((0, 1, 0), (0, 0, 1)), 'B': ((0, -1, 0), (0, 0, 1)), 'R': ((1, 0, 0), (0, 0, 1)),
         'L': ((-1, 0, 0), (0, 0, 1)), 'U': ((0, 0, 1), (0, -1, 0)), 'D': ((0, 0, -1), (0, 1, 0))}


def gris(S):
    S.render.engine = 'BLENDER_WORKBENCH'
    sh = S.display.shading
    sh.light = 'STUDIO'; sh.color_type = 'SINGLE'; sh.single_color = (0.6, 0.6, 0.6)
    try: sh.show_cavity = True
    except Exception: pass
    S.render.film_transparent = False
    S.render.image_settings.file_format = 'PNG'


# ---- ENTORNO FIJO (Ricardo t456u, 2-nov-2026): el cubemap conserva SOLO el set permanente ----
# Config editable: fondo_cubemap/fc_entorno_fijo.json (si falta, se usan estos defaults).
import fnmatch
ENTORNO_DEFAULT = {
    # nombres (objeto o colección, fnmatch sin mayúsculas) que SIEMPRE salen del cubemap
    'excluir_patrones': ['Prision*', '*_Prision*', 'Campo*', '*Poder*', '*Energia*', '*Energy*', '*Power*', '*Rayo*',
                         '*Escudo*', '*Portal*', '*Aura*', '*Hechizo*', '*Explosion*', '*Particula*', '*FX*', 'VFX*',
                         'Prop_Escena*', 'PropEscena*', 'Escena_Prop*', 'Personaje*', 'Character*'],
    # colecciones de set permanente: si la escena tiene alguna, MODO LISTA BLANCA (solo sus objetos quedan)
    'colecciones_set': ['Escenario*', 'Set_*', 'Set', 'Entorno*', 'Fondo*', 'Decorado*'],
    'conservar_tipos_siempre': ['CAMERA'],
    'conservar': []   # nombres exactos que deben quedar aunque caigan en otra regla
}


def entorno_cfg():
    c = dict(ENTORNO_DEFAULT)
    f = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fc_entorno_fijo.json')
    try:
        if os.path.isfile(f): c.update(json.load(open(f, encoding='utf-8')))
    except Exception as e: print('FC aviso fc_entorno_fijo.json ilegible:', e)
    return c


def _m(nombre, pats): return any(fnmatch.fnmatch(nombre.lower(), x.lower()) for x in pats)


NO_SET = []


def no_set(quitar):
    """Quita todo lo que NO es set permanente (además de personajes/animados)."""
    c = entorno_cfg(); exc = c['excluir_patrones']; setp = c['colecciones_set']; keep = set(c.get('conservar') or [])
    hay_set = any(_m(col.name, setp) for col in bpy.data.collections)
    for o in bpy.data.objects:
        if o.name in quitar or o.name in keep or o.type in c['conservar_tipos_siempre']: continue
        cols = [x.name for x in o.users_collection]
        motivo = None
        if _m(o.name, exc): motivo = 'nombre'
        elif any(_m(n, exc) for n in cols): motivo = 'coleccion'
        elif hay_set and o.type != 'LIGHT' and not any(_m(n, setp) for n in cols) and not (o.parent and o.parent.name not in quitar and any(_m(n, setp) for n in [x.name for x in o.parent.users_collection])):
            motivo = 'fuera_del_set'
        if motivo: quitar.add(o.name); NO_SET.append({'objeto': o.name, 'motivo': motivo})
    return hay_set


ANIMADOS = []
MODO_SET = [False]


def personajes(extra):
    """Universal: raíz EMPTY/ARMATURE con >=3 mallas hijas que se llaman «<raíz>_…», toda ARMATURE, y --quitar."""
    quitar = set()
    def desc(o): return [o] + [d for c in o.children for d in desc(c)]
    for o in bpy.data.objects:
        if o.parent is None and o.type in ('EMPTY', 'ARMATURE'):
            d = desc(o)
            if o.type == 'ARMATURE' or sum(1 for x in d if x.type == 'MESH' and x.name.startswith(o.name + '_')) >= 3:
                quitar.update(x.name for x in d)
        if o.type == 'ARMATURE': quitar.update(x.name for x in desc(o))
    for n in [x for x in extra.split(',') if x]:
        o = bpy.data.objects.get(n)
        if o: quitar.update(x.name for x in desc(o))
    # props animados (se mueven/aparecen): no son fondo fijo -> van en el molde (Imagen 2), no en el cubemap
    for o in bpy.data.objects:
        if o.parent is None and o.type == 'MESH' and o.animation_data and o.animation_data.action and o.name not in quitar:
            quitar.update(x.name for x in desc(o)); ANIMADOS.append(o.name)
    MODO_SET[0] = no_set(quitar)
    raices = sorted({bpy.data.objects[n].name for n in quitar if bpy.data.objects[n].parent is None or bpy.data.objects[n].parent.name not in quitar})
    return quitar, raices


def camara_origen(nombre):
    if nombre and bpy.data.objects.get(nombre) and bpy.data.objects[nombre].type == 'CAMERA': return bpy.data.objects[nombre]
    if S.camera: return S.camera
    cs = [o for o in bpy.data.objects if o.type == 'CAMERA']
    return cs[0] if cs else None


if a.modo == 'cubo':
    S.frame_set(S.frame_start)
    cam0 = camara_origen(a.origen)
    if cam0 is None: print('FC_JSON ' + json.dumps({'ok': False, 'error': 'la escena no tiene cámara'})); sys.exit(0)
    origen = cam0.matrix_world.translation.copy()
    q, raices = personajes(a.quitar)
    for n in q:
        o = bpy.data.objects.get(n)
        if o: bpy.data.objects.remove(o, do_unlink=True)
    clon = os.path.join(a.salida, 'fondo_sin_personajes.blend')
    bpy.ops.wm.save_as_mainfile(filepath=clon, copy=True)   # copia: el .blend original queda intacto
    cd = bpy.data.cameras.new('FC_cubo'); c = bpy.data.objects.new('FC_cubo', cd); S.collection.objects.link(c)
    cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0; cd.lens = 18.0   # 2*atan(18/36) = 90°
    cd.clip_start = 0.01; cd.clip_end = 1000
    S.camera = c; gris(S)
    S.render.resolution_x = S.render.resolution_y = a.res; S.render.resolution_percentage = 100
    caras = {}
    for k, (fw, up) in CARAS.items():
        f = Vector(fw); u = Vector(up); r = f.cross(u)
        M = Matrix((r, u, -f)).transposed()   # columnas: x=derecha, y=arriba, z=-adelante
        c.matrix_world = Matrix.Translation(origen) @ M.to_4x4()
        out = os.path.join(a.salida, 'gris', f'{k}.png'); S.render.filepath = out
        bpy.ops.render.render(write_still=True)
        caras[k] = {'adelante': list(fw), 'arriba': list(up), 'derecha': list(r), 'png': out}
    info = {'ok': True, 'origen': list(origen), 'camara_origen': cam0.name, 'res': a.res, 'caras': caras,
            'personajes_quitados': [r for r in raices if r not in ANIMADOS and r not in {x['objeto'] for x in NO_SET}], 'props_animados_quitados': ANIMADOS, 'no_set_quitados': NO_SET, 'modo_lista_blanca_set': MODO_SET[0], 'objetos_quitados': len(q), 'clon_sin_personajes': clon}
    json.dump(info, open(os.path.join(a.salida, 'caras.json'), 'w'), indent=1)
    print('FC_JSON ' + json.dumps(info))
else:
    gris(S)
    cuadros = [int(x) for x in a.cuadros.split(',') if x] or [S.frame_start]
    W = int(S.render.resolution_x * S.render.resolution_percentage / 100); H = int(S.render.resolution_y * S.render.resolution_percentage / 100)
    tomas = []
    for cam in [o for o in bpy.data.objects if o.type == 'CAMERA']:
        for fr in cuadros:
            S.frame_set(fr); S.camera = cam
            tid = f'{cam.name}_f{fr:03d}'; out = os.path.join(a.salida, 'tomas', tid, 'imagen2_molde.png')
            S.render.filepath = out; bpy.ops.render.render(write_still=True)
            d = cam.data
            tomas.append({'toma': tid, 'camara': cam.name, 'cuadro': fr, 'matriz': [list(r) for r in cam.matrix_world],
                          'lente_mm': d.lens, 'sensor_w': d.sensor_width, 'sensor_h': d.sensor_height, 'sensor_fit': d.sensor_fit,
                          'tipo': d.type, 'shift': [d.shift_x, d.shift_y], 'W': W, 'H': H, 'molde': out})
    info = {'ok': True, 'tomas': tomas}
    json.dump(info, open(os.path.join(a.salida, 'camaras.json'), 'w'), indent=1)
    print('FC_JSON ' + json.dumps({'ok': True, 'n_tomas': len(tomas)}))
