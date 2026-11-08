"""Aplica cambios explícitos sobre el blend, nunca interpreta prosa como órdenes."""
import math

def faltantes(data):
 errors=list(data.get('missing',[]))
 if data.get('status')!='complete':errors.append({'campo':'environment.live','modulo':data.get('producer','escenario vivo'),'mensaje':'Estados narrativos encontrados; faltan vínculos Blender, propiedades y tiempos ejecutables'})
 return errors

def aplicar(scene,data,fps):
 import bpy
 errors=faltantes(data)
 if errors:return {'applied':False,'missing':errors}
 count=0
 for event in data['changes']:
  obj=bpy.data.objects.get(event['object'])
  if obj is None:raise ValueError('FALTA objeto de escenario vivo: '+event['object'])
  kind=event['kind']
  if kind not in ['transform','light','visibility','material']:raise ValueError('Tipo vivo no implementado: '+kind)
  for key in event['keys']:
   frame=1+round(key['t']*fps)
   if kind=='transform':
    for field in ['location','scale','rotation_deg']:
     if field in key:
      attr='rotation_euler' if field=='rotation_deg' else field;value=[math.radians(v) for v in key[field]] if field=='rotation_deg' else key[field];setattr(obj,attr,value);obj.keyframe_insert(attr,frame=frame)
   elif kind=='visibility':obj.hide_render=not key['visible'];obj.keyframe_insert('hide_render',frame=frame)
   elif kind=='light':
    if obj.type!='LIGHT':raise ValueError('Objetivo vivo no es luz')
    for field in ['energy','color']:
     if field in key:setattr(obj.data,field,key[field]);obj.data.keyframe_insert(field,frame=frame)
   else:
    material=obj.material_slots[event['slot']].material;shader=next((n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if shader is None:raise ValueError('FALTA material PBR explícito')
    for field,socket in [('base_color','Base Color'),('emission_color','Emission Color'),('emission_strength','Emission Strength'),('roughness','Roughness'),('metallic','Metallic')]:
     if field in key:shader.inputs[socket].default_value=key[field];shader.inputs[socket].keyframe_insert('default_value',frame=frame)
   count+=1
 return {'applied':True,'keys':count,'source':data['source']}
