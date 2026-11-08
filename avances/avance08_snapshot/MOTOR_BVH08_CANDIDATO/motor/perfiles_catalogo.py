"""Perfiles Star genéricos por referencia y mapa explícito; ningún nombre de personaje en el lector."""
from seguridad import leer,ruta,sha,error

def compilar(d,root):
 receipts=[];errors=[]
 for entity in d.get('entities',[]):
  ref=entity.get('anatomical_catalog_ref')
  if not ref:continue
  p=ruta(root,ref['path'])
  if sha(p)!=ref['sha256']:raise ValueError('Perfil anatómico cambió de hash')
  profile=leer(p);mapping=ref.get('bone_map',{});points=[]
  for name,point in profile.get('puntos',{}).items():
   bone=mapping.get(point['hueso'])
   if not bone:errors.append(error('entities/'+entity['id']+'/anatomical_catalog_ref/bone_map/'+point['hueso'],'ADN→esqueleto','Falta mapa explícito de hueso del perfil'));continue
   points.append({'id':name,'bone':bone,'ext':point['ext'],'source':{'profile':ref['path'],'sha256':ref['sha256']}})
  entity['anatomical_catalog_points']=points;entity['anatomical_catalog_joint_limits']=profile.get('articulaciones',{});receipts.append({'entity':entity['id'],'profile':profile['profile_id'],'sha256':ref['sha256'],'points':len(points),'state':'BOUND' if not errors else 'WAITING_DATA'})
 return receipts,errors

def aplicar_puntos(entity,rig,objects):
 import bpy
 from mathutils import Matrix
 made=[]
 for point in entity.get('anatomical_catalog_points',[]):
  bone=rig.data.bones.get(point['bone'])
  if bone is None:raise ValueError('Perfil: hueso ausente en el .blend '+point['bone'])
  ident=entity['id']+'.'+point['id']
  if ident in objects:raise ValueError('Punto de perfil duplicado: '+ident)
  obj=bpy.data.objects.new(ident,None);bpy.context.scene.collection.objects.link(obj);obj.parent=rig;obj.parent_type='BONE';obj.parent_bone=bone.name;obj.matrix_parent_inverse=Matrix.Identity(4);obj.location=(0,-bone.length if point['ext'] in ['head','dir'] else 0,0);obj['point_source']=str(point['source']);obj['point_kind']='DIRECTION' if point['ext']=='dir' else 'POSITION';objects[ident]=obj;made.append(ident)
 return made
