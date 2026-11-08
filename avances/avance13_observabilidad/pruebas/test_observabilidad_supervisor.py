#!/usr/bin/env python3
"""Pruebas OFFLINE del supervisor operativo parchado, con hijos simulados.

No ejecuta motor_unico, constructor, Blender, GPU, n8n, APIs ni rutas VPS.
"""
import hashlib,importlib.util,json,os,shutil,signal,sys,tempfile,threading,time,unittest,uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ORIG=ROOT/'original'/'artefactos'/'supervisor_oro_constructor.py'
PARCHE=ROOT/'paquete_operativo'/'supervisor_oro_constructor.py'
APLICAR=ROOT/'paquete_operativo'/'aplicar_observabilidad.py'
HIJO=ROOT/'pruebas'/'hijos_simulados.py'
SHA_ORIG='129187406f4381fb7740e561e7835336211590e5aaf5ef2b92b1559ea5e87c85'
ESTADO_HIST=ROOT/'original'/'artefactos'/'secuencia_estado.json'
PY=sys.executable

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def cargar(raiz,off=False,prueba=True):
 os.environ['MYIA_SUPERVISOR_RAIZ']=str(raiz)
 os.environ.pop('MYIA_SUPERVISOR_SIMULACION',None)
 os.environ.pop('MYIA_SUPERVISOR_SOLO_RECUPERAR',None)
 if prueba:os.environ['MYIA_SUPERVISOR_PRUEBA_HIJO']='1'
 else:os.environ.pop('MYIA_SUPERVISOR_PRUEBA_HIJO',None)
 if off:
  (raiz/'operaciones'/'observabilidad_cierre.off').write_text('off\n')
 else:
  p=raiz/'operaciones'/'observabilidad_cierre.off'
  if p.exists():p.unlink()
 name='sup_'+uuid.uuid4().hex
 spec=importlib.util.spec_from_file_location(name,PARCHE)
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 return mod

def sandbox():
 tmp=Path(tempfile.mkdtemp(prefix='obs13_'))
 ops=tmp/'operaciones';ops.mkdir(parents=True)
 m=tmp/'MOTOR_BVH08_CANDIDATO'
 (m/'config').mkdir(parents=True)
 (m/'motor').mkdir(parents=True)
 (m/'config'/'argon_recetas.off').write_text('off\n')
 (m/'config'/'politica_ejecucion.json').write_text('{"argon_automatico":false}\n')
 (m/'motor'/'fisica_final.py').write_text('# dummy prueba; no es la física VPS\n')
 return tmp

def argv(*args):
 return [PY,'-B',str(HIJO),*args]

def estado(raiz):
 return json.loads((raiz/'operaciones'/'secuencia_estado.json').read_text())

def env_base(raiz,extra=None):
 e=os.environ.copy()
 e['MYIA_SUPERVISOR_RAIZ']=str(raiz)
 e['MYIA_SUPERVISOR_PRUEBA_HIJO']='1'
 e['PYTHONDONTWRITEBYTECODE']='1'
 e.pop('MYIA_SUPERVISOR_SOLO_RECUPERAR',None)
 if extra:e.update(extra)
 return e

class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.assertEqual_sha=None
  h=sha(ORIG)
  if h!=SHA_ORIG:
   raise AssertionError('original alterado %s'%h)

 def tearDown(self):
  os.environ.pop('MYIA_SUPERVISOR_RAIZ',None)
  os.environ.pop('MYIA_SUPERVISOR_SIMULACION',None)
  os.environ.pop('MYIA_SUPERVISOR_SOLO_RECUPERAR',None)
  os.environ.pop('MYIA_SUPERVISOR_PRUEBA_HIJO',None)

 def test_00_original_bit_identico_y_no_en_motor(self):
  self.assertEqual(sha(ORIG),SHA_ORIG)
  self.assertEqual(ORIG.stat().st_size,3439)
  self.assertNotEqual(sha(PARCHE),SHA_ORIG)
  self.assertFalse((Path('/workspace')/'motor'/'supervisor_oro_constructor.py').exists())
  src=ORIG.read_text()
  self.assertIn('subprocess.Popen',src)
  self.assertIn('secuencia_estado.json',src)
  self.assertIn("run('CONSTRUCTOR'",src)

 def test_01_hijo_exito_estado_terminal_y_logs(self):
  raiz=sandbox();mod=cargar(raiz)
  rc=mod.run('CONSTRUCTOR',argv('ok'),raiz/'operaciones'/'hijo.log')
  self.assertEqual(rc,0)
  st=estado(raiz)
  self.assertEqual(st['constructor_exitcode'],0)
  self.assertIsNone(st['constructor_signal'])
  self.assertEqual(st['constructor_returncode'],0)
  self.assertEqual(st['state'],'RUNNING')
  self.assertTrue(st.get('run_id'))
  self.assertTrue(st.get('boot_id'))
  self.assertTrue(st.get('worker_pid'))
  raw=(raiz/'operaciones'/'hijo.log').read_text()
  self.assertIn('hijo_ok stdout',raw)
  stamp=(raiz/'operaciones'/'hijo.log.stamp').read_text()
  self.assertIn('hijo_ok stdout',stamp)
  self.assertIn(' | stdout | ',stamp)
  self.assertRegex(stamp,r'\d{4}-\d{2}-\d{2}T')

 def test_02_error_stderr_traceback_conservado(self):
  raiz=sandbox();mod=cargar(raiz)
  rc=mod.run('CONSTRUCTOR',argv('stderr_tb'),raiz/'operaciones'/'hijo.log')
  self.assertEqual(rc,1)
  st=estado(raiz)
  self.assertEqual(st['constructor_exitcode'],1)
  self.assertIsNone(st['constructor_signal'])
  err=(raiz/'operaciones'/'hijo.log.stderr').read_bytes()
  self.assertIn(b'Traceback (most recent call last):',err)
  self.assertIn(b'error_simulado_observabilidad',err)
  stamp=(raiz/'operaciones'/'hijo.log.stamp').read_text()
  self.assertIn('Traceback (most recent call last):',stamp)
  self.assertIn('error_simulado_observabilidad',stamp)
  self.assertIn(' | stderr | ',stamp)

 def test_03_salida_no_cero(self):
  raiz=sandbox();mod=cargar(raiz)
  rc=mod.run('CONSTRUCTOR',argv('exit','7'),raiz/'operaciones'/'hijo.log')
  self.assertEqual(rc,7)
  st=estado(raiz)
  self.assertEqual(st['constructor_exitcode'],7)
  self.assertEqual(st['constructor_returncode'],7)
  self.assertIsNone(st['constructor_signal'])

 def test_04_senal_sigterm(self):
  raiz=sandbox();mod=cargar(raiz)
  log=raiz/'operaciones'/'hijo.log'
  box={'rc':None,'err':None}
  def go():
   try:box['rc']=mod.run('CONSTRUCTOR',argv('signal'),log)
   except Exception as e:box['err']=e
  t=threading.Thread(target=go);t.start()
  pid=None
  for _ in range(50):
   p=raiz/'operaciones'/'secuencia_estado.json'
   if p.exists():
    st=json.loads(p.read_text())
    if st.get('worker_pid') and st.get('state')=='RUNNING':
     pid=st['worker_pid'];break
   time.sleep(0.05)
  self.assertTrue(pid)
  os.kill(pid,signal.SIGTERM);t.join(timeout=10)
  self.assertIsNone(box['err'])
  self.assertEqual(box['rc'],-signal.SIGTERM)
  st=estado(raiz)
  self.assertEqual(st['constructor_signal'],signal.SIGTERM)
  self.assertIsNone(st['constructor_exitcode'])
  self.assertEqual(st['constructor_returncode'],-signal.SIGTERM)

 def test_05_hijo_silencioso(self):
  raiz=sandbox();mod=cargar(raiz)
  rc=mod.run('ORO',argv('silencio'),raiz/'operaciones'/'oro.log')
  self.assertEqual(rc,0)
  st=estado(raiz)
  self.assertEqual(st['oro_exitcode'],0)
  self.assertEqual((raiz/'operaciones'/'oro.log').stat().st_size,0)
  self.assertTrue((raiz/'operaciones'/'oro.log.stderr').exists())
  self.assertTrue((raiz/'operaciones'/'oro.log.stamp').exists())

 def test_06_boot_distinto_sin_false_positive_vivo(self):
  raiz=sandbox();mod=cargar(raiz)
  hist=json.loads(ESTADO_HIST.read_text())
  hist=dict(hist);hist['boot_id']='00000000-0000-0000-0000-000000000000'
  hist['run_id']='hist_boot_distinto'
  (raiz/'operaciones'/'secuencia_estado.json').write_text(json.dumps(hist,indent=2))
  r=mod.recuperar_running()
  self.assertEqual(r['accion'],'marcado')
  self.assertEqual(r['cierre'],'RUNNING_BOOT_ANTERIOR_SIN_CIERRE')
  st=estado(raiz)
  self.assertEqual(st['state'],'INTERRUMPIDO_SIN_CIERRE')
  self.assertIs(st['causa_inventada'],False)
  self.assertIsNone(st['returncode'])
  self.assertNotIn('failure',st)
  self.assertNotEqual(st.get('cierre'),'TypeError')
  arch=list((raiz/'operaciones'/'archivo').rglob('secuencia_estado.json'))
  self.assertTrue(arch)
  prev=json.loads(arch[0].read_text())
  self.assertEqual(prev['state'],'RUNNING')
  self.assertEqual(prev['constructor_pid'],19474)

 def test_07_mismo_boot_pid_vivo_no_interrumpe(self):
  raiz=sandbox();mod=cargar(raiz)
  proc=__import__('subprocess').Popen([PY,'-B',str(HIJO),'signal'],stdout=__import__('subprocess').DEVNULL,stderr=__import__('subprocess').DEVNULL)
  try:
   st={'state':'RUNNING','phase':'CONSTRUCTOR','returncode':None,'worker_pid':proc.pid,'constructor_pid':proc.pid,'boot_id':mod._boot_id(),'worker_starttime':mod._starttime(proc.pid),'run_id':'vivo'}
   (raiz/'operaciones'/'secuencia_estado.json').write_text(json.dumps(st,indent=2))
   r=mod.recuperar_running()
   self.assertEqual(r['accion'],'intacta')
   self.assertEqual(estado(raiz)['state'],'RUNNING')
  finally:
   proc.send_signal(signal.SIGTERM);proc.wait(timeout=5)

 def test_08_mismo_boot_pid_muerto_sin_atribuir_reboot(self):
  raiz=sandbox();mod=cargar(raiz)
  st={'state':'RUNNING','phase':'CONSTRUCTOR','returncode':None,'worker_pid':999999,'constructor_pid':999999,'boot_id':mod._boot_id(),'run_id':'muerto'}
  (raiz/'operaciones'/'secuencia_estado.json').write_text(json.dumps(st,indent=2))
  r=mod.recuperar_running()
  self.assertEqual(r['cierre'],'PID_AUSENTE_SIN_EVENTO_TERMINAL')
  self.assertEqual(estado(raiz)['state'],'INTERRUMPIDO_SIN_CIERRE')
  self.assertIs(estado(raiz)['causa_inventada'],False)

 def test_09_preserva_evidencia_historica_y_terminal(self):
  raiz=sandbox();mod=cargar(raiz)
  raw=ESTADO_HIST.read_bytes()
  (raiz/'operaciones'/'secuencia_estado.json').write_bytes(raw)
  self.assertEqual(sha(raiz/'operaciones'/'secuencia_estado.json'),sha(ESTADO_HIST))
  r=mod.recuperar_running()
  self.assertEqual(r['accion'],'marcado')
  arch=list((raiz/'operaciones'/'archivo').rglob('secuencia_estado.json'))
  self.assertEqual(arch[0].read_bytes(),raw)
  fin={'state':'FINISHED','returncode':0,'run_id':'ya_cerrado','phase':'CONSTRUCTOR'}
  (raiz/'operaciones'/'secuencia_estado.json').write_text(json.dumps(fin,indent=2))
  r2=mod.recuperar_running()
  self.assertEqual(r2['accion'],'conservado')
  self.assertEqual(estado(raiz)['state'],'FINISHED')
  self.assertEqual(estado(raiz)['returncode'],0)

 def test_10_no_exito_falso_si_registro_falla(self):
  raiz=sandbox();mod=cargar(raiz)
  n={'n':0};real=mod.save
  def boom():
   n['n']+=1
   if n['n']>=2:raise OSError('disco_simulado')
   return real()
  mod.save=boom
  with self.assertRaises(OSError):
   mod.run('CONSTRUCTOR',argv('ok'),raiz/'operaciones'/'hijo.log')
  st=estado(raiz)
  self.assertNotEqual(st.get('constructor_exitcode'),0)
  self.assertEqual(st['state'],'RUNNING')

 def test_11_off_no_anota_boot_ni_stamp_y_bloquea_recuperacion(self):
  raiz=sandbox();mod=cargar(raiz,off=True)
  rc=mod.run('CONSTRUCTOR',argv('ok'),raiz/'operaciones'/'hijo.log')
  self.assertEqual(rc,0)
  st=estado(raiz)
  self.assertNotIn('boot_id',st)
  self.assertNotIn('constructor_signal',st)
  self.assertEqual(st['constructor_returncode'],0)
  self.assertFalse((raiz/'operaciones'/'hijo.log.stamp').exists())
  self.assertIn('hijo_ok stdout',(raiz/'operaciones'/'hijo.log').read_text())
  hist=json.loads(ESTADO_HIST.read_text())
  (raiz/'operaciones'/'secuencia_estado.json').write_text(json.dumps(hist,indent=2))
  r=mod.recuperar_running()
  self.assertEqual(r['accion'],'apagado')
  self.assertFalse(r['ok'])
  self.assertEqual(json.loads((raiz/'operaciones'/'secuencia_estado.json').read_text())['state'],'RUNNING')

 def test_12_script_completo_simulacion_sin_blender(self):
  raiz=sandbox()
  plan={'fases':[
   {'nombre':'ORO','argv':argv('ok'),'log':'oro_tipoerror.log'},
   {'nombre':'CONSTRUCTOR','argv':argv('stderr_tb'),'log':'constructor_tipoerror.log'}
  ],'exigir_oro_cero':False}
  pf=raiz/'operaciones'/'simulacion.json';pf.write_text(json.dumps(plan))
  e=env_base(raiz,{'MYIA_SUPERVISOR_SIMULACION':str(pf)})
  r=__import__('subprocess').run([PY,'-B',str(PARCHE)],cwd=str(raiz),env=e,capture_output=True,text=True,timeout=20)
  self.assertEqual(r.returncode,0,r.stderr)
  st=estado(raiz)
  self.assertEqual(st['state'],'FAILED')
  self.assertEqual(st['constructor_exitcode'],1)
  self.assertEqual(st['oro_exitcode'],0)
  self.assertTrue(st.get('boot_id'))
  self.assertIn('error_simulado_observabilidad',(raiz/'operaciones'/'constructor_tipoerror.log.stderr').read_text())
  self.assertTrue(st.get('finished_bogota'))
  self.assertNotIn('/opt/blender',(raiz/'operaciones'/'constructor_tipoerror.log.stamp').read_text())

 def test_13_no_autorelanzar_y_guarda_fisica(self):
  src=PARCHE.read_text()
  self.assertNotIn('reintent',src.lower())
  self.assertIn('3423c9a777eb0157d49eb90869f39227fb7cf834322e2705a605a37a66d418d2',src)
  self.assertIn("PRUEBA_HIJO no ejecuta oro/constructor reales",src)
  raiz=sandbox();mod=cargar(raiz,prueba=False)
  with self.assertRaises(AssertionError):
   mod.run('ORO',argv('ok'),raiz/'operaciones'/'x.log')

 def test_14_aplicar_falla_cambio_ajeno_y_respaldos(self):
  raiz=sandbox()
  dest=raiz/'operaciones'/'supervisor_oro_constructor.py'
  shutil.copy2(ORIG,dest)
  self.assertEqual(sha(dest),SHA_ORIG)
  alien=dest.with_name('alien.py');alien.write_text('print(1)\n')
  r=__import__('subprocess').run([PY,'-B',str(APLICAR),'--destino',str(alien)],capture_output=True,text=True)
  self.assertEqual(r.returncode,3)
  self.assertIn('CAMBIO_AJENO_NO_FORZAR',r.stdout)
  self.assertEqual(alien.read_text(),'print(1)\n')
  r2=__import__('subprocess').run([PY,'-B',str(APLICAR),'--destino',str(dest)],capture_output=True,text=True)
  self.assertEqual(r2.returncode,0,r2.stdout+r2.stderr)
  info=json.loads(r2.stdout)
  self.assertEqual(info['estado'],'aplicado_con_off')
  self.assertEqual(sha(dest),sha(PARCHE))
  self.assertEqual(sha(info['respaldo']),SHA_ORIG)
  self.assertTrue(Path(info['off']).is_file())
  r3=__import__('subprocess').run([PY,'-B',str(APLICAR),'--destino',str(dest),'--solo-verificar'],capture_output=True,text=True)
  self.assertEqual(json.loads(r3.stdout)['estado'],'parche_ya_aplicado')

 def test_15_recuperar_por_cli_no_relanza(self):
  raiz=sandbox()
  hist=json.loads(ESTADO_HIST.read_text())
  hist['boot_id']='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
  (raiz/'operaciones'/'secuencia_estado.json').write_text(json.dumps(hist,indent=2))
  e=env_base(raiz,{'MYIA_SUPERVISOR_SOLO_RECUPERAR':'1'})
  r=__import__('subprocess').run([PY,'-B',str(PARCHE)],cwd=str(raiz),env=e,capture_output=True,text=True,timeout=10)
  self.assertEqual(r.returncode,0,r.stderr)
  out=json.loads(r.stdout)
  self.assertEqual(out['cierre'],'RUNNING_BOOT_ANTERIOR_SIN_CIERRE')
  self.assertEqual(estado(raiz)['state'],'INTERRUMPIDO_SIN_CIERRE')
  self.assertNotIn('motor_unico.py',r.stdout)

 def test_16_contratos_seguridad_sin_rutas_vps_en_prueba(self):
  raiz=sandbox();mod=cargar(raiz)
  mod.run('CONSTRUCTOR',argv('ok'),raiz/'operaciones'/'hijo.log')
  st=estado(raiz)
  self.assertNotIn('/opt/myia-motor-v9',st['log'])
  self.assertNotIn('/opt/blender',json.dumps(st.get('command')))
  pol=json.loads((raiz/'MOTOR_BVH08_CANDIDATO'/'config'/'politica_ejecucion.json').read_text())
  self.assertIs(pol['argon_automatico'],False)
  self.assertTrue((raiz/'MOTOR_BVH08_CANDIDATO'/'config'/'argon_recetas.off').is_file())
  self.assertIn('argon_automatico',PARCHE.read_text())

 def test_17_corridas_concurrentes_no_pisan_estado(self):
  raiz=sandbox()
  plan1={'fases':[{'nombre':'CONSTRUCTOR','argv':argv('signal'),'log':'a.log'}]}
  plan2={'fases':[{'nombre':'ORO','argv':argv('ok'),'log':'b.log'}]}
  (raiz/'operaciones'/'p1.json').write_text(json.dumps(plan1))
  (raiz/'operaciones'/'p2.json').write_text(json.dumps(plan2))
  sp=__import__('subprocess')
  p1=sp.Popen([PY,'-B',str(PARCHE)],cwd=str(raiz),env=env_base(raiz,{'MYIA_SUPERVISOR_SIMULACION':str(raiz/'operaciones'/'p1.json')}),stdout=sp.PIPE,stderr=sp.PIPE,text=True)
  pid=None
  for _ in range(80):
   f=raiz/'operaciones'/'secuencia_estado.json'
   if f.exists():
    st=json.loads(f.read_text())
    if st.get('state')=='RUNNING' and st.get('worker_pid'):
     pid=st['worker_pid'];break
   time.sleep(0.05)
  self.assertTrue(pid)
  p2=sp.run([PY,'-B',str(PARCHE)],cwd=str(raiz),env=env_base(raiz,{'MYIA_SUPERVISOR_SIMULACION':str(raiz/'operaciones'/'p2.json')}),capture_output=True,text=True,timeout=15)
  txt=p2.stdout+p2.stderr
  self.assertTrue('SAVE_OMITIDO_ESTADO_AJENO' in txt or 'CORRIDA_CONCURRENTE' in txt,txt)
  st=estado(raiz)
  self.assertEqual(st['state'],'RUNNING')
  self.assertEqual(st['worker_pid'],pid)
  self.assertNotEqual(st.get('state'),'FINISHED')
  os.kill(pid,signal.SIGTERM)
  p1.communicate(timeout=10)

if __name__=='__main__':
 unittest.main(verbosity=2)
