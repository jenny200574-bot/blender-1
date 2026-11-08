"""El SB completo entra al mismo worker; las faltas no se convierten en cámara quieta."""
import sys,copy,runpy
from pathlib import Path
from seguridad import leer,ruta,guardar,error,sha,cuadro
MOVES=set('STATIC TRIPOD DOLLYIN DOLLYOUT PUSH PULL ZOOMIN ZOOMOUT CRASHZOOM PAN TILT ROLL WHIPPAN ORBIT TRUCK PEDESTAL CRANE BOOM TRACK FOLLOW LEAD TRACKSIDE DOLLYZOOM HANDHELD SHOULDER STEADICAM GIMBAL SLIDER'.split())
ENC=set('SINGLE TWOSHOT THREESHOT GROUPSHOT OTS DIRTYOTS CLEANOTS POV EYELEVEL LOWANGLE HIGHANGLE TOPDOWN BIRDSEYE WORMSEYE DUTCH GROUNDLEVEL ELEVATED AERIAL DRONEVIEW LENS SHALLOW DEEPFOCUS FGFOCUS MGFOCUS BGFOCUS RACKFOCUS CENTER SYMMETRY THIRDS LOOKROOM NEGSPACE HEADROOM AXIS CROSSAXIS SCREEN EYELINE SRS MATCHACTION MATCHCUT REACTION CUTAWAY INSERT CINEMATIC'.split())
KEYS=('config','ajustes','commands','sb_scene','elevations','shot_types')

def preparar(d,root):
 c=d.get('camera') or {}
 if not c.get('source'):return {'state':'CANONICAL'},[]
 refs=c.get('resolver_inputs') or {};missing=[k for k in KEYS if not refs.get(k)];errors=[]
 for key in KEYS:
  if key in missing:continue
  asset=next((a for a in d.get('assets',[]) if a['path']==refs[key]),None)
  if not asset or not ruta(root,refs[key]).is_file() or sha(ruta(root,refs[key]))!=asset['sha256']:missing.append(key)
 if missing:errors.append(error('camera/inputs_4g','SB + preparar/configuración 4g','Faltan fuentes por hash: '+', '.join(missing),'CAMARA_DATOS_FALTANTES',causa='camera_inputs'))
 else:
  c['resolver']='SB_4G';config=leer(ruta(root,refs['config']));aj=leer(ruta(root,refs['ajustes']));enc_known=ENC|set(aj['encuadre_fraccion_altura_visible'])|set(config['orientacion_dsl_deg'])|set(config['alturas_hueso'])|set(config['lente_por_clase_mm'])|set(config['rig_suavidad']);commands=leer(ruta(root,refs['commands']));sb=leer(ruta(root,c['source']));shots={v['vineta']:v for v in sb['vinetas']}
  for shot in c['shots']:
   if shot['id'] not in shots:errors.append(error('camera/'+shot['id'],'SB','Toma fuera del SB fuente','CONFLICTO',tipo='conflicto'));continue
   a=commands.get(shot['id'],{}).get('movimiento',[]);b=[[s['t_abs'][0],s['t_abs'][1],s['movimiento'],s.get('args',{})] for s in shots[shot['id']].get('segmentos',[])]
   relative=[[x[0]+shot['t0'],x[1]+shot['t0'],x[2],x[3]] for x in a]
   stamp=lambda rows:[(cuadro(x[0],d['clock']['fps']),cuadro(x[1],d['clock']['fps']),x[2],x[3]) for x in rows]
   for command,args in commands.get(shot['id'],{}).get('encuadre',[]):
    if command not in enc_known:errors.append(error('camera/'+shot['id']+'/'+command,'motor/puente SB-4g','Comando de encuadre sin ejecutor; no se silencia','CAPACIDAD_PENDIENTE',tipo='crear capacidad'))
   for row in b:
    if row[2] not in MOVES:errors.append(error('camera/'+shot['id']+'/'+row[2],'motor/puente SB-4g','Movimiento sin ejecutor; no se convierte en STATIC','CAPACIDAD_PENDIENTE',tipo='crear capacidad'))
   if stamp(a)!=stamp(b) and stamp(relative)!=stamp(b):errors.append(error('camera/'+shot['id']+'/commands','SB','Registro de comandos y tramos del SB difieren; no escoger uno','CONFLICTO',tipo='conflicto'))
 c['_bridge_4g']={'state':'WAITING_DATA' if errors else 'READY'};return c['_bridge_4g'],errors

def construir(scene,d,root,out,objects):
 import bpy
 from objetos_star import FaltaDatos
 c=d['camera'];refs=c['resolver_inputs'];audit=out/'auditoria_4g';audit.mkdir(parents=True,exist_ok=False)
 data=copy.deepcopy(d);data['actors']=[dict(id=e['id'],spec={'altura_m':((e.get('dna_record') or {}).get('source_data') or {}).get('height_m',(e.get('legacy') or {}).get('spec',{}).get('altura_m'))}) for e in d['entities'] if e['type']=='CHARACTER'];data['environment'].pop('visibility',None)
 config=leer(ruta(root,refs['config']));roles=config['roles_hueso']
 for e in d['entities']:
  for bone in (e.get('rig') or {}).get('bones',[]):
   if bone['role']=='head' and bone['id'] not in roles['cabeza']:roles['cabeza'].append(bone['id'])
   if bone['role'] in ['foot.L','foot.R'] and bone['id'] not in roles['pies']:roles['pies'].append(bone['id'])
 guardar(audit/'entrada.json',data);guardar(audit/'config.json',config)
 first=c['shots'][0];width=c.get('sensor_width_mm',first.get('sensor_width_mm'))
 if width is None:raise FaltaDatos('camera/sensor_width_mm','Falta sensor de cámara por dato','SB/configuración cámara')
 cd=bpy.data.cameras.new('camera_4g_sensor');cd.sensor_width=width;cam=bpy.data.objects.new('camera_4g_master',cd);scene.collection.objects.link(cam);scene.camera=cam
 scene.render.resolution_x,scene.render.resolution_y=d['render']['resolution']
 argv=[str(audit/'entrada.json'),str(ruta(root,c['source'])),str(ruta(root,refs['sb_scene'])),str(audit/'config.json'),str(ruta(root,refs['ajustes'])),str(audit),str(ruta(root,refs['commands'])),str(ruta(root,refs['elevations'])),str(ruta(root,refs['shot_types']))];old=sys.argv
 try:sys.argv=['resolver_4g','--']+argv;namespace=runpy.run_path(str(Path(__file__).with_name('camara_v2_blender.py')),run_name='__motor_sb4g__')
 finally:sys.argv=old
 report=leer(audit/'camara_v2.json');unsupported=[(t['vineta'],v['comando']) for t in report['tomas'] for v in t.get('comandos',[]) if v['estado']=='no_programado']
 if unsupported:raise ValueError('Comandos con capacidad pendiente (no se silencian): '+str(unsupported))
 missing=[(t['vineta'],v['comando'],v.get('detalle')) for t in report['tomas'] for v in t.get('comandos',[]) if v['estado']=='falta_dato']
 if missing or report['faltantes']:raise FaltaDatos('camera/source_commands','SB/02N + ADN/4a2: '+str(missing)+' / '+str(report['faltantes']),'SB/02N + 4a2/ADN')
 errors=[{'type':'CAMARA_4G','shot':t['vineta'],'details':t['motivos']} for t in report['tomas'] if t['estado']!='pasa'];cams={}
 for s in c['shots']:
  ob=cam.copy();ob.data=cam.data.copy();ob.name=s['id']+'_camera';scene.collection.objects.link(ob);cams[s['id']]=ob
 return cams,{'frames_checked':sum(t['frame_fin']-t['frame_ini']+1 for t in report['tomas']),'all_passed':not errors,'errors':errors,'resolver':'SB_4G','full_command_report':'auditoria_4g/camara_v2.json','all_frames':True}
