"""Rig anatómico declarativo, puntos en objetos y bisagras con magnitudes suministradas."""
import math
from seguridad import *

def validar_rig(spec):
 E=[];bones=spec.get('bones',[]);names=[b.get('id') for b in bones]
 if not bones or len(names)!=len(set(names)):E.append(error('rig/bones','ADN/esqueleto','Huesos ausentes/repetidos'))
 known=set()
 for b in bones:
  field='rig/'+str(b.get('id'))
  if not all(k in b for k in ['id','head','tail','parent','limits_deg','role']):E.append(error(field,'ADN/esqueleto','Especificación ósea incompleta'));continue
  if b['parent'] is not None and b['parent'] not in known:E.append(error(field,'ADN/esqueleto','Padre ausente o grafo no topológico'))
  if len(b['head'])!=3 or len(b['tail'])!=3 or math.dist(b['head'],b['tail'])<=1e-8:E.append(error(field,'ADN/esqueleto','Longitud de hueso inválida'))
  if len(b['limits_deg'])!=3 or any(len(x)!=2 or x[0]>x[1] for x in b['limits_deg']):E.append(error(field,'ADN/esqueleto','Límites inválidos'))
  known.add(b['id'])
 return E

def rig_declarativo(pid,spec):
 exigir("geometria")
 import bpy
 E=validar_rig(spec)
 if E:raise ValueError(str(E))
 a=bpy.data.armatures.new(pid+'_rig');obj=bpy.data.objects.new(pid,a);bpy.context.scene.collection.objects.link(obj);bpy.context.view_layer.objects.active=obj;obj.select_set(True)
 bpy.ops.object.mode_set(mode='EDIT')
 for b in spec['bones']:
  eb=a.edit_bones.new(b['id']);eb.head=b['head'];eb.tail=b['tail']
  if b['parent']:eb.parent=a.edit_bones[b['parent']]
 bpy.ops.object.mode_set(mode='OBJECT')
 for b in spec['bones']:
  pb=obj.pose.bones[b['id']];pb.rotation_mode='XYZ';pb['role']=b['role'];con=pb.constraints.new('LIMIT_ROTATION');con.owner_space='LOCAL'
  for axis,bounds in zip('xyz',b['limits_deg']):setattr(con,'use_limit_'+axis,True);setattr(con,'min_'+axis,math.radians(bounds[0]));setattr(con,'max_'+axis,math.radians(bounds[1]))
 return obj

def registrar_puntos(obj,spec,objects=None):
 exigir("geometria")
 import bpy
 from mathutils import Matrix
 out={};objects=objects or {}
 for p in spec:
  if not all(k in p for k in ['id','position_m','rotation_deg','source']):raise ValueError('Punto sin coordenadas/procedencia')
  if p['id'] in out:raise ValueError('ID de punto repetido')
  parent_id=p.get('pieza_movil');parent=objects.get(parent_id) if parent_id is not None else obj
  if parent is None:raise ValueError('Punto referencia pieza móvil no registrada: '+str(parent_id))
  frame=p.get('frame','LOCAL')
  if frame not in ['WORLD','LOCAL']:raise ValueError('Marco de punto debe ser WORLD o LOCAL')
  pt=bpy.data.objects.new(obj.name+'.'+p['id'],None);bpy.context.scene.collection.objects.link(pt);pt.parent=parent;pt.matrix_parent_inverse=Matrix.Identity(4)
  if p.get('bone'):
   if parent.type!='ARMATURE' or p['bone'] not in parent.pose.bones:raise ValueError('Hueso padre de punto inexistente')
   pt.parent_type='BONE';pt.parent_bone=p['bone']
  if frame=='WORLD':
   from mathutils import Euler
   bpy.context.view_layer.update();world=Matrix.Translation(p['position_m'])@Euler([math.radians(x) for x in p['rotation_deg']]).to_matrix().to_4x4();pt.matrix_world=world
  else:pt.location=p['position_m'];pt.rotation_euler=[math.radians(x) for x in p['rotation_deg']]
  pt['point_source']=str(p['source']);pt['source_frame']=frame;pt['piece_binding']=parent.name;out[p['id']]=pt
 return out

def bisagra(obj,pivot,axis,angle_min,angle_max,keys,fps):
 exigir("geometria")
 import bpy
 from mathutils import Vector
 if not keys or any(not 0<=k['c']<=1 for k in keys):raise ValueError('Control c fuera de [0,1]')
 if Vector(axis).length<1e-8:raise ValueError('Eje de bisagra nulo')
 p=bpy.data.objects.new(obj.name+'_bisagra',None);bpy.context.scene.collection.objects.link(p);p.location=pivot
 world=obj.matrix_world.copy();obj.parent=p;obj.matrix_world=world;p.rotation_mode='AXIS_ANGLE';ax=Vector(axis).normalized()
 for key in keys:
  angle=math.radians(angle_min+(angle_max-angle_min)*key['c']);p.rotation_axis_angle=(angle,*ax);p.keyframe_insert('rotation_axis_angle',frame=1+cuadro(key['t'],fps))
 return p

def ik_punto(rig,bone,target,chain_length,iterations):
 exigir("geometria")
 if bone not in rig.pose.bones:raise ValueError('Efector inexistente')
 c=rig.pose.bones[bone].constraints.new('IK');c.target=target;c.chain_count=chain_length;c.iterations=iterations;c.use_tail=True;c.use_stretch=False;return c
