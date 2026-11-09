"""Preflight de solo lectura del .blend que abrirá el constructor (núcleo o escenario). Nunca guarda.

  blender -b --factory-startup --disable-autoexec ARCHIVO.blend -P motor/preflight_blend.py -- PAQUETE [--salida informe.json]

ARCHIVO.blend es el tercer argumento del constructor (núcleo) o, sin núcleo, environment.path del paquete.
Revisa que existan los objetos que la entrada da por existentes, que las mallas tengan
coordenadas finitas y caras donde se van a lanzar rayos, y cuenta polígonos del escenario
(el costo de la etapa 11 crece con ellos). Código 0 sin BLOQUEO, 2 con BLOQUEO.
"""
import json
import math
import sys
from pathlib import Path

import bpy


def _finito(vals):
    return all(math.isfinite(x) for x in vals)


def _generados(d):
    """IDs que crea el propio constructor (etapas 5/7/10), no tienen por qué estar en el .blend."""
    ids = set()
    for e in d.get('entities') or []:
        if not isinstance(e, dict):
            continue
        ids.add(str(e.get('id')))
        for p in ((e.get('appearance') or {}).get('geometry') or {}).get('parts') or []:
            if isinstance(p, dict) and p.get('id'):
                ids.add(str(p['id']))
        for p in e.get('points') or []:
            if isinstance(p, dict) and p.get('id'):
                ids.add(str(e.get('id')) + '.' + str(p['id']))
    for pr in d.get('props') or []:
        if not isinstance(pr, dict):
            continue
        ids.add(str(pr.get('id')))
        for p in pr.get('geometry') or []:
            if isinstance(p, dict) and p.get('id'):
                ids.add(str(p['id']))
        for p in pr.get('points') or []:
            if isinstance(p, dict) and p.get('id'):
                ids.add(str(pr.get('id')) + '.' + str(p['id']))
        for h in pr.get('hinges') or []:
            if isinstance(h, dict) and h.get('id'):
                ids.add(str(h['id']))
        for a in pr.get('axis_ids') or []:
            ids.add(str(a))
    for g in (d.get('environment') or {}).get('geometry') or []:
        if isinstance(g, dict) and g.get('id'):
            ids.add(str(g['id']))
    return ids


def revisar(d, sb=None, roles=None):
    filas = []

    def add(sev, codigo, campo, mensaje, **k):
        fila = {'severidad': sev, 'codigo': codigo, 'campo': campo, 'mensaje': mensaje}
        fila.update(k)
        filas.append(fila)

    objs = bpy.data.objects
    generados = _generados(d)
    dg = bpy.context.evaluated_depsgraph_get()
    for ref, b in (d.get('bindings') or {}).items():
        oid = (b or {}).get('scene_object_id') if isinstance(b, dict) else None
        if oid and oid not in objs and oid not in generados:
            add('BLOQUEO', 'BINDING_SIN_OBJETO', 'bindings/' + str(ref), 'el objeto enlazado no está en el .blend ni lo crea el constructor', dato_encontrado=oid)
    for e in d.get('entities') or []:
        if isinstance(e, dict) and e.get('type') == 'CHARACTER' and e.get('legacy'):
            o = objs.get(e['id'])
            if o is None or o.type != 'ARMATURE':
                add('BLOQUEO', 'NUCLEO_SIN_ARMATURE', 'entities/' + e['id'], 'el humanoide legacy debe llegar como ARMATURE desde el núcleo')
            elif roles:
                for rol, huesos in roles.items():
                    if huesos and not any(h in o.pose.bones for h in huesos):
                        add('AVISO', 'ROL_HUESO_AUSENTE', 'entities/%s/rig/%s' % (e['id'], rol), 'la cámara no encuentra ese rol y cae a otra medida', dato_esperado=huesos)
    rules = d.get('rules') or {}
    for c in rules.get('colliders') or []:
        if c not in objs and c not in generados:
            add('BLOQUEO', 'COLLIDER_SIN_OBJETO', 'rules/colliders', 'collider ni en el .blend ni creado por el constructor', dato_encontrado=c)
    for i, c in enumerate(d.get('contacts') or []):
        t = (c or {}).get('target_point') if isinstance(c, dict) else None
        if t and t not in objs and t not in generados:
            add('BLOQUEO', 'PUNTO_SIN_OBJETO', 'contacts/%d/target_point' % i, 'punto de contacto inexistente', dato_encontrado=t)
    ids_ent = {str(e.get('id')) for e in d.get('entities') or [] if isinstance(e, dict)}
    for v in (sb or {}).get('vinetas') or []:
        obj = v.get('objetivo')
        dest = ((d.get('bindings') or {}).get(str(obj)) or {}).get('scene_object_id') if obj is not None else None
        nombre = dest or obj
        if obj is not None and str(obj) not in ids_ent and nombre not in objs and nombre not in generados:
            add('BLOQUEO', 'OBJETIVO_SIN_OBJETO', 'camera/%s/objetivo' % v.get('vineta'), 'la toma encuadra algo que no existe', dato_encontrado=obj)
    coll = set(rules.get('colliders') or [])
    entorno = {'mallas': 0, 'poligonos': 0, 'vertices': 0}
    actores = {o.name for o in objs if o.type == 'ARMATURE'}
    for o in objs:
        if not _finito([x for fila in o.matrix_world for x in fila]):
            add('BLOQUEO', 'MATRIZ_NO_FINITA', 'objeto/' + o.name, 'matrix_world con NaN o infinito')
            continue
        if o.type != 'MESH':
            continue
        ev = o.evaluated_get(dg)
        m = ev.to_mesh()
        try:
            nv, np_ = len(m.vertices), len(m.polygons)
            co = [0.0] * (3 * nv)
            m.vertices.foreach_get('co', co)
        finally:
            ev.to_mesh_clear()
        if not _finito(co):
            add('BLOQUEO', 'VERTICES_NO_FINITOS', 'objeto/' + o.name, 'la malla evaluada tiene coordenadas NaN o infinitas')
        if o.name in coll and np_ == 0:
            add('BLOQUEO', 'COLLIDER_SIN_CARAS', 'objeto/' + o.name, 'collider sin polígonos: la revisión física no puede probar interior ni rayos')
        padre = o.parent
        while padre is not None and padre.name not in actores:
            padre = padre.parent
        if not o.hide_render and padre is None:
            entorno['mallas'] += 1
            entorno['poligonos'] += np_
            entorno['vertices'] += nv
            if np_ == 0 and nv:
                add('AVISO', 'MALLA_SIN_CARAS', 'objeto/' + o.name, 'malla visible sin caras: no tapa ni choca con la cámara')
    return filas, entorno


def main():
    a = sys.argv[sys.argv.index('--') + 1:]
    pk = Path(a[0]).resolve()
    salida = Path(a[a.index('--salida') + 1]) if '--salida' in a else None
    d = json.loads((pk / 'entrada_escena.json').read_text(encoding='utf-8'))
    cam = d.get('camera') or {}
    sb = json.loads((pk / cam['source']).read_text(encoding='utf-8')) if cam.get('source') else None
    cfg_rel = (cam.get('resolver_inputs') or {}).get('config')
    roles = json.loads((pk / cfg_rel).read_text(encoding='utf-8')).get('roles_hueso') if cfg_rel else None
    filas, entorno = revisar(d, sb, roles)
    bloqueos = [f for f in filas if f['severidad'] == 'BLOQUEO']
    fps = (d.get('clock') or {}).get('fps') or 0
    cuadros = [round((v['t_abs'][1] - v['t_abs'][0]) * fps) for v in (sb or {}).get('vinetas') or [] if isinstance(v.get('t_abs'), list)]
    r = {'estado': 'BLOQUEADO' if bloqueos else 'SIN_BLOQUEOS', 'blend': bpy.data.filepath, 'blender': bpy.app.version_string,
         'bloqueos': len(bloqueos), 'avisos': len(filas) - len(bloqueos), 'entorno_visible': entorno,
         'cuadros_por_toma': cuadros, 'guardado': False, 'filas': filas}
    texto = json.dumps(r, ensure_ascii=False, indent=1)
    if salida is not None:
        if salida.exists():
            raise SystemExit('la salida ya existe; no se sobrescribe')
        salida.write_text(texto + '\n', encoding='utf-8')
    print('PREFLIGHT_BLEND ' + json.dumps({k: r[k] for k in ('estado', 'bloqueos', 'avisos', 'entorno_visible')}), flush=True)
    sys.stdout.flush()
    sys.exit(2 if bloqueos else 0)


if __name__ == '__main__':
    main()
