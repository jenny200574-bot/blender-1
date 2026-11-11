# -*- coding: utf-8 -*-
"""[cine_v1 · Ricardo t552u/t559u, 10-nov-2026] Lectura ÚNICA de la tabla de decisión de cámara (catalogo/tabla_decision_camara.json)
para el creador de storyboard (sb_camara.py) y para la cámara de grabación (blender/sb3d.py). Python puro (sin bpy).
Todo sale del JSON: índice de verbos -> beat -> salida (plano, ángulo, colocación, altura, distancia en alturas, lente, movimiento).
Las equivalencias con el motor (alias de plano, colocación -> azimut, altura -> dz, movimiento -> DSL, beat -> familia) están en
catalogo/familias_camara.json["tabla"]. Nada de canal, escenario ni personaje."""
import json, re, unicodedata
from pathlib import Path
CAT = Path(__file__).resolve().parent / 'catalogo'

def cargar(cat=CAT):
    T = json.loads((Path(cat) / 'tabla_decision_camara.json').read_text(encoding='utf-8'))
    F = json.loads((Path(cat) / 'familias_camara.json').read_text(encoding='utf-8'))
    return T, F

def norm(x): return ''.join(ch for ch in unicodedata.normalize('NFD', str(x).lower()) if unicodedata.category(ch) != 'Mn')

def texto_vineta(v, campos):
    out = []
    for k in campos:
        x = v
        for kk in k.split('.'): x = (x or {}).get(kk) if isinstance(x, dict) else None
        if x: out.append(x if isinstance(x, str) else json.dumps(x, ensure_ascii=False))
    return norm(' '.join(out))

def beats_tabla(T):
    return {b['id']: (f['id'], b) for f in T.get('familias') or [] for b in f.get('beats') or []}

def buscar_beats(T, F, v, disp=(), n_max=None):
    """verbos del SB (índice de la tabla) -> beat ids en orden de aparición; si nada coincide, fallback por familia."""
    tc = F.get('tabla') or {}; B = beats_tabla(T)
    t = texto_vineta(v, tc.get('campos_texto_sb') or ['beats_visuales', 'intencion_narrativa']); hits = []
    for k, bid in (T.get('indice_verbos') or {}).items():
        if len(k) < int(tc.get('min_len_verbo', 3)) or bid not in B: continue
        m = re.search(r'\b' + re.escape(norm(k).replace('_', ' ')) + r'\b', t)
        if m: hits.append((m.start(), -len(k), bid))
    hits.sort(); out = []
    for _, _, bid in hits:
        if bid not in out: out.append(bid)
    out = out[:int(n_max or tc.get('max_beats_por_vineta', 2))]
    if not out:
        fb = {f['id']: f.get('fallback_id') for f in T.get('familias') or []}
        if {'inicio_escena', 'cambio_lugar'} & set(disp): out = [fb.get('espacio_escala') or 'fallback_general']
        elif 'tres_o_mas' in disp: out = [fb.get('grupo') or 'fallback_general']
        elif 'dialogo' in disp: out = [fb.get('dialogo') or 'fallback_general']
        else: out = ['fallback_general']
    return [b for b in out if b in B]

def _primero(v): return str(v or '').upper().split('_O_')[0]

def spec(T, F, bid):
    """salida del beat -> parámetros del motor (plano ES, ángulo, azimut(es), dz en alturas, d en alturas, lente, movimiento DSL, familias)."""
    tc = F.get('tabla') or {}; fam_t, b = beats_tabla(T)[bid]; o = b.get('salida') or {}
    pl = str(o.get('plano') or 'MS').upper(); pl = (tc.get('alias_plano') or {}).get(pl, pl)
    if pl not in (F.get('planos') or {}): pl = 'PM'
    an = _primero(o.get('angulo') or 'NORM'); an = (tc.get('angulo_alias') or {}).get(an, an)
    if an not in ('NORM', 'PIC', 'CPIC', 'DUTCH'): an = 'NORM'
    col = str(o.get('colocacion') or 'frente'); az = [0]; col0 = col.split('_o_')[0]
    for k_, v_ in (tc.get('colocacion_az_deg') or {}).items():
        if col0.startswith(k_): az = v_; break
    alt = str(o.get('altura') or 'ojos').split('_o_')[0].split('_luego_')[0]; dz = (tc.get('altura_dz_x_altura') or {}).get(alt, 0.0)
    le = o.get('lente_mm'); le = (sum(le) / len(le)) if isinstance(le, list) and le else (float(le) if le else None)
    mv_raw = str(o.get('movimiento') or 'STATIC').upper(); mv = 'STATIC'
    for k_, v_ in (tc.get('movimiento_dsl') or {}).items():
        if mv_raw.split('_O_')[0].startswith(k_): mv = v_; break
    fams = set(); af = tc.get('a_familia') or {}
    if (af.get('beat') or {}).get(bid): fams.add(af['beat'][bid])
    for k_, v_ in (af.get('colocacion_contiene') or {}).items():
        if k_.lower() in col.lower(): fams.add(v_)
    for k_, v_ in (af.get('movimiento_contiene') or {}).items():
        if k_ in mv_raw: fams.add(v_)
    if mv == 'RETIRADA': fams.add('RETIRADA'); mv = 'STATIC'
    tipo = 'POV' if 'POV' in fams else ('OTS' if 'OTS' in fams else ('lado' if 90 in [abs(a) for a in az] else ('detras' if 180 in az else ('tres_cuartos' if 45 in [abs(a) for a in az] else 'frente'))))
    return {"beat": bid, "familia_tabla": fam_t, "nombre": b.get('nombre'), "plano": pl, "angulo": an, "colocacion": col, "colocacion_tipo": tipo, "az": az,
            "dz_H": dz, "altura": alt, "d_alturas": o.get('distancia_alturas'), "lente": le, "movimiento": mv, "movimiento_tabla": mv_raw,
            "elemento_clave": o.get('elemento_clave'), "familias": sorted(fams)}

def d_min(T, F, altura_m):
    """[research + Ricardo] 0,50 m para 1,70 m, proporcional a la altura; nunca menos que el mínimo absoluto (lente)."""
    D = dict(F.get('distancia') or {}); cd = (T or {}).get('constantes_distancia') or {}
    href = float(cd.get('altura_referencia_m') or D.get('altura_referencia_m') or 1.70)
    amax = float(cd.get('acercamiento_maximo_ref_m') or D.get('acercamiento_max_m') or 0.5)
    return max(float(D.get('minimo_absoluto_m', 0.06)), amax * min(1.0, float(altura_m) / href))
