"""camara_sin_paredes (Blender, código propio MYIA): por cuadro, ¿la cámara quedó DENTRO de una geometría del set
(pared, mueble, otro personaje) o tan pegada que el plano cercano (clip_start) la corta?
Regla del storyboard: la cámara NUNCA se mueve. Si está dentro -> esa geometría se oculta solo para cámara
(visible_camera=False) en esos cuadros, igual que ocultar_estorbos. Si la geometría está protegida -> conflicto."""
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def aabb_mundo(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))), \
           Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))

def bvh_mundo(o, dg):
    oe = o.evaluated_get(dg); me = oe.to_mesh()
    try:
        mw = oe.matrix_world
        verts = [mw @ v.co for v in me.vertices]; polys = [tuple(p.vertices) for p in me.polygons]
    finally:
        oe.to_mesh_clear()
    if not polys: return None
    return BVHTree.FromPolygons(verts, polys)

_CACHE_LOCAL = {}   # BVH en espacio local de objetos rígidos (sin deformación): se arma 1 vez, no por cuadro

def _rigido(o):
    return not any(m.type in ('ARMATURE', 'MESH_DEFORM', 'SURFACE_DEFORM', 'LATTICE', 'HOOK', 'CLOTH', 'SOFT_BODY', 'WAVE', 'DISPLACE') for m in o.modifiers) \
        and not (o.data.shape_keys if getattr(o, 'data', None) is not None and hasattr(o.data, 'shape_keys') else None)

def _bvh_local(o, dg):
    k = o.name
    if k in _CACHE_LOCAL: return _CACHE_LOCAL[k]
    oe = o.evaluated_get(dg); me = oe.to_mesh()
    try:
        verts = [v.co.copy() for v in me.vertices]; polys = [tuple(p.vertices) for p in me.polygons]
    finally:
        oe.to_mesh_clear()
    b = BVHTree.FromPolygons(verts, polys) if polys else None
    _CACHE_LOCAL[k] = b
    return b

def dentro_de(o, C, dg, margen):
    """True/False + motivo. Prueba 1: punto más cercano y su normal (dentro si (C-p)·n<0).
    Prueba 2 (paridad): rayo +Z y -Z cuentan cruces impares. Prueba 3: distancia < clip_start (el plano cercano la corta).
    Objetos rígidos: BVH local en caché (mismo resultado, sin reconstruir por cuadro)."""
    lo, hi = aabb_mundo(o)
    if not all(lo[i] - margen <= C[i] <= hi[i] + margen for i in range(3)): return False, None, None
    if _rigido(o):
        bvh = _bvh_local(o, dg)
        if bvh is None: return False, None, None
        mw = o.matrix_world; mi = mw.inverted(); Cl = mi @ C; nm = mi.to_3x3().transposed()
        locl, norl, idx, _ = bvh.find_nearest(Cl)
        if locl is None: return False, None, None
        loc = mw @ locl; nor = (nm @ norl).normalized(); dist = (loc - C).length
        def cruces(dw):
            d = (mi.to_3x3() @ dw).normalized(); n = 0; P = Cl.copy()
            for _ in range(64):
                h = bvh.ray_cast(P, d)
                if h[0] is None: break
                n += 1; P = h[0] + d * 1e-5
            return n
    else:
        bvh = bvh_mundo(o, dg)
        if bvh is None: return False, None, None
        loc, nor, idx, dist = bvh.find_nearest(C)
        if loc is None: return False, None, None
        def cruces(d):
            n = 0; P = C.copy()
            for _ in range(64):
                h = bvh.ray_cast(P, d)
                if h[0] is None: break
                n += 1; P = h[0] + d * 1e-5
            return n
    if dist < margen: return True, "pegada_clip", round(dist, 4)
    paridad = (cruces(Vector((0, 0, 1))) % 2 == 1) and (cruces(Vector((0, 0, -1))) % 2 == 1)
    normal_dentro = (C - loc).dot(nor) < 0
    if paridad and normal_dentro: return True, "camara_dentro", round(dist, 4)
    return False, None, round(dist, 4)

def revisar_cuadro(cam, candidatos, dg):
    """candidatos: objetos MESH renderizables en este cuadro (ya filtrados). Devuelve lista de (obj, motivo, dist)."""
    C = cam.matrix_world.translation.copy()
    margen = max(cam.data.clip_start * 1.5, 0.02)
    out = []
    for o in candidatos:
        ok, mot, d = dentro_de(o, C, dg, margen)
        if ok: out.append((o, mot, d))
    return out
