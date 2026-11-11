# -*- coding: utf-8 -*-
"""Datos de la vía B (apoyos, grupos, exclusiones). Todo sale de JSON en esquemas/, sin ids de canal ni de pieza."""
from __future__ import annotations
import json, math, re
from pathlib import Path

B = Path(__file__).resolve().parent
ESQ = B / 'esquemas'

def _leer(nombre, clave=None):
    d = json.loads((ESQ / nombre).read_text(encoding='utf-8'))
    return d[clave] if clave else d

def apoyos():
    return _leer('apoyos.json', 'apoyos')

def alias_apoyo():
    m = {}
    for k, v in apoyos().items():
        for a in v.get('alias') or []:
            m[a] = k
    return m

def norma_apoyo(x):
    if not x: return x
    return alias_apoyo().get(x, x)

def ids_apoyo():
    return list(apoyos().keys())

def texto_apoyos():
    """Frase para la plantilla de Argon, armada desde apoyos.json."""
    partes = [f"`{k}` → {v['descripcion']}" for k, v in apoyos().items()]
    return 'Apoyo: ' + '. '.join(partes) + '.'

def inyectar_enum_apoyo(esquema: dict) -> dict:
    """El enum vivo del campo apoyo es el de apoyos.json, no una lista fija en el código."""
    try:
        esquema['properties']['recetas']['items']['properties']['apoyo']['enum'] = ids_apoyo()
    except Exception:
        pass
    return esquema

def toca_apoyo(ap, mn, mx, caja, tol):
    """¿La silueta (mn,mx) toca el apoyo declarado? caja={'ancho','fondo','alto'}. Primitivas de apoyos.json (z_min, z_max, y_max, libre)."""
    ap = norma_apoyo(ap)
    regla = apoyos().get(ap)
    if not regla:
        return False
    kind = regla.get('toca')
    w, d, h = caja['ancho'], caja['fondo'], caja['alto']
    if kind == 'z_min':
        return mn[2] <= tol
    if kind == 'z_max':
        return mx[2] >= h - tol
    if kind == 'y_max':
        return mx[1] >= d / 2 - tol
    if kind == 'y_min':
        return mn[1] <= -d / 2 + tol
    if kind == 'x_max':
        return mx[0] >= w / 2 - tol
    if kind == 'x_min':
        return mn[0] <= -w / 2 + tol
    if kind == 'libre':
        return True
    return False

def grupos_cfg():
    return _leer('grupos_recetas.json')

def tamano_grupo(n_ya, max_out=None, por_grupo=None):
    """¿Cabe un objeto más en el grupo actual? Límites desde grupos_recetas.json (o --por-grupo si se pasa)."""
    g = grupos_cfg()
    tope_n = int(por_grupo) if por_grupo else int(g.get('max_objetos_por_grupo') or 3)
    mo = int(max_out or g.get('max_out_por_defecto') or 32768)
    est = float(g.get('tokens_salida_estimados_por_objeto') or 9000)
    margen = float(g.get('margen_max_tokens') or 0.75)
    if n_ya >= tope_n:
        return False
    if (n_ya + 1) * est > mo * margen:
        return False
    return True

def armar_grupos(fichas, max_out=None, por_grupo=None):
    """Parte una lista de fichas en grupos que caben en el tope de salida."""
    grupos, actual = [], []
    for f in fichas:
        if actual and not tamano_grupo(len(actual), max_out=max_out, por_grupo=por_grupo):
            grupos.append(actual); actual = []
        actual.append(f)
    if actual:
        grupos.append(actual)
    return grupos

def excluir_cfg():
    return _leer('excluir_de_receta.json')

def excluye_de_receta(it):
    """(True, motivo) si este objeto del plan no va a receta. Flags del propio plan + nombres de estructura del JSON."""
    cfg = excluir_cfg()
    for fl in cfg.get('flags_plan') or []:
        if it.get(fl):
            return True, f'marcado {fl} en el plan (no va a receta)'
    nombres = cfg.get('nombres_estructura') or []
    if nombres:
        pat = re.compile(r'^(' + '|'.join(re.escape(n) for n in nombres) + r')\b', re.I)
        for campo in (it.get('oid'), it.get('id'), it.get('nombre')):
            if campo and pat.search(str(campo).strip()):
                return True, 'estructura del cuarto o efecto (no va a receta)'
    return False, None

def id_pieza_pedido(o):
    """Id de la pieza en un pedido de recetas sueltas: campo universal `id` o `pieza_id`; `gdc` queda como alias de ese campo (no es un canal fijo)."""
    return o.get('id') or o.get('pieza_id') or o.get('gdc')

def coincide_en_escena(base, claves, corto, escenario=None):
    """¿Esta instancia (id sin #) es la pieza pedida? Emparejado exacto o slug completo; nunca un sufijo suelto (p. ej. …-madera-rio ≠ rio)."""
    base = (base or '').split('#')[0]
    claves =[REDACTED]
    if any(base == k or base.startswith(k + '-') for k in claves):
        return True
    if escenario and base.startswith(f'amb-{escenario}-'):
        slug = base[len(f'amb-{escenario}-'):]
        if corto and slug == corto:
            return True
        if any(slug == k or (k.startswith('obj-') and slug == k[4:]) for k in claves):
            return True
    return False

def cargar_respuesta(texto):
    """Lee un JSON de recetas; si llegó truncado (MAX_TOKENS), salva las recetas completas que se puedan leer. No inventa las que faltan."""
    t = (texto or '').strip()
    if t.startswith('```'):
        t = t.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
    try:
        obj = json.loads(t)
        return obj, None
    except json.JSONDecodeError as e:
        recetas, meta = [], {}
        m = re.search(r'"recetas"\s*:\s*\[', t)
        if not m:
            return None, str(e)
        head = t[:m.start()]
        for key in ('schema', 'grupo', 'fecha'):
            mm = re.search(r'"%s"\s*:\s*"([^"]*)"' % key, head)
            if mm:
                meta[key] = mm.group(1)
        i, dec = m.end(), json.JSONDecoder()
        while i < len(t):
            while i < len(t) and t[i] in ' \n\r\t,':
                i += 1
            if i < len(t) and t[i] == ']':
                break
            try:
                obj, j = dec.raw_decode(t, i)
            except json.JSONDecodeError:
                break
            if isinstance(obj, dict) and obj.get('objeto_id'):
                recetas.append(obj)
            i = j
        if not recetas:
            return None, str(e)
        meta.setdefault('schema', 'recetas_objetos/v1')
        meta['recetas'] = recetas
        meta['_salvadas_de_truncada'] = True
        return meta, f'respuesta truncada: {len(recetas)} receta(s) completa(s) salvadas'
