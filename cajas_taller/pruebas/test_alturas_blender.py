"""Pruebas GRATIS (US$0), 2026-11-02 (Ricardo t306u/t308u): NO hay altura fija; el tamaño sale del diseño de Blender de CADA escena
(alturas_blender.py) y, si no hay, se sigue sin él (nota, nunca faltante ni número inventado). Nada abre Blender: la medición se FINGE."""
import json, os, sys, time
from pathlib import Path

CAJAS = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(CAJAS))
import paso01_cubos as K, alturas_blender as AB


def _montar(tmp_path, monkeypatch, por_escena):
    """por_escena = {escena: [(nombre_blend, [maniquíes])...]} (el primero de cada lista = el más nuevo)."""
    R = tmp_path / 'ab'; canal = 'canalX'
    (R / 'programa').mkdir(parents=True); (R / 'programa' / 'genesis_ayudante_v4.py').write_text('def maniqui(nombre, altura=1.72):\n    s=altura/1.72\n')
    (R / 'tramos' / canal).mkdir(parents=True)
    (R / 'tramos' / canal / 'nombres_cortos.json').write_text(json.dumps({'ch-z': 'Zarek', 'z': 'Zarek', 'ch-g': 'Gael', 'ch-a': 'Axel'}))
    med, files = {}, {}
    for esc, lst in por_escena.items():
        files[str(esc)] = []
        for nom, mqs in lst:
            f = R / 'historial' / canal / '1' / nom / 'e.blend'; f.parent.mkdir(parents=True); f.write_bytes(b'x'); med[str(f)] = mqs; files[str(esc)].append(f)
    bib = tmp_path / 'bib'; bib.mkdir(); ll = []
    def falso(f, c): ll.append(str(f)); return {'maniquies': med[str(f)]}, None
    monkeypatch.setattr(AB, '_raiz_ab', lambda: str(R)); monkeypatch.setattr(AB, '_biblio', lambda c: bib)
    monkeypatch.setattr(AB, '_medir_blend', falso)
    monkeypatch.setattr(AB, 'disenos_escena', lambda canal, cap, esc: files.get(str(esc), []))
    AB._MEM.clear()
    return canal, bib, ll


def test_tamano_del_diseno_de_esa_escena(tmp_path, monkeypatch):
    canal, bib, ll = _montar(tmp_path, monkeypatch, {
        9: [('esc09_nuevo', [{'objeto': 'Zarek', 'escala': 1.1163, 'z_min': -0.1, 'z_max': 2.0}, {'objeto': 'Gael', 'escala': 1.0, 'z_max': 1.36}]),
            ('esc09_viejo', [{'objeto': 'Zarek', 'escala': 1.1047}])],
        8: [('esc08_a', [{'objeto': 'Zarek', 'escala': 1.1047}])]})
    r9 = AB.medir_escena(canal, '1', 9)
    assert r9['ch-z']['altura_m'] == 1.92 and r9['z']['altura_m'] == 1.92        # escala × 1.72; manda el diseño más nuevo
    assert r9['ch-g']['altura_m'] == 1.72                                        # de rodillas (caja 1.36) sigue siendo 1.72: no depende de la pose
    assert r9['ch-z']['fuente'].startswith('diseño Blender de la escena 9: ') and 'esc09_nuevo' in r9['ch-z']['fuente']
    assert AB.medir_escena(canal, '1', 8)['ch-z']['altura_m'] == 1.9             # cada escena tiene SU tamaño
    assert AB.medir_escena(canal, '1', 7) == {}                                  # escena sin diseño: nada (no se inventa)
    assert 'ch-a' not in r9
    n = len(ll); AB.medir_escena(canal, '1', 9); assert len(ll) == n              # caché: no vuelve a abrir Blender
    assert (bib / 'medidas_disenos_blender.json').is_file()


def test_sin_altura_ref_no_mide(tmp_path, monkeypatch):
    canal, bib, ll = _montar(tmp_path, monkeypatch, {9: [('a', [{'objeto': 'Zarek', 'escala': 1.0}])]})
    (tmp_path / 'ab' / 'programa' / 'genesis_ayudante_v4.py').write_text('nada')
    assert AB.medir_escena(canal, '1', 9) == {} and ll == []


def test_altura_no_es_obligatoria_y_no_pisa_la_escrita(tmp_path, monkeypatch):
    monkeypatch.setattr(K, '_altura_biblioteca', lambda D, cid, fid: (None, None))
    vistos = []
    def ab(canal, cap, esc, pid):
        vistos.append((canal, cap, str(esc), pid))
        return (1.92, 'diseño Blender de la escena 9: /x/e.blend') if (pid, str(esc)) == ('ch-z', '9') else (None, None)
    monkeypatch.setattr(AB, 'altura', ab)
    D = tmp_path / 'canalX' / 'cap01_ep-x'; (D / 'respuestas').mkdir(parents=True)
    PC = {'ch-z': {'formas': {}}, 'ch-a': {'formas': {}}}
    assert K.altura({'altura': 1.8}, 'ch-z', 9, D, PC, [])[0] == 1.8             # la escrita (01) manda
    (D / 'respuestas' / 'personajes.json').write_text(json.dumps({'personajes': [{'personaje_id': 'ch-z', 'estados': [{'escena': 9, 'inicio': {'forma_id': 'f1'}}]}]}))
    assert K.altura({}, 'ch-z', 9, D, {'ch-z': {'formas': {'f1': {'altura_m': 1.95}}}}, [])[0] == 1.95   # la del canal manda
    h, de = K.altura({}, 'ch-z', 9, D, PC, [])
    assert h == 1.92 and de.startswith('diseño Blender') and vistos[-1] == ('canalX', '1', '9', 'ch-z')
    faltan, notas = [], []
    assert K.altura({}, 'ch-z', 7, D, PC, faltan, notas) == (None, None)         # escena 7 sin diseño: sigue sin altura
    assert faltan == [] and len(notas) == 1 and 'no se inventa' in notas[0]      # nota informativa, no faltante
