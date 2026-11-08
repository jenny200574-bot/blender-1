"""Inspección de un .blend sin guardar, sin cambiar su contenido ni ejecutar scripts."""
import sys,json,bpy
from pathlib import Path
from mathutils import Vector
args=sys.argv[sys.argv.index('--')+1:];out=Path(args[0]);dg=bpy.context.evaluated_depsgraph_get();records=[]
for obj in bpy.context.scene.objects:
    ev=obj.evaluated_get(dg);r={'id':obj.name,'type':obj.type,'position_m':list(ev.matrix_world.translation),'rotation_euler_rad':list(ev.matrix_world.to_euler()),'dimensions_m':list(ev.dimensions),'parent':obj.parent.name if obj.parent else None,'hidden':obj.hide_render,'material_names':[m.name for m in obj.data.materials if m] if obj.type=='MESH' else []}
    if obj.type=='MESH':
        vs=[ev.matrix_world@Vector(x) for x in ev.bound_box];r['bbox_world_m']={'min':[min(p[i] for p in vs) for i in range(3)],'max':[max(p[i] for p in vs) for i in range(3)]};r['vertices']=len(obj.data.vertices);r['faces']=len(obj.data.polygons)
    records.append(r)
sc=bpy.context.scene
out.write_text(json.dumps({'unit_system':sc.unit_settings.system,'scale_length':sc.unit_settings.scale_length,'source_not_modified':True,'objects':records},ensure_ascii=False,indent=2))
