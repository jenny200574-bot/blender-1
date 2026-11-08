"""COM ponderado, apoyos, penetración y límites: usa geometría evaluada y perfiles declarados."""
import math

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

def revisar(scene,d,rigs,objects):
    from seguridad import exigir
    exigir("revisor")
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    from seguridad import cuadro
    fps=d['clock']['fps'];n=cuadro(d['clock']['duration_s'],fps);errors=[];prev={};prev_contact={};max_out=0;max_com_accel=0;max_slip=0;max_ang=0;max_pen=0;rules=d['rules'];centres=[];naturalness={e['id']:[] for e in d['entities'] if e['type']=='CHARACTER'};last_root_z={}
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
                    if acc>rules['com_accel_max_m_s2']:errors.append({'type':'ACELERACION_COM','frame':f,'entity':e['id'],'value':acc})
                for name,q in quats.items():
                    angle=old_q[name].rotation_difference(q).angle;v=math.degrees(min(angle,2*math.pi-angle))*fps;max_ang=max(max_ang,v)
                    if v>rules['joint_speed_max_deg_s']:errors.append({'type':'VELOCIDAD_ANGULAR','frame':f,'entity':e['id'],'bone':name,'value':v})
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
        # Todos los colliders suministrados son tratados por pares; los permitidos son explícitos.
        names=rules['colliders'];trees={};verts={}
        for name in names:
            obj=objects[name].evaluated_get(dg);mesh=obj.to_mesh();vs=[obj.matrix_world@v.co for v in mesh.vertices];fs=[list(p.vertices) for p in mesh.polygons];trees[name]=BVHTree.FromPolygons(vs,fs);verts[name]=vs;obj.to_mesh_clear()
        allow={frozenset(x) for x in rules['allowed_collision_pairs']};touch={frozenset(x) for x in rules.get('contact_pairs',[])}
        def inside(tree,p):
            ray=Vector((.87431,.37291,.31415)).normalized();origin=p.copy();count=0
            for _ in range(10000):
                hit=tree.ray_cast(origin,ray)
                if hit[0] is None:return bool(count%2)
                count+=1;origin=hit[0]+ray*1e-7
            # Keep the original epsilon and physical thresholds. Ensure the
            # float32 ray origin really advances on every nonzero ray axis.
            # Otherwise hit+1e-7 can round back onto the same face at room scale.
            import struct
            for axis in range(3):
                v=float(hit[0][axis])
                if ray[axis]>0 and origin[axis]<=v:
                    bits=struct.unpack("I",struct.pack("f",v))[0]
                    bits=bits+1 if v>=0 else bits-1
                    origin[axis]=struct.unpack("f",struct.pack("I",bits))[0]
                elif ray[axis]<0 and origin[axis]>=v:
                    bits=struct.unpack("I",struct.pack("f",v))[0]
                    bits=bits-1 if v>0 else bits+1
                    origin[axis]=struct.unpack("f",struct.pack("I",bits))[0]
            raise ValueError('Malla no apta para prueba de interior')
        for i,a in enumerate(names):
            for b in names[i+1:]:
                if frozenset((a,b)) in allow:continue
                # Un rayo de un punto exterior no puede convertir AABB disjuntos en penetración.
                if aabb_separados(verts[a],verts[b]):continue
                overlapping=trees[a].overlap(trees[b]);depth=0
                for source,target in ((a,b),(b,a)):
                    for v in verts[source]:
                        nearest=trees[target].find_nearest(v)
                        if nearest[0] is not None and nearest[3]>rules['penetration_tolerance_m'] and inside(trees[target],v):depth=max(depth,nearest[3])
                max_pen=max(max_pen,depth)
                if depth>rules['penetration_tolerance_m'] or overlapping and rules['reject_surface_intersections'] and frozenset((a,b)) not in touch:errors.append({'type':'PENETRACION','frame':f,'objects':[a,b],'depth_m':depth,'intersections':len(overlapping)})
        centres.append(row)
    if rules.get('locked_naturalness'):
        from reglas_binding import revisar_limites
        errors+=revisar_limites(naturalness,rules['locked_naturalness'])
    return {'locked_naturalness_trace':naturalness,'frames':n,'max_outside_support_m':max_out,'max_com_accel_m_s2':max_com_accel,'max_relative_slip_m_frame':max_slip,'max_joint_speed_deg_s':max_ang,'max_penetration_m':max_pen,'all_passed':not errors,'errors':errors,'com_trace':centres}
