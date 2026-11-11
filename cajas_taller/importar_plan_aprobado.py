"""PISTA INMI (2026-10-29): orden 79 — conversor GENÉRICO «importar plan aprobado → formato 01» (regla 6, con pruebas). GRATIS.
Ricardo pidió ensayar el 02 con un plan de tomas YA APROBADO, gratis (la orden concreta está en ORDENES.md).
Toma un plan de tomas YA APROBADO (la RESPUESTA json con sus láminas/tomas + el PROMPT aprobado que lleva las posiciones por segundo
y las anclas del lugar) y escribe cubos/01/esc_<N>.json con el contrato de entrada del 02 (formato PASO_01), marcado como IMPORTADO
(«origen»: la etiqueta pedida, p. ej. «importado de plan aprobado <fecha>») para que nunca se confunda con una corrida real del 01
(dirigida() lo ignora salvo para el 02, que lo pide a propósito).
Reglas (nunca se inventa nada):
  · posiciones: SOLO las que dice el plan (registro por segundo del prompt aprobado). Sin giro en el plan → sin «rot».
  · personajes: nombre del plan → id del canal por id/nombre/alias/rol declarado (solo lectura de las fichas).
  · lugar: molde de la escena (paso01_datos/importar_plan.json dice cómo elegirlo). Las coordenadas del plan solo se usan si sus lugares
    con nombre (AC, tanques, caseta…) caen sobre los del molde con un ajuste rígido en planta (giro + traslado, sin estirar) dentro de la
    tolerancia. Si no caben: NO se mueven a ojo; las tomas quedan PARADAS con el motivo y los números del ajuste.
Uso: python3 importar_plan_aprobado.py --canal C --capitulo 1 --escena 8 --respuesta r.json --prompt p.txt
                                        --etiqueta "importado de plan aprobado <fecha>" --fecha-plan AAAA-MM-DD [--escenario ID] [--escribir]
Sin --escribir solo muestra lo que haría. Nunca pisa una salida REAL del 01 (sin marca de importado)."""
import argparse, hashlib, json, math, re, sys, time
from pathlib import Path
import paso01_cubos as K

CFG_NOMBRE = 'importar_plan.json'


def cfg(): return K.dato(CFG_NOMBRE)
def sha(b): return hashlib.sha256(b).hexdigest()
def tokens(s): return re.sub(r'[^a-z0-9]+', ' ', K._norm(s)).split()


def frase_en(frase, nombre):
    f, t = tokens(frase), tokens(nombre)
    return bool(f) and any(t[i:i + len(f)] == f for i in range(len(t) - len(f) + 1))


def campo(d, claves, defecto=None):
    for k in claves:
        if isinstance(d, dict) and d.get(k) is not None: return d[k]
    return defecto


# ---------------- lectura del plan ----------------
def bloque_json(texto, rx):
    """El primer objeto JSON que sigue a la línea que cumple rx (p. ej. «POSICIONES v4 (…):»)."""
    m = re.search(rx, texto, re.M)
    if not m: return None
    i = texto.find('{', m.end())
    if i < 0: return None
    try: return json.JSONDecoder().raw_decode(texto[i:])[0]
    except ValueError: return None


def leer_plan(f_resp, f_prompt, C=None):
    C = C or cfg(); cr, cp = C['respuesta'], C['prompt']
    rb, pb = Path(f_resp).read_bytes(), Path(f_prompt).read_bytes()
    R = json.loads(rb.decode('utf-8')); P = pb.decode('utf-8')
    lista = campo(R, cr['listas_de_tomas'], []) if isinstance(R, dict) else (R if isinstance(R, list) else [])
    tomas = []
    for i, l in enumerate(lista):
        tomas.append({'id': str(campo(l, cr['id'], f'T{i + 1:02d}')), 't': [K._num(campo(l, cr['t_ini'])), K._num(campo(l, cr['t_fin']))],
                      'loc': campo(l, cr['camara_loc']), 'mira': campo(l, cr['camara_mira']), 'lente': K._num(campo(l, cr['lente'])),
                      'plano': campo(l, cr['plano'])})
    pos = bloque_json(P, cp['bloque_posiciones']) or {}
    anc = bloque_json(P, cp['bloque_anclas']) or {}
    return {'R': R, 'texto': P + '\n' + rb.decode('utf-8'), 'tomas': tomas, 'posiciones': pos, 'anclas': anc,
            'total_s': K._num(campo(R, cr['total_s'])) if isinstance(R, dict) else None,
            'sha_respuesta': sha(rb), 'sha_prompt': sha(pb)}


def personajes_plan(pos, C):
    """Nombres de personaje del registro por segundo: claves «<nombre>_xyz»."""
    suf = C['prompt']['sufijo_posicion']; vistos = []
    for r in pos.get(C['prompt']['log']) or []:
        for k in r:
            if k.endswith(suf) and k[:-len(suf)] not in vistos: vistos.append(k[:-len(suf)])
    return vistos


def roles_declarados(texto, C):
    out = {}
    for rol, nom in re.findall(C['prompt']['declara_rol'], texto, re.I):
        out.setdefault(K._norm(nom.strip()), K._norm(rol))
    return out


# ---------------- personajes del canal (solo lectura) ----------------
def fichas_canal(canal_id, PC):
    """id → {nombre, alias[], rol} juntando la base del estudio (PC) y la lista de personajes del canal en la biblioteca (solo lectura)."""
    out = {k: {'nombre': v.get('nombre'), 'alias': [], 'rol': None} for k, v in (PC or {}).items()}
    f = Path(K.os.environ.get('MYIA_BIBLIOTECA', '/opt/myia-taller-n8n/trabajo/biblioteca')) / canal_id / 'personajes' / 'personajes.json'
    for p in (K.leer(f, {}) or {}).get('personajes') or []:
        if not isinstance(p, dict) or not p.get('id'): continue
        o = out.setdefault(p['id'], {'nombre': p.get('nombre'), 'alias': [], 'rol': None})
        o['alias'] = list(dict.fromkeys([*(o['alias'] or []), *([o['nombre']] if o['nombre'] and o['nombre'] != p.get('nombre') else []), *(p.get('alias') or [])]))
        o['nombre'] = p.get('nombre') or o['nombre']; o['rol'] = p.get('rol') or o['rol']
    return out


def con_miembros(canal_id, en_escena):
    """PISTA INMI (orden 85): si la escena trae un GRUPO dividido (personajes.json → grupos, por id o id del mapa), sus miembros también
    están en la escena (el plan puede nombrarlos uno por uno por nombre o por su versión vieja, que es alias). Solo lectura."""
    f = Path(K.os.environ.get('MYIA_BIBLIOTECA', '/opt/myia-taller-n8n/trabajo/biblioteca')) / canal_id / 'personajes' / 'personajes.json'
    out = set(en_escena or ())
    for g in (K.leer(f, {}) or {}).get('grupos') or []:
        if isinstance(g, dict) and ({g.get('id'), *(g.get('ids_mapa') or [])} & out):
            out |= {x.get('personaje') for x in g.get('miembros') or [] if isinstance(x, dict) and x.get('personaje')}
    return out


def cruzar(nombre, fichas, en_escena, roles, C):
    """Devuelve (id, cómo) o (None, motivo). Solo entre los personajes de la escena (si base.json los da)."""
    cand = {k: v for k, v in fichas.items() if not en_escena or k in en_escena}
    nn = K._norm(nombre); pm = int(C['personajes']['prefijo_minimo_letras'])
    def nombres(k, v): return [k, v.get('nombre'), *(v.get('alias') or [])]
    hit = [k for k, v in cand.items() if any(K._norm(x) == nn for x in nombres(k, v) if x)]
    if len(hit) == 1: return hit[0], 'mismo id/nombre/alias'
    rol = next((r for n, r in roles.items() if n == nn or n.split()[0] == nn), None)
    if rol and not hit:
        hit = [k for k, v in cand.items() if any(K._norm(x) == rol for x in [*nombres(k, v), v.get('rol')] if x)]
        if len(hit) == 1: return hit[0], f'el plan declara «{rol} = {nombre}» y en el canal «{rol}» es {fichas[hit[0]].get("nombre")}'
    if not hit and len(nn) >= pm:
        hit = [k for k, v in cand.items() if any(w.startswith(nn) for x in nombres(k, v) if x for w in tokens(x))]
        if len(hit) == 1: return hit[0], f'«{nombre}» es el comienzo de un nombre/alias de {fichas[hit[0]].get("nombre")}'
    return None, (f'«{nombre}» se parece a varios personajes del canal ({", ".join(sorted(hit))})' if hit else f'«{nombre}» no está entre los personajes del canal en esta escena')


# ---------------- lugar ----------------
def elegir_escenario(D, e, texto, pedido, C):
    if pedido: return pedido, f'pedido a mano (--escenario {pedido})', []
    moldes = sorted(p.name for p in (D / 'ramas' / 'moldes').glob('*') if (p / 'molde.blend').is_file())
    ign = set(C['escenario']['palabras_ignoradas'])
    sets = [s.get('nombre') if isinstance(s, dict) else s for s in (e['datos'].get('sets') or [])]
    cand = [m for m in moldes if m == e['escenario_id'] or any(set(tokens(s)) - ign and set(tokens(s)) - ign <= set(tokens(m)) for s in sets if s)]
    if not cand: return None, f'la escena no tiene molde (ni {e["escenario_id"]} ni los de sus sets {sets})', []
    tt = tokens(texto); puntos = []
    for m in cand:
        pal = [w for w in tokens(m) if w not in ign]
        puntos.append((sum(1 for w in tt for p in pal if w.startswith(p)), m))
    puntos.sort(reverse=True)
    det = [{'molde': m, 'veces_que_el_plan_lo_nombra': n} for n, m in puntos]
    if len(puntos) > 1 and puntos[0][0] == puntos[1][0]: return None, f'empate entre moldes {det}: decidir con --escenario', det
    m = puntos[0][1]
    por = f'el plan nombra «{m}» {puntos[0][0]} veces' + ('' if m == e['escenario_id'] else f' (base.json dice {e["escenario_id"]}; la escena tiene el set {sets})')
    return m, por, det


def lugares_plan(anc, C):
    rx = C['prompt']['posicion_en_texto']; out = {}
    for k, txt in ((anc or {}).get(C['prompt']['anclas_lugares']) or {}).items():
        tipo = next((t for t, d in C['lugares']['tipos'].items() if any(frase_en(w, k) for w in d['plan'])), None)
        if not tipo: continue
        pts = []
        for m in re.finditer(rx, str(txt)):
            g = [float(x) for x in m.groups() if x is not None]
            pts += [g[i:i + 2] for i in range(0, len(g), 2)]
        if pts: out.setdefault(tipo, {'de': [], 'pts': []}); out[tipo]['de'].append(k); out[tipo]['pts'] += pts
    return {t: {'de': v['de'], 'xy': [sum(p[0] for p in v['pts']) / len(v['pts']), sum(p[1] for p in v['pts']) / len(v['pts'])]} for t, v in out.items()}


def lugares_molde(med, C):
    out = {}
    for nom, bb in (med or {}).items():
        tipo = next((t for t, d in C['lugares']['tipos'].items() if any(frase_en(w, nom) for w in d['molde'])), None)
        if not tipo: continue
        out.setdefault(tipo, []).append((nom, [(bb['min'][0] + bb['max'][0]) / 2, (bb['min'][1] + bb['max'][1]) / 2]))
    return {t: {'de': [n for n, _ in v], 'xy': [sum(p[0] for _, p in v) / len(v), sum(p[1] for _, p in v) / len(v)]} for t, v in out.items()}


def ajuste_rigido(pares):
    """Giro + traslado en planta (mínimos cuadrados, sin escala ni espejo). pares = [(xy_plan, xy_molde)]."""
    n = len(pares); pc = [sum(p[0][i] for p in pares) / n for i in (0, 1)]; qc = [sum(p[1][i] for p in pares) / n for i in (0, 1)]
    s = c = 0.0
    for p, q in pares:
        a, b = [p[0] - pc[0], p[1] - pc[1]], [q[0] - qc[0], q[1] - qc[1]]
        c += a[0] * b[0] + a[1] * b[1]; s += a[0] * b[1] - a[1] * b[0]
    th = math.atan2(s, c); co, si = math.cos(th), math.sin(th)
    tx, ty = qc[0] - (co * pc[0] - si * pc[1]), qc[1] - (si * pc[0] + co * pc[1])
    f = lambda x, y: [co * x - si * y + tx, si * x + co * y + ty]
    res = [math.dist(f(*p), q) for p, q in pares]
    return {'giro_grados': round(math.degrees(th), 2), 'traslado_m': [round(tx, 3), round(ty, 3)],
            'rms_m': round(math.sqrt(sum(r * r for r in res) / n), 3), 'residuos_m': [round(r, 3) for r in res]}, f


def marco(anc, med, C):
    lp, lm = lugares_plan(anc, C), lugares_molde(med, C)
    comunes = sorted(set(lp) & set(lm)); L = C['lugares']
    info = {'lugares_plan': lp, 'lugares_molde': lm, 'comunes': comunes, 'tolerancia_rms_m': L['tolerancia_rms_m'], 'ok': False}
    if len(comunes) < int(L['pares_minimos']):
        info['motivo'] = (f'solo {len(comunes)} lugares con nombre en común entre el plan y el molde ({comunes}); hacen falta '
                          f'{L["pares_minimos"]} para saber dónde caen sus coordenadas'); return info, None
    aj, f = ajuste_rigido([(lp[t]['xy'], lm[t]['xy']) for t in comunes])
    info.update(aj); info['residuo_por_lugar_m'] = dict(zip(comunes, aj['residuos_m']))
    if aj['rms_m'] > float(L['tolerancia_rms_m']):
        peor = max(info['residuo_por_lugar_m'].items(), key=lambda x: x[1])
        info['motivo'] = (f'el lugar del plan no es este molde: sus lugares con nombre ({", ".join(comunes)}) no caen sobre los del molde '
                          f'ni girando ni moviendo (error medio {aj["rms_m"]} m > {L["tolerancia_rms_m"]} m; el peor, {peor[0]}, queda a {peor[1]} m). '
                          f'No se mueven las posiciones a ojo.'); return info, None
    info['ok'] = True
    z0 = max([bb['max'][2] for n, bb in (med or {}).items() if any(frase_en(w, n) for w in L['suelo_molde'])] or [0.0])
    info['suelo_z_molde'] = z0
    return info, (lambda p: [*f(float(p[0]), float(p[1])), float(p[2]) + z0])


# ---------------- conversión ----------------
def convertir(D, canal_id, n, plan, M, PC, etiqueta, fecha_plan, escenario_id, escenario_por, C=None, en_escena=None):
    C = C or cfg(); cp = C['prompt']; pos = plan['posiciones']
    log = sorted([r for r in pos.get(cp['log']) or [] if K._num(r.get('t')) is not None], key=lambda r: float(r['t']))
    fichas = fichas_canal(canal_id, PC); roles = roles_declarados(plan['texto'], C)
    info, f = marco(plan['anclas'], (M or {}).get('medidas'), C)
    cruces, pers, paradas_pj = [], [], []
    for nom in personajes_plan(pos, C):
        cid, como = cruzar(nom, fichas, en_escena, roles, C)
        cruces.append({'plan': nom, 'id': cid, 'nombre_canal': (fichas.get(cid) or {}).get('nombre'), 'como': como})
        if not cid: paradas_pj.append(f'{nom}: {como}'); continue
        if not f: continue
        segs, kx, kp = [], nom + cp['sufijo_posicion'], nom + cp['sufijo_pose']
        for a, b in zip(log, log[1:]):
            if a.get(kx) is None or b.get(kx) is None: continue
            if float(b['t']) - float(a['t']) > float(C['segundos_por_muestra_max']): continue
            segs.append({'t': [float(a['t']), float(b['t'])], 'pos': [f(a[kx]), f(b[kx])], 'rot': None, 'tipo': a.get(kp)})
        if segs: pers.append({'id': cid, 'nombre_plan': nom, 'segmentos': segs, 'entrada': {'t': segs[0]['t'][0]}})
    motivo = None
    if not f: motivo = info.get('motivo') or 'no se pudo ubicar el plan en el molde'
    elif not pers: motivo = 'ningún personaje del plan se pudo cruzar con el canal: ' + '; '.join(paradas_pj)
    tomas = []
    for t in plan['tomas']:
        m = motivo
        if not m and not (K._xyz({}, t['loc']) and K._xyz({}, t['mira'])): m = 'la toma no dice posición de cámara y mira [x,y,z]'
        if not m and (t['t'][0] is None or t['t'][1] is None): m = 'la toma no dice sus segundos'
        cam = None if m else {'loc': f(t['loc']), 'mira': f(t['mira']), 'lente': t['lente'] or 35}
        if cam:
            med = (M or {}).get('medidas') or {}; mg = float(C['lugares']['margen_fuera_m'])
            xs = [v for bb in med.values() for v in (bb['min'][0], bb['max'][0])]; ys = [v for bb in med.values() for v in (bb['min'][1], bb['max'][1])]
            if xs and not (min(xs) - mg <= cam['loc'][0] <= max(xs) + mg and min(ys) - mg <= cam['loc'][1] <= max(ys) + mg):
                m, cam = f'la cámara del plan cae fuera del molde ({[round(v, 2) for v in cam["loc"]]})', None
        tomas.append({'id': t['id'], 't': t['t'], 'plano': t['plano'], 'camara': cam, 'camara_plan': {'loc': t['loc'], 'mira': t['mira'], 'lente': t['lente']},
                      'motivo_no_animable': m})
    return {'origen': etiqueta, 'es_corrida_del_01': False,
            'importado': {'etiqueta': etiqueta, 'fecha_plan': fecha_plan, 'programa': 'importar_plan_aprobado.py (orden 79)',
                          'importado_en': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'sha_respuesta': plan['sha_respuesta'], 'sha_prompt': plan['sha_prompt'],
                          'aviso': 'NO es una corrida del cubo 01: es un plan ya aprobado pasado al formato del 01 para ensayar el 02.'},
            'escena': str(n), 'escenario_id': escenario_id, 'escenario_elegido_por': escenario_por,
            'fps': K._num(pos.get(cp['fps'])) or None, 'duracion_s': plan['total_s'] or (float(log[-1]['t']) if log else None),
            'marco': info, 'personajes_cruce': cruces, 'personajes': pers, 'motivo_no_animable': motivo, 'tomas_plan': tomas,
            'resumen': {'tomas': len(tomas), 'animables': sum(1 for t in tomas if not t['motivo_no_animable']),
                        'paradas': sum(1 for t in tomas if t['motivo_no_animable'])}}


def main(argv):
    ap = argparse.ArgumentParser(prog='importar_plan_aprobado')
    for k in ('--canal', '--capitulo', '--escena', '--respuesta', '--prompt', '--etiqueta', '--fecha-plan'): ap.add_argument(k, required=True)
    ap.add_argument('--escenario', default=''); ap.add_argument('--sha-prompt', default=''); ap.add_argument('--escribir', action='store_true')
    a = ap.parse_args(argv); C = cfg()
    D = K.carpeta(a.canal, a.capitulo)
    if not D: return {'ok': False, 'error': f'no hay carpeta del capítulo {a.capitulo} del canal {a.canal}'}
    es = K.escenas(D, {str(a.escena)})
    if not es: return {'ok': False, 'error': f'base.json no tiene la escena {a.escena}'}
    e = es[0]; plan = leer_plan(a.respuesta, a.prompt, C)
    if a.sha_prompt and not plan['sha_prompt'].startswith(a.sha_prompt):
        return {'ok': False, 'error': f'el prompt no es el aprobado: sha {plan["sha_prompt"][:12]} ≠ {a.sha_prompt}'}
    eid, por, det = elegir_escenario(D, e, plan['texto'], a.escenario, C)
    if not eid: return {'ok': False, 'error': por, 'candidatos': det}
    M, merr = K.molde(D, eid)
    if merr: return {'ok': False, 'error': merr}
    PC = K.personajes_canal(a.canal)
    x = convertir(D, a.canal, e['numero'], plan, M, PC, a.etiqueta, a.fecha_plan, eid, por, C, con_miembros(a.canal, set(p for p in e['personajes'] if p)))
    x['escenario_candidatos'] = det
    f = D / 'cubos' / '01' / f'esc_{e["numero"]}.json'; previo = K.leer(f)
    out = {'ok': True, 'archivo': str(f), 'escribe': bool(a.escribir), 'escenario_id': eid, 'escenario_elegido_por': por, **x['resumen'],
           'motivo_no_animable': x['motivo_no_animable'], 'personajes_cruce': x['personajes_cruce'],
           'marco': {k: x['marco'].get(k) for k in ('ok', 'comunes', 'rms_m', 'residuo_por_lugar_m', 'giro_grados', 'motivo')}, 'usd_gastado': 0}
    if previo is not None and not (isinstance(previo, dict) and previo.get('importado')):
        out.update(ok=False, error=f'{f} ya tiene una salida REAL del 01: no se pisa'); return out
    if a.escribir:
        if previo is not None:
            r = f.with_name(f'{f.stem}.antes_{time.strftime("%Y%m%d_%H%M%S")}.json'); r.write_bytes(f.read_bytes()); out['respaldo'] = str(r)
        K.guardar(f, x)
    return out


if __name__ == '__main__':
    print(json.dumps(main(sys.argv[1:]), ensure_ascii=False))
