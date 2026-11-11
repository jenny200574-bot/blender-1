#!/usr/bin/env python3
"""cubo 01 «SOLO ACCIÓN» (accion_v1, 2026-11-01, reorganización del flujo; Ricardo [pt325u]). Genérico: cualquier canal, historia, personaje.
El 01 decide SOLO la acción: posiciones, recorridos, giros, poses, miradas, emociones, cambios de objetos, TIEMPO por beat y
hechos para el historial. NO elige cámaras ni tomas (eso lo hará el 06 sobre la animación del 02N).
Reutiliza todo lo probado del o109 (molde, personajes, parámetros 3D, latino, pago con guarda/ledger, autocorrección); solo cambia
el pedido (sin cámaras; con la zona de la escena como pista), el esquema (acciones + hechos, sin tomas) y la validación de la acción.
Compatibilidad: la salida conserva el contrato de siempre (personajes/segmentos/puntos/duracion_s/fps; tomas_plan = []) para
Armar tramo, 02N y los cubos viejos. Se activa con argon_pago.json → 01.version = "accion" (paso01_cubos.cubo01); o109 sigue disponible.
Pago: igual que o109 (HABILITAR_PAGO_01 + --correr --ok --aprobado). Sin eso SOLO cotiza (US$0)."""
import copy, json, re, sys, time
from pathlib import Path

import paso01_pago as PG
import paso01_dirigir as DI
import autocorreccion_01 as AC
import cubo01_o109 as O   # deja DI._VALIDAR_83 = validación base del 83
import eventos_o112 as EV
P_POSES = Path(__file__).resolve().parent / 'poses_o110'
if str(P_POSES) not in sys.path: sys.path.insert(0, str(P_POSES))
import palabras_pose as PP

VERSION = 'accion_v1'
CHEQUEOS = ('contradicciones', 'alineacion_set', 'continuidad_posiciones', 'tiempos', 'poses', 'miradas_y_emociones', 'objetos_y_cambios', 'hechos')
PALABRAS = ('accion', 'pose', 'mirada', 'emocion', 'cambio')
MUEVEN = ('caminar', 'correr', 'caer', 'escalar', 'levitar', 'mover')
DEF = {'prompt': 'prompts_01/dirigir_escena_accion.txt', 'esquema': 'prompts_01/dirigir_escena_esquema_accion.json',
       'prompt_reparar': 'prompts_01/reparar_accion.txt', 'velocidad_max_mps': 9.0, 'salto_max_m': 0.3, 'hueco_max_s': 2.0}


def cfg():
    """Ajustes del 01 + el bloque 01.accion de argon_pago.json (si falta, los valores por defecto de arriba)."""
    c = dict(DI._cfg()); c.update({k: v for k, v in DEF.items() if k not in (c.get('accion') or {})}); c.update(c.get('accion') or {})
    return c


def _txt(rel): return PG.texto(rel)


# ---------------- pedido ----------------
def zona_escena(of, inf):
    """[x_min, x_max, y_min, y_max] del suelo que ven las cámaras PROPIAS de la escena (lo preparó el diseñador del set). Gratis."""
    cajas = [i['suelo_visible_caja_xy'] for i in inf.get('camaras') or [] if i.get('propia') and i.get('ofrecida') and i.get('suelo_visible_caja_xy')]
    if not cajas: cajas = [i['suelo_visible_caja_xy'] for i in inf.get('camaras') or [] if i.get('ofrecida') and i.get('suelo_visible_caja_xy')]
    if not cajas: return None
    return [round(min(c[0] for c in cajas), 2), round(max(c[1] for c in cajas), 2), round(min(c[2] for c in cajas), 2), round(max(c[3] for c in cajas), 2)]


def pedido(K, D, a, e, cd, PC, guion, avisos):
    cf = cfg(); txt = _txt(cf['prompt']); esq = _txt(cf['esquema'])
    M, err = K.molde(D, e['escenario_id'])
    if err: return None, err
    S = DI.escenario(K, M, e['numero'], e['escenario_id'], avisos)
    S['objects'] = [o for o in S['objects'] if not re.match(r'^(marca_|flecha_|rej_)', o['name'])]
    if not S['floor_bounds']: return None, f"el molde {e['escenario_id']} no trae medidas de objetos (no se puede poner a nadie sin inventar)"
    asp = K.aspecto(cd) or (16, 9); zona, inf = None, {'camaras': [], 'motivo': 'el molde no trae cámaras'}
    if (M or {}).get('camaras_molde'):
        of, inf = AC.camaras_validas(O, M, S, e['numero'], asp, AC.ajustes_01()['camaras']); zona = zona_escena(of, inf)
    for k in ('cameras', 'all_camera_names', 'camera_rule'): S.pop(k, None)   # el 01 ya no ve cámaras
    if zona: S['scene_area_xy'] = zona
    else: avisos.append(f"escena {e['numero']}: sin zona de escena (ninguna cámara del molde la marca); Argon usa todo el suelo")
    fichas, imgs, det = DI.personajes_escena(K, D, a, e, PC, avisos)
    if det and cf['si_falta_ref'] == 'detener': return None, '; '.join(det)
    fijos = {}
    for f in fichas:
        g = O.guardados(a.canal, f['id'])
        if g: fijos[f['id']] = g; f['stored_3d_parameters'] = True
    fmt = {'fps_default': cf['fps_por_defecto']}
    voc = {'ACTION_VERBS': EV.VERBOS, 'POSE_LIBRARY': PP.lista(), 'OBJECT_CHANGES': [x for x in EV.CAMBIOS if x]}
    prompt = (txt + '\n\n=== THE_SET ===\n' + json.dumps(S, ensure_ascii=False, indent=1) + '\n=== END THE_SET ==='
              + '\n\n=== CHARACTERS ===\n' + json.dumps(fichas, ensure_ascii=False, indent=1) + '\n=== END CHARACTERS ==='
              + '\n\n=== PARAMETER_DICTIONARY ===\n' + json.dumps(O.diccionario(), ensure_ascii=False) + '\n=== END PARAMETER_DICTIONARY ==='
              + '\n\n=== STORED_3D_PARAMETERS ===\n' + json.dumps(fijos, ensure_ascii=False) + '\n=== END STORED_3D_PARAMETERS ==='
              + ''.join(f'\n\n=== {k} ===\n' + json.dumps(v, ensure_ascii=False) + f'\n=== END {k} ===' for k, v in voc.items())
              + '\n\n=== SCENE ===\n' + json.dumps(e['datos'], ensure_ascii=False, indent=1) + '\n=== END SCENE ==='
              + ('\n\n=== SCRIPT ===\n' + guion + '\n=== END SCRIPT ===' if guion else '')
              + '\n\n=== FORMAT ===\n' + json.dumps(fmt, ensure_ascii=False) + '\n=== END FORMAT ===\n\nSCHEMA\n' + esq)
    return {'prompt': prompt, 'texto': txt, 'esquema': json.loads(esq), 'adjuntos': imgs, 'set': S, 'fichas': fichas, 'avisos_refs': det,
            'molde': M, 'fijos': fijos, 'aspecto': asp, 'camaras_informe': inf, 'zona': zona, 'guion': guion or '', 'vocabulario': voc}, None


# ---------------- validación ----------------
def _par(K, t):
    return [float(t[0]), float(t[1])] if isinstance(t, list) and len(t) == 2 and all(K._num(x) is not None for x in t) else None


def cita_en_guion(cita, G):
    """La cita está copiada del guion: >= 60 % de sus PARES de palabras seguidas aparecen tal cual (palabras sueltas sueltas no bastan)."""
    w = EV._pal(cita)
    if len(w) < 2: return not w or f' {w[0]} ' in f' {G} '
    pares = [f' {w[i]} {w[i + 1]} ' for i in range(len(w) - 1)]; g = f' {G} '
    return sum(1 for p in pares if p in g) / len(pares) >= .6


def _d2(a, b): return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** .5


# 2026-11-06 (Ricardo t499u): signos tipográficos que Argon copia del guion y que tienen un equivalente ASCII inequívoco.
# Se cambian en TODO el plan antes de validar (el control de alfabeto latino sigue para todo lo demás).
TIPOGRAFICOS = {'\u2212': '-'}   # − (signo menos matemático) → -


def _tipograficos(x, ruta='', cambios=None):
    if isinstance(x, str):
        y = x
        for a, b in TIPOGRAFICOS.items(): y = y.replace(a, b)
        if y != x and cambios is not None: cambios.append(f'{ruta}: signo tipográfico cambiado a ASCII ({", ".join(sorted({c for c in x if c in TIPOGRAFICOS}))})')
        return y
    if isinstance(x, dict): return {k: _tipograficos(v, f'{ruta}.{k}' if ruta else str(k), cambios) for k, v in x.items()}
    if isinstance(x, list): return [_tipograficos(v, f'{ruta}[{i}]', cambios) for i, v in enumerate(x)]
    return x


def ids_oficiales(P, ids):
    """{id oficial: nombre en palabras}. Solo ids de personajes de la escena (→ su «name» de la ficha) y nombres de objetos del set
    entregado a Argon (→ 'obj-libro-cuentos__e1-8' = 'libro cuentos': sin prefijo obj-, sin variante __eN, guiones = espacios).
    Un id que no esté aquí sigue siendo error; si el nombre resultante aún tiene números, sigue siendo error."""
    out = {}
    for o in (P.get('set') or {}).get('objects') or []:
        n = str(o.get('name') or '')
        if n: out[n] = re.sub(r'\s+', ' ', re.sub(r'^obj-', '', n.split('__')[0]).replace('-', ' ').replace('_', ' ')).strip()
    nom = {f.get('id'): f.get('name') for f in P.get('fichas') or []}
    for i in ids: out[str(i)] = str(nom.get(i) or '').strip() or str(i)
    return out


def validar(K, obj, e, P):
    """(C, errores). Errores con prefijo que la autocorrección agrupa: acciones[i] id / <personaje>.segmentos[j] / puntos.X / hechos[i]."""
    cf = cfg(); norm = []; obj = _tipograficos(O.normalizar(obj), '', norm); av = []
    for k in ('tomas', 'ejes'):
        if obj.get(k): av.append(f'Argon mandó «{k}» y se descartó: el 01 solo dirige la acción (las cámaras las elige el 06)'); obj.pop(k, None)
    C, err = DI._VALIDAR_83(K, obj, e, P)
    for ruta, s in O._todas_cadenas(obj):
        m = O.latino(s)
        if m: err.append(f'{ruta}: caracteres que no son del alfabeto latino {m[:6]}')
    dic = O.diccionario(); params = {}
    for p in obj.get('personajes') or []:
        cid = next((pp['id'] for pp in C['personajes'] if K._norm(pp['id']) == K._norm(p.get('id'))), None)
        if not cid: continue
        if cid in P['fijos']: ctl, e2 = O.resolver_parametros(P['fijos'][cid], dic); origen = 'biblioteca (aprobados)'
        else: ctl, e2 = O.resolver_parametros(p.get('parametros_3d'), dic); origen = 'Argon (diccionario)'
        err += [f'{cid}.parametros_3d: {x}' for x in e2]; params[cid] = {'controles': ctl, 'origen': origen}
    dur = float(K._num(C.get('duracion_s')) or 0); ids = {pp['id'] for pp in C['personajes']}
    # --- continuidad y velocidad de los recorridos (nadie se teletransporta) ---
    mueve = {}
    for pp in C['personajes']:
        segs = sorted([s for s in pp['segmentos'] if _par(K, s.get('t'))], key=lambda s: float(s['t'][0])); prev = None; mueve[pp['id']] = []
        orig = pp['segmentos']
        for s in segs:
            j = orig.index(s); t = _par(K, s['t']); a0, b0 = K._xyz(C, s['pos'][0]), K._xyz(C, s['pos'][-1])
            if not (a0 and b0): continue
            d = _d2(a0, b0)
            if d > 0.05: mueve[pp['id']].append(t)
            if t[1] > t[0] and d / (t[1] - t[0]) > float(cf['velocidad_max_mps']):
                err.append(f"{pp['id']}.segmentos[{j}]: velocidad imposible {d / (t[1] - t[0]):.1f} m/s (máx {cf['velocidad_max_mps']})")
            if t[1] <= t[0] and d > float(cf['salto_max_m']): err.append(f"{pp['id']}.segmentos[{j}]: recorre {d:.1f} m en 0 s (teletransporte)")
            if prev:
                pj, pt, pb = prev
                if _d2(pb, a0) > float(cf['salto_max_m']): err.append(f"{pp['id']}.segmentos[{j}]: empieza a {_d2(pb, a0):.1f} m de donde terminó el segmento {pj} (teletransporte)")
                if t[0] < pt[1] - 1e-6: err.append(f"{pp['id']}.segmentos[{j}]: empieza en {t[0]:g} s antes de que termine el segmento {pj} ({pt[1]:g} s)")
                elif t[0] - pt[1] > float(cf['hueco_max_s']): av.append(f"{pp['id']}.segmentos[{j}]: hueco de {t[0] - pt[1]:.1f} s sin segmento (se queda quieto)")
            prev = (j, t, b0)
        if segs and dur and (float(segs[0]['t'][0]) > float(cf['hueco_max_s']) or dur - float(segs[-1]['t'][1]) > float(cf['hueco_max_s'])):
            av.append(f"{pp['id']}: sus segmentos no cubren toda la escena (0-{dur:g} s)")
    # --- beats de acción (tiempo por beat) ---
    obs = {K._norm(o.get('name')) for o in P['set'].get('objects') or []} | {K._norm(i) for i in ids}
    oficiales = ids_oficiales(P, ids)
    G = ' '.join(EV._pal(P.get('guion') or '')); poses = PP.palabras(); acc_out = []; vistos = set(); cubierto = []
    A = obj.get('acciones')
    if not isinstance(A, list) or not A: err.append('falta «acciones» (los beats con su tiempo): el 01 sin beats no sirve al tramo')
    for i, b in enumerate(A or []):
        if not isinstance(b, dict): err.append(f'acciones[{i}] ?: no es un objeto'); continue
        bid = str(b.get('id') or f'a{i + 1}'); q = f'acciones[{i}] {bid}'
        if bid in vistos: err.append(f'{q}: id repetido')
        vistos.add(bid); t = _par(K, b.get('t'))
        if not t: err.append(f'{q}: «t» debe ser [inicio, fin] en segundos'); continue
        if not (0 <= t[0] <= t[1] <= dur + 1e-6): err.append(f'{q}: t={b.get("t")} fuera de 0..{dur:g}')
        act = str(b.get('actor') or '')
        actor = next((x for x in ids if K._norm(x) == K._norm(act)), None) if act else ''
        if act and actor is None: err.append(f'{q}: actor «{act}» no es un personaje de la escena {sorted(ids)}')
        if b.get('accion') not in EV.VERBOS: err.append(f"{q}: accion «{b.get('accion')}» no es uno de {EV.VERBOS}")
        if str(b.get('pose') or '') and EV._n(b['pose']).replace(' ', '_') not in poses: err.append(f"{q}: pose «{b['pose']}» no está en la biblioteca de poses {PP.lista()} (FALTA, no se inventa)")
        if str(b.get('cambio') or '') not in EV.CAMBIOS: err.append(f"{q}: cambio «{b.get('cambio')}» no es uno de {EV.CAMBIOS[1:]}")
        if b.get('cambio') in ('romper', 'mover') and not str(b.get('objeto') or '').strip(): err.append(f"{q}: cambio «{b['cambio']}» sin «objeto»")
        if str(b.get('objeto') or '').strip() and K._norm(b['objeto']) not in obs: av.append(f"{q}: objeto «{b['objeto']}» no es un nombre del set ni un personaje (se toma como palabra)")
        for k in PALABRAS:
            v = str(b.get(k) or '').strip()
            if k == 'mirada' and v in oficiales:   # t500u: el contrato pide PALABRAS; un id oficial exacto se traduce a su nombre (determinista)
                b['mirada_id'] = v; b['mirada'] = oficiales[v]
                norm.append(f'{q}.mirada: id oficial «{v}» → «{oficiales[v]}» (contrato: palabras sin números)')
                if not re.search(r'\d', oficiales[v]): continue
            if re.search(r'\d', str(b.get(k) or '')): err.append(f'{q}.{k}: tiene números (solo palabras): «{str(b[k])[:60]}»')
        if actor and b.get('accion') != 'poder':
            for k in ('mirada', 'emocion'):
                if not str(b.get(k) or '').strip(): err.append(f'{q}: {k} vacío')
        cita = str(b.get('cita') or '').strip()
        if not cita: err.append(f'{q}: falta la cita del guion')
        elif G and not cita_en_guion(cita, G): err.append(f'{q}: la cita «{cita[:60]}» no está en el guion (se copia literal)')
        if actor and b.get('accion') in ('caminar', 'correr') and not any(m[0] < t[1] + 1e-6 and m[1] > t[0] - 1e-6 for m in mueve.get(actor, [])):
            err.append(f"{q}: dice {b['accion']} pero los segmentos de {actor} no lo mueven entre {t[0]:g} y {t[1]:g} s")
        cubierto.append(t)
        acc_out.append({'id': bid, 't': t, 'actor': actor or '', **{k: str(b.get(k) or '') for k in ('accion', 'pose', 'mirada', 'emocion', 'objeto', 'cambio', 'cita')}, **({'mirada_id': b['mirada_id']} if b.get('mirada_id') else {})})
    for cid, ms in mueve.items():   # todo desplazamiento visible tiene un beat que lo explique
        for m in ms:
            if not any(x['actor'] == cid and x['accion'] in MUEVEN + ('girar',) and x['t'][0] < m[1] + 1e-6 and x['t'][1] > m[0] - 1e-6 for x in acc_out):
                av.append(f'{cid}: se mueve entre {m[0]:g} y {m[1]:g} s sin un beat que lo explique')
    if cubierto and dur:
        cubierto.sort(); fin = 0.0; hue = []
        for t0, t1 in cubierto:
            if t0 - fin > float(cf['hueco_max_s']): hue.append(f'{fin:g}-{t0:g}')
            fin = max(fin, t1)
        if dur - fin > float(cf['hueco_max_s']): hue.append(f'{fin:g}-{dur:g}')
        if hue: av.append(f'acciones: segundos sin ningún beat {hue}')
    acc_out.sort(key=lambda x: (x['t'][0], x['t'][1]))
    # --- hechos para el historial ---
    hechos = []
    H = obj.get('hechos')
    if not isinstance(H, list): err.append('falta «hechos» (lista; puede ir vacía si la escena no cambia nada)')
    for i, h in enumerate(H or []):
        q = f'hechos[{i}]'
        if not isinstance(h, dict) or not str(h.get('hecho') or '').strip(): err.append(f'{q}: falta «hecho»'); continue
        pid = str(h.get('personaje') or ''); cid = next((x for x in ids if K._norm(x) == K._norm(pid)), None) if pid else ''
        if pid and cid is None: err.append(f'{q}: personaje «{pid}» no es de la escena {sorted(ids)}')
        th = K._num(h.get('t'))
        if th is None or not (0 <= float(th) <= dur + 1e-6): err.append(f"{q}: t={h.get('t')} fuera de 0..{dur:g}")
        hechos.append({'hecho': str(h['hecho']), 'personaje': cid or '', 't': th})
    if isinstance(H, list) and not H: av.append('hechos vacío: la escena no deja nada para el historial')
    rv = obj.get('revision')
    if not isinstance(rv, list) or not rv: err.append('falta «revision» (Argon no revisó su plan)')
    else:
        falt = [c for c in CHEQUEOS if c not in {str(x.get('chequeo')) for x in rv if isinstance(x, dict)}]
        if falt: av.append(f'revision sin los chequeos {falt}')
    C.update({'parametros_3d': params, 'revision_argon': rv, 'avisos_codigo': av, 'version_01': VERSION, 'aspecto': list(P['aspecto']),
              'solo_accion': True, 'normalizaciones_codigo': norm, 'acciones': acc_out, 'hechos': hechos, 'tomas_plan': [], 'zona_escena_xy': P.get('zona'),
              'camaras': 'las elige el 06 sobre la animación (el 01 solo dirige la acción)'})
    return C, err


# ---------------- cubo ----------------
def cubo01(K, D, a, cd, PC):
    DI.validar = validar          # el camino pago del 83 (_pagar01) valida con ESTA validación
    DI._cfg_accion = cfg
    faltan = [f'archivo {x} (cajas/)' for x in PG.archivos_que_faltan('01')]
    cf = cfg()
    faltan += [f'archivo {cf[k]} (cajas/)' for k in ('prompt', 'esquema', 'prompt_reparar') if not (AC.AQUI / cf[k]).is_file()]
    if faltan: return K.r_base('01', D, {'ok': False, 'faltan': faltan, 'resumen': '01 · falta ' + ', '.join(faltan)})
    guion = K._guion(D); avisos, filas, ctx = [], [], {}
    if not guion: faltan.append('guion completo (bloque GUION_COMPLETO de pedidos/*.txt): se dirige solo con la escena del mapa')
    rv_arch = getattr(a, 'revalidar', None)
    for e in K.escenas(D, a.solo):
        n = e['numero']; P, err = pedido(K, D, a, e, cd, PC, guion, avisos)
        ya = K.leer(D / 'cubos' / '01' / f'esc_{n}.json')
        fila = {'escena': n, 'escenario_id': e['escenario_id'], 'personajes_en_cuadro': e['personajes'],
                'ya_dirigida': (ya or {}).get('version_01') if isinstance(ya, dict) else None}
        if err: filas.append({**fila, 'tiene_molde': False, 'cotizacion': None, 'por_que': err}); faltan.append(f'escena {n}: {err}'); continue
        (D / 'cubos' / '01' / 'pedidos').mkdir(parents=True, exist_ok=True)
        (D / 'cubos' / '01' / 'pedidos' / f'esc_{n}.txt').write_text(P['prompt'], encoding='utf-8')
        cot = K.cotizar(len(P['prompt']), len(P['adjuntos']), cd, '01'); ctx[n] = (e, P, cot)
        fila.update({'tiene_molde': True, 'cotizacion': cot, 'imagenes_personajes': len(P['adjuntos']), 'zona_escena_xy': P['zona'],
                     'camaras': 'ninguna (solo acción)', 'parametros_guardados': sorted(P['fijos']), 'chars_prompt': len(P['prompt']),
                     'pedido': str(D / 'cubos' / '01' / 'pedidos' / f'esc_{n}.txt')})
        if rv_arch: fila['revalidacion'] = revalidar(K, D, n, e, P, rv_arch)
        filas.append(fila)
    tot = round(sum((f.get('cotizacion') or {}).get('usd') or 0 for f in filas), 4)
    if getattr(a, 'correr', False):
        for n in ctx:
            r0 = D / 'cubos' / '01' / 'rechazadas' / f'esc_{n}.json'
            if r0.is_file(): r0.replace(r0.with_name(f"esc_{n}.antes_{time.strftime('%Y%m%d-%H%M%S')}.json"))
    pago = DI._pagar01(K, D, a, cd, ctx, filas) if getattr(a, 'correr', False) else None
    out = K.r_base('01', D, {'version': VERSION, 'escenas': filas, 'total_usd_peor_caso': tot, 'faltan': sorted(set(faltan)), 'avisos': sorted(set(avisos))[:30],
                             'pistas': ['PISTA INMI (accion_v1): el 01 dirige SOLO la acción (posiciones, recorridos, poses, tiempo por beat, hechos); las cámaras/tomas las elige el 06.',
                                        'PISTA INMI (accion_v1): pagar = guarda cajas/HABILITAR_PAGO_01 + «--correr --ok USD --aprobado QUIEN [--escena N]». Sin eso solo cotiza.'],
                             'resumen': f'01 {VERSION} · cotizado {len(ctx)}/{len(filas)} escenas: US$ {tot} peor caso' + ('' if pago else ' (no se llamó a Argon)')})
    if pago:
        rp = O.reparar_pagando(K, D, a, cd, ctx, filas, pago, validar_fn=validar, cf=cf)
        if rp: pago['reparaciones'] = rp; pago['usd_gastado'] = round(float(pago.get('usd_gastado') or 0) + rp['usd_gastado'], 6)
    if pago: out.update(pago)
    out['archivo'] = K.guardar(D / 'cubos' / '01' / 'cotizacion.json', out)
    return out


def revalidar(K, D, n, e, P, arch, escribir=True):
    """GRATIS: valida con el código una respuesta de Argon ya pagada (archivo JSON) y, si pasa, escribe cubos/01/esc_N.json (respaldando el anterior)."""
    f = Path(str(arch).replace('{n}', str(n)))
    if not f.is_file(): return {'ok': False, 'error': f'no existe {f}'}
    txt = f.read_text(encoding='utf-8'); i, j = txt.find('{'), txt.rfind('}')
    try: obj = json.loads(txt[i:j + 1])
    except Exception as ex: return {'ok': False, 'error': f'no es JSON ({type(ex).__name__})'}
    C, err = validar(K, obj, e, P)
    if err:
        K.guardar(D / 'cubos' / '01' / 'rechazadas' / f'esc_{n}.{VERSION}.json', {'errores': err, 'respuesta': obj, 'de': str(f)})
        return {'ok': False, 'errores': len(err), 'primeros': err[:8]}
    f1 = D / 'cubos' / '01' / f'esc_{n}.json'
    if f1.is_file():
        r = D / 'cubos' / '01' / 'respaldos' / f"esc_{n}.{time.strftime('%Y%m%d-%H%M%S')}.json"; r.parent.mkdir(parents=True, exist_ok=True); r.write_bytes(f1.read_bytes())
    C.update({'de': f'argon (revalidado {VERSION})', 'respuesta': str(f)}); K.guardar(f1, C)
    return {'ok': True, 'archivo': str(f1), 'acciones': len(C['acciones']), 'hechos': len(C['hechos']), 'avisos_codigo': C['avisos_codigo'][:8]}
