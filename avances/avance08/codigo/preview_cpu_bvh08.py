import sys,json,hashlib,os,subprocess,shutil,collections,copy,threading
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
R=Path('/opt/myia-motor-v9/avance08_20261107');E=R/'entrega';M=R/'MOTOR_BVH08_CANDIDATO';O=R/'preview_cpu_bvh08';core=R/'preview_cpu08/nucleo/escena.blend';sys.path.insert(0,str(M/'motor'))
from seguridad import guardar,sha
from montaje_cpu import planificar,ejecutar as montar
read=lambda p:json.loads(p.read_text());now=lambda:datetime.now(ZoneInfo('America/Bogota')).isoformat()
assert not O.exists();assert read(E/'evidencias/reuso_nucleo08_precondiciones.json')['passed']
assert read(E/'evidencias/preflight_bvh08.json')['faltantes']==0
module_hash=sha(M/'motor/fisica_final.py');assert read(E/'evidencias/bvh08_regresion11.json')['module_sha256']==module_hash and read(E/'evidencias/colision_estatica08_final.json')['module_sha256']==module_hash
assert read(E/'evidencias/bvh08_regresion11.json')['passed'];assert read(E/'evidencias/colision_estatica08_final.json')['all_passed']
assert read(E/'evidencias/oro_bvh08_codigo_vinculado.json')['code']['motor/fisica_final.py']==module_hash
gold=read(R/'oro_bvh08_final/metricas_oro.json');assert gold['all_equal'] and gold['count']==23
assert (E/'config/generador.off').exists() and (M/'config/argon_recetas.off').exists() and not read(M/'config/politica_ejecucion.json')['argon_automatico']
core_receipt=read(core.parent/'nucleo_resultado.json');assert core_receipt['estado']=='SOLO_BACKEND_FISICO' and core_receipt['frames']==1320
assert 'NUCLEO_FISICO_TERMINADO' in (R/'preview_cpu08/nucleo.log').read_text(errors='replace')
core_hash=sha(core);ledger=E/'evidencias/ledger.json';ledger_hash=sha(ledger);O.mkdir();shutil.copytree(R/'preflight_bvh08/paquete_normalizado',O/'paquete_normalizado');pk=O/'paquete_normalizado';d=read(pk/'entrada_escena.json')
reuse={'date_bogota':now(),'core':str(core),'core_sha256':core_hash,'frames':core_receipt['frames'],'preconditions_sha256':sha(E/'evidencias/reuso_nucleo08_precondiciones.json'),'native_entry':'constructor_final.py documented optional third argument','no_bake_reconstruction_or_substitution':True,'scene_approved':False};guardar(O/'reuso_nucleo.json',reuse)
summary={'date_bogota':now(),'estado':'EN_EJECUCION','errores':[],'master':None,'gpu_used':False,'paid_calls':0,'ledger_unchanged':True,'full_cpu_preview_passed':False,'production_approved':False,'scope':'Native preflight + immutable completed native core + unmodified constructor_final/render_cpu/montaje_cpu; only final fisica_final module is corrected in isolated engine copy','output':str(O),'core_reused':True,'scene_physics_review_completed':False}
guardar(O/'resultado.json',summary)
env=dict(os.environ,LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',MESA_LOADER_DRIVER_OVERRIDE='llvmpipe',EGL_PLATFORM='surfaceless',MOTOR_UNICO_CPU_PRUEBA='1');blender='/opt/blender/actual/blender'
heartbeat_stop=threading.Event();phase='native_constructor'
def heartbeat():
 while not heartbeat_stop.wait(60):print(json.dumps({'process_alive':True,'phase':phase,'date_bogota':now()}),flush=True)
threading.Thread(target=heartbeat,daemon=True).start()
try:
 with (O/'constructor.log').open('w') as log:
  proc=subprocess.run([blender,'-b','--disable-autoexec','-t','2','--python-exit-code','17','-P',str(M/'motor/constructor_final.py'),'--',str(pk),str(O),str(core)],stdout=log,stderr=subprocess.STDOUT,timeout=7200,env=env)
 summary['constructor_exit_code']=proc.returncode;w=read(O/'worker_resultado.json') if (O/'worker_resultado.json').exists() else {}
 revision=read(O/'revision_final.json') if (O/'revision_final.json').exists() else None
 if revision:
  summary['scene_physics_review_completed']=True;summary['frames_reviewed']=revision['frames'];summary['metrics']={k:revision[k] for k in ['max_bone_length_error_m','max_contact_error_m','root_speed_max_m_s','root_accel_max_m_s2']};summary['physics_metrics']={k:v for k,v in revision['physics'].items() if k not in ['errors','com_trace','locked_naturalness_trace']}
 raw=revision['errors'] if revision else w.get('errores',[])
 grouped={}
 for er in raw:
  kind=str(er.get('type',er.get('codigo','NATIVE_REJECT')));subject=str(er.get('objects',er.get('shot',er.get('toma',''))));key=(kind,str(er.get('entity','')),subject)
  row=grouped.setdefault(key,{'codigo':key[0],'campo':'/'.join(q for q in key[1:] if q),'modulo':'Native final scene gate','mensaje':json.dumps(er,ensure_ascii=False),'ocurrencias':0,'first_frame':er.get('frame'),'raw_evidence':'revision_final.json' if revision else 'worker_resultado.json'})
  row['ocurrencias']+=1
 summary['native_raw_error_count']=len(raw);summary['errores']=list(grouped.values())
 if proc.returncode!=0 or w.get('estado')!='CONSTRUIDO_REVISADO' or not revision or not revision['all_passed']:
  summary['estado']='BLOQUEADO';summary['errores'].append({'codigo':w.get('codigo','CONSTRUCTOR_O_REVISION'),'campo':'execution/final_scene_gate','modulo':'Native constructor','mensaje':w.get('mensaje','Constructor did not issue reviewed artifact'),'ocurrencias':1})
 else:
  summary['scene_physics_review_passed']=True
  # CPU preview uses the EXISTING diagnostic preset, not invented scene values.
  preset=read(M/'config/preset_cpu.json');rd=copy.deepcopy(d);original_render=copy.deepcopy(d['render']);rd['render'].update(engine=preset['engine'],seed=preset['seed'],resolution=preset['diagnostic_resolution'],samples=preset['diagnostic_samples'])
  assert original_render['resolution'][0]*rd['render']['resolution'][1]==original_render['resolution'][1]*rd['render']['resolution'][0]
  render_pk=O/'paquete_preview_cpu';shutil.copytree(pk,render_pk);guardar(render_pk/'entrada_escena.json',rd)
  summary['cpu_render_preset']={'proxy_only':True,'source':'config/preset_cpu.json','source_sha256':sha(M/'config/preset_cpu.json'),'resolution':rd['render']['resolution'],'samples':rd['render']['samples'],'seed':rd['render']['seed'],'production_render_preserved':original_render,'render_entry_sha256':sha(render_pk/'entrada_escena.json')}
  phase='native_cpu_proxy_render'
  with (O/'render.log').open('w') as log:
   proc=subprocess.run([blender,'-b','--disable-autoexec',str(O/'escena.blend'),'-t','2','--python-exit-code','17','-P',str(M/'motor/render_cpu.py'),'--',str(render_pk),str(O)],stdout=log,stderr=subprocess.STDOUT,timeout=7200,env=env)
  if proc.returncode:raise RuntimeError('Native CPU render failed; master not assembled')
  clips=read(O/'clips.json');fps=d['clock']['fps'];dur=d['clock']['duration_s'];plan=planificar(d['camera']['shots'],fps,dur,d['camera'].get('transition_semantics','outgoing'));video=montar([O/z['file'] for z in clips],plan,fps,rd['render']['resolution'],dur,[],render_pk,O/'entrega');summary.update(estado='COMPLETO',master=video['path'],full_cpu_preview_passed=True)
except Exception as exc:
 summary['estado']='BLOQUEADO';summary['errores'].append({'codigo':type(exc).__name__,'campo':'execution/cached_native_preview','modulo':'AV08 native wrapper','mensaje':str(exc),'ocurrencias':1})
finally:
 heartbeat_stop.set()
 summary['module_sha256']=module_hash;summary['module_unchanged']=sha(M/'motor/fisica_final.py')==module_hash;summary['ledger_unchanged']=sha(ledger)==ledger_hash;summary['core_unchanged']=sha(core)==core_hash;summary['date_bogota']=now();summary['faltantes_o_errores']=len(summary['errores'])
 assert summary['core_unchanged'] and summary['ledger_unchanged'] and summary['module_unchanged']
 code=[{'path':str(p.relative_to(M)),'sha256':sha(p)} for p in sorted((M/'motor').rglob('*.py')) if '__pycache__' not in p.parts]
 guardar(O/'worker_manifiesto.json',{'mode':'CPU','gpu_authorized':False,'entry_sha256':sha(R/'esc1_bvh08/entrada_escena.json'),'normalized_entry_sha256':sha(pk/'entrada_escena.json'),'core_sha256':core_hash,'code':code,'same_code_required':True,'cpu_preview_entry_sha256':sha(O/'paquete_preview_cpu/entrada_escena.json') if (O/'paquete_preview_cpu/entrada_escena.json').exists() else None,'scene_sha256':sha(O/'escena.blend') if (O/'escena.blend').exists() else None})
 guardar(O/'resultado.json',summary);guardar(E/'evidencias/preview_cpu_bvh08_resultado.json',summary);print(json.dumps(summary,ensure_ascii=False),flush=True)
