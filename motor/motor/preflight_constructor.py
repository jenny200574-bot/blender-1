#!/usr/bin/env python3
"""Preflight de solo lectura de la entrada que recibe constructor_final.py.

  python3 motor/preflight_constructor.py PAQUETE_NORMALIZADO [--nucleo NUCLEO/escena.blend] [--salida informe.json]

No escribe en el paquete, no completa campos, no aprueba nada. Clasifica cada hallazgo:
  BLOQUEO  el constructor fallaría o construiría con un contrato roto; hay que corregir al productor.
  AVISO    no rompe la construcción pero cambia lo que la revisión puede afirmar.
  DERIVADO el campo llega vacío a propósito y lo calcula una etapa posterior (se dice cuál).
Código 0 sin BLOQUEO; 2 con BLOQUEO; 3 si el paquete no se pudo leer.
Las comprobaciones de geometría del .blend van aparte (preflight_blend.py, dentro de Blender).
"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parent
sys.path.insert(0, str(AQUI))
from seguridad import cuadro, leer, numero, ruta, sha  # noqa: E402

RULES_CONSTRUCTOR = ('bone_length_error_m', 'root_speed_max_m_s', 'root_accel_max_m_s2')
CLAVES_RESOLVER_4G = ('config', 'ajustes', 'commands', 'sb_scene', 'elevations', 'shot_types')
ALTURA_EXPLICITA = ('ELEVATED', 'AERIAL', 'DRONEVIEW')


class Informe:
    def __init__(self):
        self.filas = []

    def _add(self, severidad, codigo, campo, productor, mensaje, **extra):
        fila = {'severidad': severidad, 'codigo': codigo, 'campo': campo, 'productor': productor, 'mensaje': mensaje}
        fila.update(extra)
        self.filas.append(fila)

    def bloqueo(self, *a, **k):
        self._add('BLOQUEO', *a, **k)

    def aviso(self, *a, **k):
        self._add('AVISO', *a, **k)

    def derivado(self, *a, **k):
        self._add('DERIVADO', *a, **k)

    def de(self, severidad):
        return [f for f in self.filas if f['severidad'] == severidad]


def claves_config_camara(motor_root):
    """Claves CFG['x'] que lee la versión de camara_v2_blender.py que se va a ejecutar."""
    texto = (Path(motor_root) / 'motor' / 'camara_v2_blender.py').read_text(encoding='utf-8')
    return sorted(set(re.findall(r"CFG\[['\"]([A-Za-z0-9_]+)['\"]\]", texto)))


def _lista(x):
    return x if isinstance(x, list) else None


def _revisar_basico(d, inf):
    clock = d.get('clock') if isinstance(d.get('clock'), dict) else {}
    fps, dur = clock.get('fps'), clock.get('duration_s')
    if not (numero(fps) and fps > 0):
        inf.bloqueo('CLOCK', 'clock/fps', '01', 'fps ausente o inválido; el constructor lo lee sin defecto')
    if not (numero(dur) and dur > 0):
        inf.bloqueo('CLOCK', 'clock/duration_s', '01', 'duración ausente o inválida; el constructor la lee sin defecto')
    env = d.get('environment')
    if not isinstance(env, dict):
        inf.bloqueo('FALTA_CAMPO', 'environment', '4a2', 'environment ausente')
        env = {}
    if env.get('mode') not in ('blend', 'geometry'):
        inf.bloqueo('ESCENARIO', 'environment/mode', '4a2', 'mode debe ser blend o geometry', dato_encontrado=env.get('mode'))
    if env.get('mode') == 'blend' and not isinstance(env.get('path'), str):
        inf.bloqueo('ESCENARIO', 'environment/path', '4a2', 'escenario blend sin ruta')
    if env.get('mode') == 'geometry' and _lista(env.get('geometry')) is None:
        inf.bloqueo('ESCENARIO', 'environment/geometry', '4a2', 'escenario geometry sin lista de piezas')
    if _lista(env.get('events')) is None:
        inf.bloqueo('FALTA_CAMPO', 'environment/events', 'motor/puente 4a-4a4', 'eventos de escenario: el constructor los suma sin defecto')
    light = d.get('lighting') if isinstance(d.get('lighting'), dict) else None
    if light is None:
        inf.bloqueo('FALTA_CAMPO', 'lighting', '4a2/4a4', 'lighting ausente')
    else:
        for k in ('events', 'exposure', 'view_transform'):
            if k not in light:
                inf.bloqueo('FALTA_CAMPO', 'lighting/' + k, '4a2/preset', 'el constructor lo lee sin defecto')
    if _lista(d.get('contacts')) is None:
        inf.bloqueo('FALTA_CAMPO', 'contacts', 'puentes_fisicos (01/2B/Star)', 'contacts debe ser lista; el constructor la recorre sin defecto')
    rules = d.get('rules') if isinstance(d.get('rules'), dict) else {}
    try:
        from puentes_fisicos import RULES
    except Exception:
        RULES = set()
    for k in sorted(set(RULES_CONSTRUCTOR) | set(RULES)):
        if k not in rules:
            inf.bloqueo('REGLA_AUSENTE', 'rules/' + k, 'reglas_binding/puentes_fisicos', 'regla que leen constructor_final o fisica_final sin defecto')
    motion = d.get('motion') if isinstance(d.get('motion'), dict) else {}
    if motion.get('requests') and _lista(motion.get('candidates')) is None:
        inf.bloqueo('FALTA_CAMPO', 'motion/candidates', 'indice_semantico', 'hay solicitudes de movimiento pero no candidatos')
    for i, job in enumerate(motion.get('retarget_jobs') or []):
        for k in ('bvh', 'entity', 'mapping', 'unit_scale', 'axis_quaternion', 'root_source', 'root_target'):
            if k not in job:
                inf.bloqueo('FALTA_CAMPO', 'motion/retarget_jobs/%d/%s' % (i, k), 'pulida/retarget', 'el constructor lo lee sin defecto')
    ents = _lista(d.get('entities')) or []
    if not ents:
        inf.bloqueo('FALTA_CAMPO', 'entities', 'ADN/01', 'sin entidades')
    for e in ents:
        if not isinstance(e, dict) or not isinstance(e.get('id'), str):
            inf.bloqueo('ENTIDAD', 'entities', 'ADN', 'entidad sin id')
            continue
        if e.get('type') == 'CHARACTER':
            parts = ((e.get('appearance') or {}).get('geometry') or {}).get('parts')
            if _lista(parts) is None:
                inf.bloqueo('FALTA_CAMPO', 'entities/%s/appearance/geometry/parts' % e['id'], 'traductor_adn', 'el constructor recorre parts sin defecto')
            if not e.get('legacy') and e.get('anatomy') not in ('avian', 'declarative'):
                inf.bloqueo('ANATOMIA', 'entities/%s/anatomy' % e['id'], 'ADN/esqueleto',
                            'sin legacy el constructor solo construye avian o declarative; un humanoide debe venir del núcleo', dato_encontrado=e.get('anatomy'))
    return fps, dur


def _revisar_assets(d, pk, inf):
    vistos = set()
    for i, a in enumerate(_lista(d.get('assets')) or []):
        campo = 'assets/%d' % i
        if not isinstance(a, dict):
            inf.bloqueo('ASSET', campo, 'empaquetador', 'asset no es objeto')
            continue
        p = a.get('path')
        if p in vistos:
            inf.bloqueo('ASSET', campo, 'empaquetador', 'ruta repetida', dato_encontrado=p)
        vistos.add(p)
        try:
            f = ruta(pk, p)
        except (ValueError, TypeError):
            inf.bloqueo('RUTA_INVALIDA', campo, 'empaquetador', 'ruta absoluta o fuera del paquete', dato_encontrado=p)
            continue
        if not f.is_file():
            inf.bloqueo('ASSET_AUSENTE', campo, 'empaquetador', 'archivo ausente', dato_encontrado=p)
        elif sha(f) != a.get('sha256') or f.stat().st_size != a.get('bytes'):
            inf.bloqueo('HASH_DISTINTO', campo, 'empaquetador', 'hash o bytes distintos del manifiesto', dato_encontrado=p)
    return vistos


def _revisar_recibos(d, pk, nucleo, inf, motor_root):
    from compatibilidad_artefacto import exigir_nucleo, exigir_paquete
    for m in exigir_paquete(motor_root, pk):
        inf.bloqueo('RECIBO_PAQUETE', 'compatibilidad_paquete.json', 'orquestador (preflight solo_validar)', m.get('codigo'), detalle=m)
    if nucleo is not None:
        for m in exigir_nucleo(motor_root, Path(nucleo), d.get('legacy')):
            inf.bloqueo('RECIBO_NUCLEO', 'compatibilidad_nucleo.json', 'nucleo_bueno_cpu', m.get('codigo'), detalle=m)


def _plano_y_lente(v, vin, cm, cfg, tabla):
    di = vin.get('director_imagen') or {}
    k0 = (v.get('keyframes') or [{}])[0]
    plano = k0.get('plano') or di.get('plano')
    lente = k0.get('lente_mm') or di.get('lente_mm')
    for c, args in cm.get('encuadre') or []:
        if c == 'LENS' and numero((args or {}).get('mm')):
            lente = args['mm']
        elif c in (cfg.get('lente_por_clase_mm') or {}) and not lente:
            lente = cfg['lente_por_clase_mm'][c]
    planos = [k.get('plano') for k in (v.get('keyframes') or []) if k.get('plano')] or ([plano] if plano else [])
    return planos, lente


def _revisar_camara(d, pk, fps, dur, inf, motor_root):
    cam = d.get('camera') if isinstance(d.get('camera'), dict) else None
    if cam is None or _lista(cam.get('shots')) is None or not cam['shots']:
        inf.bloqueo('CAMARA', 'camera/shots', 'SB', 'sin tomas')
        return
    try:
        from medir_objetivo_camara import sensor_ancho_mm
        sensor_ancho_mm(cam)
    except ValueError as exc:
        inf.bloqueo('SENSOR', 'camera/sensor_width_mm', 'SB/config cámara', str(exc))
    if not cam.get('source'):
        if not all('trajectory' in s for s in cam['shots']):
            inf.bloqueo('CAMARA', 'camera/shots/trajectory', 'SB', 'sin SB fuente ni trayectorias; no hay cámara que construir')
        return
    if cam.get('resolver') != 'SB_4G':
        inf.bloqueo('CAMARA_RESOLVER', 'camera/resolver', 'puente_sb4g.preparar',
                    'hay SB fuente pero el paquete no quedó en SB_4G; el constructor usaría la cámara técnica', dato_encontrado=cam.get('resolver'))
    render = d.get('render') if isinstance(d.get('render'), dict) else {}
    res = render.get('resolution')
    if not (isinstance(res, list) and len(res) == 2 and all(isinstance(x, int) and x > 0 for x in res)):
        inf.bloqueo('RENDER', 'render/resolution', 'preset de salida', 'la cámara SB_4G fija la resolución desde aquí', dato_encontrado=res)
    from puente_sb4g import preparar
    _estado, errores = preparar(copy.deepcopy(d), pk)
    for e in errores:
        inf.bloqueo(e.get('codigo', 'CAMARA'), e.get('campo'), e.get('modulo'), e.get('mensaje'))
    refs = cam.get('resolver_inputs') or {}
    datos = {}
    for k in CLAVES_RESOLVER_4G:
        try:
            datos[k] = leer(ruta(pk, refs[k]))
        except (KeyError, OSError, ValueError, TypeError):
            datos[k] = None
    try:
        sb = leer(ruta(pk, cam['source']))
    except (OSError, ValueError, TypeError):
        inf.bloqueo('SB_ILEGIBLE', 'camera/source', 'SB', 'storyboard ilegible')
        return
    cfg = datos.get('config') or {}
    if datos.get('config') is not None:
        faltan = [k for k in claves_config_camara(motor_root) if k not in cfg]
        if faltan:
            inf.bloqueo('CONFIG_CAMARA_INCOMPATIBLE', 'camera/resolver_inputs/config', 'SB/config 4g del paquete',
                        'el config del paquete no trae claves que lee camara_v2_blender.py instalado', dato_esperado=faltan)
    tabla = ((datos.get('ajustes') or {}).get('encuadre_fraccion_altura_visible')) or {}
    escena = {v.get('id'): v for v in ((datos.get('sb_scene') or {}).get('vinetas') or [])}
    comandos = datos.get('commands') or {}
    from auditar_sb import auditar
    for e in auditar(sb)['errors']:
        inf.bloqueo(e.get('codigo'), e.get('campo'), e.get('modulo'), e.get('mensaje'))
    ids_ent = {e.get('id') for e in d.get('entities') or [] if isinstance(e, dict)}
    bindings = d.get('bindings') or {}
    tomas = {s.get('id'): s for s in cam['shots']}
    vinetas = sb.get('vinetas') or []
    vistos = set()
    derivados = 0
    for v in vinetas:
        vid = v.get('vineta')
        campo = 'camera/' + str(vid)
        if vid in vistos:
            inf.bloqueo('SB_DUPLICADO', campo, 'SB', 'viñeta repetida')
        vistos.add(vid)
        t = v.get('t_abs')
        if not (isinstance(t, list) and len(t) == 2 and all(numero(x) for x in t) and 0 <= t[0] < t[1] <= (dur or 0) + 1e-9):
            inf.bloqueo('SB_TIEMPO', campo + '/t_abs', 'SB', 't_abs ausente o fuera de la escena', dato_encontrado=t)
        elif vid in tomas and numero(fps) and (cuadro(t[0], fps), cuadro(t[1], fps)) != (cuadro(tomas[vid].get('t0', -1), fps), cuadro(tomas[vid].get('t1', -1), fps)):
            inf.bloqueo('SB_TIEMPO', campo + '/t_abs', 'SB vs camera/shots', 'los cuadros del SB y de camera/shots no coinciden')
        if vid not in tomas:
            inf.bloqueo('SB_TOMA', campo, 'SB vs camera/shots', 'viñeta del SB sin toma en camera/shots')
        obj = v.get('objetivo')
        destino = (bindings.get(str(obj)) or {}).get('scene_object_id') if obj is not None else None
        if obj is None:
            inf.aviso('SB_OBJETIVO', campo + '/objetivo', 'SB', 'toma sin objetivo: la cámara no puede medir a quién encuadra')
        elif obj not in ids_ent and not destino:
            inf.aviso('SB_OBJETIVO', campo + '/objetivo', 'SB + 4a2', 'objetivo no es entidad ni binding; solo vale si ya existe en el .blend (ver preflight_blend.py)', dato_encontrado=obj)
        cm = comandos.get(vid) or {}
        planos, lente = _plano_y_lente(v, escena.get(vid) or {}, cm, cfg, tabla)
        for p in planos:
            if p not in tabla:
                inf.bloqueo('PLANO_SIN_FILA', campo + '/keyframes/plano', 'SB + ajustes 4g', 'el plano no está en encuadre_fraccion_altura_visible; la toma no se puede emplazar', dato_encontrado=p)
        if not planos:
            inf.bloqueo('PLANO_AUSENTE', campo + '/keyframes/plano', 'SB', 'toma sin plano')
        if not lente:
            inf.aviso('SIN_LENTE', campo + '/lente_mm', 'SB', 'sin lente el buscador no modela la toma y valida la rejilla fija de candidatos')
        for c, _args in cm.get('encuadre') or []:
            if c in ALTURA_EXPLICITA:
                inf.bloqueo('ALTURA_EXPLICITA', campo + '/' + c, 'SB o 02N', c + ' exige altura de cámara en metros que la cámara no deriva')
        if 'altura_m' in v and v.get('altura_m') is None:
            derivados += 1
        for k in v.get('keyframes') or []:
            if isinstance(k.get('distancia_m'), str) or ('distancia_m' in k and k.get('distancia_m') is None):
                derivados += 1
    for sid in tomas:
        if sid not in vistos:
            inf.bloqueo('SB_TOMA', 'camera/shots/' + str(sid), 'SB vs camera/shots', 'toma sin viñeta en el SB')
    if derivados:
        inf.derivado('CAMARA_ALTURA_DISTANCIA', 'SB vinetas altura_m / keyframes distancia_m', 'etapa 11 (camara_v2_blender.emplazar)',
                     'llegan vacíos o "por medir"; la etapa 11 no los lee: calcula distancia por plano+lente+altura medida del rig '
                     'y altura por elevación o hueso. Quedan en auditoria_4g/camara_v2.json (camara.loc, distancia_m).', cuantos=derivados)


def _programa_contactos(d, pk):
    m = d.get('motion') or {}
    cand = m.get('program') or ('programa_2b.json' if (pk / 'programa_2b.json').is_file() else None)
    if not cand:
        return None, 'sin programa 2B en el paquete'
    asset = next((a for a in d.get('assets', []) if a.get('path') == cand), None)
    try:
        if not asset or sha(ruta(pk, cand)) != asset.get('sha256'):
            return None, 'programa no cubierto por hash'
        prog = leer(ruta(pk, cand))
    except (OSError, ValueError, TypeError):
        return None, 'programa ilegible'
    if not isinstance(prog, dict):
        return None, 'programa no es objeto'
    fuente = prog.get('contacts', prog.get('contactos'))
    if prog.get('status') not in (None, 'complete') and prog.get('contacts_complete') is not True:
        fuente = None
    if fuente is None and prog.get('status') == 'complete' and prog.get('physics_validated') is True:
        fuente = prog.get('anclas')
    return fuente, cand


def _revisar_fisica(d, pk, inf):
    contacts = _lista(d.get('contacts'))
    if contacts == []:
        fuente, de_donde = _programa_contactos(d, pk)
        if fuente == []:
            inf.aviso('SIN_CONTACTOS_IK', 'contacts', '01/2B/Star', 'el programa declara cero contactos IK; la etapa 10 no pone restricciones y la 13 no mide resbale de manos/pies sobre puntos',
                      fuente=de_donde)
        else:
            inf.bloqueo('CONTACTOS_VACIOS_SIN_PROCEDENCIA', 'contacts', '01/2B/Star (puentes_fisicos)',
                        'contacts=[] en el paquete pero el programa no declara una lista completa vacía; una ausencia no es cero contactos',
                        dato_encontrado=de_donde if fuente is None else 'el programa trae %d contactos' % len(fuente))
    puntos = set()
    for grupo in (d.get('entities') or []) + (d.get('props') or []):
        if isinstance(grupo, dict):
            for p in grupo.get('points') or []:
                if isinstance(p, dict) and p.get('id'):
                    puntos.add(str(grupo.get('id')) + '.' + str(p['id']))
    rigs = {e['id']: {b.get('id') for b in ((e.get('rig') or {}).get('bones') or [])} for e in d.get('entities') or [] if isinstance(e, dict) and e.get('id')}
    for i, c in enumerate(contacts or []):
        if not isinstance(c, dict):
            inf.bloqueo('CONTACTO', 'contacts/%d' % i, '01/2B/Star', 'contacto no estructurado')
            continue
        if c.get('target_point') not in puntos:
            inf.aviso('CONTACTO_PUNTO', 'contacts/%d/target_point' % i, 'Star/ADN', 'el punto no está declarado en entities/props points; solo vale si existe en el .blend', dato_encontrado=c.get('target_point'))
        huesos = rigs.get(c.get('entity'))
        if huesos and c.get('bone') not in huesos:
            inf.bloqueo('CONTACTO_HUESO', 'contacts/%d/bone' % i, 'Star/ADN', 'el hueso no está en el rig declarado de la entidad', dato_encontrado=c.get('bone'))
    rules = d.get('rules') if isinstance(d.get('rules'), dict) else {}
    coll = set(rules.get('colliders') or [])
    for i, par in enumerate(rules.get('contact_pairs') or []):
        if not (isinstance(par, list) and len(par) == 2 and all(isinstance(x, str) for x in par)):
            inf.bloqueo('CONTACT_PAIRS', 'rules/contact_pairs/%d' % i, 'reglas/4a2', 'par mal formado')
        elif not set(par) <= coll:
            inf.aviso('CONTACT_PAIRS', 'rules/contact_pairs/%d' % i, 'reglas/4a2', 'par con nombres fuera de colliders: la revisión nunca lo usa', dato_encontrado=par)
    if rules.get('contact_pairs') and contacts == []:
        inf.aviso('CONTACTOS_DISTINTOS', 'rules/contact_pairs vs contacts', 'contrato',
                  'contact_pairs solo exime superficies que se tocan en la revisión física; no son contactos IK y no los sustituyen')
    puente = d.get('_rules_bridge') or {}
    if puente.get('locked_limits_connected') is False:
        inf.aviso('LIMITES_BLOQUEADOS_SIN_CONECTAR', '_rules_bridge/locked_limits_connected', 'biblioteca de reglas vigentes',
                  'sin límites bloqueados la revisión de la etapa 13 marca EQUILIBRIO en cada cuadro fuera de balance_margin_m (más estricta que con límites)')
    if puente.get('state') not in (None, 'READY'):
        inf.bloqueo('REGLAS_NO_LISTAS', '_rules_bridge/state', 'reglas_binding', 'el puente de reglas no quedó READY', dato_encontrado=puente.get('state'))


def revisar(paquete, nucleo=None, motor_root=ROOT):
    pk = Path(paquete).resolve()
    inf = Informe()
    try:
        d = leer(pk / 'entrada_escena.json')
        if not isinstance(d, dict):
            raise ValueError('entrada_escena.json no es objeto')
    except (OSError, ValueError, TypeError) as exc:
        return {'estado': 'ILEGIBLE', 'mensaje': str(exc), 'filas': []}
    fps, dur = _revisar_basico(d, inf)
    _revisar_assets(d, pk, inf)
    _revisar_recibos(d, pk, nucleo, inf, motor_root)
    _revisar_camara(d, pk, fps, dur, inf, motor_root)
    _revisar_fisica(d, pk, inf)
    if d.get('production_approved') is True:
        inf.bloqueo('APROBACION_EN_ENTRADA', 'production_approved', 'Ricardo', 'la entrada no puede traer aprobación de producción; la da Ricardo fuera del motor')
    bloqueos = inf.de('BLOQUEO')
    return {'estado': 'BLOQUEADO' if bloqueos else 'APTO_PARA_CONSTRUIR', 'paquete': str(pk), 'entrada_sha256': sha(pk / 'entrada_escena.json'),
            'nucleo': str(nucleo) if nucleo else None, 'bloqueos': len(bloqueos), 'avisos': len(inf.de('AVISO')), 'derivados': len(inf.de('DERIVADO')),
            'production_approved': False, 'no_es_aprobacion': 'Solo dice si el contrato de entrada del constructor está completo. No revisa geometría ni física.',
            'filas': inf.filas}


def main(argv=None):
    p = argparse.ArgumentParser(description='Preflight de solo lectura de la entrada del constructor')
    p.add_argument('paquete')
    p.add_argument('--nucleo')
    p.add_argument('--salida')
    a = p.parse_args(argv)
    r = revisar(a.paquete, a.nucleo)
    texto = json.dumps(r, ensure_ascii=False, indent=1, default=str)
    if a.salida:
        destino = Path(a.salida)
        if destino.exists():
            print(json.dumps({'error': 'la salida ya existe; no se sobrescribe', 'salida': str(destino)}))
            return 3
        destino.write_text(texto + '\n', encoding='utf-8')
    print(json.dumps({k: r.get(k) for k in ('estado', 'bloqueos', 'avisos', 'derivados')}, ensure_ascii=False))
    if not a.salida:
        print(texto)
    if r['estado'] == 'ILEGIBLE':
        return 3
    return 2 if r['estado'] == 'BLOQUEADO' else 0


if __name__ == '__main__':
    sys.exit(main())
