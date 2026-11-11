"""PISTA INMI (2026-10-29): orden 87 — paso «moldes de toma» del CUBO 02 (copia de taller de pruebas_o84/hibrido_blender.py,
orden 84). Método HÍBRIDO de Ako (maniquíes Blender → Nano Banana «calca» encima), versión UNIVERSAL.
Cambios de la orden 87: poses en paso01_datos/poses_maniqui.json; cámara del molde con su dirección (mira) y «reencuadrar»: false
= la cámara del plan tal cual (sin auto-encuadre cuando el plan no da alturas en pantalla). Lo arma y lo llama cubo02_moldes.py. Nada fijo a un canal: el set sale del molde del canal (molde.blend del cubo 02) o de una lista de cajas;
personajes, colores, alturas, complexión y accesorios salen de la config; la coreografía sale del plan (formato segmentos del 01);
las poses salen de datos/poses_maniqui.json (copia de datos de Ako). Misma lógica que moldes_hibrido.py de Ako:
auto-encuadre (buscar), escorzo con ≥2 personajes, sin oclusión (ray-cast), continuidad de eje (cámara espejada) y además
un pase ID plano (colores exactos) para que la conversión no dependa de umbrales de tono.
Uso: blender -b --factory-startup -P cubo02_moldes_blender.py -- config.json SALIDA     (US$0, solo local)"""
import bpy, sys, json, math, os
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

ARG = sys.argv[sys.argv.index('--') + 1:]
CFG = json.load(open(ARG[0])); OD = ARG[1]
PD = json.load(open(CFG.get('poses') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'paso01_datos', 'poses_maniqui.json')))
POSES, CARA, HUESOS, H0 = PD['poses'], PD['cara'], PD['huesos'], PD['altura_base_m']
for k, v in (CFG.get('poses_extra') or {}).items(): POSES[k] = v; CARA.setdefault(k, [0, 1, 0])


def lin(hexa):
    h = hexa.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


COL = CFG['colores_molde']; PJ = CFG['personajes']; IDS = [p['id'] for p in PJ]; PRE = lambda i: f'PJ~{i}~'

# ---------- set: molde del canal (cubo 02) o cajas simples ----------
ESC = CFG['escenario']
if ESC.get('molde_blend'): bpy.ops.wm.open_mainfile(filepath=ESC['molde_blend'])
else: bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
for o in list(bpy.data.objects):
    if o.type not in ('MESH', 'CAMERA'): bpy.data.objects.remove(o, do_unlink=True)
CAMS_MOLDE = {o.name: (tuple(o.location), o.data.lens, tuple(o.matrix_world.to_quaternion() @ Vector((0, 0, -1)))) for o in bpy.data.objects if o.type == 'CAMERA'}
for o in [o for o in bpy.data.objects if o.type == 'CAMERA']: bpy.data.objects.remove(o, do_unlink=True)


def col(o, c): o.color = (*c, 1)


def caja(n, c, ce, dim):
    bpy.ops.mesh.primitive_cube_add(location=ce); o = bpy.context.object; o.name = n; o.scale = [d / 2 for d in dim]; col(o, c); return o


def cil(n, c, a, b, r):
    a, b = Vector(a), Vector(b); d = b - a
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=max(d.length, 1e-3), location=(a + b) / 2, vertices=16)
    o = bpy.context.object; o.name = n; o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d if d.length > 1e-6 else Vector((0, 0, 1))); col(o, c); return o


def esf(n, c, p, r, esc=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=p, segments=24, ring_count=12); o = bpy.context.object; o.name = n; o.scale = esc; col(o, c); return o


for i, b in enumerate(ESC.get('cajas') or []): caja('SET_' + b['nombre'], lin(b.get('color', '#808080')), b['centro'], b['dim'])
# grises del set: cada objeto un gris distinto (no compite con la paleta de personajes)
SET_OBJ = [o for o in bpy.data.objects if o.type == 'MESH']
for i, o in enumerate(sorted(SET_OBJ, key=lambda o: o.name)):
    g = 0.30 + 0.45 * ((i * 0.618) % 1); col(o, (g, g, g * 1.03))
# piso + cuadrícula (regla semántica universal) sobre los límites del piso, no un tamaño fijo
piso = bpy.data.objects.get(ESC.get('piso', '')) or max(SET_OBJ, key=lambda o: o.dimensions.x * o.dimensions.y) if SET_OBJ else None
if piso:
    ws = [piso.matrix_world @ Vector(v) for v in piso.bound_box]; x0, x1 = min(v.x for v in ws), max(v.x for v in ws); y0, y1 = min(v.y for v in ws), max(v.y for v in ws); zt = max(v.z for v in ws)
    col(piso, (.55, .55, .57)); paso = ESC.get('cuadricula_m', 1.0); LIN = (.30, .30, .33)
    for i in range(int(math.ceil(x0 / paso)), int(math.floor(x1 / paso)) + 1):
        caja(f'GRID_x{i}', LIN, (i * paso, (y0 + y1) / 2, zt + .004), (.024, y1 - y0, .008))
    for j in range(int(math.ceil(y0 / paso)), int(math.floor(y1 / paso)) + 1):
        caja(f'GRID_y{j}', LIN, ((x0 + x1) / 2, j * paso, zt + .004), (x1 - x0, .024, .008))
sc.world = sc.world or bpy.data.worlds.new('W'); CIELO = lin(COL['cielo']) if COL.get('cielo') else (.08, .08, .085); sc.world.color = CIELO
sc.render.engine = 'BLENDER_WORKBENCH'; sh = sc.display.shading; sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
RX, RY = CFG.get('resolucion', [960, 540]); sc.render.resolution_x, sc.render.resolution_y = RX, RY; sc.render.resolution_percentage = 100
BASE = set(bpy.data.objects.keys())


def modo_sombreado():
    sh.light = 'STUDIO'; sh.color_type = 'OBJECT'; sh.show_shadows = True; sh.show_cavity = True; sh.show_object_outline = True; sh.object_outline_color = (0, 0, 0)


def modo_id():
    sh.light = 'FLAT'; sh.color_type = 'OBJECT'; sh.show_shadows = False; sh.show_cavity = False; sh.show_object_outline = False; sc.display.render_aa = 'OFF'


# ---------- maniquí genérico (articulaciones de Ako; altura, complexión y accesorios desde la config) ----------
def maniqui(p, pose, pos, rotz, mezcla=None):
    P = POSES[pose] if not mezcla else {k: [a + (b - a) * mezcla[1] for a, b in zip(POSES[pose][k], POSES[mezcla[0]][k])] for k in POSES[pose]}
    s = p['alto_m'] / H0; r = math.radians(rotz); g = p.get('grosor', 1.0); C = lin(p['color_molde']); n = PRE(p['id'])
    rot = lambda x, y: (x * math.cos(r) - y * math.sin(r), x * math.sin(r) + y * math.cos(r))
    def W(k, off=(0, 0, 0)):
        if isinstance(k, list): a, b, u = k; v = [x + (y - x) * u for x, y in zip(P[a], P[b])]
        else: v = P[k]
        x, y, z = [(c + o) * s for c, o in zip(v, off)]; X, Y = rot(x, y); return Vector((pos[0] + X, pos[1] + Y, pos[2] + z))
    cil(n + 'torso', C, W('pel'), W('pec'), .15 * s * g); esf(n + 'cadera', C, W('pel'), .16 * s * g)
    cil(n + 'cuello', C, W('pec'), W('cab'), .05 * s)
    for a, b, rr in HUESOS: cil(f'{n}{a}{b}', C, W(a), W(b), rr * s * (1 + (g - 1) * .45))
    for k in ('mi', 'md'): esf(n + 'mano_' + k, C, W(k), .05 * s)
    cv = CARA[pose] if not mezcla else [a + (b - a) * mezcla[1] for a, b in zip(CARA[pose], CARA[mezcla[0]])]
    fx, fy = rot(cv[0], cv[1]); fdir = Vector((fx, fy, cv[2])); fdir = fdir.normalized() if fdir.length > 1e-6 else Vector((0, 1, 0))
    c = W('cab'); rc = .12 * s
    esf(n + 'nuca', lin(COL['nuca']), c, rc); esf(n + 'cara', lin(COL['piel']), c + fdir * rc * .18, rc * .98)
    acc = {}
    for a in p.get('accesorios', []):
        c0 = W(a.get('en') or a['desde'], a.get('offset', (0, 0, 0))); ac = lin(a['color']); nm = n + 'acc_' + a['nombre']
        if a['forma'] == 'esfera': esf(nm, ac, c0, a['radio'] * s, a.get('escala', (1, 1, 1)))
        elif a['forma'] == 'cilindro': cil(nm, ac, W(a['desde'], a.get('desde_offset', (0, 0, 0))) if a.get('desde') else c0, W(a['hasta'], a.get('hasta_offset', (0, 0, 0))) if a.get('hasta') else c0 + Vector((0, 0, a.get('largo', .2) * s)), a['radio'] * s)
        elif a['forma'] == 'caja': caja(nm, ac, c0, [d * s for d in a['dim']])
        acc[a['nombre']] = c0
    return acc


# ---------- coreografía desde el plan (segmentos, formato 01) ----------
def ease(u): u = max(0., min(1., u)); return u * u * (3 - 2 * u)


def hacia(a, b): return math.degrees(math.atan2(-(b[0] - a[0]), b[1] - a[1]))


SEG = {x['id']: x['segmentos'] for x in CFG['plan']['personajes']}


def estado(t):
    E = {}
    for i in IDS:
        ss = SEG.get(i) or []; s = next((s for s in ss if s['t'][0] <= t <= s['t'][1]), None)
        if s is None:
            prev = [s for s in ss if s['t'][1] < t]; s = prev[-1] if prev else None; u = 1.0
            if s is None: continue
        else: u = ease((t - s['t'][0]) / max(1e-6, s['t'][1] - s['t'][0]))
        a = s['pos'][0]; b = s['pos'][-1]; p = [x + (y - x) * u for x, y in zip(a, b)]; p = (p + [0.0])[:3]
        if 'rot' in s: r = s['rot']
        elif s.get('mira_a'): r = None
        elif math.hypot(b[0] - a[0], b[1] - a[1]) > .05: r = hacia(a, b)
        else: r = 0
        mz = (s['a_pose'], u) if s.get('a_pose') else None
        E[i] = [p, s.get('pose', 'de_pie'), mz, r, s.get('mira_a')]
    for i, e in E.items():
        if e[3] is None:
            m = e[4]; q = E[m][0] if isinstance(m, str) and m in E else m; e[3] = hacia(e[0], q) if q else 0
    return E


PJD = {p['id']: p for p in PJ}


def construir(E):
    for n in list(bpy.data.objects.keys()):
        if n not in BASE: bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
    for i, e in E.items(): maniqui(PJD[i], e[1], e[0], e[3], e[2])
    bpy.context.view_layer.update()


def partes(i): return [o for o in bpy.data.objects if o.name.startswith(PRE(i)) and o.type == 'MESH']


def bbox(cam, i):
    pts = [world_to_camera_view(sc, cam, o.matrix_world @ v.co) for o in partes(i) for v in o.data.vertices]
    if not pts or min(p.z for p in pts) <= 0.05: return None
    return [min(p.x for p in pts), 1 - max(p.y for p in pts), max(p.x for p in pts), 1 - min(p.y for p in pts)]


def centro(i):
    ps = [o.matrix_world.translation for o in partes(i)]; return sum(ps, Vector()) / len(ps) if ps else None


def ocultos(cam, quien):
    dg = bpy.context.evaluated_depsgraph_get(); res = []
    for i in quien:
        for o in partes(i):
            p = o.matrix_world.translation; d = p - cam.location; L = d.length
            ok, loc, nrm, k, ob, _ = sc.ray_cast(dg, cam.location, d.normalized(), distance=L - .02)
            if ok and not ob.name.startswith('PJ~'): res.append(f"{o.name.replace('PJ~', '')}<-{ob.name}")
    return res


def camara(n, loc, mira, lens):
    d = bpy.data.cameras.new(n); d.lens = lens; d.clip_end = 500; c = bpy.data.objects.new(n, d); sc.collection.objects.link(c)
    c.location = loc; c.rotation_mode = 'QUATERNION'; c.rotation_quaternion = (Vector(mira) - Vector(loc)).to_track_quat('-Z', 'Y'); return c


def P2(cam, o): return world_to_camera_view(sc, cam, o.matrix_world.translation)


def lado_pantalla(cam, E, orden):
    """+1/-1 lado de pantalla. ≥2 personajes: el 2.º del orden a la derecha del 1.º = +1. Uno: cabeza→derecha de la cadera
    (tendido) o cara mirando a la derecha = +1. Igual que Ako, pero con cualquier lista de personajes."""
    construir(E); O = bpy.data.objects; vis = [i for i in orden if PRE(i) + 'cadera' in O]
    if len(vis) >= 2:
        a, k = P2(cam, O[PRE(vis[1]) + 'cadera']), P2(cam, O[PRE(vis[0]) + 'cadera'])
        if a.z > 0 and k.z > 0 and abs(a.x - k.x) > .02: return (1 if a.x > k.x else -1), 'dos_personajes'
    if not vis: return 0, 'sin_personajes'
    n = PRE(vis[0]); h, c, f = P2(cam, O[n + 'nuca']), P2(cam, O[n + 'cadera']), P2(cam, O[n + 'cara'])
    if abs(h.x - c.x) > abs(h.y - c.y) * 0.6: return (1 if h.x > c.x else -1), 'cabeza_pies'
    if abs(f.x - h.x) > .002: return (1 if f.x > h.x else -1), 'mirada'
    return 0, 'indeterminado'


def espejar_camara(loc, aim, E, orden):
    construir(E); O = bpy.data.objects; vis = [i for i in orden if PRE(i) + 'cadera' in O]; T = lambda n: O[n].matrix_world.translation
    if len(vis) >= 2: ax = T(PRE(vis[1]) + 'cadera') - T(PRE(vis[0]) + 'cadera')
    else:
        n = PRE(vis[0]); ax = T(n + 'nuca') - T(n + 'cadera')
        if math.hypot(ax.x, ax.y) < .3: ax = T(n + 'cara') - T(n + 'nuca')
    ax = Vector((ax.x, ax.y, 0)).normalized(); v = Vector(loc) - aim; vp = Vector((v.x, v.y, 0)); par = ax * vp.dot(ax)
    r = par - (vp - par); return aim + Vector((r.x, r.y, v.z))


# ---------- tomas ----------
os.makedirs(OD + '/sombreado', exist_ok=True); os.makedirs(OD + '/id', exist_ok=True)
med, EJE, informe = {}, [], {}; LADO_PREV = CFG.get('lado_prev')
for l in CFG['plan']['tomas']:
    pct = {i: max((c.get('alto_pct') or {}).get(i, 0) for c in l['cuadros']) / 100 for i in IDS}
    tg = [i for i in (l.get('orden') or IDS) if pct.get(i, 0) > 0]
    cm = l.get('camara') or {}
    if l.get('camara_molde'):
        loc0, lens, dr = CAMS_MOLDE[l['camara_molde']]
        cm = {'loc': loc0, 'mira': cm.get('mira') or [loc0[i] + dr[i] * 10 for i in range(3)], 'lente': cm.get('lente', lens)}
    estados = [estado(float(c['t'])) for c in l['cuadros']]; cs = []
    for E in estados: construir(E); cs += [centro(i) for i in tg if centro(i)]
    aim = sum(cs, Vector()) / len(cs) if cs else Vector(cm['mira'])
    C0 = Vector(cm['loc']); A0 = Vector(cm.get('mira') or aim); v = C0 - A0; az = math.atan2(v.y, v.x); el = math.atan2(v.z, math.hypot(v.x, v.y)); LENS = cm.get('lente', 28)

    def buscar(aim, near):
        cam = camara('CAM_TMP', tuple(C0), tuple(aim), LENS); BASE.add('CAM_TMP'); cands = []
        for elv in (el, el + math.radians(6), el + math.radians(12), max(el, math.radians(4))):
            for d10 in range(12, 300, 3):
                d = d10 / 10; loc = aim + Vector((math.cos(az) * math.cos(elv), math.sin(az) * math.cos(elv), math.sin(elv))) * d
                if loc.z >= 0.2: cands.append([loc, elv, d, True, 0.0])
        for E in estados:
            construir(E)
            for cd in cands:
                if not cd[3]: continue
                cam.location = cd[0]; cam.rotation_quaternion = (aim - cd[0]).to_track_quat('-Z', 'Y'); bpy.context.view_layer.update()
                for w in tg:
                    bb = bbox(cam, w)
                    if w == near:
                        if not bb or bb[2] < .05 or bb[0] > .6: cd[3] = False; break
                        continue
                    if not bb or bb[0] < .02 or bb[1] < .02 or bb[2] > .98 or bb[3] > .98: cd[3] = False; break
                    cd[4] += abs((bb[3] - bb[1]) - min(pct[w], .85))
                if cd[3] and [o for o in ocultos(cam, tg) if not (near and o.startswith(near + '~'))]: cd[3] = False
        bpy.data.objects.remove(cam, do_unlink=True); BASE.discard('CAM_TMP')
        ok = [c for c in cands if c[3]]
        if not ok: return None
        elv = sorted({c[1] for c in ok}, key=lambda x: abs(x - el))[0]
        c = min([c for c in ok if c[1] == elv], key=lambda c: c[4]); return (c[4], tuple(c[0]), c[2], math.degrees(c[1]))

    if l.get('reencuadrar') is False or not tg:   # orden 87: sin alturas en pantalla → la cámara del plan tal cual
        aim = A0; mejor = (None, tuple(C0), round((C0 - A0).length, 2), round(math.degrees(el), 1)); modo = 'camara_del_plan'
    else: mejor = buscar(aim, None); modo = 'completo'
    if not mejor and len(tg) >= 2 and modo == 'completo':
        construir(estados[-1]); near = min(tg, key=lambda w: (centro(w) - C0).length); far = [w for w in tg if w != near]
        aim = (sum((centro(w) for w in far), Vector()) / len(far)) * 0.6 + A0 * 0.4; mejor = buscar(aim, near); modo = 'escorzo_' + near
    if not mejor: mejor = (None, tuple(C0), None, None); aim = A0; modo = 'sin_encuadre_valido'
    ct = camara('CAM_EJE', mejor[1], tuple(aim), LENS); BASE.add(ct.name); lado, met = lado_pantalla(ct, estados[0], tg or IDS); cambio = bool(l.get('cambio_eje'))
    rec = {'toma': l['id'], 'lado_prev': LADO_PREV, 'lado': lado, 'metodo': met, 'cambio_eje_plan': cambio, 'accion': 'ok'}
    if LADO_PREV and lado and lado != LADO_PREV and not cambio:
        nl = espejar_camara(mejor[1], aim, estados[0], tg or IDS); ct.location = nl; ct.rotation_quaternion = (aim - nl).to_track_quat('-Z', 'Y')
        l2, _ = lado_pantalla(ct, estados[0], tg or IDS); rec.update(accion='camara_espejada_al_mismo_lado', lado_corregido=l2, camara_antes=[round(x, 2) for x in mejor[1]])
        if l2 == LADO_PREV: mejor = (mejor[0], tuple(nl), mejor[2], mejor[3]); lado = l2
        else: rec['accion'] = 'FALLO_no_se_pudo_corregir'
    BASE.discard(ct.name); bpy.data.objects.remove(ct, do_unlink=True); EJE.append(rec); print('EJE', rec, flush=True)
    informe[l['id']] = {'objetivos': tg, 'camara_plan': list(cm['loc']), 'camara_final': [round(x, 2) for x in mejor[1]], 'mira_final': [round(x, 2) for x in aim], 'lente': LENS, 'dist': mejor[2], 'elev_deg': mejor[3], 'modo': modo}
    cam = camara('CAM_' + l['id'], mejor[1], tuple(aim), LENS); BASE.add(cam.name); sc.camera = cam
    for c, E in zip(l['cuadros'], estados):
        construir(E); k = f"{l['id']}_{c['n']}"
        modo_sombreado(); sc.world.color = CIELO; sc.render.filepath = f'{OD}/sombreado/{k}.png'; bpy.ops.render.render(write_still=True)
        modo_id(); sc.render.filepath = f'{OD}/id/{k}.png'; bpy.ops.render.render(write_still=True); sc.display.render_aa = '8'
        vis = {}
        for w in IDS:
            b = bbox(cam, w)
            if b and b[2] > 0 and b[0] < 1 and b[3] > 0 and b[1] < 1:
                vis[w] = {'bbox_uv': [round(max(0, x), 3) if i < 2 else round(min(1, x), 3) for i, x in enumerate(b)]}
                for o in partes(w):
                    if '~acc_' in o.name:
                        p = world_to_camera_view(sc, cam, o.matrix_world.translation)
                        if 0 <= p.x <= 1 and 0 <= p.y <= 1 and p.z > 0: vis[w].setdefault('accesorios_uv', {})[o.name.split('~acc_')[1]] = [round(p.x, 2), round(1 - p.y, 2)]
                cara = bpy.data.objects[PRE(w) + 'cara'].matrix_world.translation; nuca = bpy.data.objects[PRE(w) + 'nuca'].matrix_world.translation
                vis[w]['mira_a_camara'] = bool((cam.location - nuca).dot(cara - nuca) > 0)
        med[k] = {'t': c['t'], 'toma': l['id'], 'vis': vis, 'ocultos': ocultos(cam, IDS), 'pose': {i: (E[i][2][0] if E[i][2] and E[i][2][1] >= 0.5 else E[i][1]) for i in E}}   # PISTA INMI (2026-10-29): orden 87 — a mitad del cambio de pose ya cuenta la pose nueva
    LADO_PREV = lado_pantalla(cam, estados[-1], tg or IDS)[0] or LADO_PREV
for n, x in (('medidas', med), ('continuidad_eje', EJE), ('camaras_ajustadas', informe)): json.dump(x, open(f'{OD}/{n}.json', 'w'), indent=1, ensure_ascii=False)
print('LISTO', len(med), 'cuadros', flush=True)
