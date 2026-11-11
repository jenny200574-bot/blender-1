# -*- coding: utf-8 -*-
"""[constructores_v1_20261109 · 10-nov-2026] Vía B para objetos SUELTOS (no dibujados en ningún escenario o mal emparejados):
misma plantilla, corpus gratis y revisor que recetas_argon.py, pero las fichas vienen del pedido (sello + ADN del cubo +
caja dada por el pedido con su FUENTE: dato del plan de un escenario o deducción declarada). Sin IA aquí.
Uso: python3 recetas_sueltas.py preparar --pedido pedido.json --salida S [--adn-dir DIR]
     python3 recetas_sueltas.py revisar --salida S           (= recetas_argon.py revisar)"""
import argparse, json, sys
from pathlib import Path
B = Path(__file__).resolve().parent
sys.path[:0] = [str(B.parent / 'codigo'), str(B)]
import recetas_argon as RA
import datos_via_b as DV

def fichas_de(pedido, adn_dir, cubo):
    out = []
    for o in pedido['objetos']:
        f = {'objeto_id': o['objeto_id'], 'nombre': o.get('nombre') or o['objeto_id'], 'caja_m': o['caja_m'], 'apoyo': o['apoyo'],
             'fuente_caja': o.get('fuente_caja'), 'nota': o.get('nota')}
        pid = DV.id_pieza_pedido(o)
        sp = Path(cubo) / 'objetos_pj' / f"{pid}.json" if pid else Path('/nonexist')
        if sp.is_file():
            s = json.loads(sp.read_text(encoding='utf-8'))
            for k in ('nombre', 'nunca_cambia', 'subclase', 'portador'):
                if s.get(k): f[f'sello_{k}'] = s[k]
        p = Path(adn_dir) / f"{pid}_ako.json" if pid and adn_dir else Path('/nonexist')
        if p.is_file():
            f['adn_texto'] = p.read_text(encoding='utf-8')[:6000]; f['adn_id'] = pid
        out.append({k: v for k, v in f.items() if v not in (None, '', [], {})})
    return out

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('modo', choices=['preparar', 'revisar']); ap.add_argument('--pedido')
    ap.add_argument('--salida', required=True); ap.add_argument('--adn-dir'); ap.add_argument('--cubo'); ap.add_argument('--por-grupo', type=int, default=None, help='si no se pasa, sale de esquemas/grupos_recetas.json')
    a = ap.parse_args()
    if a.modo == 'revisar': RA.revisar(a); sys.exit(0)
    ped = json.loads(Path(a.pedido).read_text(encoding='utf-8')); fs = fichas_de(ped, a.adn_dir, a.cubo or Path(a.adn_dir).parent)
    RA._fichas = lambda datos, esc, adn: (fs, {})
    a.datos, a.escenario = None, ped.get('grupo', 'sueltos')
    RA.preparar(a)
