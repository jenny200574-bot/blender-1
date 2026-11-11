"""relaciones_blender — [argon_v2, 10-nov-2026] ejecución GENÉRICA de relaciones físicas en Blender (cualquier rig/canal).
  hueso(arm, parte, lado)      -> nombre del hueso del rig para 'hombro'|'mano'|'cabeza'|'pecho'|'antebrazo' y lado 'L'|'R'
                                  1) nombre exacto de la convención de la fábrica (p. ej. hombro_L), 2) sinónimos ES/EN y
                                  sufijos de lado (.L _L Left izq ...), 3) respaldo GEOMÉTRICO (posición del hueso en el molde).
  punto_apoyo(H, hueso, dg)    -> punto sobre la superficie de la malla del portador encima de ese hueso (raycast hacia abajo)
  soporte(objs_prefijos)       -> BVH de la superficie superior de un mueble (sentado_en / acostado_en)
Nada de nombres de personaje, canal ni escenario."""
import re, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SINONIMOS = {
    'hombro': ['hombro', 'shoulder', 'clavicula', 'clavicle', 'clav'],
    'mano': ['mano', 'hand', 'muneca', 'wrist', 'palm'],
    'antebrazo': ['antebrazo', 'forearm', 'lowerarm', 'lower_arm'],
    'brazo': ['brazo', 'upperarm', 'upper_arm', 'arm'],
    'cabeza': ['cabeza', 'head'],
    'pecho': ['pecho', 'chest', 'spine2', 'spine_02', 'torso', 'upperchest'],
}
LADO_RX = {'L': r'(?:[._\- ](?:l|left|izq|izquierdo|izquierda)$|^(?:l|left)[._\-]|left)', 'R': r'(?:[._\- ](?:r|right|der|derecho|derecha)$|^(?:r|right)[._\-]|right)'}

def _n(s): return str(s or '').lower()

def _lado_de(nombre):
    n = _n(nombre)
    for k, rx in LADO_RX.items():
        if re.search(rx, n): return k
    return None

def hueso(arm, parte, lado=None):
    """(nombre_hueso, metodo). None si el rig no tiene nada razonable."""
    bones = arm.data.bones; parte = _n(parte or 'hombro'); lado = (lado or '').upper()[:1] or None
    exacto = f"{parte}_{lado}" if lado and parte not in ('cabeza', 'pecho') else parte
    if exacto in bones: return exacto, 'nombre exacto (convención de la fábrica)'
    sin = SINONIMOS.get(parte, [parte])
    cand = [b.name for b in bones if any(s in _n(b.name).replace('.', '_') for s in sin)]
    if parte == 'brazo': cand = [c for c in cand if not any(s in _n(c) for s in SINONIMOS['antebrazo'])]
    if lado: cand = [c for c in cand if _lado_de(c) == lado] or ([c for c in cand if _lado_de(c) is None] if parte in ('cabeza', 'pecho') else [])
    if cand: return sorted(cand, key=len)[0], 'sinónimo/sufijo de lado'
    # respaldo geométrico en el reposo del molde (mira -Y por convención Blender: su izquierda es +X)
    alto = max((b.tail_local.z for b in bones), default=1.0) or 1.0
    def lat(b): return (b.head_local.x + b.tail_local.x) / 2
    if parte == 'cabeza':
        b = max(bones, key=lambda b: b.tail_local.z, default=None); return (b.name, 'geométrico: hueso más alto') if b else (None, 'sin huesos')
    if parte in ('hombro', 'brazo'):
        zona = [b for b in bones if 0.6 * alto <= b.head_local.z <= 0.92 * alto and abs(lat(b)) > 0.03 * alto]
    elif parte in ('mano', 'antebrazo'):
        zona = [b for b in bones if abs(lat(b)) > 0.1 * alto]
    else:
        zona = [b for b in bones if 0.5 * alto <= b.head_local.z <= 0.8 * alto and abs(lat(b)) < 0.05 * alto]
    if lado: zona = [b for b in zona if (lat(b) > 0) == (lado == 'L')]
    if not zona: return None, 'sin hueso compatible'
    if parte in ('hombro', 'brazo'): b = min(zona, key=lambda b: abs(lat(b)) - 0.5 * b.head_local.z / alto)
    elif parte in ('mano', 'antebrazo'): b = max(zona, key=lambda b: abs(lat(b)))
    else: b = zona[0]
    return b.name, 'geométrico (posición en el molde)'

def bvh_mallas(objs, dg):
    V = []; F = []
    for o in objs:
        oe = o.evaluated_get(dg); me = oe.to_mesh(); mw = oe.matrix_world; b = len(V)
        V += [mw @ v.co for v in me.vertices]; F += [tuple(b + i for i in p.vertices) for p in me.polygons]; oe.to_mesh_clear()
    return BVHTree.FromPolygons(V, F) if F else None

def punto_apoyo(H, nombre_hueso, dg, frac=0.65):
    """punto de la SUPERFICIE del portador encima del hueso (frac del hueso desde su cabeza): raycast vertical a su malla."""
    pb = H.pose.bones[nombre_hueso]
    P = (H.matrix_world @ pb.head).lerp(H.matrix_world @ pb.tail, frac)
    bv = bvh_mallas([c for c in H.children_recursive if c.type == 'MESH'], dg)
    if bv is None: return P, 'sin malla: punto del hueso'
    # desde DENTRO del cuerpo (el hueso) hacia arriba: el primer cruce es la piel justo encima del hueso (no la cabeza que sobresale)
    hit = bv.ray_cast(P, Vector((0, 0, 1)), 0.5)
    if hit[0] is not None: return Vector((P.x, P.y, hit[0].z)), 'superficie de la malla del portador (rayo interior hacia arriba)'
    hit = bv.ray_cast(P + Vector((0, 0, 0.6)), Vector((0, 0, -1)), 1.2)
    if hit[0] is not None and P.z - 0.05 <= hit[0].z <= P.z + 0.15: return Vector((P.x, P.y, hit[0].z)), 'superficie de la malla del portador'
    return P, 'punto del hueso (rayo sin impacto)'

def mallas_de(sc, prefijos):
    out = []
    for o in sc.objects:
        if o.type != 'MESH': continue
        if any(o.name == p or o.name.startswith(p + '#') or o.name.startswith(p + '__') or o.name.startswith(p + '.') for p in prefijos): out.append(o)
    return out

class Soportes:
    """superficies superiores de muebles para sentado_en / acostado_en, por personaje y tramo de tiempo."""
    def __init__(s, sc, dg, relaciones, fps):
        s.items = {}   # pid -> [(f0, f1, bvh, lo, hi, con)]
        for r in relaciones or []:
            if r.get('tipo') not in ('sentado_en', 'acostado_en') or r.get('con_tipo') != 'objeto': continue
            ms = mallas_de(sc, [r['con']])
            if not ms: continue
            bv = bvh_mallas(ms, dg); lo = Vector((min((o.matrix_world @ Vector(c)).x for o in ms for c in o.bound_box), min((o.matrix_world @ Vector(c)).y for o in ms for c in o.bound_box), 0))
            hi = Vector((max((o.matrix_world @ Vector(c)).x for o in ms for c in o.bound_box), max((o.matrix_world @ Vector(c)).y for o in ms for c in o.bound_box), 0))
            f0 = int(round(r['t'][0] * fps)) + 1; f1 = int(round(r['t'][1] * fps)) + 1
            s.items.setdefault(r['sujeto'], []).append((f0, f1, bv, lo, hi, r['con'], [o.name for o in ms]))
    def z(s, pid, f, x, y):
        for f0, f1, bv, lo, hi, con, _ in s.items.get(pid, []):
            if f0 <= f <= f1 and lo.x <= x <= hi.x and lo.y <= y <= hi.y and bv is not None:
                hit = bv.ray_cast(Vector((x, y, 5.0)), Vector((0, 0, -1)), 10.0)
                if hit[0] is not None: return hit[0].z, con
        return None, None
    def prefijos(s, pid):
        return sorted({n for it in s.items.get(pid, []) for n in it[6]})
