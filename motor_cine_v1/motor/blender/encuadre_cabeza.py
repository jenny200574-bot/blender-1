"""encuadre_cabeza: caja real de la cabeza de cada molde (vértices de la malla que siguen al hueso 'cabeza' y sus hijos),
en espacio del hueso; por cuadro da las 8 esquinas en mundo. Sirve para la cámara (distancia mínima, aire sobre la cabeza)
y para la compuerta (cabeza COMPLETA en cuadro). No modifica nada del molde."""
import bpy
from mathutils import Vector

def _huesos_cabeza(arm):
    b = arm.data.bones.get(hueso_cabeza(arm))
    if b is None: return set()
    return {b.name} | {c.name for c in b.children_recursive}

_HC = {}
def hueso_cabeza(arm):
    """[argon_v2] hueso de la cabeza de CUALQUIER rig: 'cabeza' (fábrica) -> sinónimos (head...) -> el más alto. Cacheado."""
    k = arm.name
    if k not in _HC:
        try:
            import relaciones_blender as RB; _HC[k] = RB.hueso(arm, 'cabeza')[0] or 'cabeza'
        except Exception: _HC[k] = 'cabeza'
    return _HC[k]

def caja_cabeza(arm):
    hs = _huesos_cabeza(arm)
    if not hs: return None
    pp = arm.data.pose_position; arm.data.pose_position = 'REST'; bpy.context.view_layer.update()
    try:
        return _caja(arm, hs)
    finally:
        arm.data.pose_position = pp; bpy.context.view_layer.update()

def _caja(arm, hs):
    B = arm.data.bones[hueso_cabeza(arm)]; Mb_inv = (arm.matrix_world @ B.matrix_local).inverted()
    pts = []
    for o in bpy.data.objects:
        if o.type != 'MESH': continue
        pegado_hueso = o.parent == arm and o.parent_type == 'BONE' and o.parent_bone in hs
        mod = any(m.type == 'ARMATURE' and m.object == arm for m in o.modifiers)
        if not (pegado_hueso or mod): continue
        if not pegado_hueso:
            gi = {g.index for g in o.vertex_groups if g.name in hs}
            if not gi: continue
        Mw = o.matrix_world
        for v in o.data.vertices:
            if not pegado_hueso:
                w = sum(g.weight for g in v.groups if g.group in gi)
                if w < 0.5: continue
            pts.append(Mb_inv @ (Mw @ v.co))
    if not pts: return None
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return [Vector((x, y, z)) for x in (mn.x, mx.x) for y in (mn.y, mx.y) for z in (mn.z, mx.z)]

def esquinas(arm, caja):
    """8 esquinas de la cabeza en mundo en el cuadro actual (el armature ya evaluado)."""
    pb = arm.pose.bones[hueso_cabeza(arm)]; M = arm.matrix_world @ pb.matrix
    return [M @ c for c in caja]
