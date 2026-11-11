"""Tamaño de los personajes MEDIDO en el diseño de Blender de CADA escena (2026-11-02, Ricardo t306u/t308u). Genérico: cualquier canal.
US$0: solo abre .blend ya hechos, sin ventana.

Ricardo: no hay altura fija; el tamaño lo define el diseño de Blender de cada escena. Ese diseño es la corrida REAL del motor de Ako
(02N) de esa escena (motor_02n.corridas, la escena sale del tramo; las «-seco» no). En ella cada personaje es un maniquí del motor:
raíz con la propiedad «escala» = altura / altura_ref (altura_ref se lee del ayudante del motor, «s=altura/1.72»).
Tamaño = escala × altura_ref (no depende de la pose). La caja z del primer cuadro se guarda como comprobación.
Nombres: tramos/<canal>/nombres_cortos.json (id → nombre corto del maniquí), el mismo mapa del motor.
Caché de medidas por archivo: <biblioteca>/<canal>/personajes/medidas_disenos_blender.json (se rehace si el .blend cambia).
Nunca se inventa ni se pisa una altura escrita: quien llama lo usa solo si no hay otra; si no hay diseño, sigue sin altura."""
import json, os, re, subprocess, tempfile, time
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def _cfg():
    return json.loads((AQUI / 'paso01_datos' / 'alturas_blender.json').read_text(encoding='utf-8'))


def _raiz_ab():
    try:
        import motor_02n as M2; return M2.ajustes()['raiz']
    except Exception: return os.environ.get('MYIA_AB_RAIZ') or '/opt/myia-argon-blender'


def _fmt(s, canal=''): return str(s).replace('{raiz_ab}', _raiz_ab()).replace('{canal}', canal)


def _blender(cfg=None):
    for b in (cfg or {}).get('blender') or []:
        b = _fmt(b)
        if os.path.isfile(b) and os.access(b, os.X_OK): return b
    import paso01_cubos as K
    return K.blender()


def _biblio(canal):
    import personajes as PJ
    return Path(PJ.raiz(canal))


def altura_ref(cfg=None):
    cfg = cfg or _cfg()
    try:
        m = re.search(cfg['regex_altura_ref'], Path(_fmt(cfg['ayudante_maniqui'])).read_text(encoding='utf-8'))
        return float(m.group(1)) if m else None
    except Exception: return None


def disenos_escena(canal, capitulo, escena):
    """.blend de las corridas REALES del motor para esa escena, la más nueva primero."""
    import motor_02n as M2
    cfg2 = dict(M2.ajustes()); cfg2['modos'] = ['real']
    out = []
    for c in M2.corridas(canal, capitulo, escena, cfg2):
        out += sorted(Path(c['carpeta']).glob('*.blend'), key=lambda f: -f.stat().st_mtime)
    return out


def nombres(canal):
    """nombre corto del maniquí → [ids del personaje]."""
    try: m = json.loads((Path(_raiz_ab()) / 'tramos' / canal / 'nombres_cortos.json').read_text(encoding='utf-8'))
    except Exception: return {}
    inv = {}
    for pid, corto in m.items(): inv.setdefault(str(corto), []).append(pid)
    return inv


def _medir_blend(f, cfg):
    b = _blender(cfg)
    if not b: return None, 'no hay Blender en este equipo'
    with tempfile.TemporaryDirectory(prefix='alturas_') as td:
        fs = Path(td) / 's.json'
        try: subprocess.run(['nice', '-n', '15', b, '-b', str(f), '--factory-startup', '--python', str(AQUI / 'blender_alturas.py'), '--', str(fs), cfg['propiedad_escala']],
                            capture_output=True, text=True, timeout=180)
        except subprocess.TimeoutExpired: return None, 'Blender tardó demasiado'
        if not fs.is_file(): return None, 'Blender no devolvió datos'
        return json.loads(fs.read_text(encoding='utf-8')), None


def _medidas(canal, f, cfg, ref):
    """Maniquíes del .blend (usa la caché del canal si el archivo no cambió)."""
    try: cf = _biblio(canal) / cfg['cache']
    except Exception: cf = None
    C = {}
    if cf and cf.is_file():
        try: C = json.loads(cf.read_text(encoding='utf-8'))
        except Exception: C = {}
    st = f.stat(); firma = f'{st.st_size}:{int(st.st_mtime)}'; x = C.get(str(f))
    if x and x.get('firma') == firma and x.get('ref') == ref: return x.get('maniquies') or []
    d, err = _medir_blend(f, cfg)
    C[str(f)] = {'firma': firma, 'ref': ref, 'error': err, 'maniquies': (d or {}).get('maniquies') or [], 'medido': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
    if cf:
        try:
            cf.parent.mkdir(parents=True, exist_ok=True); tmp = cf.with_suffix('.tmp')
            tmp.write_text(json.dumps(C, ensure_ascii=False, indent=1), encoding='utf-8'); os.replace(tmp, cf)
        except Exception: pass
    return C[str(f)]['maniquies']


def medir_escena(canal, capitulo, escena, cfg=None):
    """{pid: {altura_m, objeto, escala, altura_ref_m, caja_z_cuadro1, fuente}} del diseño más nuevo de la escena."""
    cfg = cfg or _cfg(); ref = altura_ref(cfg)
    if ref is None: return {}
    inv = nombres(canal); out = {}
    for f in disenos_escena(canal, capitulo, escena):          # el más nuevo primero: el primero que trae al personaje manda
        for mq in _medidas(canal, f, cfg, ref):
            for pid in inv.get(mq.get('objeto'), []):
                if pid in out: continue
                out[pid] = {'altura_m': round(float(mq['escala']) * ref, 3), 'objeto': mq['objeto'], 'escala': mq['escala'], 'altura_ref_m': ref,
                            'caja_z_cuadro1': [mq.get('z_min'), mq.get('z_max')], 'fuente': f'diseño Blender de la escena {escena}: {f}'}
    return out


_MEM = {}


def altura(canal, capitulo, escena, pid):
    """(tamaño_m, fuente) del personaje en el diseño de Blender de esa escena, o (None, None). Una medición por proceso y escena."""
    k = (canal, str(capitulo), str(escena))
    if k not in _MEM:
        try: _MEM[k] = medir_escena(canal, capitulo, escena)
        except Exception: _MEM[k] = {}
    x = _MEM[k].get(pid)
    return (x['altura_m'], x['fuente'] + f" (maniquí {x['objeto']}, escala {round(float(x['escala']), 4)} × {x['altura_ref_m']} m)") if x else (None, None)


if __name__ == '__main__':
    import sys
    print(json.dumps(medir_escena(sys.argv[1], sys.argv[2], sys.argv[3]), ensure_ascii=False, indent=1))
