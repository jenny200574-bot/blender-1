"""Traduce cámara entregada o calcula encuadre automático declarado."""
import bpy,math
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

def crear(scene,data,trazas,actors,fps):
 cd=bpy.data.cameras.new('camera_data');ob=bpy.data.objects.new('CAMARA_ENTRADA',cd);scene.collection.objects.link(ob);scene.camera=ob;cd.clip_end=data['clip_end'];cd.sensor_width=data['sensor_width_mm']
 report={'origen':data['source'],'causa':data['cause'],'modo':data['mode'],'ajustes':[]}
 if data['mode']=='plan':
  for k in data['keys']:
   frame=1+round(k['t']*fps);ob.location=k['loc'];ob.rotation_euler=(Vector(k['mira'])-ob.location).to_track_quat('-Z','Y').to_euler();cd.lens=k['lens'];ob.keyframe_insert('location',frame=frame);ob.keyframe_insert('rotation_euler',frame=frame);cd.keyframe_insert('lens',frame=frame)
 elif data['mode']=='sb':
  cut_frames=[]
  for shot in data['shots']:
   pid=shot['target'];is_object=shot.get('target_type')=='object';T=next(iter(trazas.values())) if is_object else trazas[pid];H=0 if is_object else actors[pid]['spec']['altura_m'];heads=1 if is_object else actors[pid]['spec']['cabezas'];keys=shot['keys'];last=max(1,round(shot['t1']*fps));cut_frames.append(last)
   track_keys=keys+[dict(keys[-1],t=(last-1)/fps)]
   if is_object:
    # El objetivo está anclado y se mueve: seguir su posición evaluada, no interpolar sólo los extremos.
    track_keys=[]
    for frame in range(1+round(shot['t0']*fps),last+1):
     tt=(frame-1)/fps;left=keys[0];right=keys[-1]
     for k0,k1 in zip(keys,keys[1:]):
      if k0['t']<=tt<=k1['t']:left,right=k0,k1;break
     u=max(0.,min(1.,(tt-left['t'])/(right['t']-left['t']))) if right['t']!=left['t'] else 0.
     key=dict(left,t=tt)
     for field in ['lens','azimuth_deg','object_margin']:key[field]=left[field]+(right[field]-left[field])*u
     track_keys.append(key)
   for key in track_keys:
    fr=max(1,min(len(T),1+round(key['t']*fps)));tr=T[fr-1];head=Vector(tr['cabeza']);floor=data['floor_z'];mode=key['target_point']
    if mode=='head':target=head-Vector((0,0,H/heads*.45))
    elif mode=='chest':target=Vector(tr['pecho'])
    else:target=Vector((tr['loc'][0],tr['loc'][1],(floor+head.z)/2))
    distance=key['distance_m']
    if is_object:
     scene.frame_set(fr);scene.view_layers[0].update();root=bpy.data.objects.get(pid)
     if root is None:raise ValueError('FALTA geometría del objetivo cámara')
     stack=[root];corners=[]
     while stack:
      obj=stack.pop();stack.extend(obj.children)
      if obj.type=='MESH':corners.extend(obj.matrix_world@Vector(c) for c in obj.bound_box)
     lo=Vector([min(p[i] for p in corners) for i in range(3)]);hi=Vector([max(p[i] for p in corners) for i in range(3)]);target=(lo+hi)/2
     if distance is None:
      extent=max(hi[i]-lo[i] for i in range(3));distance=extent*key['object_margin']*key['lens']/data['sensor_height_mm'];report['ajustes'].append({'frame':fr,'causa':'distancia técnica derivada de geometría proxy; NO SB aprobado','dimension_medida_m':extent,'distancia_m':distance})
    yaw=math.radians(key['azimuth_deg']);pitch=math.radians(shot['elevation_deg']);offset=Vector((math.sin(yaw)*math.cos(pitch),-math.cos(yaw)*math.cos(pitch),math.sin(pitch)))*distance
    ob.location=target+offset
    clearance=floor+data['clearance_m']
    if ob.location.z<clearance:report['ajustes'].append({'frame':fr,'causa':'b: traducción del ángulo penetraba el suelo','antes_z':ob.location.z,'despues_z':clearance});ob.location.z=clearance
    ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler();cd.lens=key['lens'];ob.keyframe_insert('location',frame=fr);ob.keyframe_insert('rotation_euler',frame=fr);cd.keyframe_insert('lens',frame=fr)
  for block in [ob,cd]:
   if block.animation_data and block.animation_data.action:
    act=block.animation_data.action
    for layer in act.layers:
     for strip in layer.strips:
      for slot in act.slots:
       bag=strip.channelbag(slot)
       if bag:
        for fc in bag.fcurves:
         for key in fc.keyframe_points:
          if round(key.co.x) in cut_frames:key.interpolation='CONSTANT'
 elif data['mode']=='auto_inside':
  # Cámara dentro del molde: no ocultar el techo/paredes para obtener una toma.
  samples=[]
  for pid,T in trazas.items():
   for fr in range(0,len(T),max(1,len(T)//12)):
    root=Vector(T[fr]['loc']);low=T[fr]['zmin'];high=T[fr]['cabeza'][2]
    samples.extend([Vector((root.x,root.y,low+(high-low)*z)) for z in [0,.5,1]])
  lo=Vector([min(x[i] for x in samples) for i in range(3)]);hi=Vector([max(x[i] for x in samples) for i in range(3)]);target=(lo+hi)/2;best=None;dep=bpy.context.evaluated_depsgraph_get();pad=data['margin_fraction']
  for name in data['candidates']:
   source=bpy.data.objects.get(name)
   if source is None:raise ValueError('Cámara fuente ausente: '+name)
   ob.location=source.matrix_world.translation;ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
   l,h=data['lens_limits']
   for _ in range(18):
    cd.lens=(l+h)/2;scene.view_layers[0].update();xy=[world_to_camera_view(scene,ob,p) for p in samples];fits=all(x.z>0 and pad<=x.x<=1-pad and pad<=x.y<=1-pad for x in xy)
    if fits:l=cd.lens
    else:h=cd.lens
   cd.lens=l;visible=0
   for point in samples:
    ray=point-ob.location;dist=ray.length;hit,loc,normal,index,obj,matrix=scene.ray_cast(dep,ob.location,ray.normalized(),distance=max(0,dist-.05))
    if not hit or (obj and obj.parent and obj.parent.type=='ARMATURE'):visible+=1
   score=visible/len(samples)*1000+l
   if best is None or score>best[0]:best=(score,ob.location.copy(),ob.rotation_euler.copy(),l,name,visible/len(samples))
  if best is None:raise ValueError('Sin cámaras/puntos candidatos para encuadre interior')
  ob.location=best[1];ob.rotation_euler=best[2];cd.lens=best[3];report.update(camara_fuente=best[4],lente_tecnica_mm=best[3],visibilidad_muestreada=best[5],encuadre='AUTOMATICO sobre puntos de 4a2, NO SB')
 else:
  points=[Vector(x['loc']) for T in trazas.values() for x in T];lo=Vector([min(x[i] for x in points) for i in range(3)]);hi=Vector([max(x[i] for x in points) for i in range(3)]);H=max(a['spec']['altura_m'] for a in actors.values());target=(lo+hi)/2+Vector((0,0,H*.5));extent=max(hi.x-lo.x,hi.y-lo.y,H);cd.type='ORTHO';cd.ortho_scale=extent*data['margin'];ob.location=target+Vector(data['direction'])*extent;ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
 return ob,report
