import pathlib,json,subprocess,os,time,datetime,shutil,hashlib,traceback
s=pathlib.Path('/opt/myia-motor-v9/avance13_20261108_tipoerror');m=s/'MOTOR_BVH08_CANDIDATO';ops=s/'operaciones';status=ops/'secuencia_estado.json';now=lambda:datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-5))).isoformat();start=time.monotonic()
x={'supervisor_pid':os.getpid(),'started_bogota':now(),'state':'STARTING','phase':'GATES','returncode':None,'free_before':shutil.disk_usage(s).free}
def save():
 p=status.with_suffix('.partial');p.write_text(json.dumps(x,ensure_ascii=False,indent=2));os.replace(p,status)
def guard():
 assert shutil.disk_usage(s).free>=2*1024**3
 assert (m/'config/argon_recetas.off').is_file()
 assert json.loads((m/'config/politica_ejecucion.json').read_text()).get('argon_automatico') is False
 assert hashlib.sha256((m/'motor/fisica_final.py').read_bytes()).hexdigest()=='3423c9a777eb0157d49eb90869f39227fb7cf834322e2705a605a37a66d418d2'
def run(phase,a,log,extra=None):
 guard();assert not log.exists();env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
 if extra:env.update(extra)
 with log.open('xb') as f:
  p=subprocess.Popen(a,cwd=s,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,env=env)
  x.update({'state':'RUNNING','phase':phase,'worker_pid':p.pid,'command':a,'log':str(log),'phase_started_bogota':now()});x[phase.lower()+'_pid']=p.pid;save();rc=p.wait()
 x[phase.lower()+'_returncode']=rc;save();return rc
try:
 assert not status.exists() and not (s/'oro_tipoerror').exists() and not (s/'rebuild_tipoerror').exists()
 a=['/usr/bin/python3',str(m/'motor_unico.py'),str(s/'entradas/oro/entrada_escena.json'),'--salida',str(s/'oro_tipoerror'),'--regresion','--blender','/opt/blender/actual/blender','--referencia',str(s/'entradas/revisor_comparable.json')]
 rc=run('ORO',a,ops/'oro_tipoerror.log');assert rc==0,'ORO_EXIT_NO_CERO'
 metrics=json.loads((s/'oro_tipoerror/metricas_oro.json').read_text());x['oro_metrics']={'count':metrics['count'],'all_equal':metrics['all_equal'],'checks':len(metrics['checks'])}
 assert metrics['count']==23 and metrics['all_equal'] is True and len(metrics['checks'])==23 and all(v['equal'] is True for v in metrics['checks']),'ORO_NO_IDENTICO'
 x['oro_pass_bogota']=now();save()
 core=s/'nucleo_reutilizable/escena.blend';assert hashlib.sha256(core.read_bytes()).hexdigest()=='353c8ae47fe0bd9c435adc5a647d85786513932a900407ac9219526c467d8a2e'
 receipt=json.loads(core.with_name('compatibilidad_nucleo.json').read_text());assert all(hashlib.sha256((m/k).read_bytes()).hexdigest()==v for k,v in receipt['codigo'].items())
 a=['/opt/blender/actual/blender','-b','--disable-autoexec','-t','2','--python-exit-code','17','-P',str(m/'motor/constructor_final.py'),'--',str(s/'preflight_av11/paquete_normalizado'),str(s/'rebuild_tipoerror'),str(core)]
 extra={'SONDA_CAMARA':'1','SONDA_ACTOR':'ch-pintor-bce0','SONDA_FRAMES':'433,468,504,601,660,720','SONDA_SALIDA':str(s/'sonda_tipoerror.json')};x['sonda_environment']=extra;save()
 rc=run('CONSTRUCTOR',a,ops/'constructor_tipoerror.log',extra);x.update({'returncode':rc,'state':'FINISHED' if rc==0 else 'FAILED'})
except BaseException as e:
 x.update({'state':'FAILED','failure':str(e)});traceback.print_exc()
finally:
 x.update({'finished_bogota':now(),'elapsed_seconds':round(time.monotonic()-start,3),'free_after':shutil.disk_usage(s).free});save()
print(json.dumps(x,ensure_ascii=False,indent=2),flush=True)
