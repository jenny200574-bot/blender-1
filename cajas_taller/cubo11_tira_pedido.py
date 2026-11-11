"""PISTA INMI (2026-10-29): orden 87 — pedido de PINTURA del CUBO 11 «híbrido tira» (Nano Banana «calca» sobre la hoja de
moldes del cubo 02). Copia de taller de pruebas_o84/hibrido_pedido.py (orden 84): construir() y vinetas_plantilla() son las MISMAS
(con los datos del canal real de la orden 84 reproducen byte a byte el pedido T06 aprobado). Los textos del método están en paso01_datos/pintura_base.json;
los del canal llegan en la config que arma cubo11_tira.py. Solo arma texto + lista ordenada de imágenes: NO llama a nadie.
La cotización está en cubo11_tira.py (fórmula del cubo 11, paso00_pintar.precio_llamada, con el modelo del canal)."""
import os, json
AQUI = os.path.dirname(os.path.abspath(__file__))
BASE = json.load(open(os.path.join(AQUI, 'paso01_datos', 'pintura_base.json'), encoding='utf-8'))
POSE_EN = json.load(open(os.path.join(AQUI, 'paso01_datos', 'poses_maniqui.json'), encoding='utf-8')).get('descripcion_en', {})


def _lado(i, cols): return ('left' if i % 2 == 0 else 'right') if cols == 2 else f'column {i % cols + 1}'


def leyenda_auto(cfg):
    """Leyenda del molde a partir de la paleta de la config (sin colores fijos)."""
    P = cfg['pintura']; cols, filas = P['cuadricula']; fig, ext = [], []
    for p in cfg['personajes']:
        fig.append(f"the {p['color_nombre']} blocky figure marks ONLY {p['nombre_prompt']}'s exact position, pose, orientation and size")
        por_color = {}
        for a in p.get('accesorios', []): por_color.setdefault(a['color_nombre'], []).append(a.get('nombre_prompt', a['nombre']))
        for cn, xs in por_color.items(): ext.append(f"{cn} shape on {p['nombre_corto']} = {p['nombre_corto']}'s {' and '.join(xs)}")
    if cfg.get('colores_molde', {}).get('cielo'): ext.append('flat light-blue area = open SKY (no sky where it is absent)')
    return BASE['leyenda'].format(cols=cols, filas=filas, figuras='; '.join(fig), extras=(', ' + ', '.join(ext)) if ext else '')


def vinetas_plantilla(cfg, med, cam, cielo):
    """Texto de cada viñeta SIN Argon (gratis): sale de las medidas del molde y de la acción del plan. En producción lo
    reescribe Argon (cubo 01/03), como en el método original; aquí es la versión de código para probar sin pagar."""
    PJ = {p['id']: p for p in cfg['personajes']}; est = cfg['pintura']['estilo']; out = []
    for t in cfg['plan']['tomas']:
        ca = cam[t['id']]; d = ca.get('dist') or 0; el = ca.get('elev_deg') or 0
        vista = ('wide establishing shot' if d > 8 else 'medium shot' if d > 3 else 'close-up') + (', eye-level camera' if el < 10 else ', high camera looking down')
        for c in t['cuadros']:
            k = f"{t['id']}_{c['n']}"; m = med[k]; quien = []
            for i, v in m['vis'].items():
                b = v['bbox_uv']; cx = (b[0] + b[2]) / 2; h = round((b[3] - b[1]) * 100)
                pos = 'left' if cx < .3 else 'center-left' if cx < .45 else 'center' if cx < .55 else 'center-right' if cx < .7 else 'right'
                p = PJ[i]; fr = 'facing the camera' if v.get('mira_a_camara') else 'back to the camera'
                pose = POSE_EN.get(m['pose'].get(i, ''), m['pose'].get(i, '').replace('_', ' '))
                ob = ', '.join(p.get('obligatorias', []))   # PISTA INMI (2026-10-29): orden 87 — sin «, )» cuando no hay obligatorias
                quien.append(f"{p['nombre_corto']} ({h}% height, {pos}{', ' + ob if ob else ''}) {pose}, {fr}")
            sk = round(cielo.get(k, 0) * 100)
            cielo_t = f"open sky {sk}% of the frame at the top" if sk else 'no sky, no horizon'
            # PISTA INMI (2026-10-29): orden 87 — el estilo va UNA vez (sección STYLE); en la viñeta solo si es corto (≤ estilo_en_vineta_max letras)
            pre = f"{est.rstrip('. ')}. " if len(est) <= int(cfg['pintura'].get('estilo_en_vineta_max', 200)) else ''
            out.append({'id': k, 'quien': list(m['vis']), 'prompt': f"{pre}{vista[0].upper() + vista[1:]}; {cielo_t}; the {cfg['escenario']['set_corto']} set exactly as in the mold. " + '; '.join(quien) + f". Action: {str(c['accion']).rstrip('. ')}."})
    return out


def construir(cfg, vinetas, hoja_molde, previa=None, encabezado=None, exclude_extra='', historia='', ancla=None):
    P = cfg['pintura']; E = cfg['escenario']; cols, filas = P['cuadricula']; n = len(vinetas)
    quien = [p for p in cfg['personajes'] if any(p['id'] in v['quien'] for v in vinetas)]
    refs, rango = [], {}
    for p in quien:
        a = len(refs) + 1; refs += [(r['desc'], r['ruta']) for r in p.get('refs', [])]; rango[p['id']] = (a, len(refs))
    refs += [(o['desc'], o['ruta']) for o in P.get('objetos', [])]
    iM = len(refs) + 1
    refs.append((P.get('leyenda_molde') or leyenda_auto(cfg), hoja_molde))
    if previa: refs.append((BASE['previa'].format(set_corto=E['set_corto']), previa))
    if ancla and ancla.get('ruta'): refs.append((ancla.get('desc') or 'scene anchor', ancla['ruta']))  # antes del estilo (paso 2)
    if P.get('estilo_ref'): refs.append((P['estilo_ref']['desc'], P['estilo_ref']['ruta']))  # ÚLTIMA (paso 1 / receta 183)
    HEAD = encabezado or BASE['encabezado']
    lab = ' '.join(f'Image {i + 1}: {d}' for i, (d, _) in enumerate(refs))
    ident = []
    for p in quien:
        a, b = rango[p['id']]
        if b >= a: ident.append(f"{p['nombre_prompt']} = {'Images %d-%d' % (a, b) if b > a else 'Image %d' % a}: {p['identidad']}")
        else: ident.append(f"{p['nombre_prompt']} (no approved reference yet): {p['identidad']}")
    alturas = ', '.join(f"{p['nombre_corto']} {round(p['alto_m'] * 100)} cm" for p in quien)
    PAN = [f"Panel {i + 1} (row {i // cols + 1} {_lado(i, cols)}): " + v['prompt'].replace(HEAD, '').strip() for i, v in enumerate(vinetas)]
    exb = P.get('exclude_base') or ', '.join([BASE['exclude_metodo']] + [x.replace('no ', '', 1) for p in quien for x in p.get('prohibidas', [])])
    prompt = '\n'.join([HEAD, '', BASE['estilo'].format(**P), '',
        BASE['hoja'].format(escena_corta=E['escena_corta'], tomas=', '.join(v['id'] for v in vinetas)), '',
        '1. PAGE LAYOUT', BASE['maqueta'].format(n=n, filas=filas, cols=cols, iM=iM, aspecto_panel=P['aspecto_panel']), '',
        BASE['consistencia'].format(n=n, y_previa=' and with the previous strip' if previa else '', momento=P['momento']), '',
        '3. REFERENCE IMAGES', lab, '',
        '4. CHARACTERS (identity locked to the references)', *ident, BASE['solo'].format(claves=', '.join(p['clave'] for p in quien), alturas=alturas, iM=iM), '',
        '5. SET AND STORY STATE', BASE['set'].format(descripcion=E['descripcion_prompt'], iM=iM), '',
        '6. STORY OF THE SCENE (context only)', historia, '',
        '7. PANELS', *PAN, '',
        '8. EXCLUDE (word list)', 'Avoid: ' + (exclude_extra + ', ' if exclude_extra else '') + exb])
    if P['estilo'] not in prompt: raise ValueError('el estilo del canal no quedó en el pedido')
    if len(refs) > int(P.get('max_refs', 14)): raise ValueError(f"{len(refs)} imágenes de referencia > {P.get('max_refs', 14)} (máximo del modelo)")
    texto = prompt + '\n\nREFS:\n' + '\n'.join(f'{d} | {x}' for d, x in refs)
    return {'prompt': prompt, 'refs': refs, 'texto_archivo': texto, 'imagen_molde': iM}
