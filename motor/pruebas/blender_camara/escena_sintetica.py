"""Escena sintética para probar la etapa 11 (cámara) en Blender real, sin material de cliente.

Genera una habitación, dos actores genéricos con los huesos de roles_hueso de
camara_v2_config.json y una caja cerrada delante del actor principal para que
la pose pedida falle y el buscador recorra la rejilla completa. También escribe
los insumos SB/4g en el formato que usa puente_sb4g.construir.
Los IDs (actor_a, actor_b, bloque_frente) son de prueba; el motor no los conoce.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

AJUSTES = {'encuadre_fraccion_altura_visible': {'EWS': 8.0, 'WS': 2.2, 'FS': 1.15, 'MFS': 0.85, 'COWBOY': 0.8,
                                                'MS': 0.55, 'MCU': 0.38, 'CU': 0.22, 'ECU': 0.1}}
ELEV = {'sb_angulo_a_elevacion_deg': {'EYELEVEL': 0}}


def _malla_caja(nombre, centro, medida, cortes=0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=centro)
    ob = bpy.context.object
    ob.name = nombre
    ob.scale = medida
    if cortes:
        mod = ob.modifiers.new('sub', 'SUBSURF')
        mod.subdivision_type = 'SIMPLE'
        mod.levels = cortes
        mod.render_levels = cortes
    return ob


def _actor(nombre, pos, giro_deg):
    arm = bpy.data.armatures.new(nombre + '_arm')
    ob = bpy.data.objects.new(nombre, arm)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    huesos = {'raiz': ((0, 0, 0.05), (0, 0, 0.9)), 'pecho': ((0, 0, 0.9), (0, 0, 1.4)), 'cabeza': ((0, 0, 1.45), (0, 0, 1.75)),
              'pie_L': ((0.1, -0.05, 0.02), (0.1, 0.2, 0.02)), 'pie_R': ((-0.1, -0.05, 0.02), (-0.1, 0.2, 0.02))}
    for n, (h, t) in huesos.items():
        b = arm.edit_bones.new(n)
        b.head = h
        b.tail = t
    for n in ('pecho', 'pie_L', 'pie_R'):
        arm.edit_bones[n].parent = arm.edit_bones['raiz']
    arm.edit_bones['cabeza'].parent = arm.edit_bones['pecho']
    bpy.ops.object.mode_set(mode='OBJECT')
    ob.location = pos
    ob.rotation_euler = (0, 0, math.radians(giro_deg))
    bpy.context.view_layer.update()
    partes = [('cuerpo', 'pecho', 'cyl', (0, 0, 0.95), (0.18, 0.18, 0.9), None),
              ('cabeza', 'cabeza', 'sph', (0, 0, 1.6), (0.13, 0.13, 0.15), 'head')]
    for sufijo, hueso, forma, loc, esc, rol in partes:
        if forma == 'cyl':
            bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=1.0, depth=1.0)
        else:
            bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1.0)
        m = bpy.context.object
        m.name = nombre + '.' + sufijo
        m.scale = esc
        mundo = ob.matrix_world @ Vector(loc)
        m.parent = ob
        m.parent_type = 'BONE'
        m.parent_bone = hueso
        bpy.context.view_layer.update()
        m.matrix_world.translation = mundo
        if rol:
            m['semantic_role'] = rol
    return ob


def construir(n_cuadros, fps=24, cortes_entorno=3, giro_actor=True, entorno_animado=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = fps
    sc.render.fps_base = 1.0
    sc.frame_start = 1
    sc.frame_end = n_cuadros
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    _malla_caja('piso', (0, 0, -0.05), (10, 10, 0.1), cortes_entorno)
    for i, (c, s) in enumerate((((0, 5, 1.4), (10, 0.2, 2.8)), ((0, -5, 1.4), (10, 0.2, 2.8)),
                                ((5, 0, 1.4), (0.2, 10, 2.8)), ((-5, 0, 1.4), (0.2, 10, 2.8)))):
        _malla_caja('pared_%d' % i, c, s, cortes_entorno)
    _malla_caja('techo', (0, 0, 2.85), (10, 10, 0.1), cortes_entorno)
    _malla_caja('mesa', (2.5, -2.5, 0.4), (1.2, 0.8, 0.8), cortes_entorno)
    a = _actor('actor_a', (0, 0, 0), 0)
    b = _actor('actor_b', (-1.6, 0.6, 0), -60)
    # Caja cerrada justo donde cae la cámara pedida (frente de actor_a): la pose directa falla holgura.
    _malla_caja('bloque_frente', (0, 2.3, 1.2), (3.2, 2.6, 2.4), cortes_entorno)
    a.animation_data_create()
    a.location = (0, 0, 0)
    a.keyframe_insert('location', frame=1)
    a.location = (0.6, 0.0, 0)
    a.keyframe_insert('location', frame=n_cuadros)
    if giro_actor:
        a.rotation_euler = (0, 0, 0)
        a.keyframe_insert('rotation_euler', frame=1)
        a.rotation_euler = (0, 0, math.radians(35))
        a.keyframe_insert('rotation_euler', frame=n_cuadros)
    if entorno_animado:
        # Hoja que gira y un bloque que se deforma con shape key: el BVH del escenario cambia por cuadro.
        hoja = _malla_caja('hoja_giratoria', (-1.2, 1.4, 1.0), (0.05, 1.0, 2.0), 1)
        hoja.rotation_euler = (0, 0, 0)
        hoja.keyframe_insert('rotation_euler', frame=1)
        hoja.rotation_euler = (0, 0, math.radians(80))
        hoja.keyframe_insert('rotation_euler', frame=n_cuadros)
        bloque = bpy.data.objects['bloque_frente']
        bloque.shape_key_add(name='base')
        sk = bloque.shape_key_add(name='hundir')
        for v in sk.data:
            v.co.y -= 0.3
        sk.value = 0.0
        sk.keyframe_insert('value', frame=max(1, n_cuadros // 2))
        sk.value = 1.0
        sk.keyframe_insert('value', frame=n_cuadros)
    cd = bpy.data.cameras.new('camara_sintetica')
    cd.sensor_width = 36
    cam = bpy.data.objects.new('camara_sintetica', cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    sc.frame_set(1)
    return sc


def insumos(destino, n_cuadros, fps=24, tomas=2):
    """Escribe entrada/SB/comandos en destino. Devuelve la lista argv que espera camara_v2_blender.py."""
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    dur = n_cuadros / fps
    paso = dur / tomas
    vinetas, escena, comandos, shots = [], [], {}, []
    for i in range(tomas):
        vid = 'v%02d' % (i + 1)
        t0, t1 = round(i * paso, 6), round((i + 1) * paso, 6)
        mov = 'STATIC' if i % 2 == 0 else 'TRACK'
        vinetas.append({'vineta': vid, 't_abs': [t0, t1], 'objetivo': 'actor_a', 'lado_objetivo': 'C',
                        'keyframes': [{'t': t0, 'plano': 'MS', 'lente_mm': 35}],
                        'segmentos': [{'t_abs': [t0, t1], 'movimiento': mov, 'args': {}}]})
        escena.append({'id': vid, 'director_imagen': {'en_cuadro': [{'id': 'actor_a', 'orientacion': 'frontal'}]},
                       'continuidad': {}, 'transicion_salida': {'tipo': 'CORTE'}})
        comandos[vid] = {'encuadre': [['MS', {}], ['EYELEVEL', {}], ['LENS', {'mm': 35}], ['CENTER', {}]],
                         'movimiento': [[0, t1 - t0, mov, {}]]}
        shots.append({'id': vid, 'vineta': vid, 'elevation_deg': 0, 'sensor_width_mm': 36})
    entrada = {'actors': [{'id': 'actor_a', 'spec': {'altura_m': 1.75}}, {'id': 'actor_b', 'spec': {'altura_m': 1.75}}],
               'camera': {'sensor_width_mm': 36, 'shots': shots}, 'bindings': {}, 'environment': {}}
    archivos = {'entrada.json': entrada, 'sb_camara.json': {'escena': 'S', 'vinetas': vinetas},
                'sb_escena.json': {'vinetas': escena}, 'ajustes.json': AJUSTES, 'comandos.json': comandos,
                'elevaciones.json': ELEV, 'tipos_plano.json': {'tipos': []}}
    for nombre, data in archivos.items():
        (destino / nombre).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    return archivos
