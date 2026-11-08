"""Verificación independiente del blend sintético; no evalúa identidad Guardianes."""
import sys,math,json,bpy
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'motor'));from seguridad import guardar
out=Path(sys.argv[sys.argv.index('--')+1]);sc=bpy.context.scene;checks=[]
def check(id,actual,expected,tol=1e-5):checks.append({'test':id,'actual':actual,'expected':expected,'passed':abs(actual-expected)<=tol})
check('huesos_aviares',len(bpy.data.objects['bird_fixture'].pose.bones),19,0)
for f,energy,red,angle in [(1,400,1,0),(9,250,.6,30),(17,100,.2,60)]:
 sc.frame_set(f);bpy.context.view_layer.update();check('luz_global_f'+str(f),bpy.data.lights['key_light'].energy,energy)
 check('material_global_f'+str(f),bpy.data.materials['prop_base_material'].node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value[0],red)
 check('bisagra_global_f'+str(f),math.degrees(bpy.data.objects['lid_hinge'].rotation_axis_angle[0]),angle)
guardar(out,{'all_passed':all(c['passed'] for c in checks),'checks':checks,'fixture_only':True});print('CHEQUEOS',all(c['passed'] for c in checks))
