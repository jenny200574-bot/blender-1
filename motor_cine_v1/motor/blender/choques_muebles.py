"""[t518 10-nov-2026] choque cuerpo<->mueble (Blender, CPU, US$0). Lo usan la revisión de motor_blender y las pruebas.
Regla: un personaje NO puede tener más de UMBRAL_FRAC de sus vértices (muestreados) dentro de un mueble del inventario.
Mueble = malla listada en inventario.json:obstaculos_piso con alto > 5 cm (alfombras y piso fuera). Personaje = armature 'ch-*'
y sus mallas hijas (ojos/pupilas fuera). Dentro = paridad de cruces de un rayo +Z contra el BVH del mueble (malla cerrada)."""
import bpy, mathutils
from mathutils.bvhtree import BVHTree
UMBRAL_FRAC = 0.03
MAX_VERT_MUESTRA = 300

def _bvh(o, dg):
    e = o.evaluated_get(dg); me = e.to_mesh()
    vs = [e.matrix_world @ v.co for v in me.vertices]; ps = [tuple(p.vertices) for p in me.polygons]
    e.to_mesh_clear()
    return (BVHTree.FromPolygons(vs, ps) if ps else None), vs

def _dentro(bvh, p):
    n = 0; o = p.copy(); d = mathutils.Vector((0.0003, 0.0002, 1.0))
    for _ in range(64):
        hit = bvh.ray_cast(o, d)
        if hit[0] is None: break
        n += 1; o = hit[0] + d * 1e-4
    return n % 2 == 1

def muebles_de_inventario(sc, inv):
    ids = {o['id'] for o in inv.get('obstaculos_piso', []) if (o['max'][2] - o['min'][2]) > 0.05}
    return [o for o in sc.objects if o.type == 'MESH' and o.name in ids]

def personajes(sc, ids=None):
    out = {}
    for o in sc.objects:
        if o.type == 'ARMATURE' and o.name.startswith('ch-') and (ids is None or o.name in ids):
            out[o.name] = [c for c in o.children_recursive if c.type == 'MESH' and not any(k in c.name for k in ('pupila', 'ojo_'))]
    return out

def medir(sc, inv, paso=4, ids=None, cuadros=None, excluir=None):
    """devuelve {pid: {cuadros_choque, revisados, peor_frac, peor_cuadro, mueble, ok}}. excluir: {pid: [prefijos de mueble permitidos]}
    (p. ej. sentado/acostado SOBRE la cama cuando el 01 lo pide y la superficie existe)."""
    excluir = excluir or {}
    dg = bpy.context.evaluated_depsgraph_get()
    mue = []
    for m in muebles_de_inventario(sc, inv):
        b, vs = _bvh(m, dg)
        if b: mue.append((m.name, b, m))
    PJ = personajes(sc, ids)
    res = {p: {"cuadros_choque": 0, "revisados": 0, "peor_frac": 0.0, "peor_cuadro": None, "mueble": None} for p in PJ}
    fr = cuadros or range(sc.frame_start, sc.frame_end + 1, paso)
    for f in fr:
        sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
        for pid, mallas in PJ.items():
            res[pid]['revisados'] += 1
            vs_all = []; bvhs = []
            for o in mallas:
                if not o.visible_get(): continue
                b, vs = _bvh(o, dg)
                if b: bvhs.append(b); vs_all.extend(vs)
            if not vs_all: continue
            muestra = vs_all[::max(1, len(vs_all) // MAX_VERT_MUESTRA)]
            peor = (0.0, None)
            for (mn, mb, _) in mue:
                if any(mn.startswith(x) for x in excluir.get(pid, [])): continue
                if not any(b.overlap(mb) for b in bvhs): continue
                frac = sum(1 for v in muestra if _dentro(mb, v)) / len(muestra)
                if frac > peor[0]: peor = (frac, mn)
            if peor[0] > UMBRAL_FRAC: res[pid]['cuadros_choque'] += 1
            if peor[0] > res[pid]['peor_frac']:
                res[pid].update(peor_frac=round(peor[0], 3), peor_cuadro=f, mueble=peor[1])
    for r in res.values(): r['ok'] = r['cuadros_choque'] == 0
    return res
