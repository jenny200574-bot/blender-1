"""Despeje de escenario para render y validación: visible_camera por toma (R12)."""
import json

from camara_directa_exp import es_entidad_historia, es_geometria_escenario_auto

FUENTES_VISIBLE_CAMERA = (
    'https://docs.blender.org/manual/en/4.2/render/eevee/object_settings/object_data.html — Ray Visibility → Camera (EEVEE 4.2 alineado con Cycles)',
    'https://docs.blender.org/manual/en/4.2/render/cycles/object_settings/object_data.html — Ray Visibility → Camera',
)


def objeto_permitido_despeje(nombre, act_ids=(), act_mesh_names=()):
    """Solo envolvente de escenario; nunca personajes ni props de historia."""
    if not nombre:
        return False
    low = nombre.lower()
    if low.startswith('ch-') or low.startswith('obj-'):
        return False
    if es_entidad_historia(nombre, act_ids, act_mesh_names):
        return False
    return es_geometria_escenario_auto(nombre)


def filtrar_objetos_despeje(nombres, act_ids=(), act_mesh_names=()):
    salida = []
    for n in nombres or []:
        if not objeto_permitido_despeje(n, act_ids, act_mesh_names):
            raise ValueError('Despeje prohibido (contrato): %s' % n)
        salida.append(n)
    return salida


def _fijar_constante_ruta(ob, data_path):
    from curvas_accion import fijar_constante

    ad = getattr(ob, 'animation_data', None)
    if not ad or not ad.action:
        return
    for fc in ad.action.fcurves:
        if fc.data_path == data_path:
            for kp in fc.keyframe_points:
                kp.interpolation = 'CONSTANT'
    fijar_constante(ad.action)


def aplicar_visible_camera_toma(bpy, nombres, f0, f1, toma_id):
    """
    visible_camera=False solo en [f0..f1]; CONSTANT en bordes.
    No modifica hide_render, hide_viewport ni sombras (visible_shadow intacto).
    """
    nombres = list(nombres)
    if f1 < f0:
        raise ValueError('Rango de toma inválido para despeje')
    f_restaurar = int(f1) + 1
    f_antes = max(1, int(f0) - 1) if int(f0) > 1 else None
    aplicados = []
    for name in nombres:
        ob = bpy.data.objects.get(name)
        if ob is None:
            raise ValueError('Objeto despeje ausente en escena: %s' % name)
        if ob.type != 'MESH':
            continue
        if f_antes is not None and f_antes < f0:
            ob.visible_camera = True
            ob.keyframe_insert(data_path='visible_camera', frame=f_antes)
        ob.visible_camera = False
        ob.keyframe_insert(data_path='visible_camera', frame=int(f0))
        ob.visible_camera = True
        ob.keyframe_insert(data_path='visible_camera', frame=f_restaurar)
        _fijar_constante_ruta(ob, 'visible_camera')
        ob['motor_despeje_camara'] = json.dumps(
            {'toma': toma_id, 'f0': int(f0), 'f1': int(f1), 'propiedad': 'visible_camera'},
            ensure_ascii=False,
        )
        aplicados.append(name)
    return aplicados


def _co_x(p):
    c = p.co
    return float(c.x if hasattr(c, 'x') else c[0])


def _co_y(p):
    c = p.co
    return float(c.y if hasattr(c, 'y') else c[1])


def _fcurve_visible_camera(action):
    if action is None:
        return None
    fcs = getattr(action, 'fcurves', None) or []
    find = getattr(fcs, 'find', None)
    if find is not None:
        return find('visible_camera')
    for fc in fcs:
        if fc.data_path == 'visible_camera':
            return fc
    return None


def valor_visible_camera_en_cuadro(action, frame):
    """Interpola visible_camera en el cuadro (para tests sin depsgraph)."""
    fc = _fcurve_visible_camera(action)
    if fc is None:
        return None
    pts = sorted(fc.keyframe_points, key=_co_x)
    if not pts:
        return None
    v = _co_y(pts[0])
    for p in pts:
        if _co_x(p) <= frame:
            v = _co_y(p)
        else:
            break
    return v > 0.5


def comprobar_fcurve_despeje(ob, f0, f1):
    """Devuelve None si OK; si no, motivo corto."""
    if ob is None:
        return 'objeto_ausente'
    ad = getattr(ob, 'animation_data', None)
    if not ad or not ad.action:
        return 'despeje_registrado_sin_fcurve_visible_camera'
    fc = _fcurve_visible_camera(ad.action)
    if fc is None:
        return 'despeje_registrado_sin_fcurve_visible_camera'
    f_rest = int(f1) + 1
    frames_requeridos = {int(f0): False, f_rest: True}
    if int(f0) > 1:
        frames_requeridos[max(1, int(f0) - 1)] = True
    encontrados = {}
    for kp in fc.keyframe_points:
        fr = int(round(_co_x(kp)))
        encontrados[fr] = _co_y(kp) > 0.5
    for fr, debe_visible in frames_requeridos.items():
        if fr not in encontrados:
            return 'fcurve_visible_camera_incompleta_cuadro_%d' % fr
        if encontrados[fr] != debe_visible:
            return 'fcurve_visible_camera_valor_incorrecto_cuadro_%d' % fr
    for kp in fc.keyframe_points:
        if kp.interpolation != 'CONSTANT':
            return 'fcurve_visible_camera_sin_interpolacion_CONSTANT'
    return None


def revisar_despeje_etapa13(bpy, tomas, registro_bvh_huérfano=None):
    """
    Falla si hay despeje en JSON sin fcurve, o visible_camera=True en rango de toma despejada,
    o registro legacy solo BVH (anti falso pase).
    """
    errores = []
    for t in tomas or []:
        tid = t.get('vineta') or t.get('toma')
        exp = (t.get('experimental_directa') or {})
        des = exp.get('despeje_escenario') or {}
        objs = des.get('objetos') or des.get('objetos_excluidos_bvh') or []
        if not objs:
            continue
        nota = (des.get('nota') or '')
        if 'Solo exclusión en BVH' in nota:
            errores.append({
                'type': 'DESPEJE_FALSO_PASE',
                'shot': tid,
                'details': ['despeje solo BVH sin visible_camera en escena'],
            })
            continue
        f0, f1 = int(t['frame_ini']), int(t['frame_fin'])
        for name in objs:
            if not objeto_permitido_despeje(name):
                errores.append({
                    'type': 'DESPEJE_PROHIBIDO',
                    'shot': tid,
                    'object': name,
                    'details': ['objeto no es envolvente de escenario'],
                })
                continue
            ob = bpy.data.objects.get(name)
            motivo = comprobar_fcurve_despeje(ob, f0, f1)
            if motivo:
                errores.append({
                    'type': 'DESPEJE_SIN_FCURVE',
                    'shot': tid,
                    'object': name,
                    'details': [motivo],
                })
    if registro_bvh_huérfano:
        errores.append({
            'type': 'DESPEJE_FALSO_PASE',
            'details': [str(registro_bvh_huérfano)],
        })
    return errores
