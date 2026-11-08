import sys,json,math,os
os.environ['MOTOR_UNICO_CPU_PRUEBA']='1'
from pathlib import Path
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r/'motor'));import bpy
from apariencia_3d import construir_parte
from seguridad import guardar
args=sys.argv[sys.argv.index('--')+1:];data=json.loads(Path(args[0]).read_text());out=Path(args[1]);out.mkdir(parents=True,exist_ok=True);checks=[]
for i,case in enumerate(data['cases']):
 for ob in list(bpy.context.scene.objects):ob.hide_render=True
 parent=bpy.data.objects.new('container_'+str(i),None);bpy.context.scene.collection.objects.link(parent);objects={parent.name:parent};spec=case['spec']
 try:
  root=construir_parte(spec,parent,objects);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();verts=[]
  for ob in root.children_recursive:
   if ob.type!='MESH':continue
   ev=ob.evaluated_get(dg);m=ev.to_mesh();verts.extend(root.matrix_world.inverted()@ev.matrix_world@v.co for v in m.vertices);ev.to_mesh_clear()
  passed=max(abs(root.rotation_euler[i]-math.radians(spec['rotation_deg'][i])) for i in range(3))<1e-6;dimensions=None;lo=None
  if case['check_bounds']:
   lo=[min(v[i] for v in verts) for i in range(3)];hi=[max(v[i] for v in verts) for i in range(3)];dimensions=[b-a for a,b in zip(lo,hi)];passed &= max(abs(x-y) for x,y in zip(dimensions,spec['dimensions_m']))<2e-5;expected_z=0 if spec['ancla_z']=='base' else -spec['dimensions_m'][2]/2;passed &= abs(lo[2]-expected_z)<2e-5
  checks.append({'formula':spec['formula'],'anchor':spec['ancla_z'],'passed':bool(passed),'dimensions_m':dimensions,'min_local':lo,'objects':len(objects)})
 except Exception as exc:checks.append({'formula':spec['formula'],'anchor':spec['ancla_z'],'passed':False,'error_type':type(exc).__name__,'message':str(exc)})
 guardar(out/'regresiones_catalogo.json',{'checks':checks,'all_passed':all(x['passed'] for x in checks),'cpu':True,'spend_usd':0})
print('CATALOGO',sum(x['passed'] for x in checks),'/',len(checks));sys.exit(0 if all(x['passed'] for x in checks) else 17)
