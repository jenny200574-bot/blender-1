"""Retarget Blender por mapa/rest explícitos. No elige actor, acción ni clip."""
import math
from seguridad import exigir

def transferir(source,target,mapping,frames,unit_scale,axis_quaternion,root_source,root_target):
 exigir("movimiento")
 from mathutils import Quaternion
 if not mapping or unit_scale<=0:raise ValueError('Mapa y escala explícitos requeridos')
 if any(a not in source.pose.bones or b not in target.pose.bones for a,b in mapping.items()):raise ValueError('Mapa referencia hueso ausente')
 if root_source not in mapping or mapping[root_source]!=root_target:raise ValueError('Mapa de raíz inválido')
 import bpy
 axis=Quaternion(axis_quaternion);axis.normalize();trace=[];lengths={b.name:b.length for b in target.data.bones}
 for f in frames:
  bpy.context.scene.frame_set(f);bpy.context.view_layer.update()
  for src,dst in mapping.items():
   a=source.pose.bones[src];b=target.pose.bones[dst];basis=b.bone.matrix_local.to_quaternion().inverted() @ axis @ a.bone.matrix_local.to_quaternion()
   b.rotation_mode='QUATERNION';b.rotation_quaternion=basis @ a.matrix_basis.to_quaternion() @ basis.inverted();b.keyframe_insert('rotation_quaternion',frame=f)
  target.location=axis @ source.pose.bones[root_source].matrix_basis.translation * unit_scale;target.keyframe_insert('location',frame=f);bpy.context.view_layer.update()
  trace.append({'frame':f,'root':list(target.location),'bone_lengths':{b.name:(b.tail-b.head).length for b in target.pose.bones}})
 max_d=max(abs(row['bone_lengths'][k]-v) for row in trace for k,v in lengths.items())
 return {'frames':len(trace),'bone_length_error_m':max_d,'scale':unit_scale,'axis_quaternion':list(axis),'mapping':mapping,'trace':trace}
