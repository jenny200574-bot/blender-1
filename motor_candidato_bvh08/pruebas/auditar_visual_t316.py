import bpy,json,sys
from pathlib import Path
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r/'motor'));from seguridad import guardar
bpy.ops.wm.open_mainfile(filepath=str(r/'evidencia/contacto_guardianes_t314_definitivo/diagnostico.blend'));sc=bpy.context.scene
d={'render':sc.render.engine,'view':sc.view_settings.view_transform,'exposure':sc.view_settings.exposure,'world':[],'lights':[],'objects':[]}
for n in sc.world.node_tree.nodes:
 if n.type=='BACKGROUND':d['world'].append({'color':list(n.inputs['Color'].default_value),'strength':n.inputs['Strength'].default_value})
for o in sc.objects:
 if o.type=='LIGHT':d['lights'].append({'id':o.name,'energy':o.data.energy,'shadow':o.data.use_shadow,'hidden':o.hide_render})
 if o.type=='MESH' and not o.parent:d['objects'].append({'id':o.name,'props':{k:v for k,v in o.items() if isinstance(v,(str,int,float,bool))},'materials':[{'id':m.name,'nodes':m.use_nodes,'rgba':list(m.diffuse_color)} for m in o.data.materials if m],'hidden':o.hide_render})
guardar(r/'evidencia/auditoria_visual_t314.json',d)
