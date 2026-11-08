import sys,json,math
from pathlib import Path
import bpy
from mathutils import Vector
R=Path('/opt/myia-motor-v9/avance08_20261107');M=R/'MOTOR_UNICO_20261107/motor'
sys.path.insert(0,str(M/'heredado'))
import rig
x=json.loads((R/'esc1_candidata/entrada_escena.json').read_text());e=next(q for q in x['entities'] if q['id']=='ch-eco-eff3');a=rig.crear(e['id'],e['legacy']['spec'],e['legacy']['colors'])
b=a.data.bones['clavicula_L'];arm=a.data.bones['brazo_L'];inv=b.matrix_local.to_3x3().inverted()
out={'source':'Measured native rig from existing Eco ADN; rest rig coordinates, not certified surface thickness','head_upperarm_minus_tail_clavicle_m':(arm.head_local-b.tail_local).length,'clavicle_bone':'clavicula_L','length_m':b.length,'head':list(b.head_local),'tail':list(b.tail_local),'inverse_rotation_rows':[list(q) for q in inv],'inverse_rotation_euler_deg':[math.degrees(v) for v in inv.to_euler()],'point_tail_local':[0,0,0],'native_left_measured':True}
assert out['head_upperarm_minus_tail_clavicle_m']<1e-7
(R/'entrega/evidencias/hombro_medido08.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
