"""Pruebas GRATIS (US$0), 2026-11-01 (Ricardo t304u): (1) el 03 lee los renders del motor de Ako (02N) de forma genérica;
(2) el IndexError del «05 · leer» (pos_en con puntos de piso [x, y]). Nada llama a Argon ni a Blender; el historial es FALSO en una carpeta temporal.
Correr:  cd /opt/myia-taller-n8n/cajas && /opt/myia-staging-arreglos-20261026/venv/bin/python -m pytest -q pruebas"""
import json, sys
from pathlib import Path
import pytest

CAJAS = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(CAJAS))
import paso01_cubos as K, motor_02n as M2


# ---------------- (2) 05 · leer: pos_en ----------------
def test_pos_en_puntos_de_piso_2d():
    per = {'segmentos': [{'t': [0, 2], 'pos': [[0, 0], [2, 4]], 'rot': 90}]}
    p, r = K.pos_en({}, per, 1.0)
    assert p == [1.0, 2.0, 0.0] and r == 90.0


def test_pos_en_3d_y_puntos_con_nombre():
    C = {'puntos': {'A': [0, 0, 1], 'B': [4, 0, 1]}}
    assert K.pos_en(C, {'segmentos': [{'t': [0, 4], 'pos': ['A', 'B']}]}, 1)[0] == [1.0, 0.0, 1.0]
    assert K.pos_en(C, {'segmentos': [{'t': [0, 4], 'pos': [[0, 0, 0], [0, 0, 8]]}]}, 2)[0] == [0.0, 0.0, 4.0]


def test_pos_en_malformado_no_revienta():
    C = {'puntos': {}}
    for seg in ({'t': [0, 1], 'pos': [[1]]}, {'t': [0, 1], 'pos': ['NO_EXISTE']}, {'t': ['x', 1], 'pos': [[0, 0]]}, {'t': [0, 1], 'pos': []}, {'pos': [[0, 0]]}):
        assert K.pos_en(C, {'segmentos': [seg]}, 0.5) == (None, None)



def test_eje_en_ejes_en_texto_del_01_argon():
    per = lambda a, b: {'segmentos': [{'t': [0, 2], 'pos': [a, b]}]}
    C = {'ejes': ['Eje principal oeste-este entre A y B'], 'personajes': [per([0, 0], [0, 0]), per([2, 0], [2, 0])]}
    ln, de, lado = K.eje_en(C, 1.0)
    assert ln == [[0.0, 0.0], [2.0, 0.0]] and de.startswith('calculado')


def test_eje_en_eje_con_linea_del_01():
    C = {'puntos': {'P': [5, 5, 0]}, 'ejes': [{'t': [0, 3], 'linea': [[0, 0], 'P'], 'lado_camara': 'izquierda'}], 'personajes': []}
    assert K.eje_en(C, 1) == ([[0.0, 0.0], [5.0, 5.0]], 'cubo 01 (ejes)', 'izquierda')
    assert K.eje_en(C, 9) == (None, None, None)


def test_altura_con_marcador_de_texto_es_falta(tmp_path):
    PC = {'ch-a': {'formas': {'f1': {'altura_m': 'falta'}}}}
    (tmp_path / 'respuestas').mkdir()
    (tmp_path / 'respuestas' / 'personajes.json').write_text(json.dumps({'personajes': [{'personaje_id': 'ch-a', 'estados': [{'escena': 3, 'inicio': {'forma_id': 'f1'}}]}]}))
    faltan, notas = [], []   # 2026-11-02 (t308u): sin altura NO es faltante: nota informativa y se sigue
    assert K.altura({}, 'ch-a', 3, tmp_path, PC, faltan, notas) == (None, None) and faltan == [] and 'dice' not in ''.join(notas) and len(notas) == 1
    PC['ch-a']['formas']['f1']['altura_m'] = '1.75'
    assert K.altura({}, 'ch-a', 3, tmp_path, PC, []) == (1.75, 'canal: forma f1 altura_m')
    assert K.altura({'altura': 1.6}, 'ch-a', 3, tmp_path, PC, [])[0] == 1.6


def test_altura_desde_la_biblioteca_del_canal(tmp_path, monkeypatch):
    import types
    man = {'personajes': [{'id': 'ch-a', 'ids_mapa': ['ch-a'], 'versiones': [{'id': 'v1', 'forma_id': 'f1', 'ids_mapa': ['f1'], 'altura_m': 1.8},
                                                                               {'id': 'v2', 'forma_id': 'f2', 'ids_mapa': ['f2'], 'altura_m': None}]}]}
    fake = types.SimpleNamespace(leer_manifiesto=lambda c: man,
                                 buscar_personaje=lambda m, pid, nom: next((p for p in m['personajes'] if p['id'] == pid), None),
                                 buscar_version=lambda p, fid, nom: next((v for v in p['versiones'] if v['forma_id'] == fid), None))
    monkeypatch.setitem(sys.modules, 'personajes', fake); K._CACHE_BIBLIO.clear()
    D = tmp_path / 'canalZ' / 'cap01_x'; (D / 'respuestas').mkdir(parents=True)
    (D / 'respuestas' / 'personajes.json').write_text(json.dumps({'personajes': [{'personaje_id': 'ch-a', 'estados': [
        {'escena': 1, 'inicio': {'forma_id': 'f1'}}, {'escena': 2, 'inicio': {'forma_id': 'f2'}}]}]}))
    PC = {'ch-a': {'formas': {'f1': {'altura_m': 'falta'}, 'f2': {'altura_m': 'falta'}}}}
    h, de = K.altura({}, 'ch-a', 1, D, PC, [])
    assert h == 1.8 and de.startswith('biblioteca del canal: versión v1')
    faltan = []
    monkeypatch.setattr(K, '_altura_diseno', lambda D, cid, n: (None, None))
    assert K.altura({}, 'ch-a', 2, D, PC, faltan) == (None, None) and faltan == []   # sin dato real: no se inventa (2026-11-02: ya no es faltante)
    K._CACHE_BIBLIO.clear()


# ---------------- (1) 03 lee el 02N ----------------
def _corrida(R, canal, cap, modo, tramo, fecha, escena, renders=(1, 25, 49), errores=0):
    (R / 'tramos' / canal / cap).mkdir(parents=True, exist_ok=True)
    (R / 'tramos' / canal / cap / f'{tramo}.json').write_text(json.dumps({'escena': escena, 'fps': 24, 'frames': 49, 'cubo01_ventana_s': [2.0, 6.0],
                                                                          'cubo01_ledger': 'L-01', 'cubo01_tomas': ['toma_01']}))
    d = R / 'historial' / canal / (cap if modo == 'real' else f'{cap}-seco') / f'{tramo}_{fecha}'; d.mkdir(parents=True)
    (d / 'estado_escena.json').write_text(json.dumps({'frames': [1, 49], 'actores': {'gael': {'pos': [0, 0, 0]}},
                                                      'tomas': [{'id': 'T1', 'f': [1, 24], 'accion': 'a'}, {'id': 'T2', 'f': [25, 49], 'accion': 'b'}],
                                                      'validacion': {'ok': True}}))
    hall = [{'severidad': 'error', 'tipo': 'atraviesa', 'actor': 'gael', 'frames': [[25, 30]], 'detalle': 'x'}][:errores] + [{'severidad': 'aviso', 'tipo': 'pie'}]
    (d / 'revision_movimiento.json').write_text(json.dumps({'errores': errores, 'hallazgos': hall}))
    for f in renders: (d / f'render_f{f:03d}.png').write_bytes(b'png')
    return d


@pytest.fixture
def raiz(tmp_path, monkeypatch):
    monkeypatch.setenv('MYIA_AB_RAIZ', str(tmp_path)); return tmp_path


def test_prefiere_real_y_la_mas_nueva(raiz):
    _corrida(raiz, 'canalX', '1', 'seco', 'esc05_l1-2', '20261101_130000', '5')
    _corrida(raiz, 'canalX', '1', 'real', 'esc05_l1-2', '20261101_100000', '5')
    _corrida(raiz, 'canalX', '1', 'real', 'esc05_l1-2', '20261101_120000', '5')
    _corrida(raiz, 'canalX', '1', 'real', 'esc06_l3-4', '20261101_140000', '6')
    c = M2.mejor('canalX', '1', 5)
    assert c['modo'] == 'real' and c['fecha'] == '20261101_120000' and c['escena'] == '5'
    assert [x['escena'] for x in M2.corridas('canalX', '1')].count('6') == 1
    assert M2.mejor('canalX', '1', 7) is None


def test_solo_seco_se_usa_y_se_marca(raiz):
    _corrida(raiz, 'canalY', '1', 'seco', 'esc09_l1-2', '20261101_130000', '9')
    c = M2.mejor('canalY', '01', 9)   # el capítulo «01» también encuentra la carpeta «1»
    assert c['modo'] == 'seco' and c['costo_usd'] == 0.0


def test_tomas_fotos_y_segundos_del_01(raiz):
    _corrida(raiz, 'canalX', '1', 'real', 'esc05_l1-2', '20261101_120000', '5', errores=1)
    c = M2.mejor('canalX', '1', 5)
    tomas, fotos = M2.tomas_y_fotos(c, {'nombre': 'cam_01', 'loc': [1, 2, 3]})
    assert [t['toma'] for t in tomas] == ['T1', 'T2']
    assert tomas[0]['segundos_tramo'] == [0.0, 0.958] and tomas[0]['segundos_escena'][0] == 2.0 and tomas[1]['segundos_escena'][1] == 6.0
    assert tomas[0]['camara_usada']['loc'] == [1, 2, 3]
    assert [(f['toma'], f['frame']) for f in fotos] == [('T1', 1), ('T2', 25), ('T2', 49)] and fotos[-1]['segundo'] == 6.0
    h = M2.hallazgos_revisor(c); r = M2.resumen(c)
    assert len(h) == 1 and h[0]['tipo'] == 'movimiento' and r['revisor_errores'] == 1 and r['revisor_avisos'] == 1 and r['ledger_01'] == 'L-01'


def test_nombres_inseguros_no_leen_nada(raiz):
    assert M2.corridas('../etc', '1') == [] and M2.corridas('canalX', '1/../..') == []


def test_sin_historial_no_falla(raiz):
    assert M2.corridas('nadie', '1') == []
