"""Pruebas GRATIS (US$0) del cubo 01 «solo acción» (accion_v1, 2026-11-01, reorganización; Ricardo [pt325u]).
Nada aquí llama a Argon ni escribe el ledger ni toca los archivos reales del capítulo: el «Argon» es falso, armar_tramo escribe en tmp.
Fixtures: pruebas/datos/esc_9_o109_20261101.json (dirección REAL ya pagada, o109) y esc_9_accion_falsa_20261101.json (FALSA, accion_v1).
Correr:  cd /opt/myia-taller-n8n/cajas && /opt/myia-staging-arreglos-20261026/venv/bin/python -m pytest -q pruebas"""
import copy, json, os, re, subprocess, sys, types
from pathlib import Path
import pytest

CAJAS = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(CAJAS))
import paso01_cubos as K, cubo01_accion as CA, autocorreccion_01 as AC, paso01_pago as PG

DATOS = Path(__file__).resolve().parent / 'datos'
CASO = json.loads((DATOS / 'caso_esc9.json').read_text(encoding='utf-8'))
FA = json.loads((DATOS / 'esc_9_accion_falsa_20261101.json').read_text(encoding='utf-8'))['respuesta']
O109 = json.loads((DATOS / 'esc_9_o109_20261101.json').read_text(encoding='utf-8'))
AT = CASO.get('armar_tramo', '/opt/myia-argon-blender/programa/armar_tramo.py')
LINEAS = '1036-1056'   # el tramo real de la escena 9 que corrió el 02N (7.7 s antes del arreglo)


@pytest.fixture(scope='module')
def ctx():
    D = K.carpeta(CASO['canal'], CASO['capitulo']); cd = K.canal(CASO['canal']); PC = K.personajes_canal(CASO['canal'])
    e = K.escenas(D, {CASO['escena']})[0]
    a = types.SimpleNamespace(canal=CASO['canal'], capitulo=CASO['capitulo'], solo={CASO['escena']})
    P, err = CA.pedido(K, D, a, e, cd, PC, K._guion(D), [])
    assert err is None, err
    return {'D': D, 'cd': cd, 'e': e, 'P': P, 'a': a}


def _val(ctx): return lambda o: CA.validar(K, copy.deepcopy(o), ctx['e'], ctx['P'])


def _bloque(prompt, nombre):
    m = re.search(r'=== ' + re.escape(nombre) + r'[^=]*===\n(.*?)\n=== END', prompt, re.S); assert m, nombre
    return json.loads(m.group(1))


def test_h_pedido_sin_camaras_con_zona_y_vocabulario(ctx):
    P = ctx['P']; S = _bloque(P['prompt'], 'THE_SET')
    assert 'cameras' not in S and 'all_camera_names' not in S and 'cam_' not in json.dumps(S)
    assert S.get('scene_area_xy') and len(S['scene_area_xy']) == 4
    assert _bloque(P['prompt'], 'ACTION_VERBS') and 'de_pie' in _bloque(P['prompt'], 'POSE_LIBRARY')
    esq = P['esquema']['properties']; assert 'tomas' not in esq and 'acciones' in esq and 'hechos' in esq
    assert 'acciones' in P['esquema']['required'] and 'tomas' not in P['esquema']['required']
    cot = K.cotizar(len(P['prompt']), len(P['adjuntos']), ctx['cd'], '01')
    print('\n(h) chars', len(P['prompt']), 'imgs', len(P['adjuntos']), 'zona', S['scene_area_xy'], 'cotizacion', cot)
    assert cot.get('ok') and cot['usd'] > 0


def test_i_respuesta_accion_pasa_y_es_compatible(ctx):
    C, err = _val(ctx)(FA)
    print('\n(i) errores', err, '\n    avisos', C['avisos_codigo'])
    assert not err
    assert C['version_01'] == 'accion_v1' and C['solo_accion'] is True and C['tomas_plan'] == []
    assert len(C['acciones']) == len(FA['acciones']) and len(C['hechos']) == 3
    e2, _ = K.validar_01(C); assert not e2                  # contrato de siempre (lo que leen 02/05/06/08)
    alt = {p['id']: p['altura'] for p in C['personajes']}
    assert alt['ch-protagonista-c71a'] == 1.72              # alturas: las de la ficha/diseño, no inventadas


def test_j_errores_de_accion_se_rechazan_y_agrupan(ctx):
    o = copy.deepcopy(FA)
    o['acciones'][0]['accion'] = 'volar'                    # verbo fuera del vocabulario
    o['acciones'][3]['pose'] = 'pose_heroica'               # pose inventada
    o['acciones'][6]['cita'] = 'Una frase que no existe en ningun lado del texto original inventada'
    o['acciones'][8]['t'] = [40, 44]                        # «correr» cuando sus segmentos no lo mueven
    o['acciones'][2]['emocion'] = 'nivel 3'                 # números en palabras
    o['tomas'] = [{'id': 'toma_01', 't': [0, 5], 'camara_molde': 'cam_03_esc9'}]   # el 01 ya no elige cámaras
    pr = next(p for p in o['personajes'] if p['id'] == 'ch-protagonista-c71a')
    pr['segmentos'][2]['pos'] = [[9.5, 12.0, 0.0], [9.5, 12.0, 0.0]]              # teletransporte entre segmentos
    C, err = _val(ctx)(o)
    print('\n(j)', *err, sep='\n    ')
    g = AC.agrupar_errores(err, o)
    assert set(g['acciones']) == {'a1', 'a4', 'a7', 'a9', 'a3'}
    assert 'ch-protagonista-c71a' in g['personajes']
    assert any('teletransporte' in x for x in g['personajes']['ch-protagonista-c71a'])
    assert any('se descartó' in x for x in C['avisos_codigo']) and C['tomas_plan'] == []


def argon_falso(o_bueno):
    """Lee SOLO lo que trae el prompt de reparación y devuelve los beats/segmentos fallidos como en la respuesta buena (por id)."""
    def llamar(prompt, k):
        F = _bloque(prompt, 'FAILED_PARTS'); B = {b['id']: b for b in o_bueno['acciones']}; Pb = {p['id']: p for p in o_bueno['personajes']}
        assert 'tomas' not in F and 'cam_' not in prompt.split('=== ACCEPTED_PLAN')[0]
        rep = {'acciones': [copy.deepcopy(B[b['id']]) for b in F['acciones']],
               'personajes': [{'id': p['id'], 'segmentos': copy.deepcopy(Pb[p['id']]['segmentos'])} for p in F['personajes']],
               'revision': [{'chequeo': 'tiempos', 'resultado': 'corregido', 'detalle': 'prueba'}]}
        return rep, {'usd': 0}
    return llamar


def test_k_autocorreccion_repara_solo_lo_que_fallo(ctx):
    o = copy.deepcopy(FA); o['acciones'][0]['accion'] = 'volar'; o['acciones'][4]['pose'] = 'pose_heroica'
    pr = next(p for p in o['personajes'] if p['id'] == 'ch-protagonista-c71a'); pr['segmentos'][2]['pos'] = [[9.5, 12.0, 0.0], [9.5, 12.0, 0.0]]
    _, err = _val(ctx)(o); assert err
    esq = AC.esquema_reparacion(ctx['P']['esquema']); assert esq['required'] == ['acciones', 'revision']
    g = AC.agrupar_errores(err, o)
    pr_txt = AC.prompt_reparacion(PG.texto(CA.cfg()['prompt_reparar']), ctx['P']['set'], ctx['P']['fichas'], o, g, 1, esq, extra=ctx['P']['vocabulario'])
    F = _bloque(pr_txt, 'FAILED_PARTS'); acept = _bloque(pr_txt, 'ACCEPTED_PLAN')
    assert sorted(b['id'] for b in F['acciones']) == ['a1', 'a5'] and [p['id'] for p in F['personajes']] == ['ch-protagonista-c71a']
    assert len(acept['acciones_aceptadas']) == len(FA['acciones']) - 2 and 'ACTION_VERBS' in pr_txt
    B = AC.bucle(_val(ctx), CASO['escena'], o, err, argon_falso(FA),
                 lambda ob, gg, k: AC.prompt_reparacion(PG.texto(CA.cfg()['prompt_reparar']), ctx['P']['set'], ctx['P']['fichas'], ob, gg, k, esq, extra=ctx['P']['vocabulario']),
                 2, ctx['P']['fichas'])
    print('\n(k)', B['intentos'])
    assert B['ok'] and len(B['intentos']) == 1 and B['intentos'][0]['acciones_pedidas'] == ['a1', 'a5']
    assert 'tomas' not in B['obj'] and [b['id'] for b in B['obj']['acciones']] == [b['id'] for b in FA['acciones']]


def test_k2_explicacion_sin_jerga_si_no_se_arregla(ctx):
    o = copy.deepcopy(FA); o['acciones'][0]['accion'] = 'volar'
    _, err = _val(ctx)(o)
    B = AC.bucle(_val(ctx), CASO['escena'], o, err, lambda p, k: (None, {'parar': True, 'por_que': 'prueba: sin pagar'}),
                 lambda ob, gg, k: 'x', 2, ctx['P']['fichas'])
    print('\n(k2)', B['explicacion']); assert not B['ok'] and 'Beat a1' in B['explicacion'] and 'cámara' not in B['explicacion']


def _armar(tmp_path, C, lineas=LINEAS):
    d01 = tmp_path / 'c01'; d01.mkdir(exist_ok=True); (d01 / f"esc_{CASO['escena']}.json").write_text(json.dumps(C, ensure_ascii=False))
    env = {**os.environ, 'AB_CUBO01_DIR': str(d01), 'AB_TRAMOS': str(tmp_path / 'tramos')}
    r = subprocess.run([sys.executable, AT, '--canal', CASO['canal'], '--capitulo', CASO['capitulo'], '--escena', CASO['escena']] + (['--lineas', lineas] if lineas else []),
                       env=env, capture_output=True, text=True, timeout=120)
    meta = json.loads(r.stdout.strip().splitlines()[-1]); assert meta['ok'], r.stdout[-500:]
    assert str(tmp_path) in meta['archivo']   # nunca escribe en los tramos reales
    return meta, Path(meta['archivo']).read_text(encoding='utf-8')


def test_m_tramo_con_01_accion_usa_beats_y_su_tiempo(ctx, tmp_path):
    C, err = _val(ctx)(FA); assert not err; C['origen'] = 'prueba: accion_v1 (Argon falso)'
    meta, txt = _armar(tmp_path, C)
    i = txt.index('DIRECCIÓN DEL 01'); print('\n(m)', {k: meta[k] for k in ('segundos', 'frames', 'segundos_de', 'cubo01_ventana_s', 'cubo01_acciones')}); print(txt[i:i + 1800])
    v = meta['cubo01_ventana_s']; assert meta['cubo01_ventana_de'].startswith('beats')
    assert v == [0.0, 14.0]                                         # a1..a6: las citas de las líneas 1036-1056
    assert abs(meta['segundos'] - (v[1] - v[0])) < 1e-6 and meta['frames'] == round(meta['segundos'] * meta['fps'])
    assert meta['cubo01_solo_accion'] and meta['cubo01_tomas'] == [] and meta['cubo01_acciones'] == ['a1', 'a2', 'a3', 'a4', 'a5', 'a6']
    assert 'Beats de acción del 01' in txt and '¡Déjala ir!' in txt and 'Hechos que deben quedar' in txt
    assert 'no trae cámaras' in txt and 'Toma toma_' not in txt and 'Tu especie' not in txt   # a7 empieza en 14 s: no es de este tramo


def test_n_tramo_con_01_viejo_dura_lo_que_su_ventana(ctx, tmp_path):
    """Compatibilidad o109 + arreglo del tiempo: la duración del tramo = ventana del 01 (antes 7.7 s por líneas × 0.7)."""
    meta, txt = _armar(tmp_path, O109)
    v = meta['cubo01_ventana_s']; print('\n(n)', meta['segundos'], meta['frames'], v, meta['segundos_de'])
    assert meta['cubo01_ventana_de'].startswith('fracción') and abs(meta['segundos'] - round(v[1] - v[0], 2)) < 1e-6
    assert meta['cubo01_tomas'] and 'cámaras.' in txt


def test_o_version_elige_el_modulo(monkeypatch):
    import cubo01_o109 as O
    llam = []
    monkeypatch.setattr(CA, 'cubo01', lambda *x: llam.append('accion') or {'ok': True})
    monkeypatch.setattr(O, 'cubo01', lambda *x: llam.append('o109') or {'ok': True})
    base = PG.ajustes()
    for v, esp in (('accion', 'accion'), ('o109', 'o109'), (None, 'o109')):
        d = copy.deepcopy(base); d['01']['version'] = v
        monkeypatch.setattr(PG, 'ajustes', lambda d=d: d); K.cubo01(None, None, None, None)
        assert llam[-1] == esp
    assert base['01']['version'] == 'accion'   # configuración real: el 01 ya es solo acción


def test_p_ventana_por_pares_con_01_real():
    """La ventana del tramo sale de los beats cuya cita está en el texto POR PARES de palabras seguidas: con el 01 real
    (accion_v1, ledger taller-01-esc9-20261102-022307) las líneas 1036-1056 de la esc. 9 son a1-a4 (0-8 s), no a1-a16."""
    import json, sys
    sys.path.insert(0, '/opt/myia-argon-blender/programa'); import armar_tramo as AT
    C = json.load(open(Path(__file__).parent / 'datos' / 'esc_9_accion_real_20261101.json'))
    texto = ("El alienígena levanta la mano. El espacio se abre detrás de él, revelando una prisión transparente suspendida sobre la ciudad. "
             "Dentro está la novia del protagonista. Golpea las paredes de energía, intentando liberarse. PROTAGONISTA: —¡No! "
             "Intenta levantarse. No puede. PROTAGONISTA: —¡Déjala ir!")
    assert AT.ventana_acciones(C, texto) == [0.0, 8.0]
    assert AT.ventana_acciones(C, "protagonista prisión precio mira") is None   # palabras sueltas no bastan
