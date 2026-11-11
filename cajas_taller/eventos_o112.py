#!/usr/bin/env python3
"""PISTA INMI (2026-10-30): orden 112 (t305u) — EVENTOS («beats») MUY DETALLADOS que Argon entrega en el cubo 01 y que el 02v convierte en el
video gris 3D. Genérico: cualquier historia, canal y personaje. Base: eventos_o111 (mismo vocabulario). Aquí: el esquema para Argon y el
VALIDADOR del código (rechaza palabras desconocidas, números en campos de palabras, texto no latino, puntos fuera del set, saltos sin caminar,
cámaras que no son del molde, citas que no están en el guion). Sin borrador: si Argon no lo trae bien, se rechaza (no se inventa)."""
import json, re, unicodedata
VERBOS = ['quieto', 'caminar', 'correr', 'caer', 'arrodillarse', 'sentarse', 'levantarse', 'acostarse', 'girar', 'senalar', 'mirar',
          'hablar', 'gritar', 'acoplarse', 'levitar', 'aparecer', 'desaparecer', 'romper', 'mover', 'escalar', 'poder']
CAMBIOS = ['', 'aparecer', 'desaparecer', 'romper', 'mover', 'escalar', 'comprimir']
EFECTOS = ['', 'anillo_portal', 'rayo', 'particulas', 'prision', 'pulso']
PARTES = ['', 'muneca_izquierda', 'muneca_derecha', 'pecho', 'cabeza', 'hombro_izquierdo', 'hombro_derecho', 'mano_izquierda', 'mano_derecha']
ORIENT = ['', 'frente', 'espalda', 'perfil_izquierdo', 'perfil_derecho', 'tres_cuartos_frente', 'tres_cuartos_espalda']
CAMPOS_PALABRAS = ('accion', 'pose', 'mirada_cuerpo', 'mirada_cabeza', 'mirada_ojos', 'emocion', 'cambio', 'acoplado_parte', 'orientacion_camara')
_S = {'type': 'string'}; _N = {'type': 'number'}; _P3 = {'type': 'array', 'items': _N}
ESQUEMA_BEAT = {'type': 'object', 'required': ['t', 'dur', 'actor', 'accion', 'pose', 'espejo', 'pos', 'rot', 'ruta', 'mirada_cuerpo', 'mirada_cabeza',
                'mirada_ojos', 'emocion', 'objeto', 'cambio', 'efecto', 'acoplado_actor', 'acoplado_parte', 'camara_molde', 'orientacion_camara', 'cita'],
                'properties': {'t': _N, 'dur': _N, 'actor': _S, 'accion': _S, 'pose': _S, 'espejo': {'type': 'boolean'}, 'pos': _P3, 'rot': _N,
                               'ruta': {'type': 'array', 'items': {'type': 'object', 'required': ['pos'], 'properties': {'pos': _P3}}},
                               'mirada_cuerpo': _S, 'mirada_cabeza': _S, 'mirada_ojos': _S, 'emocion': _S, 'objeto': _S, 'cambio': _S,
                               'efecto': {'type': 'object', 'required': ['id', 'tipo', 'de', 'a'], 'properties': {'id': _S, 'tipo': _S, 'de': _S, 'a': _S}},
                               'acoplado_actor': _S, 'acoplado_parte': _S, 'camara_molde': _S, 'orientacion_camara': _S, 'cita': _S}}
ESQUEMA = {'type': 'object', 'required': ['beats', 'revision_eventos'], 'properties': {'beats': {'type': 'array', 'minItems': 1, 'items': ESQUEMA_BEAT},
           'revision_eventos': {'type': 'array', 'items': {'type': 'object', 'required': ['chequeo', 'resultado', 'detalle'], 'properties': {'chequeo': _S, 'resultado': _S, 'detalle': _S}}}}}
CHEQUEOS_EV = ('contradicciones_guion', 'continuidad_posiciones', 'poses_de_la_biblioteca', 'miradas_y_emociones', 'cambios_de_objetos', 'poderes', 'acoples', 'camaras')

def _n(s): return ''.join(c for c in unicodedata.normalize('NFKD', str(s or '').lower()) if not unicodedata.combining(c))
def _pal(s): return [w for w in re.split(r'[^a-z0-9]+', _n(s)) if w]
def latino(s):
    return sorted({ch for ch in str(s) if not (ord(ch) < 0x250 or 0x2000 <= ord(ch) <= 0x206F or 0x1E00 <= ord(ch) <= 0x1EFF)})
def _p3(v): return isinstance(v, list) and len(v) == 3 and all(isinstance(x, (int, float)) for x in v)

def validar(EV, C, ctx):
    """EV = obj['eventos'] de Argon. C = plan validado del 01 (personajes, duracion_s). ctx = {poses: {palabra_norm: id}, camaras: set,
    objetos: set, limites: [xmin,xmax,ymin,ymax], margen, guion: texto}. Devuelve (eventos_normalizados, errores, avisos)."""
    err, av = [], []
    if not isinstance(EV, dict) or not isinstance(EV.get('beats'), list) or not EV['beats']: return None, ['falta «eventos.beats» (sin eventos no hay video; no se inventan)'], av
    ids = {p['id'] for p in C['personajes']}; dur = float(C.get('duracion_s') or 0)
    efx = {(b.get('efecto') or {}).get('id') for b in EV['beats'] if isinstance(b, dict) and (b.get('efecto') or {}).get('id')}
    refs = ids | efx | set(ctx['objetos']) | {''}
    L = ctx.get('limites'); mg = float(ctx.get('margen', .5)); G = ' '.join(_pal(ctx.get('guion') or ''))
    def dentro(p): return not L or (L[0] - mg <= p[0] <= L[1] + mg and L[2] - mg <= p[1] <= L[3] + mg)
    ult = {}; out = []; acop = {}; t_prev = -1
    for i, b in enumerate(EV['beats']):
        q = f'eventos.beats[{i}]'
        if not isinstance(b, dict): err.append(f'{q}: no es un objeto'); continue
        for k, v in b.items():
            for s in ([v] if isinstance(v, str) else [x for x in (v.values() if isinstance(v, dict) else []) if isinstance(x, str)]):
                m = latino(s)
                if m: err.append(f'{q}.{k}: caracteres no latinos {m[:5]}')
        for k in CAMPOS_PALABRAS:
            if re.search(r'\d', str(b.get(k) or '')): err.append(f'{q}.{k}: tiene números (solo palabras): «{str(b.get(k))[:40]}»')
        if re.search(r'\d', str((b.get('efecto') or {}).get('tipo') or '')): err.append(f'{q}.efecto.tipo: tiene números')
        t, d = b.get('t'), b.get('dur')
        if not isinstance(t, (int, float)) or not isinstance(d, (int, float)) or t < 0 or d < 0 or t + d > dur + 1e-6: err.append(f'{q}: tiempo t={t} dur={d} fuera de la escena (0..{dur})'); continue
        if t < t_prev - 1e-6: err.append(f'{q}: beats fuera de orden de tiempo')
        t_prev = t
        a = b.get('actor') or ''
        if a and a not in ids: err.append(f'{q}: actor «{a}» no es un personaje de la escena')
        if b.get('accion') not in VERBOS: err.append(f"{q}: accion «{b.get('accion')}» no está en {VERBOS}")
        pz = b.get('pose') or ''
        if pz and _n(pz).replace(' ', '_') not in ctx['poses']: err.append(f"{q}: pose «{pz}» FALTA en la biblioteca {sorted(set(ctx['poses'].values()))} (no se inventa)")
        if not isinstance(b.get('espejo'), bool): err.append(f'{q}: espejo debe ser verdadero/falso')
        if b.get('orientacion_camara', '') not in ORIENT: err.append(f"{q}: orientacion_camara «{b.get('orientacion_camara')}» no es una de {ORIENT[1:]}")
        pos = b.get('pos') or []; ruta = [x.get('pos') for x in b.get('ruta') or [] if isinstance(x, dict)]
        if pos and not _p3(pos): err.append(f'{q}: pos debe ser [x,y,z] en metros del set')
        elif pos and not dentro(pos): err.append(f'{q}: pos {pos} fuera del piso del set')
        for j, r in enumerate(ruta):
            if not _p3(r) or not dentro(r): err.append(f'{q}: ruta[{j}] {r} no es [x,y,z] dentro del set')
        rot = b.get('rot')
        if not isinstance(rot, (int, float)) or not (-1 <= rot <= 360): err.append(f'{q}: rot {rot} (grados 0..360, o -1 = sin cambio)')
        cam = b.get('camara_molde') or ''
        if cam not in ctx['camaras']: err.append(f'{q}: camara_molde «{cam}» no es una cámara del molde')
        if b.get('cambio', '') not in CAMBIOS: err.append(f"{q}: cambio «{b.get('cambio')}» no está en {CAMBIOS[1:]}")
        if b.get('cambio') and (b.get('objeto') or '') not in refs - {''}: err.append(f"{q}: cambio «{b['cambio']}» sobre «{b.get('objeto')}» que no es objeto del molde ni efecto")
        if b.get('cambio') == 'mover' and not pos: err.append(f'{q}: mover un objeto pide «pos» destino')
        ef = b.get('efecto') or {}
        if ef.get('tipo', '') not in EFECTOS: err.append(f"{q}: efecto.tipo «{ef.get('tipo')}» no está en {EFECTOS[1:]}")
        if ef.get('tipo'):
            if not ef.get('id'): err.append(f'{q}: efecto sin id')
            for k in ('de', 'a'):
                if (ef.get(k) or '') not in refs: err.append(f"{q}: efecto.{k} «{ef.get(k)}» no es personaje, objeto del molde ni efecto")
            if not ef.get('de'): err.append(f'{q}: efecto sin origen «de»')
        if b.get('accion') == 'poder' and not ef.get('tipo'): err.append(f'{q}: accion poder sin efecto')
        if b.get('acoplado_actor'):
            if b['acoplado_actor'] not in ids or b['acoplado_actor'] == a: err.append(f"{q}: acoplado_actor «{b['acoplado_actor']}» inválido")
            if b.get('acoplado_parte') not in PARTES[1:]: err.append(f"{q}: acoplado_parte «{b.get('acoplado_parte')}» no es una de {PARTES[1:]}")
            if a: acop[a] = {'actor': b['acoplado_actor'], 'parte': b.get('acoplado_parte')}
        if b.get('accion') == 'acoplarse' and not b.get('acoplado_actor'): err.append(f'{q}: acoplarse sin acoplado_actor')
        if a and a not in acop and b.get('accion') not in ('poder',):
            for k in ('mirada_cuerpo', 'mirada_cabeza', 'mirada_ojos', 'emocion'):
                if not str(b.get(k) or '').strip(): err.append(f'{q}: {k} vacío')
        cita = str(b.get('cita') or '').strip()
        if not cita: err.append(f'{q}: falta la cita del guion')
        elif G:
            w = [x for x in _pal(cita) if len(x) > 3]
            if w and sum(1 for x in w if x in G) / len(w) < .6: err.append(f'{q}: la cita «{cita[:60]}» no está en el guion')
        if a and a not in acop:   # continuidad: nadie se teletransporta
            ini = ruta[0] if ruta else pos
            if a in ult and ini and _p3(ini) and _p3(ult[a]):
                dd = ((ini[0] - ult[a][0]) ** 2 + (ini[1] - ult[a][1]) ** 2) ** .5
                if dd > .6 and b.get('accion') not in ('caminar', 'correr', 'caer'): err.append(f'{q}: {a} salta {dd:.1f} m sin caminar (teletransporte)')
                if b.get('accion') in ('caminar', 'correr') and d > 0 and dd / d > 9: err.append(f'{q}: {a} va a {dd / d:.1f} m/s (imposible)')
            fin = (ruta[-1] if ruta else None) or pos
            if fin and _p3(fin): ult[a] = fin
            elif a not in ult: err.append(f'{q}: primer beat de {a} sin «pos» (no se inventan posiciones)')
        out.append(b)
    for p in ids - set(ult) - set(acop): err.append(f'{p}: no tiene ningún beat con posición')
    rv = EV.get('revision_eventos')
    if not isinstance(rv, list) or not rv: err.append('falta «revision_eventos» (Argon no se revisó)')
    else:
        falt = [c for c in CHEQUEOS_EV if c not in {str(x.get('chequeo')) for x in rv if isinstance(x, dict)}]
        if falt: av.append(f'revision_eventos sin {falt}')
    return {'version': 'eventos_o112', 'origen': 'argon', 'beats': out, 'acoples': acop, 'revision_eventos': rv}, err, av
