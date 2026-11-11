"""MYIA · Taller n8n · caja 4a2 · MOLDE 3D de un escenario con Blender (headless, gratis, sin red).
Genérico: sirve para cualquier canal / escenario. Lo llama paso00_ramas.py (caja 4a2):
  blender -b --factory-startup --python blender_molde.py -- <escenario.json> <carpeta_salida>
Entrada: un registro de ramas/4a2_entrada_blender.json (receta 4a1: medidas, planta, aberturas, elementos_blender,
objetos_del_lugar_posicion (+ objetos_tamano), materiales_texturas, luz_por_escena, camaras_sugeridas, ambiente_vivo).
Orden 61: la utilería de ambiente_vivo con volumen va como bloques (colección «ambiente», mismas reglas de esquina/centro y de no tragarse
cámaras), lo plano de pared como panel de 2 cm, 0,9 m libres frente a cada puerta, y los extras de fondo como siluetas grises.
Orden 61b: lugar ABIERTO (EXT o perfil_real.que_es sin «interior» y con exterior/paisaje/Luna/fondo del mar…) = sin muros inventados ni techo;
categorías nuevas (terreno, roca, flora, fauna, agua, fenómeno) con su gris; apoyo flotando usa z_m, enterrado z ≤ 0; fondo_lejano no se modela
(solo se anota en molde.json); la vida de fondo animal va como bloque bajo.
Orden 61c: un objeto oficial o de ambiente que es un GRUPO de vehículos (nombre en plural, «fila de 4 carros», o huella de varios) ya no
va como un solo bloque: se reparte en vehículos de tamaño real, paralelos y junto a la acera de la vía (calzada, calle, carretera,
estacionamiento…) o a lo largo de su propia huella, sin tapar cámaras, puertas, pasos peatonales ni otros bloques. Lo repetido de
ambiente con cantidad en el nombre («3 tanques de agua») se parte en esas unidades. Genérico: nada atado a un lugar.
Convención: x = ancho (izquierda→derecha), y = fondo (frente y=0 → fondo), z = alto; metros; el interior va de (0,0,0) a (ancho,fondo,alto).
Salida en <carpeta_salida>: molde.blend, planta.png (cenital ortográfica), cam_NN_escX.png (Workbench, una por cámara sugerida),
luz_escX.png (Cycles CPU, luces de esa escena), molde.json (qué se armó, decisiones y avisos)."""
import bpy, sys, json, math, re, time, os
from mathutils import Vector

T0 = time.time()
bpy.ops.wm.read_factory_settings(use_empty=True)   # sin el cubo/cámara/luz de fábrica
argv = sys.argv[sys.argv.index('--') + 1:]
E = json.load(open(argv[0], encoding='utf-8')); OUT = argv[1]; os.makedirs(OUT, exist_ok=True)
RES = int(os.environ.get('MOLDE_RES', '960')); MUESTRAS = int(os.environ.get('MOLDE_MUESTRAS', '8'))
avisos, armado = [], []

def num(v, d=None):
    try: return float(v) if v is not None and str(v).strip() != '' else d
    except Exception: return d

M = E.get('medidas') or {}
W, Dm, H = num(M.get('ancho_m'), 6.0), num(M.get('fondo_m'), 6.0), num(M.get('alto_m'), 3.0)
EXT = str(E.get('int_ext') or '').upper().startswith('EXT')
# orden 61b: lugar ABIERTO (paisaje, Luna, fondo del mar, campo…) = EXT o perfil_real que dice que no es un interior. Sin muros ni techo inventados.
_PR = (E.get('ambiente_vivo') or {}).get('perfil_real') or {}
_QUE = str(_PR.get('que_es') or '').lower() if isinstance(_PR, dict) else ''
ABIERTO = EXT or (not re.search(r'\binterior', _QUE) and bool(re.search(r'exterior|abierto|aire libre|natural|paisaje|superficie de|fondo del mar|submarin|bajo el agua|campo|monta|valle|glaciar|cima|cumbre|desierto|bosque|selva|playa|lago|calle|plaza|parque|azotea|cielo|espacio exterior|orbita|órbita', _QUE)))
if not M: avisos.append('sin medidas en 4a1: se usó 6 × 6 × 3 m')

# ---------- texto → coordenadas ----------
RNUM = r'(-?\d+(?:[.,]\d+)?)(?:\s*(?:a|-|–|y)\s*(-?\d+(?:[.,]\d+)?))?'
def coord(txt, eje):
    m = re.search(rf'\b{eje}\s*[=:≈]\s*{RNUM}', str(txt or ''))
    if not m: return None
    a = float(m.group(1).replace(',', '.')); b = m.group(2)
    return (a + float(b.replace(',', '.'))) / 2 if b else a
def xyz(txt):
    return coord(txt, 'x'), coord(txt, 'y'), coord(txt, 'z')

def hex_color(txt):
    m = re.search(r'#([0-9a-fA-F]{6})', str(txt or ''))
    if m: h = m.group(1); return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    t = str(txt or '').lower()
    for k, c in [('violeta', (.55, .2, .9)), ('morad', (.5, .2, .8)), ('rojo', (1, .12, .12)), ('naranja', (1, .6, .3)), ('ámbar', (1, .72, .35)),
                 ('ambar', (1, .72, .35)), ('dorad', (1, .82, .4)), ('amarill', (1, .9, .4)), ('verde', (.3, .9, .4)), ('cian', (0, .85, 1)),
                 ('azul', (.25, .45, 1)), ('plate', (.75, .8, .9)), ('blanco', (1, .97, .92)), ('gris', (.6, .6, .62))]:
        if k in t: return c
    return None

def srgb2lin(c): return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)

# ---------- materiales ----------
MATS = {}
def mat(nombre, rgb, alpha=1.0):
    k = (nombre, rgb, alpha)
    if k in MATS: return MATS[k]
    m = bpy.data.materials.new(nombre); m.use_nodes = True
    lin = srgb2lin(rgb)
    b = m.node_tree.nodes.get('Principled BSDF'); b.inputs['Base Color'].default_value = (*lin, 1); b.inputs['Roughness'].default_value = 0.8
    if alpha < 1: b.inputs['Alpha'].default_value = alpha
    m.diffuse_color = (*lin, alpha); MATS[k] = m; return m

SUP = {'piso': (.45, .40, .35), 'pared': (.72, .72, .70), 'techo': (.85, .85, .83)}
for t in E.get('materiales_texturas') or []:
    s = str(t.get('superficie') or '').lower(); c = hex_color(t.get('color'))
    if not c: continue
    if any(k in s for k in ('piso', 'suelo', 'pavimento', 'calzada')): SUP['piso'] = c
    elif any(k in s for k in ('pared', 'muro', 'fachada')): SUP['pared'] = c
    elif 'techo' in s: SUP['techo'] = c
PALETA = [(.85, .45, .25), (.30, .60, .85), (.45, .75, .40), (.85, .75, .30), (.65, .45, .80), (.35, .75, .75), (.80, .40, .55), (.55, .55, .35)]

# ---------- colecciones ----------
def col(nombre):
    c = bpy.data.collections.new(nombre); bpy.context.scene.collection.children.link(c); return c
C_SALA, C_EL, C_OBJ, C_ETQ, C_TECHO = col('sala'), col('elementos'), col('objetos_del_lugar'), col('etiquetas_planta'), col('techo')
C_CAM = col('camaras')
C_AMB = col('ambiente')   # orden 61: zona AMBIENTE de 4a1 (ids amb-…), separada de la historia

def caja(nombre, x0, y0, z0, x1, y1, z1, material, coleccion, rot=0.0, cx=None, cy=None):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.active_object; o.name = nombre
    o.scale = (max(abs(x1 - x0), 0.01), max(abs(y1 - y0), 0.01), max(abs(z1 - z0), 0.01))
    o.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    if rot:
        o.rotation_euler[2] = math.radians(rot)
    o.data.materials.append(material)
    for c in o.users_collection: c.objects.unlink(o)
    coleccion.objects.link(o); return o

def primitiva(nombre, forma, cx, cy, z0, w, d, h, rot, material, coleccion):
    f = str(forma or '').lower()
    if 'cilind' in f or 'circular' in f:
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.5, depth=1)
    elif 'esfer' in f:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5)
    else:
        bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.active_object; o.name = nombre
    o.scale = (max(w, 0.02), max(d, 0.02), max(h, 0.02)); o.location = (cx, cy, z0 + max(h, 0.02) / 2)
    o.rotation_euler[2] = math.radians(rot or 0)
    o.data.materials.append(material)
    for c in o.users_collection: c.objects.unlink(o)
    coleccion.objects.link(o); return o

def etiqueta(txt, x, y, z, tam, coleccion=None, color=(1, 1, 1)):
    bpy.ops.object.text_add(location=(x, y, z)); o = bpy.context.active_object
    o.data.body = txt[:38]; o.data.size = tam; o.data.align_x = 'CENTER'; o.data.align_y = 'CENTER'
    o.data.materials.append(mat('etiqueta', color))
    for c in o.users_collection: c.objects.unlink(o)
    (coleccion or C_ETQ).objects.link(o); return o

# ---------- sala: piso, paredes con huecos, techo ----------
GROSOR = 0.15 if not EXT else 0.3
m_piso, m_pared, m_techo = mat('piso', SUP['piso']), mat('pared', SUP['pared']), mat('techo', SUP['techo'])
caja('piso', -GROSOR, -GROSOR, -0.1, W + GROSOR, Dm + GROSOR, 0, m_piso, C_SALA)
LARGO = {'frente': W, 'fondo': W, 'izquierda': Dm, 'derecha': Dm}
huecos = {k: [] for k in LARGO}
for a in E.get('aberturas') or []:
    p = str(a.get('pared') or '').lower().strip()
    if p not in huecos: avisos.append(f"abertura «{a.get('tipo')}» con pared «{a.get('pared')}»: no va en un muro exterior, no se recorta"); continue
    t = str(a.get('tipo') or '').lower(); w = num(a.get('ancho_m'), 1.0); h = num(a.get('alto_m'), 2.1)
    c = num(a.get('x_m'), W / 2) if p in ('frente', 'fondo') else num(a.get('y_m'), Dm / 2)
    piso_ = num(a.get('alto_desde_piso_m'), num(a.get('z_m'), 0.9 if 'ventana' in t else 0.0))
    if piso_ + h > H: piso_ = max(0.0, H - h)
    L = LARGO[p]; a0, a1 = max(0.0, c - w / 2), min(L, c + w / 2)
    if a1 - a0 < 0.05: avisos.append(f"abertura «{t}» en {p} queda fuera del muro (centro {c} m)"); continue
    huecos[p].append((a0, a1, piso_, min(H, piso_ + h), t))
    armado.append(f"hueco {t} en pared {p}: {a1 - a0:.2f} × {min(H, piso_ + h) - piso_:.2f} m desde {piso_:.2f} m (centro {c:g} m)")

muros_ext = set(LARGO)
if ABIERTO:   # exterior o lugar abierto: solo hay muros donde 4a1 dice que hay fachada (pared con puerta/ventana, o envolvente alta)
    muros_ext = {p for p, v in huecos.items() if any(t not in ('otro', 'pasillo') for *_, t in v)}
    env_alta = any((num(b.get('ancho_m'), 0) >= 0.9 * W and num(b.get('fondo_m'), 0) >= 0.9 * Dm and num(b.get('alto_m'), 0) >= 0.6 * H)
                   for b in E.get('elementos_blender') or [])
    if env_alta and H > 4: muros_ext |= {'izquierda', 'derecha'}
    armado.append(('exterior' if EXT else 'lugar abierto') + ': muros solo en ' + (', '.join(sorted(muros_ext)) or 'ninguno') + '; sin techo')

def muro(p, hs):
    L = LARGO[p]; hs = sorted(hs); segs, x = [], 0.0
    for a0, a1, z0, z1, _ in hs:
        if a0 > x: segs.append((x, a0, 0, H))
        if z0 > 0.01: segs.append((a0, a1, 0, z0))
        if z1 < H - 0.01: segs.append((a0, a1, z1, H))
        x = max(x, a1)
    if x < L: segs.append((x, L, 0, H))
    for i, (s0, s1, z0, z1) in enumerate(segs):
        if s1 - s0 < 0.005: continue
        if p == 'frente': caja(f'muro_frente_{i}', s0, -GROSOR, z0, s1, 0, z1, m_pared, C_SALA)
        elif p == 'fondo': caja(f'muro_fondo_{i}', s0, Dm, z0, s1, Dm + GROSOR, z1, m_pared, C_SALA)
        elif p == 'izquierda': caja(f'muro_izq_{i}', -GROSOR, s0, z0, 0, s1, z1, m_pared, C_SALA)
        else: caja(f'muro_der_{i}', W, s0, z0, W + GROSOR, s1, z1, m_pared, C_SALA)
for p in LARGO:
    if p in muros_ext:
        # una abertura que ocupa casi todo el muro (tipo otro/pasillo) = ese lado está abierto
        if any(t in ('otro', 'pasillo') and a1 - a0 >= 0.8 * LARGO[p] for a0, a1, _, _, t in huecos[p]):
            armado.append(f'pared {p}: abierta (abertura de casi todo el ancho)'); continue
        muro(p, huecos[p])
if not ABIERTO: caja('techo', -GROSOR, -GROSOR, H, W + GROSOR, Dm + GROSOR, H + 0.1, m_techo, C_TECHO)
armado.append(f"sala {W:g} × {Dm:g} × {H:g} m ({'exterior' if EXT else 'abierto (perfil_real)' if ABIERTO else 'interior'}, planta {(E.get('planta') or {}).get('forma', '?')})")

# ---------- orden 61c: grupos de vehículos y cosas repetidas (genérico: calle, carretera, estacionamiento, puerto, garaje…) ----------
import unicodedata
def _slug(t): return re.sub(r'[^a-z0-9]+', '-', unicodedata.normalize('NFKD', str(t or '')).encode('ascii', 'ignore').decode().lower()).strip('-')
_VEH = r'vehiculo|carro|auto|coche|automovil|taxi|camion|camioneta|bus|buseta|autobus|moto|motocicleta|furgon|furgoneta|patrulla|jeep|pickup|trafico|sedan|hatchback'
def es_vehiculo(*txt): return bool(re.search(rf'(^|-)({_VEH})(e?s)?(-|$)', '-'.join(_slug(t) for t in txt)))
def vehiculos_plural(*txt):
    t = '-'.join(_slug(t) for t in txt)
    return es_vehiculo(*txt) and bool(re.search(rf'(^|-)(({_VEH})e?s|trafico|fila|filas|hilera|estacionados|aparcados|parqueados|caravana|flota|conjunto)(-|$)', t))
_NUMS = {'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5, 'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9, 'diez': 10, 'par': 2}
def cantidad_en(txt):
    mp = re.search(r'[(\[]\s*[x×]?\s*(\d{1,2})\s*[)\]]\s*$', str(txt or ''))   # «Carros estacionados (4)»
    if mp: return int(mp.group(1))
    t = _slug(txt); m = re.search(r'(^|-)(\d{1,2})-', t)   # un número al FINAL del nombre es una etiqueta («Tanque 2»), no una cantidad
    if m and re.search(r'(^|-)(n|no|nro|num|numero)-\d{1,2}(-|$)', t): m = None
    if m and not re.search(r'(^|-)\d{1,2}-(m|cm|mm|metros?|pisos?|plantas?|km|kg|l|litros?|w|v)(-|$)', t): return int(m.group(2))
    for k, v in _NUMS.items():
        if re.search(rf'(^|-){k}(-|$)', t): return v
    return None
def unidad_vehiculo(txt, w=None, d=None, h=None):
    t = _slug(txt)
    if 'moto' in t: base = (0.8, 2.1, 1.2)
    elif re.search(r'(^|-)(bus|buses|autobus|autobuses|buseta|busetas)(-|$)', t): base = (2.5, 11.0, 3.2)
    elif re.search(r'camion(?!eta)', t): base = (2.5, 8.0, 3.2)
    else: base = (1.8, 4.4, 1.5)
    if w and d and h and max(w, d) <= 1.3 * base[1] and min(w, d) <= 1.5 * base[0] and max(w, d) >= 0.5 * base[1]: base = (min(w, d), max(w, d), h)   # ya es UNA unidad
    return base
VIAS = r'(^|-)(calzada|calzadas|carretera|avenida|asfalto|carril|carriles|via|vias|autopista|calle|pavimento|estacionamiento|parqueadero|aparcamiento|rotonda|camino|pista)(-|$)'
CRUCES = r'(^|-)(cebra|paso-peatonal|cruce-peatonal|paso-de-peatones)(-|$)'
RECT_VIA, OCUPADOS, VEH_PEND = [], [], []   # vías (x0,y0,x1,y1); huellas puestas (x0,y0,x1,y1); vehículos en grupo por repartir
def anota_ocupado(n, cx, cy, ex, ey, h):
    r_ = (cx - ex / 2, cy - ey / 2, cx + ex / 2, cy + ey / 2)
    if re.search(VIAS, _slug(n)) and h <= 0.35: RECT_VIA.append(r_); return
    if (h > 0.05 or re.search(CRUCES, _slug(n))) and ex * ey < 0.4 * W * Dm: OCUPADOS.append(r_)

# ---------- elementos_blender (esquina o centro: se decide por cuál cabe en la sala) ----------
def cabe(a0, a1, L, tol): return a0 >= -tol and a1 <= L + tol
# puntos de cámara (posición y «mira hacia») como pista: un bloque no debe tragarse la cámara
PUNTOS = []
for _cs in E.get('camaras_sugeridas') or []:
    for _k in ('posicion', 'mira_hacia'):
        _p = xyz(_cs.get(_k))
        if _p[0] is not None and _p[1] is not None: PUNTOS.append((_p[0], _p[1]))
def tragadas(x0, y0, x1, y1): return sum(1 for px, py in PUNTOS if x0 + 0.05 < px < x1 - 0.05 and y0 + 0.05 < py < y1 - 0.05)
def ubica(x, y, w, d, r=0.0, centro_declarado=False):
    tol = 0.05 * max(W, Dm) + 0.1
    giro90 = abs((r % 180) - 90) < 1
    cw, cd_ = (d, w) if giro90 else (w, d)          # huella real en x/y del bloque centrado y girado
    esq = cabe(x, x + w, W, tol) and cabe(y, y + d, Dm, tol)          # esquina: huella en ejes del mundo
    cen = cabe(x - cw / 2, x + cw / 2, W, tol) and cabe(y - cd_ / 2, y + cd_ / 2, Dm, tol)
    if (x == 0 and y == 0) or (esq and not cen): return x + w / 2, y + d / 2, 'esquina', giro90
    if centro_declarado and cen:   # orden 61: el ambiente declara el CENTRO; solo se lee como esquina si el centro no cabe
        return x, y, 'centro', False
    if esq and cen and (abs(x + w - W) < 0.15 or abs(y + d - Dm) < 0.15):   # pegado a un muro leyéndolo desde la esquina
        return x + w / 2, y + d / 2, 'esquina (pegado al muro)', giro90
    if esq and cen:
        te, tc = tragadas(x, y, x + w, y + d), tragadas(x - cw / 2, y - cd_ / 2, x + cw / 2, y + cd_ / 2)
        if te < tc: return x + w / 2, y + d / 2, f'esquina: centrado tapaba {tc} cámara(s)/mira(s)', giro90
    return x, y, 'centro' if cen else 'centro (se sale de la sala)', False

for i, b in enumerate(E.get('elementos_blender') or []):
    n = str(b.get('nombre') or f'elemento {i + 1}'); f = str(b.get('forma') or '').lower()
    x, y, z = num(b.get('x_m'), W / 2), num(b.get('y_m'), Dm / 2), num(b.get('z_m'), 0.0)
    w, d, h = num(b.get('ancho_m'), 1.0), num(b.get('fondo_m'), 1.0), num(b.get('alto_m'), 1.0); r = num(b.get('rotacion_grados'), 0.0)
    huella = w >= 0.9 * W and d >= 0.9 * Dm
    if huella and h <= 0.35:
        if re.search(VIAS, _slug(n)): RECT_VIA.append((0.0, 0.0, W, Dm))   # orden 61c: toda la zona es vía
        armado.append(f"«{n}»: es el piso/losa completa → ya está en la sala"); continue
    if huella and h >= 0.6 * H:
        armado.append(f"«{n}»: es la envolvente de la sala ({w:g}×{d:g}×{h:g} m) → la sala ya la representa"); continue
    if w > 1.5 * W or d > 1.5 * Dm:
        armado.append(f"«{n}»: contexto lejano más grande que la sala ({w:g}×{d:g} m) → no se modela como bloque"); continue
    if min(w, d) <= 0.35 and h >= 0.8 * H and (d >= 0.9 * Dm or w >= 0.9 * W) and (x >= W - 0.5 or x <= 0.5 or y <= 0.5 or y >= Dm - 0.5):
        armado.append(f"«{n}»: coincide con un muro de la sala → se usan los muros (con sus huecos)"); continue
    if huella:   # perímetro bajo (pretil, zócalo, baranda)
        mm = mat(f'el_{i}', PALETA[i % len(PALETA)]); g = 0.2
        for k, (a, bb, c, dd) in enumerate([(0, 0, W, g), (0, Dm - g, W, Dm), (0, 0, g, Dm), (W - g, 0, W, Dm)]):
            caja(f'{n[:30]}_{k}', a, bb, z, c, dd, z + h, mm, C_EL)
        armado.append(f"«{n}»: perímetro de {h:g} m de alto"); etiqueta(n, W / 2, g * 3, H + 0.5, max(W, Dm) / 45); continue
    cx, cy, conv, mundo = ubica(x, y, w, d, r)
    ex, ey = (w, d) if (mundo or abs((r % 180) - 90) >= 1) else (d, w)   # huella real en el mundo
    if mundo: w, d = d, w   # esquina con giro 90/270: el bloque ocupa x..x+ancho, y..y+fondo
    nt = tragadas(cx - ex / 2, cy - ey / 2, cx + ex / 2, cy + ey / 2)
    if h >= 0.6 * H and nt and abs(r % 90) < 1:   # zona alta con cámaras adentro (sala dentro de sala, muros): se hace hueca
        mm = mat(f'el_{i}', PALETA[i % len(PALETA)]); g = 0.08; x0, y0, x1, y1 = cx - ex / 2, cy - ey / 2, cx + ex / 2, cy + ey / 2
        for k, (a, bb, c, dd) in enumerate([(x0, y0, x1, y0 + g), (x0, y1 - g, x1, y1), (x0, y0, x0 + g, y1), (x1 - g, y0, x1, y1)]):
            caja(f'{n[:30]}_{k}', a, bb, z, c, dd, z + h, mm, C_EL)
        armado.append(f"«{n}»: zona hueca {ex:g}×{ey:g}×{h:g} m en x={x0:.2f}..{x1:.2f}, y={y0:.2f}..{y1:.2f} ({conv}; tiene {nt} cámara(s)/mira(s) adentro → solo sus paredes)")
        etiqueta(n, cx, cy, H + 0.5, max(W, Dm) / 45); continue
    if 'plano' in f and h < 0.08 and z <= 0.06:
        avisos.append(f"«{n}»: plano a nivel del piso, se dibuja con 2 cm"); h = 0.02
    primitiva(n[:60], f, cx, cy, z, w, d, h, r, mat(f'el_{i}', PALETA[i % len(PALETA)]), C_EL)
    anota_ocupado(n, cx, cy, ex, ey, h)
    armado.append(f"«{n}»: {f or 'caja'} {w:g}×{d:g}×{h:g} m en x={cx:.2f}, y={cy:.2f}, z={z:g}, giro {r:g}° ({conv})")
    if conv.endswith('sala)'): avisos.append(f"«{n}» se sale de la sala ({cx:.2f}, {cy:.2f}) – revisar 4a1")
    etiqueta(n, cx, cy, H + 0.5, max(W, Dm) / 45)

# ---------- objetos del lugar (centro, apoyados en z) ----------
TAM = E.get('objetos_tamano') or {}
# t353u: un mismo objeto puede estar en VARIAS posiciones, una por grupo de escenas («escenas»). Cada posición es su propio bloque
# (nombre <id>__e<escenas>) y en las vistas de una escena solo se ven las posiciones de esa escena. Genérico para cualquier escenario.
import collections as _co
_REP = _co.Counter(str(o.get('objeto_id')) for o in (E.get('objetos_del_lugar_posicion') or []))
POR_ESC = {}   # objeto de Blender → {escenas donde está}; sin «escenas» = está en todas
objetos_por_escena = []
for i, o in enumerate(E.get('objetos_del_lugar_posicion') or []):
    oid0 = o.get('objeto_id') or f'objeto_{i + 1}'; t = TAM.get(oid0) or {}; ta = t.get('tamano') or {}
    escs_o = sorted({str(s) for s in (o.get('escenas') or [])}, key=lambda s: (len(s), s))
    oid = f"{oid0}__e{'-'.join(escs_o) or 'todas'}" if _REP[str(oid0)] > 1 else oid0
    w, d, h = (num(ta.get(k), None) for k in ('ancho_cm', 'fondo_cm', 'alto_cm'))
    falta = [k for k, v in zip(('ancho', 'fondo', 'alto'), (w, d, h)) if v is None]
    w, d, h = (w or 50) / 100, (d or 50) / 100, (h or 50) / 100
    if falta: avisos.append(f"{oid}: sin {'/'.join(falta)} en 4b1/4c1 → 50 cm")
    x, y, z = num(o.get('x_m'), W / 2), num(o.get('y_m'), Dm / 2), num(o.get('z_m'), 0.0); r = num(o.get('rotacion_grados'), 0.0)
    if vehiculos_plural(oid, t.get('nombre')):   # orden 61c: «vehículos …» es un grupo, no un bloque: se reparte después (junto a la acera)
        VEH_PEND.append({'id': oid, 'nombre': t.get('nombre') or oid, 'x': x, 'y': y, 'w': w, 'd': d, 'h': h, 'n': cantidad_en(t.get('nombre')) or num(t.get('cantidad')),
                         'propia': False, 'col': C_OBJ, 'mat': mat(f'obj_{i}', PALETA[(i + 3) % len(PALETA)])}); continue
    # si se sale de la sala lo meto dentro (interior) y lo aviso
    rr = math.radians(r); ew = abs(w * math.cos(rr)) + abs(d * math.sin(rr)); ed = abs(w * math.sin(rr)) + abs(d * math.cos(rr))
    nx, ny = min(max(x, ew / 2), W - ew / 2) if ew < W else W / 2, min(max(y, ed / 2), Dm - ed / 2) if ed < Dm else Dm / 2
    if not ABIERTO and (abs(nx - x) > 0.01 or abs(ny - y) > 0.01):
        avisos.append(f"{oid}: se salía de la sala en ({x:g}, {y:g}) → movido a ({nx:.2f}, {ny:.2f})"); x, y = nx, ny
    if z + h > H and not ABIERTO: avisos.append(f"{oid}: atraviesa el techo (z {z:g} + alto {h:g} > {H:g})")
    nom = (t.get('nombre') or oid0) + (f" (esc {', '.join(escs_o)})" if _REP[str(oid0)] > 1 and escs_o else '')
    _ob = primitiva(oid, (t.get('forma') or 'caja'), x, y, z, w, d, h, r, mat(f'obj_{i}', PALETA[(i + 3) % len(PALETA)]), C_OBJ)
    if _ob is None: _ob = bpy.context.view_layer.objects.active
    if escs_o and _ob is not None: POR_ESC[_ob] = set(escs_o)
    objetos_por_escena.append({'objeto_id': oid0, 'bloque': _ob.name if _ob is not None else oid, 'escenas': escs_o or 'todas', 'x_m': x, 'y_m': y, 'z_m': z})
    armado.append(f"objeto {oid}: {w:g}×{d:g}×{h:g} m en x={x:g}, y={y:g}, z={z:g}, giro {r:g}°")
    etiqueta(nom, x, y, H + 0.6, max(W, Dm) / 50, color=(1, .95, .6))

# ---------- orden 61: AMBIENTE VIVO (zona ambiente de 4a1; lo que tiene volumen) ----------
AV = E.get('ambiente_vivo') or {}
OBJ_HIST = {str(o.get('objeto_id')) for o in (E.get('objetos_del_lugar_posicion') or [])}
PUERTAS = []   # zona libre de 0,9 m frente a cada puerta (dentro de la sala)
for p_, hs in huecos.items():
    for a0, a1, z0, z1, t_ in hs:
        if 'puerta' not in t_ and 'porton' not in t_ and 'portón' not in t_: continue
        PUERTAS.append({'frente': (a0, 0, a1, 0.9), 'fondo': (a0, Dm - 0.9, a1, Dm), 'izquierda': (0, a0, 0.9, a1), 'derecha': (W - 0.9, a0, W, a1)}[p_])
def choca(x0, y0, x1, y1, z): return [q for q in PUERTAS if z < 2.0 and x0 < q[2] and x1 > q[0] and y0 < q[3] and y1 > q[1]]
GRIS = {'mueble': (.62, .52, .42), 'utileria': (.70, .66, .58), 'decoracion': (.78, .68, .55), 'vegetacion': (.35, .60, .30), 'vehiculo': (.45, .50, .58),
        'infraestructura': (.55, .57, .60), 'senal_uso': (.75, .72, .65), 'otro': (.65, .65, .65),
        'terreno': (.58, .55, .50), 'roca_mineral': (.50, .50, .50), 'flora': (.35, .60, .30), 'fauna': (.70, .55, .40),   # orden 61b
        'agua_fluido': (.35, .55, .75), 'fenomeno_natural': (.80, .80, .85)}
amb_n = {'bloques': 0, 'paneles': 0, 'sin_volumen': 0, 'extras': 0, 'ascendidos_omitidos': 0, 'movidos_por_puerta': 0, 'vehiculos_repartidos': 0, 'repetidos_partidos': 0}
def expandir(lista):   # orden 61c: «3 tanques de agua» con una huella que cubre el grupo → 3 unidades a lo largo de su lado largo
    out = []
    for q in lista:
        if not isinstance(q, dict): continue
        n_ = cantidad_en(q.get('nombre')); w_, d_ = num(q.get('ancho_m'), 0.5), num(q.get('fondo_m'), 0.5)
        if (str(q.get('categoria')) == 'vehiculo' or es_vehiculo(q.get('nombre'))) or not n_ or not 2 <= n_ <= 12 or q.get('tiene_volumen') is False \
           or str(q.get('apoyo') or 'piso') not in ('piso', 'sobre_otro', 'enterrado', 'techo') or max(w_, d_) < 1.5 * min(w_, d_) or max(w_, d_) / n_ < 0.25:
            out.append(q); continue
        r_ = math.radians(num(q.get('rotacion_grados'), 0.0)); largo = max(w_, d_); pieza = largo / n_
        ux, uy = (math.cos(r_), math.sin(r_)) if w_ >= d_ else (-math.sin(r_), math.cos(r_))
        for k in range(n_):
            off = (k - (n_ - 1) / 2) * pieza; q2 = dict(q)
            q2['ambiente_id'] = f"{q.get('ambiente_id') or 'amb'}-{k + 1}"; q2['x_m'] = num(q.get('x_m'), W / 2) + off * ux; q2['y_m'] = num(q.get('y_m'), Dm / 2) + off * uy
            if w_ >= d_: q2['ancho_m'] = pieza * 0.85
            else: q2['fondo_m'] = pieza * 0.85
            out.append(q2)
        amb_n['repetidos_partidos'] += 1; armado.append(f"ambiente «{q.get('nombre')}»: grupo de {n_} → {n_} unidades a lo largo de su huella")
    return out
for i, q in enumerate(expandir(AV.get('utileria_ambiente') or [])):
    aid = str(q.get('ambiente_id') or f'amb-{i + 1}'); n = str(q.get('nombre') or aid)
    asc = (q.get('ascender_a_oficial') or {}).get('objeto_id')
    if asc and asc in OBJ_HIST:
        amb_n['ascendidos_omitidos'] += 1; armado.append(f"ambiente «{n}»: asciende a oficial {asc} y ese objeto ya está → no se duplica"); continue
    if q.get('tiene_volumen') is False:
        amb_n['sin_volumen'] += 1; continue
    w, d, h = num(q.get('ancho_m'), 0.5), num(q.get('fondo_m'), 0.5), num(q.get('alto_m'), 0.5)
    x, y, z = num(q.get('x_m'), W / 2), num(q.get('y_m'), Dm / 2), num(q.get('z_m'), 0.0); r = num(q.get('rotacion_grados'), 0.0)
    f = str(q.get('forma') or 'caja').lower(); pa = str(q.get('pared') or 'ninguna').lower(); apoyo = str(q.get('apoyo') or 'piso').lower()
    if w > 1.5 * W or d > 1.5 * Dm: armado.append(f"ambiente «{n}»: más grande que la sala → no se modela"); continue
    if (str(q.get('categoria')) == 'vehiculo' or es_vehiculo(n)) and apoyo in ('piso', 'enterrado'):   # orden 61c: grupo de vehículos → se reparte
        uw_, ul_, _ = unidad_vehiculo(n)
        if vehiculos_plural(n) or (cantidad_en(n) or 0) >= 2 or max(w, d) > 1.6 * ul_:
            VEH_PEND.append({'id': aid, 'nombre': n, 'x': x, 'y': y, 'w': w, 'd': d, 'h': h, 'r': r, 'n': cantidad_en(n), 'propia': max(w, d) > 1.6 * ul_,
                             'col': C_AMB, 'mat': mat(f'amb_{i}', hex_color(q.get('color')) or GRIS['vehiculo'])}); continue
    if apoyo in ('pared', 'colgado') and pa in LARGO:   # pegado a su pared: «ancho» corre a lo largo del muro; lo plano va como panel de 2 cm
        largo_, grueso = (max(w, d), 0.02) if (f == 'plano' or min(w, d) < 0.06) else (w, d)
        if grueso == 0.02: amb_n['paneles'] += 1
        r = 0.0
        if pa in ('frente', 'fondo'): w, d = largo_, grueso; y = grueso / 2 if pa == 'frente' else Dm - grueso / 2
        else: w, d = grueso, largo_; x = grueso / 2 if pa == 'izquierda' else W - grueso / 2
        ex, ey, conv = w, d, f'pegado a pared {pa}'
    else:
        x, y, conv, mundo = ubica(x, y, w, d, r, centro_declarado=True)
        if mundo: w, d = d, w
        ex, ey = (w, d) if abs((r % 180) - 90) >= 1 else (d, w)
    if apoyo == 'techo' and not ABIERTO: z = max(0.0, H - h)
    if apoyo == 'flotando': z = num(q.get('z_m'), max(0.0, H / 2 - h / 2))   # en el agua, el aire o sin gravedad: su altura real
    if apoyo == 'enterrado': z = min(num(q.get('z_m'), -h * 0.3), 0.0)      # medio hundido en el suelo
    for _ in range(3):   # 0,9 m libres frente a las puertas: lo corro afuera de esa zona
        c_ = choca(x - ex / 2, y - ey / 2, x + ex / 2, y + ey / 2, z)
        if not c_: break
        q0 = c_[0]; opciones = [(q0[2] - (x - ex / 2), 0), ((q0[0] - (x + ex / 2)), 0), (0, q0[3] - (y - ey / 2)), (0, q0[1] - (y + ey / 2))]
        dx, dy = min(opciones, key=lambda o: abs(o[0]) + abs(o[1]))
        x, y = x + dx + (0.01 if dx > 0 else -0.01 if dx < 0 else 0), y + dy + (0.01 if dy > 0 else -0.01 if dy < 0 else 0)
        amb_n['movidos_por_puerta'] += 1; avisos.append(f"ambiente «{n}»: tapaba una puerta → movido a ({x:.2f}, {y:.2f})")
    if not ABIERTO:
        x = min(max(x, ex / 2), W - ex / 2) if ex < W else W / 2; y = min(max(y, ey / 2), Dm - ey / 2) if ey < Dm else Dm / 2
    if tragadas(x - ex / 2, y - ey / 2, x + ex / 2, y + ey / 2) and h >= 1.2:
        avisos.append(f"ambiente «{n}»: una cámara queda dentro → se oculta en esa vista")
    color = hex_color(q.get('color')) or GRIS.get(str(q.get('categoria') or 'otro'), GRIS['otro'])
    primitiva(aid[:60], f if f in ('caja', 'cilindro', 'plano') else 'caja', x, y, z, w, d, max(h, 0.02), r, mat(f'amb_{i}', color), C_AMB)
    anota_ocupado(n, x, y, ex, ey, h)
    amb_n['bloques'] += 1
    armado.append(f"ambiente «{n}» ({aid}): {f} {w:g}×{d:g}×{h:g} m en x={x:.2f}, y={y:.2f}, z={z:g} ({conv})" + (f" · asciende a {asc}" if asc else ''))
    if max(w, d) >= 0.6: etiqueta(n, x, y, H + 0.45, max(W, Dm) / 70, color=(.75, .85, 1))
# orden 61c: reparto de los grupos de vehículos: paralelos y junto a la acera (bordes largos de la vía), o en fila sobre su propia huella
def _solapa(a, b, m=0.0): return a[0] < b[2] + m and a[2] > b[0] - m and a[1] < b[3] + m and a[3] > b[1] - m
def _plazas(via, uw, ul, una_fila=False):
    x0, y0, x1, y1 = via; en_y = (y1 - y0) >= (x1 - x0); paso = ul + 1.3; out = []
    a0, a1, b0, b1 = (y0, y1, x0, x1) if en_y else (x0, x1, y0, y1)
    bordes = [(b0 + b1) / 2] if una_fila or (b1 - b0) < 2 * uw + 1.5 else [b0 + uw / 2 + 0.25, b1 - uw / 2 - 0.25]
    m_ = 0.0 if una_fila else 0.8
    for lado, bb in enumerate(bordes):
        aa = a0 + m_ + ul / 2
        while aa + ul / 2 <= a1 - m_ + 1e-6:
            out.append(((bb, aa, uw, ul) if en_y else (aa, bb, ul, uw)) + (lado,)); aa += paso
    return out
for v in VEH_PEND:
    uw, ul, uh = unidad_vehiculo(v['nombre'], v['w'], v['d'], v['h'])
    if v['propia']:   # su huella ya marca dónde está la fila (p. ej. junto a la acera): una fila a lo largo de su lado largo
        ex_, ey_ = (v['w'], v['d']) if abs((v.get('r', 0) % 180) - 90) >= 1 else (v['d'], v['w'])
        via, donde = (v['x'] - ex_ / 2, v['y'] - ey_ / 2, v['x'] + ex_ / 2, v['y'] + ey_ / 2), 'a lo largo de su huella'
        pl = _plazas(via, uw, ul, una_fila=True)
    else:
        via = min(RECT_VIA, key=lambda r_: (not (r_[0] <= v['x'] <= r_[2] and r_[1] <= v['y'] <= r_[3]), abs((r_[0] + r_[2]) / 2 - v['x']) + abs((r_[1] + r_[3]) / 2 - v['y']))) if RECT_VIA else None
        if via: donde = 'junto a la acera de la vía'
        else:   # sin vía declarada: una franja en el sentido largo de la zona, pasando por donde el guion lo puso
            L_ = min(max(W, Dm), 6 * (ul + 1.3))
            via = ((max(0, v['x'] - L_ / 2), v['y'] - uw / 2 - 0.3, min(W, v['x'] + L_ / 2), v['y'] + uw / 2 + 0.3) if W >= Dm else
                   (v['x'] - uw / 2 - 0.3, max(0, v['y'] - L_ / 2), v['x'] + uw / 2 + 0.3, min(Dm, v['y'] + L_ / 2)))
            donde = 'en fila (no hay vía declarada)'
        pl = _plazas(via, uw, ul)
    libres = []
    for (cx, cy, ew, ed, lado) in pl:
        rr = (cx - ew / 2, cy - ed / 2, cx + ew / 2, cy + ed / 2)
        if any(_solapa(rr, o_, 0.2) for o_ in OCUPADOS) or tragadas(rr[0] - 0.6, rr[1] - 0.6, rr[2] + 0.6, rr[3] + 0.6) or choca(*rr, 0.0): continue
        if not ABIERTO and not (0 <= rr[0] and rr[2] <= W and 0 <= rr[1] and rr[3] <= Dm): continue
        libres.append((cx, cy, ew, ed))
    try: n_ = int(v['n']) if v['n'] else 0
    except Exception: n_ = 0
    if not n_: n_ = len(libres) if v['propia'] else max(min(2, len(libres)), min(10, math.ceil(0.6 * len(libres))))
    if n_ < len(libres): libres = [libres[round(k * (len(libres) - 1) / max(n_ - 1, 1))] for k in range(n_)] if n_ > 1 else libres[len(libres) // 2:len(libres) // 2 + 1]
    for k, (cx, cy, ew, ed) in enumerate(libres):
        primitiva(f"{v['id'][:52]}_{k + 1}", 'caja', cx, cy, 0.0, ew, ed, uh, 0.0, v['mat'], v['col'])
        OCUPADOS.append((cx - ew / 2, cy - ed / 2, cx + ew / 2, cy + ed / 2))
    amb_n['vehiculos_repartidos'] += len(libres)
    if libres: etiqueta(str(v['nombre']), libres[0][0], libres[0][1], H + 0.5, max(W, Dm) / 60, color=(1, .95, .6) if v['col'] is C_OBJ else (.75, .85, 1))
    armado.append(f"vehículos «{v['nombre']}» ({v['id']}): {len(libres)} de {uw:g}×{ul:g}×{uh:g} m {donde} ({len(pl)} plazas, orden 61c)")
    if not libres: avisos.append(f"vehículos «{v['nombre']}»: no quedó ninguna plaza libre para repartirlos")
m_extra = mat('extra_fondo', (.55, .55, .55))
for j, g in enumerate(AV.get('extras_fondo') or []):
    gx, gy = num(g.get('x_m')), num(g.get('y_m'))
    if gx is None or gy is None: continue
    try: cant = max(1, min(4, int(num(g.get('cantidad'), 1))))
    except Exception: cant = 1
    ani = str(g.get('tipo') or '').lower() == 'animal'   # orden 61b: vida de fondo; un animal va como bloque bajo
    for k in range(cant):
        ox, oy = gx + 0.6 * (k % 2) - 0.3 * (cant > 1), gy + 0.6 * (k // 2)
        if not ABIERTO: ox, oy = min(max(ox, 0.25), W - 0.25), min(max(oy, 0.25), Dm - 0.25)
        if ani: primitiva(f"extra_{j + 1}_{k + 1}", 'caja', ox, oy, 0, 0.5, 0.3, 0.5, 0, m_extra, C_AMB)
        else: primitiva(f"extra_{j + 1}_{k + 1}", 'cilindro', ox, oy, 0, 0.45, 0.45, 1.7, 0, m_extra, C_AMB)
        amb_n['extras'] += 1
    armado.append(f"extras de fondo {j + 1}: {cant} silueta(s) gris(es) en ({gx:g}, {gy:g}) · {str(g.get('que_hacen') or '')[:60]}")
# fondo_lejano NO se modela: solo se anota para quien pinta (4a4/4a5)
FONDO_LEJANO = [{'que_es': g.get('que_es'), 'direccion': g.get('direccion'), 'distancia_aprox_m': g.get('distancia_aprox_m'), 'tamano_aparente': g.get('tamano_aparente')}
                for g in (AV.get('fondo_lejano') or []) if isinstance(g, dict)]
if FONDO_LEJANO: armado.append(f"fondo lejano (no se modela, se pinta): {len(FONDO_LEJANO)} · " + ', '.join(str(g['que_es']) for g in FONDO_LEJANO[:5]))
if AV or VEH_PEND: armado.append(f"ambiente vivo: {amb_n['bloques']} bloques ({amb_n['paneles']} paneles de pared), {amb_n['extras']} extras, {amb_n['sin_volumen']} sin volumen (solo para pintar), {amb_n['vehiculos_repartidos']} vehículos repartidos, {amb_n['repetidos_partidos']} grupos partidos")

# ---------- luces por escena ----------
def hora_tipo(txt):
    t = str(txt or '').lower()
    if any(k in t for k in ('noche', 'madrug', 'oscur', 'a. m.', 'a.m')): return 'noche'
    if 'tarde' in t: return 'tarde'
    if any(k in t for k in ('mañana', 'manana', 'amanec', 'día', 'dia', 'mediod')): return 'dia'
    return 'noche' if not EXT else 'dia'
POT = {'baja': 0.4, 'media': 1.0, 'alta': 2.2}
escala = 15 * (max(W, Dm, H) / 4) ** 2   # vatios de una luz «media» según el tamaño del espacio (≈ 28 W en un cuarto de 5.5 m)
luces = {}
for j, l in enumerate(E.get('luz_por_escena') or []):
    esc = str(l.get('escena') or j + 1); cname = f'luz_esc{esc}'
    c = bpy.data.collections.new(cname); bpy.context.scene.collection.children.link(c); luces[esc] = (c, hora_tipo(l.get('hora')), l)
    for k, fu in enumerate(l.get('fuentes') or []):
        px, py, pz = xyz(fu.get('posicion'))
        pos_txt = str(fu.get('posicion') or '').lower(); sin = px is None and py is None
        if px is None: px = W / 2
        if py is None: py = Dm / 2
        if pz is None: pz = H * 1.5 if (EXT and ('cenit' in pos_txt or 'cielo' in pos_txt)) else (H * 0.9 if 'cenit' in pos_txt else min(H * 0.6, 2.5))
        if sin: avisos.append(f"escena {esc}: luz «{fu.get('tipo')}» sin coordenadas («{fu.get('posicion')}») → x={px:g}, y={py:g}, z={pz:g}")
        ld = bpy.data.lights.new(f'esc{esc}_{k}', 'POINT'); ld.color = hex_color(fu.get('color')) or (1, 1, 1)
        ld.energy = escala * POT.get(str(fu.get('intensidad') or 'media').lower(), 1.0); ld.shadow_soft_size = 0.3
        lo = bpy.data.objects.new(f'luz_esc{esc}_{k}', ld); lo.location = (px, py, pz); c.objects.link(lo)
        if fu.get('encendida') is False: lo.hide_render = True
    armado.append(f"luces escena {esc}: {len(l.get('fuentes') or [])} fuentes ({luces[esc][1]})")

# ---------- cámaras ----------
cams = []
for k, cs in enumerate(E.get('camaras_sugeridas') or []):
    esc = str(cs.get('escena') or ''); px, py, pz = xyz(cs.get('posicion'))
    if px is None or py is None: avisos.append(f"cámara {k + 1}: posición sin coordenadas («{str(cs.get('posicion'))[:60]}») → se omite"); continue
    pz = 1.5 if pz is None else pz
    tx, ty, tz = xyz(cs.get('mira_hacia'))
    if tx is None and ty is None: tx, ty = W / 2, Dm / 2; avisos.append(f"cámara {k + 1}: «mira hacia» sin coordenadas → al centro de la sala")
    tx = px if tx is None else tx; ty = py if ty is None else ty; tz = pz if tz is None else tz
    cd = bpy.data.cameras.new(f'cam{k + 1}'); cd.lens = num(re.sub(r'[^\d.]', '', str(cs.get('lente_mm') or '')) or None, 35.0); cd.sensor_width = 36
    cd.clip_start = 0.05; cd.clip_end = 1000
    co = bpy.data.objects.new(f'cam_{k + 1:02d}_esc{esc}', cd); co.location = (px, py, pz); C_CAM.objects.link(co)
    dv = Vector((tx, ty, tz)) - Vector((px, py, pz))
    if dv.length < 0.05: dv = Vector((0, 1, 0)); avisos.append(f"cámara {k + 1}: mira a su propia posición → mira hacia el fondo")
    co.rotation_euler = dv.to_track_quat('-Z', 'Y').to_euler()
    cams.append((co, esc, cs))
    armado.append(f"cámara {k + 1} (escena {esc}): ({px:g}, {py:g}, {pz:g}) → ({tx:g}, {ty:g}, {tz:g}), {cd.lens:g} mm")

# cámara cenital (planta)
cd = bpy.data.cameras.new('planta'); cd.type = 'ORTHO'; cd.ortho_scale = max(W, Dm) * 1.15 + 1; cd.clip_end = 1000
cp = bpy.data.objects.new('cam_planta', cd); cp.location = (W / 2, Dm / 2, H + 30); C_CAM.objects.link(cp)
# marcas de cámaras en la planta (flecha = triángulo hacia donde mira)
m_cam = mat('marca_cam', (1, .2, .2)); TM = max(W, Dm)
for co, esc, cs in cams:
    dv = co.matrix_world.to_quaternion() @ Vector((0, 0, -1)); ang = math.atan2(dv.y, dv.x); lf = TM / 10
    p0 = Vector((co.location.x, co.location.y, H + 0.4))
    primitiva(f'marca_{co.name}', 'cilindro', p0.x, p0.y, H + 0.4, TM / 70, TM / 70, 0.02, 0, m_cam, C_ETQ)
    fl = primitiva(f'flecha_{co.name}', 'caja', p0.x + math.cos(ang) * lf / 2, p0.y + math.sin(ang) * lf / 2, H + 0.4, lf, TM / 250, 0.02, math.degrees(ang), m_cam, C_ETQ)
    etiqueta(co.name.replace('cam_', 'C'), co.location.x, co.location.y - TM / 35, H + 0.45, TM / 55, color=(1, .3, .3))
etiqueta(f'{W:g} m (ancho, x)', W / 2, -GROSOR - max(W, Dm) / 25, H + 0.5, max(W, Dm) / 40, color=(.6, 1, .6))
t = etiqueta(f'{Dm:g} m (fondo, y)', -GROSOR - max(W, Dm) / 25, Dm / 2, H + 0.5, max(W, Dm) / 40, color=(.6, 1, .6)); t.rotation_euler[2] = math.pi / 2
etiqueta('FRENTE (y=0)', W / 2, max(W, Dm) / 30, H + 0.5, max(W, Dm) / 50, color=(.6, 1, .6))
# rejilla de 1 m (o 5 m si es grande) en el piso, solo para la planta
paso = 1 if max(W, Dm) <= 25 else 5
m_rej = mat('rejilla', (.15, .15, .15))
for gx in range(0, int(W // paso) + 1): caja(f'rej_x{gx}', gx * paso - 0.01 * paso, 0, H + 0.05, gx * paso + 0.01 * paso, Dm, H + 0.06, m_rej, C_ETQ)
for gy in range(0, int(Dm // paso) + 1): caja(f'rej_y{gy}', 0, gy * paso - 0.01 * paso, H + 0.05, W, gy * paso + 0.01 * paso, H + 0.06, m_rej, C_ETQ)

# ---------- render ----------
S = bpy.context.scene; S.render.image_settings.file_format = 'PNG'
S.render.threads_mode = 'FIXED'; S.render.threads = int(os.environ.get('MOLDE_HILOS', '3'))
mundo = S.world or bpy.data.worlds.new('mundo'); S.world = mundo; mundo.use_nodes = True
fondo = mundo.node_tree.nodes['Background']
def visibles(etq=False, techo=True, esc=None):
    for c in (C_ETQ,): c.hide_render = not etq
    C_TECHO.hide_render = not techo
    for e, (c, _, _) in luces.items(): c.hide_render = (e != esc)
    for ob, es in POR_ESC.items(): ob.hide_render = bool(esc) and esc not in es   # t353u: posición de otra escena → oculta
def workbench():
    S.render.engine = 'BLENDER_WORKBENCH'; sh = S.display.shading
    sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'; sh.show_shadows = True; sh.show_cavity = True; sh.cavity_type = 'BOTH'; sh.show_object_outline = True
    sh.background_type = 'VIEWPORT' if False else 'WORLD'
    fondo.inputs[0].default_value = (.05, .05, .06, 1); S.view_settings.view_transform = 'Standard'
renders, tiempos = [], {}
def render(nombre, cam, rx, ry):
    t = time.time(); S.camera = cam; S.render.resolution_x, S.render.resolution_y = rx, ry; S.render.resolution_percentage = 100
    S.render.filepath = os.path.join(OUT, nombre); bpy.ops.render.render(write_still=True)
    tiempos[nombre] = round(time.time() - t, 1); renders.append(nombre)

workbench(); visibles(etq=True, techo=False)
rx, ry = (1400, max(500, int(1400 * (Dm + 2) / (W + 2)))) if W >= Dm else (max(500, int(1400 * (W + 2) / (Dm + 2))), 1400)
render('planta.png', cp, rx, ry)
visibles(etq=False, techo=True)
def tapan(co):   # bloques que contienen la cámara: se ocultan solo en esa vista
    out = []
    for col_ in (C_EL, C_OBJ, C_AMB):
        for ob in col_.objects:
            if ob.type != 'MESH': continue
            bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
            if all(min(v[i] for v in bb) < co.location[i] < max(v[i] for v in bb) for i in range(3)): out.append(ob)
    return out
OCULTOS = {}
for co, esc, cs in cams:
    t_ = tapan(co); OCULTOS[co.name] = t_
    for ob in t_: ob.hide_render = True
    if t_: avisos.append(f"{co.name}: la cámara queda dentro de «{', '.join(o.name for o in t_)}» → se oculta en esa vista")
    for ob, es in POR_ESC.items():
        if esc and esc not in es: ob.hide_render = True   # t353u
    render(f'{co.name}.png', co, RES, int(RES * 9 / 16))
    for ob in t_: ob.hide_render = False
    for ob in POR_ESC: ob.hide_render = False

# Cycles: una vista por escena con sus luces (hora/color)
S.render.engine = 'CYCLES'; S.cycles.device = 'CPU'; S.cycles.samples = MUESTRAS; S.cycles.use_denoising = True
try: S.cycles.denoiser = 'OPENIMAGEDENOISE'
except Exception: pass
S.cycles.max_bounces = 3; S.render.use_persistent_data = True; S.cycles.use_adaptive_sampling = True; S.view_settings.view_transform = 'AgX' if 'AgX' in [i.identifier for i in S.view_settings.bl_rna.properties['view_transform'].enum_items] else 'Filmic'
AMB = {'noche': (.004, .006, .015), 'tarde': (.25, .16, .10), 'dia': (.55, .65, .85)}
sol = None
for esc, (c, hora, l) in luces.items():
    cam = next((co for co, e, _ in cams if e == esc), cams[0][0] if cams else None)
    if cam is None: break
    fondo.inputs[0].default_value = (*AMB[hora], 1); fondo.inputs[1].default_value = 1.0 if EXT or hora != 'noche' else 0.6
    if EXT and hora in ('dia', 'tarde'):
        if sol is None:
            sd = bpy.data.lights.new('sol', 'SUN'); sol = bpy.data.objects.new('sol', sd); S.collection.objects.link(sol); sol.rotation_euler = (math.radians(50), 0, math.radians(30))
        sol.data.energy = 3 if hora == 'dia' else 1.5; sol.data.color = (1, .95, .85) if hora == 'dia' else (1, .7, .45); sol.hide_render = False
    elif sol is not None: sol.hide_render = True
    visibles(etq=False, techo=True, esc=esc)
    for ob in OCULTOS.get(cam.name, []): ob.hide_render = True
    render(f'luz_esc{esc}.png', cam, int(RES * 5 / 6), int(RES * 5 / 6 * 9 / 16))
for _l in OCULTOS.values():
    for ob in _l: ob.hide_render = False
visibles(etq=True, techo=True, esc=None)
for c, _, _ in luces.values(): c.hide_render = False
S.render.engine = 'BLENDER_WORKBENCH'; S.camera = cams[0][0] if cams else cp
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'molde.blend'), compress=True)
res = {'ok': True, 'escenario_id': E.get('id'), 'medidas_m': [W, Dm, H], 'exterior': EXT, 'abierto': ABIERTO, 'fondo_lejano_no_modelado': FONDO_LEJANO, 'renders': renders, 'tiempos_s': tiempos,
       'camaras': len(cams), 'escenas_con_luz': list(luces), 'ambiente': amb_n, 'armado': armado, 'avisos': avisos, 'segundos': round(time.time() - T0, 1),
       'blender': bpy.app.version_string, 'objetos_por_escena': objetos_por_escena}
json.dump(res, open(os.path.join(OUT, 'molde.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('MOLDE_OK ' + json.dumps({k: res[k] for k in ('escenario_id', 'renders', 'segundos')}, ensure_ascii=False))
