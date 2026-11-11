#!/usr/bin/env python3
"""paso00_resolver — caja «4r. Resolver dudas» (orden t340u/t341u, Ricardo 3-nov-2026). GENÉRICO para cualquier canal.

Junta TODAS las dudas, contradicciones y faltantes que dejaron los pasos del 00 (base, 2a, 2b, 2c, 4a1, 4b1, 4c1, 4a4…)
y arma UNA decisión automática por cada una, según: 1) GÉNERO y reglas del canal, 2) la HISTORIA (guion + 4P),
3) el DRAMATISMO de la escena donde pasa. La cadena NUNCA se detiene a esperar a un humano: lo que sería un
«bloqueante» también se decide (el mejor valor por defecto dramático) y queda solo REGISTRADO para revisión.

  paso00_cadena resolver cotizar --canal C --capitulo N [--pasos a,b] [--corrida ID]   GRATIS, sin red: arma pedidos + peor caso US$
  paso00_cadena resolver aplicar --canal C --capitulo N [--respuesta F …]              GRATIS, sin red: aplica decisiones (o la regla
                                                                                         por defecto del código si falta una) → <paso>.resuelto.json
  paso00_cadena resolver correr  …                                                      PAGO (t348u): solo con HABILITAR_PAGO_00 pasos=4r, --ok y --aprobado

Salida aplicada: respuestas/<paso>.resuelto.json (la original nunca se pisa) + resultados/resolver_dudas.json.
paso00_cadena.archivo_resp usa <paso>.resuelto.json SOLO si se hizo sobre el MISMO archivo de origen (sha) — si el paso se
vuelve a correr, la resolución vieja deja de valer sola.
"""
import json, re, hashlib, time, argparse, copy
from pathlib import Path
import paso00_cadena as C

PASOS_DEF = ['base', 'escenarios', 'objetos', 'personajes', 'inv_escenarios', 'inv_obj_historia', 'inv_obj_lugar', 'prompts_escenarios']
TIPOS = ('dudas', 'contradicciones', 'faltantes_en_base')
CRITERIOS = ['genero_canal', 'historia', 'dramatismo', 'continuidad', 'regla_canal', 'por_defecto']
FUENTES = ['guion', '4p_base', 'paso', 'config_canal', 'deducido']
RIESGO = ['bajo', 'medio', 'alto']
CLAVES_GENERO =[REDACTED]
                           r'regla|valores|idioma|language|clima_prohibido|moral|mensaje|ritmo', re.I)

def cfg():
    try: d = json.loads(C.LS.CONFIG_LLAMADAS.read_text(encoding='utf-8')).get('resolver_dudas') or {}
    except Exception: d = {}
    return {'pasos': d.get('pasos') or PASOS_DEF, 'max_dudas_por_llamada': int(d.get('max_dudas_por_llamada') or 25),
            'max_out': int(d.get('max_out') or 16384), 'chars_genero': int(d.get('chars_genero') or 6000),
            'chars_escena': int(d.get('chars_escena') or 2500), 'chars_registro': int(d.get('chars_registro') or 1200)}

def sha(t): return hashlib.sha256(t if isinstance(t, bytes) else t.encode('utf-8')).hexdigest()
def _txt(x): return x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, sort_keys=True)

def recolectar(D, pasos):
    """Una entrada por duda/contradicción/faltante de cada paso que exista (canónico, ya unido). id estable por contenido."""
    out, fuentes = [], {}
    for p in pasos:
        f = C.archivo_resp(D, p, resuelto=False)
        if not f.is_file(): continue
        try: j = json.loads(f.read_text(encoding='utf-8'))
        except Exception: continue
        fuentes[p] = {'archivo': f.name, 'sha': sha(f.read_bytes())}
        for t in TIPOS:
            for i, v in enumerate(j.get(t) or []):
                if v in (None, '', {}): continue
                tx = _txt(v)
                out.append({'duda_id': 'd-' + sha(f'{p}|{t}|{tx}')[:10], 'paso': p, 'tipo': t, 'indice': i, 'texto': tx,
                            'escenas': sorted({n for m in re.findall(r'[Ee]scenas?\s+((?:\d+(?:\s*,\s*|\s+y\s+|\s+e\s+)?)+)', tx) for n in re.findall(r'\d+', m)}, key=int),
                            'ids': sorted(set(re.findall(r'\b(?:esc|obj|ch|var)-[a-z0-9-]+', tx)))})
    return out, fuentes

def genero_canal(X, n):
    """Todo lo del canal que habla de género, tono, público, reglas y estilo (por NOMBRE de campo, sin conocer ningún canal)."""
    sal = {}
    def rec(d, pre=''):
        if isinstance(d, dict):
            for k, v in d.items():
                if CLAVES_GENERO.search(str(k)) and v not in (None, '', [], {}): sal[pre + str(k)] = v
                elif isinstance(v, dict): rec(v, pre + str(k) + '.')
    rec(X.get('canal_data') or {}); rec(X.get('cfg') or {}, 'config.')
    for k in [k for k in sal if re.search(r'styl|estilo', k, re.I)]: sal.pop(k)   # t342u: el estilo NUNCA sale de un campo adivinado
    t = json.dumps(sal, ensure_ascii=False)
    return t[:n] + ('…' if len(t) > n else '')

def estilo_vigente(X):
    """t342u: estilo VIGENTE = el sello de estilo aprobado del canal (style_fijo, misma fuente que 4a4 y el SELLO ESTILO), por
    paso00_cadena.estilo_canal. Sin sello aprobado → error registrado; nunca se inventa ni se usa un valor por defecto."""
    try: e = C.estilo_canal(X)
    except Exception as ex: return None, f'no se pudo leer el sello de estilo: {type(ex).__name__}: {str(ex)[:200]}'
    if not e or not (e.get('style_fijo') or {}).get('descripcion_en'): return None, 'ERROR: el canal no tiene sello de estilo aprobado (style_fijo); 4r no inventa estilo'
    sf = e['style_fijo']
    return {'nombre': sf.get('nombre'), 'descripcion_en': sf.get('descripcion_en'), 'negativo': sf.get('negativo'), 'imagen_sello': sf.get('imagen'),
            'origen': e.get('origen_texto'), 'avisos': e.get('avisos') or []}, None

def escenas_guion(g):
    """Texto del guion por escena (encabezados ESCENA N / PRÓLOGO…, igual criterio que myia_paso00)."""
    g = g if isinstance(g, str) else _txt(g)
    partes, cur, buf = {}, None, []
    for l in g.split('\n'):
        m = re.match(r'^\s*#*\s*\**\s*ESCENA\s+(\d+)', l, re.I)
        if m:
            if cur: partes[cur] = '\n'.join(buf)
            cur, buf = m.group(1), [l]
        elif cur: buf.append(l)
    if cur: partes[cur] = '\n'.join(buf)
    return partes

def ficha_escena(base, gesc, num, n):
    e = next((x for x in (base.get('escenas') or []) if str(x.get('numero')) == str(num)), {}) or {}
    v = lambda k: (e.get(k) or {}).get('valor') if isinstance(e.get(k), dict) else e.get(k)
    head = f"ESCENA {num} · {e.get('titulo', '')} · escenario {e.get('escenario_id')} · {v('int_ext')} · hora {v('hora')} · clima {v('clima')}"
    tx = gesc.get(str(num)) or ' / '.join(s.get('cita', '') for s in (e.get('sets') or []))
    return head + '\n' + tx[:n] + ('…' if len(tx) > n else '')

def registros_citados(D, item, n):
    """Lo que el paso dejó sobre los ids citados en la duda (para que la decisión sea concreta)."""
    f = C.archivo_resp(D, item['paso'], resuelto=False)
    try: j = json.loads(f.read_text(encoding='utf-8'))
    except Exception: return ''
    sal = []
    for clave in ('escenarios', 'objetos', 'personajes'):
        for r in (j.get(clave) or []):
            rid = next((r.get(k) for k in ('escenario_id', 'objeto_id', 'personaje_id', 'id') if isinstance(r, dict) and r.get(k)), None)
            if rid in item['ids']: sal.append(f'{rid}: ' + json.dumps(r, ensure_ascii=False)[:n])
    return '\n'.join(sal[:3])

FIJO = """TAREA (paso 4r · resolver dudas, MYIA). Eres el director/guionista del canal. Los pasos anteriores dejaron DUDAS, CONTRADICCIONES
y FALTANTES. La producción es AUTOMÁTICA y NUNCA se detiene a preguntar: tienes que DECIDIR cada una, sin excepción.

CÓMO DECIDES (en este orden de prioridad):
1. GÉNERO Y REGLAS DEL CANAL (GENERO_CANAL_JSON): público, edad, tono, estilo, cosas prohibidas. Nunca decidas algo que lo rompa.
2. LA HISTORIA (guion de la escena + 4P): lo que el guion dice o implica manda; respeta la continuidad entre escenas.
3. EL DRAMATISMO DE LA ESCENA: identifica su función (gancho, conflicto, giro, clímax, resolución, cierre) y elige lo que MÁS
   sirve a esa emoción y a la claridad para el público del canal (lo legible, lo que se entiende en pantalla, lo que remata el momento).
4. Si nada de eso decide: el valor por defecto más simple y coherente con escenas vecinas (criterio "por_defecto").

REGLAS
- Una decisión por cada duda_id de la lista (todas; ni una más, ni una menos). "decision" = qué se hace, concreto y ejecutable.
- "justificacion" corta (≤ 2 frases) y "cita" literal del guion/4P/canal si existe (si no, "").
- "riesgo": bajo = detalle visual/continuidad; medio = cambia algo que se ve en pantalla; alto = cambia la historia. Aun en "alto" decides.
- "cambios": SOLO si la decisión cambia un dato del paso: ruta JSON Pointer dentro de la salida de ESE paso (p. ej.
  /escenarios/0/objetos_del_lugar_posicion/3/escenas) y "valor_json" (el valor nuevo en JSON). Si no hay que cambiar datos, [].
  Nunca inventes ids nuevos; nunca borres registros.
- Lo que no tiene respuesta en ningún lado NO se deja abierto: decide lo mejor para la escena y márcalo criterio "por_defecto".
"""

def esquema(ids):
    return {'type': 'object', 'required': ['decisiones'], 'properties': {
        'decisiones': {'type': 'array', 'minItems': len(ids), 'maxItems': len(ids), 'items': {'type': 'object',
            'required': ['duda_id', 'decision', 'justificacion', 'criterio', 'fuente', 'cita', 'riesgo', 'funcion_dramatica', 'cambios'],
            'properties': {'duda_id': {'type': 'string', 'enum': ids}, 'decision': {'type': 'string'}, 'justificacion': {'type': 'string'},
                           'criterio': {'type': 'string', 'enum': CRITERIOS}, 'fuente': {'type': 'string', 'enum': FUENTES},
                           'cita': {'type': 'string'}, 'riesgo': {'type': 'string', 'enum': RIESGO}, 'funcion_dramatica': {'type': 'string'},
                           'cambios': {'type': 'array', 'items': {'type': 'object', 'required': ['ruta', 'valor_json'],
                                       'properties': {'ruta': {'type': 'string'}, 'valor_json': {'type': 'string'}}}}}}},
        'notas': {'type': 'string'}}}

def esquema_api(ids):
    """t348u: esquema que va a la API. Orden 88: con más de max_items_exactos objetos, minItems/maxItems dan 400 INVALID_ARGUMENT
    (sin cobro). El conteo va en la descripción y lo cumple el CÓDIGO: «aplicar» decide por defecto lo que falte."""
    e = esquema(ids); d = e['properties']['decisiones']
    if len(ids) > C.tope_items_exactos(): d.pop('minItems'); d.pop('maxItems')   # sin texto extra: el pedido ya lista cada duda_id
    return e

def contar_props(s):
    n = 0
    def rec(x):
        nonlocal n
        if isinstance(x, dict):
            if isinstance(x.get('properties'), dict): n += len(x['properties'])
            for v in x.values(): rec(v)
        elif isinstance(x, list):
            for v in x: rec(v)
    rec(s); return n

def armar(X, c):
    D = X['D']; base = C._leer_resp(X['P'], D, 'base') or {}
    items, fuentes = recolectar(D, c['pasos'])
    gesc = escenas_guion(X.get('g') or '')
    gen = genero_canal(X, c['chars_genero'])
    est, est_err = estilo_vigente(X)
    X['_estilo_4r'] = (est, est_err)
    lotes = [items[i:i + c['max_dudas_por_llamada']] for i in range(0, len(items), c['max_dudas_por_llamada'])]
    pedidos = []
    for k, lote in enumerate(lotes, 1):
        escs = sorted({e for it in lote for e in it['escenas']}, key=int) or sorted({str(e.get('numero')) for e in base.get('escenas') or []}, key=lambda z: int(z) if z.isdigit() else 999)
        bloques = [FIJO, '=== GENERO_CANAL_JSON ===', gen, '=== FIN ===', '=== ESTILO_VIGENTE_DEL_CANAL (sello aprobado; manda sobre cualquier otro dato de estilo) ===',
                   json.dumps(est, ensure_ascii=False) if est else est_err, '=== FIN ===', '=== ESCENAS (guion + 4P, con su función dramática a deducir) ===']
        bloques += [ficha_escena(base, gesc, e, c['chars_escena']) for e in escs]
        bloques += ['=== FIN ===', '=== DUDAS A DECIDIR ===']
        for it in lote:
            bloques.append(json.dumps({k_: it[k_] for k_ in ('duda_id', 'paso', 'tipo', 'texto', 'escenas', 'ids')}, ensure_ascii=False))
            rc = registros_citados(D, it, c['chars_registro'])
            if rc: bloques.append('  datos actuales del paso: ' + rc)
        bloques.append('=== FIN ===')
        pr = '\n'.join(bloques); esq = esquema_api([it['duda_id'] for it in lote])
        est = round(X['AR'].estimar(len(pr) + len(json.dumps(esq)), max_out=c['max_out'], modelo=X['modelo']), 4)
        nom = f'resolver_dudas_g{k}de{len(lotes)}'
        (D / 'pedidos' / f'{nom}.txt').write_text(pr, encoding='utf-8')
        (D / 'pedidos' / f'{nom}.esquema.json').write_text(json.dumps(esq, ensure_ascii=False, indent=1), encoding='utf-8')
        pedidos.append({'paso': nom, 'dudas': len(lote), 'escenas': escs, 'chars': len(pr), 'propiedades_esquema': contar_props(esq),
                        'max_out': c['max_out'], 'peor_caso_usd': est, 'cabe_en_tope': est <= C.TOPE_LLAMADA + 1e-9, '_pr': pr, '_esq': esq})
    return items, fuentes, pedidos

def cmd_cotizar(a):
    X = C.preparar(a, pagar=False); c = cfg()
    try:
        if a.pasos: c['pasos'] = a.pasos.split(',')
        items, fuentes, pedidos = armar(X, c)
        (X['D'] / 'resultados').mkdir(exist_ok=True)
        r = {'ok': True, 'accion': 'resolver_cotizar', 'canal': a.canal, 'capitulo': int(X['e']['number']), 'gratis': True,
             'dudas_total': len(items), 'por_paso': {p: sum(1 for i in items if i['paso'] == p) for p in fuentes},
             'por_tipo': {t: sum(1 for i in items if i['tipo'] == t) for t in TIPOS}, 'pedidos': C.publico(pedidos),
             'total_peor_caso_usd': round(sum(p['peor_caso_usd'] for p in pedidos), 4), 'tope_por_llamada_usd': C.TOPE_LLAMADA,
             'estilo_vigente': {k: v for k, v in (X['_estilo_4r'][0] or {}).items() if k != 'descripcion_en'} or None, 'estilo_error': X['_estilo_4r'][1],
             'modelo': f"{X['modelo']} {X['nivel']}", 'fuentes': fuentes, 'carpeta': str(X['D']), 'hora': C.ahora(),
             'nota': 'la cadena no espera a nadie: con o sin respuesta del modelo, «aplicar» decide todo (por defecto del código si falta)'}
        (X['D'] / 'resultados' / 'cotizacion_resolver_dudas.json').write_text(json.dumps(r, ensure_ascii=False, indent=1))
        (X['D'] / 'respuestas' / 'resolver_dudas_lista.json').write_text(json.dumps({'items': items, 'fuentes': fuentes}, ensure_ascii=False, indent=1))
        return r
    finally:
        import os, shutil
        if not os.environ.get('TALLER_DATOS'): shutil.rmtree(X['T'], ignore_errors=True)

def _puntero(obj, ruta):
    if not ruta.startswith('/'): raise ValueError('ruta no es JSON Pointer')
    partes = [p.replace('~1', '/').replace('~0', '~') for p in ruta[1:].split('/')]
    cur = obj
    for p in partes[:-1]:
        cur = cur[int(p)] if isinstance(cur, list) else cur[p]
    return cur, partes[-1]

def aplicar_cambio(doc, ruta, valor):
    """Solo reemplaza un valor QUE YA EXISTE y del mismo tipo (no crea claves, no borra registros, no toca ids)."""
    padre, k = _puntero(doc, ruta)
    if isinstance(padre, list): k = int(k); viejo = padre[k]
    else:
        if k not in padre: raise ValueError('la clave no existe')
        viejo = padre[k]
    if re.search(r'(^|_)id$', str(k)): raise ValueError('no se cambian ids')
    if type(viejo) is not type(valor) and not (isinstance(viejo, (int, float)) and isinstance(valor, (int, float))) and viejo is not None:
        raise ValueError(f'tipo distinto ({type(viejo).__name__} → {type(valor).__name__})')
    padre[k] = valor
    return viejo

def defecto(it):
    """Regla del CÓDIGO cuando el modelo no respondió esa duda: se conserva lo que el paso ya decidió (su suposición queda como decisión)."""
    return {'duda_id': it['duda_id'], 'decision': 'Se conserva lo que el paso ya dejó en sus datos (suposición del paso = decisión).',
            'justificacion': 'Sin respuesta del resolver para esta duda; la cadena no se detiene.', 'criterio': 'por_defecto',
            'fuente': 'paso', 'cita': '', 'riesgo': 'bajo', 'funcion_dramatica': '', 'cambios': [], 'origen': 'codigo'}

def aplicar(D, respuestas):
    L = json.loads((D / 'respuestas' / 'resolver_dudas_lista.json').read_text(encoding='utf-8'))
    items, fuentes = L['items'], L['fuentes']
    dec = {}
    for f in respuestas:
        try: j = json.loads(Path(f).read_text(encoding='utf-8'))
        except Exception: continue
        for d in (j.get('decisiones') or []):
            if isinstance(d, dict) and d.get('duda_id'): dec.setdefault(d['duda_id'], dict(d, origen='modelo'))
    docs, reg = {}, []
    for it in items:
        d = dec.get(it['duda_id']) or defecto(it)
        if d.get('criterio') not in CRITERIOS: d['criterio'] = 'por_defecto'
        if d.get('riesgo') not in RIESGO: d['riesgo'] = 'alto'
        p = it['paso']
        if p not in docs:
            f = C.archivo_resp(D, p, resuelto=False); docs[p] = json.loads(f.read_text(encoding='utf-8'))
        aplicados, rechazados = [], []
        for cb in d.get('cambios') or []:
            try:
                val = json.loads(cb['valor_json']) if isinstance(cb.get('valor_json'), str) else cb.get('valor_json')
                viejo = aplicar_cambio(docs[p], cb['ruta'], val); aplicados.append({'ruta': cb['ruta'], 'antes': viejo, 'ahora': val})
            except Exception as e: rechazados.append({'ruta': cb.get('ruta'), 'motivo': str(e)[:200]})
        reg.append({**{k: it[k] for k in ('duda_id', 'paso', 'tipo', 'texto')}, **{k: d.get(k) for k in ('decision', 'justificacion', 'criterio', 'fuente', 'cita', 'riesgo', 'funcion_dramatica', 'origen')},
                    'cambios_aplicados': aplicados, 'cambios_rechazados': rechazados, 'revisar_despues': d.get('riesgo') == 'alto' or bool(rechazados)})
    hora = C.ahora()
    for p, doc in docs.items():
        mias = [r for r in reg if r['paso'] == p]
        doc['_resolucion'] = {'paso': '4r', 'fuente_archivo': fuentes[p]['archivo'], 'fuente_sha': fuentes[p]['sha'], 'hora': hora,
                              'decisiones': len(mias), 'abiertas': 0}
        for t in TIPOS:
            if doc.get(t): doc[t + '_resueltas'] = [r for r in mias if r['tipo'] == t]; doc[t] = []
        (D / 'respuestas' / f'{p}.resuelto.json').write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')
    res = {'ok': True, 'accion': 'resolver_aplicar', 'gratis': True, 'decisiones': len(reg), 'del_modelo': sum(1 for r in reg if r['origen'] == 'modelo'),
           'por_defecto_codigo': sum(1 for r in reg if r['origen'] == 'codigo'), 'abiertas': 0,
           'cambios_aplicados': sum(len(r['cambios_aplicados']) for r in reg), 'cambios_rechazados': sum(len(r['cambios_rechazados']) for r in reg),
           'para_revisar_despues': [r['duda_id'] for r in reg if r['revisar_despues']], 'pasos_resueltos': sorted(docs), 'hora': hora, 'registro': reg}
    (D / 'resultados' / 'resolver_dudas.json').write_text(json.dumps(res, ensure_ascii=False, indent=1))
    return {k: v for k, v in res.items() if k != 'registro'}

def esquema_fijo():
    """t348u: parte FIJA declarada del 4r (igual para todos los lotes): el esquema sin la lista de ids ni el conteo.
    Al API va el esquema del lote (enum de ids + conteo exacto); la revisión local usa este, genérico."""
    e = esquema(['x']); d = e['properties']['decisiones']
    d.pop('minItems'); d.pop('maxItems'); d['items']['properties']['duda_id'] = {'type': 'string'}
    return e

def fijo_4r(X, c):
    partes = {'texto': FIJO, 'rotulos_bloques': ROTULOS, 'esquema': json.dumps(esquema_fijo(), ensure_ascii=False, sort_keys=True),
              'modelo': X['modelo'], 'nivel': X['nivel'], 'max_out': c['max_out'], 'max_rondas': 1, 'json_out': True,
              'json_schema_api': 'response_json_schema'}
    return {'paso': f'taller00_{C.VER}_4r_resolver', 'partes': partes, 'fragmentos': [FIJO]}

ROTULOS = '=== GENERO_CANAL_JSON ===|=== ESTILO_VIGENTE_DEL_CANAL|=== ESCENAS|=== DUDAS A DECIDIR ===|=== FIN ==='

def _correr_par(a, X, pedidos, fijo, c, tope, n):
    """t358u: los grupos de dudas son independientes → a la vez (máx n, ranuras compartidas entre procesos). Tope atómico (PC.Bolsa):
    se reserva el peor caso de todos antes de lanzar; ledger antes de cada intento (myia_argon.llamar, con candado)."""
    bolsa = C.PC.Bolsa(a.ok)
    if not bolsa.reservar(sum(p['peor_caso_usd'] for p in pedidos)):
        return [{'paso': p['paso'], 'estado': 'no_llamado', 'motivo': f'peor caso total pasa {a.ok}'} for p in pedidos]
    def fn(p):
        est = p['peor_caso_usd']; extra = bolsa.extra(est)
        x = {'paso': p['paso'], '_pr': p['_pr'], '_fijo': fijo, 'peor_caso_usd': est, '_esquema': p['_esq'], '_max_out': c['max_out'], 'ids': None, 'prueba': '4r'}
        try:
            with C.PC.ranura('argon', C.TRABAJO / '_ranuras'): r = C.llamar_uno(a, X, x, tope, limite=round(est + extra, 6))
        except Exception as exc: r = {'paso': p['paso'], 'estado': 'error', 'error': f'{type(exc).__name__}: {str(exc)[:300]}'}
        bolsa.asentar(est + extra, float(r.get('usd_real') or 0) + float(r.get('usd_posible_cobro') or 0))
        return {k: r.get(k) for k in ('paso', 'estado', 'id', 'usd_real', 'usd_posible_cobro', 'tokens_entrada', 'tokens_salida', 'fin', 'error', 'motivo', 'esquema_errores')}
    return [r for _, r, _, _ in C.PC.correr_paralelo(pedidos, fn, n)]   # 4r nunca detiene la cadena: corren todos

def cmd_correr(a):
    """t348u: PAGO. Solo con compuerta HABILITAR_PAGO_00 que incluya pasos=4r (y canal/capítulo/monto); ledger antes de cada llamada
    (lo hace myia_argon.llamar vía C.llamar_uno). Si el peor caso total pasa --ok o el tope, no llama a nada."""
    import os, shutil
    if a.ok is None or not a.aprobado: return {'ok': False, 'error': 'falta --ok (precio aprobado) y --aprobado (quién aprobó)', 'llamadas_hechas': 0}
    a.caja = 'resolver_dudas'
    g = C.compuerta_00(a)
    if g: return {'ok': False, 'error': g, 'llamadas_hechas': 0}
    X = C.preparar(a, pagar=True); c = cfg(); C.PC.blindar_ledger(X['AR'], C.LEDGER)   # t358u
    try:
        if a.pasos: c['pasos'] = a.pasos.split(',')
        items, fuentes, pedidos = armar(X, c)
        (X['D'] / 'resultados').mkdir(exist_ok=True)
        (X['D'] / 'respuestas' / 'resolver_dudas_lista.json').write_text(json.dumps({'items': items, 'fuentes': fuentes}, ensure_ascii=False, indent=1))
        tc = X['AR'].tope_de_canal(X['cfg']); tope = C.TOPE_LLAMADA if tc is None else min(C.TOPE_LLAMADA, tc)
        total = round(sum(p['peor_caso_usd'] for p in pedidos), 4)
        if any(p['peor_caso_usd'] > tope + 1e-9 for p in pedidos) or total > a.ok + 1e-9:
            return {'ok': False, 'error': f'peor caso {total} pasa lo aprobado {a.ok} o un pedido pasa el tope {tope}', 'pedidos': C.publico(pedidos), 'llamadas_hechas': 0}
        fijo = fijo_4r(X, c); C.registrar_taller(fijo, X['FP'], X['F'])
        for f in (X['D'] / 'respuestas').glob('resolver_dudas_g*.json'):   # respuestas viejas de otro armado: se archivan (no se borran)
            (X['D'] / 'archivo').mkdir(exist_ok=True); shutil.move(str(f), str(X['D'] / 'archivo' / f'{f.stem}.{time.strftime("%Y%m%d-%H%M%S")}.json'))
        n_par = C.PC.max_a_la_vez('argon') if C.PC.activo() and len(pedidos) > 1 else 1   # t358u: grupos de dudas a la vez
        res, gast = (_correr_par(a, X, pedidos, fijo, c, tope, n_par) if n_par > 1 else []), 0.0
        for p in (pedidos if n_par <= 1 else []):
            limite = round(a.ok - gast, 4)
            if p['peor_caso_usd'] > limite + 1e-9:
                res.append({'paso': p['paso'], 'estado': 'no_llamado', 'motivo': f'quedan {limite} de {a.ok}'}); continue
            x = {'paso': p['paso'], '_pr': p['_pr'], '_fijo': fijo, 'peor_caso_usd': p['peor_caso_usd'], '_esquema': p['_esq'],
                 '_max_out': c['max_out'], 'ids': None, 'prueba': '4r'}
            r = C.llamar_uno(a, X, x, tope, limite=limite)
            gast += float(r.get('usd_real') or 0) + float(r.get('usd_posible_cobro') or 0)
            res.append({k: r.get(k) for k in ('paso', 'estado', 'id', 'usd_real', 'usd_posible_cobro', 'tokens_entrada', 'tokens_salida', 'fin', 'error', 'motivo', 'esquema_errores')})
        return {'ok': all(z['estado'] in ('ok', 'reparado') for z in res), 'accion': 'resolver_correr', 'dudas_total': len(items),
                'peor_caso_usd': total, 'usd_real': round(sum(float(z.get('usd_real') or 0) for z in res), 4), 'pedidos': res, 'hora': C.ahora()}
    finally:
        if not os.environ.get('TALLER_DATOS'): shutil.rmtree(X['T'], ignore_errors=True)

def carpeta_cap(canal, capitulo):
    pat = f'cap*_{capitulo}' if str(capitulo).startswith('ep-') else f'cap{int(capitulo):02d}_ep-*'
    return next(iter(sorted((C.TRABAJO / canal).glob(pat))), None)

def main(argv):
    ap = argparse.ArgumentParser(prog='resolver'); ap.add_argument('accion', choices=['cotizar', 'aplicar', 'correr'])
    ap.add_argument('--canal', required=True); ap.add_argument('--capitulo', required=True); ap.add_argument('--corrida', default=None)
    ap.add_argument('--pasos', default=None); ap.add_argument('--respuesta', action='append', default=[])
    ap.add_argument('--ok', type=float, default=None); ap.add_argument('--aprobado', default=None); ap.add_argument('--max-intentos', dest='max_intentos', type=int, default=None)
    a = ap.parse_args(argv)
    if not re.fullmatch(r'cn-[a-z0-9-]+', a.canal) or not re.fullmatch(r'(ep-[a-z0-9]+|\d{1,3})', a.capitulo): return {'ok': False, 'error': 'canal o capítulo no válido'}
    if a.accion == 'cotizar': return cmd_cotizar(a)
    if a.accion == 'correr': return cmd_correr(a)   # t348u: pago solo con HABILITAR_PAGO_00 (pasos=4r)
    D = carpeta_cap(a.canal, a.capitulo)
    if not D or not (D / 'respuestas' / 'resolver_dudas_lista.json').is_file(): return {'ok': False, 'error': 'primero «resolver cotizar» (arma la lista)'}
    resp = a.respuesta or sorted(str(f) for f in (D / 'respuestas').glob('resolver_dudas_g*.json'))
    for f in resp:
        if not str(Path(f).resolve()).startswith(str(D.resolve())): return {'ok': False, 'error': 'respuesta fuera de la carpeta del capítulo'}
    return aplicar(D, resp)
