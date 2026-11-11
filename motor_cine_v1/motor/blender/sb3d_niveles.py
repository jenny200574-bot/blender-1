"""sb3d_niveles (Blender 5.2.3, código propio MYIA) [t1066u, 10-nov-2026] — paso «storyboard después del 3D».
UNIVERSAL: no hay nombres de canal, capítulo, escena, personaje ni objeto. Todo sale de la escena 3D armada y del guion/SB.
  - entidades(): agrupa las mallas en entidades (personaje = armature con mallas; prop = malla con 'prop_motor' hija de un
    hueso; objeto del set = nombre base antes de '__' / '#' / '.NNN').
  - medir_personaje(): posición real, caja, altura, ojos, pecho y frente por cuadro (malla deformada evaluada).
  - interior(): caja interior del recinto (caras internas de muros, piso, techo) medida.
  - grafo_soporte(): quién pisa / se apoya / está en contacto con qué (rayos hacia abajo + solape de cajas) y quién sostiene qué prop.
  - clasificar(): N0 historia (nunca se oculta) · N1 obstáculo de historia (se mueve la cámara) · N2 cerramiento perimetral
    (solo se recorta si la cámara está FUERA del recinto de ese lado) · N3 adorno que nadie toca ni nombra (único ocultable)."""
import bpy, re, math, json, unicodedata
from mathutils import Vector
import numpy as np

CABEZA = ('cabeza', 'face', 'head', 'hair', 'helmet', 'casco', 'eye', 'nose', 'mouth', 'brow', 'iris', 'pupil', 'pelo', 'ojo', 'boca')
CAMINABLE = ('piso', 'suelo', 'floor', 'tapete', 'alfombra', 'rug', 'carpet', 'cesped', 'pasto', 'grass', 'terreno', 'ground')
PARED = ('pared', 'muro', 'wall', 'zocalo', 'rodapie')
TECHO = ('techo', 'ceiling', 'cielo_raso', 'plafon')
STOP = {'obj', 'amb', 'esc', 'prop', 'con', 'del', 'las', 'los', 'una', 'uno', 'para', 'por', 'que', 'the', 'and', 'junto', 'sobre', 'bajo'}

def _sin_tildes(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')

def base_nombre(n):
    n = re.sub(r'\.\d{3}$', '', n)
    return re.split(r'__|#', n)[0]

def es_cabeza(nombre):
    n = nombre.lower(); return any(k in n for k in CABEZA)

def personajes():
    """armatures con mallas hijas (sin copias temporales)."""
    return [o for o in bpy.data.objects if o.type == 'ARMATURE' and not o.name.startswith(('TMP_', 'SRC_'))
            and any(c.type == 'MESH' for c in o.children_recursive)]

def _raiz_armature(o):
    p = o.parent
    while p is not None:
        if p.type == 'ARMATURE': return p
        p = p.parent
    return None

def entidades():
    """{id: {"tipo": personaje|prop|set, "mallas": [nombres], "portador": id|None}}"""
    pj = {a.name for a in personajes()}
    ent = {a: {"tipo": "personaje", "mallas": [], "portador": None} for a in pj}
    for o in bpy.data.objects:
        if o.type != 'MESH': continue
        arm = _raiz_armature(o)
        if o.get('prop_motor'):
            emp = o.parent
            eid = emp.name[5:] if emp is not None and emp.name.startswith('PROP_') else base_nombre(o.name).split('.')[0]
            e = ent.setdefault(eid, {"tipo": "prop", "mallas": [], "portador": arm.name if arm is not None and arm.name in pj else None})
            e['mallas'].append(o.name)
        elif arm is not None and arm.name in pj:
            ent[arm.name]['mallas'].append(o.name)
        else:
            ent.setdefault(base_nombre(o.name), {"tipo": "set", "mallas": [], "portador": None})['mallas'].append(o.name)
    return ent

def bbox_objs(names):
    lo = [1e9] * 3; hi = [-1e9] * 3
    for n in names:
        o = bpy.data.objects.get(n)
        if o is None: continue
        for c in o.bound_box:
            p = o.matrix_world @ Vector(c)
            for i in range(3): lo[i] = min(lo[i], p[i]); hi[i] = max(hi[i], p[i])
    return lo, hi

def verts_mundo(o, dg, max_n=None):
    oe = o.evaluated_get(dg); me = oe.to_mesh()
    try:
        n = len(me.vertices)
        if n == 0: return np.zeros((0, 3))
        co = np.empty(n * 3, dtype=np.float64); me.vertices.foreach_get('co', co); co = co.reshape(n, 3)
        if max_n and n > max_n: co = co[np.linspace(0, n - 1, max_n).astype(int)]
        M = np.array(oe.matrix_world)
        return co @ M[:3, :3].T + M[:3, 3]
    finally:
        oe.to_mesh_clear()

def frente(arm):
    """dirección horizontal hacia donde mira el personaje en el cuadro actual (cadera: cruz de fémures; si no, -Y del armature)."""
    pb = arm.pose.bones
    if 'femur_L' in pb and 'femur_R' in pb:
        mw = arm.matrix_world; v = (mw @ pb['femur_R'].head) - (mw @ pb['femur_L'].head)
        f = Vector((0, 0, 1)).cross(v); f.z = 0
        if f.length > 1e-6: return f.normalized()
    f = arm.matrix_world.to_3x3() @ Vector((0, -1, 0)); f.z = 0
    return f.normalized() if f.length > 1e-6 else Vector((0, -1, 0))

def medir_personaje(arm, dg, ent, n_cab=40, n_cuerpo=40):
    """muestras de la malla deformada + caja + cabeza/ojos/pecho/frente en el cuadro actual."""
    mallas = [bpy.data.objects[n] for n in ent['mallas'] if n in bpy.data.objects]
    pb = arm.pose.bones; mw = arm.matrix_world
    zc = (mw @ pb['cabeza'].head).z if 'cabeza' in pb else None
    cab, cue, allp = [], [], []
    for o in mallas:
        if o.hide_render: continue
        P = verts_mundo(o, dg, 400)
        if not len(P): continue
        allp.append(P)
        if es_cabeza(o.name): cab.append(P)
        elif zc is not None:
            m = P[:, 2] >= zc; cab.append(P[m]); cue.append(P[~m])
        else: cue.append(P)
    if not allp: return None
    A = np.vstack(allp); lo = A.min(0); hi = A.max(0)
    C = np.vstack(cab) if cab and sum(len(x) for x in cab) else A[A[:, 2] >= lo[2] + 0.8 * (hi[2] - lo[2])]
    B = np.vstack(cue) if cue and sum(len(x) for x in cue) else A
    def ralear(X, m): return X if len(X) <= m else X[np.linspace(0, len(X) - 1, m).astype(int)]
    C = ralear(C, n_cab); B = ralear(B, n_cuerpo)
    hc = Vector(C.mean(0)) if len(C) else Vector(((lo + hi) / 2))
    if 'cabeza' in pb: hc = (mw @ pb['cabeza'].head).lerp(mw @ pb['cabeza'].tail, 0.5)
    ojos = [bpy.data.objects[n] for n in ent['mallas'] if n in bpy.data.objects and re.search(r'(^|[_.])(ojo|eye)s?(_[LR])?$', n.split('.', 1)[-1], re.I)]
    po = Vector(np.vstack([verts_mundo(o, dg, 50) for o in ojos]).mean(0)) if ojos else hc.copy()
    pecho = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2] + 0.62 * (hi[2] - lo[2])))
    if 'cadera' in pb: pecho = (mw @ pb['cadera'].head).lerp(hc, 0.55)
    return {"cab": [Vector(p) for p in C], "cue": [Vector(p) for p in B], "lo": Vector(lo), "hi": Vector(hi),
            "altura": float(hi[2] - lo[2]), "cabeza": hc, "ojos": po, "pecho": pecho, "frente": frente(arm),
            "acostado": bool((hi[2] - lo[2]) < 0.6 * max(hi[0] - lo[0], hi[1] - lo[1]))}

def clase_estructura(eid, lo, hi):
    n = _sin_tildes(eid); alto = hi[2] - lo[2]; ax = hi[0] - lo[0]; ay = hi[1] - lo[1]
    if any(k in n for k in TECHO) or (lo[2] > 2.2 and alto < 0.4 and ax * ay > 4): return 'techo'
    if any(k in n for k in CAMINABLE) and hi[2] < 0.12: return 'caminable'
    if hi[2] < 0.035 and ax * ay > 0.2: return 'caminable'
    if any(k in n for k in PARED) or (alto > 1.6 and min(ax, ay) < 0.35 and max(ax, ay) > 1.0): return 'pared'
    return None

def interior(ents, cajas):
    """caja interior del recinto medida: caras internas de los muros, tope del piso, cara baja del techo."""
    pisos = [e for e, c in cajas.items() if c['clase'] == 'caminable']
    muros = [e for e, c in cajas.items() if c['clase'] == 'pared']
    techos = [e for e, c in cajas.items() if c['clase'] == 'techo']
    if pisos:
        lo = [min(cajas[e]['lo'][i] for e in pisos) for i in range(2)]; hi = [max(cajas[e]['hi'][i] for e in pisos) for i in range(2)]
        z0 = max(cajas[e]['hi'][2] for e in pisos if cajas[e]['hi'][2] < 0.12) if any(cajas[e]['hi'][2] < 0.12 for e in pisos) else 0.0
    else:
        lo = [-1e3, -1e3]; hi = [1e3, 1e3]; z0 = 0.0
    cen = [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2]
    bajos = {0: [], 1: []}; altos = {0: [], 1: []}; lados = {}
    for e in muros:
        l, h = cajas[e]['lo'], cajas[e]['hi']; ext = [h[0] - l[0], h[1] - l[1]]
        a = 0 if ext[0] < ext[1] else 1
        if ext[a] > 0.4: continue
        if (l[a] + h[a]) / 2 < cen[a]: bajos[a].append(h[a]); lados[e] = (a, -1)
        else: altos[a].append(l[a]); lados[e] = (a, +1)
    ilo = [max(bajos[a]) if bajos[a] else lo[a] for a in (0, 1)]
    ihi = [min(altos[a]) if altos[a] else hi[a] for a in (0, 1)]
    z1 = min(cajas[e]['lo'][2] for e in techos) if techos else z0 + 6.0
    return {"lo": [ilo[0], ilo[1], z0], "hi": [ihi[0], ihi[1], z1], "muros_lado": lados, "tiene_techo": bool(techos)}

def perimetral(lo, hi, I, tol=0.16):
    """pieza pegada a un muro (zócalo, puerta, ventana, cuadro de pared) o fuera del recinto: va con el cerramiento."""
    for a in (0, 1):
        ext = hi[a] - lo[a]
        if ext < 0.22 and (abs(lo[a] - I['lo'][a]) < tol or abs(hi[a] - I['hi'][a]) < tol): return True
    if hi[0] < I['lo'][0] - 0.02 or lo[0] > I['hi'][0] + 0.02 or hi[1] < I['lo'][1] - 0.02 or lo[1] > I['hi'][1] + 0.02: return True
    if lo[2] > I['hi'][2] - 0.02: return True
    return False

def lado_fuera(C, I, margen=0.0):
    """lados del recinto por los que la cámara C está FUERA: lista de (eje, signo)."""
    out = []
    for a in (0, 1):
        if C[a] < I['lo'][a] - margen: out.append((a, -1))
        elif C[a] > I['hi'][a] + margen: out.append((a, +1))
    if C[2] > I['hi'][2] + margen: out.append((2, +1))
    return out

def textos_historia(E, SB):
    """todo el texto de historia (guion 01 + SB) en minúsculas sin tildes, y los ids nombrados explícitamente."""
    txt = []; ids = set()
    for a in (E or {}).get('acciones_01', []):
        txt += [str(a.get(k) or '') for k in ('cita', 'accion', 'mirada', 'objeto')]
        for k in ('objeto', 'mirada_id', 'actor'):
            if a.get(k): ids.add(a[k])
    for h in (E or {}).get('hechos', []): txt.append(str(h.get('hecho') or ''))
    for v in (SB or {}).get('vinetas', []):
        di = v.get('director_imagen', {})
        txt += [str(v.get('intencion_narrativa') or ''), ' '.join(map(str, v.get('beats_visuales') or [])), str(di.get('composicion') or '')]
        for x in di.get('objetos', []):
            txt.append(str(x.get('nombre') or '') + ' ' + str(x.get('estado') or ''))
            if x.get('nombre'): ids.add(x['nombre'])
        for x in di.get('en_cuadro', []):
            if x.get('id'): ids.add(x['id'])
        for x in v.get('debe_verse', []) or []: ids.add(x)
        for au in v.get('audio', []) or []: txt.append(str(au.get('texto') or ''))
    return _sin_tildes(' '.join(txt)), ids

def _tokens(eid, excluir):
    t = [x for x in re.split(r'[^a-z0-9]+', _sin_tildes(eid)) if len(x) >= 3 and x not in STOP and x not in excluir and not x.isdigit()]
    return t

def grafo_soporte(ents, cajas, frames, sc, med_cache):
    """aristas: (a, rel, b, cuadros). rel: soportado_por | contacto | sostenido_por."""
    aris = {}
    pj = [e for e, v in ents.items() if v['tipo'] == 'personaje']
    setents = {e for e, v in ents.items() if v['tipo'] == 'set'}
    obj_ent = {n: e for e, v in ents.items() for n in v['mallas']}
    for e, v in ents.items():
        if v['tipo'] == 'prop' and v['portador']: aris[(e, 'sostenido_por', v['portador'])] = None
    for f in frames:
        sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
        for p in pj:
            M = med_cache(p, f)
            if M is None: continue
            lo, hi = M['lo'], M['hi']
            # soporte: rayos hacia abajo desde 5 puntos bajos del cuerpo
            zb = lo.z + 0.25 * (hi.z - lo.z)
            for x, y in ((0.5, 0.5), (0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)):
                O0 = Vector((lo.x + x * (hi.x - lo.x), lo.y + y * (hi.y - lo.y), zb)); O = O0.copy(); d = Vector((0, 0, -1))
                for _ in range(12):
                    hit, loc, nor, idx, ob, mx = sc.ray_cast(dg, O, d, distance=max(0.01, 3.0 - (O - O0).length))
                    if not hit: break
                    eo = obj_ent.get(ob.name)
                    if eo == p or eo is None or ents.get(eo, {}).get('portador') == p:
                        O = loc + d * 1e-4; continue
                    aris.setdefault((p, 'soportado_por', eo), set()).add(f); break
            # contacto: solape de cajas (personaje acostado/sentado/apoyado o metido bajo un mueble)
            for e in setents:
                c = cajas[e]
                if c['clase'] in ('pared', 'techo'): continue
                l2, h2 = c['lo'], c['hi']; m = 0.03
                if all(lo[i] <= h2[i] + m and hi[i] >= l2[i] - m for i in range(3)):
                    ov = [max(0.0, min(hi[i], h2[i]) - max(lo[i], l2[i])) for i in range(3)]
                    if c['clase'] == 'caminable' or (ov[0] * ov[1] > 0.0005 and ov[2] > 0.01):
                        aris.setdefault((p, 'contacto', e), set()).add(f)
    return [{"a": a, "rel": r, "b": b, "cuadros": sorted(fs)[:6] if fs else None} for (a, r, b), fs in aris.items()]

def clasificar(E, SB, frames, sc, med_cache, ents=None):
    """devuelve (niveles {eid: {...}}, interior, grafo)."""
    ents = ents or entidades()
    cajas = {}
    for e, v in ents.items():
        lo, hi = bbox_objs(v['mallas'])
        cajas[e] = {"lo": lo, "hi": hi, "clase": (clase_estructura(e, lo, hi) if v['tipo'] == 'set' else None)}
    I = interior(ents, cajas)
    grafo = grafo_soporte(ents, cajas, frames, sc, med_cache)
    texto, ids_sb = textos_historia(E, SB)
    esc_tok = set(_tokens((E or {}).get('escenario', {}).get('id', ''), set()))
    # tokens comunes a más de la mitad de las piezas del set (prefijos de fábrica) no cuentan como mención
    from collections import Counter
    cnt = Counter(t for e, v in ents.items() if v['tipo'] == 'set' for t in set(_tokens(e, set())))
    nset = max(1, sum(1 for v in ents.values() if v['tipo'] == 'set'))
    comunes = {t for t, k in cnt.items() if k > 0.5 * nset} | esc_tok
    def nombrado(e):
        for i in ids_sb:
            b = base_nombre(str(i))
            if b and (e == b or e.startswith(b + '_') or b.startswith(e + '_') or e == re.sub(r'__.*$', '', str(i))): return f"nombrado en SB/guion ({i})"
        tk = _tokens(e, comunes)
        if tk and all(re.search(r'\b' + re.escape(t), texto) for t in tk): return "mencionado en el guion (" + ' '.join(tk) + ")"
        return None
    niv = {}
    for e, v in ents.items():
        c = cajas[e]; mot = []
        if v['tipo'] == 'personaje': lvl = 'N0'; mot.append('personaje en escena')
        elif v['tipo'] == 'prop': lvl = 'N0'; mot.append(f"prop sostenido por {v['portador']}")
        elif c['clase'] == 'caminable': lvl = 'N0'; mot.append('piso / superficie que se pisa')
        else:
            lvl = None
            sop = [g for g in grafo if g['b'] == e and g['rel'] in ('soportado_por', 'contacto')]
            if sop: lvl = 'N0'; mot.append('soporta o toca a ' + ','.join(sorted({g['a'] for g in sop})))
            nm = nombrado(e)
            if nm: lvl = 'N0'; mot.append(nm)
            if lvl is None and c['clase'] in ('pared', 'techo'): lvl = 'N2'; mot.append(c['clase'])
            if lvl is None and perimetral(c['lo'], c['hi'], I): lvl = 'N2'; mot.append('pegado al cerramiento / fuera del recinto')
            if lvl is None: lvl = 'N3'; mot.append('adorno: nadie lo toca ni lo nombra')
        niv[e] = {"nivel": lvl, "motivo": mot, "tipo": v['tipo'], "clase": c['clase'], "mallas": v['mallas'], "portador": v['portador'],
                  "lo": [round(x, 3) for x in c['lo']], "hi": [round(x, 3) for x in c['hi']]}
    # lo que descansa sobre un soporte N0 y cae casi entero en su huella (sábanas, almohadas, cojines, libro sobre la cama) va con él
    soportes0 = [e for e, d in niv.items() if d['nivel'] == 'N0' and d['tipo'] == 'set' and d['clase'] is None]
    for e, d in niv.items():
        if d['nivel'] != 'N3': continue
        lo, hi = d['lo'], d['hi']; a = max(1e-6, (hi[0] - lo[0]) * (hi[1] - lo[1]))
        for s in soportes0:
            l2, h2 = niv[s]['lo'], niv[s]['hi']
            ov = max(0, min(hi[0], h2[0]) - max(lo[0], l2[0])) * max(0, min(hi[1], h2[1]) - max(lo[1], l2[1]))
            if ov / a >= 0.5 and l2[2] - 0.02 <= lo[2] <= h2[2] + 0.05:
                d['nivel'] = 'N0'; d['motivo'] = [f'descansa sobre {s} (soporte de historia)']; break
    return niv, I, grafo

def mallas_de_nivel(niv, nivel):
    return [m for d in niv.values() if d['nivel'] == nivel for m in d['mallas']]
