"""Pruebas GRATIS (US$0) del arreglo 1 de continuidad (estado_continuidad.py). Datos INVENTADOS, sin red, sin IA.
Correr:  cd /opt/myia-taller-n8n/cajas && /opt/myia-staging-arreglos-20261026/venv/bin/python -m pytest -q pruebas"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import estado_continuidad as EC


def beat(i, t, obj, cam): return {'id': i, 't': [t, t + 0.5], 'actor': '', 'objeto': obj, 'cambio': cam}


C1 = {'duracion_s': 12, 'acciones': [beat('a1', 5, 'vaso', 'romper')], 'hechos': [{'hecho': 'el vaso quedó roto', 'personaje': '', 't': 5}]}


def test_vaso_entero_antes_roto_despues():
    tomas = [{'id': 'x1', 'escena': '1', 't': 2, 't_fin': 4}, {'id': 'x2', 'escena': '1', 't': 8, 't_fin': 10}]
    av = EC.anotar_plan(tomas, lambda n: C1, {})
    assert 'vaso' not in tomas[0]['estado']['objetos'] and tomas[0]['estado']['hechos_vigentes'] == []
    assert tomas[1]['estado']['objetos']['vaso'] == 'roto' and 'vaso: roto' in tomas[1]['estado']['texto']
    assert len(tomas[1]['estado']['hechos_vigentes']) == 1 and av == []


def test_doble_cambio_queda_el_ultimo():
    C = {'duracion_s': 12, 'acciones': [beat('a1', 2, 'puerta', 'aparecer'), beat('a2', 6, 'puerta', 'desaparecer')], 'hechos': []}
    e = EC.estado_toma({}, EC.cambios_de_escena(C), [], 9, 11)
    assert e['objetos'] == {'puerta': 'ausente'}


def test_arrastre_de_la_escena_anterior():
    mem = {'escenas': {'1': {'salida': {'personajes': {'ana': {'danos': ['raspón brazo'], 'vestuario': ['chaqueta']}}, 'objetos_escena': ['mesa volcada']}}}}
    tomas = [{'id': 'y1', 'escena': '2', 't': 0}]
    EC.anotar_plan(tomas, lambda n: {'duracion_s': 5, 'acciones': [], 'hechos': []}, mem, orden=['1', '2'])
    e = tomas[0]['estado']
    assert e['personajes']['ana']['danos'] == ['raspón brazo'] and 'mesa volcada' in e['objetos'] and 'escena 1' in e['entrada_fuente']


def test_entrada_guardada_en_memoria_manda():
    mem = {'escenas': {'2': {'entrada': {'objetos_escena': ['lámpara rota'], 'fuente': 'salida validada del storyboard de la escena 1'}}}}
    ent, fte = EC.entrada_de_escena(mem, '2', ['1', '2'])
    assert ent['objetos_escena'] == ['lámpara rota'] and 'escena 1' in fte


def test_hecho_sin_segundo_es_aviso():
    C = {'duracion_s': 10, 'acciones': [], 'hechos': [{'hecho': 'Ana sabe el secreto', 'personaje': 'ana', 't': None}]}
    tomas = [{'id': 'z1', 'escena': '3', 't': 4}]
    av = EC.anotar_plan(tomas, lambda n: C, {})
    assert any('sin segundo' in a for a in av) and tomas[0]['estado']['hechos_vigentes'] == []


def test_toma_que_cruza_el_cambio_lleva_nota():
    tomas = [{'id': 'w1', 'escena': '1', 't': 3, 't_fin': 7}]
    EC.anotar_plan(tomas, lambda n: C1, {})
    d = tomas[0]['estado']['cambios_durante_toma']
    assert d and d[0]['objeto'] == 'vaso' and d[0]['termina'] == 'roto' and d[0]['t'] == 5
    assert 'vaso' not in tomas[0]['estado']['objetos'] and 'a mitad de toma' in tomas[0]['cambios_durante_toma']


def test_sin_t_fin_usa_siguiente_toma_o_duracion():
    tomas = [{'id': 'v1', 'escena': '1', 't': 3}, {'id': 'v2', 'escena': '1', 't': 6}]
    EC.anotar_plan(tomas, lambda n: C1, {})
    assert tomas[0]['estado']['t_fin'] == 6 and tomas[0].get('cambios_durante_toma')
    assert tomas[1]['estado']['t_fin'] == 12 and not tomas[1].get('cambios_durante_toma')


def test_cambio_sin_objeto_es_aviso_y_sin_direccion_no_falla():
    av = []
    assert EC.cambios_de_escena({'acciones': [beat('a9', 1, '', 'romper')]}, av, '4') == [] and av
    tomas = [{'id': 'u1', 'escena': '9', 't': 0}]
    av2 = EC.anotar_plan(tomas, lambda n: None, {})
    assert tomas[0]['estado']['texto'] == 'sin cambios de objetos' and any('sin dirección' in a for a in av2)


# ---------------- Arreglo 4 (cubo 11) ----------------
def test_linea_estado_y_nota_para_el_11():
    tomas = [{'id': 'p1', 'escena': '1', 't': 3, 't_fin': 7}, {'id': 'p2', 'escena': '1', 't': 8, 't_fin': 10}]
    b = EC.bloque_estados(['p1', 'p2', 'no_existe'], tomas, lambda n: C1, {})
    l1, l2 = b.split('\n')
    assert l1.startswith('STATE IN THIS SHOT p1:') and 'CHANGE MID-SHOT' in l1 and 'becomes broken' in l1 and 'vaso' in l1
    assert l2.startswith('STATE IN THIS SHOT p2:') and 'vaso: broken' in l2 and 'MID-SHOT' not in l2
    assert 'estado' not in tomas[0]   # no escribe en el plan


def test_bloque_usa_estado_ya_guardado_por_el_05():
    tomas = [{'id': 'q1', 'escena': '1', 't': 0, 'estado': {'texto': 'puerta: abierta', 'personajes': {'ana': {'danos': ['raspón']}}, 'nota_cambios': ''}}]
    b = EC.bloque_estados(['q1'], tomas, None, None)
    assert b == 'STATE IN THIS SHOT q1: puerta: abierta; ana: danos raspón.'


def test_sin_plan_no_hay_bloque():
    assert EC.bloque_estados(['x'], [], lambda n: None, {}) == ''


def test_cubo11_solo_cotiza_lleva_estado(tmp_path, monkeypatch):
    """El pedido REAL del 11 (pedido_hoja, modo cotizar) con pintor/precio FALSOS: el texto lleva la línea de estado. US$0."""
    import json, types
    import paso01_cubos as K, cubo11_tira as CT
    D = tmp_path / 'canal-prueba' / 'cap01_x'
    base = D / 'ramas' / 'moldes' / 'esc-x' / 'tomas' / 'esc_1'; (base / 'crudos').mkdir(parents=True)
    (base / 'crudos' / 'medidas.json').write_text(json.dumps({'p1_1': {'vis': {'ana': {'mira_a_camara': True}}}, 'p2_1': {'vis': {'ana': {'mira_a_camara': True}}}}))
    (D / 'cubos' / '05').mkdir(parents=True)
    (D / 'cubos' / '05' / 'plan_tomas.json').write_text(json.dumps({'tomas': [{'id': 'p1', 'escena': '1', 't': 3, 't_fin': 7}, {'id': 'p2', 'escena': '1', 't': 8, 't_fin': 10}]}))
    monkeypatch.setattr(K, 'dirigida', lambda D_, n, importados=False: (C1, '01'))
    P = types.SimpleNamespace(refs_para=lambda *a, **k: {'usar': [{'personaje_id': 'ana', 'imagenes': [], 'tipo': 'relleno', 'personaje': 'Ana', 'version': 'v1'}]})
    HP = types.SimpleNamespace(vinetas_plantilla=lambda *a, **k: [], construir=lambda *a, **k: {'prompt': 'PINTA', 'refs': [], 'texto_archivo': 'PINTA', 'imagen_molde': None})
    PT = types.SimpleNamespace(precio_llamada=lambda I, T, ch, n: round(ch / 1e6, 6), aspecto=lambda h: '16:9')
    idx = {'escenario_id': 'esc-x', 'personajes': [{'id': 'ana', 'personaje_id': 'ana', 'nombre': 'Ana'}]}
    h = {'id': 'h1', 'ids': ['p1_1', 'p2_1'], 'cuadros': {}, 'tomas': ['p1', 'p2'], 'hoja': str(base / 'hoja.png')}
    q = CT.pedido_hoja(K, P, None, PT, HP, D, {'numero': '1', 'datos': {}}, C1, idx, base, h, None, {}, {'descripcion_en': 'style'},
                       {'modelo': 'falso', 'talla': '1K'}, None, CT.CM.ajustes())
    assert 'STATE IN THIS SHOT p1:' in q['texto'] and 'CHANGE MID-SHOT' in q['texto'] and 'vaso: broken' in q['texto']
    assert 'STATE IN THIS SHOT p2' in (D / 'cubos' / '11' / 'esc_1' / 'h1' / 'pedido_pintura.txt').read_text()
    assert q['chars'] == len(q['texto']) and q['estado_tomas']



# ---------------- Arreglo 2 (cubo 03) ----------------
def test_estado_para_03_por_toma_y_fotograma():
    tr = [{'shot': 's1', 'scene_seconds': [3, 7], 'frames': [{'second': 4}, {'second': 6}]}, {'shot': 's2', 'scene_seconds': [8, 10], 'frames': []}]
    S, av = EC.estado_para_03(C1, '1', {}, ['1'], tr)
    a, b = S['shots']
    assert a['objects_at_start'] == {} and 'becomes broken' in a['changes_mid_shot']
    assert a['frames'][0]['objects'] == {} and a['frames'][1]['objects'] == {'vaso': 'broken'}   # no vuelve atrás
    assert b['objects_at_start'] == {'vaso': 'broken'} and b['facts_in_force'] == ['el vaso quedó roto'] and av == []
    assert S['object_changes_in_scene'] == [{'object': 'vaso', 'becomes': 'broken', 'second': 5.0}]


def test_estado_para_03_arrastra_escena_anterior():
    mem = {'escenas': {'1': {'salida': {'personajes': {'ana': {'danos': ['raspón']}}, 'objetos_escena': ['mesa volcada']}}}}
    S, _ = EC.estado_para_03({'acciones': [], 'hechos': []}, '2', mem, ['1', '2'], [{'shot': 'x', 'scene_seconds': [0, 2]}])
    assert S['shots'][0]['characters_carried_in'] == {'ana': {'danos': ['raspón']}} and 'mesa volcada' in S['shots'][0]['objects_at_start']


def test_regla_5_del_03_cubre_objetos_y_set():
    txt = (Path(__file__).resolve().parents[1] / 'prompts_03' / 'revisar_coherencia.txt').read_text(encoding='utf-8')
    r5 = txt[txt.index('\n5. '):txt.index('CODE_CHECKS lists')]
    assert 'objects' in r5 and 'set' in r5 and 'restores itself' in r5 and 'STATE_PER_SHOT' in txt


def test_pedido03_lleva_state_per_shot(monkeypatch, tmp_path):
    import paso01_revision as RV, paso01_cubos as K
    D = tmp_path / 'c' / 'cap01'; D.mkdir(parents=True)
    monkeypatch.setattr(K, 'escenas', lambda D_, solo=None: [{'numero': '1'}])
    monkeypatch.setattr(RV, '_anterior', lambda K_, D_, n: None)
    tomas = [{'toma': 's1', 'segundos_escena': [3, 7], 'tipo': 'PG', 'camara_usada': 'c', 'figuras': []}]
    prompt, _, _ = RV.pedido03(K, D, '1', {'C': C1, 'k': 0}, tomas, [{'toma': 's1', 'segundo': 6, 'archivo': '/x/s1_6.png'}], [], {})
    assert '=== STATE_PER_SHOT ===' in prompt and 'broken' in prompt
