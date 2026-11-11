"""Pruebas GRATIS del ADAPTIVE CINEMATIC DIRECTOR (storyboard/). Ninguna llama a Argon ni a la red. Datos FALSOS marcados en pruebas/datos/."""
import copy, json, sys, types
from pathlib import Path
import pytest

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
import sb_comun as S
import selector_perfiles as SP
import validador_sb as VA
import memoria_sb as ME
import traductor_dsl_blender as TR
import esquemas_sb as E
import cubo_sb as CB

DAT = AQUI / 'datos'
def J(n): return json.loads((DAT / n).read_text(encoding='utf-8'))
def R(n): x = J(n); return x.get('respuesta', x)

P_ = 'ch-protagonista-c71a'; I_ = 'ch-imi-69f6'; AL = 'ch-el-aliengena-73a9'; N_ = 'ch-la-novia-5cdf'
CFG = {'canal': 'prueba', 'nivel_1_genero_tono': {'estado': 'definido (prueba)', 'generos': ['ciencia_ficcion', 'accion', 'fantasia', 'romance', 'drama']},
       'nivel_2_estilo_visual': {'estado': 'por definir', 'estilo_catalogo': 'por definir'},
       'nivel_3_direccion_artistica': {'estado': 'por definir', 'reglamento': None}, 'por_capitulo': {}, 'por_escena': {}}


def ctx(nv=None, mem=True, cd=None):
    fe = J('fichas_y_escena_esc9_genesis_cap1.json'); C01 = R('esc_9_accion01_falsa_sb_20261101.json')
    guion = (DAT / 'guion_esc9_genesis_cap1.txt').read_text(encoding='utf-8')
    m = J('memoria_entrada_falsa_esc9_20261101.json')['memoria'] if mem else {'personajes': {}}
    nv = nv or S.niveles('prueba', 1, '9', CFG)[0]
    P, faltan = CB.contexto(None, None, None, fe['escena'], cd or {'narration': 'none'}, fe['fichas'], guion, R('etapa1_falsa_cap1_20261101.json'), C01, m, nv)
    return P, faltan


def val(obj, P=None): P = P or ctx()[0]; return VA.validar(copy.deepcopy(obj), P, E.etapa3y4())


# ---------------- DSL fijado ----------------
def test_dsl_copia_fija_y_analiza():
    assert S.DSL_COMMIT in (S.AQUI / 'vendor' / 'camera_dsl' / 'VENDOR.txt').read_text()
    r = S.analizar('0-2s: /STATIC 2-6s: /DOLLYIN:MS>CU:SLOW')
    assert r['status'] in ('OK', 'WARN') and S.comandos(r)[1][3]['size_range'] == ['MS', 'CU']
    assert S.errores_dsl(S.analizar('/DOLLYIN:MS>WS'))           # acercarse pero abrir = error del DSL
    assert S.errores_dsl(S.analizar('/FOO'))


# ---------------- guion ----------------
def test_guion_y_dialogos_con_ids_sin_renombrar():
    P, faltan = ctx()
    assert not faltan
    assert len(P['dialogos']) == 17 and P['dialogos'][0]['texto'] == '¡No!'
    ids = {d['quien_guion']: d['id'] for d in P['dialogos']}
    assert ids == {'PROTAGONISTA': P_, 'ALIENÍGENA': AL, 'NOVIA': N_, 'IMI': I_}
    assert S.guion_escena('ESCENA 1. A\nx\nESCENA 9. B\nhola\nESCENA 10. C', '9') == 'ESCENA 9. B\nhola'


# ---------------- etapa 2 ----------------
def test_etapa1_a_segundos_y_perfiles_combinados():
    P, _ = ctx()
    assert [s['t'] for s in P['segmentos']] == [[0.0, 16.0], [16.0, 31.0], [31.0, 57.0], [57.0, 92.0]]
    f = P['perfiles'][1]['fuentes']
    assert [x['perfil'] for x in f] == ['drama', 'suspenso', 'romance'] and abs(sum(x['peso'] for x in f) - 1) < 1e-6
    assert P['perfiles'][0]['notas_subgenero'] and 'fantasia_oscura' in P['perfiles'][0]['notas_subgenero'][0]


def test_perfiles_no_fijan_numero_de_vinetas_y_nivel3_manda():
    for f in (S.AQUI / 'config' / 'perfiles').glob('*.json'):
        txt = f.read_text(); assert 'vinetas_por' not in txt and 'numero_de_vinetas' not in txt
    c, _ = SP.combinar([{'genero': 'terror', 'peso': 1}], None, {'nombre': 'X', 'lenguaje_camara': {'lente_mm_min': 35, 'lente_mm_max': 50, 'movimientos_prohibidos': ['DOLLYIN']}})
    assert c['preferencias']['lente_mm'] == [35.0, 50.0] and 'DOLLYIN' not in c['preferencias']['movimientos_preferidos']


# ---------------- validador ----------------
def test_respuesta_falsa_buena_pasa():
    C, err, av = val(R('sb_esc9_respuesta_falsa_buena_20261101.json'))
    assert err == [] and C is not None and len(C['vinetas']) == 17


def test_respuesta_falsa_con_errores_los_encuentra():
    C, err, _ = val(R('sb_esc9_respuesta_falsa_con_errores_20261101.json'))
    t = ' | '.join(err)
    assert C is None and 'salto de eje' in t and 'regla de 30°' in t and '«Sí.»' in t


def test_tiempos_huecos_y_beats():
    o = R('sb_esc9_respuesta_falsa_buena_20261101.json'); o['vinetas'][3]['t'] = [10.5, 14]; o['vinetas'][3]['ritmo']['duracion_s'] = 3.5
    o['vinetas'][3]['audio'][0]['t'] = [12.2, 13.8]
    _, err, _ = val(o); assert any('sin huecos' in e for e in err)
    o = R('sb_esc9_respuesta_falsa_buena_20261101.json'); o['vinetas'][8]['beats_01'] = []
    _, err, _ = val(o); assert any('«a13»' in e for e in err)
    o = R('sb_esc9_respuesta_falsa_buena_20261101.json'); o['vinetas'][-1]['t'] = [84, 90]; o['vinetas'][-1]['ritmo']['duracion_s'] = 6
    _, err, _ = val(o); assert any('dura 92.0 s' in e for e in err)


def test_dsl_en_vineta():
    o = R('sb_esc9_respuesta_falsa_buena_20261101.json'); o['vinetas'][3]['director_camara']['dsl_movimiento'] = '0-4s: /DOLLYIN:MS>WS:SLOW'
    _, err, _ = val(o); assert any('R02-SIZE-RANGE-DIRECTION' in e for e in err)
    o = R('sb_esc9_respuesta_falsa_buena_20261101.json'); o['vinetas'][3]['director_camara']['dsl_movimiento'] = '0-9s: /DOLLYIN:MS>MCU:SLOW'
    _, err, _ = val(o); assert any('la viñeta dura 4' in e for e in err)
    o = R('sb_esc9_respuesta_falsa_buena_20261101.json'); o['vinetas'][0]['director_imagen']['dsl_encuadre'] = '/MS /LOWANGLE /LENS24'
    _, err, _ = val(o); assert any('plano = WS' in e for e in err)


def test_audio_narrador_y_velocidad():
    o = R('sb_esc9_respuesta_falsa_buena_20261101.json'); o['vinetas'][0]['audio'] = [{'tipo': 'narracion', 'quien': 'NARRADOR', 't': [0.5, 2.5], 'texto': 'El alienígena levanta la mano.'}]
    _, err, _ = val(o); assert any('no tiene narrador' in e for e in err)
    o = R('sb_esc9_respuesta_falsa_buena_20261101.json'); o['vinetas'][4]['audio'][0]['t'] = [14.2, 16.0]
    _, err, _ = val(o); assert any('no alcanza a decirse' in e for e in err)
    o = R('sb_esc9_respuesta_falsa_buena_20261101.json'); o['vinetas'][3]['audio'][0]['quien'] = AL
    _, err, _ = val(o); assert any('pero el storyboard se lo da' in e for e in err)


def test_continuidad_nunca_se_sacrifica():
    o = R('sb_esc9_respuesta_falsa_buena_20261101.json'); o['memoria_salida']['personajes'][0]['danos'] = []
    _, err, _ = val(o); assert any('sale sin eso' in e for e in err)
    o['vinetas'][3]['continuidad']['cambios_declarados'] = [{'que': 'danos', 'personaje': P_, 'antes': 'golpeado', 'despues': 'curado', 'beat_01': 'a5'}]
    _, err, _ = val(o); assert not any('sale sin eso' in e for e in err)
    o = R('sb_esc9_respuesta_falsa_buena_20261101.json')
    for v in o['vinetas']: v['continuidad']['debe_mantenerse'] = [x for x in v['continuidad']['debe_mantenerse'] if 'golpeado' not in x]
    _, err, _ = val(o); assert any('debe estar en debe_mantenerse' in e for e in err)
    o = R('sb_esc9_respuesta_falsa_buena_20261101.json')   # continuación: empieza con los lados al revés que al final de la 8
    for c in o['vinetas'][0]['director_imagen']['en_cuadro']: c['lado'] = {'L': 'R', 'R': 'L'}[c['lado']]
    for v in o['vinetas'][1:2]:
        for c in v['director_imagen']['en_cuadro']: c['lado'] = {'L': 'R', 'R': 'L', 'C': 'C'}[c['lado']]
    _, err, _ = val(o); assert any('continuación' in e for e in err)


def test_genero_solo_avisa_reglamento_obliga():
    o = R('sb_esc9_respuesta_falsa_buena_20261101.json'); o['vinetas'][7]['director_imagen']['lente_mm'] = 200; o['vinetas'][7]['director_imagen']['dsl_encuadre'] = '/ECU /EYELEVEL /LENS200'
    _, err, av = val(o); assert err == [] and any('solo aviso' in a for a in av)
    P, _ = ctx(); P['reglamento'] = {'nombre': 'R-PRUEBA', 'lenguaje_camara': {'lente_mm_max': 100}}
    _, err, _ = val(o, P); assert any('máximo del reglamento R-PRUEBA' in e for e in err)


def test_tres_niveles_separados():
    cfg = copy.deepcopy(CFG); cfg['por_escena'] = {'1/9': {'nivel_2_estilo_visual': {'estilo_catalogo': 'manga'}}}
    nv, _ = S.niveles('prueba', 1, '9', cfg)
    assert nv['nivel_2_estilo_visual']['estilo_catalogo'] == 'manga' and nv['nivel_1_genero_tono'] == CFG['nivel_1_genero_tono']
    nv8, _ = S.niveles('prueba', 1, '8', cfg); assert nv8['nivel_2_estilo_visual']['estilo_catalogo'] == 'por definir'
    o = R('sb_esc9_respuesta_falsa_buena_20261101.json'); o['niveles_aplicados']['nivel_1_generos'] = ['anime_2d']
    _, err, _ = val(o); assert any('nivel_1_generos' in e for e in err)


def test_esquemas_sin_min_max_items():
    for f in (E.etapa1, E.etapa3y4, E.reparar):
        assert 'minItems' not in json.dumps(f()) and 'maxItems' not in json.dumps(f())


# ---------------- autocorrección ----------------
def _fake_llamar(cola):
    def ll(prompt, k):
        assert 'EXACT_ERRORS' in prompt
        return (copy.deepcopy(cola.pop(0)['respuesta']), {'usd': 0}) if cola else (None, {'parar': True, 'por_que': 'sin más'})
    return ll


def test_reparacion_parcial_en_2_vueltas():
    P, _ = ctx(); esq = E.etapa3y4(); o = R('sb_esc9_respuesta_falsa_con_errores_20261101.json'); _, err, _ = VA.validar(o, P, esq)
    B = CB.bucle(lambda x: VA.validar(x, P, esq), o, err, _fake_llamar([J('sb_esc9_reparacion1_falsa_20261101.json'), J('sb_esc9_reparacion2_falsa_20261101.json')]),
                 lambda x, er, k: CB.prompt_reparar('REGLAS', P, x, er, k)[0], 2)
    assert B['ok'] and [h['resultado'] for h in B['intentos']] == ['sigue con errores', 'ok']


def test_reparacion_maximo_2_y_explica():
    P, _ = ctx(); esq = E.etapa3y4(); o = R('sb_esc9_respuesta_falsa_con_errores_20261101.json'); _, err, _ = VA.validar(o, P, esq)
    B = CB.bucle(lambda x: VA.validar(x, P, esq), o, err, _fake_llamar([J('sb_esc9_reparacion1_falsa_20261101.json')]),
                 lambda x, er, k: CB.prompt_reparar('REGLAS', P, x, er, k)[0], 2)
    assert not B['ok'] and len(B['intentos']) == 2 and '«Sí.»' in B['explicacion']


def test_fusionar_por_id():
    o = {'vinetas': [{'id': 'a', 't': [0, 1]}, {'id': 'b', 't': [1, 2]}]}
    f = CB.fusionar(o, {'vinetas': [{'id': 'b', 't': [1, 1.5]}, {'id': 'c', 't': [1.5, 2]}], 'eliminar': []})
    assert [v['id'] for v in f['vinetas']] == ['a', 'b', 'c'] and f['vinetas'][1]['t'] == [1, 1.5]


# ---------------- memoria y traductor ----------------
def test_memoria_pasa_de_escena_a_escena(tmp_path):
    ME.registrar(tmp_path, '8', {}, {'personajes': [{'id': P_, 'vestuario': ['v'], 'danos': ['d'], 'objetos': [], 'posicion': {'lado': 'L', 'zona': 'z'}, 'arco_emocional': 'a'}],
                                     'direccion_pantalla': 'L2R', 'eje': 'x', 'objetos_escena': []}, 'prueba')
    e, av = ME.entrada(tmp_path, ['8', '9'], '9'); assert e['personajes'][P_]['danos'] == ['d'] and e['direccion_pantalla'] == 'L2R' and not av
    e, av = ME.entrada(tmp_path, ['7', '8', '9', '10'], '10'); assert av and 'sin memoria de la escena 9' in av[0]


def test_traductor_no_inventa_alturas():
    sb = R('sb_esc9_respuesta_falsa_buena_20261101.json')
    T = TR.traducir(sb, lambda pid: (None, None))
    assert T['alturas_por_medir'] and T['vinetas'][0]['keyframes'][0]['distancia_m'] == 'por medir en 02N'
    T = TR.traducir(sb, lambda pid: (1.8, 'diseño Blender prueba'))
    v4 = T['vinetas'][3]; assert isinstance(v4['keyframes'][0]['distancia_m'], float) and v4['keyframes'][-1]['plano'] == 'MCU'
    assert v4['keyframes'][-1]['distancia_m'] < v4['keyframes'][0]['distancia_m']


# ---------------- pago cerrado y cotización ----------------
def test_pago_cerrado_sin_guarda(monkeypatch, tmp_path):
    import paso01_pago as PG
    monkeypatch.setattr(PG, 'GUARDA_DIR', tmp_path)
    monkeypatch.setattr(PG, 'correr', lambda *a, **k: (_ for _ in ()).throw(AssertionError('NO debe llamar')))
    assert 'cerrado' in CB.revisar_guarda(1.0, 'Ricardo')
    r = CB.cmd_correr(types.SimpleNamespace(ok=1.0, aprobado='Ricardo', canal='x', capitulo='1', escena='9'))
    assert r['ok'] is False and r['llamadas_pagas'] == 0
    (tmp_path / 'HABILITAR_PAGO_SB').write_text('0.50')
    assert 'pasa el monto' in CB.revisar_guarda(1.0, 'Ricardo') and CB.revisar_guarda(0.5, None)


def test_cotizacion_usa_K_cotizar():
    llamadas = []
    def cot(chars, n_img, cd, para):
        llamadas.append((chars, n_img, cd['paso01']['max_output_tokens'], para))
        return {'ok': True, 'usd': round(chars * 1e-6 + cd['paso01']['max_output_tokens'] * 1e-5, 4), 'modelo': 'm', 'nivel': 'HIGH', 'max_salida_tokens': cd['paso01']['max_output_tokens']}
    K = types.SimpleNamespace(cotizar=cot)
    c = CB.cotizacion(K, {'paso01': {'max_output_tokens': 40000}}, 40000, {'9': 60000}, 15)
    assert c['ok'] and all(x[1] == 0 and x[3] == 'SB' for x in llamadas)           # sin imágenes, siempre «SB»
    assert c['max_salida'] == {'etapa1': 38500, 'etapa3y4': 40000, 'reparar': 16000}   # 16000 razonar + 1500 x 15 escenas
    c2 = CB.cotizacion(K, {'paso01': {'max_output_tokens': 40000}}, 40000, {'9': 60000}, 15, 41000, 1)
    assert c2['etapa1_solo_escenas_pedidas']['max_salida_tokens'] == 17500 and c2['etapa1_solo_escenas_pedidas']['usd'] < c2['etapa1_capitulo']['usd']
    assert c['capitulo_estimado']['total_peor_usd'] > c['capitulo_estimado']['total_sin_reparar_usd']


def test_fusionar_etapa1_por_escena():
    v = {'escenas': [{'escena': '8', 'segmentos': [1]}]}
    n = {'escenas': [{'escena': '9', 'segmentos': [2]}], 'arco_capitulo': 'a', 'revision': {'x': True}}
    f = CB._fusionar_e1(v, n)
    assert CB._segs_e1(f, '8') == [1] and CB._segs_e1(f, '9') == [2] and f['arco_capitulo'] == 'a' and v == {'escenas': [{'escena': '8', 'segmentos': [1]}]}


def test_n8n_correr_cerrado_y_guarda_json(monkeypatch, tmp_path):
    import paso01_pago as PG
    monkeypatch.setattr(PG, 'GUARDA_DIR', tmp_path)
    monkeypatch.setattr(PG, 'correr', lambda *a, **k: (_ for _ in ()).throw(AssertionError('NO debe llamar')))
    r = CB.n8n(['correr', '--canal', 'x', '--capitulo', '1', '--escena', '9'])
    assert r['ok'] and r['cerrado'] and r['llamadas_pagas'] == 0
    (tmp_path / 'HABILITAR_PAGO_SB').write_text(json.dumps({'tope_usd': 0.91, 'aprobado': 'prueba'}))
    assert CB.guarda_tope(tmp_path / 'HABILITAR_PAGO_SB') == 0.91
    assert CB.revisar_guarda(0.91, 'prueba') is None and 'pasa el monto' in CB.revisar_guarda(0.92, 'prueba')
