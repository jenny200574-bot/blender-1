"""COM ponderado, apoyos, penetración y límites: usa geometría evaluada y perfiles declarados."""
import math
from continuidad_tomas import anotar_error_toma, cuadros_inicio_toma, exclusion_cinematica_contrato
from superficie_caminable import es_superficie_caminable, z_superior_estimada

# Criterio de penetración (etapa 13):
# - interior_cerrado: sólidos donde la parity por rayos es resoluble (un rayo + respaldo 6 ejes).
# - distancia_overlap: láminas/cortinas, mallas abiertas, degeneradas o parity ambigua;
#   se mide con find_nearest + overlap BVH, sin abortar el constructor.

def _coord(p):
    if hasattr(p, 'x'):
        return float(p.x), float(p.y), float(p.z)
    return float(p[0]), float(p[1]), float(p[2])


def extents_vertices(verts):
    if not verts:
        return 0.0, 0.0, 0.0
    xs = [_coord(v)[0] for v in verts]
    ys = [_coord(v)[1] for v in verts]
    zs = [_coord(v)[2] for v in verts]
    return max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)


def _ray_unit():
  try:
    from mathutils import Vector
    return Vector((0.87431, 0.37291, 0.31415)).normalized()
  except ImportError:
    n = math.sqrt(0.87431 ** 2 + 0.37291 ** 2 + 0.31415 ** 2)
    return (0.87431 / n, 0.37291 / n, 0.31415 / n)


def _shift(p, d, s):
  if hasattr(p, 'copy'):
    try:
      return p + d * s
    except TypeError:
      pass
  px, py, pz = _coord(p)
  dx, dy, dz = _coord(d)
  return (px + dx * s, py + dy * s, pz + dz * s)


def ray_parity_interiores(tree, p, max_rebotes=10000):
  """Parity por un rayo; devuelve (resoluble, dentro|None, motivo). Nunca lanza excepción."""
  ray = _ray_unit()
  origin = p.copy() if hasattr(p, 'copy') else p
  count = 0
  prev = None
  for _ in range(max_rebotes):
    hit = tree.ray_cast(origin, ray)
    if hit[0] is None:
      return True, bool(count % 2), None
    hp = hit[0]
    if prev is not None:
      dpx, dpy, dpz = _coord(hp)
      qx, qy, qz = _coord(prev)
      if (dpx - qx) ** 2 + (dpy - qy) ** 2 + (dpz - qz) ** 2 < 1e-18:
        return False, None, 'rayo estancado en el mismo impacto (malla abierta, lámina o autointersección)'
    prev = hp
    count += 1
    origin = _shift(hp, ray, 1e-4)
  return False, None, f'más de {max_rebotes} impactos en un rayo (malla abierta, lámina o autointersección)'


def interior_multiray(tree, p):
  """Respaldo: 6 ejes; coherente con camara_v2_blender.dentro_de_malla (≥4 impactos frontales)."""
  o = p.copy() if hasattr(p, 'copy') else p
  n = 0
  ejes = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
  for d in ejes:
    h = tree.ray_cast(o, d, 1000)
    if h[0] is not None and h[1] is not None:
      dx, dy, dz = d[0], d[1], d[2]
      nx, ny, nz = _coord(h[1])
      if nx * dx + ny * dy + nz * dz > 0:
        n += 1
  return n >= 4


def clasificar_collider(nombre, verts, tree, face_count=None):
  ex, ey, ez = extents_vertices(verts)
  emin, emax = min(ex, ey, ez), max(ex, ey, ez)
  base = {'object': nombre, 'metodo': 'distancia_overlap'}
  if not verts or len(verts) < 4:
    return {**base, 'motivo': f'{nombre}: menos de cuatro vértices; no se aplica parity de interior'}
  if face_count == 0:
    return {**base, 'motivo': f'{nombre}: cero caras de polígono'}
  if emax < 1e-9:
    return {**base, 'motivo': f'{nombre}: extensión espacial nula'}
  if emin / max(emax, 1e-9) < 0.02 and emin < 0.05:
    return {**base, 'motivo': f'{nombre}: malla tipo lámina (espesor≈{emin:.4f} m); parity de volumen cerrado no aplica'}
  cen = (
    sum(_coord(v)[0] for v in verts) / len(verts),
    sum(_coord(v)[1] for v in verts) / len(verts),
    sum(_coord(v)[2] for v in verts) / len(verts),
  )
  viable, _, motivo = ray_parity_interiores(tree, cen)
  if viable:
    return {'object': nombre, 'metodo': 'interior_cerrado', 'motivo': None}
  return {**base, 'motivo': f'{nombre}: {motivo or "malla no apta para prueba de interior cerrado"}'}


def punto_dentro_collider(tree, p, meta, max_rebotes=256):
  if meta.get('metodo') != 'interior_cerrado':
    return False
  viable, dentro, _ = ray_parity_interiores(tree, p, max_rebotes=max_rebotes)
  if viable:
    return bool(dentro)
  return interior_multiray(tree, p)


def cuadros_muestra_penetracion(n, max_muestras=48):
  """Cuadros donde se revisan colliders (COM y contactos siguen en todos los cuadros)."""
  if n <= max_muestras:
    return list(range(1, n + 1))
  paso = max(1, (n + max_muestras - 1) // max_muestras)
  xs = list(range(1, n + 1, paso))
  if xs[-1] != n:
    xs.append(n)
  return xs


def _muestra_vertices(vs, nmax=32):
  if not vs or len(vs) <= nmax:
    return vs or []
  paso = max(1, len(vs) // nmax)
  return vs[::paso][:nmax]


def _algun_solido_cerrado(ma, mb):
  return ma.get('metodo') == 'interior_cerrado' or mb.get('metodo') == 'interior_cerrado'


def _adjacencia_maxima(rules, tol):
  """Distancia máxima para contar contacto entre láminas (no distancia a través del set)."""
  extra = rules.get('penetration_adjacency_max_m')
  if extra is not None:
    try:
      return max(float(tol), float(extra))
    except (TypeError, ValueError):
      pass
  return max(float(tol), 0.15)


def _firma_collider_mundo(obj):
  t = obj.matrix_world.translation
  return (round(float(t.x), 5), round(float(t.y), 5), round(float(t.z), 5))

def aabb_separados(a,b):
    return any(max(v[j] for v in a)<min(v[j] for v in b) or max(v[j] for v in b)<min(v[j] for v in a) for j in range(3))

def hull(points):
    points=sorted(set(tuple(p) for p in points))
    if len(points)<3:return points
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lo=[];hi=[]
    for p in points:
        while len(lo)>1 and cross(lo[-2],lo[-1],p)<=0:lo.pop()
        lo.append(p)
    for p in reversed(points):
        while len(hi)>1 and cross(hi[-2],hi[-1],p)<=0:hi.pop()
        hi.append(p)
    return lo[:-1]+hi[:-1]

def outside_distance(point,polygon):
    h=hull(polygon)
    if not h:raise ValueError('Apoyos ausentes: no existe suelo infinito implícito')
    if len(h)==1:return math.dist(point,h[0])
    d=math.inf;inside=True
    for a,b in zip(h,h[1:]+h[:1]):
        dx,dy=b[0]-a[0],b[1]-a[1];v=(point[0]-a[0])*dy-(point[1]-a[1])*dx
        if v>1e-10:inside=False
        u=max(0,min(1,((point[0]-a[0])*dx+(point[1]-a[1])*dy)/(dx*dx+dy*dy)))
        d=min(d,math.dist(point,(a[0]+u*dx,a[1]+u*dy)))
    return 0 if inside and len(h)>2 else d

def revisar(scene,d,rigs,objects,salida=None):
    from seguridad import exigir
    exigir("revisor")
    import bpy
    import os
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    from seguridad import cuadro
    try:
        from camara_memoria import objeto_animado
    except ImportError:
        objeto_animado = lambda _o: False
    try:
        from progreso_fisica import Progreso
        prog = Progreso(salida) if salida is not None else None
    except ImportError:
        prog = None
    fps=d['clock']['fps'];n=cuadro(d['clock']['duration_s'],fps);errors=[];mesh_review=[];revisados_malla=set();prev={};prev_contact={};max_out=0;max_com_accel=0;max_slip=0;max_ang=0;max_pen=0;rules=d['rules'];centres=[];naturalness={e['id']:[] for e in d['entities'] if e['type']=='CHARACTER'};last_root_z={}
    names=list(rules.get('colliders') or [])
    try:
        max_pen_f = int(os.environ.get('MOTOR_FISICA_MAX_CUADROS_PEN', '48'))
    except ValueError:
        max_pen_f = 48
    cuadros_pen=set(cuadros_muestra_penetracion(n, max_muestras=max(8, max_pen_f)))
    inicios_toma=cuadros_inicio_toma(d); skip_cine, _src_cine=exclusion_cinematica_contrato(rules)
    collider_estatico={nm: not objeto_animado(objects[nm]) for nm in names if nm in objects}
    cache_collider={}
    allow={frozenset(x) for x in rules['allowed_collision_pairs']};touch={frozenset(x) for x in rules.get('contact_pairs',[])}
    pares=[(a,b) for i,a in enumerate(names) for b in names[i+1:] if frozenset((a,b)) not in allow]
    if prog: prog.marcar(forzar=True, fase='inicio', cuadros_totales=n, cuadros_penetracion=len(cuadros_pen), colliders=len(names), pares=len(pares))
    def _collider(nm, f, dg):
        obj=objects[nm].evaluated_get(dg);clave=(nm, f) if collider_estatico.get(nm) is False else (nm, _firma_collider_mundo(obj))
        if clave in cache_collider: return cache_collider[clave]
        mesh=obj.to_mesh()
        try:
            vs=[obj.matrix_world@v.co for v in mesh.vertices];fs=[list(p.vertices) for p in mesh.polygons];nf=len(mesh.polygons)
        finally: obj.to_mesh_clear()
        tree=BVHTree.FromPolygons(vs, fs) if fs else None
        meta=clasificar_collider(nm, vs, tree, nf) if tree else {'object': nm, 'metodo': 'distancia_overlap', 'motivo': f'{nm}: sin geometría de polígonos'}
        if es_superficie_caminable(nm):
            zt=z_superior_estimada(vs)
            meta['superficie_caminable']=True
            if zt is not None:
                meta['z_top_m']=zt
        if nm not in revisados_malla and meta['metodo']!='interior_cerrado':
            revisados_malla.add(nm);mesh_review.append(meta)
        cache_collider[clave]=(tree, vs, meta)
        return cache_collider[clave]
    for f in range(1,n+1):
        scene.frame_set(f);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();row={'frame':f,'com':{}}
        for e in d['entities']:
            if e['type']!='CHARACTER':continue
            r=rigs[e['id']].evaluated_get(dg);mass=e['physics'].get('bone_mass_kg',e['physics'].get('bone_mass_weights'));total=sum(mass.values())
            if total<=0 or set(mass)!=set(r.pose.bones.keys()):raise ValueError('Mapa de masas completo y positivo requerido')
            com=sum(((r.matrix_world@((r.pose.bones[b].head+r.pose.bones[b].tail)/2))*m for b,m in mass.items()),Vector())/total;row['com'][e['id']]=list(com)
            out=None;is_supported=True
            if e['physics'].get('support_method')=='legacy_solver':
                # Mismo modelo y tolerancias del núcleo bueno, ahora sobre pose evaluada final.
                import importlib.util
                from pathlib import Path
                path=Path(__file__).parent/'heredado/movimiento_natural.py'
                if 'MN_legacy' not in globals():
                    sp=importlib.util.spec_from_file_location('MN_legacy',path);module=importlib.util.module_from_spec(sp);sp.loader.exec_module(module);globals()['MN_legacy']=module
                mn=globals()['MN_legacy'];rad=e['physics']['radii_m'];out=mn.distancia_fuera(mn.centro_masa(r,rad),mn.puntos_contacto(r,rad));max_out=max(max_out,out)
                if not rules.get('locked_naturalness') and out>e['physics']['balance_margin_m']:errors.append({'type':'EQUILIBRIO','frame':f,'entity':e['id'],'outside_m':out})
            else:
                states=[x for x in e['physics']['support_intervals'] if x['t0']<=(f-1)/fps<x['t1']]
                if len(states)!=1:raise ValueError('Cobertura de apoyos/aire incompleta o solapada')
                state=states[0]
                if state['mode']=='supported':
                    pts=[objects[x].evaluated_get(dg).matrix_world.translation for x in state['support_points']];out=outside_distance((com.x,com.y),[(p.x,p.y) for p in pts]);max_out=max(max_out,out)
                    if not rules.get('locked_naturalness') and out>e['physics']['balance_margin_m']:errors.append({'type':'EQUILIBRIO','frame':f,'entity':e['id'],'outside_m':out})
                elif state['mode'] not in {'airborne','flight','suspended'}:raise ValueError('Modo de apoyo desconocido')
                # Vuelos/cuelgues necesitan autorización de actuación en el programa, no bandera de perfil.
                elif not state.get('action_ref'):raise ValueError('Estado sin apoyo carece de acción fuente')
                is_supported=state['mode']=='supported'
            if rules.get('locked_naturalness'):
                z=r.matrix_world.translation.z;v=(z-last_root_z[e['id']])*fps if e['id'] in last_root_z else 0;last_root_z[e['id']]=z
                naturalness[e['id']].append({'frame':f,'outside_m':out if out is not None else 0,'balance_margin_m':e['physics']['balance_margin_m'],'hop':is_supported and v>e['physics']['hop_vertical_max_m_s']})
            quats={b.name:b.matrix.to_quaternion() for b in r.pose.bones}
            if e['id'] in prev:
                old_com,old_vel,old_q=prev[e['id']];vel=(com-old_com)*fps
                if old_vel is not None:
                    acc=(vel-old_vel).length*fps;max_com_accel=max(max_com_accel,acc)
                    if acc>rules['com_accel_max_m_s2']:
                        if not (skip_cine and f in inicios_toma):
                            err={'type':'ACELERACION_COM','frame':f,'entity':e['id'],'value':acc}
                            errors.append(anotar_error_toma(err, d, f, fps, rules))
                for name,q in quats.items():
                    angle=old_q[name].rotation_difference(q).angle;v=math.degrees(min(angle,2*math.pi-angle))*fps;max_ang=max(max_ang,v)
                    if v>rules['joint_speed_max_deg_s']:
                        if not (skip_cine and f in inicios_toma):
                            err={'type':'VELOCIDAD_ANGULAR','frame':f,'entity':e['id'],'bone':name,'value':v}
                            errors.append(anotar_error_toma(err, d, f, fps, rules))
            else:vel=None
            prev[e['id']]=(com.copy(),vel,quats)
        # Resbale relativo al punto objetivo, incluso cuando éste se mueve con otro actor.
        for i,c in enumerate(d['contacts']):
            if c['t0']<=(f-1)/fps<c['t1']:
                r=rigs[c['entity']].evaluated_get(dg);p=r.matrix_world@r.pose.bones[c['bone']].tail;t=objects[c['target_point']].evaluated_get(dg).matrix_world.translation;rel=p-t
                if i in prev_contact:
                    slip=(rel-prev_contact[i]).length;max_slip=max(max_slip,slip)
                    if slip>rules['slip_max_m_per_frame']:errors.append({'type':'RESBALE','frame':f,'contact':i,'value_m':slip})
                prev_contact[i]=rel.copy()
            else:prev_contact.pop(i,None)
        if f in cuadros_pen and names:
            if prog: prog.marcar(fase='penetracion', cuadro=f, rss_mb=None)
            trees={};verts={};meta_coll={}
            for name in names:
                ta, va, ma=_collider(name, f, dg);trees[name]=ta;verts[name]=va;meta_coll[name]=ma
            tol=rules['penetration_tolerance_m']; adj=_adjacencia_maxima(rules, tol)
            for pi, (a, b) in enumerate(pares):
                if prog and pi % 4 == 0: prog.marcar(fase='penetracion_par', cuadro=f, par='%s/%s' % (a, b), par_i=pi, pares=len(pares))
                va, vb=verts.get(a) or [], verts.get(b) or []
                if aabb_separados(va, vb): continue
                ta, tb=trees.get(a), trees.get(b)
                if ta is None or tb is None: continue
                overlapping=ta.overlap(tb);depth=0.0;ma, mb=meta_coll[a], meta_coll[b]
                for source, target in ((a, b), (b, a)):
                    vs=_muestra_vertices(verts.get(source)); tree_t=trees.get(target); mt=meta_coll.get(target)
                    if tree_t is None or not vs: continue
                    for v in vs:
                        nearest=tree_t.find_nearest(v)
                        if nearest[0] is None or nearest[3] <= tol: continue
                        ndist=float(nearest[3])
                        if mt.get('metodo') == 'interior_cerrado':
                            if punto_dentro_collider(tree_t, v, mt):
                                depth=max(depth, ndist)
                        elif overlapping and ndist <= adj:
                            depth=max(depth, ndist)
                        if depth > tol * 8: break
                max_pen=max(max_pen, depth)
                par=frozenset((a,b))
                if depth>tol:
                    err={'type':'PENETRACION','frame':f,'objects':[a,b],'depth_m':depth,'intersections':len(overlapping)}
                    if es_superficie_caminable(b) or es_superficie_caminable(a):
                        err['nota_apoyo']='Revisar apoyos IK/legacy y contact_pairs diseño (etapa 9-10); alfombra no sustituye piso en datos.'
                    errors.append(anotar_error_toma(err, d, f, fps, rules))
                elif overlapping and rules.get('reject_surface_intersections') and par not in touch and _algun_solido_cerrado(ma, mb):
                    err={'type':'PENETRACION','frame':f,'objects':[a,b],'depth_m':depth,'intersections':len(overlapping),'modo':'interseccion_superficie'}
                    errors.append(anotar_error_toma(err, d, f, fps, rules))
        centres.append(row)
    if rules.get('locked_naturalness'):
        from reglas_binding import revisar_limites
        errors+=revisar_limites(naturalness,rules['locked_naturalness'])
    out={'locked_naturalness_trace':naturalness,'frames':n,'max_outside_support_m':max_out,'max_com_accel_m_s2':max_com_accel,'max_relative_slip_m_frame':max_slip,'max_joint_speed_deg_s':max_ang,'max_penetration_m':max_pen,'mesh_review':mesh_review,'cuadros_penetracion':sorted(cuadros_pen),'all_passed':not errors,'errors':errors,'com_trace':centres}
    if prog: prog.cerrar('TERMINADO', errores=len(errors), max_penetracion_m=max_pen)
    return out
