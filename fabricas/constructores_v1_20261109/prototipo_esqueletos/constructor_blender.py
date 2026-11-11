"""[constructores_v1_20261109 · fábrica conectada] Cambios vs prototipo del 9-nov: --blend RUTA (antes fijo AQUI/blend/),
informe 'gpu' según MYIA_GPU=1 (pod RunPod), sin rutas del box. Lógica de armado, piezas y pruebas: SIN cambios.

constructor_blender.py — arma en Blender (headless) un personaje desde una FICHA DE ESQUELETO v1.

MYIA · prototipo · CPU · US$0 · sin IA. Uso:
  blender -b --factory-startup --python constructor_blender.py -- --ficha F.json --salida DIR [--res 640]

1. Valida la ficha con validador.py (si RECHAZADA: no arma nada, escribe el informe y sale con código 3).
2. Crea el armature (huesos con cabeza/cola × altura_m, padres, sin conectar).
3. Crea las piezas (primitivas estilo Star) y las emparenta a su hueso; añade ojos (blanco + pupila) y nariz/pico.
4. Guarda los límites en el armature (propiedad 'limites_deg') y la pose se aplica SIEMPRE recortada a los límites.
5. Prueba de pose: cada articulación a su mínimo y máximo por eje; pedir más allá del límite debe dar lo mismo que el
   límite; L con (x,y,z) y R con (x,−y,−z) deben quedar en espejo exacto; ninguna matriz con NaN.
6. Renders (Workbench, CPU): reposo frente/perfil/tres cuartos, cada pose de poses_prueba, extremos mín y máx.
7. Guarda el .blend en reposo.
"""
import bpy, sys, json, math, time
from pathlib import Path
from mathutils import Vector, Matrix, Euler, Quaternion

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import validador as V

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(k, d=None):
    return argv[argv.index(k) + 1] if k in argv else d
FICHA = Path(arg('--ficha'))
SAL = Path(arg('--salida', str(AQUI / 'renders')))
RES = int(arg('--res', '640'))
SAL.mkdir(parents=True, exist_ok=True)
t0 = time.time()
F = json.loads(FICHA.read_text(encoding='utf-8'))
ID = F.get('id', FICHA.stem)
import os
informe = {'ficha': str(FICHA), 'id': ID, 'origen': F.get('origen'), 'gasto_usd': 0, 'gpu': os.environ.get('MYIA_GPU') == '1',
           'gpu_backend': os.environ.get('MYIA_GPU_BACKEND')}
val = V.validar(F)
informe['validacion'] = val.dict()
if not val.apta:
    (SAL / f'{ID}_informe.json').write_text(json.dumps(informe, ensure_ascii=False, indent=1))
    print('RECHAZADA: no se arma', json.dumps(val.errores, ensure_ascii=False))
    sys.exit(3)

S = float(F['altura_m'])
def P(v):
    return Vector(v) * S

# ---------- escena limpia ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
MATS = {}
def mat(hexc):
    if hexc in MATS:
        return MATS[hexc]
    h = hexc.lstrip('#')
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    m = bpy.data.materials.new('M_' + h)
    m.diffuse_color = (*lin, 1.0)
    m.roughness = 0.6
    MATS[hexc] = m
    return m

# ---------- armature ----------
arm_data = bpy.data.armatures.new(f'ESQ_{ID}_data')
A = bpy.data.objects.new(f'ESQ_{ID}', arm_data)
sc.collection.objects.link(A)
bpy.context.view_layer.objects.active = A
bpy.ops.object.mode_set(mode='EDIT')
HUESOS = {h['nombre']: h for h in F['huesos']}
orden, hechos = [], set()
while len(orden) < len(HUESOS):   # padres antes que hijos (el validador ya garantizó árbol)
    for n, h in HUESOS.items():
        if n not in hechos and (h.get('padre') in (None, '') or h['padre'] in hechos):
            orden.append(n); hechos.add(n)
for n in orden:
    h = HUESOS[n]
    eb = arm_data.edit_bones.new(n)
    eb.head, eb.tail, eb.roll = P(h['cabeza']), P(h['cola']), 0.0
    if h.get('padre'):
        eb.parent = arm_data.edit_bones[h['padre']]
        eb.use_connect = False
bpy.ops.object.mode_set(mode='OBJECT')
A['limites_deg'] = json.dumps({n: h['limites_deg'] for n, h in HUESOS.items()})
A['convencion'] = 'ejes del cuerpo en reposo (+Z arriba, -Y frente, +X izquierda), XYZ, recortado a limites'
A['origen'] = json.dumps(F.get('origen'), ensure_ascii=False)
A.show_in_front = True
arm_data.display_type = 'STICK'

# ---------- piezas ----------
def parent_bone(o, bone):
    mw = o.matrix_world.copy()
    o.parent, o.parent_type, o.parent_bone = A, 'BONE', bone
    bpy.context.view_layer.update()
    o.matrix_world = mw

def nuevo(nombre, color):
    o = bpy.context.object
    o.name = nombre
    o.data.materials.append(mat(color))
    bpy.ops.object.shade_smooth()
    return o

def a_lo_largo(o, a, b):
    d = b - a
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)

def pieza(p):
    hb = HUESOS[p['hueso']]
    n, c, prim = f"{ID}_{p['nombre']}", p['color'], p['primitiva']
    if p['modo'] == 'hueso':
        a, b = P(hb['cabeza']), P(hb['cola'])
        L, r = (b - a).length, p['radio'] * S
        if prim == 'cono':
            bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=0, depth=L, location=(a + b) / 2, vertices=20)
            o = nuevo(n, c); a_lo_largo(o, a, b)
        elif prim == 'cilindro':
            bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=L, location=(a + b) / 2, vertices=20)
            o = nuevo(n, c); a_lo_largo(o, a, b)
        else:  # capsula = cilindro + 2 esferas unidas
            bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=L, location=(a + b) / 2, vertices=20)
            o = nuevo(n, c); a_lo_largo(o, a, b)
            partes = [o]
            for q in (a, b):
                bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=q, segments=20, ring_count=10)
                partes.append(nuevo(n + '_tapa', c))
            bpy.ops.object.select_all(action='DESELECT')
            for x in partes:
                x.select_set(True)
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.join()
            o = bpy.context.object; o.name = n
    else:
        ctr, rad = P(p['centro']), [x * S for x in p['radios']]
        rot = Euler([math.radians(x) for x in p.get('rotacion_deg', [0, 0, 0])], 'XYZ')
        if prim == 'esfera':
            bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=ctr, segments=32, ring_count=16)
            o = nuevo(n, c); o.scale = rad
        elif prim == 'caja':
            bpy.ops.mesh.primitive_cube_add(size=2, location=ctr); o = nuevo(n, c); o.scale = rad
        elif prim in ('cilindro', 'capsula'):
            bpy.ops.mesh.primitive_cylinder_add(radius=1, depth=2, location=ctr, vertices=24); o = nuevo(n, c); o.scale = rad
        elif prim == 'cono':
            bpy.ops.mesh.primitive_cone_add(radius1=1, radius2=0, depth=2, location=ctr, vertices=24); o = nuevo(n, c); o.scale = rad
        else:  # toro
            bpy.ops.mesh.primitive_torus_add(major_radius=rad[0], minor_radius=rad[2], location=ctr); o = nuevo(n, c)
        o.rotation_euler = rot
    bpy.context.view_layer.update()
    parent_bone(o, p['hueso'])
    return o

OBJS = [pieza(p) for p in F['piezas']]
# ---------- rostro ----------
R = F['rostro']
hcab = R['hueso']
r_ojo = R['ojos']['radio'] * S
for lado, sx in (('L', 1), ('R', -1)):
    cL = R['ojos']['centro_L']
    c = P([sx * cL[0], cL[1], cL[2]])
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r_ojo, location=c, segments=24, ring_count=12)
    o = nuevo(f'{ID}_ojo_{lado}', '#FFFFFF'); parent_bone(o, hcab); OBJS.append(o)
    d = Vector((sx * 0.35, -1, 0.1)).normalized()
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r_ojo * 0.55, location=c + d * r_ojo * 0.62, segments=16, ring_count=8)
    o = nuevo(f'{ID}_pupila_{lado}', '#111111'); parent_bone(o, hcab); OBJS.append(o)
na = R['nariz']
cn, rn = P(na['centro']), na['radio'] * S
if na['primitiva'] == 'cono':
    bpy.ops.mesh.primitive_cone_add(radius1=rn, radius2=0, depth=rn * 2.2, location=cn, rotation=(math.radians(90), 0, 0), vertices=20)
else:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=rn, location=cn, segments=20, ring_count=10)
o = nuevo(f'{ID}_nariz', na.get('color', '#E07A2A')); parent_bone(o, hcab); OBJS.append(o)

# ---------- pose recortada a límites ----------
for pb in A.pose.bones:
    pb.rotation_mode = 'QUATERNION'

def recortar(n, rot):
    lim = HUESOS[n]['limites_deg']
    return [max(lim[ax][0], min(lim[ax][1], float(v))) for ax, v in zip('xyz', rot)]

def reposo():
    for pb in A.pose.bones:
        pb.rotation_quaternion = Quaternion((1, 0, 0, 0))

def poner(pose):
    """pose: {hueso: [x,y,z] grados en ejes del cuerpo}. Devuelve lo realmente aplicado (recortado)."""
    reposo()
    aplicado = {}
    for n, rot in pose.items():
        if n not in HUESOS:
            continue
        r = recortar(n, rot)
        aplicado[n] = r
        Mb = A.data.bones[n].matrix_local.to_3x3()
        Rm = Euler([math.radians(x) for x in r], 'XYZ').to_matrix()
        A.pose.bones[n].rotation_quaternion = (Mb.inverted() @ Rm @ Mb).to_quaternion()
    bpy.context.view_layer.update()
    return aplicado

def colas():
    return {pb.name: (A.matrix_world @ pb.tail).copy() for pb in A.pose.bones}

# ---------- mirada (nariz vs frente del pecho) ----------
# Convención ficha: frente del cuerpo = −Y en reposo. En el hueso vertical (pecho/columna/cabeza),
# el eje local +Z del hueso apunta a −Y mundo en reposo (comprobado en Blender).
ANG_MIRADA_MAX = 100.0  # >100° = cabeza mirando opuesta al torso

def _hueso_pecho():
    for n in ('pecho', 'columna', 'cadera', 'torso'):
        if n in A.pose.bones:
            return A.pose.bones[n]
    # ave / otros: primer hueso rol pecho/columna/cadera
    for n, h in HUESOS.items():
        if h.get('rol') in ('pecho', 'columna', 'cadera') and n in A.pose.bones:
            return A.pose.bones[n]
    return A.pose.bones[next(iter(HUESOS))]

def frente_pecho():
    """Vector mundo hacia donde mira el pecho (frente del torso)."""
    pb = _hueso_pecho()
    return (pb.matrix.to_3x3() @ Vector((0, 0, 1))).normalized()

def mirada_nariz():
    """Vector mundo nariz ← centro cabeza (dirección de la cara)."""
    cab = None
    for n, h in HUESOS.items():
        if h.get('rol') == 'cabeza' and n in A.pose.bones:
            cab = A.pose.bones[n]; break
    if cab is None:
        cab = A.pose.bones.get('cabeza') or next(A.pose.bones)
    ctr = (A.matrix_world @ cab.head + A.matrix_world @ cab.tail) / 2
    nariz = next((o for o in OBJS if '_nariz' in o.name or o.name.endswith('_pico')), None)
    if nariz is None:
        # fallback: eje frente del hueso cabeza
        return (cab.matrix.to_3x3() @ Vector((0, 0, 1))).normalized(), ctr
    return (nariz.matrix_world.translation - ctr).normalized(), ctr

def angulo_mirada_pecho():
    bpy.context.view_layer.update()
    f = frente_pecho(); m, _ = mirada_nariz()
    return math.degrees(f.angle(m))

# ---------- prueba de pose ----------
pt = {'casos': 0, 'fallos': [], 'nan': 0, 'recorte_ok': 0, 'espejo_ok': 0, 'z_min_extremos_m': {},
      'mirada': [], 'mirada_fallos': 0}
for n, h in HUESOS.items():
    for i, ax in enumerate('xyz'):
        lo, hi = h['limites_deg'][ax]
        if lo == hi:
            continue
        for borde, fuera in ((lo, lo - 25), (hi, hi + 25)):
            v = [0, 0, 0]; v[i] = borde; poner({n: v}); a = colas()
            v2 = [0, 0, 0]; v2[i] = fuera; poner({n: v2}); b = colas()
            pt['casos'] += 1
            if any(any(math.isnan(c) for c in p) for p in a.values()):
                pt['nan'] += 1
            dmax = max((a[k] - b[k]).length for k in a)
            if dmax < 1e-6:
                pt['recorte_ok'] += 1
            else:
                pt['fallos'].append(f'{n}.{ax}: pedir {fuera} no se recortó a {borde} (Δ={dmax:.2e} m)')
            # espejo
            m = V.espejo_nombre(n)
            if h['lado'] == 'L' and m in HUESOS:
                vm = [v[0], -v[1], -v[2]]
                poner({n: v, m: vm}); c = colas()
                err = max((Vector((-c[k].x, c[k].y, c[k].z)) - c[V.espejo_nombre(k) or k]).length for k in c)
                if err < 1e-5 * max(S, 1):
                    pt['espejo_ok'] += 1
                else:
                    pt['fallos'].append(f'{n}/{m}.{ax}={borde}: espejo roto (err {err:.2e} m)')
reposo()
def zmin():
    bpy.context.view_layer.update()
    return min((o.matrix_world @ Vector(c)).z for o in OBJS for c in o.bound_box)
pt['z_min_reposo_m'] = round(zmin(), 5)
# Mirada en reposo y en cada pose de prueba (también sirve para Piquito u otros)
reposo()
ang0 = angulo_mirada_pecho()
pt['mirada'].append({'pose': 'reposo', 'angulo_deg': round(ang0, 1), 'ok': ang0 <= ANG_MIRADA_MAX})
if ang0 > ANG_MIRADA_MAX:
    pt['mirada_fallos'] += 1
    pt['fallos'].append(f'mirada reposo: nariz vs pecho {ang0:.1f}° > {ANG_MIRADA_MAX}°')
for pn, pose in (F.get('poses_prueba') or {}).items():
    poner(pose)
    ang = angulo_mirada_pecho()
    ok = ang <= ANG_MIRADA_MAX
    pt['mirada'].append({'pose': pn, 'angulo_deg': round(ang, 1), 'ok': ok})
    if not ok:
        pt['mirada_fallos'] += 1
        pt['fallos'].append(f'mirada {pn}: nariz vs pecho {ang:.1f}° > {ANG_MIRADA_MAX}° (cabeza opuesta al torso)')
reposo()
informe['prueba_pose'] = pt

# ---------- render ----------
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'FLAT' if '--plano' in argv else 'STUDIO'
try:
    sc.display.shading.studio_light = 'paint.sl'   # luz de estudio más clara y pareja (Blender incluye paint.sl)
except Exception:
    pass
sc.display.shading.color_type = 'MATERIAL'
sc.display.shading.show_shadows = True
sc.display.shading.show_cavity = True
sc.display.shading.cavity_type = 'WORLD'
sc.display.shading.shadow_intensity = 0.25
sc.view_settings.exposure = 0.3
sc.display.shading.show_object_outline = True
sc.render.resolution_x = sc.render.resolution_y = RES
sc.render.image_settings.file_format = 'PNG'
sc.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new('W'); w.color = (0.82, 0.84, 0.88); sc.world = w
bpy.ops.mesh.primitive_plane_add(size=S * 12, location=(0, 0, 0))
piso = nuevo('piso', '#9EA3AA')
cam = bpy.data.objects.new('CAM', bpy.data.cameras.new('CAM'))
sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 50; cam.data.clip_start = S * 0.01; cam.data.clip_end = S * 100
A.hide_render = True

def encuadre(vista):
    bpy.context.view_layer.update()
    pts = [(o.matrix_world @ Vector(c)) for o in OBJS for c in o.bound_box]
    mn = Vector([min(p[i] for p in pts) for i in range(3)]); mx = Vector([max(p[i] for p in pts) for i in range(3)])
    ctr = (mn + mx) / 2; span = max((mx - mn).length, S * 0.3)
    dist = span * 1.9
    d = {'frente': Vector((0, -1, 0.15)), 'perfil': Vector((1, 0, 0.15)), 'tres_cuartos': Vector((0.75, -0.75, 0.3))}[vista].normalized()
    cam.location = ctr + d * dist
    cam.rotation_euler = (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()

renders = {}
def render(nombre, vista):
    encuadre(vista)
    p = SAL / f'{ID}_{nombre}.png'
    sc.render.filepath = str(p)
    bpy.ops.render.render(write_still=True)
    renders[nombre] = str(p)

t_r = time.time()
reposo()
for v in ('frente', 'perfil', 'tres_cuartos'):
    render(f'reposo_{v}', v)
aplicadas = {}
contacto = {}
APOYO = [o for o in OBJS if o.parent_bone in HUESOS and HUESOS[o.parent_bone]['rol'] in V.ROLES_APOYO]
def contacto_suelo(nombre):
    bpy.context.view_layer.update()
    z_todo = zmin()
    z_apoyo = min(((o.matrix_world @ Vector(c)).z for o in APOYO for c in o.bound_box), default=None)
    contacto[nombre] = {'z_min_m': round(z_todo, 5), 'z_min_apoyos_m': None if z_apoyo is None else round(z_apoyo, 5),
                        'toca_suelo': z_apoyo is not None and abs(z_apoyo) <= V.TOL_SUELO * S,
                        'atraviesa_suelo': z_todo < -V.TOL_SUELO * S}
contacto_suelo('reposo')
BANCO = None
def asegurar_banco(on):
    """Caja de apoyo bajo la cadera para poses sentada (no flotar)."""
    global BANCO
    if on:
        if BANCO is None:
            bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.1 * S))
            BANCO = nuevo(f'{ID}_banco_sentada', '#8B7355')
            BANCO.scale = (0.3 * S, 0.3 * S, 0.1 * S)
            bpy.context.view_layer.update()
        BANCO.hide_render = False
        BANCO.hide_viewport = False
    elif BANCO is not None:
        BANCO.hide_render = True
        BANCO.hide_viewport = True

for pn, pose in (F.get('poses_prueba') or {}).items():
    sentada = 'sentad' in pn.lower()
    aplicadas[pn] = poner(pose)
    if sentada:
        # Coloca el banco JUSTO bajo la pelvis (piezas de cadera/pecho-bajo), sin mover al personaje
        bpy.context.view_layer.update()
        pelv = [o for o in OBJS if o.parent_bone in HUESOS and HUESOS[o.parent_bone]['rol'] in ('cadera', 'columna')]
        if not pelv:
            pelv = [o for o in OBJS if 'cadera' in o.name or 'torso' in o.name]
        z_bajo = min((o.matrix_world @ Vector(c)).z for o in pelv for c in o.bound_box)
        y_pel = sum((o.matrix_world.translation.y for o in pelv), 0.0) / max(len(pelv), 1)
        h_asiento = max(0.05 * S, z_bajo)  # asiento a la altura del punto bajo de la pelvis
        asegurar_banco(True)
        BANCO.scale = (0.32 * S, 0.32 * S, max(h_asiento / 2, 0.02 * S))
        BANCO.location = (0.0, y_pel + 0.02 * S, BANCO.scale.z)
        # si la pelvis queda por encima del asiento, subir el banco; si atraviesa, bajar personaje 0
        bpy.context.view_layer.update()
        top = BANCO.location.z + BANCO.scale.z
        if z_bajo > top + 0.005 * S:
            BANCO.location.z += (z_bajo - top)
        elif z_bajo < top - 0.01 * S:
            A.location.z += (top - z_bajo)  # sube un pelo si penetraba
        bpy.context.view_layer.update()
    else:
        asegurar_banco(False)
    contacto_suelo(pn)
    if sentada and BANCO is not None:
        contacto[pn]['banco'] = True
        contacto[pn]['banco_z_asiento_m'] = round(BANCO.location.z + BANCO.scale.z, 4)
        contacto[pn]['pelvis_z_min_m'] = round(z_bajo + A.location.z, 4)
    ang = angulo_mirada_pecho()
    contacto[pn]['mirada_angulo_deg'] = round(ang, 1)
    contacto[pn]['mirada_ok'] = ang <= ANG_MIRADA_MAX
    render(f'pose_{pn}', 'tres_cuartos')
    if sentada:
        A.location.z = 0.0
        asegurar_banco(False)
        bpy.context.view_layer.update()
if '--chequeos' in argv:
    # ¿Pueden las alas cubrir los ojos? Búsqueda determinista DENTRO de los límites de la cadena del ala (no son datos de Argon).
    import random
    from mathutils.bvhtree import BVHTree
    rnd = random.Random(20261109)
    cad = {l: V.cadena_ala(HUESOS, l) for l in 'LR'}
    ala_obj = {l: [o for o in OBJS if o.parent_bone in cad[l]] for l in 'LR'}
    ojo = {l: bpy.data.objects[f'{ID}_ojo_{l}'] for l in 'LR'}
    def cubierto(l):
        bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
        e = ojo[l]; c = e.matrix_world.translation; r = r_ojo
        arboles = [BVHTree.FromObject(o, dg, deform=True) for o in ala_obj[l]]
        mats = [o.matrix_world.inverted() for o in ala_obj[l]]
        n = ok = 0
        for dx, dz in [(0, 0)] + [(math.cos(a) * 0.7, math.sin(a) * 0.7) for a in [k * math.pi / 4 for k in range(8)]]:
            o_w = Vector((c.x + dx * r, c.y - 20 * S, c.z + dz * r)); n += 1
            for T, Mi in zip(arboles, mats):
                lo = Mi @ o_w; ld = (Mi.to_3x3() @ Vector((0, 1, 0))).normalized()
                hit = T.ray_cast(lo, ld)
                if hit[0] is not None:
                    hw = Mi.inverted() @ hit[0]
                    if hw.y <= c.y - r * math.sqrt(max(0.0, 1 - dx * dx - dz * dz)):    # la pluma queda DELANTE de la superficie del ojo (vista de frente, −Y)
                        ok += 1; break
        dmin = min((o.matrix_world @ v.co - c).length for o in ala_obj[l] for v in o.data.vertices)
        return ok / n - dmin   # cobertura (0..1) y, a igual cobertura, más cerca es mejor
    # Huesos que se mueven: los 'huesos_mandan' del movimiento 'cubrir_rostro_con_alitas' del catálogo si existe; si no, la cadena del ala.
    def _buscar_mov(o):
        if isinstance(o, dict):
            n = str(o.get('nombre', ''))
            if ('cubrir' in n and 'alita' in n or n.startswith('cubrir') and 'ala' in n) and isinstance(o.get('huesos_mandan'), list): return o
            o = list(o.values())
        if isinstance(o, list):
            for v in o:
                r = _buscar_mov(v)
                if r: return r
        return None
    MOV = _buscar_mov(json.loads(Path(arg('--catalogo')).read_text(encoding='utf-8'))) if arg('--catalogo') else _buscar_mov(F)
    mueve = [b for b in (MOV['huesos_mandan'] if MOV else cad['L']) if b in HUESOS and HUESOS[b].get('lado') != 'R']
    centrales = {b for b in mueve if HUESOS[b].get('lado') not in ('L', 'R')}
    def muestra():
        pose = {}
        for b in mueve:
            lim = HUESOS[b]['limites_deg']
            pose[b] = [rnd.uniform(*lim['x']), 0.0, 0.0] if b in centrales else [rnd.uniform(*lim[ax]) for ax in 'xyz']
        return pose
    def espejo(pose):
        out = dict(pose)
        for b, v in pose.items():
            if b in centrales:
                out[b] = [v[0], 0.0, 0.0]; continue
            m = V.espejo_nombre(b)
            if m in HUESOS: out[m] = [v[0], -v[1], -v[2]]
        return out
    mejor, mval = None, -1.0
    for i in range(3000):
        pz = muestra(); poner(espejo(pz)); v = min(cubierto('L'), cubierto('R'))
        if v > mval: mejor, mval = pz, v
        if mval >= 1.0: break
    paso = 15.0
    while paso >= 2 and mval < 1.0:   # refinamiento por coordenadas
        mejoro = False
        for b in list(mejor):
            for i in range(3):
                for s in (-1, 1):
                    q = {k: list(v) for k, v in mejor.items()}; q[b][i] += s * paso
                    q[b] = recortar(b, q[b]); poner(espejo(q)); v = min(cubierto('L'), cubierto('R'))
                    if v > mval: mejor, mval, mejoro = q, v, True
        if not mejoro: paso /= 2
    ap = poner(espejo(mejor)); contacto_suelo('cubrir_ojos_busqueda')
    _sL, _sR = cubierto('L'), cubierto('R')
    _cob = lambda s: round(math.ceil(s * 9 - 1e-9) / 9, 3) if s > 0 else 0.0
    _bpy_up = bpy.context.view_layer.update()
    dist = {l: round(min((o.matrix_world @ v.co - ojo[l].matrix_world.translation).length for o in ala_obj[l] for v in o.data.vertices), 4) for l in 'LR'}
    mval = min(_cob(_sL), _cob(_sR))
    informe['alas_cubren_ojos'] = {'cobertura_min_ojos': round(mval, 3), 'distancia_min_pluma_a_centro_ojo_m': dist, 'radio_ojo_m': round(r_ojo, 4), 'puede_cubrir': mval >= 0.75, 'cadena': cad, 'huesos_movidos': mueve, 'movimiento_catalogo': MOV['nombre'] if MOV else None,
                                   'pose_encontrada_grados': {k: [round(x, 1) for x in v] for k, v in ap.items()},
                                   'metodo': '3000 muestras + refinamiento por coordenadas dentro de limites_deg (semilla 20261109); '
                                             '9 rayos de frente por ojo; cubierto = pluma delante de la superficie del ojo. Pose del programa, no de Argon.'}
    render('pose_cubrir_ojos_busqueda', 'frente')
informe['contacto_suelo'] = contacto
for etiqueta, idx in (('extremos_min', 0), ('extremos_max', 1)):
    pose = {n: [h['limites_deg'][ax][idx] for ax in 'xyz'] for n, h in HUESOS.items() if h['rol'] != 'raiz'}
    poner(pose)
    pt['z_min_extremos_m'][etiqueta] = round(zmin(), 5)
    ang = angulo_mirada_pecho()
    pt['mirada'].append({'pose': etiqueta, 'angulo_deg': round(ang, 1), 'ok': ang <= ANG_MIRADA_MAX,
                         'nota': 'extremos combinan todos los límites a la vez; un fallo aquí no invalida poses sueltas'})
    # no suma a fallos: extremos simultáneos pueden cruzar 100° a propósito
    render(etiqueta, 'tres_cuartos')
reposo()
informe['poses_aplicadas_recortadas'] = aplicadas
informe['renders'] = renders
informe['tiempo_render_s'] = round(time.time() - t_r, 2)
# ---------- guardar ----------
A.hide_render = False
blend = Path(arg('--blend', str(SAL / f'{ID}.blend')))
blend.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
informe.update({'blend': str(blend), 'n_huesos': len(HUESOS), 'n_objetos': len(OBJS),
                'tiempo_total_s': round(time.time() - t0, 2), 'blender': bpy.app.version_string,
                'resultado': 'OK' if not pt['fallos'] and not pt['nan'] else 'FALLOS_POSE',
                'mirada_fallos': pt.get('mirada_fallos', 0)})
(SAL / f'{ID}_informe.json').write_text(json.dumps(informe, ensure_ascii=False, indent=1))
print('INFORME', json.dumps({k: informe[k] for k in ('id', 'resultado', 'n_huesos', 'n_objetos', 'tiempo_total_s')}),
      'casos', pt['casos'], 'recorte_ok', pt['recorte_ok'], 'espejo_ok', pt['espejo_ok'], 'fallos', len(pt['fallos']))
