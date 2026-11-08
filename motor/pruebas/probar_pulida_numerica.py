from pathlib import Path
import sys,math,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'motor'))
from seguridad import guardar,archivar,sha
from pulida_estricta import pulir
out=ROOT/'evidencia/pulida_real';out.mkdir(exist_ok=True)
# Clip sintético conocido, no movimiento inventado para un personaje de producción.
hier='''HIERARCHY
ROOT Hips
{
 OFFSET 0 0 0
 CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation
 JOINT Foot
 {
  OFFSET 0 -100 0
  CHANNELS 3 Zrotation Xrotation Yrotation
  End Site
  {
   OFFSET 0 -10 0
  }
 }
}
MOTION
Frames: 48
Frame Time: 0.041666666666666664
'''
rows=[];posed=[]
for i in range(48):
 x=.7*math.sin(i*.7);rows.append(f'{x} 100 0 0 0 0 0 0 0');posed.append([[x/100,0,0]])
src=out/'fixture.bvh';archivar(src);src.write_text(hier+'\n'.join(rows)+'\n')
npz=out/'effectors.npz';archivar(npz);np.savez(npz,posed_joints=np.array(posed),foot_contacts=np.ones((48,1),dtype=bool))
dst=out/'pulido.bvh';archivar(dst)
report=pulir(src,dst,unit_scale=.01,footlock=True,npz=npz,effector_map={'ids':['Foot'],'unit':'m','up':'Y'})
assert report['footlock_applied'] is True and dst.is_file()
report.update({'passed':True,'synthetic_fixture':True,'source_sha256':sha(src),'result_sha256':sha(dst),'production_motion':False})
guardar(out/'prueba.json',report);print('PULIDA_NUMERICA_REAL',report['footlock_applied'],report['n_frames'])
