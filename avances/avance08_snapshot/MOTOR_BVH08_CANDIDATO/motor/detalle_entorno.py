"""Sustituye moldes por recetas explícitas del catálogo. No decide por nombres."""
import math
from seguridad import exigir
def aplicar(jobs,objects):
 exigir('detalle_entorno');import bpy
 from apariencia_3d import construir_parte
 receipts=[]
 for job in jobs:
  old=objects.get(job['object_id'])
  if old is None:raise ValueError('FALTA objeto de plano: '+job['object_id'])
  old.name=job['object_id']+'.archivo_molde';old.hide_render=True;old['motor_preserve_hidden']=True
  root=bpy.data.objects.new(job['object_id'],None);bpy.context.scene.collection.objects.link(root);root.location=job['position_m'];root.rotation_euler=[math.radians(x) for x in job['rotation_deg']];objects[root.name]=root
  spec=dict(job['spec']);construir_parte(spec,root,objects);receipts.append({'object':root.name,'formula':spec['formula'],'source':job['source'],'library_fidelity':'base de catálogo, no ADN exacto','children':len(root.children_recursive)})
 return receipts
