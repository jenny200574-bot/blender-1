"""ADN estructurado por piezas: no sustituye medidas/materiales ausentes con cápsulas."""
from pathlib import Path

def analizar(record):
 used=[];missing=[];source=record.get('source_data',{});numeric=source.get('geometria_3d')
 # Las descripciones y medidas existentes se conservan; no equivalen a una malla final.
 for key in ['frase_sello','nunca_cambia','texto','text','medidas_cm','colores','materiales','puntos_anclaje']:
  if key in source:used.append(key)
 if not numeric:
  missing.append({'campo':'geometria_3d','modulo':'ADN Maestro 03/04 / puente ADN→3D','mensaje':'ADN descriptivo conservado; falta representación 3D declarativa o activo 3D vinculado. No se inventa malla.'})
 else:
  for i,part in enumerate(numeric):
   for key in ['id','shape','dimensions_m','position_m','rotation_deg','material']:
    if key not in part:missing.append({'campo':f'geometria_3d/{i}/{key}','modulo':'ADN Maestro 03/04','mensaje':'Campo de pieza ausente'})
   for key in ['base_color','roughness','metallic']:
    if key not in part.get('material',{}):missing.append({'campo':f'geometria_3d/{i}/material/{key}','modulo':'ADN Maestro 03/04','mensaje':'No se infiere color/material desde una palabra'})
 import re
 dimensions={k[:-3]:v/100 for k,v in source.get('medidas_cm',{}).items() if k.endswith('_cm') and isinstance(v,(int,float))}
 colors={}
 for name,value in source.get('colores',{}).items():
  match=re.search(r'#([0-9a-fA-F]{6})',str(value))
  if match:colors[name]=[int(match[1][i:i+2],16)/255 for i in [0,2,4]]
 return {'fields_present':used,'dimensions_m_read_from_DNA':dimensions,'rgb_hex_read_from_DNA':colors,'missing':missing,'can_build':not missing}

def construir(record,collection,host_rig=None):
 import bpy
 from mathutils import Matrix
 import math
 report=analizar(record)
 if report['missing']:return [],report
 objects=[]
 for part in record['source_data']['geometria_3d']:
  shape=part['shape'];dims=part['dimensions_m']
  if shape=='box':bpy.ops.mesh.primitive_cube_add(size=1)
  elif shape=='ellipsoid':bpy.ops.mesh.primitive_uv_sphere_add(radius=1,segments=part['segments'],ring_count=part['rings'])
  elif shape=='cylinder':bpy.ops.mesh.primitive_cylinder_add(radius=1,depth=1,vertices=part['segments'])
  else:raise ValueError('FALTA constructor de forma ADN: '+shape)
  obj=bpy.context.object;obj.name=record['id']+'_'+part['id'];obj.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);obj.location=part['position_m'];obj.rotation_euler=[math.radians(v) for v in part['rotation_deg']]
  mat=bpy.data.materials.new(obj.name+'_material');mat.use_nodes=True;shader=mat.node_tree.nodes.get('Principled BSDF');m=part['material'];shader.inputs['Base Color'].default_value=m['base_color'];shader.inputs['Roughness'].default_value=m['roughness'];shader.inputs['Metallic'].default_value=m['metallic'];obj.data.materials.append(mat)
  if part.get('anchor'):
   anchor=part['anchor']
   if host_rig is None:raise ValueError('FALTA rig host del ancla ADN')
   obj.parent=host_rig;obj.parent_type='BONE';obj.parent_bone=anchor['bone'];obj.matrix_parent_inverse=Matrix()
  objects.append(obj)
 return objects,report

def aplicar_paquete(bundle,scene):
 import bpy
 reports=[]
 for record in bundle['records']:
  obj=bpy.data.objects.get(record['id']);report=analizar(record);report['id']=record['id'];report['fields_used_for_geometry']=[]
  if obj is None:report['binding']='No hay ID Blender exacto; no se adivina correspondencia';reports.append(report);continue
  if not report['can_build']:report['binding']='ADN exacto presente pero todavía descriptivo';reports.append(report);continue
  old=[x for x in obj.children_recursive if x.type=='MESH'];host=obj if obj.type=='ARMATURE' else None;objects,report2=construir(record,scene.collection,host);report.update(report2);report['fields_used_for_geometry']=['geometria_3d','materiales por pieza','transformaciones/anclas']
  for x in old:x.hide_render=True
  reports.append(report)
 return reports
