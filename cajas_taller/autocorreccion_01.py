#!/usr/bin/env python3
"""PISTA INMI (2026-11-01, Ricardo t296u/t297u): autocorrección GENÉRICA del cubo 01 (cualquier canal, escenario y personaje).

1. PREVENIR  · camaras_validas(): antes de llamar a Argon el código calcula, con la geometría REAL de las cámaras del molde,
               qué cámaras ven el suelo libre del set y ofrece SOLO las de ESTA escena (política en paso01_datos/argon_pago.json
               → 01.camaras). Si la escena no tiene cámara propia que vea el suelo, ofrece las del mismo set que sí lo ven y lo avisa.
2. REPARAR   · agrupar_errores() + prompt_reparacion(): cuando el validador rechaza, a Argon se le mandan los errores EXACTOS y
               SOLO las tomas / segmentos que fallaron (más el plan aceptado como contexto fijo). No se rehace la escena.
3. CONSERVAR · fusionar(): lo que pasó se queda; se reemplazan solo las tomas / personajes / puntos que vinieron en la reparación,
               y se vuelve a validar TODO el resultado fusionado.
4. LÍMITE    · bucle(): como mucho N reparaciones (01.reparaciones_max, por defecto 2). Cada intento pago lo hace la función
               `llamar` que recibe (en el camino pago: cotización fresca + guarda HABILITAR_PAGO_01 + ledger ANTES + tope).
               Si sigue fallando devuelve un error en español simple para Ricardo (explicar()).
Este archivo NO llama a la red ni al ledger: todo lo pago entra por `llamar`. Las pruebas usan un Argon falso (sin costo)."""
import copy, json, re
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PROMPT_REPARAR = 'prompts_01/reparar_tomas_o120.txt'
DEF_CAMARAS = {'politica': 'solo_escena', 'min_suelo_visible_pct': 3.0, 'min_zona_escena_pct': 40.0, 'paso_muestreo_m': 0.5, 'altura_centro_m': 0.95}


def ajustes_01():
    try: c = json.loads((AQUI / 'paso01_datos' / 'argon_pago.json').read_text(encoding='utf-8'))['01']
    except Exception: c = {}
    return {'camaras': {**DEF_CAMARAS, **(c.get('camaras') or {})}, 'reparaciones_max': int(c.get('reparaciones_max', 2))}


# ---------------------------------------------------------------- 1. PREVENIR: cámaras que sirven
def _solidos(S):
    """Cajas de objetos que ocupan suelo (no se puede parar nadie dentro). Las muy finas o altas en el aire no cuentan."""
    L = S.get('floor_bounds') or {}; z0 = float(L.get('z_floor', 0))
    out = []
    for o in S.get('objects') or []:
        mn, mx = o.get('min'), o.get('max')
        if not (mn and mx): continue
        if mn[2] > z0 + 1.2: continue                       # en el aire (antena, baliza): no ocupa suelo
        if (mx[0] - mn[0]) * (mx[1] - mn[1]) > 0.6 * (L['x'][1] - L['x'][0]) * (L['y'][1] - L['y'][0]): continue   # el piso mismo
        out.append((mn, mx))
    return out


def suelo_libre(S, paso):
    """Puntos de muestra del suelo libre del set (rejilla, fuera de objetos sólidos), a la altura del piso que pisan los objetos."""
    L = S['floor_bounds']; sol = _solidos(S)
    pisos = sorted(o['min'][2] for o in S.get('objects') or [] if o.get('min'))
    zp = pisos[len(pisos) // 2] if pisos else float(L['z_floor'])   # altura típica de apoyo (mediana de las bases)
    zp = min(zp, float(L['z_floor']) + 1.0)
    pts = []; x = L['x'][0] + paso / 2
    while x < L['x'][1]:
        y = L['y'][0] + paso / 2
        while y < L['y'][1]:
            if not any(mn[0] <= x <= mx[0] and mn[1] <= y <= mx[1] for mn, mx in sol): pts.append([round(x, 3), round(y, 3), zp])
            y += paso
        x += paso
    return pts


def ve_punto(O, cam, p, aspecto, altura_centro):
    u, v, dl = O.proyectar(cam, [p[0], p[1], p[2] + altura_centro], aspecto)
    return bool(dl and 0.0 <= u <= 1.0 and 0.0 <= v <= 1.0)


def camaras_validas(O, M, S, n, aspecto, cfg=None):
    """Devuelve (ofrecidas, informe). ofrecidas = cámaras del molde que Argon puede usar en la escena n (con la caja del suelo
    que cada una ve). informe = por cámara: de qué escena es, % del suelo libre que ve y por qué se ofrece o no.
    Políticas (paso01_datos/argon_pago.json → 01.camaras.politica):
      solo_escena  = solo las cámaras de ESTA escena que ven el suelo libre (si no hay, las del set que lo ven, con aviso).
      escena_y_set = las de ESTA escena (preferidas, van primero) + las del MISMO set (mismo molde) SOLO si la geometría comprueba
                     que ven la ZONA DE ESTA ESCENA = el suelo libre que ven las cámaras propias (>= min_zona_escena_pct de esa zona).
                     Si la escena no tiene cámara propia que vea el suelo, la zona es todo el suelo libre.
    Después de dirigir, el validador vuelve a comprobar en cada toma que la cámara elegida vea a cada personaje en su posición."""
    cfg = {**DEF_CAMARAS, **(cfg or {})}
    cams = (M or {}).get('camaras_molde') or []
    pts = suelo_libre(S, float(cfg['paso_muestreo_m'])) if S.get('floor_bounds') else []
    inf = []; vis_de = {}
    for c in cams:
        vis = [p for p in pts if ve_punto(O, c, p, aspecto, float(cfg['altura_centro_m']))] if pts else []
        vis_de[c['nombre']] = {tuple(p) for p in vis}
        pct = round(100.0 * len(vis) / len(pts), 1) if pts else 0.0
        caja = ([min(p[0] for p in vis), max(p[0] for p in vis), min(p[1] for p in vis), max(p[1] for p in vis)] if vis else None)
        inf.append({'nombre': c['nombre'], 'escena_molde': str(c.get('escena_molde')), 'propia': str(c.get('escena_molde')) == str(n),
                    'suelo_visible_pct': pct, 'suelo_visible_caja_xy': caja, 'ven': len(vis)})
    minp = float(cfg['min_suelo_visible_pct']); minz = float(cfg.get('min_zona_escena_pct', 40.0))
    propias = [i for i in inf if i['propia'] and i['suelo_visible_pct'] >= minp]
    zona = set().union(*[vis_de[i['nombre']] for i in propias]) if propias else {tuple(p) for p in pts}
    for i in inf:
        i['zona_escena_visible_pct'] = round(100.0 * len(vis_de[i['nombre']] & zona) / len(zona), 1) if zona else 0.0
    usar = propias; motivo = 'solo cámaras de esta escena que ven el suelo libre'
    if cfg['politica'] == 'escena_y_set':
        set_ = [i for i in inf if not (i in propias) and i['suelo_visible_pct'] >= minp and i['zona_escena_visible_pct'] >= minz]
        usar = propias + sorted(set_, key=lambda i: -i['zona_escena_visible_pct'])
        motivo = (f'cámaras de esta escena (preferidas) + las del mismo set que ven >= {minz}% de la zona de esta escena' if propias else
                  f'la escena {n} no tiene cámara propia que vea el suelo: se ofrecen las del mismo set que ven >= {minz}% del suelo libre')
    elif not propias:
        usar = [i for i in inf if i['suelo_visible_pct'] >= minp]
        motivo = f'la escena {n} no tiene cámara propia que vea el suelo: se ofrecen las del mismo set que sí lo ven'
    nombres = [i['nombre'] for i in usar]
    for i in inf:
        i['ofrecida'] = i['nombre'] in nombres
        if i['ofrecida']: i['por_que'] = ('propia de la escena; ' if i['propia'] else 'del mismo set; ') + motivo
        elif i['suelo_visible_pct'] < minp: i['por_que'] = f"ve solo {i['suelo_visible_pct']}% del suelo libre (< {minp}%)"
        elif not i['propia'] and cfg['politica'] == 'escena_y_set': i['por_que'] = f"del mismo set pero ve solo {i['zona_escena_visible_pct']}% de la zona de esta escena (< {minz}%)"
        elif not i['propia']: i['por_que'] = 'es de otra escena (' + i['escena_molde'] + ')'
        else: i['por_que'] = 'no se ofrece'
    por_nombre = {c['nombre']: c for c in cams}
    of = [por_nombre[x] for x in nombres]   # en orden: propias primero, luego las del set que más zona ven
    return of, {'politica': cfg['politica'], 'motivo': motivo, 'muestras_suelo': len(pts), 'muestras_zona_escena': len(zona),
                'min_zona_escena_pct': minz, 'camaras': inf}


def ve_personajes(O, K, C, cam, t, aspecto):
    """Para un plan ya dirigido: qué personajes ve la cámara en el segundo t (sirve para explicar y para el Argon falso)."""
    out = {}
    for p in C.get('personajes') or []:
        g = O.geometria(K, C, p, cam, t, aspecto)
        out[p['id']] = bool(g and g['en_cuadro'])
    return out


# ---------------------------------------------------------------- 2. REPARAR: qué falló
_RX_TOMA = re.compile(r'^tomas\[(\d+)\]\s+([^\s:.]+)')
_RX_SEG = re.compile(r'^(?:personajes\[\d+\]\s+\()?([A-Za-z0-9_\-]+)\)?\.segmentos\[(\d+)\]')
_RX_PUNTO = re.compile(r'^puntos\.([^\s:]+)')
_RX_ACC = re.compile(r'^acciones\[(\d+)\](?:\s+([^\s:.]+))?')   # accion_v1
_RX_HECHO = re.compile(r'^(?:falta «)?hechos[\[»]')


def agrupar_errores(err, obj):
    """{'tomas': {id: [errores]}, 'personajes': {id: [errores]}, 'puntos': {nombre: [errores]}, 'otros': [errores]}."""
    tomas = obj.get('tomas') or []; ids_p = {str(p.get('id')) for p in obj.get('personajes') or []}
    g = {'tomas': {}, 'personajes': {}, 'puntos': {}, 'acciones': {}, 'hechos': [], 'otros': []}
    acc = obj.get('acciones') or []
    for e in err:
        s = str(e); m = _RX_ACC.match(s)
        if m:
            i = int(m.group(1)); aid = str(acc[i].get('id')) if i < len(acc) and isinstance(acc[i], dict) and acc[i].get('id') else (m.group(2) or f'#{i}')
            g['acciones'].setdefault(aid, []).append(s); continue
        if _RX_HECHO.match(s): g['hechos'].append(s); continue
        m = _RX_TOMA.match(s)
        if m:
            i = int(m.group(1)); tid = str(tomas[i].get('id')) if i < len(tomas) else m.group(2)
            g['tomas'].setdefault(tid, []).append(s); continue
        m = _RX_SEG.match(s)
        if m and m.group(1) in ids_p: g['personajes'].setdefault(m.group(1), []).append(s); continue
        m = _RX_PUNTO.match(s)
        if m: g['puntos'].setdefault(m.group(1), []).append(s); continue
        g['otros'].append(s)
    for k in ('tomas', 'personajes', 'puntos', 'acciones'):
        g[k] = {x: sorted(set(v), key=v.index) for x, v in g[k].items()}
    return g


def esquema_reparacion(esq01):
    """Esquema de la respuesta de reparación, armado desde el esquema del 01 (siempre en sincronía con él)."""
    P = esq01.get('properties') or {}
    seg = ((P.get('personajes') or {}).get('items') or {}).get('properties', {}).get('segmentos', {'type': 'array'})
    if 'tomas' not in P and 'acciones' in P:   # accion_v1: el 01 sin cámaras repara beats/segmentos/puntos/hechos
        return {'type': 'object', 'required': ['acciones', 'revision'],
                'properties': {'acciones': {**P['acciones'], 'minItems': 0},
                               'personajes': {'type': 'array', 'items': {'type': 'object', 'required': ['id', 'segmentos'],
                                                                         'properties': {'id': {'type': 'string'}, 'segmentos': seg}}},
                               'puntos': P.get('puntos') or {'type': 'array'}, 'hechos': P.get('hechos') or {'type': 'array'},
                               'avisos': {'type': 'array', 'items': {'type': 'string'}}, 'revision': P.get('revision') or {'type': 'array'}}}
    return {'type': 'object', 'required': ['tomas', 'revision'],
            'properties': {'tomas': {**(P.get('tomas') or {'type': 'array'}), 'minItems': 0},
                           'personajes': {'type': 'array', 'items': {'type': 'object', 'required': ['id', 'segmentos'],
                                                                     'properties': {'id': {'type': 'string'}, 'segmentos': seg}}},
                           'puntos': P.get('puntos') or {'type': 'array'}, 'avisos': {'type': 'array', 'items': {'type': 'string'}},
                           'revision': P.get('revision') or {'type': 'array'}}}


def _puntos_lista(p):
    if isinstance(p, dict): return [{'nombre': k, 'pos': v} for k, v in p.items()]
    return p or []


def prompt_reparacion(texto_fijo, S, fichas, obj, grupos, intento, esq, extra=None):
    """Prompt de reparación PARCIAL: plan aceptado (contexto, no se toca) + SOLO lo que falló + sus errores exactos.
    extra = bloques fijos que el 01 también le dio a Argon (p. ej. ACTION_VERBS / POSE_LIBRARY de accion_v1)."""
    if 'tomas' not in obj and 'acciones' in obj: return _prompt_reparacion_accion(texto_fijo, S, fichas, obj, grupos, intento, esq, extra)
    tomas = obj.get('tomas') or []
    malas = [t for t in tomas if str(t.get('id')) in grupos['tomas']]
    buenas = [{'id': t.get('id'), 't': t.get('t'), 'camara_molde': t.get('camara_molde'),
               'en_cuadro': (t.get('palabras') or {}).get('en_cuadro'),
               'lados': {x.get('id'): x.get('lado_pantalla') for x in (t.get('palabras') or {}).get('por_personaje') or []}}
              for t in tomas if str(t.get('id')) not in grupos['tomas']]
    pers_mal = [p for p in obj.get('personajes') or [] if str(p.get('id')) in grupos['personajes']]
    aceptado = {'duracion_s': obj.get('duracion_s'), 'fps': obj.get('fps'), 'puntos': _puntos_lista(obj.get('puntos')),
                'personajes': [{'id': p.get('id'), 'altura': p.get('altura'), 'segmentos': p.get('segmentos')} for p in obj.get('personajes') or []
                               if str(p.get('id')) not in grupos['personajes']],
                'tomas_aceptadas': buenas}
    fallo = {'tomas': malas, 'personajes': pers_mal, 'puntos_con_error': sorted(grupos['puntos'])}
    errores = {'tomas': grupos['tomas'], 'personajes': grupos['personajes'], 'puntos': grupos['puntos'], 'otros': grupos['otros']}
    set_min = {k: S.get(k) for k in ('mold', 'units', 'objects', 'floor_bounds', 'cameras', 'all_camera_names', 'camera_rule') if k in S}
    fich = [{k: f.get(k) for k in ('id', 'name', 'height_m', 'version', 'voice_only', 'group', 'filler') if f.get(k) is not None} for f in fichas]
    return (texto_fijo.replace('{INTENTO}', str(intento))
            + '\n\n=== THE_SET ===\n' + json.dumps(set_min, ensure_ascii=False, indent=1) + '\n=== END THE_SET ==='
            + '\n\n=== CHARACTERS ===\n' + json.dumps(fich, ensure_ascii=False, indent=1) + '\n=== END CHARACTERS ==='
            + '\n\n=== ACCEPTED_PLAN (do not change) ===\n' + json.dumps(aceptado, ensure_ascii=False, indent=1) + '\n=== END ACCEPTED_PLAN ==='
            + '\n\n=== FAILED_PARTS (fix only these) ===\n' + json.dumps(fallo, ensure_ascii=False, indent=1) + '\n=== END FAILED_PARTS ==='
            + '\n\n=== EXACT_ERRORS_FROM_THE_PROGRAM ===\n' + json.dumps(errores, ensure_ascii=False, indent=1) + '\n=== END EXACT_ERRORS ==='
            + '\n\nSCHEMA\n' + json.dumps(esq, ensure_ascii=False))


def _prompt_reparacion_accion(texto_fijo, S, fichas, obj, grupos, intento, esq, extra=None):
    """accion_v1: igual idea, sin cámaras: beats aceptados (contexto) + beats/segmentos/puntos/hechos que fallaron + errores exactos."""
    g = {k: grupos.get(k) or ({} if k != 'hechos' and k != 'otros' else []) for k in ('acciones', 'personajes', 'puntos', 'hechos', 'otros')}
    acc = [b for b in obj.get('acciones') or [] if isinstance(b, dict)]
    pers_mal = [p for p in obj.get('personajes') or [] if str(p.get('id')) in g['personajes']]
    aceptado = {'duracion_s': obj.get('duracion_s'), 'fps': obj.get('fps'), 'puntos': _puntos_lista(obj.get('puntos')),
                'personajes': [{'id': p.get('id'), 'altura': p.get('altura'), 'segmentos': p.get('segmentos')} for p in obj.get('personajes') or []
                               if str(p.get('id')) not in g['personajes']],
                'acciones_aceptadas': [b for b in acc if str(b.get('id')) not in g['acciones']]}
    if not g['hechos']: aceptado['hechos'] = obj.get('hechos') or []
    fallo = {'acciones': [b for b in acc if str(b.get('id')) in g['acciones']], 'personajes': pers_mal, 'puntos_con_error': sorted(g['puntos'])}
    if g['hechos']: fallo['hechos'] = obj.get('hechos') or []
    set_min = {k: S.get(k) for k in ('mold', 'units', 'objects', 'floor_bounds', 'scene_area_xy') if k in S}
    fich = [{k: f.get(k) for k in ('id', 'name', 'height_m', 'version', 'voice_only', 'group', 'filler') if f.get(k) is not None} for f in fichas]
    return (texto_fijo.replace('{INTENTO}', str(intento))
            + '\n\n=== THE_SET ===\n' + json.dumps(set_min, ensure_ascii=False, indent=1) + '\n=== END THE_SET ==='
            + '\n\n=== CHARACTERS ===\n' + json.dumps(fich, ensure_ascii=False, indent=1) + '\n=== END CHARACTERS ==='
            + ''.join(f'\n\n=== {k} ===\n' + json.dumps(v, ensure_ascii=False) + f'\n=== END {k} ===' for k, v in (extra or {}).items())
            + '\n\n=== ACCEPTED_PLAN (do not change) ===\n' + json.dumps(aceptado, ensure_ascii=False, indent=1) + '\n=== END ACCEPTED_PLAN ==='
            + '\n\n=== FAILED_PARTS (fix only these) ===\n' + json.dumps(fallo, ensure_ascii=False, indent=1) + '\n=== END FAILED_PARTS ==='
            + '\n\n=== EXACT_ERRORS_FROM_THE_PROGRAM ===\n' + json.dumps(g, ensure_ascii=False, indent=1) + '\n=== END EXACT_ERRORS ==='
            + '\n\nSCHEMA\n' + json.dumps(esq, ensure_ascii=False))


# ---------------------------------------------------------------- 3. CONSERVAR: fusionar
def fusionar(obj, rep):
    """Plan original + reparación → plan nuevo. Solo se reemplaza lo que vino en la reparación (por id / nombre)."""
    out = copy.deepcopy(obj); rep = rep or {}
    por_id = {str(t.get('id')): t for t in rep.get('tomas') or [] if isinstance(t, dict)}
    out['tomas'] = [copy.deepcopy(por_id.pop(str(t.get('id')))) if str(t.get('id')) in por_id else t for t in out.get('tomas') or []]
    for t in por_id.values(): out['tomas'].append(copy.deepcopy(t))   # una toma nueva (p. ej. partir una toma en dos)
    out['tomas'].sort(key=lambda t: float((t.get('t') or [0])[0] or 0))
    if not out['tomas'] and 'tomas' not in obj: out.pop('tomas')   # accion_v1: no inventar «tomas» vacías
    if rep.get('acciones') or 'acciones' in obj:                   # accion_v1: beats por id, igual que las tomas
        pa = {str(b.get('id')): b for b in rep.get('acciones') or [] if isinstance(b, dict)}
        out['acciones'] = [copy.deepcopy(pa.pop(str(b.get('id')))) if isinstance(b, dict) and str(b.get('id')) in pa else b for b in out.get('acciones') or []]
        out['acciones'] += [copy.deepcopy(b) for b in pa.values()]
        out['acciones'].sort(key=lambda b: float(((b.get('t') if isinstance(b, dict) else None) or [0])[0] or 0))
    if isinstance(rep.get('hechos'), list) and rep['hechos']: out['hechos'] = copy.deepcopy(rep['hechos'])
    pp = {str(p.get('id')): p for p in rep.get('personajes') or [] if isinstance(p, dict)}
    for p in out.get('personajes') or []:
        if str(p.get('id')) in pp: p['segmentos'] = copy.deepcopy(pp[str(p['id'])].get('segmentos') or p.get('segmentos'))
    if rep.get('puntos'):
        cur = {x['nombre']: x for x in _puntos_lista(out.get('puntos')) if isinstance(x, dict) and x.get('nombre')}
        for x in _puntos_lista(rep['puntos']):
            if isinstance(x, dict) and x.get('nombre'): cur[x['nombre']] = x
        out['puntos'] = list(cur.values())
    if rep.get('avisos'): out['avisos'] = list(out.get('avisos') or []) + [f'reparación: {a}' for a in rep['avisos']]
    if rep.get('revision'): out['revision_reparacion'] = rep['revision']
    return out


# ---------------------------------------------------------------- 4. LÍMITE + explicación simple
def _nombre(fichas, cid):
    f = next((x for x in fichas or [] if x.get('id') == cid), None)
    return (f or {}).get('name') or cid


def explicar(n, err, fichas, intentos, usd=None):
    """Error en español simple para Ricardo (sin jerga): qué toma falla, a quién no ve la cámara, qué decidir."""
    g = agrupar_errores(err, {'tomas': [], 'personajes': [{'id': f['id']} for f in fichas or []]})
    lineas = [f'La escena {n} sigue con {len(err)} problema(s) después de {intentos} reparación(es) automática(s)'
              + (f' (gastado en esta escena: US$ {usd})' if usd is not None else '') + '. No se guardó la dirección.']
    for tid, es in g['tomas'].items():
        quien = sorted({_nombre(fichas, m.group(1)) for x in es for m in [re.search(r'\.\s*([A-Za-z0-9_\-]+):', x)] if m})
        cam = sorted({m.group(1) for x in es for m in [re.search(r'(cam_[A-Za-z0-9_]+)', x)] if m})
        mot = []
        if any('no está entre las cámaras ofrecidas' in x for x in es): mot.append('la cámara elegida no está entre las permitidas para esta escena')
        if any('no lo ve' in x for x in es): mot.append('la cámara no ve a ' + ', '.join(quien))
        if any('palabras dicen' in x for x in es): mot.append('lo que dice que se ve no coincide con la cámara')
        tipo = '; '.join(mot) or 'otro problema: ' + es[0][:120]
        lineas.append(f'- Toma {tid}: {tipo}' + (f' ({", ".join(cam)})' if cam else '') + '.')
    for aid, es in (g.get('acciones') or {}).items(): lineas.append(f'- Beat {aid}: {es[0].split(": ", 1)[-1][:140]}' + (f' (y {len(es) - 1} más)' if len(es) > 1 else '') + '.')
    if g.get('hechos'): lineas.append(f'- Hechos para el historial: {g["hechos"][0][:140]}.')
    for cid, es in g['personajes'].items(): lineas.append(f'- {_nombre(fichas, cid)}: sus movimientos tienen {len(es)} problema(s) (posiciones o tiempos).')
    if g['puntos']: lineas.append(f'- Puntos del set mal puestos: {", ".join(sorted(g["puntos"]))}.')
    for x in g['otros'][:3]: lineas.append(f'- Otro: {x[:160]}')
    if g.get('acciones') and not g['tomas']:   # accion_v1: el 01 no tiene cámaras
        lineas.append('Qué puedes decidir: (1) aprobar 1 reparación más, (2) pedir la escena entera de nuevo, o (3) corregir a mano los beats que fallan.')
    else:
        lineas.append('Qué puedes decidir: (1) aprobar 1 reparación más, (2) pedir la escena entera de nuevo, '
                      '(3) agregar una cámara para esta escena en el molde, o (4) aceptar la escena sin las tomas que fallan.')
    return '\n'.join(lineas)


def bucle(validar, n, obj, err, llamar, armar_prompt, max_rep=None, fichas=None):
    """validar(obj) -> (C, errores) · llamar(prompt, intento) -> (respuesta_dict | None, info) · armar_prompt(obj, grupos, intento) -> str.
    Devuelve {'ok', 'C', 'obj', 'intentos': [...], 'explicacion'}. No llama a nada pago por su cuenta."""
    max_rep = ajustes_01()['reparaciones_max'] if max_rep is None else int(max_rep)
    hist = []; cur = obj; C = None
    for k in range(1, max_rep + 1):
        g = agrupar_errores(err, cur)
        prompt = armar_prompt(cur, g, k)
        rep, info = llamar(prompt, k)
        h = {'intento': k, 'tomas_pedidas': sorted(g['tomas']), 'acciones_pedidas': sorted(g.get('acciones') or {}), 'personajes_pedidos': sorted(g['personajes']), 'errores_antes': len(err), **(info or {})}
        if not isinstance(rep, dict):
            h['resultado'] = 'sin respuesta usable'; hist.append(h)
            if (info or {}).get('parar'): break
            continue
        nuevo = fusionar(cur, rep); C, e2 = validar(copy.deepcopy(nuevo))
        h.update({'errores_despues': len(e2), 'resultado': 'ok' if not e2 else 'sigue con errores'}); hist.append(h)
        cur, err = nuevo, e2
        if not e2: return {'ok': True, 'C': C, 'obj': cur, 'intentos': hist, 'explicacion': None}
    usd = round(sum(float(x.get('usd') or 0) for x in hist), 4) if any('usd' in x for x in hist) else None
    ex = explicar(n, err, fichas, sum(1 for x in hist if 'errores_despues' in x), usd)
    paro = next((x.get('por_que') for x in reversed(hist) if x.get('por_que')), None)
    if paro: ex += '\nSe paró antes de terminar: ' + str(paro)
    return {'ok': False, 'C': None, 'obj': cur, 'errores': err, 'intentos': hist, 'explicacion': ex}
