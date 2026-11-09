"""Inspección de solo lectura de un actor en cuadros ya construidos.

No guarda el .blend, no mueve la cámara y no decide si la toma pasa.
La cabeza que agrega el constructor después de abrir el núcleo no está en el
.blend del núcleo: para ver ese estado hay que llamar escribir() dentro del
constructor, con SONDA_CAMARA=1, o abrir un .blend guardado después de esa etapa.

Uso directo, sin escribir la escena:
  blender -b nucleo/escena.blend -P sonda_inspeccion_camara.py -- \
    --actor ID --frames 433,468,504,601,660,720 --salida /tmp/sonda_camara.json \
    --config camara_v2_config.json
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

from malla_cabeza import malla_es_cabeza


def _roles(config):
    if not config or not Path(config).is_file():
        return {}
    data = json.loads(Path(config).read_text(encoding='utf-8'))
    roles = data.get('roles_hueso') or {}
    return roles if isinstance(roles, dict) else {}


def _caja(obj):
    try:
        puntos = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    except (TypeError, AttributeError, ValueError):
        return None
    if not puntos:
        return None
    lo = [min(p[i] for p in puntos) for i in range(3)]
    hi = [max(p[i] for p in puntos) for i in range(3)]
    return {'min': [round(x, 4) for x in lo], 'max': [round(x, 4) for x in hi]}


def _malla(obj, dg):
    try:
        ev = obj.evaluated_get(dg)
    except (AttributeError, RuntimeError):
        ev = None
    verts = None
    if ev is not None and getattr(ev, 'type', None) == 'MESH':
        mesh = ev.to_mesh()
        try:
            verts = len(mesh.vertices)
        finally:
            ev.to_mesh_clear()
    try:
        visible = bool(obj.visible_get())
    except (AttributeError, RuntimeError):
        visible = None
    return {
        'nombre': obj.name,
        'parent_type': obj.parent_type,
        'parent_bone': obj.parent_bone or None,
        'hide_viewport': bool(obj.hide_viewport),
        'hide_render': bool(obj.hide_render),
        'visible_get': visible,
        'semantic_role': obj.get('semantic_role'),
        'role': obj.get('role'),
        'bind_role': obj.get('bind_role'),
        'motor_preserve_hidden': bool(obj.get('motor_preserve_hidden')),
        'claves_hide_render': _claves_hide(obj),
        'vertices_evaluados': verts,
        'bbox_mundo': _caja(obj),
    }


def _claves_hide(obj):
    """Cuadros y valores de hide_render. No copia la acción ni el ADN."""
    anim = getattr(obj, 'animation_data', None)
    action = None if anim is None else anim.action
    if action is None:
        return []
    from curvas_accion import curvas_de_accion
    claves = []
    for curva in curvas_de_accion(action):
        if getattr(curva, 'data_path', None) != 'hide_render':
            continue
        for punto in curva.keyframe_points:
            claves.append({'frame': int(round(punto.co[0])), 'hide_render': bool(round(punto.co[1]))})
    return claves


def inspeccionar(ctx, actor, frames, config=None):
    """Lee el depsgraph. No modifica la escena."""
    roles = _roles(config)
    cabeza = set(roles.get('cabeza') or [])
    obj = bpy.data.objects.get(actor)
    if obj is None:
        return {'actor': actor, 'existe': False, 'cuadros': [], 'production_approved': False,
                'nota': 'Ese objeto no está en este .blend. Si es el núcleo, la cabeza puede crearse después, en el constructor.'}
    informe = {'actor': actor, 'existe': True, 'tipo': obj.type, 'production_approved': False, 'cuadros': [],
               'nota': 'Lectura del blend abierto. hide_* y los vértices evaluados distinguen malla ausente, oculta y deformada. No es una aprobación.'}
    for f in frames:
        ctx.scene.frame_set(int(f))
        dg = ctx.evaluated_depsgraph_get()
        hijos = [x for x in obj.children_recursive if x.type == 'MESH']
        mallas = [_malla(x, dg) for x in hijos]
        de_cabeza = [x for x in mallas if malla_es_cabeza(x, cabeza)]
        huesos = {}
        if obj.type == 'ARMATURE':
            mw = obj.matrix_world
            for nombre, hueso in obj.pose.bones.items():
                if cabeza and nombre not in cabeza and nombre not in set(roles.get('pecho') or []) and nombre not in set(roles.get('pies') or []):
                    continue
                head = mw @ hueso.head
                tail = mw @ hueso.tail
                huesos[nombre] = {'head': [round(float(v), 4) for v in head], 'tail': [round(float(v), 4) for v in tail]}
        rayo = None
        cam = ctx.scene.camera
        if cam is not None and obj.type == 'ARMATURE' and huesos:
            origen = next(iter(huesos.values()))['head']
            destino = cam.matrix_world.translation
            dir_ = Vector(destino) - Vector(origen)
            largo = dir_.length
            if largo > 1e-6:
                propios = {obj.name} | {x.name for x in obj.children_recursive}
                origen_v = Vector(origen)
                direccion = dir_.normalized()
                restante = largo
                propio = None
                externo = None
                for _ in range(6):
                    hit, loc, _normal, _index, hit_obj, _matrix = ctx.scene.ray_cast(dg, origen_v, direccion, distance=restante)
                    if not hit or hit_obj is None:
                        break
                    dist = (Vector(loc) - Vector(origen)).length
                    if hit_obj.name in propios:
                        if propio is None:
                            propio = {'objeto': hit_obj.name, 'distancia_m': round(dist, 4)}
                        origen_v = Vector(loc) + direccion * 0.002
                        restante = largo - (origen_v - Vector(origen)).length
                        if restante <= 0.002:
                            break
                        continue
                    externo = {'objeto': hit_obj.name, 'distancia_m': round(dist, 4)}
                    break
                rayo = {'golpe_propio': propio, 'golpe_externo': externo, 'no_es_validacion': True}
        informe['cuadros'].append({
            'frame': int(f),
            'mallas': len(mallas),
            'mallas_cabeza': len(de_cabeza),
            'vertices_cabeza': sum(x['vertices_evaluados'] or 0 for x in de_cabeza),
            'detalle_cabeza': de_cabeza,
            'huesos': huesos,
            'rayo_hacia_camara': rayo,
        })
    return informe


def escribir(ctx, actor, frames, salida, config=None):
    path = Path(salida)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(inspeccionar(ctx, actor, frames, config), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return path


def _args(argv):
    if '--' in argv:
        argv = argv[argv.index('--') + 1:]
    out = {'actor': '', 'frames': [], 'salida': '', 'config': ''}
    i = 0
    while i < len(argv):
        if argv[i] == '--actor' and i + 1 < len(argv):
            out['actor'] = argv[i + 1]; i += 2
        elif argv[i] == '--frames' and i + 1 < len(argv):
            out['frames'] = [int(x) for x in argv[i + 1].split(',') if x.strip()]; i += 2
        elif argv[i] == '--salida' and i + 1 < len(argv):
            out['salida'] = argv[i + 1]; i += 2
        elif argv[i] == '--config' and i + 1 < len(argv):
            out['config'] = argv[i + 1]; i += 2
        else:
            i += 1
    return out


if __name__ == '__main__':
    args = _args(sys.argv)
    if not args['actor'] or not args['frames'] or not args['salida']:
        raise SystemExit('Hacen falta --actor, --frames y --salida. No se inspecciona un id supuesto.')
    escribir(bpy.context, args['actor'], args['frames'], args['salida'], args['config'] or None)
    print('SONDA_CAMARA_OK ' + args['salida'])
