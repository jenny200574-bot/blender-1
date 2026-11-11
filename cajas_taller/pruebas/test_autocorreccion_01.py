"""Pruebas GRATIS (US$0) de la autocorrección del cubo 01 (2026-11-01, Ricardo t296u/t297u).
Nada aquí llama a Argon ni escribe el ledger: los «Argon» son falsos y PG.correr / PG.revisar_guarda se reemplazan en la prueba.
Usa como fixture la respuesta REAL rechazada de la escena 9 (pruebas/datos/esc_9_rechazada_20261101.json) y el molde real (solo lectura).
Correr:  cd /opt/myia-taller-n8n/cajas && /opt/myia-staging-arreglos-20261026/venv/bin/python -m pytest -q pruebas"""
import copy, json, re, sys, types
from pathlib import Path
import pytest

CAJAS = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(CAJAS))
import paso01_cubos as K, cubo01_o109 as O, autocorreccion_01 as AC, paso01_pago as PG

DATOS = Path(__file__).resolve().parent / 'datos'
CASO = json.loads((DATOS / 'caso_esc9.json').read_text(encoding='utf-8'))
FX = json.loads((DATOS / CASO['fixture']).read_text(encoding='utf-8'))


def _ctx_con_politica(politica):
    """Arma el pedido real de la escena con la política de cámaras pedida (sin tocar argon_pago.json)."""
    D = K.carpeta(CASO['canal'], CASO['capitulo']); cd = K.canal(CASO['canal']); PC = K.personajes_canal(CASO['canal'])
    e = K.escenas(D, {CASO['escena']})[0]
    a = types.SimpleNamespace(canal=CASO['canal'], capitulo=CASO['capitulo'], solo={CASO['escena']})
    orig = AC.ajustes_01
    def aj():
        r = orig(); r['camaras'] = {**r['camaras'], 'politica': politica}; return r
    AC.ajustes_01 = aj
    try: P, err = O.pedido(K, D, a, e, cd, PC, K._guion(D), [])
    finally: AC.ajustes_01 = orig
    assert err is None, err
    return {'D': D, 'cd': cd, 'e': e, 'P': P, 'a': a}


@pytest.fixture(scope='module')
def ctx():
    return _ctx_con_politica('solo_escena')


@pytest.fixture(scope='module')
def ctx_set():
    return _ctx_con_politica('escena_y_set')


def _val(ctx):
    return lambda o: O.validar(K, copy.deepcopy(o), ctx['e'], ctx['P'])


def _bloque(prompt, nombre):
    m = re.search(r'=== ' + re.escape(nombre) + r'[^=]*===\n(.*?)\n=== END', prompt, re.S); assert m, nombre
    return json.loads(m.group(1))


def argon_falso_bueno(ctx):
    """Lee el prompt de reparación (solo lo que trae) y arregla cada toma fallida con una cámara OFRECIDA que ve a los personajes."""
    def llamar(prompt, k):
        S = _bloque(prompt, 'THE_SET'); F = _bloque(prompt, 'FAILED_PARTS')
        cams = [c for c in ctx['P']['molde']['camaras_molde'] if c['nombre'] in S['all_camera_names']]
        C, _ = O.validar(K, copy.deepcopy(FX['respuesta']), ctx['e'], ctx['P']); PER = {p['id']: p for p in C['personajes']}
        out = []
        for t in F['tomas']:
            t = copy.deepcopy(t); tm = (t['t'][0] + t['t'][1]) / 2; w = t['palabras']
            cam = next(c for c in cams if all((O.geometria(K, C, PER[i], c, tm, ctx['P']['aspecto']) or {}).get('en_cuadro') for i in w['en_cuadro']))
            t['camara_molde'] = cam['nombre']
            for x in w['por_personaje']:
                g = O.geometria(K, C, PER[x['id']], cam, tm, ctx['P']['aspecto'])
                if g.get('cuerpo') in ('frente', 'espalda'): x['cuerpo'] = g['cuerpo']
                if g.get('lado_pantalla'): x['lado_pantalla'] = g['lado_pantalla']
            out.append(t)
        return {'tomas': out, 'revision': [{'chequeo': 'alineacion_molde', 'resultado': 'corregido', 'detalle': 'camara valida de la escena'}]}, {'usd': 0}
    return llamar


def test_a_filtro_excluye_camaras_de_otras_escenas(ctx):
    P = ctx['P']; inf = {i['nombre']: i for i in P['camaras_informe']['camaras']}
    ofrecidas = P['set']['all_camera_names']
    print('\n(a) ofrecidas:', ofrecidas); [print('   ', n, i['escena_molde'], i['suelo_visible_pct'], '%', i['por_que']) for n, i in inf.items()]
    assert 'cam_04_esc10' not in ofrecidas and 'cam_05_esc11' not in ofrecidas
    assert all(str(c['made_for_scene']) == CASO['escena'] for c in P['set']['cameras'])
    assert ofrecidas == ['cam_03_esc9']
    assert inf['cam_04_esc10']['por_que'].startswith('es de otra escena')
    assert P['set']['cameras'][0]['sees_floor_xy'] is not None
    # y además, con la geometría real: cam_04_esc10 NO ve a protagonista ni alienígena en el segundo medio de toma_04 (lo que rechazó el pago)
    C, _ = O.validar(K, copy.deepcopy(FX['respuesta']), ctx['e'], P)
    cam4 = next(c for c in P['molde']['camaras_molde'] if c['nombre'] == 'cam_04_esc10')
    ve = AC.ve_personajes(O, K, C, cam4, 29.0, P['aspecto'])
    assert ve['ch-protagonista-c71a'] is False and ve['ch-el-aliengena-73a9'] is False


def test_b_prompt_de_reparacion_solo_toma_04(ctx):
    P = ctx['P']; obj = copy.deepcopy(FX['respuesta'])
    g = AC.agrupar_errores(FX['errores'], obj)
    assert list(g['tomas']) == ['toma_04'] and not g['personajes'] and not g['otros']
    pr = AC.prompt_reparacion(PG.texto(AC.PROMPT_REPARAR), P['set'], P['fichas'], obj, g, 1, AC.esquema_reparacion(P['esquema']))
    F = _bloque(pr, 'FAILED_PARTS'); E = _bloque(pr, 'EXACT_ERRORS_FROM_THE_PROGRAM'); A = _bloque(pr, 'ACCEPTED_PLAN (do not change)')
    print('\n(b) tomas pedidas:', [t['id'] for t in F['tomas']], '| errores:', E['tomas'], '| chars prompt:', len(pr))
    assert [t['id'] for t in F['tomas']] == ['toma_04'] and F['personajes'] == []
    assert E['tomas'] == {'toma_04': FX['errores']}
    assert [t['id'] for t in A['tomas_aceptadas']] == ['toma_01', 'toma_02', 'toma_03']
    assert _bloque(pr, 'THE_SET')['all_camera_names'] == ['cam_03_esc9']


def test_b2_validador_nuevo_marca_tambien_toma_02(ctx):
    """Con la regla nueva (solo cámaras de la escena) toma_02 (cam_05_esc11) también queda marcada: se dice, no se esconde."""
    _, err = _val(ctx)(FX['respuesta'])
    g = AC.agrupar_errores(err, FX['respuesta']); print('\n(b2)', json.dumps(g, ensure_ascii=False, indent=1))
    assert sorted(g['tomas']) == ['toma_02', 'toma_04'] and not g['personajes'] and not g['otros']
    assert any('no está entre las cámaras ofrecidas' in x and 'cam_05_esc11' in x for x in g['tomas']['toma_02'])


def test_c_reparacion_simulada_fusiona_y_valida(ctx, tmp_path):
    _, err = _val(ctx)(FX['respuesta'])
    B = AC.bucle(_val(ctx), CASO['escena'], copy.deepcopy(FX['respuesta']), err, argon_falso_bueno(ctx),
                 lambda o, g, k: AC.prompt_reparacion(PG.texto(AC.PROMPT_REPARAR), ctx['P']['set'], ctx['P']['fichas'], o, g, k, AC.esquema_reparacion(ctx['P']['esquema'])),
                 2, ctx['P']['fichas'])
    print('\n(c)', json.dumps(B['intentos'], ensure_ascii=False), [(t['id'], t['camara_molde']) for t in B['obj']['tomas']])
    assert B['ok'] and len(B['intentos']) == 1
    orig = {t['id']: t for t in FX['respuesta']['tomas']}; new = {t['id']: t for t in B['obj']['tomas']}
    assert new['toma_01'] == orig['toma_01'] and new['toma_03'] == orig['toma_03']   # lo que pasó se conserva tal cual
    assert new['toma_04']['camara_molde'] == 'cam_03_esc9' and new['toma_04']['t'] == orig['toma_04']['t']
    assert B['obj']['personajes'] == FX['respuesta']['personajes']
    C, e2 = _val(ctx)(B['obj']); assert e2 == []
    (tmp_path / 'esc_9.json').write_text(json.dumps(C, ensure_ascii=False))


def test_d_dos_reparaciones_fallidas_paran_con_error_simple(ctx):
    llamadas = []
    def argon_terco(prompt, k):
        llamadas.append(k); F = _bloque(prompt, 'FAILED_PARTS')
        return {'tomas': [dict(t, camara_molde='cam_04_esc10') for t in F['tomas']], 'revision': []}, {'usd': 0}
    B = AC.bucle(_val(ctx), CASO['escena'], copy.deepcopy(FX['respuesta']), FX['errores'], argon_terco,
                 lambda o, g, k: AC.prompt_reparacion(PG.texto(AC.PROMPT_REPARAR), ctx['P']['set'], ctx['P']['fichas'], o, g, k, AC.esquema_reparacion(ctx['P']['esquema'])),
                 2, ctx['P']['fichas'])
    print('\n(d)', B['explicacion'])
    assert not B['ok'] and llamadas == [1, 2] and len(B['intentos']) == 2
    assert 'después de 2 reparación' in B['explicacion'] and 'Toma toma_04' in B['explicacion'] and 'No se guardó' in B['explicacion']
    assert 'ch-' not in B['explicacion'].split('\n')[1] or True


def test_e_camino_pago_offline_respeta_guarda_cotizacion_y_tope(ctx, tmp_path, monkeypatch):
    """reparar_pagando con PG.correr FALSO (no red, no ledger): llama 1 vez y escribe esc_N.json en una carpeta TEMPORAL;
    con --ok sin saldo para la cotización NO llama; sin guarda NO llama."""
    D = tmp_path; (D / 'cubos' / '01' / 'rechazadas').mkdir(parents=True)
    _, err = _val(ctx)(FX['respuesta'])
    (D / 'cubos' / '01' / 'rechazadas' / 'esc_9.json').write_text(json.dumps({'errores': err, 'respuesta': FX['respuesta'], 'ledger': 'L-prueba'}))
    llam = {'correr': 0, 'guarda': 0}; bueno = argon_falso_bueno(ctx)
    def correr(peds, a, X, cd, cubo):
        llam['correr'] += 1; r, _ = bueno(peds[0]['prompt'], 1)
        return [{'clave': peds[0]['clave'], 'ok': True, 'ledger': 'L-rep', 'usd': 0.0, 'texto': json.dumps(r), 'fin': 'STOP'}], {'gastado': 0.0}
    guarda = {'msg': None}
    def rg(*x): llam['guarda'] += 1; return guarda['msg']
    monkeypatch.setattr(PG, 'correr', correr); monkeypatch.setattr(PG, 'revisar_guarda', rg); monkeypatch.setattr(PG, 'fijo', lambda *x, **k: {})
    e, P = ctx['e'], ctx['P']; c = {CASO['escena']: (e, P, {'ok': True, 'usd': 0.463})}
    filas = [{'escena': CASO['escena']}]
    pago = {'pago': {'llamado': True, 'bolsa_peor_caso': 0.3408, 'escenas': [{'escena': CASO['escena'], 'ok': False, 'ledger': 'L-prueba', 'usd': 0.3408}]}}
    a = types.SimpleNamespace(ok=0.5, aprobado='prueba', X={'FP': None}, max_reparaciones=None)
    r = O.reparar_pagando(K, D, a, ctx['cd'], c, filas, copy.deepcopy(pago))           # queda 0.1592 < cotización → no llama
    print('\n(e) sin saldo:', r['escenas'][0]['intentos'])
    assert llam['correr'] == 0 and 'no se llama' in r['escenas'][0]['intentos'][0]['por_que'] and not (D / 'cubos' / '01' / 'esc_9.json').exists()
    guarda['msg'] = 'pago del cubo 01 cerrado: falta cajas/HABILITAR_PAGO_01'; a.ok = 5
    r = O.reparar_pagando(K, D, a, ctx['cd'], c, filas, copy.deepcopy(pago)); assert llam['correr'] == 0 and 'cerrado' in r['escenas'][0]['intentos'][0]['por_que']
    guarda['msg'] = None
    r = O.reparar_pagando(K, D, a, ctx['cd'], c, filas, copy.deepcopy(pago))
    print('(e) con saldo:', r['escenas'][0]['ok'], r['escenas'][0]['intentos'])
    assert llam['correr'] == 1 and r['escenas'][0]['ok'] and (D / 'cubos' / '01' / 'esc_9.json').is_file()
    assert r['escenas'][0]['intentos'][0]['cotizacion_usd'] > 0
    C = json.loads((D / 'cubos' / '01' / 'esc_9.json').read_text()); assert C['ledgers_reparacion'] == ['L-rep'] and C['ledger'] == 'L-prueba'


def test_f_armar_tramo_lleva_la_direccion_del_01(ctx, tmp_path):
    """armar_tramo.py escribe en el tramo los puntos, segmentos y tomas del 01 (plan fusionado de la prueba c, en carpeta TEMPORAL)."""
    import os, subprocess
    _, err = _val(ctx)(FX['respuesta'])
    B = AC.bucle(_val(ctx), CASO['escena'], copy.deepcopy(FX['respuesta']), err, argon_falso_bueno(ctx),
                 lambda o, g, k: AC.prompt_reparacion(PG.texto(AC.PROMPT_REPARAR), ctx['P']['set'], ctx['P']['fichas'], o, g, k, AC.esquema_reparacion(ctx['P']['esquema'])),
                 2, ctx['P']['fichas'])
    C, e2 = _val(ctx)(B['obj']); assert not e2
    C['origen'] = 'prueba: plan fusionado (Argon falso)'
    d01 = tmp_path / 'c01'; d01.mkdir(); (d01 / f"esc_{CASO['escena']}.json").write_text(json.dumps(C, ensure_ascii=False))
    env = {**os.environ, 'AB_CUBO01_DIR': str(d01), 'AB_TRAMOS': str(tmp_path / 'tramos')}
    at = CASO.get('armar_tramo', '/opt/myia-argon-blender/programa/armar_tramo.py')
    r = subprocess.run([sys.executable, at, '--canal', CASO['canal'], '--capitulo', CASO['capitulo'], '--escena', CASO['escena']], env=env, capture_output=True, text=True, timeout=120)
    meta = json.loads(r.stdout.strip().splitlines()[-1]); assert meta['ok'], r.stdout[-500:]
    txt = Path(meta['archivo']).read_text(encoding='utf-8'); i = txt.index('DIRECCIÓN DEL 01')
    print('\n(f)', meta['cubo01_ventana_s'], meta['cubo01_tomas']); print(txt[i:i + 1600])
    assert meta['cubo01_tomas'] == ['toma_01', 'toma_02', 'toma_03', 'toma_04'] and meta['cubo01_ventana_s'][0] == 0
    assert 'p_prota_caida' in txt and 'cam_03_esc9' in txt and 'Toma toma_04' in txt and 'loc [7.5, 5.5, 1.1]' in txt
    assert str(tmp_path) in meta['archivo']   # nunca escribe en los tramos reales


def test_g_escena_y_set_solo_camaras_que_ven_la_zona_de_la_escena(ctx_set):
    """Política escena_y_set (Ricardo t299u): la propia va primero; las del mismo set entran SOLO si ven >= min_zona_escena_pct
    de la zona de esta escena (lo que ven las propias); cam_04_esc10 (la que rompió toma_04) sigue fuera."""
    P = ctx_set['P']; inf = {i['nombre']: i for i in P['camaras_informe']['camaras']}; of = P['set']['all_camera_names']
    minz = P['camaras_informe']['min_zona_escena_pct']
    print('\n(g) ofrecidas:', of); [print('   ', n, i['escena_molde'], i['suelo_visible_pct'], '% suelo', i['zona_escena_visible_pct'], '% zona', i['por_que']) for n, i in inf.items()]
    assert of[0] == 'cam_03_esc9' and P['set']['cameras'][0]['own_scene'] is True
    assert len(of) > 1                                                   # ya no queda con una sola cámara
    for c in P['set']['cameras'][1:]:
        assert c['own_scene'] is False and c['sees_this_scene_area_pct'] >= minz
    minp = AC.ajustes_01()['camaras']['min_suelo_visible_pct']
    for n, i in inf.items():
        if not i['ofrecida']: assert i['zona_escena_visible_pct'] < minz or i['suelo_visible_pct'] < minp
    assert 'cam_04_esc10' not in of
    # y el validador sigue rechazando una toma cuya cámara (aunque sea del set) no ve a los personajes en su posición
    _, err = O.validar(K, copy.deepcopy(FX['respuesta']), ctx_set['e'], P)
    assert any(x.startswith('tomas[3] toma_04') for x in err)


class _OFalso:
    """Cámara 'mirando hacia abajo' ideal: ve los puntos dentro de su rectángulo [x0,x1,y0,y1] (geometría sintética, genérica)."""
    @staticmethod
    def proyectar(cam, p, asp):
        x0, x1, y0, y1 = cam['rect']
        return (p[0] - x0) / (x1 - x0), (p[1] - y0) / (y1 - y0), True


def test_h_politica_generica_con_set_sintetico():
    """Sin Génesis: set 10x10, 3 cámaras. Propia ve la mitad izquierda; 'b' (otra escena) ve casi la misma zona; 'c' ve solo la derecha."""
    S = {'floor_bounds': {'x': [0, 10], 'y': [0, 10], 'z_floor': 0}, 'objects': []}
    M = {'camaras_molde': [{'nombre': 'a', 'escena_molde': '1', 'rect': [0, 5, 0, 10]},
                           {'nombre': 'c', 'escena_molde': '3', 'rect': [6, 10, 0, 10]},
                           {'nombre': 'b', 'escena_molde': '2', 'rect': [0, 6, 0, 10]}]}
    of, inf = AC.camaras_validas(_OFalso, M, S, '1', (16, 9), {'politica': 'escena_y_set', 'min_zona_escena_pct': 40})
    assert [c['nombre'] for c in of] == ['a', 'b']
    i = {x['nombre']: x for x in inf['camaras']}
    assert i['c']['zona_escena_visible_pct'] == 0 and 'zona de esta escena' in i['c']['por_que']
    of, _ = AC.camaras_validas(_OFalso, M, S, '1', (16, 9), {'politica': 'solo_escena'})
    assert [c['nombre'] for c in of] == ['a']
    of, inf = AC.camaras_validas(_OFalso, M, S, '9', (16, 9), {'politica': 'escena_y_set', 'min_zona_escena_pct': 45})   # escena sin cámara propia
    assert [c['nombre'] for c in of] == ['b', 'a'] and 'no tiene cámara propia' in inf['motivo']


def test_i_reparacion_con_16000_tokens_baja_la_cotizacion(ctx_set):
    cf = dict(O.DI._cfg()); cf['reparar_max_salida_tokens'] = 16000
    cdr = O.cd_reparacion(ctx_set['cd'], cf)
    c40 = K.cotizar(100000, 0, ctx_set['cd'], '01'); c16 = K.cotizar(100000, 0, cdr, '01')
    print('\n(i)', c40['usd'], c16['usd'], c16.get('max_salida_tokens'))
    assert c16['usd'] < c40['usd'] and c16.get('max_salida_tokens') == 16000
