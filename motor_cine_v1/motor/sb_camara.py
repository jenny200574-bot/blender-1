# -*- coding: utf-8 -*-
"""[cine_v1 · Ricardo t552u/t559u, 10-nov-2026] CREADOR DE STORYBOARD — paso de CÁMARA (motor copia argon_v2u, US$0, sin GPU).
Lee storyboard.json (+ camara_v1/v2 y entrada_motor.json) de una corrida y, por viñeta:
  1) anota beat (tabla_decision_camara.json, mismo lector que sb3d), emoción, protagonista y cambio de lugar/acción;
  2) escribe el plano: tipo, ángulo, colocación (frente / tres cuartos / lado / detrás / POV / OTS), altura, distancia en alturas
     (nunca menos que d_min = 0,50 m × H/1,70), lente y movimiento — todo de la salida del beat en la tabla;
  3) aplica las reglas de secuencia de la tabla: establecimiento al abrir o al cambiar de lugar (salvo que el guion abra en un
     detalle), re-establecer tras 3 cercanos, no repetir plano+ángulo+colocación 3 veces, regla de 30° con el mismo sujeto,
     eje 180° (mismo lado para el mismo par), general estratégico con tope.
Escribe: storyboard.json (respaldo storyboard_antes_sb_camara.json) con director_imagen.plano/angulo, director_camara.dsl_movimiento
y el bloque camara_tabla; la cámara v1/v2 (respaldos) con los mismos plano/ángulo/movimiento; y sb_camara_reporte.json.
Nada de canal, escenario ni personaje en el código.
Uso: python3 sb_camara.py --corrida DIR [--escribir 1]"""
import argparse, json, shutil, sys, re
from pathlib import Path
AQUI = Path(__file__).resolve().parent; sys.path.insert(0, str(AQUI / 'sb3d'))
import tabla_camara as TC

ESCALA = ['GPG', 'PG', 'PE', 'PA', 'PM', 'PMC', 'PP', 'PPP']
CERCANOS = {'PMC', 'PP', 'PPP'}
ES_EN = {'PPP': 'ECU', 'PP': 'CU', 'PMC': 'MCU', 'PM': 'MS', 'PA': 'MLS', 'PE': 'FS', 'PG': 'WS', 'GPG': 'EWS'}
EN_ES = {v: k for k, v in ES_EN.items()} | {'LS': 'GPG', 'MWS': 'PE', 'ELS': 'GPG'}
ANG_EN = {'NORM': 'EYELEVEL', 'PIC': 'HIGHANGLE', 'CPIC': 'LOWANGLE', 'DUTCH': 'DUTCH', 'CEN': 'OVERHEAD'}
EN_ANG = {v: k for k, v in ANG_EN.items()}
PALABRAS_DETALLE = ('insert_object', 'reveal', 'discovery', 'important_prop')   # beats que justifican abrir en un detalle

def paso(pl, k):
    if pl not in ESCALA: return pl
    return ESCALA[max(0, min(len(ESCALA) - 1, ESCALA.index(pl) + k))]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--corrida', required=True); ap.add_argument('--escribir', type=int, default=1)
    a = ap.parse_args(); C = Path(a.corrida)
    T, F = TC.cargar(); E = json.loads((C / 'entrada_motor.json').read_text())
    sb_p = C / E['storyboard']; bk = C / 'storyboard_antes_sb_camara.json'
    S = json.loads((bk if bk.is_file() else sb_p).read_text())   # idempotente: siempre parte del SB original
    cams = [k for k in ('camara_v1', 'camara_v2') if E.get(k) and (C / E[k]).is_file()]
    CV = {k: json.loads(((C / (Path(E[k]).stem + '_antes_sb_camara.json')) if (C / (Path(E[k]).stem + '_antes_sb_camara.json')).is_file() else (C / E[k])).read_text()) for k in cams}
    cv_por = {v.get('vineta'): v for v in (CV.get('camara_v1') or CV.get('camara_v2') or {}).get('vinetas', [])}
    alt = {p['id']: float(p.get('altura_m') or 1.0) for p in E.get('personajes') or [] if p.get('id')}
    pt = F.get('patron') or {}
    n = len(S.get('vinetas') or [])
    try: max_gen = int(eval(str(pt.get('max_general_por_escena', 'max(2, n_vinetas // 4)')), {'__builtins__': {}}, {'max': max, 'min': min, 'n_vinetas': n}))
    except Exception: max_gen = max(2, n // 4)
    rep = []; prev = []; n_gen = 0; eje_lado = {}
    for i, v in enumerate(S.get('vinetas') or []):
        di = v.setdefault('director_imagen', {}); dc = v.setdefault('director_camara', {}); cv = cv_por.get(v.get('id')) or {}
        en_cuadro = [x.get('id') for x in di.get('en_cuadro') or [] if x.get('id')]
        prota = cv.get('objetivo') or next((x.get('quien') for x in v.get('audio') or [] if x.get('quien')), None) or (en_cuadro[0] if en_cuadro else None)
        disp = set()
        if i == 0: disp.add('inicio_escena')
        P_ = (S['vinetas'][i - 1] if i else {})
        if i and v.get('segmento_genero') != P_.get('segmento_genero'): disp.add('cambio_lugar')
        if i and v.get('beat_narrativo') != P_.get('beat_narrativo'): disp.add('cambio_accion')
        if len(en_cuadro) >= 3: disp.add('tres_o_mas')
        if v.get('audio') and len(en_cuadro) >= 2: disp.add('dialogo')
        beats = TC.buscar_beats(T, F, v, disp)
        if any(b in ('location_change', 'arrive_place', 'leave_place') for b in beats): disp.add('cambio_lugar')
        sps = [TC.spec(T, F, b) for b in beats]; sp = dict(sps[0]) if sps else {}
        orig = {"plano": di.get('plano'), "angulo": di.get('angulo'), "dsl_movimiento": dc.get('dsl_movimiento')}
        plano, ang, tipo, mov = sp.get('plano', 'PM'), sp.get('angulo', 'NORM'), sp.get('colocacion_tipo', 'frente'), sp.get('movimiento', 'STATIC')
        reglas = []
        if tipo in ('POV', 'OTS') and len(en_cuadro) < 2:   # POV/OTS necesita a otro personaje que mire
            tipo = 'frente'; reglas.append('pov_ots: un solo personaje en cuadro -> frente (eyeline)')
        # 1) establecimiento al abrir o al cambiar de lugar (salvo que el guion abra en un detalle y revele)
        if disp & {'inicio_escena', 'cambio_lugar'}:
            if any(b in PALABRAS_DETALLE for b in beats):
                bd = next(b for b in beats if b in PALABRAS_DETALLE); sd = TC.spec(T, F, bd)
                plano, ang, tipo, mov = sd['plano'], sd['angulo'], sd['colocacion_tipo'], sd['movimiento']; sp = dict(sd, d_alturas=sd.get('d_alturas'))
                reglas.append(f'abrir_con_establecimiento: el guion abre en un detalle y revela ({bd}; se respeta)')
            elif n_gen < max_gen:
                est = TC.spec(T, F, 'establish_place' if 'inicio_escena' in disp else ('location_change' if 'location_change' in TC.beats_tabla(T) else 'establish_place'))
                plano, ang, tipo, mov = est['plano'] if est['plano'] in ('GPG', 'PG') else 'PG', est['angulo'], 'general', est['movimiento']
                reglas.append(f"abrir_con_establecimiento ({'inicio' if 'inicio_escena' in disp else 'cambio de lugar'}): {est['beat']}")
        # 2) re-establecer después de 3 cercanos
        if len(prev) >= 3 and all(p_['plano'] in CERCANOS for p_ in prev[-3:]) and plano in CERCANOS and n_gen < max_gen:
            plano = 'PE'; tipo = 'general' if tipo == 'frente' else tipo; reglas.append('reestablecer_despues_de_cercanos: 3 cercanos seguidos -> PE')
        # 3) no repetir plano + ángulo + colocación 3 veces seguidas
        if len(prev) >= 2 and all((p_['plano'], p_['angulo'], p_['tipo']) == (plano, ang, tipo) for p_ in prev[-2:]):
            plano = paso(plano, -1 if plano in CERCANOS else 1); reglas.append(f'no_repetir_tres_veces: plano -> {plano}')
        # 4) regla de 30°: mismo sujeto que la viñeta anterior -> cambiar colocación (≥30°) o el tamaño de forma clara (≥2 pasos)
        if prev and prev[-1]['prota'] == prota and plano in ESCALA and prev[-1]['plano'] in ESCALA and abs(ESCALA.index(plano) - ESCALA.index(prev[-1]['plano'])) < 2 and prev[-1]['tipo'] == tipo:
            tipo = {'frente': 'tres_cuartos', 'tres_cuartos': 'frente', 'lado': 'tres_cuartos', 'general': 'frente'}.get(tipo, tipo)
            reglas.append(f'regla_30: mismo sujeto -> colocación {tipo}')
        # 5) eje 180°: par (protagonista, el otro más cercano en el SB o el eje de continuidad); mismo lado que la última vez
        eje = str((v.get('continuidad') or {}).get('eje') or '')
        par = tuple(sorted([prota, next((q for q in en_cuadro if q != prota), None)])) if prota and len(en_cuadro) >= 2 else None
        lado = None
        if par:
            lado = eje_lado.get(par, +1); eje_lado[par] = lado; reglas.append(f'regla_180: par {par[0]}|{par[1]} lado {lado:+d} (mantener)')
        if tipo == 'general': n_gen += 1
        H = alt.get(prota, 1.0); dmin = TC.d_min(T, F, H)
        d = max(float(sp.get('d_alturas') or 1.6) * H, dmin) if plano not in ('GPG', 'PG') else None
        bloque = {"contrato": "camara_tabla_v1", "beats": beats, "beat": beats[0] if beats else None, "familia_tabla": sp.get('familia_tabla'),
                  "emocion": (v.get('justificacion') or {}).get('emocion_buscada'), "protagonista": prota, "en_cuadro": en_cuadro,
                  "cambio_lugar": 'cambio_lugar' in disp, "cambio_accion": 'cambio_accion' in disp, "inicio": 'inicio_escena' in disp,
                  "plano": plano, "angulo": ang, "colocacion": tipo, "colocacion_tabla": sp.get('colocacion'), "altura": sp.get('altura'),
                  "distancia_alturas": sp.get('d_alturas'), "distancia_m": round(d, 3) if d else None, "d_min_m": round(dmin, 3), "lente_mm": sp.get('lente'),
                  "movimiento": mov, "movimiento_tabla": sp.get('movimiento_tabla'), "elemento_clave": sp.get('elemento_clave'),
                  "familias_especiales": sorted({f for s_ in sps for f in s_['familias']}), "eje_180": {"par": list(par) if par else None, "lado": lado},
                  "reglas_aplicadas": reglas, "original": orig}
        v['camara_tabla'] = bloque
        di['plano'] = ES_EN.get(plano, plano); di['angulo'] = ANG_EN.get(ang, 'EYELEVEL')
        dc['dsl_movimiento'] = f"/{mov}" + (f":{ES_EN.get(plano, plano)}>{ES_EN.get(paso(plano, 1), plano)}:SLOW" if mov == 'DOLLYIN' else '')
        dc['motivacion_tabla'] = f"tabla: {bloque['beat']} ({bloque['familia_tabla']}); reglas: {'; '.join(reglas) or '—'}"
        for k, J in CV.items():   # la cámara v1/v2 dice lo mismo que el SB
            for x in J.get('vinetas', []):
                if x.get('vineta') != v.get('id'): continue
                x['angulo'] = ANG_EN.get(ang, 'EYELEVEL')
                for kf in x.get('keyframes') or []: kf['plano'] = ES_EN.get(plano, plano)
                if x.get('segmentos'): x['segmentos'] = [dict(x['segmentos'][0], movimiento=mov, t_abs=[x['segmentos'][0]['t_abs'][0], x['segmentos'][-1]['t_abs'][1]])]
        prev.append({"plano": plano, "angulo": ang, "tipo": tipo, "prota": prota})
        rep.append({"vineta": v.get('id'), "beats": beats, "protagonista": prota, "original": f"{orig['plano']} {orig['angulo']} {orig['dsl_movimiento']}",
                    "nuevo": f"{ES_EN.get(plano, plano)} {ANG_EN.get(ang)} {tipo} {mov}", "reglas": reglas})
    out = {"contrato": "sb_camara_reporte_v1", "tabla": str(TC.CAT / 'tabla_decision_camara.json'), "generales": n_gen, "max_generales": max_gen, "vinetas": rep}
    if a.escribir:
        for p, src in [(C / 'storyboard_antes_sb_camara.json', sb_p)] + [(C / (Path(E[k]).stem + '_antes_sb_camara.json'), C / E[k]) for k in cams]:
            if not p.exists(): shutil.copy(src, p)
        sb_p.write_text(json.dumps(S, indent=1, ensure_ascii=False))
        for k, J in CV.items(): (C / E[k]).write_text(json.dumps(J, indent=1, ensure_ascii=False))
    (C / 'sb_camara_reporte.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print('RESULT_SB_CAMARA', json.dumps({"vinetas": len(rep), "generales": n_gen}, ensure_ascii=False))
    for r in rep: print(r['vineta'], '|', r['original'], '->', r['nuevo'], '|', ','.join(r['beats']), '|', '; '.join(r['reglas'])[:160])

if __name__ == '__main__': main()
