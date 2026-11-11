# -*- coding: utf-8 -*-
"""MYIA · Taller n8n · orden 65 (Ricardo pt455u): estilo COMPLETO del canal y modelo/talla de imagen DEL CANAL. Genérico.

Por qué existe:
- La ficha guarda style_fijo.descripcion_en pasada por myia_estilo_fijo (E1.clean_gloss(..., 480)): el Validador de estilo de la
  app corta la frase a 480 caracteres (límite oficial de la app, para que style_header la reconozca). Un estilo de la biblioteca de
  la app (myia_estilos.PRESETS) más largo que eso llega CORTADO a la ficha («Characters: fine thin clean lineart, soft.»).
- El taller no cambia la app ni la ficha: aquí se RESUELVE el texto completo desde la MISMA fuente de la que salió (el preset de
  myia_estilos cuyo texto empieza igual o cuyo nombre es el mismo), y se avisa si parece cortado y no hay fuente completa.
- Modelo y talla de imagen: SIEMPRE los del canal (channels.data.imagen_modelo / imagen_talla, igual que web/myia_imagen.py).
  Precio: precios_myia.json de la app. Si falta algo → no se cotiza ni se llama (no se supone nada).
Solo lee. Sin red.
"""
import re, sys, json, sqlite3
from pathlib import Path

REPO = Path('/opt/myia-staging-arreglos-20261026/repo')
STUDIO_DB = Path('/opt/myia-staging-arreglos-20261026/demo_chat/estudio/web/data/studio.db')
LIMITE_FICHA = 480   # E1.clean_gloss(descripcion_en, 480) en web/myia_estilo_fijo.py
TECNICA_VS_CONTENIDO = (
    "Fixed channel style. Apply its TECHNIQUE exactly (painting medium, brushwork, texture, line quality, lighting, color palette, "
    "atmosphere). Its example subjects (for example foliage, stones, magic glow, fur) are not content to add: adapt them to what "
    "really exists in this place and render this place's real materials with that same technique. Never replace this place with "
    "the style's example scenery. The 'Characters' part applies only to characters added later, not to this empty set. Style:")


def _ws(s): return re.sub(r'\s+', ' ', str(s or '')).strip()


def _sin_punto(s): return _ws(s).rstrip(' .,;:')


def _web():
    w = str(REPO / 'web')
    if w not in sys.path: sys.path.insert(0, w)


def canal_datos(canal_id, db=None):
    """channels.data del canal (dict). Base de solo lectura (mode=ro)."""
    s = sqlite3.connect(f'file:{db or STUDIO_DB}?mode=ro', uri=True)
    try:
        r = s.execute('SELECT data FROM channels WHERE id=?', (canal_id,)).fetchone()
    finally:
        s.close()
    if not r: return None
    d = r[0]
    try: return json.loads(d) if isinstance(d, str) else (d or {})
    except Exception: return {}


def _presets():
    try:
        _web(); import myia_estilos as ME
        return ME, [ME.get(k) for k in ME.KEYS]
    except Exception:
        return None, []


def resolver(cd):
    """Estilo fijo aprobado, COMPLETO. None si el canal no tiene style_fijo aprobado.
    Devuelve nombre, descripcion_en (completa), fondo_en, negativo, origen y avisos."""
    cd = cd or {}
    sf = cd.get('style_fijo') if isinstance(cd.get('style_fijo'), dict) else None
    if not sf or not sf.get('aprobado') or not _ws(sf.get('descripcion_en')): return None
    ficha = _ws(sf.get('descripcion_en')); nombre = _ws(sf.get('nombre'))
    ME, ps = _presets()
    elegido, motivo = None, ''
    pk = _ws(cd.get('style_preset'))
    cands = [p for p in ps if p and p['key'] == pk] + [p for p in ps if p and _ws(p['label']).lower() == nombre.lower()] + [p for p in ps if p]
    for p in cands:
        full = _ws(p['anchor_en'])
        if full == ficha:
            elegido, motivo = p, 'igual'; break
        if len(full) > len(ficha) and full.startswith(_sin_punto(ficha)):
            elegido, motivo = p, 'cortado'; break
    avisos = []
    if motivo == 'cortado':
        desc = _ws(elegido['anchor_en'])
        avisos.append(f"La ficha guarda el estilo CORTADO a {len(ficha)} caracteres (el Validador de estilo de la app corta en {LIMITE_FICHA}). "
                      f"Se usa el texto COMPLETO ({len(desc)} caracteres) del estilo de la app «{elegido['label']}» (myia_estilos.{elegido['key']}), del que salió.")
        origen = f"myia_estilos.{elegido['key']} (completo; la ficha lo tenía cortado)"
    else:
        desc = ficha; origen = 'style_fijo.descripcion_en (ficha del canal)'
        if not elegido and len(ficha) >= LIMITE_FICHA - 40:
            avisos.append(f'El estilo de la ficha mide {len(ficha)} caracteres, cerca del corte de {LIMITE_FICHA} del Validador de la app, y no hay '
                          'otra fuente con el texto completo: revisa en la ficha que no esté cortado.')
    neg = _ws(sf.get('negativo')) or _ws(cd.get('negative_prompt'))
    if not neg and elegido and ME: neg = ME.negatives_for(elegido['key'])
    return {'nombre': nombre, 'descripcion_en': desc, 'fondo_en': _ws(elegido['bg_style']) if elegido else '',
            'negativo': neg, 'imagen': _ws(sf.get('imagen')), 'origen_texto': origen, 'largo_en_ficha': len(ficha),
            'largo_usado': len(desc), 'cortado_en_ficha': motivo == 'cortado', 'avisos': avisos,
            'regla_tecnica_vs_contenido': TECNICA_VS_CONTENIDO}


def bloque_pintura(est, adaptacion=''):
    """Bloque de estilo que se pega SIEMPRE al final de cada pedido de imagen (lo pone el código, no el modelo)."""
    if not est: return ''
    t = f"{TECNICA_VS_CONTENIDO}\n{est['nombre']}\n{est['descripcion_en']}"
    if adaptacion: t += f"\nHow this technique applies to this place: {_ws(adaptacion)}"
    return t


class FaltaImagen(Exception): pass


def imagen_canal(cd):
    """(modelo, talla, precio) del canal + fuente. Sin modelo, talla o precio → FaltaImagen (no se supone)."""
    cd = cd or {}
    m = _ws(cd.get('imagen_modelo')); t = _ws(cd.get('imagen_talla')).upper()
    if not m: raise FaltaImagen('el canal no tiene imagen_modelo (ficha del canal). No se cotiza ni se llama.')
    if t not in ('1K', '2K', '4K'): raise FaltaImagen(f'el canal no tiene imagen_talla válida ({cd.get("imagen_talla")!r}). No se cotiza ni se llama.')
    if str(REPO) not in sys.path: sys.path.insert(0, str(REPO))
    import precios_myia as PR
    fila = ((PR.cargar().get('imagen') or {}).get('modelos') or {}).get(m)
    if not isinstance(fila, dict) or fila.get(t) in (None, ''):
        raise FaltaImagen(f'precios_myia.json no tiene precio para {m} a {t}. No se cotiza ni se llama.')
    try: ref = float(PR.referencia_extra())
    except Exception: ref = 0.0
    return {'modelo': m, 'talla': t, 'usd_por_imagen': float(fila[t]), 'usd_referencia_extra': ref, 'fuente_precio': f'precios_myia.json imagen.modelos["{m}"]["{t}"]',
            'fuente_modelo': 'channels.data.imagen_modelo / imagen_talla (ficha del canal)'}
