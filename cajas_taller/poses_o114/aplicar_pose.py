# o110: aplica una pose de poses_basicas.json a un VRM (cualquier humanoide). Direccion + giro por parte, orientacion del cuerpo,
# espejo, y apoyo en el piso sin hundir ni flotar. Nombre desconocido -> PoseFalta (nunca inventa).
import bpy, json, math, unicodedata
from mathutils import Vector, Matrix, Quaternion
class PoseFalta(KeyError): pass
def _n(s): return ''.join(c for c in unicodedata.normalize('NFKD', str(s).lower()) if not unicodedata.combining(c)).replace(' ', '_')
def buscar(LIB, nombre):
    k = _n(nombre)
    for pid, p in LIB['poses'].items():
        if k == _n(pid) or k in [_n(a) for a in p.get('alias', [])]: return pid
    raise PoseFalta(f'pose «{nombre}» no existe en la biblioteca: FALTA (no se inventa)')
def resolver(LIB, pid):
    p = LIB['poses'][pid]; partes = {}
    if p.get('base'): partes.update(resolver(LIB, p['base'])[1])
    partes.update(p.get('partes') or {}); return p, partes
def espejar(partes):
    out = {}
    for k, v in partes.items():
        k2 = k.replace('_izq', '#').replace('_der', '_izq').replace('#', '_der')
        out[k2] = {'dir': [-v['dir'][0], v['dir'][1], v['dir'][2]], 'giro': -v.get('giro', 0)}
    return out
def preparar(A):
    """o114 (causa probada): la «gordura» escala huesos de forma NO uniforme; un hijo que hereda la escala completa (inherit_scale FULL)
    sufre cizalla al girar y cada pose escrita por matriz le deja escala de más que se ACUMULA pose tras pose (pierna 1.0 -> 0.03).
    Arreglo genérico: guardar UNA vez la escala propia de cada hueso (proporciones del personaje), heredar la escala ALINEADA (sin
    cizalla) y volver a poner esa escala después de cada giro. Vale para cualquier esqueleto."""
    if A.get('o114_escala_base') is None:
        A['o114_escala_base'] = json.dumps({pb.name: list(pb.scale) for pb in A.pose.bones})
        if any(max(pb.scale) - min(pb.scale) > 1e-4 for pb in A.pose.bones):
            for b in A.data.bones:   # (Argon o114) sin entrar a modo edición: funciona aunque el esqueleto esté oculto
                if b.inherit_scale == 'FULL': b.inherit_scale = 'ALIGNED'
            bpy.context.view_layer.update()
    return json.loads(A['o114_escala_base'])
def aplicar(A, LIB, nombre, espejo=False, pos=(0, 0, 0), rot_z=0.0):
    pid = buscar(LIB, nombre); p, partes = resolver(LIB, pid)
    if espejo: partes = espejar(partes)
    BASE = preparar(A)
    for pb in A.pose.bones: pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0); pb.scale = BASE[pb.name]
    bpy.context.view_layer.update()
    orden = ['torso', 'cuello', 'brazo_izq', 'antebrazo_izq', 'brazo_der', 'antebrazo_der', 'muslo_izq', 'pierna_izq', 'muslo_der', 'pierna_der', 'pie_izq', 'pie_der']
    for parte in orden:
        if parte not in partes: continue
        pb = A.pose.bones[LIB['partes'][parte]]; bpy.context.view_layer.update()
        cur = (A.pose.bones[LIB['partes']['cuello']].head - pb.head) if parte == 'torso' else (pb.tail - pb.head)
        d = Vector(partes[parte]['dir']).normalized()
        q = cur.normalized().rotation_difference(d) @ Quaternion(cur.normalized(), 0)
        q = Quaternion(d, math.radians(partes[parte].get('giro', 0))) @ q
        h = pb.head.copy(); pb.matrix = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ pb.matrix
        pb.scale = BASE[pb.name]   # o114: la escala del personaje no cambia al girar
    A.rotation_mode = 'XYZ'; A.rotation_euler = (math.radians(p.get('cuerpo', 0)), 0, math.radians(rot_z)); A.location = Vector(pos)
    bpy.context.view_layer.update(); return pid, p
def zmin_malla(objs):
    dg = bpy.context.evaluated_depsgraph_get(); z = 1e9
    for o in objs:
        e = o.evaluated_get(dg); m = e.to_mesh(); z = min([z] + [(o.matrix_world @ v.co).z for v in m.vertices]); e.to_mesh_clear()
    return z
def apoyar(A, objs, piso=0.0):
    A.location.z += piso - zmin_malla(objs); bpy.context.view_layer.update()
