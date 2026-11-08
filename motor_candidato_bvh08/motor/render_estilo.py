"""Preset técnico por datos, compartido por render final y diagnóstico."""
from seguridad import exigir
def configurar(scene,preset,base_lighting=True):
 exigir('render_estilo');scene.render.engine=preset['engine'];scene.render.resolution_x,scene.render.resolution_y=preset['resolution'];scene.render.resolution_percentage=100
 if preset['engine']=='BLENDER_EEVEE':
  if not preset.get('software_cpu'):raise ValueError('EEVEE exige software_cpu explícito en fases CPU')
  scene.eevee.taa_render_samples=preset['samples'];scene.render.film_transparent=False
 if base_lighting:
  scene.world.use_nodes=True
  for n in scene.world.node_tree.nodes:
   if n.type=='BACKGROUND':n.inputs['Color'].default_value=[*preset['world_color'],1];n.inputs['Strength'].default_value=preset['world_strength']
  scene.view_settings.exposure=preset['exposure'];scene.view_settings.view_transform=preset['view_transform'];scene.view_settings.look=preset['look']
 if base_lighting:
  import bpy
  from mathutils import Vector
  for light in preset.get('technical_lights',[]):
   ob=bpy.data.objects.get(light['id'])
   if ob is None:
    data=bpy.data.lights.new(light['id'],'AREA');ob=bpy.data.objects.new(light['id'],data);scene.collection.objects.link(ob)
   ob.location=light['position_m'];ob.rotation_euler=(Vector(light['target_m'])-ob.location).to_track_quat('-Z','Y').to_euler();ob.data.energy=light['energy'];ob.data.color=light['color'];ob.data.shape='DISK';ob.data.size=light['size_m'];ob.data.use_shadow=True;ob['technical_preview_not_artistic']=True
 for ob in scene.objects:
  if ob.type=='LIGHT':ob.data.use_shadow=True
 return {'engine':scene.render.engine,'world_strength':preset['world_strength'],'exposure':scene.view_settings.exposure,'look':scene.view_settings.look,'source':preset['source'],'all_lights_shadow':all(o.data.use_shadow for o in scene.objects if o.type=='LIGHT')}
