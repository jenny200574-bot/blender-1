"""PISTA INMI (2026-11-01) ETAPA 2 — CINEMATIC PROFILE SELECTOR (CÓDIGO, gratis, auditable).
Recibe los segmentos de la etapa 1 (géneros con peso) y COMBINA los perfiles modulares de config/perfiles/ por segmento:
  - textos de reglas: todos los perfiles del segmento, ordenados por peso (Argon los lee como guía, no como plantilla);
  - números (duración de viñeta, lente): promedio ponderado;
  - listas (planos, ángulos, movimientos, transiciones preferidas): puntaje = suma de pesos; un movimiento es «evitar» solo si pesa más
    quien lo evita que quien lo prefiere;
  - el reglamento del nivel 3 (si existe) MANDA sobre el género: recorta lentes y quita lo prohibido.
Nunca fija cuántas viñetas hay. También pasa los segmentos (anclados a citas del guion) a SEGUNDOS con los beats del 01."""
import sb_comun as S

PAUSAS = {'pocas': 1, 'algunas': 2, 'muchas': 3}


def indice(): return S.leer(S.AQUI / 'config' / 'perfiles' / '_indice.json') or {}


def perfil(gid):
    ix = indice(); g = (ix.get('alias') or {}).get(S.norm(gid).replace('_', ' '), gid)
    g = g if g in (ix.get('perfiles') or {}) else (ix.get('alias') or {}).get(S.norm(gid), g)
    f = (ix.get('perfiles') or {}).get(g)
    return (g, S.leer(S.AQUI / 'config' / 'perfiles' / f)) if f else (g, None)


def combinar(generos, subgenero=None, regl=None):
    """generos = [{genero, peso}] → perfil combinado + avisos."""
    av, P = [], []
    for x in generos or []:
        gid, p = perfil(x.get('genero'))
        if not p: av.append(f"género «{x.get('genero')}» sin perfil en config/perfiles (se ignora; agregarlo es agregar un archivo)"); continue
        P.append((max(0.0, float(x.get('peso') or 0)), gid, p))
    tot = sum(w for w, _, _ in P) or 1.0
    P = sorted([(w / tot, g, p) for w, g, p in P], key=lambda z: -z[0])
    if not P: return {'fuentes': [], 'reglas': {}, 'preferencias': {}}, av + ['segmento sin perfiles: se dirige solo con gramática clásica de continuidad']
    campos = list(P[0][2]['reglas'])
    reglas = {c: [f"{g} ({round(w, 2)}): {p['reglas'].get(c)}" for w, g, p in P if p['reglas'].get(c)] for c in campos}
    def media(k, i): return round(sum(w * p['validable'][k][i] for w, _, p in P), 2)
    pref = {'duracion_vineta_s': [media('duracion_vineta_s', 0), media('duracion_vineta_s', 1)], 'lente_mm': [media('lente_mm', 0), media('lente_mm', 1)]}
    for k in ('planos_preferidos', 'angulos_preferidos', 'movimientos_preferidos', 'transiciones_preferidas'):
        sc = {}
        for w, _, p in P:
            for t in p['validable'].get(k) or []: sc[t] = sc.get(t, 0) + w
        pref[k] = [t for t, _ in sorted(sc.items(), key=lambda z: -z[1])]
    ev, pr = {}, {}
    for w, _, p in P:
        for t in p['validable'].get('movimientos_evitar') or []: ev[t] = ev.get(t, 0) + w
        for t in p['validable'].get('movimientos_preferidos') or []: pr[t] = pr.get(t, 0) + w
    pref['movimientos_evitar'] = sorted(t for t in ev if ev[t] > pr.get(t, 0))
    pz = sum(w * PAUSAS.get(p['validable'].get('pausas'), 2) for w, _, p in P)
    pref['pausas'] = 'pocas' if pz < 1.5 else ('muchas' if pz >= 2.5 else 'algunas')
    sub = []
    for _, _, p in P:
        for k, v in (p.get('subgeneros') or {}).items():
            if subgenero and S.norm(k).replace(' ', '_') in S.norm(subgenero).replace(' ', '_') or (subgenero and S.norm(subgenero) in S.norm(k)): sub.append(f'{k}: {v}')
    ejemplos = [f"{g}: {p.get('ejemplo_puerta')}" for _, g, p in P if p.get('ejemplo_puerta')]
    if regl:   # nivel 3 manda sobre el género
        lc = (regl.get('lenguaje_camara') or {})
        if lc.get('lente_mm_min') is not None: pref['lente_mm'][0] = max(pref['lente_mm'][0], float(lc['lente_mm_min']))
        if lc.get('lente_mm_max') is not None: pref['lente_mm'][1] = min(pref['lente_mm'][1], float(lc['lente_mm_max']))
        for k, kp in (('movimientos_preferidos', 'movimientos_prohibidos'), ('angulos_preferidos', 'angulos_prohibidos'), ('planos_preferidos', 'planos_prohibidos')):
            pref[k] = [t for t in pref[k] if t not in (lc.get(kp) or [])]
    return {'fuentes': [{'perfil': g, 'peso': round(w, 3)} for w, g, _ in P], 'subgenero': subgenero or '', 'notas_subgenero': sub,
            'reglas': reglas, 'preferencias': pref, 'ejemplos_direccion': ejemplos}, av


def a_segundos(segmentos, acciones, trozo, duracion):
    """Segmentos de la etapa 1 (citas) → [t0, t1] con los beats del 01 (cada beat trae su cita del guion). Gratis.
    Devuelve (segmentos_con_t, avisos). Si una cita no se encuentra, ese corte se pone donde está su beat más cercano o se une al anterior."""
    av = []; N = len(segmentos or [])
    if not N: return [], ['etapa 1 sin segmentos para esta escena']
    pos_b = []
    for a in acciones or []:
        p = S.posicion(a.get('cita') or '', trozo)
        if p is None: av.append(f"beat {a.get('id')}: su cita no está en el guion de la escena (no ayuda a ubicar segmentos)")
        else: pos_b.append((p, float(a['t'][0]), a.get('id')))
    pos_b.sort()
    cortes = [0.0]
    for k, sg in enumerate(segmentos[1:], 1):
        p = S.posicion(sg.get('desde_cita') or '', trozo)
        if p is None: av.append(f'segmento {k}: «desde_cita» no está en el guion; se une al anterior'); cortes.append(None); continue
        sig = [t for q, t, _ in pos_b if q >= p]
        cortes.append(min(sig) if sig else float(duracion))
    out = []; t_prev = 0.0
    for k, sg in enumerate(segmentos):
        if cortes[k] is None: continue
        out.append({**sg, 'indice_etapa1': k})
    for i, sg in enumerate(out):
        t0 = 0.0 if i == 0 else cortes[sg['indice_etapa1']]
        t0 = max(t0, t_prev); sg['t'] = [round(t0, 3), None]; t_prev = t0
        if i: out[i - 1]['t'][1] = round(t0, 3)
    if out: out[-1]['t'][1] = float(duracion)
    limpio = []
    for sg in out:
        if sg['t'][1] - sg['t'][0] <= 1e-6: av.append(f"segmento {sg['indice_etapa1']}: queda sin tiempo (ningún beat del 01 cae en él); se omite"); continue
        limpio.append(sg)
    for i, sg in enumerate(limpio): sg['indice'] = i
    return limpio, av


def seleccionar(segmentos, regl=None):
    """Etapa 2 completa: un perfil combinado por segmento."""
    out, av = [], []
    for sg in segmentos:
        c, a = combinar(sg.get('generos'), sg.get('subgenero'), regl); av += [f"segmento {sg.get('indice')}: {x}" for x in a]
        out.append({'segmento': sg.get('indice'), 't': sg.get('t'), **c})
    return out, av
