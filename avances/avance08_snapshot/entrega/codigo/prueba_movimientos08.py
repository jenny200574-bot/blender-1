import sys,json,math,copy
from pathlib import Path
import bpy
R=Path('/opt/myia-motor-v9/avance08_20261107');P=R/'esc1_candidata';M=R/'MOTOR_UNICO_20261107';sys.path.insert(0,str(M/'motor/heredado'));import rig
read=lambda p:json.loads(p.read_text());d=read(P/'entrada_escena.json');c=read(P/'catalogo_poses_escena.json');rows=read(P/'asignacion_para_motor.json');checks=[];report=[];maximum=0
for e in d['entities']:
 if not e.get('legacy'):continue
 a=rig.crear(e['id'],e['legacy']['spec'],e['legacy']['colors']);lengths={b.name:b.length for b in a.data.bones}
 used=sorted({x['movimiento'] for x in rows if x['personaje']==e['id']})
 for mid in used:
  m=c['movimientos'][mid];fs=m['fases'];fr=[f['t_fin_frac'] for f in fs];errors=[]
  if not fr or fr[-1]!=1 or any(a>=b for a,b in zip([0]+fr[:-1],fr)):errors.append('phase_fraction_coverage')
  for f in fs:
   angles=c['poses'][f['pose']]['angulos']
   if any(k not in lengths and k!='raiz' for k in angles):errors.append('unknown_native_bone')
   if any(len(v)!=3 or any(not isinstance(q,(float,int)) or not math.isfinite(q) or abs(q)>180 for q in v) for v in angles.values()):errors.append('angular_sanity')
   rig.aplicar(a,angles);bpy.context.view_layer.update()
   err=max(abs((b.tail-b.head).length-lengths[b.name]) for b in a.pose.bones);maximum=max(maximum,err)
   if err>.0001:errors.append('actual_native_rig_length_error')
   if any(not all(math.isfinite(v) for v in list(b.head)+list(b.tail)) for b in a.pose.bones):errors.append('nonfinite_evaluated_native_rig')
   if not f.get('apoyos') or any(s not in lengths for s in f['apoyos']):errors.append('support_bone_missing')
  report.append({'entity':e['id'],'movement':mid,'phases':len(fs),'passed':not errors,'errors':errors})
passed=all(x['passed'] for x in report)
out={'passed':passed,'scope':'REAL_CPU_NATIVE_RIG_POSES_PHASES_SUPPORT_SANITY_ONLY; not scene dynamics, collision, balance, continuity or production approval','checks':report,'unique_used_movements':len({x['movement'] for x in report}),'max_measured_bone_length_error_m':maximum,'model_approval_used':False,'scene_physics_approved':False,'production_approved':False}
(R/'entrega/evidencias/movimientos08_prevalidacion_cpu.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='checks'}))
