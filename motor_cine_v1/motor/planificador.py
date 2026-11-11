"""planificador — A* (python-pathfinding) + RVO2 (Python-RVO2) [motor unificado v1, 10-nov-2026].
Corre FUERA de Blender (python3.11 del pod; el .so de RVO2 es cpython-311).
Entradas: entrada_motor.json (puntos, N, fps), movimiento.json (segmentos traducidos), inventario.json (medido en el molde de escenario
por blender/inventario_set.py). No hay línea recta a ciegas: cada «caminar» es una ruta A* sobre la grilla del piso real del set
(obstáculos medidos, inflados por el radio del personaje), suavizada por línea de vista, y luego RVO2 evita choques entre personajes.
Salida plan.json: por personaje y cuadro -> x, y, rumbo_deg (convención 01: ángulo desde +X hacia donde mira), dist (metros
caminados acumulados, para la fase del clip), modo (quieto|caminar|girar|acoplado|oculto)."""
import json, math, argparse, sys
# [argon_v2 10-nov-2026, Ricardo t535u/t536u/t538u] reglas GENERALES (cualquier canal/escenario/personaje; todo sale de los datos):
#  - validación 01: cada marca debe estar libre (fuera de muebles) y ser ALCANZABLE (misma zona transitable del piso real);
#  - separación mínima entre personajes = suma de sus radios (radio por altura) + margen: si dos marcas simultáneas se pisan,
#    se separan lo justo hacia espacio libre (aviso SEPARACION_AJUSTADA);
#  - relaciones (movimiento.json['relaciones'], de relaciones.py): anclados salen del plan (los lleva su portador);
#    sentado_en / acostado_en: ese mueble deja de ser obstáculo SOLO para ese personaje (se apoya en su superficie);
#    debajo_de: solo si el hueco libre bajo el mueble (medido en el inventario) cabe al personaje; si no -> RELACION_IMPOSIBLE.
FACTOR_ACOSTADO = 0.45   # grosor de un cuerpo acostado ≈ 0.45 × altura (proporción genérica, no de un personaje)
SEP_MARGEN_M = 0.02

RES = 0.05; RADIO = {'default': 0.2}; GIRO_MAX_DEG_S = 300.0; GIRO_MIN_DEG_S = 45.0; VEL_MAX = 1.6
# [t518 10-nov-2026] personajes NUNCA dentro de muebles: radio según la altura del ADN, inicio/fin proyectados al borde libre
# (antes liberar() vaciaba la celda aunque cayera dentro de la cama), RVO2 con los muebles como obstáculos estáticos,
# los quietos clavados en su marca y verificación final cuadro a cuadro (POSICION_EN_MUEBLE / CHOQUE_MUEBLE_PLAN).
RADIO_MIN = 0.07; RADIO_MAX = 0.2; RADIO_K = 0.18          # radio = clamp(0.18 × altura, 0.07, 0.20): un personaje de 0,18 m -> 0,07
TOL_MUEBLE_M = 0.01                                        # tolerancia de la verificación final (huella del personaje vs mueble)

def radio_de(pid, E):
    if pid in RADIO: return RADIO[pid]
    for p in E.get('personajes', []):
        if p.get('id') == pid and p.get('altura_m'):
            return max(RADIO_MIN, min(RADIO_MAX, RADIO_K * float(p['altura_m'])))
    return RADIO['default']

def _dist_caja(p, ob):
    (ax, ay), (bx, by) = ob['bbox_xy']
    dx = max(ax - p[0], 0.0, p[0] - bx); dy = max(ay - p[1], 0.0, p[1] - by)
    return math.hypot(dx, dy)

def choques_huella(p, r, inv, tol=TOL_MUEBLE_M):
    """muebles (obstaculos_piso) que pisa el disco de radio r centrado en p (sin inflar). Lista de ids."""
    return [ob['id'] for ob in inv.get('obstaculos_piso', []) if _dist_caja(p, ob) < r - tol]

def piezas_de(obj, inv):
    """piezas del inventario que pertenecen a un objeto pedido (id exacto, 'id#n', 'id__n')."""
    return [ob for ob in inv.get('obstaculos_piso', []) if ob['id'] == obj or ob['id'].startswith(obj + '#') or ob['id'].startswith(obj + '__')]

def hueco_debajo(obj, inv):
    """altura libre bajo la cubierta del mueble (piezas que cubren ≥40 % de su huella; las patas no cuentan). None si no hay datos."""
    ps = [p for p in piezas_de(obj, inv) if p.get('min') and p.get('max')]
    if not ps: return None, []
    ax = min(p['min'][0] for p in ps); ay = min(p['min'][1] for p in ps); bx = max(p['max'][0] for p in ps); by = max(p['max'][1] for p in ps)
    A = max(1e-6, (bx - ax) * (by - ay)); piso = float(inv.get('piso_z_mediana') or 0.0)
    cub = [p for p in ps if (p['max'][0] - p['min'][0]) * (p['max'][1] - p['min'][1]) >= 0.4 * A and p['min'][2] > piso + 0.005]
    if not cub: return 0.0, []
    z = min(p['min'][2] for p in cub); return round(z - piso, 3), [p['id'] for p in cub]

def inv_sin(inv, excluir):
    if not excluir: return inv
    return dict(inv, obstaculos_piso=[ob for ob in inv.get('obstaculos_piso', []) if ob['id'] not in excluir])

def componentes(g):
    """etiqueta de zona transitable por celda (4-vecinos); devuelve (etiquetas, id de la zona más grande)."""
    lab = [[-1] * g.W for _ in range(g.H)]; tam = {}; k = 0
    for j0 in range(g.H):
        for i0 in range(g.W):
            if not g.m[j0][i0] or lab[j0][i0] >= 0: continue
            pila = [(i0, j0)]; lab[j0][i0] = k; n = 0
            while pila:
                i, j = pila.pop(); n += 1
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    a, b = i + di, j + dj
                    if 0 <= a < g.W and 0 <= b < g.H and g.m[b][a] and lab[b][a] < 0: lab[b][a] = k; pila.append((a, b))
            tam[k] = n; k += 1
    return lab, (max(tam, key=tam.get) if tam else None)

def smooth(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)

def ang_lerp(a, b, u):
    d = (b - a + 180) % 360 - 180; return a + d * u

class Grilla:
    def __init__(s, inv, radio):
        (x0, y0), (x1, y1) = inv['limites_xy']
        s.x0, s.y0 = x0, y0; s.W = int(math.ceil((x1 - x0) / RES)) + 1; s.H = int(math.ceil((y1 - y0) / RES)) + 1
        s.m = [[1] * s.W for _ in range(s.H)]          # 1 = libre
        margen = radio + 0.03
        for ob in inv.get('obstaculos_piso', []):
            (ax, ay), (bx, by) = ob['bbox_xy']
            for j in range(s.H):
                y = s.y0 + j * RES
                if y < ay - margen or y > by + margen: continue
                for i in range(s.W):
                    x = s.x0 + i * RES
                    if ax - margen <= x <= bx + margen: s.m[j][i] = 0
        for j in range(s.H):                               # paredes = borde del piso, inflado
            for i in range(s.W):
                x = s.x0 + i * RES; y = s.y0 + j * RES
                if x < x0 + margen or x > x1 - margen or y < y0 + margen or y > y1 - margen: s.m[j][i] = 0
    def celda(s, p): return (min(s.W - 1, max(0, int(round((p[0] - s.x0) / RES)))), min(s.H - 1, max(0, int(round((p[1] - s.y0) / RES)))))
    def xy(s, c): return (s.x0 + c[0] * RES, s.y0 + c[1] * RES)
    def libre(s, p):
        i, j = s.celda(p); return bool(s.m[j][i])
    def proyectar(s, p, rmax=1.5):
        """celda libre más cercana a p (anillos crecientes). Devuelve (punto, distancia) o (None, None)."""
        if s.libre(p): return list(p), 0.0
        ci, cj = s.celda(p); mejor = None
        for k in range(1, int(rmax / RES) + 1):
            for j in range(cj - k, cj + k + 1):
                for i in range(ci - k, ci + k + 1):
                    if max(abs(i - ci), abs(j - cj)) != k or not (0 <= i < s.W and 0 <= j < s.H) or not s.m[j][i]: continue
                    q = s.xy((i, j)); d = math.dist(q, p)
                    if mejor is None or d < mejor[1]: mejor = (list(q), d)
            if mejor and mejor[1] <= k * RES: break
        return mejor if mejor else (None, None)
    def liberar(s, p, r=0.12):   # [t518] YA NO SE USA para inicio/fin (metía personajes dentro de muebles); se deja por compatibilidad
        ci, cj = s.celda(p); k = int(math.ceil(r / RES)) + 1
        for j in range(cj - k, cj + k + 1):
            for i in range(ci - k, ci + k + 1):
                if 0 <= i < s.W and 0 <= j < s.H and math.hypot((i - ci) * RES, (j - cj) * RES) <= r: s.m[j][i] = 1
    def libre_linea(s, a, b):
        n = max(2, int(math.dist(a, b) / (RES * 0.5)))
        for k in range(n + 1):
            u = k / n; i, j = s.celda((a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u))
            if not s.m[j][i]: return False
        return True

def ruta_astar(g, p0, p1):
    from pathfinding.core.grid import Grid
    from pathfinding.finder.a_star import AStarFinder
    from pathfinding.core.diagonal_movement import DiagonalMovement
    # [t518] inicio/fin dentro de un mueble -> se proyectan al borde libre (el aviso lo da planear)
    p0 = g.proyectar(p0)[0] or p0; p1 = g.proyectar(p1)[0] or p1
    grid = Grid(matrix=g.m)
    s = grid.node(*g.celda(p0)); e = grid.node(*g.celda(p1))
    path, _ = AStarFinder(diagonal_movement=DiagonalMovement.only_when_no_obstacle).find_path(s, e, grid)
    if not path: return None
    pts = [list(p0)] + [list(g.xy((n.x, n.y))) for n in path[1:-1]] + [list(p1)]
    out = [pts[0]]; k = 0                                  # suavizado por línea de vista
    while k < len(pts) - 1:
        m = len(pts) - 1
        while m > k + 1 and not g.libre_linea(pts[k], pts[m]): m -= 1
        out.append(pts[m]); k = m
    return out

def largo(pl): return sum(math.dist(pl[i], pl[i + 1]) for i in range(len(pl) - 1))

def punto_en(pl, d):
    for i in range(len(pl) - 1):
        l = math.dist(pl[i], pl[i + 1])
        if d <= l or i == len(pl) - 2:
            u = 0 if l == 0 else min(1, d / l); return [pl[i][0] + (pl[i + 1][0] - pl[i][0]) * u, pl[i][1] + (pl[i + 1][1] - pl[i][1]) * u]
        d -= l
    return list(pl[-1])

def relaciones_plan(E, M, inv, avisos):
    """{pid: set(ids de inventario que NO son obstáculo para ese personaje)} + informe de relaciones físicas."""
    alt = {p['id']: float(p.get('altura_m') or 1.0) for p in E.get('personajes', [])}
    exentos = {}; info = []
    for r in M.get('relaciones', []) or []:
        pid, tipo, con = r['sujeto'], r['tipo'], r['con']
        if r.get('con_tipo') != 'objeto' or not con: continue
        ps = piezas_de(con, inv)
        if tipo in ('sentado_en', 'acostado_en'):
            exentos.setdefault(pid, set()).update(p['id'] for p in ps)
            info.append({"sujeto": pid, "tipo": tipo, "con": con, "piezas": len(ps), "ok": bool(ps), "metodo": "apoyo en superficie (mueble no es obstáculo para el sujeto)"})
            if not ps: avisos.append({"personaje": pid, "aviso": "RELACION_SIN_MUEBLE", "relacion": tipo, "con": con})
        elif tipo == 'debajo_de':
            h, cub = hueco_debajo(con, inv)
            acost = any(x['sujeto'] == pid and x['tipo'] == 'acostado_en' for x in M.get('relaciones', [])) or \
                any(a.get('actor') == pid and str(a.get('pose') or '').startswith(('acostado', 'tumbado')) for a in E.get('acciones_01', []))
            nec = round(alt.get(pid, 1.0) * (FACTOR_ACOSTADO if acost else 1.0), 3)
            cabe = h is not None and h >= nec
            info.append({"sujeto": pid, "tipo": tipo, "con": con, "hueco_m": h, "necesita_m": nec, "postura": "acostado" if acost else "de pie", "cabe": cabe})
            if cabe: exentos.setdefault(pid, set()).update(cub)
            else:
                avisos.append({"personaje": pid, "aviso": "RELACION_IMPOSIBLE", "relacion": "debajo_de", "con": con, "hueco_m": h, "necesita_m": nec,
                               "resultado": "queda en el borde libre del mueble (fuera del volumen)", "decision": "escenario/01: mueble con más hueco o cambiar la acción"})
    return exentos, info

def separar_marcas(M, E, inv, radios, grillas, avisos, fps):
    """separación mínima entre marcas SIMULTÁNEAS de personajes distintos (no anclados): d ≥ r_a + r_b + margen."""
    occ = []   # (pid, f0, f1, punto, lista de (segmento, clave)) — un punto por coordenada del personaje
    for pid, P in M['personajes'].items():
        if pid not in radios or P.get('acople'): continue
        for sg in P['segmentos']:
            if sg['tipo'] == 'acoplado': continue
            occ.append([pid, sg['f0'], sg['f1'], sg['p1'] if sg['tipo'] == 'caminar' else sg['p0'], sg])
    resumen = {}
    for _ in range(4):
        cambio = False
        for i in range(len(occ)):
            for j in range(i + 1, len(occ)):
                a, b = occ[i], occ[j]
                if a[0] == b[0] or a[2] < b[1] or b[2] < a[1]: continue
                if a[4]['tipo'] == 'caminar' and b[4]['tipo'] == 'caminar': continue   # entre caminantes manda RVO2
                need = radios[a[0]] + radios[b[0]] + SEP_MARGEN_M; d = math.dist(a[3], b[3])
                if d >= need - 1e-6: continue
                ux, uy = ((b[3][0] - a[3][0]) / d, (b[3][1] - a[3][1]) / d) if d > 1e-6 else (1.0, 0.0)
                falta = need - d
                # se mueve más el más chico (radio menor): reparto inverso al radio
                wa = radios[b[0]] / (radios[a[0]] + radios[b[0]]); wb = 1 - wa
                for X, s_, w in ((a, -1, wa), (b, 1, wb)):
                    old = list(X[3]); q = [old[0] + s_ * ux * falta * w, old[1] + s_ * uy * falta * w]
                    q2 = grillas[X[0]].proyectar(q)[0] or q
                    for P in (M['personajes'][X[0]]['segmentos']):
                        for kk in ('p0', 'p1'):
                            if P.get(kk) is not None and math.dist(P[kk], old) < 1e-6: P[kk] = list(q2)
                    for Y in occ:
                        if Y[0] == X[0] and math.dist(Y[3], old) < 1e-6: Y[3] = list(q2)
                k_ = (a[0], b[0]) if a[0] < b[0] else (b[0], a[0])
                if k_ not in resumen: resumen[k_] = {"personaje": k_[0], "con": k_[1], "aviso": "SEPARACION_AJUSTADA", "dist_min_m": round(d, 3), "minimo_m": round(need, 3), "ajustes": 0}
                resumen[k_]['ajustes'] += 1; resumen[k_]['dist_min_m'] = min(resumen[k_]['dist_min_m'], round(d, 3))
                cambio = True
        if not cambio: break
    avisos.extend(resumen.values())

def validar_01(M, radios, grillas, avisos):
    """cada marca del 01 en la zona transitable principal del piso (alcanzable). Devuelve lista de marcas inalcanzables."""
    malas = []
    for pid, P in M['personajes'].items():
        if pid not in grillas or P.get('acople'): continue
        g = grillas[pid]; lab, prin = componentes(g)
        for sg in P['segmentos']:
            if sg['tipo'] == 'acoplado': continue
            for kk in ('p0', 'p1'):
                p = sg.get(kk)
                if p is None: continue
                i, j = g.celda(p)
                if prin is None or lab[j][i] != prin:
                    malas.append({"personaje": pid, "marca": [round(v, 3) for v in p], "segmento": sg.get('t'), "zona": lab[j][i]})
    for m in malas: avisos.append(dict(m, aviso="MARCA_INALCANZABLE"))
    return malas

def planear(E, M, inv):
    fps = E['fps']; N = E['N']; avisos = []; rutas = {}
    deseado = {}; grillas = {}; radios = {}; vistos = set()
    exentos, rel_info = relaciones_plan(E, M, inv, avisos)
    inv_pj = {}
    for pid, P in M['personajes'].items():
        if P.get('molde_faltante'): continue
        radios[pid] = radio_de(pid, E); inv_pj[pid] = inv_sin(inv, exentos.get(pid)); grillas[pid] = Grilla(inv_pj[pid], radios[pid])
    for pid, P in M['personajes'].items():
        if P.get('molde_faltante'): continue
        rr = radios[pid]; g = grillas[pid]
        acoplado_pj = all(sg['tipo'] == 'acoplado' for sg in P['segmentos']) if P['segmentos'] else False
        if not acoplado_pj:   # [t518] marcas del 01 dentro de muebles -> borde libre más cercano + aviso
            for sg in P['segmentos']:
                if sg['tipo'] == 'acoplado': continue
                for kk in ('p0', 'p1'):
                    if sg.get(kk) is None: continue
                    q, d = g.proyectar(sg[kk])
                    if d:
                        mm = choques_huella(sg[kk], rr, inv_pj[pid])
                        clave =[REDACTED]
                        if clave not in vistos:
                            vistos.add(clave)
                            avisos.append({"personaje": pid, "aviso": "POSICION_EN_MUEBLE" if mm else "MARCA_AJUSTADA_MARGEN",
                                           "marca": [round(v, 3) for v in sg[kk]], "movida_a": [round(v, 3) for v in q], "movida_m": round(d, 3),
                                           "segmento": sg.get('t'), "muebles": sorted({m.split('__')[0] for m in mm})[:4]})
                        sg[kk] = q
                    elif q is None:
                        avisos.append({"personaje": pid, "aviso": "SIN_LUGAR_LIBRE", "marca": sg[kk]})
    separar_marcas(M, E, inv, radios, grillas, avisos, fps)
    inalcanzables = validar_01(M, radios, grillas, avisos)
    for pid, P in M['personajes'].items():
        if P.get('molde_faltante') or pid not in grillas: continue
        rr = radios[pid]; g = grillas[pid]
        pos = [None] * (N + 2); modo = ['quieto'] * (N + 2); rumbo_obj = [None] * (N + 2)
        for sg in P['segmentos']:
            f0, f1 = sg['f0'], max(sg['f0'], sg['f1'])
            if sg['tipo'] == 'caminar':
                pl = ruta_astar(g, sg['p0'], sg['p1'])
                if pl is None: avisos.append({"personaje": pid, "aviso": "SIN_RUTA_A*", "de": sg['p0'], "a": sg['p1']}); pl = [sg['p0'], sg['p1']]
                L = largo(pl); dur = max(1e-3, (f1 - f0) / fps)
                if L / dur > VEL_MAX: avisos.append({"personaje": pid, "aviso": "VELOCIDAD_ALTA", "m_s": round(L / dur, 2), "segmento": sg['t']})
                rutas.setdefault(pid, []).append({"t": sg['t'], "ruta": pl, "largo_m": round(L, 3)})
                for f in range(f0, f1 + 1):
                    u = smooth((f - f0) / max(1, f1 - f0)); pos[f] = punto_en(pl, u * L); modo[f] = 'caminar'
                rumbo_obj[f1] = sg['rot_deg']
            else:
                for f in range(f0, f1 + 1):
                    pos[f] = list(sg['p0']); modo[f] = {'girar': 'girar', 'acoplado': 'acoplado'}.get(sg['tipo'], 'quieto'); rumbo_obj[f] = sg['rot_deg']
        last = None
        for f in range(1, N + 1):
            if pos[f] is None: pos[f] = last
            last = pos[f]
        first = next((p for p in pos[1:N + 1] if p), [0, 0])
        for f in range(1, N + 1):
            if pos[f] is None: pos[f] = first
        deseado[pid] = {"pos": pos, "modo": modo, "rumbo_obj": rumbo_obj, "visible_desde": P.get('visible_desde', 1)}
    # RVO2: evitar choques entre personajes que caminan (los quietos son agentes fijos)
    rvo_ok = False
    try:
        import rvo2
        sim = rvo2.PyRVOSimulator(1.0 / fps, 1.2, 6, 1.0, 0.5, 0.2, VEL_MAX * 1.2)
        ids = [p for p in deseado if not all(m == 'acoplado' for m in deseado[p]['modo'][1:N + 1])]
        # [t518] los muebles entran a RVO2 como obstáculos estáticos (antes RVO2 empujaba a un personaje dentro de un mueble)
        exento_alguno = set().union(*exentos.values()) if exentos else set()   # [argon_v2] el apoyo de uno no es pared para él
        for ob in inv.get('obstaculos_piso', []):
            (ax, ay), (bx, by) = ob['bbox_xy']
            if bx - ax < 1e-3 or by - ay < 1e-3 or ob['id'] in exento_alguno: continue
            sim.addObstacle([(ax, ay), (bx, ay), (bx, by), (ax, by)])   # antihorario
        sim.processObstacles()
        ag = {p: sim.addAgent(tuple(deseado[p]['pos'][1]), 1.2, 6, 1.0, 0.5, radios.get(p, RADIO['default']), VEL_MAX * 1.2, (0, 0)) for p in ids}
        real = {p: [None, list(deseado[p]['pos'][1])] for p in ids}
        for f in range(1, N):
            for p in ids:
                cur = sim.getAgentPosition(ag[p]); tgt = deseado[p]['pos'][f + 1]
                v = ((tgt[0] - cur[0]) * fps, (tgt[1] - cur[1]) * fps)
                vis = f >= deseado[p]['visible_desde']
                if not vis: sim.setAgentPosition(ag[p], tuple(tgt)); v = (0, 0)
                sim.setAgentPrefVelocity(ag[p], v)
            sim.doStep()
            for p in ids:
                q = list(sim.getAgentPosition(ag[p]))
                if deseado[p]['modo'][f + 1] != 'caminar':
                    # [t518] quietos = agentes FIJOS en su marca (antes, si los empujaban > 6 cm, quedaban donde cayeran: dentro de la cama)
                    q = list(deseado[p]['pos'][f + 1]); sim.setAgentPosition(ag[p], tuple(q))
                elif p in grillas and not grillas[p].libre(q):
                    q = grillas[p].proyectar(q)[0] or list(deseado[p]['pos'][f + 1]); sim.setAgentPosition(ag[p], tuple(q))
                real[p].append(q)
        for p in ids:
            dmax = max(math.dist(real[p][f], deseado[p]['pos'][f]) for f in range(1, N + 1))
            if dmax > 0.25: avisos.append({"personaje": p, "aviso": "RVO2_DESVIO", "max_m": round(dmax, 3)})
            deseado[p]['pos'] = real[p] + [real[p][-1]]
        rvo_ok = True
    except ImportError as ex:
        avisos.append({"aviso": "RVO2_NO_DISPONIBLE", "detalle": str(ex)})
    # [t518] verificación final: ningún cuadro con la huella de un personaje dentro de un mueble
    choques = {}
    for p, D in deseado.items():
        if p not in radios: continue
        malos = [f for f in range(1, N + 1) if D['modo'][f] != 'acoplado' and D['pos'][f] is not None and choques_huella(D['pos'][f], radios[p], inv_pj[p])]
        if malos:
            choques[p] = {"cuadros": len(malos), "primero": malos[0], "ultimo": malos[-1], "muebles": choques_huella(D['pos'][malos[0]], radios[p], inv_pj[p])[:4]}
            avisos.append({"personaje": p, "aviso": "CHOQUE_MUEBLE_PLAN", **choques[p]})
    # [argon_v2] separación final cuadro a cuadro entre personajes (no anclados entre sí): d ≥ r_a + r_b
    sep = []; ids_s = [p for p in deseado if p in radios and not M['personajes'][p].get('acople')]
    for i in range(len(ids_s)):
        for j in range(i + 1, len(ids_s)):
            a, b = ids_s[i], ids_s[j]; va = deseado[a]['visible_desde']; vb = deseado[b]['visible_desde']; need = radios[a] + radios[b]
            mal = [f for f in range(max(va, vb), N + 1) if math.dist(deseado[a]['pos'][f], deseado[b]['pos'][f]) < need - TOL_MUEBLE_M]
            dmin = min((math.dist(deseado[a]['pos'][f], deseado[b]['pos'][f]) for f in range(max(va, vb), N + 1)), default=9.0)
            sep.append({"a": a, "b": b, "dist_min_m": round(dmin, 3), "minimo_m": round(need, 3), "cuadros_pisandose": len(mal), "ok": not mal})
    # rumbo: caminar -> dirección de la velocidad; quieto/girar -> rot del 01; giro limitado
    salida = {}
    for p, D in deseado.items():
        pos = D['pos']; modo = D['modo']; ro = D['rumbo_obj']; fr = []; dist = 0.0
        rumbo = ro[1] if ro[1] is not None else 270.0
        for f in range(1, N + 1):
            if modo[f] == 'caminar':
                a, b = pos[max(1, f - 1)], pos[min(N, f + 1)]
                obj = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) if math.dist(a, b) > 1e-4 else rumbo
            else:
                obj = ro[f] if ro[f] is not None else rumbo
            paso = GIRO_MAX_DEG_S / fps; d = (obj - rumbo + 180) % 360 - 180
            if modo[f] == 'girar':   # giro en el sitio: repartido parejo en todo el tramo 'girar' del 01 (no de golpe)
                g = f
                while g < N and modo[g + 1] == 'girar': g += 1
                paso = min(paso, max(abs(d) / max(1, g - f + 1), GIRO_MIN_DEG_S / fps))
            rumbo = rumbo + max(-paso, min(paso, d))
            if f > 1: dist += math.dist(pos[f], pos[f - 1])
            fr.append([round(pos[f][0], 4), round(pos[f][1], 4), round(rumbo % 360, 2), round(dist, 4), modo[f] if f >= D['visible_desde'] else 'oculto'])
        salida[p] = fr
    return {"contrato": "plan_v1", "fps": fps, "N": N, "campos": ["x", "y", "rumbo_deg", "dist_m", "modo"], "personajes": salida,
            "rutas": rutas, "avisos": avisos, "rvo2": rvo_ok, "radios_m": {k: round(v, 3) for k, v in radios.items()},
            "choques_muebles": choques, "sin_choques_muebles": not choques,
            "relaciones": M.get('relaciones', []), "relaciones_fisicas": rel_info, "exentos": {k: sorted(v) for k, v in exentos.items()},
            "separacion": sep, "sin_personajes_pisandose": all(x['ok'] for x in sep), "marcas_inalcanzables": inalcanzables,
            "anclados": {p: M['personajes'][p]['acople'] for p in M['personajes'] if M['personajes'][p].get('acople')}, "astar": "python-pathfinding AStarFinder", "resolucion_m": RES}

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--entrada'); ap.add_argument('--movimiento'); ap.add_argument('--inventario'); ap.add_argument('--salida'); ap.add_argument('--estricto', action='store_true')
    a = ap.parse_args()
    R = planear(json.load(open(a.entrada)), json.load(open(a.movimiento)), json.load(open(a.inventario)))
    json.dump(R, open(a.salida, 'w'))
    print('RESULT_PLAN', json.dumps({"personajes": len(R['personajes']), "rutas": sum(len(v) for v in R['rutas'].values()), "rvo2": R['rvo2'],
                                     "sin_choques_muebles": R['sin_choques_muebles'], "sin_personajes_pisandose": R['sin_personajes_pisandose'],
                                     "marcas_inalcanzables": len(R['marcas_inalcanzables']), "avisos": R['avisos'][:10]}, ensure_ascii=False))
    if not R['sin_choques_muebles'] and '--estricto' in sys.argv: sys.exit(12)   # [t518] STOP antes de pagar GPU
    if (not R['sin_personajes_pisandose'] or R['marcas_inalcanzables']) and '--estricto' in sys.argv: sys.exit(13)   # [argon_v2] STOP antes de GPU
