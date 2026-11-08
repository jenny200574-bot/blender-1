"""Cadena real BVH pulido→Blender→retarget→revisor geométrico, fixture sintético."""
import sys,math
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'motor'))
from seguridad import leer,guardar,sha,archivar
from geometria import rig_declarativo
from retarget import transferir
out=ROOT/'evidencia/bvh_retarget';out.mkdir(exist_ok=True)
source=ROOT/'evidencia/pulida_real/pulido.bvh'
before=set(o.name for o in bpy.data.objects)
bpy.ops.import_anim.bvh(filepath=str(source),axis_forward='-Z',axis_up='Y',global_scale=.01,rotate_mode='NATIVE',update_scene_fps=False,update_scene_duration=True)
armatures=[o for o in bpy.data.objects if o.type=='ARMATURE' and o.name not in before]
assert len(armatures)==1;src=armatures[0]
def b(id,head,tail,parent,role):return {'id':id,'head':head,'tail':tail,'parent':parent,'role':role,'limits_deg':[[-180,180]]*3}
spec={'bones':[b('r',[0,0,0],[0,0,.1],None,'root'),b('f',[0,0,0],[0,0,-1],'r','foot')]}
target=rig_declarativo('fixture_target',spec)
receipt=transferir(src,target,{'Hips':'r','Foot':'f'},range(1,49),1,[1,0,0,0],'Hips','r')
assert receipt['frames']==48 and receipt['bone_length_error_m']<1e-5
root=[x['root'] for x in receipt['trace']];acc=[math.dist([root[i+1][j]-2*root[i][j]+root[i-1][j] for j in range(3)],[0,0,0])*24**2 for i in range(1,len(root)-1)]
review={'frames':48,'fixed_lengths_pass':receipt['bone_length_error_m']<1e-5,'bone_length_error_m':receipt['bone_length_error_m'],'root_acceleration_max_m_s2':max(acc),'production_approved':False,'note':'No certifica contactos/acción/identidad de una escena real'}
result={'passed_component_chain':True,'source_bvh_sha256':sha(source),'polish_receipt':leer(ROOT/'evidencia/pulida_real/prueba.json'),'retarget':receipt,'review':review,'synthetic_fixture':True}
guardar(out/'cadena.json',result);archivar(out/'fixture.blend');bpy.ops.wm.save_as_mainfile(filepath=str(out/'fixture.blend'));print('CADENA_BVH_RETARGET_OK',48,receipt['bone_length_error_m'])
