"""m3_traductor — motor unificado v1 [10-nov-2026]. Python puro (sin Blender, sin IA).
Traduce la dirección 01 (segmentos y acciones) + el programa 2B de Argon (si existe, t923 universal) a una lista de
movimientos que el motor sabe ejecutar:
  - locomoción/giro/sentarse/reposo  -> clip de mocap (CMU / 100STYLE) que retargetea Mwni + nuestro foot-lock;
  - gestos (señalar, hablar, mirar, poder) -> pose 2B por ángulos encima del reposo (capa gesto);
  - acciones sin clip ni método -> Kimodo (texto, GPU) si está encendido; si no, reporte_rechazo (no se inventa);
  - acoplarse (un personaje en el hombro de otro) -> ancla a un hueso del portador (cita textual del 01);
  - aparecer -> visibilidad desde t0.
El enrutador de movimientos especiales (vuelo, pelea, sin forma) vive en m3_router.py.
Uso: python3 m3_traductor.py --entrada entrada_motor.json [--programa_2b programa_2b.json] --salida movimiento.json"""
import json, argparse, math, re, unicodedata
from pathlib import Path
import m3_router as ROUTER
import relaciones as RL   # [argon_v2] relaciones físicas genéricas (anclar / apoyar / debajo), sin nombres fijos

def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(s or '').lower()) if not unicodedata.combining(c))

GESTO_POR_ACCION = {'poder': 'senalar', 'senalar': 'senalar', 'apuntar': 'senalar', 'hablar': 'hablar', 'decir': 'hablar',
                    'gritar': 'hablar', 'reir': 'hablar', 'mirar': 'mirar', 'observar': 'mirar', 'saludar': 'saludar',
                    'celebrar': 'celebrar', 'bostezar': 'bostezar'}
LOCOMOCION = {'caminar': 'caminar', 'andar': 'caminar', 'correr': 'caminar', 'acercarse': 'caminar', 'girar': 'girar',
              'voltear': 'girar', 'sentarse': 'sentarse', 'quieto': 'quieto', 'acoplarse': 'acoplado', 'acoplado': 'acoplado'}
LADO = {'izquierdo': 'L', 'izquierda': 'L', 'derecho': 'R', 'derecha': 'R'}
PARTE = {'hombro': 'hombro', 'cabeza': 'cabeza', 'mano': 'mano', 'brazo': 'antebrazo', 'espalda': 'pecho'}

def frame(t, fps): return int(round(t * fps)) + 1

def resolver_punto(p, puntos):
    if isinstance(p, (list, tuple)): return [float(p[0]), float(p[1])]
    if p in puntos: return [float(puntos[p][0]), float(puntos[p][1])]
    raise KeyError(f'PUNTO_FALTANTE {p}')

def host_de(texto, ids, alias=None):
    """Acoplado: SOLO con cita textual del 01 (portador + parte + lado). Si no está, no se elige.
    [argon_v2] los nombres salen de relaciones.nombres (id/bib de la escena; antes split('-')[1] cortaba nombres compuestos)."""
    t = RL.norm(texto)
    host = None
    for i in ids:
        for stem in ((alias or {}).get(i) or [RL.norm(i)]):
            if re.search(r'\b' + re.escape(stem) + r'\b', t): host = i; break
    parte = next((v for k, v in PARTE.items() if k in t), None)
    lado = next((v for k, v in LADO.items() if k in t), None)
    return host, parte, lado

def traducir(E, programa_2b=None, kimodo_on=False):
    fps = E['fps']; N = E['N']; puntos = E['puntos']; ids = [p['id'] for p in E['personajes']]
    out = {"contrato": "movimiento_v1", "fps": fps, "N": N, "personajes": {}, "router": [], "rechazos": [], "avisos": []}
    ALIAS = RL.nombres(E); REL = RL.extraer(E); out['relaciones'] = REL
    asig_2b = {}
    if programa_2b:
        for a in programa_2b.get('asignacion', []): asig_2b[a['accion_plan']] = a
    for p in E['personajes']:
        pid = p['id']; segs = sorted(E['segmentos_01'].get(pid, []), key=lambda s: s['t'][0])
        P = {"segmentos": [], "gestos": [], "visible_desde": 1, "acople": None, "molde_faltante": p.get('faltante', False)}
        for s in segs:
            t0, t1 = s['t']; tipo01 = norm(s.get('tipo'))
            try:
                p0 = resolver_punto(s['pos'][0], puntos); p1 = resolver_punto(s['pos'][1], puntos)
            except KeyError as ex:
                out['rechazos'].append({"personaje": pid, "segmento": s, "que_fallo": str(ex), "quien_arregla": "01/4a2 (coordenadas)"}); continue
            dist = math.dist(p0, p1)
            tipo = LOCOMOCION.get(tipo01)
            if tipo == 'girar' and dist > 0.15: tipo = 'caminar'          # «girar» con desplazamiento real = caminar + giro
            if tipo == 'quieto' and dist > 0.15: tipo = 'caminar'
            seg = {"f0": frame(t0, fps), "f1": min(N, frame(t1, fps)), "t": [t0, t1], "tipo01": s.get('tipo'), "p0": p0, "p1": p1,
                   "rot_deg": float(s.get('rot') or 0.0), "porque": s.get('porque', '')}
            if tipo is None:
                dec = ROUTER.enrutar({"accion": tipo01, "texto": s.get('porque', ''), "personaje": pid, "plantilla": p.get('plantilla'), "sujeto": p.get('sujeto_kimodo')}, kimodo_on)
                out['router'].append(dec); seg.update(tipo=dec['tipo_ejecucion'], metodo=dec['metodo'])
                if dec['tipo_ejecucion'] == 'rechazo': out['rechazos'].append(dec['reporte_rechazo']); seg['tipo'] = 'quieto'
            elif tipo == 'acoplado':
                host, parte, lado = host_de(s.get('porque', ''), [i for i in ids if i != pid], ALIAS)
                if host and parte:
                    hueso = f"{parte}_{lado}" if lado and parte not in ('cabeza', 'pecho') else parte
                    P['acople'] = {"host": host, "hueso": hueso, "parte": parte, "lado": lado, "cita": s.get('porque'), "relacion": "acoplarse (01)"}
                    seg.update(tipo='acoplado', metodo=f"ancla a {host}.{hueso} (cita 01)")
                else:
                    seg.update(tipo='quieto', metodo='acople sin cita suficiente -> quieto'); out['avisos'].append({"personaje": pid, "aviso": "ACOPLE_SIN_CITA", "texto": s.get('porque')})
            else:
                clip = {'caminar': 'caminar', 'girar': 'girar', 'sentarse': 'sentarse', 'quieto': 'quieto'}[tipo]
                seg.update(tipo=tipo, metodo=f"mocap:{clip}", clip=clip)
                out['router'].append({"personaje": pid, "accion": tipo01, "tipo_movimiento": "normal", "metodo": f"mocap:{clip}"})
            P['segmentos'].append(seg)
        # [argon_v2] relación de anclaje genérica (sobre_hombro_de / sostenido_por / sobre_cabeza_de) sacada del 01 aunque el tipo
        # del segmento sea quieto/girar/caminar: si cubre casi todo el tiempo visible del sujeto, el sujeto va ANCLADO al portador
        # (parent BONE) y sale del planificador: así nunca choca con su portador ni RVO2 lo empuja.
        r_an = RL.ancla_de(REL, pid)
        if r_an and not P['acople'] and r_an['con'] in ids:
            dur = max(1e-3, E.get('duracion_s') or N / fps); cubre = (r_an['t'][1] - r_an['t'][0]) / dur
            if cubre >= 0.9:
                parte = r_an.get('parte') or 'hombro'; lado = r_an.get('lado')
                P['acople'] = {"host": r_an['con'], "hueso": f"{parte}_{lado}" if lado and parte not in ('cabeza', 'pecho') else parte,
                               "parte": parte, "lado": lado, "cita": r_an.get('cita'), "relacion": r_an['tipo'], "fuente": r_an['fuente'], "cubre": round(cubre, 3)}
            else:
                out['avisos'].append({"personaje": pid, "aviso": "RELACION_PARCIAL_SIN_ANCLA", "relacion": r_an, "cubre": round(cubre, 3),
                                      "detalle": "anclaje solo en parte de la escena: el motor aún no suelta/engancha a mitad de escena"})
        # acople: SOLO si el 01 marca un segmento «acoplarse» (cita explícita) o una relación de anclaje; todo el plano va anclado
        if P['acople']:
            for sg in P['segmentos']: sg['tipo'] = 'acoplado'; sg['metodo'] = f"ancla {P['acople']['host']}.{P['acople']['hueso']}"
        out['personajes'][pid] = P
    # acciones 01 -> gestos / visibilidad
    for a in E['acciones_01']:
        pid = a.get('actor'); acc = norm(a.get('accion'))
        t0, t1 = a['t']; f0, f1 = frame(t0, fps), min(N, frame(t1, fps))
        if not pid:
            out['avisos'].append({"accion": a['id'], "aviso": "accion_de_objeto", "objeto": a.get('objeto'), "cambio": a.get('cambio'), "f0": f0}); continue
        if pid not in out['personajes']: continue
        P = out['personajes'][pid]
        if acc == 'aparecer':
            P['visible_desde'] = f0; continue
        if acc in ('caminar', 'girar', 'quieto'): continue          # ya están en los segmentos
        a2 = asig_2b.get(a['id'])
        gesto = GESTO_POR_ACCION.get(acc)
        pose = norm(a.get('pose'))
        if pose in ('senalando', 'apuntando'): gesto = 'senalar'
        if a2:
            P['gestos'].append({"f0": f0, "f1": f1, "gesto": a2['movimiento'], "origen": "2B Argon", "huesos": a2.get('huesos', []), "accion": a['id']})
        elif gesto:
            P['gestos'].append({"f0": f0, "f1": f1, "gesto": gesto, "origen": "traductor (catálogo genérico)", "mirada": a.get('mirada'), "objeto": a.get('objeto'), "accion": a['id']})
            out['router'].append({"personaje": pid, "accion": acc, "tipo_movimiento": "normal", "metodo": f"gesto:{gesto}"})
        else:
            dec = ROUTER.enrutar({"accion": acc, "texto": a.get('cita', ''), "personaje": pid,
                                  "sujeto": next((q.get('sujeto_kimodo') for q in E['personajes'] if q['id'] == pid), None)}, kimodo_on)
            out['router'].append(dec)
            if dec['tipo_ejecucion'] == 'kimodo':
                P['gestos'].append({"f0": f0, "f1": f1, "gesto": "kimodo", "kimodo_texto": dec['kimodo_texto'], "accion": a['id']})
            elif dec['tipo_ejecucion'] == 'rechazo':
                out['rechazos'].append(dec['reporte_rechazo'])
    return out

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--entrada', required=True); ap.add_argument('--programa_2b'); ap.add_argument('--salida', required=True)
    ap.add_argument('--kimodo', action='store_true')
    a = ap.parse_args()
    E = json.load(open(a.entrada)); P2 = json.load(open(a.programa_2b)) if a.programa_2b and Path(a.programa_2b).exists() else None
    R = traducir(E, P2, a.kimodo)
    json.dump(R, open(a.salida, 'w'), indent=1, ensure_ascii=False)
    print('RESULT_TRADUCTOR', json.dumps({"personajes": len(R['personajes']), "router": len(R['router']), "rechazos": len(R['rechazos']), "avisos": len(R['avisos'])}))
