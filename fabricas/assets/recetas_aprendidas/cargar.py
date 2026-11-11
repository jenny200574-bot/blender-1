# -*- coding: utf-8 -*-
"""Carga fichas de recetas_aprendidas + ids de Star (copia local del escenario). US$0."""
from __future__ import annotations
import json
from pathlib import Path
AQUI = Path(__file__).resolve().parent
STAR_JSON = AQUI.parents[1] / 'escenario' / 'codigo' / 'biblioteca_formas' / 'biblioteca_formas.json'
# también acepta la original solo-lectura
STAR_ORIG = Path('/workspace/pr17/comb/herramientas/escenario_detallado/biblioteca_formas/biblioteca_formas.json')

def catalogo_aprendidas():
    return json.loads((AQUI / 'catalogo.json').read_text(encoding='utf-8'))

def ficha(gid: str):
    p = AQUI / 'recetas' / f'{gid}.json'
    if not p.exists():
        raise FileNotFoundError(gid)
    return json.loads(p.read_text(encoding='utf-8'))

def ids_aprendidas():
    return set(json.loads((AQUI / 'indice.json').read_text(encoding='utf-8'))['por_id'])

def alias_n8n():
    return json.loads((AQUI / 'alias_objeto_n8n.json').read_text(encoding='utf-8'))

def ids_star():
    p = STAR_JSON if STAR_JSON.exists() else STAR_ORIG
    d = json.loads(p.read_text(encoding='utf-8'))
    return {f['id'] for f in d['fichas']}

def resolver(objeto_id: str, fid_plan=None):
    """Devuelve ('star', fid) | ('aprendida', gid) | ('excluido', motivo) | ('falta', None)."""
    al = alias_n8n()
    if fid_plan:
        return ('star', fid_plan)
    if objeto_id in al:
        return ('aprendida', al[objeto_id])
    # id genérico directo
    if objeto_id in ids_aprendidas():
        return ('aprendida', objeto_id)
    return ('falta', None)
