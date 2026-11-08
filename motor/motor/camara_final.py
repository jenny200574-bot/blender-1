"""Coordenadas 4g integradas: SB normalizado, OneEuro, rayos y NDC por cuadro.
La traducción DSL completa continúa en camara_v2_blender.py; nunca convierte
un comando desconocido en una cámara quieta.
"""
import math
from seguridad import cuadro
from cinematica_camara import trayectoria

def construir(scene,shots,fps,objects):
    import bpy
    from mathutils import Vector,Quaternion
    from rig_camara_coords import OneEuro,mirar,sacudida
    cameras={}
    for s in shots:
        sp=dict(s['trajectory'],t0=s['t0'],t1=s['t1']);rows=trayectoria(sp,fps);data=bpy.data.cameras.new(s['id']);cam=bpy.data.objects.new(s['id']+'_camera',data);scene.collection.objects.link(cam);data.sensor_width=s['sensor_width_mm'];data.clip_start=s['clip_start_m'];data.clip_end=s['clip_end_m'];cam.rotation_mode='QUATERNION';filter=OneEuro(s['smoothing'])
        for r in rows:
            p=Vector(r['position']);q=mirar(p,Vector(r['target']),math.radians(s['roll_deg']));t=(r['frame']-1)/fps
            if s['handheld_amount']:
                rot,delta=sacudida(t,s['handheld_amount']);p+=delta;q=q@__import__('mathutils').Euler(rot).to_quaternion()
            if s['smoothing']>0:p=filter.P(p,1/fps);q=filter.Q(q,1/fps)
            cam.location=p;cam.rotation_quaternion=q;data.lens=r['lens_mm'];cam.keyframe_insert('location',frame=r['frame']);cam.keyframe_insert('rotation_quaternion',frame=r['frame']);data.keyframe_insert('lens',frame=r['frame'])
        cameras[s['id']]=cam
    return cameras

def revisar(scene,shots,cameras,fps,objects):
    import bpy
    from mathutils import Vector
    from bpy_extras.object_utils import world_to_camera_view
    errors=[];checked=0;extents_checked=0
    for s in shots:
        cam=cameras[s['id']];scene.camera=cam
        for f in range(cuadro(s['t0'],fps)+1,cuadro(s['t1'],fps)+1):
            scene.frame_set(f);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();checked+=1;p=cam.matrix_world.translation
            for id in s['check_points']:
                obj=objects[id];target=obj.matrix_world.translation;v=world_to_camera_view(scene,cam,target)
                if not (s['ndc_margin']<=v.x<=1-s['ndc_margin'] and s['ndc_margin']<=v.y<=1-s['ndc_margin'] and v.z>0):errors.append({'type':'ENCUADRE','shot':s['id'],'frame':f,'point':id})
                d=target-p
                if d.length:
                    hit,loc,normal,index,ob,matrix=scene.ray_cast(dg,p,d.normalized(),distance=max(0,d.length-s['ray_epsilon_m']))
                    if hit and ob.name not in s['occlusion_allowed_objects']:errors.append({'type':'OCLUSION','shot':s['id'],'frame':f,'point':id,'obstacle':ob.name})
            # Identidad del plano: medir todos los vértices evaluados de la anatomía final,
            # no aprobar una cámara porque sólo pasó el centro del personaje.
            for subject in s['subjects']:
                root=objects[subject['id']]
                members=[x for x in [root]+list(root.children_recursive) if x.type=='MESH' and not x.hide_render]
                if subject['scope']=='HEAD':members=[x for x in members if x.get('semantic_role') in {'head','face','eye','pupil','beak','eyebrow','hair'}]
                elif subject['scope']!='FULL':raise ValueError('El tipo de plano necesita una región explícita; no se sustituye por FULL')
                if not members:raise ValueError('Sujeto sin geometría evaluable para el plano')
                for member in members:
                    ev=member.evaluated_get(dg);mesh=ev.to_mesh()
                    for vertex in mesh.vertices:
                        v=world_to_camera_view(scene,cam,ev.matrix_world@vertex.co);extents_checked+=1
                        if not (s['ndc_margin']<=v.x<=1-s['ndc_margin'] and s['ndc_margin']<=v.y<=1-s['ndc_margin'] and v.z>0):
                            errors.append({'type':'RECORTE_SUJETO','shot':s['id'],'frame':f,'subject':subject['id'],'part':member.name});break
                    ev.to_mesh_clear()
            # Distancia mínima a superficies de mallas en coordenadas mundiales.
            from mathutils.bvhtree import BVHTree
            for obj in scene.objects:
                if obj.type!='MESH' or obj.hide_render:continue
                ev=obj.evaluated_get(dg);mesh=ev.to_mesh();vertices=[ev.matrix_world@v.co for v in mesh.vertices];polygons=[list(x.vertices) for x in mesh.polygons]
                if polygons:
                    tree=BVHTree.FromPolygons(vertices,polygons);nearest=tree.find_nearest(p)
                    if nearest[0] is not None and nearest[3]<s['min_clearance_m']:errors.append({'type':'HOLGURA_SUPERFICIE','shot':s['id'],'frame':f,'obstacle':obj.name,'distance_m':nearest[3]})
                ev.to_mesh_clear()
            # Holgura: seis rayos contra geometría real, no sólo centro dentro del bbox.
            clearance=s['min_clearance_m']
            for axis in (Vector((1,0,0)),Vector((-1,0,0)),Vector((0,1,0)),Vector((0,-1,0)),Vector((0,0,1)),Vector((0,0,-1))):
                if clearance>0 and scene.ray_cast(dg,p,axis,distance=clearance)[0]:errors.append({'type':'HOLGURA','shot':s['id'],'frame':f})
            if s['axis180']:
                a,b=([objects[x].matrix_world.translation for x in s['axis180']['point_ids']] if 'point_ids' in s['axis180'] else [Vector(x) for x in s['axis180']['points']]);v=(b-a).cross(p-a).z;sign=s['axis180']['side']
                if v*sign<-s['axis180']['epsilon_m2']:errors.append({'type':'EJE180','shot':s['id'],'frame':f})
    return {'frames_checked':checked,'extent_vertices_checked':extents_checked,'errors':errors,'all_passed':not errors}
