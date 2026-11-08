# AVISO PAQUETE: rutas /workspace/... son las del origen Star.
# El test standalone (tests/correr_prueba.py) las remapea a rutas DENTRO de este paquete.
# No contiene secretos.
#!/usr/bin/env python3
"""Convierte traducción Argon v3 → JSON de escena para el motor local.
Beats de locomoción desde acciones cadera→destino; resto en acciones_puntos.
Baseline técnico de_pie SOLO como resto esquelético (no pose emocional).
Diccionario local solo rellena huecos que Argon dejó en falta (opcional).
"""
from __future__ import annotations
import json, argparse, copy
from pathlib import Path

V5 = Path('/workspace/STAR_MOTOR_ESCENAS_v5_20261031')

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def resolve_punto_xyz(nombre, puntos_map, param):
    if not nombre: return None
    if nombre in puntos_map:
        v=puntos_map[nombre]
        return list(v) if isinstance(v,(list,tuple)) else v
    # object.point from param
    if '.' in nombre:
        oid, pk = nombre.split('.', 1)
        for o in param.get('objetos') or []:
            if o.get('id')!=oid: continue
            pts=o.get('puntos') or {}
            if pk in pts:
                val=pts[pk]
                if isinstance(val, dict) and 'xyz' in val: return list(val['xyz'])
                if isinstance(val, (list,tuple)): return list(val)
            # try full key
            if nombre in pts:
                val=pts[nombre]
                if isinstance(val, dict) and 'xyz' in val: return list(val['xyz'])
                if isinstance(val,(list,tuple)): return list(val)
            # derive from pos_m + offset heurística
            pos=o.get('pos_m')
            if pos and pk in ('frente_pies','superficie','agarre','boton','pantalla'):
                x,y,z=float(pos[0]),float(pos[1]),float(pos[2])
                if pk=='frente_pies': return [x, y-0.55, 0.0]
                if pk=='superficie': return [x, y, z+0.75]
                if pk in ('agarre','boton'): return [x, y-0.1, z+0.75]
                if pk=='pantalla': return [x, y, z+1.1]
    return None

def build_puntos_map(param, argon):
    m={}
    # from parametric defaults if any
    for o in param.get('objetos') or []:
        oid=o.get('id')
        pos=o.get('pos_m') or [0,0,0]
        for k,v in (o.get('puntos') or {}).items():
            key = k if '.' in str(k) else f'{oid}.{k}'
            if isinstance(v, dict) and 'xyz' in v:
                m[key]=list(v['xyz']); m[k]=list(v['xyz'])
            elif isinstance(v,(list,tuple)) and len(v)==3:
                m[key]=list(v); m[k]=list(v)
        if oid=='escritorio' and pos:
            m.setdefault('escritorio.frente_pies', [float(pos[0]), float(pos[1])-0.55, 0.0])
            m.setdefault('cerca_monitor', [float(pos[0]), float(pos[1])-0.35, 0.0])
            m.setdefault('frente_escritorio', [float(pos[0]), float(pos[1])-0.55, 0.0])
    # from v5 esc_6 if exists
    esc6=V5/'entrada/capitulo/cubos/01/esc_6_v5.json'
    if esc6.is_file():
        for k,v in (load(esc6).get('puntos') or {}).items():
            if isinstance(v,(list,tuple)) and len(v)>=3:
                m.setdefault(k, list(v)[:3])
    # from 05 puntos
    p05=Path('/workspace/PRUEBA_ESC6_20261031/05_moldes_motor_puntos/animacion/esc_6_puntos.json')
    if p05.is_file():
        for k,v in (load(p05).get('puntos') or {}).items():
            if isinstance(v,(list,tuple)) and len(v)>=3:
                m.setdefault(k, list(v)[:3])
    return m

def convertir(argon, param, lexico_local=None):
    puntos = build_puntos_map(param, argon)
    actor0 = 'ch-protagonista-c71a'
    for p in argon.get('personajes') or []:
        if str(p.get('id','')).startswith('ch-protagonista'):
            actor0=p['id']; break

    acciones_puntos=[]
    faltas_local=[]
    # root keyframes from cadera actions
    root_keys=[]  # (t, xyz, rot)
    pos0=None
    rot0=180.0
    for pj in argon.get('personajes') or []:
        if pj.get('id')!=actor0: continue
        pi=pj.get('posicion_inicial') or {}
        if 'xyz' in pi: pos0=list(pi['xyz'])
        elif 'punto' in pi:
            pos0=resolve_punto_xyz(pi['punto'], puntos, param)
        rot0=float(pi.get('rot_deg', 180))
    if not pos0:
        pos0 = puntos.get('puerta.paso') or puntos.get('escritorio.frente_pies') or [1.5, 3.0, 0.0]
        faltas_local.append({'tipo':'pos_inicial_default','detalle':'sin posicion_inicial resoluble'})

    for a in argon.get('acciones') or []:
        sujeto=a.get('sujeto') or ''
        punto=a.get('punto') or ''
        dest=a.get('destino')
        t0,t1=float(a.get('t_ini',0)), float(a.get('t_fin',0))
        # locomoción
        if punto=='cadera' and sujeto.startswith('ch-'):
            xyz=None
            if isinstance(dest, dict) and 'xyz' in dest:
                xyz=list(dest['xyz'])
            elif isinstance(dest, str):
                xyz=resolve_punto_xyz(dest, puntos, param)
                if xyz is None:
                    faltas_local.append({'tipo':'destino_cadera_sin_xyz','accion':a.get('id'),'destino':dest})
            if xyz:
                root_keys.append({'t': t1, 'xyz': xyz, 'rot': rot0, 't0': t0, 'cita': a.get('cita')})
            acciones_puntos.append({**a, 'origen':'argon'})
            continue
        acciones_puntos.append({**a, 'origen':'argon'})

    # contactos → ensure in list
    contactos=[]
    for c in argon.get('contactos') or []:
        contactos.append({
            'actor': c.get('sujeto') or actor0,
            'parte_cuerpo': c.get('punto'),
            'objeto_punto': c.get('destino'),
            't0': float(c.get('t_ini',0)),
            't1': float(c.get('t_fin',0)),
            'c': float(c.get('c1',1)),
            'cita': c.get('cita'),
            'origen':'argon',
        })

    # eventos
    eventos_esc=[]
    for e in argon.get('eventos_escenario') or []:
        ev={
            'tipo': e.get('tipo'),
            'punto': e.get('punto') or ('escenario.temblor' if e.get('tipo')=='temblor' else None),
            't0': float(e.get('t_ini', e.get('t0',0))),
            't1': float(e.get('t_fin', e.get('t1',0))),
            'c0': float(e.get('c0',0)),
            'c1': float(e.get('c1',1)),
            'amplitud_m': e.get('amplitud_m'),
            'frecuencia_hz': e.get('frecuencia_hz'),
            'cita': e.get('cita'),
            'origen':'argon',
        }
        eventos_esc.append(ev)

    # Build beats UNIVERSAL: un beat-path por cada personaje de Argon (sin IMI inventado)
    dur=float(argon.get('duracion_s') or 60)
    beats=[]
    personajes_out=[]
    for pj in argon.get('personajes') or []:
        pid = pj.get('id')
        if not pid: continue
        h = float(pj.get('altura_m') or pj.get('altura') or 1.7)
        personajes_out.append({'id': pid, 'altura_m': h, 'altura': h})
        pi = pj.get('posicion_inicial') or {}
        pos_i = None
        if 'xyz' in pi: pos_i = list(pi['xyz'])
        elif 'punto' in pi:
            pos_i = resolve_punto_xyz(pi['punto'], puntos, param)
        rot_i = float(pi.get('rot_deg', 0 if pid != actor0 else rot0))
        if not pos_i:
            # intentar primera cadera del sujeto
            for a in argon.get('acciones') or []:
                if a.get('sujeto')==pid and a.get('punto')=='cadera':
                    dest=a.get('destino')
                    if isinstance(dest, dict) and 'xyz' in dest:
                        pos_i=list(dest['xyz']); break
                    if isinstance(dest, str):
                        pos_i=resolve_punto_xyz(dest, puntos, param)
                        if pos_i: break
        if not pos_i:
            faltas_local.append({'tipo':'pos_inicial_FALTA','personaje':pid,'detalle':'sin posicion_inicial ni cadera resoluble'})
            pos_i = list(pos0) if pid==actor0 else [0.0, 0.0, 0.0]
        # locomoción de este personaje
        keys=[]
        for a in argon.get('acciones') or []:
            if a.get('sujeto')!=pid or a.get('punto')!='cadera':
                continue
            dest=a.get('destino'); xyz=None
            if isinstance(dest, dict) and 'xyz' in dest: xyz=list(dest['xyz'])
            elif isinstance(dest, str):
                xyz=resolve_punto_xyz(dest, puntos, param)
                if xyz is None:
                    faltas_local.append({'tipo':'destino_cadera_sin_xyz','accion':a.get('id'),'destino':dest,'sujeto':pid})
            if xyz:
                keys.append({'t': float(a.get('t_fin',0)), 't0': float(a.get('t_ini',0)),
                             'xyz': xyz, 'rot': rot_i, 'cita': a.get('cita')})
        keys.sort(key=lambda x: x['t'])
        cur=list(pos_i); cur[2]=0.0
        t_cursor=0.0
        if not keys:
            beats.append({
                't':0.0,'dur':dur,'actor':pid,'accion':'quieto',
                'pose':'de_pie','espejo':False,
                'pos':list(cur),'rot':rot_i,
                'ruta':[{'pos':list(cur)},{'pos':list(cur)}],
                'c0':0,'c1':1,'cita': pj.get('cita') or 'hold',
                'contacto':False,'origen':'v3_baseline_tecnico',
                'nota':'pose=de_pie solo como resto; expresión vía acciones_puntos',
            })
            continue
        # primer quieto hasta primera locomoción
        first_t0=float(keys[0].get('t0',0))
        if first_t0 > 0.05:
            beats.append({
                't':0.0,'dur':first_t0,'actor':pid,'accion':'quieto',
                'pose':'de_pie','espejo':False,'pos':list(cur),'rot':rot_i,
                'ruta':[{'pos':list(cur)},{'pos':list(cur)}],
                'c0':0,'c1':1,'cita':'hold inicial','contacto':False,'origen':'v3_hold',
            })
            t_cursor=first_t0
        for rk in keys:
            t0=float(rk.get('t0', t_cursor)); t1=float(rk['t'])
            if t0 < t_cursor - 1e-6: t0=t_cursor
            if t1 <= t0: t1=t0+0.1
            xyz=list(rk['xyz']); xyz[2]=0.0
            beats.append({
                't': t0, 'dur': t1-t0, 'actor': pid, 'accion': 'mover',
                'pose': 'de_pie', 'espejo': False,
                'pos': xyz, 'rot': float(rk.get('rot', rot_i)),
                'ruta': [{'pos': list(cur)}, {'pos': xyz}],
                'c0':0,'c1':1,'cita': rk.get('cita') or '',
                'contacto': False, 'origen': 'argon_cadera',
                'nota': 'baseline de_pie; gesto en acciones_puntos',
            })
            cur=xyz; t_cursor=t1
        if t_cursor < dur - 0.05:
            beats.append({
                't': t_cursor, 'dur': dur-t_cursor, 'actor': pid, 'accion': 'quieto',
                'pose': 'de_pie', 'espejo': False,
                'pos': list(cur), 'rot': rot_i,
                'ruta': [{'pos': list(cur)}, {'pos': list(cur)}],
                'c0':0,'c1':1,'cita': 'hold final', 'contacto': False,
                'origen': 'v3_hold',
            })

    # anim_escenario from objetos_que_cambian
    anim_esc=[]
    for o in argon.get('objetos_que_cambian') or []:
        anim_esc.append({
            'objeto': o.get('objeto'), 'hueso': o.get('hueso'),
            'param': o.get('param'), 'c0': o.get('c0',0), 'c1': o.get('c1',1),
            't0': o.get('t_ini', o.get('t0',0)), 't1': o.get('t_fin', o.get('t1',1)),
            'cita': o.get('cita'), 'origen':'argon',
        })

    # merge object-channel actions into anim_escenario
    for a in argon.get('acciones') or []:
        punto=a.get('punto') or ''
        if '.' in punto and not str(a.get('sujeto','')).startswith('ch-'):
            oid=punto.split('.')[0]
            anim_esc.append({
                'objeto': oid, 'hueso': punto, 'param': a.get('canal') or 'c',
                'c0': a.get('c0',0), 'c1': a.get('c1',1),
                't0': a.get('t_ini'), 't1': a.get('t_fin'),
                'cita': a.get('cita'), 'origen':'argon_accion_objeto',
            })

    out={
        'escena': argon.get('escena', 6),
        'version_motor': 'puntos_universal_v3_maniqui',
        'nota': 'Argon traduce a puntos+c+tiempos; motor IK genérico; de_pie solo baseline técnico; personajes = Argon (sin inventar)',
        'origen': 'argon_traducir_v3',
        'escenario_id': argon.get('escenario_id') or (argon.get('escenario') or {}).get('escenario_id'),
        'duracion_s': dur,
        'fps': int(argon.get('fps') or 8),
        'usd': 0.0,
        'personajes': personajes_out,
        'puntos': puntos,
        'eventos': {'beats': beats, 'origen': 'argon_v3'},
        'acciones_puntos': acciones_puntos,
        'anim_escenario': anim_esc,
        'eventos_escenario': eventos_esc,
        'contactos': contactos,
        'poderes': argon.get('poderes') or [],
        'pelea': argon.get('pelea') or [],
        'escenario_parametrico': str(param.get('_path') or ''),
        'piso_solo_suelo': True,
        'camaras_auto': True,
        'faltas_argon': argon.get('falta') or [],
        'faltas_convertidor': faltas_local,
        'avisos_argon': argon.get('avisos') or [],
    }
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('argon_json')
    ap.add_argument('--param', required=True)
    ap.add_argument('-o', required=True)
    args=ap.parse_args()
    argon=load(args.argon_json)
    param=load(args.param)
    param['_path']=args.param
    out=convertir(argon, param)
    Path(args.o).parent.mkdir(parents=True, exist_ok=True)
    Path(args.o).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'ok':True,'n_beats':len(out['eventos']['beats']),
                      'n_acciones_puntos':len(out['acciones_puntos']),
                      'n_contactos':len(out['contactos']),
                      'n_eventos':len(out['eventos_escenario']),
                      'n_faltas_conv':len(out['faltas_convertidor']),
                      'out':args.o}, ensure_ascii=False, indent=2))

if __name__=='__main__':
    main()
