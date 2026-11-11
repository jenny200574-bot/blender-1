# -*- coding: utf-8 -*-
"""Elige si la cámara v2 (altura) puede mandar sobre la v1 del storyboard actual.

Regla genérica (cualquier canal): se usa v2 solo si
  (a) calza con el SB vigente (ids de viñeta + rangos t + objetivos, cuando el SB/v1 los trae), o
  (b) el archivo v2 es más nuevo que esc_N_camara.json (v1).
Si no, se avisa y se usa v1. El archivo v2 no se borra ni se pisa.
"""
from __future__ import annotations

import json
from pathlib import Path

TOL_S = 0.05


def _vid(v: dict):
    return v.get('vineta') or v.get('id')


def _t(v: dict):
    t = v.get('t_abs') or v.get('t')
    if isinstance(t, (list, tuple)) and len(t) >= 2:
        try:
            return (float(t[0]), float(t[1]))
        except (TypeError, ValueError):
            return None
    return None


def _obj(v: dict):
    o = v.get('objetivo')
    if o:
        return o
    di = v.get('director_imagen') or {}
    if isinstance(di, dict) and di.get('objetivo'):
        return di['objetivo']
    return None


def _vinetas(data) -> list:
    if isinstance(data, dict):
        v = data.get('vinetas') or data.get('tomas') or []
        return v if isinstance(v, list) else []
    return []


def _carga(path):
    p = Path(path)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding='utf-8'))


def v2_calza_con(v2, referencia, tol_s: float = TOL_S) -> tuple[bool, str]:
    """Compara viñetas de v2 contra una referencia (SB o cámara v1)."""
    a = {_vid(v): v for v in _vinetas(v2) if _vid(v)}
    b = {_vid(v): v for v in _vinetas(referencia) if _vid(v)}
    if set(a) != set(b):
        return False, 'ids_distintos (%d v2 vs %d ref)' % (len(a), len(b))
    if not a:
        return False, 'sin_vinetas'
    for i, va in a.items():
        ta, tb = _t(va), _t(b[i])
        if ta is None or tb is None:
            return False, 't_faltante en %s' % i
        if abs(ta[0] - tb[0]) > tol_s or abs(ta[1] - tb[1]) > tol_s:
            return False, 't_distinto en %s' % i
        oa, ob = _obj(va), _obj(b[i])
        if oa and ob and oa != ob:
            return False, 'objetivo_distinto en %s' % i
    return True, 'calza'


def v2_es_vigente(path_v2, path_v1=None, path_sb=None, tol_s: float = TOL_S) -> tuple[bool, str]:
    """True si v2 puede mandar. No toca archivos."""
    p2 = Path(path_v2) if path_v2 else None
    if not p2 or not p2.is_file():
        return False, 'sin_v2'
    p1 = Path(path_v1) if path_v1 else None
    if p1 and p1.is_file() and p2.stat().st_mtime > p1.stat().st_mtime + 1e-6:
        return True, 'v2_mas_nueva_que_v1'
    v2 = _carga(p2)
    # Prioridad: calzar con el SB (tiempos e ids); objetivos se contrastan con v1 si el SB no los trae.
    if path_sb and Path(path_sb).is_file():
        ok, motivo = v2_calza_con(v2, _carga(path_sb), tol_s=tol_s)
        if ok:
            if p1 and p1.is_file():
                ok2, m2 = v2_calza_con(v2, _carga(p1), tol_s=tol_s)
                if not ok2 and 'objetivo_distinto' in m2:
                    return False, m2
            return True, 'calza_con_sb'
        return False, motivo
    if p1 and p1.is_file():
        return v2_calza_con(v2, _carga(p1), tol_s=tol_s)
    return True, 'solo_esta_v2'
