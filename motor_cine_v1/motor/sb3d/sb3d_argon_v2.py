# -*- coding: utf-8 -*-
"""[argon_v2 · 10-nov-2026 · OK Ricardo t535u/t536u/t537u] Argon como DIRECTOR DE FOTOGRAFÍA que ESCOGE, no que inventa xyz.
Entrada: corrida/sb3d/paquete.json (contrato sb3d_paquete_v2: SOLO candidatas ya re-medidas en 3D en TODA la viñeta) + una hoja
por viñeta (fotos claras C1..Cn con nombres) + guion de la viñeta. Prompt CORTO (< 10 000 caracteres): por viñeta solo su guion,
el censo de quienes están en ella y las candidatas con sus métricas medidas. Salida JSON estricto: por viñeta la candidata elegida
(id), tipo de plano, ángulo, ritmo y movimiento. Corrección: UNA ronda solo con las viñetas que fallaron y el motivo medido.
GENERAL: nada de canal/escenario/personaje en el código. El estilo del canal (opcional) sale de
motor/config_canales/<canal>.json (canal = carpeta padre de E['cadena']); si no existe, texto neutro.
Gasto: misma puerta de fábricas que sb3d_argon.llamar_con_imagenes (ledger ANTES, tope por llamada ≤ US$0,75, sin reintento).
Prueba sin costo: --simulado auto [--inyectar_invalida v4] [--inyectar_invalida_corr v8] (no llama a Argon ni toca el ledger).
Uso: python3 sb3d_argon_v2.py --corrida DIR --fase principal|correccion [--validacion VJ] --autorizacion TXT [--solo_prompt]"""
from __future__ import annotations
import argparse, json, os, re, sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
MOT = AQUI.parent
MAX_PROMPT = 10000
DSL_MOV = ['STATIC', 'LOCK', 'DOLLYIN', 'DOLLYOUT', 'PAN', 'TILT', 'TRACK', 'ORBIT', 'CRANE', 'PEDESTAL', 'ZOOMIN', 'ZOOMOUT', 'STEADICAM', 'HANDHELD', 'WHIPPAN']
RECHAZOS = ['ERROR_EJE_180', 'ERROR_COMPOSICION', 'ERROR_TONO']

def canal_de(E):
    try: return Path(E.get('cadena') or '').parent.name or None
    except Exception: return None

def config_canal(E):
    c = canal_de(E); p = MOT / 'config_canales' / f'{c}.json'
    try: return c, json.loads(p.read_text(encoding='utf-8')), str(p)
    except Exception: return c, {}, None

def nombre(pid, P):
    m = re.match(r'^ch-(.+?)(-[0-9a-f]{3,})?$', pid or '')
    return m.group(1) if m else pid

def _r(x, n=2):
    return [round(float(v), n) for v in x] if isinstance(x, (list, tuple)) else (round(float(x), n) if isinstance(x, (int, float)) else x)

def _corta(s, n):
    s = s if isinstance(s, str) else ' / '.join(map(str, s or []))
    return s if len(s) <= n else s[:n - 1] + '…'

CAT = AQUI / 'catalogo'
def _cat(nombre):
    try: return (CAT / nombre).read_text(encoding='utf-8').strip()
    except Exception: return ''
def familias_cfg():
    try: return json.loads((CAT / 'familias_camara.json').read_text(encoding='utf-8'))
    except Exception: return {}
ABR = {'PRINCIPAL': 'PRIN', 'GENERAL': 'GEN', 'PAISAJE': 'PAIS', 'POV': 'POV', 'OTS': 'OTS', 'RETIRADA': 'RETIR', 'PASE_CARAS': 'PASE'}
def topes_patron(n, F=None):
    """[cine_v1] regla de patrón: generales y especiales estratégicos, con tope (de familias_camara.json, fórmula segura)."""
    pt = (F or familias_cfg()).get('patron') or {}
    def ev(x, dflt):
        try: return int(eval(str(x), {'__builtins__': {}}, {'max': max, 'min': min, 'n_vinetas': n}))
        except Exception: return dflt
    return {"GENERAL": ev(pt.get('max_general_por_escena', 'max(2, n_vinetas // 4)'), max(2, n // 4)),
            "especial": ev(pt.get('max_especial_por_familia', 2), 2), "especiales": pt.get('especiales') or ['POV', 'OTS', 'RETIRADA', 'PASE_CARAS', 'PAISAJE'],
            "seguidas": ev(pt.get('no_repetir_familia_y_plano_seguidas', 2), 2)}
def revisar_patron(elecciones, P):
    """elecciones: [(vid, candidata)] en orden. Devuelve avisos de patrón (topes y repeticiones seguidas)."""
    T = topes_patron(len(P['vinetas'])); cuenta = {}; av = []; prev = []
    for vid, c in elecciones:
        f = c.get('familia') or 'PRINCIPAL'; cuenta[f] = cuenta.get(f, 0) + 1
        if f in ('GENERAL',) and cuenta[f] > T['GENERAL']: av.append(f"{vid}: {cuenta[f]}º GENERAL (tope {T['GENERAL']} por escena)")
        if f in T['especiales'] and cuenta[f] > T['especial']: av.append(f"{vid}: {cuenta[f]}º {f} (tope {T['especial']} por escena)")
        k = (f, c.get('plano'), c.get('angulo')); prev.append(k)
        if len(prev) > T['seguidas'] and len(set(prev[-(T['seguidas'] + 1):])) == 1: av.append(f"{vid}: mismo {f} {k[1]} {k[2]} {T['seguidas'] + 1} veces seguidas")
    return av, cuenta

def limite_prompt(P):
    """[cine_v1] el límite sale del catálogo (familias_camara.json 'prompt_max_caracteres'): la guía + reglas de Ricardo ocupan ~4k."""
    if P.get('cine'):
        try: return int(familias_cfg().get('prompt_max_caracteres') or MAX_PROMPT)
        except Exception: return MAX_PROMPT
    return MAX_PROMPT

def bloque_vineta(v, P, k=1.0):
    cen = P.get('censo') or {}
    pres = []
    for pid in v.get('en_cuadro') or []:
        d = (cen.get(pid) or {}).get('por_vineta', {}).get(v['id'])
        if not d: continue
        pres.append(f"{nombre(pid, P)} {d.get('altura_m')}m@{_r(d.get('base', [])[:2], 1)}" + (" acostado" if d.get('acostado') else ''))
    cs = []; _ms = [c.get('movimiento_sugerido') for c in v.get('candidatas') or [] if c.get('familia') and not c.get('trayecto')]
    vm = max(set(_ms), key=_ms.count) if _ms else None
    for c in v.get('candidatas') or []:
        m = c.get('val3d') or {}
        if c.get('familia'):   # [cine_v1] línea compacta: id familia plano ángulo lente [beat] [desde quién] [trayecto] [cruza 180]
            cm = c.get('c_motor') or {}
            cs.append(f"{c['id']} {ABR.get(c['familia'], c['familia'])} {c.get('plano')} {c.get('angulo')} {int(c.get('lente') or 0)}mm"
                      + (f" a {nombre(cm.get('mira_pj'), P)}" if cm.get('mira_pj') and cm.get('mira_pj') != v.get('objetivo') else '')
                      + (f" desde {nombre(c.get('dueno'), P)}" if c.get('dueno') else '') + (f" [{c['beat']}]" if c.get('beat') else '')
                      + (f" mov:{c.get('movimiento_sugerido') or 'STATIC'}" if c.get('movimiento_sugerido') != vm and not c.get('trayecto') else '')
                      + (" trayecto" if c.get('trayecto') else '') + (" X180" if c.get('cruza_eje') else ''))
            continue
        cs.append(f"{c['id']} {c.get('plano')} {c.get('angulo')} {int(c.get('lente') or 0)}mm d{c.get('dist_m')} vis {m.get('vis_media')}/{m.get('vis_min')} cab {m.get('cabeza_en_cuadro')}"
                  + (" FUERA_DEL_CUARTO" if c.get('fuera_recinto') else '') + (" rescate" if c.get('rescate') else '')
                  + (f" nota:{_corta(m.get('notas') or '', 50)}" if m.get('notas') else ''))
    sbo = v.get('sb_original') or {}
    dis = [x for x in (v.get('disparadores') or []) if x in ('inicio_escena', 'cambio_beat', 'cambio_segmento', 'desplazamiento', 'muchos_cercanos_seguidos', 'contraste_tamano')]
    return (f"## {v['id']} t={v.get('t')}s objetivo={nombre(v.get('objetivo'), P)} (SB: {sbo.get('plano')} {sbo.get('angulo')} {sbo.get('movimiento')})"
            + (f" · momento: {','.join(dis)}" if dis else '') + (f" · mov sugerido: {vm}" if vm and vm != 'STATIC' else '')
            + (f" · SB(tabla): {v['sb_tabla'].get('plano')} {v['sb_tabla'].get('angulo')} {v['sb_tabla'].get('colocacion')}" if v.get('sb_tabla') else '') + (f" · beat: {','.join(v.get('beats_tabla') or [])}" if v.get('beats_tabla') else '') + "\n"
            f"intención: {_corta(v.get('intencion') or '', int(170 * k))}\nacción: {_corta(v.get('accion') or [], int(150 * k))}\n"
            + (f"diálogo: {_corta(v.get('dialogo') or [], int(130 * k))}\n" if v.get('dialogo') else '')
            + f"emoción: {_corta(v.get('emocion') or '', 50)} · {v.get('ritmo_s')} s · presentes: {'; '.join(pres)}\n" + "\n".join(cs))

FORMA = ('{"vinetas":[{"id":"v1","camara":"C2","tipo_plano":"PG|PE|PA|PM|PMC|PP|PPP|GPG","angulo":"NORM|PIC|CPIC|CEN|NAD",'
         '"ritmo":"lenta|media|rapida","movimiento":{"tipo":"' + '|'.join(DSL_MOV) + '","intensidad":0.4,"velocidad":"lenta|media|rapida",'
         '"direccion":"izquierda|derecha|arriba|abajo|adentro|afuera|null"},"justificacion":"<=140 caracteres","rechazo":null}]}')

def construir_prompt(C: Path, fase='principal', fallas=None):
    S = C / 'sb3d'; P = json.loads((S / 'paquete.json').read_text()); E = json.loads((C / 'entrada_motor.json').read_text())
    canal, CC, _ = config_canal(E)
    estilo = CC.get('estilo_fotografia') or CC.get('estilo') or 'el estilo visual de la serie'
    publico = CC.get('publico') or 'el público de la serie'
    sin = [v['id'] for v in P['vinetas'] if not v.get('candidatas')]
    if fase == 'principal':
        vs = [v for v in P['vinetas'] if v.get('candidatas')]
    else:
        ids_f = {f['vineta'] for f in (fallas or [])}
        vs = [v for v in P['vinetas'] if v['id'] in ids_f and v.get('candidatas')]
    ids = [v['id'] for v in vs]
    imgs = [str(S / f"hoja_{v['id']}.jpg") for v in vs if (S / f"hoja_{v['id']}.jpg").is_file()]
    cine = any(c.get('familia') for v in P['vinetas'] for c in v.get('candidatas') or [])
    if cine:   # [cine_v1] reglas de Ricardo + su guía + regla de patrón (textos en catalogo/, nada fijo de canal)
        T = topes_patron(len(P['vinetas']))
        cab = (f"Eres el DIRECTOR DE FOTOGRAFÍA de esta escena ({estilo}; público: {publico}). La escena ya está armada y animada en 3D. "
               "El motor ya armó y midió en Blender, por viñeta, cámaras de varias FAMILIAS (lente fuera de muros/muebles/cuerpos y la cara clave "
               "en cuadro sin quedar tapada del todo; un primer término parcial está bien). TÚ ESCOGES UNA por su id (C1, C2…) según el guion y "
               "la emoción; no inventes posiciones. Familias: PRIN = de frente a la altura de los ojos; GEN = general estratégico; PAIS = paisaje; "
               "POV/OTS = desde los ojos u hombro de otro; RETIR = retirada de escala hasta el techo o la pared; PASE = travelling por las caras. "
               "[beat] = tipo de beat de la tabla de decisión; mov: = movimiento sugerido; X180 = cruza el eje.\n\n"
               + _cat('REGLAS_RICARDO_camara.md') + "\n\n" + _cat('GUIA_RICARDO_resumen.md') + "\n\n"
               f"PATRÓN (obligatorio): GEN como mucho {T['GENERAL']} veces en la escena y solo al inicio o cuando cambia la acción/lugar ('momento'); "
               f"cada especial (POV, OTS, RETIR, PASE, PAIS) como mucho {T['especial']} veces y solo donde cuenta algo; no repitas la misma familia, "
               f"plano y ángulo más de {T['seguidas']} viñetas seguidas; varía los planos y respeta el eje 180°. Mira la hoja de cada viñeta.\n")
    else:
      cab = (f"Eres el DIRECTOR DE FOTOGRAFÍA de esta escena ({estilo}; público: {publico}). La escena ya está armada y animada en 3D. "
           "El motor YA midió en Blender varias cámaras válidas por viñeta (el protagonista se ve, la cámara no está dentro de nada). "
           "TÚ ESCOGES por viñeta UNA candidata por su id (C1, C2…): no inventes posiciones. Elige la que mejor cuente la historia: "
           "quién habla, qué se revela, qué emoción; varía planos entre viñetas seguidas y respeta el eje 180°. "
           "Mira la hoja de cada viñeta (una foto por candidata con su id grande y el nombre de cada personaje). "
           "Formato candidata: id plano ángulo lente distancia_m vis media/mínima del protagonista, cab = cabeza en cuadro.\n")
    if fase != 'principal':
        prev = {}
        try: prev = {x['id']: x for x in json.loads((S / 'sb_argon.json').read_text())['decision']['vinetas']}
        except Exception: pass
        cab += "\nCORRECCIÓN (única): estas viñetas NO pasaron la re-medición 3D con tu elección. Escoge OTRA candidata válida o un movimiento más suave.\n"
        for f in fallas or []:
            if f['vineta'] in ids:
                cab += f"- {f['vineta']}: elegiste {(prev.get(f['vineta']) or {}).get('camara')} → falló: {_corta(f.get('fallas') or [], 220)}\n"
    k = 1.0   # [argon_v2] el prompt se ajusta solo al límite (escenas con muchas viñetas): se acortan los textos, nunca las candidatas
    while True:
        cuerpo = "\n\n".join(bloque_vineta(v, P, k) for v in vs)
        if len(cab) + len(cuerpo) + 1400 <= limite_prompt(P) or k <= 0.25: break
        k = round(k - 0.1, 2)
    pie = (f"\n\nRESPONDE SOLO JSON (sin texto fuera) con exactamente las viñetas {ids}, esta forma:\n{FORMA}\n"
           "Reglas: 'camara' DEBE ser uno de los ids listados en esa viñeta. Movimiento solo del DSL; si dudas, STATIC"
           + (" (RETIR y PASE: movimiento TRAYECTO). No pidas esconder nada; solo si la toma lo exige agrega \"ocultar\":[ids] y \"motivo_ocultar\"." if cine else ".") + "\n"
           "FILTRO ANTENA (revisa al final, antes de responder): si tu elección cruza el eje 180° sin motivo → rechazo \"ERROR_EJE_180\"; "
           "si el protagonista queda mal compuesto (cortado, de espaldas sin motivo, perdido en el fondo) → \"ERROR_COMPOSICION\"; si el plano "
           "contradice la emoción → \"ERROR_TONO\". Si marcas un rechazo, igual escoge la MEJOR candidata disponible.")
    pr = cab + "\n" + cuerpo + pie
    return pr, imgs, ids, sin, canal

def validar(txt, ids, P):
    t = re.sub(r'^```(json)?', '', (txt or '').strip()).rstrip('`').strip()
    try: d = json.loads(t)
    except Exception as e: return None, [f'JSON inválido: {e}']
    if isinstance(d, list): d = {"vinetas": d}
    av = []; cand = {v['id']: {c['id'] for c in v.get('candidatas') or []} for v in P['vinetas']}
    vs = []
    for x in d.get('vinetas', []):
        if not isinstance(x, dict) or x.get('id') not in ids: continue
        x['camara'] = str(x.get('camara') or '').strip().upper()
        if x['camara'] not in cand.get(x['id'], set()): av.append(f"{x['id']}: camara «{x['camara']}» no es candidata ({sorted(cand.get(x['id'], []))})")
        if x.get('rechazo') not in (None, 'null', *RECHAZOS): av.append(f"{x['id']}: rechazo desconocido {x.get('rechazo')}"); x['rechazo'] = None
        if isinstance(x.get('justificacion'), str): x['justificacion'] = x['justificacion'][:200]
        vs.append(x)
    falt = [i for i in ids if i not in {x['id'] for x in vs}]
    if falt: av.append(f'faltan viñetas: {falt}')
    d['vinetas'] = vs
    cs_ = {v['id']: {c['id']: c for c in v.get('candidatas') or []} for v in P['vinetas']}
    ele = [(x['id'], cs_.get(x['id'], {}).get(x['camara'])) for x in vs if cs_.get(x['id'], {}).get(x['camara'])]
    if any(c.get('familia') for _, c in ele):   # [cine_v1] regla de patrón (aviso; la corrección la puede pedir)
        avp, cuenta = revisar_patron(ele, P); av += avp; d['patron'] = {"familias": cuenta, "avisos": avp}
    return d, av

def simular_cine(ids, P, fase, inyectar, excluir=None):
    """[cine_v1] Argon SIMULADO que respeta las reglas: GEN solo en 'momento' y con tope; especiales donde hay disparador y con tope;
    RETIR/POV si hay contraste de tamaño; PASE si hay emoción con 2+ caras; si no PRIN (primero la del beat de la tabla o la del SB),
    variando plano respecto a la anterior y evitando X180."""
    T = topes_patron(len(P['vinetas'])); cuenta = {}; out = []; prev = None
    for v in P['vinetas']:
        if v['id'] not in ids: continue
        cs0 = [c for c in v.get('candidatas') or [] if c.get('id') != (excluir or {}).get(v['id'])] or list(v.get('candidatas') or [])   # corrección: OTRA candidata
        cs = [c for c in cs0 if not c.get('cruza_eje')] or cs0
        dis = set(v.get('disparadores') or []); fam = lambda f: [c for c in cs if c.get('familia') == f]
        ok = lambda f: cuenta.get(f, 0) < (T['GENERAL'] if f == 'GENERAL' else T['especial'])
        c = None; st = v.get('sb_tabla') or {}
        if st:   # el SB (creador, con la tabla y las reglas de secuencia) ya dijo la colocación: se respeta si hay candidata válida
            want = {'general': 'GENERAL', 'POV': 'POV', 'OTS': 'OTS'}.get(st.get('colocacion'))
            if want and fam(want) and ok(want): c = fam(want)[0]
            if c is None and want == 'GENERAL' and fam('PAISAJE') and ok('PAISAJE'): c = fam('PAISAJE')[0]
            dis = dis - {'cambio_beat', 'cambio_segmento', 'desplazamiento'}   # el general estratégico ya lo decidió el SB
        if c is None and dis & {'inicio_escena'} and fam('PAISAJE') and ok('PAISAJE') and 'sb_pide_establecimiento' in dis: c = fam('PAISAJE')[0]
        if c is None and dis & {'inicio_escena', 'cambio_beat', 'cambio_segmento', 'desplazamiento', 'muchos_cercanos_seguidos'} and fam('GENERAL') and ok('GENERAL'): c = fam('GENERAL')[0]
        if c is None and 'contraste_tamano' in dis and fam('RETIRADA') and ok('RETIRADA') and (prev or {}).get('familia') != 'RETIRADA': c = fam('RETIRADA')[0]
        if c is None and 'contraste_tamano' in dis and fam('POV') and ok('POV') and (prev or {}).get('familia') not in ('POV', 'RETIRADA'):
            c = max(fam('POV'), key=lambda x: abs(((x.get('busqueda') or {}).get('escala') or 1) - 1))
        if c is None and 'dos_o_mas' in dis and fam('PASE_CARAS') and ok('PASE_CARAS') and (prev or {}).get('familia') not in ('PASE_CARAS', 'GENERAL', 'POV', 'RETIRADA'): c = fam('PASE_CARAS')[0]
        if c is None:
            pr = fam('PRINCIPAL') or cs
            pref = [x for x in pr if x.get('beat')] + [x for x in pr if (x.get('origen') or '') == 'storyboard'] + pr
            c = next((x for x in pref if not prev or x.get('plano') != prev.get('plano')), pref[0] if pref else None)
        if c: cuenta[c.get('familia')] = cuenta.get(c.get('familia'), 0) + 1
        mv = 'TRAYECTO' if (c or {}).get('trayecto') else ((c or {}).get('movimiento_sugerido') or 'STATIC')
        if mv not in DSL_MOV and mv != 'TRAYECTO': mv = 'STATIC'
        out.append({"id": v['id'], "camara": 'C99' if v['id'] in inyectar else (c['id'] if c else 'C1'), "tipo_plano": (c or {}).get('plano'), "angulo": (c or {}).get('angulo'),
                    "ritmo": "media", "movimiento": {"tipo": mv, "intensidad": 0.4, "velocidad": "media", "direccion": None},
                    "justificacion": f"simulado cine ({fase}): {(c or {}).get('familia')} {(c or {}).get('beat') or ''}".strip(), "rechazo": None, "ocultar": None})
        prev = c
    return json.dumps({"vinetas": out}, ensure_ascii=False)

def simular(ids, P, fase, inyectar):
    """Argon simulado (sin costo): escoge la candidata con mejor visibilidad y varía el plano respecto a la anterior;
    'inyectar' = viñetas a las que se les da a propósito una cámara inexistente (prueba de corrección / STOP)."""
    out = []; prev = None
    for v in P['vinetas']:
        if v['id'] not in ids: continue
        cs = sorted(v.get('candidatas') or [], key=lambda c: -((c.get('val3d') or {}).get('vis_media') or 0))
        c = next((c for c in cs if c.get('plano') != prev), cs[0]) if cs else None
        cid = 'C99' if v['id'] in inyectar else (c['id'] if c else 'C1')
        out.append({"id": v['id'], "camara": cid, "tipo_plano": c.get('plano') if c else None, "angulo": c.get('angulo') if c else None,
                    "ritmo": "media", "movimiento": {"tipo": "STATIC", "intensidad": 0.3, "velocidad": "media", "direccion": None},
                    "justificacion": f"simulado ({fase})", "rechazo": None})
        prev = c.get('plano') if c else prev
    return json.dumps({"vinetas": out}, ensure_ascii=False)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--corrida', required=True); ap.add_argument('--fase', default='principal', choices=['principal', 'correccion'])
    ap.add_argument('--validacion', default=''); ap.add_argument('--autorizacion', default=''); ap.add_argument('--max_out', type=int, default=6000)
    ap.add_argument('--nivel', default='LOW'); ap.add_argument('--solo_prompt', action='store_true'); ap.add_argument('--etiqueta', default='')
    ap.add_argument('--simulado', default=''); ap.add_argument('--inyectar_invalida', default=''); ap.add_argument('--inyectar_invalida_corr', default='')
    a = ap.parse_args(); C = Path(a.corrida); S = C / 'sb3d'; suf = '' if a.fase == 'principal' else '_correccion'
    P = json.loads((S / 'paquete.json').read_text())
    fallas = None
    if a.fase == 'correccion':
        VJ = json.loads(Path(a.validacion).read_text())
        fallas = [{k: r.get(k) for k in ('vineta', 'fallas', 'vis_media', 'vis_min', 'camara', 'avisos_decision')} for r in VJ['vinetas'] if not r.get('ok')]
    prompt, imgs, ids, sin, canal = construir_prompt(C, a.fase, fallas)
    (S / f'argon_prompt_v2{suf}.md').write_text(prompt, encoding='utf-8')
    info = {"contrato": "sb3d_argon_v2_estado", "fase": a.fase, "canal": canal, "caracteres_prompt": len(prompt), "limite_prompt": limite_prompt(P),
            "imagenes": [os.path.basename(i) for i in imgs], "vinetas_pedidas": ids, "vinetas_sin_candidata_valida": sin,
            "alertas": [f"{v}: ninguna cámara pasó la medición 3D → STOP_CAMARA_SIN_SUJETO (no se filma)" for v in sin]}
    if len(prompt) > limite_prompt(P): info['alertas'].append(f'prompt de {len(prompt)} caracteres > {limite_prompt(P)}')
    if not ids:
        info.update(ok=False, motivo='no hay viñetas que pedir'); json.dump(info, open(S / f'sb3d_argon_estado{suf}.json', 'w'), indent=1, ensure_ascii=False)
        print('RESULT_SB3D_ARGON', json.dumps(info, ensure_ascii=False)[:1500]); return
    out = S / f'argon_respuesta{suf}.txt'
    if a.simulado:
        iny = set(filter(None, (a.inyectar_invalida if a.fase == 'principal' else a.inyectar_invalida_corr).split(',')))
        cine = any(c.get('familia') for v in P['vinetas'] for c in v.get('candidatas') or [])
        _ex = {}
        if a.fase != 'principal':
            try: _ex = {x['id']: x.get('camara') for x in json.loads((S / 'sb_argon.json').read_text())['decision']['vinetas']}
            except Exception: _ex = {}
        out.write_text(simular_cine(ids, P, a.fase, iny, _ex) if cine else simular(ids, P, a.fase, iny), encoding='utf-8'); info['argon'] = {"ok": True, "simulado": True, "costo_real_usd": 0.0, "inyectadas": sorted(iny)}
    else:
        sys.path.insert(0, '/opt/myia-fabricas/app'); sys.path.insert(0, str(AQUI))
        import argon_fabrica as AF, sb3d_argon as V1
        cfg = json.loads(V1.CFG_FAB.read_text()); ac = AF._cfg(cfg)
        info['reserva_usd'] = AF.peor_caso(ac, len(prompt) + V1.tokens_medios(imgs) * ac['chars_por_token'], a.max_out)
        if a.solo_prompt:
            info.update(ok=True, solo_prompt=True); print('RESULT_SB3D_ARGON', json.dumps(info, ensure_ascii=False)); return
        try:
            res = V1.llamar_con_imagenes(cfg, prompt, imgs, (a.etiqueta or f"sb3d_v2_{a.fase}_{C.name}")[:80], out, a.autorizacion, a.max_out, nivel=a.nivel)
            info['argon'] = {k: res.get(k) for k in ('ok', 'ledger_n', 'costo_real_usd', 'reserva_usd', 'tokens_entrada', 'tokens_salida', 'finish', 'error', 'codigo')}
        except AF.ArgonParado as ex:
            info['argon'] = {"ok": False, "parado": str(ex)}
    dec = None
    if out.is_file() and info['argon'].get('ok'):
        dec, av = validar(out.read_text(encoding='utf-8'), ids, P); info['avisos_validacion'] = av
    if dec and dec.get('vinetas'):
        json.dump({"contrato": "sb_argon_v3", "fase": a.fase, "corrida": str(C), "decision": dec, "argon": info['argon'],
                   "avisos_validacion": info.get('avisos_validacion'), "sin_candidata_valida": sin}, open(S / f'sb_argon{suf}.json', 'w'), indent=1, ensure_ascii=False)
        info['ok'] = True; info['vinetas'] = len(dec['vinetas'])
    else:
        info['ok'] = False; info['motivo'] = 'sin decisión válida de Argon (las viñetas quedan STOP en aplicar estricto)'
    json.dump(info, open(S / f'sb3d_argon_estado{suf}.json', 'w'), indent=1, ensure_ascii=False)
    print('RESULT_SB3D_ARGON', json.dumps(info, ensure_ascii=False)[:2000])

if __name__ == '__main__': main()
