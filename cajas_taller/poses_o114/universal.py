# o110 HIPOTESIS (t291u, t292u): poses universales por TIPO DE CUERPO. Lee el esqueleto (jerarquia + geometria, NUNCA nombres),
# lo clasifica y da a cada hueso un ROL. Las poses se escriben por rol en el marco del cuerpo (F adelante, L izquierda, U arriba).
# Tipo o pose que no esta en POSES -> Falta (nunca se inventa).
import bpy, math
from mathutils import Vector, Quaternion, Matrix
class Falta(Exception): pass
def _ext(B):
    P = [p for b in B for p in (b.head_local, b.tail_local)]
    ex = [max(p[k] for p in P) - min(p[k] for p in P) for k in range(3)]
    return ex[2], math.hypot(ex[0], ex[1]), min(p.z for p in P), max(p.z for p in P)
def fin_rest(B, h, sig=None):
    b = B[h]
    if sig and h in sig: return B[sig[h]].head_local
    if len(b.children) == 1 and (b.children[0].head_local - b.head_local).length > 1e-6: return b.children[0].head_local
    return b.tail_local
def largo_ef(B, h): return (fin_rest(B, h) - B[h].head_local).length
def _segmentos(arm):
    B = arm.data.bones; H, Hh, z0, ztop = _ext(B); esc = max(H, Hh)
    hijos = {b.name: [c.name for c in b.children] for b in B}
    def cadena(n):
        c = [n]
        while len(hijos[c[-1]]) == 1: c.append(hijos[c[-1]][0])
        return c
    segs = []; pila = [(b.name, None) for b in B if b.parent is None]
    while pila:
        n, padre = pila.pop(); c = cadena(n); segs.append({'huesos': c, 'padre': padre, 'largo': sum(largo_ef(B, x) for x in c)})
        for h in hijos[c[-1]]: pila.append((h, len(segs) - 1))
    vivo = [True] * len(segs)
    while True:   # podar ramitas cortas (dedos, ojos, pelo), nunca la punta mas alta
        cambio = False
        for i, s in enumerate(segs):
            if not vivo[i] or s['padre'] is None: continue
            if any(vivo[j] and segs[j]['padre'] == i for j in range(len(segs))): continue
            alto = max(fin_rest(B, x).z for x in s['huesos']) >= ztop - 0.02 * H
            if not alto and s['largo'] < 0.12 * esc: vivo[i] = False; cambio = True
        if not cambio: break
    return [s if vivo[i] else None for i, s in enumerate(segs)]
def clasificar(arm):
    B = arm.data.bones; segs = _segmentos(arm); H, Hh, z0, ztop = _ext(B); esc = max(H, Hh)
    vivos = [i for i, s in enumerate(segs) if s]
    hojas = [i for i in vivos if not any(segs[j] and segs[j]['padre'] == i for j in vivos)]
    punta = lambda i: fin_rest(B, segs[i]['huesos'][-1])
    bajo = lambda i: min(punta(i).z, B[segs[i]['huesos'][-1]].head_local.z)
    def camino_a(i):
        c = []
        while i is not None: c.append(i); i = segs[i]['padre']
        return c[::-1]
    largo_c = lambda c: sum(segs[k]['largo'] for k in c)
    larga = camino_a(max(hojas, key=lambda i: largo_c(camino_a(i))))
    P = [p for k in larga for h in segs[k]['huesos'] for p in (B[h].head_local, fin_rest(B, h))]
    vz = max(p.z for p in P) - min(p.z for p in P); vh = math.hypot(max(p.x for p in P) - min(p.x for p in P), max(p.y for p in P) - min(p.y for p in P))
    plano = vz < 0.2 * vh   # la cadena mas larga va acostada (serpiente, pez): la columna no se busca por altura
    if plano: fin = max(hojas, key=lambda i: largo_c(camino_a(i)))   # la cadena mas larga desde la raiz
    else: fin = max(hojas, key=lambda i: punta(i).z)                 # la punta mas alta = cabeza
    camino = camino_a(fin)
    ramas = [i for i in hojas if i not in camino]
    def huesos_rama(i):
        out = []
        while i not in camino: out = segs[i]['huesos'] + out; i = segs[i]['padre']
        return out
    todo = [h for k in camino for h in segs[k]['huesos']]
    # huesos raiz "de suelo" (control/colocacion en el origen, al nivel del piso) no son cuerpo
    suelo = []
    while len(todo) > 2 and B[todo[0]].head_local.z - z0 < 0.08 * H and not plano: suelo.append(todo.pop(0))
    camino_huesos = set(todo)
    if plano:   # cabeza = extremo de la raiz (primer hueso), columna = el resto; los huesos apuntan hacia la cola
        cabeza, columna = todo[:1], todo[1:]; cab = B[todo[0]].head_local; atras = B[todo[-1]].tail_local
    else:
        columna = [h for k in camino[:-1] for h in segs[k]['huesos'] if h in camino_huesos]; cabeza = segs[camino[-1]]['huesos']
        if not columna: columna, cabeza = cabeza[:-1], cabeza[-1:]
        cab = fin_rest(B, cabeza[-1])
    cad = sum(((B[h].head_local + B[h].tail_local) / 2 for h in columna or cabeza), Vector()) / len(columna or cabeza)
    patas, sup, cola = [], [], []
    w0 = cab - cad; w0.z = 0; Lw = Vector((0, 0, 1)).cross(w0.normalized()) if w0.length > 0.25 * max(H, 1e-6) else None
    linea_media = lambda hs, p: Lw is not None and abs((p - cad).dot(Lw)) < 0.05 * H and abs((B[hs[0]].head_local - cad).dot(Lw)) < 0.05 * H
    for i in ramas:
        hs = huesos_rama(i); p = punta(i)
        if not plano and bajo(i) - z0 < 0.12 * H and linea_media(hs, p): cola.append(hs)   # cola colgando hasta el piso: no es pata
        elif not plano and bajo(i) - z0 < 0.12 * H: patas.append(hs)
        else:
            v = p - cad; w = cab - cad; v.z = w.z = 0
            if not plano and w.length > 0.2 * H and v.length > 0.2 * H and v.normalized().dot(w.normalized()) < -0.5: cola.append(hs)
            else: sup.append(hs)
    n = len(patas)
    if plano: w = cab - atras
    else: w = cab - cad
    w.z = 0
    if w.length > 0.25 * (Hh if plano else H): F = w.normalized()
    else:
        F = Vector()
        for hs in patas: d = fin_rest(B, hs[-1]) - B[hs[-1]].head_local; d.z = 0; F += d
        if F.length < 1e-4: raise Falta('no se puede saber hacia donde mira el cuerpo (FALTA)')
        F.normalize()
    U = Vector((0, 0, 1)); L = U.cross(F)
    for hs in list(cola):   # una cola va por la linea media; si sale hacia un lado es ala/brazo plegado
        a = (B[hs[0]].head_local - cad).dot(L)   # nace fuera de la linea media -> es un par (ala/brazo plegado), no cola
        if abs(a) > 0.05 * max(H, 1e-6): cola.remove(hs); sup.append(hs)
    horizontal = (lambda d: abs(d.dot(F)) > abs(d.z))(fin_rest(B, columna[-1]) - B[columna[0]].head_local) if columna else False
    if n == 0: tipo = 'sin_patas_con_aletas' if sup else 'sin_patas'   # pez vs serpiente
    elif n == 2: tipo = 'bipedo_horizontal' if horizontal else 'bipedo'   # ave / dinosaurio vs humano
    elif n == 4: tipo = 'cuadrupedo'
    elif n >= 6 and n % 2 == 0: tipo = 'multipata'
    else: raise Falta(f'cuerpo con {n} patas: tipo que no esta en la biblioteca (FALTA)')
    lado = lambda hs: 'izq' if (B[hs[0]].head_local - cad).dot(L) > 0 else 'der'
    adelante = lambda hs: (B[hs[0]].head_local - cad).dot(F)
    largo = lambda hs: sum(largo_ef(B, h) for h in hs)
    R = {'tipo': tipo, 'altura': H, 'escala': esc, 'F': F, 'L': L, 'U': U, 'centro': cad, 'columna': columna, 'cabeza': cabeza, 'cola': cola,
         'extra': ['con_cola'] if cola else [], 'plano': plano, 'suelo': suelo}
    if n == 4:
        ps = sorted(patas, key=adelante)
        for grupo, nom in ((ps[2:], 'pata_delantera'), (ps[:2], 'pata_trasera')):
            for hs in grupo: R[f'{nom}_{lado(hs)}'] = hs
    elif n >= 6:
        for k, hs in enumerate(sorted(patas, key=adelante)): R[f'pata_{k + 1}'] = hs
    else:
        for hs in patas: R[f'pierna_{lado(hs)}'] = hs
    if tipo.startswith('sin_patas'):
        for k, hs in enumerate(sup): R[f'aleta_{k + 1}'] = hs
    else:
        for hs in sorted(sup, key=largo): R[f'brazo_{lado(hs)}'] = hs   # por lado gana la rama superior mas larga (brazo/ala)
    sig = {}
    cadenas = [columna + cabeza] + [v for k, v in R.items() if isinstance(v, list) and k not in ('columna', 'cabeza', 'cola', 'extra', 'suelo')] + cola
    for c in cadenas:
        for a, b in zip(c, c[1:]):
            if B[b].parent and B[b].parent.name == a: sig[a] = b
    R['sig'] = sig
    return R
# Direcciones: (f, l, u) en el marco del cuerpo, o ('radial', h, u) = hacia afuera del centro (h) + arriba (u), o ('espiral', vueltas)
POSES = {
 'bipedo': {
  'de_pie': {'columna': (0, 0, 1), 'cabeza': (0, 0, 1), 'pierna_*': (0, 0, -1), 'brazo_*': (0, 0, -1)},
  'acostado_boca_arriba': {'base': 'de_pie', 'cuerpo': ('L', -90)},
  'acostado_boca_abajo': {'base': 'de_pie', 'cuerpo': ('L', 90)}},
 'bipedo_horizontal': {
  'de_pie': {'columna': (1, 0, 0.15), 'cabeza': (0.3, 0, 1), 'pierna_*': (0, 0, -1), 'brazo_*': (-1, 0, -0.1), 'cola': (-1, 0, 0)},
  'alas_abiertas': {'base': 'de_pie', 'brazo_*': ('lateral', 1, 0.15)},
  'acostado_boca_arriba': {'base': 'de_pie', 'cuerpo': ('F', 180), 'cabeza': (1, 0, 0.05)},
  'acostado_boca_abajo': {'base': 'de_pie', 'pierna_*': (-1, 0, -0.1), 'cabeza': (1, 0, 0.3)}},
 'cuadrupedo': {
  'de_pie': {'columna': (1, 0, 0), 'cabeza': (0.45, 0, 1), 'pata_*': (0, 0, -1), 'cola': (-0.6, 0, -1)},
  'acostado_boca_arriba': {'base': 'de_pie', 'cuerpo': ('F', 180), 'cabeza': (1, 0, 0.05), 'cola': (-1, 0, 0.05)},
  'acostado_boca_abajo': {'columna': (1, 0, 0), 'cabeza': (0.6, 0, 1), 'pata_delantera_*': (1, 0, -0.08), 'pata_trasera_*': (-1, 0, -0.08), 'cola': (-1, 0, -0.2)}},
 'multipata': {
  'de_pie': {'columna': (1, 0, 0), 'cabeza': (1, 0, 0.2), 'pata_*': ('radial', 0.75, -0.65)},
  'acostado_boca_arriba': {'base': 'de_pie', 'cuerpo': ('F', 180), 'pata_*': ('radial', 0.35, -0.95)},
  'acostado_boca_abajo': {'base': 'de_pie', 'pata_*': ('radial', 1, -0.12)}},
 'sin_patas': {   # los huesos de la columna apuntan hacia la cola (-F)
  'de_pie': {'columna': (-1, 0, 0), 'cabeza': (-1, 0, -0.15)},
  'acostado_boca_arriba': {'base': 'de_pie', 'cuerpo': ('F', 180)},
  'acostado_boca_abajo': {'base': 'de_pie'},   # en un cuerpo sin patas "boca abajo" = vientre al piso = reposo
  'enrollado': {'base': 'de_pie', 'columna': ('espiral', 1.6)}},
 'sin_patas_con_aletas': {
  'de_pie': {'columna': (-1, 0, 0), 'cabeza': (-1, 0, 0)},
  'acostado_boca_arriba': {'base': 'de_pie', 'cuerpo': ('F', 180), 'aleta_*': (-1, 0, 0)},   # aletas plegadas hacia atras
  'acostado_boca_abajo': {'base': 'de_pie'}}}
def _rol_dir(pose, rol):
    if rol in pose: return pose[rol]
    for k, v in pose.items():
        if k.endswith('*') and rol.startswith(k[:-1]): return v
    return None
def poses_de(R): return sorted(POSES.get(R['tipo'], {}))
def aplicar(arm, R, nombre):
    if R['tipo'] not in POSES: raise Falta(f'tipo {R["tipo"]}: sin poses (FALTA)')
    if nombre not in POSES[R['tipo']]: raise Falta(f'pose «{nombre}» no existe para {R["tipo"]} (FALTA, no se inventa)')
    p = POSES[R['tipo']][nombre]; dirs = dict(POSES[R['tipo']][p['base']]) if 'base' in p else {}
    dirs.update({k: v for k, v in p.items() if k not in ('base', 'cuerpo')})
    arm.rotation_mode = 'QUATERNION'; arm.rotation_quaternion = (1, 0, 0, 0); arm.location = (0, 0, 0)
    import aplicar_pose as _AP; BASE = _AP.preparar(arm)   # o114: escala propia fija, herencia alineada
    for pb in arm.pose.bones: pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = BASE[pb.name]
    bpy.context.view_layer.update()
    B = arm.data.bones; F, L, U = R['F'], R['L'], R['U']
    trabajo = []
    sig = R.get('sig', {})
    for rol in ['columna', 'cabeza'] + [k for k in R if isinstance(R[k], list) and k not in ('columna', 'cabeza', 'cola', 'extra', 'suelo')] + ['cola']:
        grupos = R[rol] if rol == 'cola' else [R[rol]]
        f = _rol_dir(dirs, rol)
        if f is None: continue
        for hs in grupos:
            for k, h in enumerate(hs):
                if rol not in ('columna', 'cabeza') and len(hs) >= 3 and k == len(hs) - 1 and h not in sig: continue
                if f[0] == 'radial':
                    r = fin_rest(B, hs[-1], sig) - B[hs[0]].head_local; r.z = 0; r = r.normalized() if r.length > 1e-4 else L
                    d = r * f[1] + U * f[2]
                elif f[0] == 'lateral':
                    sg = 1 if (B[hs[0]].head_local - R['centro']).dot(L) > 0 else -1; d = L * sg * f[1] + U * f[2]
                elif f[0] == 'espiral':
                    a = 2 * math.pi * f[1] * (k + 0.5) / len(hs); d = Quaternion(U, a) @ (-F)
                else: d = F * f[0] + L * f[1] + U * f[2]
                trabajo.append((h, d.normalized()))
    depth = lambda h: len(B[h].parent_recursive)
    for h, d in sorted(trabajo, key=lambda t: depth(t[0])):   # padres primero
        pb = arm.pose.bones[h]; bpy.context.view_layer.update()
        n = sig.get(h) or (pb.children[0].name if len(pb.children) == 1 else None)
        eje = (arm.pose.bones[n].head - pb.head) if n and (arm.pose.bones[n].head - pb.head).length > 1e-6 else (pb.tail - pb.head)
        q = eje.normalized().rotation_difference(d); c = pb.head.copy()
        pb.matrix = Matrix.Translation(c) @ q.to_matrix().to_4x4() @ Matrix.Translation(-c) @ pb.matrix; pb.scale = BASE[pb.name]
    if 'cuerpo' in p:
        eje, ang = p['cuerpo']; arm.rotation_quaternion = Quaternion(R[eje], math.radians(ang))
    bpy.context.view_layer.update()
def marco_mundo(arm, R, v): return (arm.matrix_world.to_3x3() @ v).normalized()
