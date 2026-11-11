#!/usr/bin/env python3
"""PISTA INMI (2026-10-29): orden 83 — cubo 01 «Argon dirige cada escena» (plan de tomas), genérico (regla 6).
Por escena arma UN pedido a Argon (prompts_01/dirigir_escena.txt, en inglés) con:
  · THE_SET: el MISMO molde de Blender que usa el 02 para esa escena (escenario_id de base.json): nombre y caja (min/max) de cada
    objeto, el área del suelo y las cámaras del molde (loc, dirección, lente). Argon pone todo en ESAS coordenadas.
  · CHARACTERS: los personajes en cuadro, con su versión de esa escena (personajes.json: forma, descripción) y sus referencias
    frente/espalda (personajes.refs_para, solo lectura) adjuntas como imágenes.
  · SCENE / SCRIPT / FORMAT: la escena del mapa, el guion y el formato del canal.
Por defecto SOLO cotiza. Con --correr (guarda HABILITAR_PAGO_01 + --ok + --aprobado) llama; la respuesta se valida con el código
(ids de personajes de la escena, posiciones dentro del suelo del molde, cámaras que existen en el molde, tiempos, contrato del 02)
y, si pasa, se escribe cubos/01/esc_N.json (si había un plan importado, se respalda antes en cubos/01/respaldos/ y se reemplaza)."""
import json, time
from pathlib import Path

import paso01_pago as PG


def _cfg(): return PG.ajustes()['01']


def escenario(K, M, n, eid, avisos):
    med = (M or {}).get('medidas') or {}
    objs = [{'name': k, 'min': v.get('min'), 'max': v.get('max')} for k, v in sorted(med.items()) if isinstance(v, dict) and v.get('min') and v.get('max')]
    if objs:
        lim = {'x': [min(o['min'][0] for o in objs), max(o['max'][0] for o in objs)], 'y': [min(o['min'][1] for o in objs), max(o['max'][1] for o in objs)],
               'z_floor': min(o['min'][2] for o in objs), 'z_top': max(o['max'][2] for o in objs)}
    else: lim = None
    cams = [{'name': c['nombre'], 'loc': c.get('loc'), 'direction': c.get('dir'), 'up': c.get('arriba'), 'lens_mm': c.get('lente_mm'),
             'sensor_width_mm': c.get('sensor_ancho_mm')} for c in K.camaras_de_escena(M, n, eid, avisos)]
    return {'mold': str(eid), 'units': 'metres, z up', 'objects': objs, 'floor_bounds': lim, 'cameras': cams,
            'all_camera_names': [c['nombre'] for c in (M or {}).get('camaras_molde') or []]}


def personajes_escena(K, D, a, e, PC, avisos):
    """Versión de cada personaje en la escena + referencias frente/espalda (solo lectura de personajes.py)."""
    cf = _cfg(); fichas, imgs, det = [], [], []
    for cid in e['personajes']:
        p = PC.get(cid) or {}
        fichas.append({'id': cid, 'name': p.get('nombre') or cid, 'height_m': K._num(p.get('altura')) if p.get('altura') else None, 'version': None, 'images': []})
    try:
        import personajes as PJ
        for lado in cf['lados_refs']:
            r = PJ.refs_para(a.canal, D, e['numero'], lado=lado)
            det += r.get('detener') or []
            for gid, gx in (r.get('grupos') or {}).items():   # orden 85: un GRUPO del guion → una ficha por miembro (cada uno se pone en cuadro)
                i = next((k for k, x in enumerate(fichas) if x['id'] == gid), None)
                if i is None: continue
                nuevas = [{'id': mb['id'], 'name': mb['nombre'], 'height_m': None, 'version': None, 'images': [], 'group': fichas[i]['name']}
                          for mb in gx.get('miembros') or [] if not any(x['id'] == mb['id'] for x in fichas)]
                fichas[i:i + 1] = nuevas
            for u in r.get('solo_voz') or []:   # orden 88: solo se oye → nunca en cuadro, sin imagen
                f = next((x for x in fichas if x['id'] == u.get('personaje_id') or K._norm(x['name']) == K._norm(u.get('personaje'))), None)
                if f is not None: f['voice_only'] = 'voice only: never place it on screen; it has no image'
            for u in r.get('usar') or []:
                f = next((x for x in fichas if x['id'] == u.get('personaje_id') or K._norm(x['name']) == K._norm(u.get('personaje'))), None)
                if f is None: continue
                if f.get('height_m') is None and u.get('altura_m'): f['height_m'] = K._num(u['altura_m'])
                f['version'] = {'name': u.get('version'), 'form': u.get('forma_id'), 'description': u.get('descripcion'), 'never_changes': u.get('nunca_cambia')}
                if u.get('tipo') == 'relleno':   # orden 88: relleno del capítulo (sin imagen): se pone en cuadro desde la descripción
                    f['filler'] = 'background/secondary extra of this chapter only: no reference image; place and stage it from version.description, generic, never resembling a main character'
                for im in u.get('imagenes') or []:
                    if im not in imgs and len(imgs) < int(cf['max_imagenes']) and Path(im).is_file():
                        imgs.append(im); f['images'].append({'n': len(imgs), 'view': lado})
    except Exception as ex:
        det.append(f'no pude leer las referencias de personajes ({type(ex).__name__}: {str(ex)[:120]})')
    for d in sorted(set(det)): avisos.append(f"escena {e['numero']}: {d}")
    return fichas, imgs, sorted(set(det))


def pedido01(K, D, a, e, cd, PC, guion, avisos):
    cf = _cfg(); txt = PG.texto(cf['prompt']); esq = PG.texto(cf['esquema'])
    M, err = K.molde(D, e['escenario_id'])
    if err: return None, err
    S = escenario(K, M, e['numero'], e['escenario_id'], avisos)
    if not S['floor_bounds']: return None, f"el molde {e['escenario_id']} no trae medidas de objetos (no se puede poner a nadie sin inventar)"
    fichas, imgs, det = personajes_escena(K, D, a, e, PC, avisos)
    if det and cf['si_falta_ref'] == 'detener': return None, '; '.join(det)
    fmt = {'aspect': (cd or {}).get('aspect'), 'fps_default': cf['fps_por_defecto'], 'frame_height_pct': ((cd or {}).get('paso01') or {}).get('alto_cuadro_pct')}
    sc = {k: v for k, v in e['datos'].items()}
    prompt = (txt + '\n\n=== THE_SET ===\n' + json.dumps(S, ensure_ascii=False, indent=1) + '\n=== END THE_SET ==='
              + '\n\n=== CHARACTERS ===\n' + json.dumps(fichas, ensure_ascii=False, indent=1) + '\n=== END CHARACTERS ==='
              + '\n\n=== SCENE ===\n' + json.dumps(sc, ensure_ascii=False, indent=1) + '\n=== END SCENE ==='
              + ('\n\n=== SCRIPT ===\n' + guion + '\n=== END SCRIPT ===' if guion else '')
              + '\n\n=== FORMAT ===\n' + json.dumps(fmt, ensure_ascii=False) + '\n=== END FORMAT ===\n\nSCHEMA\n' + esq)
    return {'prompt': prompt, 'texto': txt, 'esquema': json.loads(esq), 'adjuntos': imgs, 'set': S, 'fichas': fichas, 'avisos_refs': det}, None


def validar(K, obj, e, P):
    """Lo que el código exige antes de escribir el 01. Devuelve (C, errores)."""
    S = P['set']; L = S['floor_bounds']; mg = float(_cfg()['margen_fuera_m']); err = []
    dur = K._num(obj.get('duracion_s')) or 0
    ids = {K._norm(f['id']): f['id'] for f in P['fichas']}
    ids.update({K._norm(f['name']): f['id'] for f in P['fichas']})
    pts = obj.get('puntos') or {}

    def dentro(p, q):
        if not (isinstance(p, list) and len(p) in (2, 3) and all(K._num(v) is not None for v in p)): err.append(f'{q}: no es [x,y,z]'); return None
        x, y = float(p[0]), float(p[1]); z = float(p[2]) if len(p) == 3 else L['z_floor']
        if not (L['x'][0] - mg <= x <= L['x'][1] + mg and L['y'][0] - mg <= y <= L['y'][1] + mg): err.append(f'{q}: {p} fuera del suelo del molde {S["mold"]} (x {L["x"]}, y {L["y"]})')
        if not (L['z_floor'] - mg <= z <= L['z_top'] + mg): err.append(f'{q}: altura z={z} fuera del molde')
        return [x, y, z]
    for k, p in pts.items(): dentro(p, f'puntos.{k}')
    pers = []
    for i, p in enumerate(obj.get('personajes') or []):
        cid = ids.get(K._norm(p.get('id')))
        if not cid: err.append(f"personajes[{i}]: «{p.get('id')}» no es un personaje en cuadro de esta escena ({sorted(set(ids.values()))})"); continue
        segs = []
        for j, s in enumerate(p.get('segmentos') or []):
            t = s.get('t') or []
            if len(t) == 2 and all(K._num(x) is not None for x in t) and not (0 <= float(t[0]) <= float(t[1]) <= dur + 1e-6): err.append(f'{cid}.segmentos[{j}]: t={t} fuera de 0..{dur}')
            for x in (s.get('pos') or [])[:2]:
                if isinstance(x, str):
                    if x not in pts: err.append(f'{cid}.segmentos[{j}]: punto «{x}» no está en «puntos»')
                else: dentro(x, f'{cid}.segmentos[{j}].pos')
            segs.append({k: s[k] for k in ('t', 'pos', 'rot', 'tipo', 'porque') if k in s})
        f = next(x for x in P['fichas'] if x['id'] == cid)
        pers.append({'id': cid, 'altura': K._num(p.get('altura')) or f.get('height_m'), 'estado': p.get('estado') or {}, 'segmentos': segs,
                     'version_personaje': f.get('version')})
    nomcams = set(S.get('all_camera_names') or []); tomas = []   # accion_v1: el 01 puede venir sin cámaras
    for i, t in enumerate(obj.get('tomas') or []):
        tt = t.get('t') or []
        if len(tt) == 2 and all(K._num(x) is not None for x in tt) and not (0 <= float(tt[0]) <= float(tt[1]) <= dur + 1e-6): err.append(f"tomas[{i}] {t.get('id')}: t={tt} fuera de 0..{dur}")
        if t.get('camara_molde'):
            if t['camara_molde'] not in nomcams: err.append(f"tomas[{i}] {t.get('id')}: la cámara «{t['camara_molde']}» no existe en el molde {S['mold']}"); continue
            cam = {'molde': t['camara_molde']}
        elif isinstance(t.get('camara'), dict):
            c = t['camara']; loc = c.get('loc'); mira = c.get('mira')
            if not (isinstance(loc, list) and isinstance(mira, list) and len(loc) == 3 and len(mira) == 3): err.append(f"tomas[{i}] {t.get('id')}: cámara sin loc/mira [x,y,z]"); continue
            cam = {'loc': [float(v) for v in loc], 'mira': [float(v) for v in mira], 'lente': K._num(c.get('lente')) or 35}
        else: err.append(f"tomas[{i}] {t.get('id')}: sin cámara"); continue
        tomas.append({'id': str(t.get('id') or f't{i + 1}'), 'plano': t.get('plano'), 't': [K._num(x) for x in tt], 'camara': cam, 'porque': t.get('porque')})
    faltan = {f['id'] for f in P['fichas']} - {p['id'] for p in pers}
    if faltan: err.append(f'faltan personajes en cuadro: {sorted(faltan)}')
    C = {'escena': str(e['numero']), 'fps': int(K._num(obj.get('fps')) or _cfg()['fps_por_defecto']), 'duracion_s': dur, 'puntos': pts, 'personajes': pers,
         'tomas_plan': tomas, 'ejes': obj.get('ejes') or [], 'avisos_argon': obj.get('avisos') or [], 'escenario_id': S['mold'],
         'escenario_elegido_por': 'base.json (el mismo molde que usa el 02)', 'origen': 'corrida del 01 (Argon)'}
    e2, _ = K.validar_01(C); err += e2
    return C, err


def cubo01(K, D, a, cd, PC):
    faltan = [f'archivo {x} (cajas/)' for x in PG.archivos_que_faltan('01')]
    if faltan: return K.r_base('01', D, {'ok': False, 'faltan': faltan, 'resumen': '01 · falta ' + ', '.join(faltan)})
    guion = K._guion(D); avisos, filas, ctx = [], [], {}
    if not guion: faltan.append('guion completo (bloque GUION_COMPLETO de pedidos/*.txt): se dirige solo con la escena del mapa')
    for e in K.escenas(D, a.solo):
        n = e['numero']; P, err = pedido01(K, D, a, e, cd, PC, guion, avisos)
        ya = K.leer(D / 'cubos' / '01' / f'esc_{n}.json')
        fila = {'escena': n, 'escenario_id': e['escenario_id'], 'personajes_en_cuadro': e['personajes'],
                'ya_dirigida': bool(isinstance(ya, dict) and ya.get('personajes') is not None and not ya.get('importado')),
                'hay_importado': bool(isinstance(ya, dict) and ya.get('importado'))}
        if err: filas.append({**fila, 'tiene_molde': False, 'cotizacion': None, 'por_que': err}); faltan.append(f'escena {n}: {err}'); continue
        (D / 'cubos' / '01' / 'pedidos').mkdir(parents=True, exist_ok=True)
        (D / 'cubos' / '01' / 'pedidos' / f'esc_{n}.txt').write_text(P['prompt'], encoding='utf-8')
        cot = K.cotizar(len(P['prompt']), len(P['adjuntos']), cd, '01'); ctx[n] = (e, P, cot)
        filas.append({**fila, 'tiene_molde': True, 'cotizacion': cot, 'imagenes_personajes': len(P['adjuntos']), 'avisos_refs': P['avisos_refs'],
                      'pedido': str(D / 'cubos' / '01' / 'pedidos' / f'esc_{n}.txt'), 'camaras_molde': [c['name'] for c in P['set']['cameras']]})
    tot = round(sum((f.get('cotizacion') or {}).get('usd') or 0 for f in filas), 4)
    pago = _pagar01(K, D, a, cd, ctx, filas) if getattr(a, 'correr', False) else None
    out = K.r_base('01', D, {'escenas': filas, 'total_usd_peor_caso': tot, 'faltan': sorted(set(faltan)), 'avisos': sorted(set(avisos))[:30],
                             'pistas': ['PISTA INMI (orden 83): prompt cajas/prompts_01/dirigir_escena.txt (inglés) con el MISMO molde del 02; pedido exacto en cubos/01/pedidos/esc_N.txt.',
                                        'PISTA INMI (orden 83): pagar = guarda cajas/HABILITAR_PAGO_01 + «--correr --ok USD --aprobado QUIEN [--escena N]». Sin eso solo cotiza.'],
                             'resumen': f'01 · cotizado {len(ctx)}/{len(filas)} escenas: US$ {tot} peor caso' + ('' if pago else ' (no se llamó a Argon)')})
    if pago: out.update(pago)
    out['archivo'] = K.guardar(D / 'cubos' / '01' / 'cotizacion.json', out)
    return out


def _pagar01(K, D, a, cd, ctx, filas):
    msg = PG.revisar_guarda('01', a.ok, a.aprobado)
    if msg: return {'pago': {'llamado': False, 'por_que': msg}}
    quien = [n for n in ctx if ctx[n][2].get('ok')]
    if not quien: return {'pago': {'llamado': False, 'por_que': 'ninguna escena tiene cotización (falta molde o datos)'}}
    tot = round(sum(ctx[n][2]['usd'] for n in quien), 4)
    if tot > float(a.ok) + 1e-9: return {'pago': {'llamado': False, 'por_que': f'cotización fresca US${tot} > --ok {a.ok}: no se llama (usar --escena para ir de a una)'}}
    X = a.X if getattr(a, 'X', None) else PG.app()
    modelo, nivel, mo = K.modelo_canal(cd); peds = []
    for n in quien:
        e, P, cot = ctx[n]
        peds.append({'clave': f'esc{n}', 'n': n, 'prompt': P['prompt'], 'salida': D / 'cubos' / '01' / 'respuestas' / f'esc_{n}.txt', 'est': cot['usd'],
                     'adjuntos': P['adjuntos'], 'esquema': P['esquema'], 'modelo': modelo, 'nivel': nivel, 'max_out': mo,
                     'fijo': PG.fijo('01', P['texto'], json.dumps(P['esquema'], ensure_ascii=False, sort_keys=True), modelo, nivel, mo, X.get('FP')),
                     'nota': f'cubo 01 dirige esc {n}'})
        Path(peds[-1]['salida']).parent.mkdir(parents=True, exist_ok=True)
    res, bolsa = PG.correr(peds, a, X, cd, '01'); hechas = []
    for q, r in zip(peds, res):
        n = q['n']; e, P, _ = ctx[n]; fila = next(f for f in filas if f['escena'] == n)
        if not r['ok']: fila['pago'] = r; hechas.append({'escena': n, **{k: r.get(k) for k in ('ok', 'error', 'no_llamado')}}); continue
        rv = PG.LS.revisar_respuesta(r['texto'], q['esquema'], r.get('fin'))
        if rv['obj'] is None or rv.get('esquema_errores'):
            fila['pago'] = {'ok': False, 'ledger': r['ledger'], 'error': f"respuesta no válida ({rv['estado']}; {rv.get('esquema_errores', [])[:3]})"}
            hechas.append({'escena': n, 'ok': False, 'ledger': r['ledger'], 'usd': r.get('usd'), 'error': fila['pago']['error']}); continue
        C, err = validar(K, rv['obj'], e, P)
        if err:
            K.guardar(D / 'cubos' / '01' / 'rechazadas' / f'esc_{n}.json', {'errores': err, 'respuesta': rv['obj'], 'ledger': r['ledger']})
            fila['pago'] = {'ok': False, 'ledger': r['ledger'], 'error': f'el código rechazó la dirección ({len(err)} errores): {err[:3]}'}
            hechas.append({'escena': n, 'ok': False, 'ledger': r['ledger'], 'usd': r.get('usd'), 'error': fila['pago']['error']}); continue
        C.update({'de': 'argon', 'ledger': r['ledger'], 'usd': r.get('usd'), 'aprobado_por': a.aprobado, 'fecha': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                  'refs_personajes': {f['id']: f['images'] for f in P['fichas']}})
        f1 = D / 'cubos' / '01' / f'esc_{n}.json'; resp = None
        if f1.is_file():   # un 01 real reemplaza un importado (o uno anterior): se respalda primero
            resp = D / 'cubos' / '01' / 'respaldos' / f"esc_{n}.{time.strftime('%Y%m%d-%H%M%S')}.json"; resp.parent.mkdir(parents=True, exist_ok=True)
            resp.write_bytes(f1.read_bytes())
        K.guardar(f1, C)
        fila.update({'ya_dirigida': True, 'hay_importado': False, 'archivo': str(f1), 'respaldo_anterior': str(resp) if resp else None, 'ledger': r['ledger']})
        hechas.append({'escena': n, 'ok': True, 'ledger': r['ledger'], 'usd': r.get('usd'), 'archivo': str(f1)})
    usd = round(sum(float(r.get('usd') or 0) for r in res if r.get('ok')), 6)
    return {'gratis': False, 'modo': 'correr', 'llamadas_pagas': sum(int(r.get('anotados') or 0) for r in res), 'usd_gastado': usd,
            'pago': {'llamado': True, 'aprobado_por': a.aprobado, 'ok_usd': a.ok, 'cotizacion_fresca_usd': tot, 'bolsa_peor_caso': round(bolsa['gastado'], 4), 'escenas': hechas}}
