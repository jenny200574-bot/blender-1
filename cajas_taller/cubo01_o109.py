#!/usr/bin/env python3
"""PISTA INMI (2026-10-30): orden 109 — cubo 01 «Argon dirige la escena», consolidado. Genérico (cualquier canal, historia, personaje).
Sobre paso01_dirigir.py (orden 83) agrega lo PROBADO en o98–o108 (única fuente de verdad: nuestros experimentos):
  · Cámaras: SOLO las del molde (cualquier cámara del MISMO set). Se acabaron las cámaras inventadas (10-29: 12/15 escenas rechazadas «sin cámara»).
  · Coordenadas: se quedan, pero SOLO para Blender (el pintor nunca las ve: los números estorban al calco, o100–o104).
  · «palabras» por toma: composición, cuerpo/cabeza/mirada (frente/espalda/perfil + lado de la pantalla), emoción, mano del accesorio,
    cuántas personas y cuántas manos, fondo. Sin números ni colores del molde (nombrar colores del molde = piel coloreada, o100).
  · «parametros_3d» por personaje con el DICCIONARIO de parámetros (o106) → el 02 arma el cuerpo VRM por parámetros (o105–o108).
    Si el canal ya tiene parámetros aprobados del personaje (biblioteca), se pasan fijos.
  · «revision»: Argon revisa contradicciones, alineación con el molde, congruencia de posiciones entre tomas, emociones y fondos.
  · El CÓDIGO valida el texto (solo alfabeto latino, sin números/molde en las palabras, enums, personas = en_cuadro, manos) y lo
    cruza con la geometría REAL de la cámara del molde (frente/espalda, lado de la pantalla, que se vea). Contradicción = rechazo.
Pago: igual que el 83 (guarda HABILITAR_PAGO_01 + --correr --ok --aprobado). Sin eso SOLO cotiza. --revalidar = valida una respuesta ya
pagada (gratis).
2026-11-01 (Ricardo t296u/t297u, autocorrección): (1) a Argon se le ofrecen SOLO las cámaras de ESTA escena que ven el suelo libre
(autocorreccion_01.camaras_validas, calculado con la geometría real del molde); (2) si el código rechaza, se le mandan los errores
exactos y SOLO las tomas/segmentos que fallaron; (3) se fusiona con lo que pasó y se valida todo de nuevo; (4) como mucho
01.reparaciones_max (2) reparaciones, cada una cotizada y por la MISMA guarda/ledger/--ok; si sigue fallando, error en español simple."""
import copy, json, math, re, sys, time
from pathlib import Path

import paso01_pago as PG
sys.path.insert(0, str(Path(__file__).resolve().parent / 'poses_o110')); import palabras_pose as _PP   # o110
import paso01_dirigir as DI
import autocorreccion_01 as AC
_VALIDAR_83 = getattr(DI, '_VALIDAR_83', DI.validar)
DI._VALIDAR_83 = _VALIDAR_83

AQUI = Path(__file__).resolve().parent
DIC_F = AQUI / 'paso01_datos' / 'diccionario_parametros.json'
BIB = Path('/opt/myia-taller-n8n/trabajo/biblioteca')
CUERPO = ('frente', 'espalda', 'perfil_izquierdo', 'perfil_derecho', 'tres_cuartos_frente', 'tres_cuartos_espalda')
LADOS = ('izquierda', 'centro', 'derecha')
MANO = ('izquierda', 'derecha', 'no_aplica')
CHEQUEOS = ('contradicciones', 'alineacion_molde', 'congruencia_posiciones', 'emociones', 'fondos', 'mano_accesorio', 'personas_y_manos')
CONTROLES = ('gordura', 'colores.pelo', 'colores.piel', 'colores.cara', 'colores.ropa_superior', 'colores.ropa_inferior', 'colores.zapatos',
             'colores.ojos', 'gafas', 'pulsera', 'orejas_puntiagudas', 'pelo_largo', 'armadura', 'nucleo_pecho', 'capa', 'expresion', 'expresion_valor',
             'ocultar_pelo_base', 'mangas_cortas')
PROHIBIDAS = ('maniqu', 'mannequin', 'molde', 'cam_', 'coordenad')


def diccionario(): return json.loads(DIC_F.read_text(encoding='utf-8'))['diccionario']


# ---------------- texto ----------------
def latino(s):
    """Caracteres que NO son del alfabeto latino (ni signos comunes). Vacío = bien."""
    malos = []
    for ch in str(s):
        o = ord(ch)
        if o < 0x250 or 0x2000 <= o <= 0x206F or 0x1E00 <= o <= 0x1EFF or ch in '\n\t': continue
        malos.append(ch)
    return sorted(set(malos))


def _todas_cadenas(x, ruta=''):
    if isinstance(x, str): yield ruta, x
    elif isinstance(x, dict):
        for k, v in x.items(): yield from _todas_cadenas(v, f'{ruta}.{k}' if ruta else str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x): yield from _todas_cadenas(v, f'{ruta}[{i}]')


# ---------------- parámetros 3D ----------------
def guardados(canal, cid):
    f = BIB / str(canal) / 'personajes' / str(cid) / 'parametros_3d.json'
    try: return json.loads(f.read_text(encoding='utf-8'))
    except Exception: return None


def resolver_parametros(p3, dic=None):
    """palabras del diccionario + controles crudos → dict de controles (lo que lee el 02). Devuelve (controles, errores)."""
    dic = dic or diccionario(); P = dic['personaje']; out, err = {}, []
    if not isinstance(p3, dict): return {}, ['parametros_3d no es un objeto']
    for w in p3.get('palabras') or []:
        if w not in P: err.append(f'palabra «{w}» no está en el diccionario de personajes'); continue
        c, v = P[w]['control'], P[w]['valor']
        if c == 'colores.piel_y_cara': out['colores.piel'], out['colores.cara'] = v['piel'], v['cara']
        elif c in ('gafas',) and isinstance(v, dict): out['gafas'] = v.get('gafas', True); out['gafas_color'] = v.get('gafas_color')
        elif c == 'pelo_largo' and isinstance(v, dict):
            out['pelo_largo'] = {k: v[k] for k in ('largo_m', 'color') if k in v}
            if v.get('ocultar_pelo_base'): out['ocultar_pelo_base'] = True
        else: out[c] = v
    for k, v in (p3.get('controles') or {}).items():
        # 2026-11-06 (Ricardo t499u): «colores.piel_y_cara» es el control COMPUESTO del propio diccionario ({piel, cara}).
        # Si Argon lo manda como control crudo con ese mismo formato, se reparte igual que hace la palabra del diccionario
        # (sin inventar nada; cada color sigue validándose abajo). Otro formato = error como siempre.
        if k == 'colores.piel_y_cara' and isinstance(v, dict) and set(v) == {'piel', 'cara'}:
            out['colores.piel'], out['colores.cara'] = v['piel'], v['cara']; continue
        if k not in CONTROLES and k != 'gafas_color': err.append(f'control «{k}» no existe (usar: {", ".join(CONTROLES)})'); continue
        out[k] = v
    for k, v in out.items():
        if k.startswith('colores.') or k == 'gafas_color':
            if not (isinstance(v, list) and len(v) >= 3 and all(isinstance(x, (int, float)) and 0 <= x <= 1 for x in v[:3])): err.append(f'{k}: color debe ser [r,g,b] entre 0 y 1')
    pu = out.get('pulsera')
    if pu is not None and not (isinstance(pu, dict) and pu.get('muneca') in ('izquierda', 'derecha')): err.append('pulsera: falta «muneca» izquierda|derecha')
    return out, err


# ---------------- geometría de la cámara del molde ----------------
def _n(v):
    l = math.sqrt(sum(x * x for x in v)) or 1.0; return [x / l for x in v]


def _cross(a, b): return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def proyectar(cam, p, aspecto=(16, 9)):
    """(u, v, delante) en el cuadro de la cámara del molde: u 0 = izquierda, 1 = derecha; v 0 = arriba."""
    loc, d, up = cam['loc'], _n(cam['dir']), _n(cam.get('arriba') or [0, 0, 1])
    r = _n(_cross(d, up)); up2 = _cross(r, d); q = [p[i] - loc[i] for i in range(3)]
    z = sum(q[i] * d[i] for i in range(3)); x = sum(q[i] * r[i] for i in range(3)); y = sum(q[i] * up2[i] for i in range(3))
    if z <= 1e-3: return None, None, False
    f = float(cam.get('lente_mm') or 35) / float(cam.get('sensor_ancho_mm') or 36)
    return 0.5 + x / z * f, 0.5 - y / z * f * aspecto[0] / aspecto[1], True


def estado_en(K, C, per, t):
    """Posición [x,y,z] y giro (grados) del personaje en el segundo t (interpolado entre inicio y fin del segmento)."""
    segs = sorted(per.get('segmentos') or [], key=lambda s: float(s['t'][0])); rot = None; last = None
    for s in segs:
        t0, t1 = float(s['t'][0]), float(s['t'][1]); r = K._num(s.get('rot')); rot = r if r is not None else rot
        a, b = K._xyz(C, s['pos'][0]), K._xyz(C, s['pos'][-1]); last = (b, rot)
        if t0 - 1e-6 <= t <= t1 + 1e-6 and a and b:
            u = 0 if t1 <= t0 else (t - t0) / (t1 - t0)
            return [a[i] + (b[i] - a[i]) * u for i in range(3)], rot
    return (last if last else (None, None))


def geometria(K, C, per, cam, t, aspecto):
    pos, rot = estado_en(K, C, per, t)
    if pos is None: return None
    h = float(K._num(per.get('altura')) or 1.7)
    cen = [pos[0], pos[1], pos[2] + h * 0.55]; u, v, dl = proyectar(cam, cen, aspecto)
    g = {'u': None if u is None else round(u, 3), 'v': None if v is None else round(v, 3), 'delante': dl}
    g['en_cuadro'] = bool(dl and -0.05 <= u <= 1.05 and -0.1 <= v <= 1.1)
    g['lado_pantalla'] = None if u is None else ('izquierda' if u < 0.38 else 'derecha' if u > 0.62 else 'centro')
    if rot is not None:
        f = [math.cos(math.radians(rot)), math.sin(math.radians(rot))]
        tc = _n([cam['loc'][0] - pos[0], cam['loc'][1] - pos[1]]); c = f[0] * tc[0] + f[1] * tc[1]
        g['coseno_a_camara'] = round(c, 3)
        g['cuerpo'] = 'frente' if c > 0.5 else 'espalda' if c < -0.5 else 'perfil'
        izq = [-f[1], f[0]]   # mano izquierda del personaje (giro +90°, visto desde arriba)
        ml = [pos[0] + izq[0] * 0.22, pos[1] + izq[1] * 0.22, pos[2] + h * 0.5]; mr = [pos[0] - izq[0] * 0.22, pos[1] - izq[1] * 0.22, pos[2] + h * 0.5]
        ul, _, _ = proyectar(cam, ml, aspecto); ur, _, _ = proyectar(cam, mr, aspecto)
        if ul is not None and ur is not None: g['mano_izquierda_en_pantalla'] = 'izquierda' if ul < ur else 'derecha'
    return g


# ---------------- pedido ----------------
def pedido(K, D, a, e, cd, PC, guion, avisos):
    cf = DI._cfg(); txt = PG.texto(cf['prompt']); esq = PG.texto(cf['esquema'])
    M, err = K.molde(D, e['escenario_id'])
    if err: return None, err
    S = DI.escenario(K, M, e['numero'], e['escenario_id'], avisos)
    S['objects'] = [o for o in S['objects'] if not re.match(r'^(marca_|flecha_|rej_)', o['name'])]   # marcas del plano, no son del set
    if not S['floor_bounds']: return None, f"el molde {e['escenario_id']} no trae medidas de objetos (no se puede poner a nadie sin inventar)"
    if not (M or {}).get('camaras_molde'): return None, f"el molde {e['escenario_id']} no trae cámaras: el 01 solo usa cámaras del molde"
    # 2026-11-01 PREVENIR: solo cámaras que la geometría comprueba (antes se ofrecían TODAS las del set → toma_04 con cam_04_esc10).
    # Política escena_y_set (Ricardo t299u): propias primero + las del mismo set que ven la zona de esta escena.
    asp = K.aspecto(cd) or (16, 9)
    of, inf_cam = AC.camaras_validas(sys.modules[__name__], M, S, e['numero'], asp, AC.ajustes_01()['camaras'])
    caja = {i['nombre']: i['suelo_visible_caja_xy'] for i in inf_cam['camaras']}
    zpct = {i['nombre']: i['zona_escena_visible_pct'] for i in inf_cam['camaras']}
    S['cameras'] = [{'name': c['nombre'], 'loc': c.get('loc'), 'direction': c.get('dir'), 'lens_mm': c.get('lente_mm'), 'made_for_scene': c.get('escena_molde'),
                     'own_scene': str(c.get('escena_molde')) == str(e['numero']), 'sees_floor_xy': caja.get(c['nombre']),
                     'sees_this_scene_area_pct': zpct.get(c['nombre'])} for c in of]
    S['all_camera_names'] = [c['nombre'] for c in of]
    if not S['cameras']: return None, f"ninguna cámara del molde {e['escenario_id']} ve el suelo libre de la escena {e['numero']} (revisar cámaras del molde)"
    if not any(i['propia'] and i['ofrecida'] for i in inf_cam['camaras']): avisos.append(f"escena {e['numero']}: {inf_cam['motivo']}")
    fichas, imgs, det = DI.personajes_escena(K, D, a, e, PC, avisos)
    if det and cf['si_falta_ref'] == 'detener': return None, '; '.join(det)
    fijos = {}
    for f in fichas:
        g = guardados(a.canal, f['id'])
        if g: fijos[f['id']] = g; f['stored_3d_parameters'] = True
    fmt = {'aspect': (cd or {}).get('aspect'), 'fps_default': cf['fps_por_defecto'], 'frame_height_pct': ((cd or {}).get('paso01') or {}).get('alto_cuadro_pct')}
    prompt = (txt + '\n\n=== THE_SET ===\n' + json.dumps(S, ensure_ascii=False, indent=1) + '\n=== END THE_SET ==='
              + '\n\n=== CHARACTERS ===\n' + json.dumps(fichas, ensure_ascii=False, indent=1) + '\n=== END CHARACTERS ==='
              + '\n\n=== PARAMETER_DICTIONARY ===\n' + json.dumps(diccionario(), ensure_ascii=False) + '\n=== END PARAMETER_DICTIONARY ==='
              + '\n\n=== STORED_3D_PARAMETERS ===\n' + json.dumps(fijos, ensure_ascii=False) + '\n=== END STORED_3D_PARAMETERS ==='
              + '\n\n=== SCENE ===\n' + json.dumps(e['datos'], ensure_ascii=False, indent=1) + '\n=== END SCENE ==='
              + ('\n\n=== SCRIPT ===\n' + guion + '\n=== END SCRIPT ===' if guion else '')
              + '\n\n=== FORMAT ===\n' + json.dumps(fmt, ensure_ascii=False) + '\n=== END FORMAT ===\n\nSCHEMA\n' + esq)
    return {'prompt': prompt, 'texto': txt, 'esquema': json.loads(esq), 'adjuntos': imgs, 'set': S, 'fichas': fichas, 'avisos_refs': det,
            'molde': M, 'fijos': fijos, 'aspecto': asp, 'camaras_informe': inf_cam}, None


# ---------------- validación ----------------
_RX_NO_EXISTE = re.compile(r'^(tomas\[\d+\] \S+): la cámara «(.+?)» no existe en el molde .*$')


def _camara_no_ofrecida(x, P):
    m = _RX_NO_EXISTE.match(str(x)); todas = {c['nombre']: c for c in (P['molde'] or {}).get('camaras_molde') or []}
    if not m or m.group(2) not in todas: return x
    validas = P['set'].get('all_camera_names') or []
    return (f"{m.group(1)}: la cámara «{m.group(2)}» no está entre las cámaras ofrecidas para esta escena "
            f"(es de la escena {todas[m.group(2)].get('escena_molde')}); usar una de {validas}")


def normalizar(obj):
    """Salida estructurada (Vertex) no admite objetos libres: puntos y controles llegan como LISTAS → dict (lo que usan el 83 y el 02)."""
    if isinstance(obj.get('puntos'), list):
        obj['puntos'] = {str(x.get('nombre')): x.get('pos') for x in obj['puntos'] if isinstance(x, dict) and x.get('nombre')}
    for p in obj.get('personajes') or []:
        p3 = p.get('parametros_3d')
        if isinstance(p3, dict) and isinstance(p3.get('controles'), list):
            d = {}
            for x in p3['controles']:
                try: d[str(x.get('control'))] = json.loads(x.get('valor_json'))
                except Exception: d[str(x.get('control'))] = x.get('valor_json')
            p3['controles'] = d
    return obj


def validar(K, obj, e, P):
    obj = normalizar(obj)
    C, err = _VALIDAR_83(K, obj, e, P); av = []
    err = [_camara_no_ofrecida(x, P) for x in err]   # 2026-11-01: «no existe en el molde» → mensaje claro con las cámaras válidas
    for ruta, s in _todas_cadenas(obj):
        m = latino(s)
        if m: err.append(f'{ruta}: caracteres que no son del alfabeto latino {m[:6]}')
    dic = diccionario(); params = {}
    for p in obj.get('personajes') or []:
        cid = next((pp['id'] for pp in C['personajes'] if K._norm(pp['id']) == K._norm(p.get('id'))), None)
        if not cid: continue
        if cid in P['fijos']: ctl, e2 = resolver_parametros(P['fijos'][cid], dic); origen = 'biblioteca (aprobados)'
        else: ctl, e2 = resolver_parametros(p.get('parametros_3d'), dic); origen = 'Argon (diccionario)'
        err += [f'{cid}.parametros_3d: {x}' for x in e2]; params[cid] = {'controles': ctl, 'origen': origen}
    cams = {c['nombre']: c for c in (P['molde'] or {}).get('camaras_molde') or []}
    ids = {pp['id'] for pp in C['personajes']}; PER = {pp['id']: pp for pp in C['personajes']}
    tomas = obj.get('tomas') or []; lado_prev = {}
    for i, t in enumerate(tomas):
        q = f"tomas[{i}] {t.get('id')}"
        if not t.get('camara_molde'): err.append(f'{q}: sin cámara del molde (solo se aceptan cámaras del molde)'); continue
        if t.get('camara'): err.append(f'{q}: trae cámara inventada (loc/mira): solo cámaras del molde')
        w = t.get('palabras')
        if not isinstance(w, dict): err.append(f'{q}: falta la sección «palabras»'); continue
        for ruta, s in _todas_cadenas(w):
            if ruta.startswith('en_cuadro') or ruta.endswith('.id'): continue
            if re.search(r'\d', s): err.append(f'{q}.palabras.{ruta}: tiene números (solo palabras): «{s[:60]}»')
            low = s.lower()
            for x in PROHIBIDAS:
                if x in low: err.append(f'{q}.palabras.{ruta}: nombra el molde/cámara/coordenadas («{x}»)')
        enc = [x for x in w.get('en_cuadro') or [] if isinstance(x, str)]
        fuera = [x for x in enc if x not in ids]
        if fuera: err.append(f'{q}: en_cuadro con ids que no son de la escena {fuera}')
        if not isinstance(w.get('personas'), int) or w.get('personas') != len(enc): err.append(f"{q}: personas={w.get('personas')} pero en_cuadro tiene {len(enc)}")
        mv = w.get('manos_visibles')
        if not isinstance(mv, int) or mv < 0 or mv > 2 * len(enc): err.append(f'{q}: manos_visibles={mv} imposible para {len(enc)} personas')
        pp = {x.get('id'): x for x in w.get('por_personaje') or [] if isinstance(x, dict)}
        if set(pp) != set(enc): err.append(f'{q}: por_personaje {sorted(pp)} no coincide con en_cuadro {sorted(enc)}')
        for k in ('composicion', 'fondo'):
            if not str(w.get(k) or '').strip(): err.append(f'{q}: palabras.{k} vacío')
        cam = cams.get(t['camara_molde']); tm = None
        tt = t.get('t') or []
        if len(tt) == 2 and all(K._num(x) is not None for x in tt): tm = (float(tt[0]) + float(tt[1])) / 2
        geo = {}
        for cid, x in pp.items():
            if cid not in ids: continue
            for k, ok in (('cuerpo', CUERPO), ('cabeza', CUERPO), ('lado_pantalla', LADOS), ('mano_accesorio', MANO)):
                if x.get(k) not in ok: err.append(f'{q}.{cid}.{k}: «{x.get(k)}» no es uno de {ok}')
            for k in ('mirada', 'emocion'):
                if not str(x.get(k) or '').strip(): err.append(f'{q}.{cid}.{k} vacío')
            err += _PP.validar_toma(q, cid, x)   # o110: pose opcional; palabra fuera de la biblioteca de poses = rechazo (FALTA)
            pu = (params.get(cid, {}).get('controles') or {}).get('pulsera')
            if isinstance(pu, dict) and x.get('mano_accesorio') in ('izquierda', 'derecha') and x['mano_accesorio'] != pu.get('muneca'):
                err.append(f"{q}.{cid}: mano_accesorio {x['mano_accesorio']} pero su ficha 3D la lleva en la {pu.get('muneca')}")
            if not pu and x.get('mano_accesorio') in ('izquierda', 'derecha'): av.append(f'{q}.{cid}: dice mano_accesorio pero su ficha 3D no tiene accesorio de muñeca')
            if cam and tm is not None:
                g = geometria(K, C, PER[cid], cam, tm, P['aspecto']); geo[cid] = g
                if not g: continue
                if not g['en_cuadro']: err.append(f"{q}.{cid}: Argon dice que se ve, pero la cámara {t['camara_molde']} no lo ve en su posición")
                if g.get('cuerpo') == 'espalda' and x.get('cuerpo') in ('frente', 'tres_cuartos_frente'): err.append(f"{q}.{cid}: palabras dicen {x['cuerpo']} pero según su giro está de ESPALDA a la cámara")
                if g.get('cuerpo') == 'frente' and x.get('cuerpo') in ('espalda', 'tres_cuartos_espalda'): err.append(f"{q}.{cid}: palabras dicen {x['cuerpo']} pero según su giro está de FRENTE a la cámara")
                if g['lado_pantalla'] and {g['lado_pantalla'], x.get('lado_pantalla')} == {'izquierda', 'derecha'}:
                    err.append(f"{q}.{cid}: palabras dicen lado {x.get('lado_pantalla')} pero la cámara lo ve a la {g['lado_pantalla']}")
                if isinstance(pu, dict) and g.get('mano_izquierda_en_pantalla'):
                    li = g['mano_izquierda_en_pantalla']; g['lado_pantalla_accesorio'] = li if pu['muneca'] == 'izquierda' else ('derecha' if li == 'izquierda' else 'izquierda')
            if cid in lado_prev and x.get('lado_pantalla') in ('izquierda', 'derecha') and lado_prev[cid] in ('izquierda', 'derecha') and x['lado_pantalla'] != lado_prev[cid]:
                av.append(f'{q}.{cid}: cambia de lado de la pantalla respecto de la toma anterior (revisar eje)')
            if x.get('lado_pantalla'): lado_prev[cid] = x['lado_pantalla']
        for k in ids - set(enc):
            if cam and tm is not None:
                g = geometria(K, C, PER[k], cam, tm, P['aspecto'])
                if g and g['en_cuadro'] and 0.15 < (g['u'] or 0) < 0.85: av.append(f'{q}: {k} no está en en_cuadro pero la cámara lo ve en el centro')
        tp = next((x for x in C['tomas_plan'] if x['id'] == str(t.get('id') or f't{i + 1}')), None)
        if tp is not None: tp.update({'camara_molde': t['camara_molde'], 'palabras': w, 'geometria_codigo': geo,
                                      'camara_datos': {k: cam.get(k) for k in ('loc', 'dir', 'arriba', 'lente_mm', 'sensor_ancho_mm')} if cam else None})
    rv = obj.get('revision')
    if not isinstance(rv, list) or not rv: err.append('falta «revision» (Argon no revisó contradicciones)')
    else:
        hechos = {str(x.get('chequeo')) for x in rv if isinstance(x, dict)}
        falt = [c for c in CHEQUEOS if c not in hechos]
        if falt: av.append(f'revision sin los chequeos {falt}')
    C.update({'parametros_3d': params, 'revision_argon': rv, 'avisos_codigo': av, 'version_01': 'o109', 'aspecto': list(P['aspecto'])})
    return C, err


# ---------------- cubo ----------------
def cubo01(K, D, a, cd, PC):
    DI.validar = validar   # el camino pago del 83 usa ESTA validación
    faltan = [f'archivo {x} (cajas/)' for x in PG.archivos_que_faltan('01')]
    if faltan: return K.r_base('01', D, {'ok': False, 'faltan': faltan, 'resumen': '01 · falta ' + ', '.join(faltan)})
    guion = K._guion(D); avisos, filas, ctx = [], [], {}
    if not guion: faltan.append('guion completo (bloque GUION_COMPLETO de pedidos/*.txt): se dirige solo con la escena del mapa')
    rv_arch = getattr(a, 'revalidar', None)
    for e in K.escenas(D, a.solo):
        n = e['numero']; P, err = pedido(K, D, a, e, cd, PC, guion, avisos)
        ya = K.leer(D / 'cubos' / '01' / f'esc_{n}.json')
        fila = {'escena': n, 'escenario_id': e['escenario_id'], 'personajes_en_cuadro': e['personajes'],
                'ya_dirigida_o109': bool(isinstance(ya, dict) and ya.get('version_01') == 'o109')}
        if err: filas.append({**fila, 'tiene_molde': False, 'cotizacion': None, 'por_que': err}); faltan.append(f'escena {n}: {err}'); continue
        (D / 'cubos' / '01' / 'pedidos').mkdir(parents=True, exist_ok=True)
        (D / 'cubos' / '01' / 'pedidos' / f'esc_{n}.txt').write_text(P['prompt'], encoding='utf-8')
        cot = K.cotizar(len(P['prompt']), len(P['adjuntos']), cd, '01'); ctx[n] = (e, P, cot)
        fila.update({'tiene_molde': True, 'cotizacion': cot, 'imagenes_personajes': len(P['adjuntos']), 'camaras_molde': [c['name'] for c in P['set']['cameras']],
                     'camaras_descartadas': {i['nombre']: i['por_que'] for i in P['camaras_informe']['camaras'] if not i['ofrecida']},
                     'parametros_guardados': sorted(P['fijos']), 'pedido': str(D / 'cubos' / '01' / 'pedidos' / f'esc_{n}.txt')})
        if rv_arch:
            fila['revalidacion'] = revalidar(K, D, n, e, P, rv_arch)
        filas.append(fila)
    tot = round(sum((f.get('cotizacion') or {}).get('usd') or 0 for f in filas), 4)
    if getattr(a, 'correr', False):   # no borrar nada: una rechazada anterior se guarda con fecha antes de que el pago escriba encima
        for n in ctx:
            r0 = D / 'cubos' / '01' / 'rechazadas' / f'esc_{n}.json'
            if r0.is_file(): r0.replace(r0.with_name(f"esc_{n}.antes_{time.strftime('%Y%m%d-%H%M%S')}.json"))
    pago = DI._pagar01(K, D, a, cd, ctx, filas) if getattr(a, 'correr', False) else None
    out = K.r_base('01', D, {'version': 'o109', 'escenas': filas, 'total_usd_peor_caso': tot, 'faltan': sorted(set(faltan)), 'avisos': sorted(set(avisos))[:30],
                             'pistas': ['PISTA INMI (o109): solo cámaras del molde + «palabras» por toma + parametros_3d con el diccionario + revisión de Argon; el código cruza las palabras con la cámara real.',
                                        'PISTA INMI (o109): pagar = guarda cajas/HABILITAR_PAGO_01 + «--correr --ok USD --aprobado QUIEN [--escena N]». Sin eso solo cotiza.'],
                             'resumen': f'01 o109 · cotizado {len(ctx)}/{len(filas)} escenas: US$ {tot} peor caso' + ('' if pago else ' (no se llamó a Argon)')})
    if pago:
        rp = reparar_pagando(K, D, a, cd, ctx, filas, pago)
        if rp: pago['reparaciones'] = rp; pago['usd_gastado'] = round(float(pago.get('usd_gastado') or 0) + rp['usd_gastado'], 6)
    if pago: out.update(pago)
    out['archivo'] = K.guardar(D / 'cubos' / '01' / 'cotizacion.json', out)
    return out


def cd_reparacion(cd, cf=None):
    """Canal para la reparación: igual al del 01, salvo 01.reparar_max_salida_tokens (si Ricardo lo fija, baja el peor caso; null = el del canal)."""
    cf = cf or DI._cfg(); m = cf.get('reparar_max_salida_tokens')
    if not m: return cd
    c = copy.deepcopy(cd or {}); p = c.setdefault('paso01', {}); p['max_output_tokens'] = min(int(m), int(p.get('max_output_tokens') or m)); return c


def fragmentos_reparacion(texto_fijo):
    """2026-11-06 (Ricardo t499u). El texto fijo de reparación lleva el hueco «{INTENTO}», que prompt_reparacion rellena con el número
    del intento. La guarda (myia_fijo_prompt.fragmentos_en_orden) buscaba el texto fijo ENTERO, con «{INTENTO}» literal, en el prompt
    ya rellenado: nunca lo encontraba y bloqueaba TODA reparación aunque el sha coincidiera. El sha sigue calculándose sobre el texto
    fijo completo (sin cambios); aquí solo se dan los trozos fijos entre huecos, en orden, que sí deben aparecer tal cual."""
    return [t for t in str(texto_fijo).split('{INTENTO}') if t.strip()] or [texto_fijo]


def reparar_pagando(K, D, a, cd, ctx, filas, pago, validar_fn=None, cf=None):
    """2026-11-01 REPARAR + CONSERVAR + LÍMITE, camino pago. Solo para escenas que el CÓDIGO rechazó en ESTA corrida (rechazadas/esc_N.json
    con el ledger de esta corrida). Cada intento: guarda HABILITAR_PAGO_01 de nuevo, cotización fresca del prompt de reparación (sin imágenes),
    que no pase lo que queda del --ok, PG.correr (ledger ANTES, tope por llamada, intentos acotados). Nada aquí paga si falta algo de eso."""
    p = (pago or {}).get('pago') or {}
    aj = AC.ajustes_01(); mx = aj['reparaciones_max']
    if getattr(a, 'max_reparaciones', None) is not None: mx = max(0, min(mx, int(a.max_reparaciones)))
    if mx <= 0 or not p.get('llamado'): return None
    cf = cf or DI._cfg(); V = validar_fn or validar; usado = float(p.get('bolsa_peor_caso') or 0); hechas = []; total = 0.0
    for h in p.get('escenas') or []:
        n = h.get('escena')
        if h.get('ok') or n not in ctx: continue
        R = K.leer(D / 'cubos' / '01' / 'rechazadas' / f'esc_{n}.json')
        if not (isinstance(R, dict) and R.get('errores') and isinstance(R.get('respuesta'), dict) and R.get('ledger') == h.get('ledger')): continue
        e, P, _ = ctx[n]; rel = cf.get('prompt_reparar') or AC.PROMPT_REPARAR
        if not (AC.AQUI / rel).is_file(): hechas.append({'escena': n, 'ok': False, 'error': f'falta cajas/{rel}'}); continue
        texto_fijo = PG.texto(rel); esq = AC.esquema_reparacion(P['esquema']); cdr = cd_reparacion(cd, cf); modelo, nivel, mo = K.modelo_canal(cdr)
        if not getattr(a, 'X', None): a.X = PG.app()
        X = a.X; fx = PG.fijo('01', texto_fijo, json.dumps(esq, ensure_ascii=False, sort_keys=True), modelo, nivel, mo, X.get('FP'))
        fx['fragmentos'] = fragmentos_reparacion(texto_fijo)   # 2026-11-06: el hueco {INTENTO} se rellena; se compara lo fijo de alrededor
        gasto = {'usd': 0.0}

        def armar(obj, g, k, P=P, texto_fijo=texto_fijo, esq=esq): return AC.prompt_reparacion(texto_fijo, P['set'], P['fichas'], obj, g, k, esq, extra=P.get('vocabulario'))

        def llamar(prompt, k, n=n, esq=esq, fx=fx, X=X, modelo=modelo, nivel=nivel, mo=mo, gasto=gasto, cdr=cdr):
            msg = PG.revisar_guarda('01', a.ok, a.aprobado)
            if msg: return None, {'parar': True, 'por_que': msg}
            cot = K.cotizar(len(prompt), 0, cdr, '01'); resto = round(float(a.ok) - usado - total - gasto['usd'], 6)
            if not cot.get('ok'): return None, {'parar': True, 'por_que': 'sin cotización para la reparación'}
            if float(cot['usd']) > resto + 1e-9:
                return None, {'parar': True, 'cotizacion_usd': cot['usd'], 'por_que': f"reparación cotizada US${cot['usd']} > lo que queda del --ok (US${resto}): no se llama"}
            sal = D / 'cubos' / '01' / 'respuestas' / f'esc_{n}.reparacion_{k}.txt'; sal.parent.mkdir(parents=True, exist_ok=True)
            q = {'clave': f'esc{n}-rep{k}', 'prompt': prompt, 'salida': sal, 'est': cot['usd'], 'adjuntos': None, 'esquema': esq, 'modelo': modelo,
                 'nivel': nivel, 'max_out': mo, 'fijo': fx, 'nota': f'cubo 01 repara esc {n} (reparación {k})'}
            a2 = copy.copy(a); a2.ok = resto
            res, bolsa = PG.correr([q], a2, X, cdr, '01'); r = res[0]; gasto['usd'] += float(bolsa['gastado'])
            info = {'cotizacion_usd': cot['usd'], 'usd': round(float(bolsa['gastado']), 6), 'ledger': r.get('ledger'), 'error': r.get('error')}
            if not r.get('ok'): info['parar'] = True; return None, info
            rv = PG.LS.revisar_respuesta(r['texto'], esq, r.get('fin'))
            if rv['obj'] is None or rv.get('esquema_errores'): info['error'] = f"respuesta no válida ({rv['estado']}; {rv.get('esquema_errores', [])[:3]})"; return None, info
            return rv['obj'], info
        B = AC.bucle(lambda o, e=e, P=P: V(K, o, e, P), n, R['respuesta'], R['errores'], llamar, armar, mx, P['fichas'])
        total += gasto['usd']; fila = next((f for f in filas if f['escena'] == n), {})
        reg = {'escena': n, 'ok': B['ok'], 'intentos': B['intentos'], 'usd': round(gasto['usd'], 6)}
        K.guardar(D / 'cubos' / '01' / 'rechazadas' / f'esc_{n}.reparaciones.json', {**reg, 'errores_finales': B.get('errores'), 'plan_fusionado': B['obj'],
                                                                                  'explicacion': B['explicacion']})
        if B['ok']:
            C = B['C']; C.update({'de': 'argon + autocorrección (reparación parcial)', 'ledger': R['ledger'], 'ledgers_reparacion': [x.get('ledger') for x in B['intentos']],
                                  'usd': round(float(h.get('usd') or 0) + gasto['usd'], 6), 'aprobado_por': a.aprobado, 'fecha': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                                  'reparaciones': B['intentos'], 'refs_personajes': {f['id']: f['images'] for f in P['fichas']}})
            f1 = D / 'cubos' / '01' / f'esc_{n}.json'; resp = None
            if f1.is_file():
                resp = D / 'cubos' / '01' / 'respaldos' / f"esc_{n}.{time.strftime('%Y%m%d-%H%M%S')}.json"; resp.parent.mkdir(parents=True, exist_ok=True); resp.write_bytes(f1.read_bytes())
            K.guardar(f1, C); reg['archivo'] = str(f1); fila.update({'ya_dirigida_o109': True, 'archivo': str(f1), 'respaldo_anterior': str(resp) if resp else None, 'reparada': True})
        else:
            reg['explicacion'] = B['explicacion']; fila['explicacion_para_ricardo'] = B['explicacion']
        hechas.append(reg)
    if not hechas: return None
    return {'escenas': hechas, 'usd_gastado': round(total, 6), 'max_reparaciones': mx}


def revalidar(K, D, n, e, P, arch):
    """GRATIS: valida con el código una respuesta de Argon ya pagada (archivo JSON) y, si pasa, escribe cubos/01/esc_N.json (respaldando el anterior)."""
    f = Path(str(arch).replace('{n}', str(n)))
    if not f.is_file(): return {'ok': False, 'error': f'no existe {f}'}
    txt = f.read_text(encoding='utf-8'); i, j = txt.find('{'), txt.rfind('}')
    try: obj = json.loads(txt[i:j + 1])
    except Exception as ex: return {'ok': False, 'error': f'no es JSON ({type(ex).__name__})'}
    C, err = validar(K, obj, e, P)
    if err:
        K.guardar(D / 'cubos' / '01' / 'rechazadas' / f'esc_{n}.o109.json', {'errores': err, 'respuesta': obj, 'de': str(f)})
        return {'ok': False, 'errores': len(err), 'primeros': err[:8]}
    f1 = D / 'cubos' / '01' / f'esc_{n}.json'
    if f1.is_file():
        r = D / 'cubos' / '01' / 'respaldos' / f"esc_{n}.{time.strftime('%Y%m%d-%H%M%S')}.json"; r.parent.mkdir(parents=True, exist_ok=True); r.write_bytes(f1.read_bytes())
    C.update({'de': 'argon (revalidado o109)', 'respuesta': str(f)}); K.guardar(f1, C)
    return {'ok': True, 'archivo': str(f1), 'tomas': len(C['tomas_plan']), 'avisos_codigo': C['avisos_codigo'][:8]}


def main(argv):
    import argparse
    import paso01_cubos as K
    ap = argparse.ArgumentParser(prog='ver o109 cubo01')
    ap.add_argument('--canal', required=True); ap.add_argument('--capitulo', required=True); ap.add_argument('--escena', default='')
    ap.add_argument('--revalidar', default=None, help='archivo de respuesta ya pagada ({n} = escena): valida gratis')
    ap.add_argument('--correr', action='store_true'); ap.add_argument('--ok', type=float, default=None); ap.add_argument('--aprobado', default=None)
    ap.add_argument('--max-intentos', dest='max_intentos', type=int, default=None)
    ap.add_argument('--max-reparaciones', dest='max_reparaciones', type=int, default=None, help='0 = no reparar; nunca más que 01.reparaciones_max')
    a = ap.parse_args(argv); a.solo = {x for x in a.escena.split(',') if x}
    D = K.carpeta(a.canal, a.capitulo)
    if not D: return {'ok': False, 'caja': 'cubo', 'cubo': '01', 'error': f'no hay carpeta del capítulo {a.capitulo} del canal {a.canal}'}
    return cubo01(K, D, a, K.canal(a.canal), K.personajes_canal(a.canal))
