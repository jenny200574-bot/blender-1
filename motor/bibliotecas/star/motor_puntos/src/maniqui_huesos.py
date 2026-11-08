"""maniqui_huesos.py — Star · MYIA · US$0
Maniquí de cápsulas/cilindros CON armature J_Bip_* (compatible con motor de puntos).
Cuerpo desde ficha: altura_m, gordura, colores, pulsera, gafas.
Look aprobado (azotea): cápsula de color de ficha + pulsera cian si la ficha lo dice.
Nada inventado: si falta color de cuerpo, FALTA y usa gris técnico marcado.
"""
from __future__ import annotations
import bpy, math, json
from mathutils import Vector, Matrix, Quaternion
from pathlib import Path

# Proporciones base (metros) a altura 1.72 — escalan con altura_m
BASE_H = 1.72

def _col4(c):
    if c is None: return (0.55, 0.55, 0.58, 1.0)
    if len(c) == 3: return (float(c[0]), float(c[1]), float(c[2]), 1.0)
    return tuple(float(x) for x in c[:4])

def _cil(nombre, color, a, b, r, parent=None, parent_bone=None):
    a, b = Vector(a), Vector(b)
    d = b - a
    L = max(d.length, 1e-4)
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=L, location=(a + b) / 2, vertices=16)
    o = bpy.context.object
    o.name = nombre
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d if d.length > 1e-6 else Vector((0, 0, 1)))
    o.color = _col4(color)
    if parent is not None:
        mw = o.matrix_world.copy()
        o.parent = parent
        if parent_bone:
            o.parent_type = 'BONE'
            o.parent_bone = parent_bone
        bpy.context.view_layer.update()
        o.matrix_world = mw
    return o

def _esf(nombre, color, p, r, esc=(1, 1, 1), parent=None, parent_bone=None):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=p, segments=16, ring_count=8)
    o = bpy.context.object
    o.name = nombre
    o.scale = esc
    o.color = _col4(color)
    if parent is not None:
        mw = o.matrix_world.copy()
        o.parent = parent
        if parent_bone:
            o.parent_type = 'BONE'
            o.parent_bone = parent_bone
        bpy.context.view_layer.update()
        o.matrix_world = mw
    return o

def _add_bone(arm, name, head, tail, parent=None):
    eb = arm.edit_bones.new(name)
    eb.head = Vector(head)
    eb.tail = Vector(tail)
    if parent is not None:
        eb.parent = arm.edit_bones[parent]
        eb.use_connect = False
    return eb

def _color_cuerpo(K, faltas, pid):
    """Color principal del maniquí. Preferencia: ropa_superior → piel → FALTA gris."""
    for key in ('colores.ropa_superior', 'colores.piel', 'colores.cara'):
        v = K.get(key)
        if isinstance(v, (list, tuple)) and len(v) >= 3:
            return tuple(float(x) for x in v[:3]), None
    faltas.append(f'FALTA color cuerpo en ficha de {pid}; uso gris técnico')
    return (0.55, 0.55, 0.58), 'falta_color'

def construir(pid, altura, K, color_override=None):
    """Construye maniquí con huesos. Devuelve dict compatible con video_o114 (root, objs, A, tipo, ...).
    K = controles de parametros_3d.
    """
    faltas = []
    h = float(altura or BASE_H)
    s = h / BASE_H
    g = K.get('gordura') or {}
    gt = float(g.get('torso', 1.0))
    gc = float(g.get('cadera', 1.0))
    gp = float(g.get('piernas', 1.0))
    gb = float(g.get('brazos', 1.0))
    gcara = float(g.get('cara', 1.0))

    if color_override is not None:
        cuerpo = tuple(float(x) for x in color_override[:3])
    else:
        cuerpo, _ = _color_cuerpo(K, faltas, pid)

    # --- Armature en T-pose ligera (brazos ligeramente abajo), mira −Y como VRM ---
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    A = bpy.context.object
    A.name = f'MAN_{pid}'
    arm = A.data
    arm.name = f'MAN_{pid}_data'
    # quitar hueso default
    for b in list(arm.edit_bones):
        arm.edit_bones.remove(b)

    # Alturas locales (z) a escala 1.72 luego *s
    z_pie = 0.05 * s
    z_tobillo = 0.08 * s
    z_rodilla = 0.50 * s
    z_cadera = 0.95 * s
    z_spine = 1.10 * s
    z_chest = 1.28 * s
    z_upper = 1.40 * s
    z_neck = 1.50 * s
    z_head = 1.60 * s
    z_head_tip = 1.72 * s
    hx = 0.20 * s   # hombro x
    cx = 0.11 * s   # cadera pierna x

    _add_bone(arm, 'Root', (0, 0, 0), (0, 0, 0.05 * s))
    _add_bone(arm, 'J_Bip_C_Hips', (0, 0, z_cadera), (0, 0, z_cadera + 0.02 * s), 'Root')
    _add_bone(arm, 'J_Bip_C_Spine', (0, 0, z_cadera), (0, 0, z_spine), 'J_Bip_C_Hips')
    _add_bone(arm, 'J_Bip_C_Chest', (0, 0, z_spine), (0, 0, z_chest), 'J_Bip_C_Spine')
    _add_bone(arm, 'J_Bip_C_UpperChest', (0, 0, z_chest), (0, 0, z_upper), 'J_Bip_C_Chest')
    _add_bone(arm, 'J_Bip_C_Neck', (0, 0, z_upper), (0, 0, z_neck), 'J_Bip_C_UpperChest')
    _add_bone(arm, 'J_Bip_C_Head', (0, 0, z_neck), (0, 0, z_head_tip), 'J_Bip_C_Neck')

    # Hombros / brazos (T → ligeramente abajo)
    for L, sx in (('L', -1), ('R', 1)):
        _add_bone(arm, f'J_Bip_{L}_Shoulder', (0, 0, z_upper), (sx * hx * 0.5, 0, z_upper), 'J_Bip_C_UpperChest')
        _add_bone(arm, f'J_Bip_{L}_UpperArm', (sx * hx * 0.5, 0, z_upper), (sx * hx, 0, z_upper - 0.02 * s), f'J_Bip_{L}_Shoulder')
        _add_bone(arm, f'J_Bip_{L}_LowerArm', (sx * hx, 0, z_upper - 0.02 * s), (sx * (hx + 0.04 * s), 0, z_upper - 0.28 * s), f'J_Bip_{L}_UpperArm')
        _add_bone(arm, f'J_Bip_{L}_Hand', (sx * (hx + 0.04 * s), 0, z_upper - 0.28 * s), (sx * (hx + 0.06 * s), 0, z_upper - 0.40 * s), f'J_Bip_{L}_LowerArm')

    # Piernas
    for L, sx in (('L', -1), ('R', 1)):
        _add_bone(arm, f'J_Bip_{L}_UpperLeg', (sx * cx, 0, z_cadera), (sx * cx, 0, z_rodilla), 'J_Bip_C_Hips')
        _add_bone(arm, f'J_Bip_{L}_LowerLeg', (sx * cx, 0, z_rodilla), (sx * cx, 0, z_tobillo), f'J_Bip_{L}_UpperLeg')
        _add_bone(arm, f'J_Bip_{L}_Foot', (sx * cx, 0, z_tobillo), (sx * cx, -0.12 * s, z_pie), f'J_Bip_{L}_LowerLeg')

    bpy.ops.object.mode_set(mode='OBJECT')

    # --- Mallas cápsula parentadas a huesos (estilo azotea) ---
    objs = []
    def hw(n):
        return A.matrix_world @ A.data.bones[n].head_local
    def tw(n):
        return A.matrix_world @ A.data.bones[n].tail_local

    # torso
    objs.append(_cil(f'{pid}_torso', cuerpo, hw('J_Bip_C_Hips'), hw('J_Bip_C_UpperChest'), 0.15 * s * gt, A, 'J_Bip_C_Spine'))
    objs.append(_esf(f'{pid}_cadera', cuerpo, hw('J_Bip_C_Hips'), 0.16 * s * gc, parent=A, parent_bone='J_Bip_C_Hips'))
    objs.append(_cil(f'{pid}_cuello', cuerpo, hw('J_Bip_C_Neck'), hw('J_Bip_C_Head'), 0.05 * s, A, 'J_Bip_C_Neck'))
    objs.append(_esf(f'{pid}_cabeza', cuerpo, (hw('J_Bip_C_Head') + tw('J_Bip_C_Head')) / 2, 0.12 * s * gcara, parent=A, parent_bone='J_Bip_C_Head'))
    # nariz (mira −Y)
    cab = (hw('J_Bip_C_Head') + tw('J_Bip_C_Head')) / 2
    objs.append(_esf(f'{pid}_nariz', (0.9, 0.5, 0.1), (cab.x, cab.y - 0.12 * s, cab.z), 0.03 * s, parent=A, parent_bone='J_Bip_C_Head'))

    for L, sx in (('L', -1), ('R', 1)):
        objs.append(_cil(f'{pid}_hombro{L}', cuerpo, hw(f'J_Bip_{L}_Shoulder'), hw(f'J_Bip_{L}_UpperArm'), 0.06 * s * gb, A, f'J_Bip_{L}_Shoulder'))
        objs.append(_cil(f'{pid}_brazo{L}', cuerpo, hw(f'J_Bip_{L}_UpperArm'), hw(f'J_Bip_{L}_LowerArm'), 0.05 * s * gb, A, f'J_Bip_{L}_UpperArm'))
        objs.append(_cil(f'{pid}_antebrazo{L}', cuerpo, hw(f'J_Bip_{L}_LowerArm'), hw(f'J_Bip_{L}_Hand'), 0.045 * s * gb, A, f'J_Bip_{L}_LowerArm'))
        objs.append(_esf(f'{pid}_mano{L}', cuerpo, hw(f'J_Bip_{L}_Hand'), 0.05 * s * gb, parent=A, parent_bone=f'J_Bip_{L}_Hand'))
        objs.append(_cil(f'{pid}_muslo{L}', cuerpo, hw(f'J_Bip_{L}_UpperLeg'), hw(f'J_Bip_{L}_LowerLeg'), 0.07 * s * gp, A, f'J_Bip_{L}_UpperLeg'))
        objs.append(_cil(f'{pid}_pierna{L}', cuerpo, hw(f'J_Bip_{L}_LowerLeg'), hw(f'J_Bip_{L}_Foot'), 0.06 * s * gp, A, f'J_Bip_{L}_LowerLeg'))
        objs.append(_esf(f'{pid}_pie{L}', cuerpo, tw(f'J_Bip_{L}_Foot'), 0.05 * s * gp, esc=(1.2, 1.6, 0.7), parent=A, parent_bone=f'J_Bip_{L}_Foot'))

    ACCN = None
    muneca_acc = None
    # Pulsera
    pu = K.get('pulsera')
    if isinstance(pu, dict):
        lado = 'L' if pu.get('muneca') == 'izquierda' else 'R'
        muneca_acc = lado
        w = hw(f'J_Bip_{lado}_Hand')
        lo = hw(f'J_Bip_{lado}_LowerArm')
        p = lo * 0.25 + w * 0.75
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.065 * s, location=p, segments=12, ring_count=8)
        o = bpy.context.object
        o.name = f'ACC_{pid}_muneca'
        o.color = _col4(pu.get('color') or (0.05, 0.95, 1.0))
        ACCN = o.name
        mw = o.matrix_world.copy()
        o.parent = A
        o.parent_type = 'BONE'
        o.parent_bone = f'J_Bip_{lado}_LowerArm'
        bpy.context.view_layer.update()
        o.matrix_world = mw
        objs.append(o)

    # Gafas
    if K.get('gafas'):
        H = (hw('J_Bip_C_Head') + tw('J_Bip_C_Head')) / 2
        gc_ = K.get('gafas_color') or (0.02, 0.02, 0.02)
        for sx in (-1, 1):
            bpy.ops.mesh.primitive_torus_add(major_radius=0.028 * s, minor_radius=0.005 * s,
                                            location=(H.x + sx * 0.033 * s, H.y - 0.105 * s, H.z + 0.02 * s),
                                            rotation=(math.radians(90), 0, 0))
            o = bpy.context.object
            o.name = f'ACC_{pid}_gafa_{sx}'
            o.color = _col4(gc_)
            mw = o.matrix_world.copy()
            o.parent = A
            o.parent_type = 'BONE'
            o.parent_bone = 'J_Bip_C_Head'
            bpy.context.view_layer.update()
            o.matrix_world = mw
            objs.append(o)

    # Pelo largo (novia)
    pl = K.get('pelo_largo')
    if isinstance(pl, dict):
        H = (hw('J_Bip_C_Head') + tw('J_Bip_C_Head')) / 2
        Ls = float(pl.get('largo_m', 0.5)) * s
        c_ = pl.get('color') or (0.1, 0.1, 0.1)
        bpy.ops.mesh.primitive_cone_add(radius1=0.13 * s, radius2=0.05 * s, depth=Ls,
                                        location=(H.x, H.y + 0.05 * s, H.z - Ls / 3), vertices=16)
        o = bpy.context.object
        o.name = f'ACC_{pid}_pelo'
        o.color = _col4(c_)
        mw = o.matrix_world.copy()
        o.parent = A
        o.parent_type = 'BONE'
        o.parent_bone = 'J_Bip_C_Head'
        bpy.context.view_layer.update()
        o.matrix_world = mw
        objs.append(o)

    # Pose reposo: brazos un poco abajo (como VRM de_pie del motor)
    pb = A.pose.bones
    for n, ang in (('J_Bip_L_UpperArm', 55), ('J_Bip_R_UpperArm', -55)):
        if n not in pb:
            continue
        b = A.data.bones[n]
        R = Matrix.Rotation(math.radians(ang), 3, 'Y')
        Mb = b.matrix_local.to_3x3()
        pb[n].rotation_mode = 'QUATERNION'
        pb[n].rotation_quaternion = (Mb.inverted() @ R @ Mb).to_quaternion()
    bpy.context.view_layer.update()

    return {
        'root': A,
        'objs': objs,
        'tipo': 'maniqui_huesos',
        'A': A,
        'acc': ACCN,
        'muneca_acc': muneca_acc,
        'giro_base': 90,
        'faltas': faltas,
        'color_cuerpo': list(cuerpo),
    }


def aplicar_limites_canal(pb, bn, canal, c, lib_arts=None):
    """Clamp c a [0,1]. Si hay lib de articulaciones, tope de ángulo según AAOS.
    Devuelve (c_usado, ang_rad_sugerido o None).
    """
    c = max(0.0, min(1.0, float(c)))
    if lib_arts is None:
        return c, None
    # Mapa canal+hueso → articulación/movimiento
    mapa = {
        ('flexion', 'J_Bip_L_LowerLeg'): ('rodilla_L', 'flexion'),
        ('flexion', 'J_Bip_R_LowerLeg'): ('rodilla_R', 'flexion'),
        ('flexion', 'J_Bip_L_LowerArm'): ('codo_L', 'flexion'),
        ('flexion', 'J_Bip_R_LowerArm'): ('codo_R', 'flexion'),
        ('subir', 'J_Bip_L_UpperArm'): ('hombro_L', 'flexion'),
        ('subir', 'J_Bip_R_UpperArm'): ('hombro_R', 'flexion'),
        ('inclinacion', 'J_Bip_C_Spine'): ('torso', 'flexion'),
        ('inclinacion', 'J_Bip_C_Head'): ('cuello', 'flexion'),
        ('giro', 'J_Bip_C_Spine'): ('torso', 'rotacion_izq'),
        ('giro', 'J_Bip_C_Head'): ('cuello', 'rotacion_izq'),
    }
    key = (canal, bn)
    if key not in mapa:
        return c, None
    art, mov = mapa[key]
    try:
        m = lib_arts['articulaciones'][art]['movimientos'][mov]
        rest = float(m.get('rest_deg', 0))
        mx = float(m['max_deg'])
        ang = rest + c * (mx - rest)
        # cartoon ~80% del rango médico
        ang = ang * 0.80
        return c, math.radians(ang)
    except KeyError:
        return c, None
