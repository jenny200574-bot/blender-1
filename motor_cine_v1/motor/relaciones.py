"""relaciones — [argon_v2, 10-nov-2026, Ricardo t535u/t536u/t538u] relaciones físicas GENÉRICAS entre un personaje y otro
personaje u objeto, para que el motor las EJECUTE (anclar al hueso / apoyar en la superficie) en vez de chocar.
Sin nombres de canal, escenario ni personaje en el código: los nombres se sacan de los ids/bib de la propia escena.
Tipos (contrato relacion_v1):
  sobre_hombro_de  -> el sujeto va anclado (parent BONE) al hombro del destino; lado L/R si el texto lo dice
  sostenido_por    -> anclado a la mano/brazo del destino
  sobre_cabeza_de  -> anclado a la cabeza del destino
  sentado_en       -> el sujeto se apoya en la superficie superior del objeto/mueble destino (no choca con él)
  acostado_en      -> igual, acostado sobre la superficie
  debajo_de        -> el sujeto debe caber DEBAJO del mueble: se comprueba el hueco libre (inventario) contra su tamaño
Fuente (en este orden): 1) campo explícito del plan 01  seg['relacion'] = {"tipo":..., "con": id, "parte": .., "lado": ..}
                        2) frases del 01 (porque / cita / pose) con un vocabulario de patrones del idioma (no de la escena).
Uso: R = extraer(E)  ->  lista de dicts {sujeto, tipo, con, con_tipo, parte, lado, t:[t0,t1], fuente, cita}"""
import re, unicodedata

TIPOS = ('sobre_hombro_de', 'sostenido_por', 'sobre_cabeza_de', 'sentado_en', 'acostado_en', 'debajo_de')
ANCLA = {'sobre_hombro_de': 'hombro', 'sostenido_por': 'mano', 'sobre_cabeza_de': 'cabeza'}   # tipo -> parte del cuerpo
APOYO = ('sentado_en', 'acostado_en')

def norm(s):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', str(s or '').lower()) if not unicodedata.combining(c)).replace('_', ' ').replace('-', ' ').split())

LADO = {'izquierdo': 'L', 'izquierda': 'L', 'izq': 'L', 'left': 'L', 'derecho': 'R', 'derecha': 'R', 'der': 'R', 'right': 'R'}
# patrones del idioma (ES + EN). X = el nombre (se sustituye por cada candidato de la escena)
PATRONES = [
    ('sobre_hombro_de', r'hombros?(?: (?P<lado>izquierdo|derecho|izquierda|derecha))? de(?:l)? (?:la |el )?X'),
    ('sobre_hombro_de', r'X\W.{0,40}?\b(?:su|sus) hombros?'),
    ('sobre_hombro_de', r'(?:on|onto) X\W?s? (?P<lado>left|right)? ?shoulder'),
    ('sobre_cabeza_de', r'(?:sobre|en) la cabeza de(?:l)? (?:la |el )?X'),
    ('sostenido_por', r'(?:en (?:los )?brazos|en (?:la )?mano|cargad[oa]|sostenid[oa]|alzad[oa]|llevad[oa] en brazos) (?:por |de )?(?:la |el )?X'),
    ('sostenido_por', r'(?:carried|held) by X'),
    ('sentado_en', r'sentad[oa]s? (?:en|sobre) (?:el |la |los |las |un |una )?X'),
    ('sentado_en', r'sit(?:s|ting)? (?:on|in) (?:the |a )?X'),
    ('acostado_en', r'(?:acostad[oa]|tumbad[oa]|recostad[oa]|dormid[oa])s? (?:boca \w+ )?(?:en|sobre) (?:el |la |un |una )?X'),
    ('acostado_en', r'(?:lying|lies|asleep) (?:on|in) (?:the |a )?X'),
    ('debajo_de', r'(?:debajo|abajo|bajo) (?:de )?(?:la |el |del )?X'),
    ('debajo_de', r'under(?:neath)? (?:the |a )?X'),
]
POSES_APOYO = {'acostado': 'acostado_en', 'tumbado': 'acostado_en', 'sentado': 'sentado_en'}

def _prefijo_comun(ids):
    """prefijo de canal común a los bib (p. ej. 'xyz-'), sacado de los datos; '' si no hay uno compartido por todos."""
    pre = [m.group(1) for m in (re.match(r'^([a-z0-9]{2,6}-)', i or '') for i in ids) if m]
    return pre[0] if pre and len(pre) == len(ids) and len(set(pre)) == 1 and len(ids) > 1 else ''

def nombres(E):
    """{id: [alias normalizados]} de personajes y objetos de la escena (derivados de id/bib/pedido; nunca escritos a mano)."""
    out = {}
    pjs = E.get('personajes', []) or []
    pre = _prefijo_comun([p.get('bib') for p in pjs if p.get('bib')] + [o.get('id') for o in E.get('objetos', []) or [] if o.get('id')])
    for p in pjs:
        al = set()
        m = re.match(r'^ch-(.+?)(?:-[0-9a-f]{4})?$', p['id']); al.add(norm(m.group(1) if m else p['id']))
        if p.get('bib'): al.add(norm(p['bib'][len(pre):] if pre and p['bib'].startswith(pre) else p['bib']))
        for k in ('nombre', 'nombre_visible', 'alias'):
            v = p.get(k)
            for x in (v if isinstance(v, list) else [v]):
                if x: al.add(norm(x))
        out[p['id']] = sorted((a for a in al if len(a) >= 2), key=len, reverse=True)
    for o in E.get('objetos', []) or []:
        oid = o.get('id') or ''; oid = oid[len(pre):] if pre and oid.startswith(pre) else oid
        al = {norm(re.sub(r'^obj-', '', o.get('pedido') or '')), norm(re.sub(r'^obj-', '', oid))}
        out.setdefault(o.get('pedido') or o.get('id'), sorted((a for a in al if len(a) >= 3), key=len, reverse=True))
    return out

def _tipo_destino(i, E):
    return 'personaje' if any(p['id'] == i for p in E.get('personajes', [])) else 'objeto'

def _otro_antes(t, pos, sujeto, destino, alias):
    """True si antes de la frase aparece el nombre de otro personaje (que no es el sujeto ni el destino)."""
    pre = t[:pos]
    for i, als in alias.items():
        if i in (sujeto, destino) or not i.startswith('ch-'): continue
        if any(re.search(r'\b' + re.escape(a) + r'\b', pre) for a in als): return True
    return False

def buscar(texto, sujeto, E, alias=None):
    """relaciones que menciona un texto para un sujeto. Devuelve lista [(tipo, destino, lado)]."""
    t = norm(texto)
    if not t: return []
    alias = alias or nombres(E); out = []
    for tipo, pat in PATRONES:
        for i, als in alias.items():
            if i == sujeto: continue
            es_pj = _tipo_destino(i, E) == 'personaje'
            if tipo in ANCLA and not es_pj: continue            # anclar solo a cuerpos con huesos
            if tipo in APOYO + ('debajo_de',) and es_pj: continue  # apoyarse / meterse debajo: objetos o muebles
            for a in als:
                rx = pat.replace('X', r'\b' + re.escape(a) + r'\b')
                m = re.search(rx, t)
                if m and tipo not in ANCLA and _otro_antes(t, m.start(), sujeto, i, alias):
                    m = None   # la frase habla de OTRO personaje («... cuando X se asoma por debajo de ...»): no es del sujeto
                if m:
                    lado = None
                    try: lado = LADO.get((m.group('lado') or '').strip())
                    except IndexError: pass
                    if lado is None:
                        lado = next((v for k, v in LADO.items() if re.search(r'\b' + k + r'\b', t)), None) if tipo in ANCLA else None
                    out.append((tipo, i, lado)); break
            if out and out[-1][1] == i and out[-1][0] == tipo: break
    # dedup conservando orden
    vis = set(); res = []
    for x in out:
        if (x[0], x[1]) not in vis: vis.add((x[0], x[1])); res.append(x)
    return res

def extraer(E):
    """relaciones por personaje y tramo, del 01 (campo explícito primero; si no, frases)."""
    alias = nombres(E); R = []
    for pid, segs in (E.get('segmentos_01') or {}).items():
        for s in sorted(segs, key=lambda s: s['t'][0]):
            ex = s.get('relacion')
            if isinstance(ex, dict) and ex.get('tipo') in TIPOS and ex.get('con'):
                R.append({"sujeto": pid, "tipo": ex['tipo'], "con": ex['con'], "con_tipo": _tipo_destino(ex['con'], E), "lado": ex.get('lado'),
                          "parte": ex.get('parte') or ANCLA.get(ex['tipo']), "t": list(s['t']), "fuente": "01.relacion", "cita": s.get('porque')})
                continue
            for tipo, con, lado in buscar(s.get('porque', ''), pid, E, alias):
                R.append({"sujeto": pid, "tipo": tipo, "con": con, "con_tipo": _tipo_destino(con, E), "lado": lado, "parte": ANCLA.get(tipo),
                          "t": list(s['t']), "fuente": "01.porque (frase)", "cita": s.get('porque')})
    for a in E.get('acciones_01') or []:
        pid = a.get('actor')
        if not pid: continue
        txt = ' '.join(str(a.get(k) or '') for k in ('cita', 'pose'))
        found = buscar(txt, pid, E, alias)
        pz = norm(a.get('pose'))
        for k, tipo in POSES_APOYO.items():   # «pose: acostado_*» + objeto de la acción = apoyo en ese objeto
            if pz.startswith(k) and a.get('objeto') and not any(f[0] in ('debajo_de',) and f[1] == a['objeto'] for f in found):
                found.append((tipo, a['objeto'], None))
        for tipo, con, lado in found:
            R.append({"sujeto": pid, "tipo": tipo, "con": con, "con_tipo": _tipo_destino(con, E), "lado": lado, "parte": ANCLA.get(tipo),
                      "t": list(a['t']), "fuente": f"01.accion {a.get('id')}", "cita": a.get('cita')})
    return consolidar(R)

def consolidar(R):
    """une tramos contiguos/solapados de la misma relación; si un sujeto tiene a la vez 'debajo_de' y 'acostado_en' del MISMO
    objeto, gana 'debajo_de' (la frase concreta manda sobre la pose genérica)."""
    R = sorted(R, key=lambda r: (r['sujeto'], r['tipo'], str(r['con']), r['t'][0]))
    out = []
    for r in R:
        if out and all(out[-1][k] == r[k] for k in ('sujeto', 'tipo', 'con')) and r['t'][0] <= out[-1]['t'][1] + 0.05:
            out[-1]['t'][1] = max(out[-1]['t'][1], r['t'][1]); out[-1]['lado'] = out[-1]['lado'] or r['lado']
            out[-1].setdefault('fuentes', [out[-1]['fuente']]).append(r['fuente']); continue
        out.append(dict(r))
    # huecos entre dos tramos de la MISMA relación de anclaje (p. ej. un tramo que solo dice «gira con X»): se rellenan si el sujeto
    # no tiene otra relación en el hueco (seguir anclado es lo físico; soltarse exigiría que el 01 lo diga)
    anc = [r for r in out if r['tipo'] in ANCLA]; otros = [r for r in out if r['tipo'] not in ANCLA]; anc2 = []
    for r in anc:
        p = anc2[-1] if anc2 else None
        if p and all(p[k] == r[k] for k in ('sujeto', 'tipo', 'con')):
            g0, g1 = p['t'][1], r['t'][0]
            if not any(o['sujeto'] == r['sujeto'] and o['t'][0] < g1 and o['t'][1] > g0 for o in otros):
                p['t'][1] = max(p['t'][1], r['t'][1]); p['lado'] = p['lado'] or r['lado']; p.setdefault('huecos_rellenados', []).append([g0, g1]); continue
        anc2.append(r)
    out = sorted(anc2 + otros, key=lambda r: (r['sujeto'], r['t'][0]))
    deb = {(r['sujeto'], r['con']) for r in out if r['tipo'] == 'debajo_de'}
    return [r for r in out if not (r['tipo'] == 'acostado_en' and (r['sujeto'], r['con']) in deb)]

def ancla_de(R, pid):
    """la relación de anclaje (hombro/mano/cabeza) de un personaje, con el tramo más largo; None si no hay."""
    xs = [r for r in R if r['sujeto'] == pid and r['tipo'] in ANCLA]
    return max(xs, key=lambda r: r['t'][1] - r['t'][0]) if xs else None
