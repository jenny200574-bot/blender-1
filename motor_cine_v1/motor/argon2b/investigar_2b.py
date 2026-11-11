"""2B universal: análisis/programación dentro del motor. Preparar es GRATIS.
No hay llamada implícita: --package P --out O [--provisional] sólo genera prompt/esquema.
Respuesta pagada entra por --response JSON; nunca reintenta ni llama escalera.
"""
import json,argparse,hashlib,math
from pathlib import Path
from entrada_universal import contrato,evidencia_2b,leer,guardar
import esqueleto_adn as EA
AQUI=Path(__file__).resolve().parent
ANG={'type':'object','properties':{'hueso':{'type':'string'},'flex':{'type':'number'},'abd':{'type':'number'},'giro':{'type':'number'}},'required':['hueso','flex','abd','giro']}
POSE={'type':'object','properties':{'nombre':{'type':'string'},'descripcion':{'type':'string'},'angulos':{'type':'array','items':ANG},'raiz':{'type':'array','items':{'type':'number'}},'apoyos':{'type':'array','items':{'type':'string'}}},'required':['nombre','descripcion','angulos','raiz','apoyos']}
MOV={'type':'object','properties':{'nombre':{'type':'string'},'descripcion':{'type':'string'},'fases':{'type':'array','items':{'type':'object','properties':{'pose':{'type':'string'},'t_fin_frac':{'type':'number'},'apoyos':{'type':'array','items':{'type':'string'}},'anclar_apoyo':{'type':'boolean'},'desplazamiento_m':{'type':'number'}},'required':['pose','t_fin_frac','apoyos','anclar_apoyo','desplazamiento_m']}},'objetivos':{'type':'array','items':{'type':'object','properties':{'tipo':{'type':'string'},'desde':{'type':'string'},'hacia':{'type':'string'},'t_ini_frac':{'type':'number'},'t_fin_frac':{'type':'number'}},'required':['tipo','desde','hacia','t_ini_frac','t_fin_frac']}},'excepciones':{'type':'object','properties':{'vuela':{'type':'boolean'},'rapido':{'type':'boolean'},'golpe':{'type':'boolean'}},'required':['vuela','rapido','golpe']},'temblor_deg':{'type':'number'},'ciclo_s':{'type':'number'}},'required':['nombre','descripcion','fases','objetivos','excepciones','temblor_deg','ciclo_s']}
ASIG={'type':'object','properties':{'personaje':{'type':'string'},'accion_plan':{'type':'string'},'movimiento':{'type':'string'},'t0':{'type':'number'},'t1':{'type':'number'},'objetivo_punto':{'type':'string'},'capa':{'type':'string','enum':['base','gesto','locomocion']},'huesos':{'type':'array','items':{'type':'string'}}},'required':['personaje','accion_plan','movimiento','t0','t1','objetivo_punto','capa','huesos']}
ESQ={'type':'object','properties':{'poses':{'type':'array','items':POSE},'movimientos':{'type':'array','items':MOV},'asignacion':{'type':'array','items':ASIG},'iniciales':{'type':'array','items':{'type':'object','properties':{'personaje':{'type':'string'},'pose':{'type':'string'}},'required':['personaje','pose']}},'anclas':{'type':'array','items':{'type':'object','properties':{'prop_id':{'type':'string'},'host_id':{'type':'string'},'hueso':{'type':'string'},'formula':{'type':'string'},'cita_fuente':{'type':'string'}},'required':['prop_id','host_id','hueso','formula','cita_fuente']}},'faltantes':{'type':'array','items':{'type':'string'}},'notas':{'type':'string'}},'required':['poses','movimientos','asignacion','iniciales','anclas','faltantes','notas']}
CONV='''Frente +Y, arriba +Z. Angulos [flex,abd,giro] GRADOS relativos al PADRE.
flex+: hombro/cadera/codo adelante; rodilla flexiona hacia atrás; tronco se inclina delante.
abd+: separar hacia su lado. raiz=[pitch adelante+,roll derecha+,yaw] rota cuerpo entero sobre pelvis.
Muslo0/pierna90 = arrodillarse; muslo90/pierna90 NO es arrodillarse erguido.
Root POSICIÓN usa SIEMPRE segmentos originales de01; NO alterar trayectoria, duración ni altura del suelo/levitación.
El motor interpola fases con movimiento_natural, controla velocidad y mide física sin aprobarla a ciegas.'''
GEOM=CONV

def preparar(package,out,provisional=False):
 ctx=contrato(package,provisional);o=Path(out);o.mkdir(parents=True,exist_ok=True);guardar(o/'contrato_motor.json',ctx)
 from investigar_2a import preparar as p2a
 setr=p2a(package,out)
 cat=leer(AQUI/'catalogo_poses/catalogo_poses.json')
 compact={'poses':{n:{'angulos':p['angulos'],'apoyos':p.get('apoyos',[])} for n,p in cat['poses'].items()},'movimientos':cat['movimientos']}
 ev=evidencia_2b(ctx)
 prompt='''Eres el director de animación del MOTOR universal MYIA, PASO2B. Analiza comportamiento, emoción, intención, postura, mirada y desplazamientos de CADA acción y segmento del plan actual. Responde JSON según esquema. No pienses en una escena histórica.
1. Compara primero catálogo. Reutiliza sólo si semántica/estado adecuados; si faltan, PROGRAMA poses/fases genéricas en esta misma respuesta. No necesitas GPU para ángulos; no uses el paso exhausto como caminar alegre.
2. Asignación accion_plan usa EXACTAMENTE action_id de entrada. Cada acción y segmento de actor soportado requiere asignación; ignora sólo PROP y anatomía unsupported. No inventes tiempos; reproduce t0/t1 exactos.
3. Para segmentos caminando/corriendo usa capa locomocion y huesos piernas+brazos de balanceo, ciclo_s0.5..1.2, fases alternas que cierran ciclo. No dejes extremidades quietas sobre root móvil. Para quietud segmental capa base (reposo adecuado, no pisar gestos); para acciones/diálogo capa gesto con huesos relevantes. Una caída/arrodillarse/levantarse afecta raiz y piernas: inclúyelas en huesos. Preferir huesos específicos; [] significa cuerpo completo. Motor combina base → locomocion → gesto, sólo en huesos declarados. Root rutas NO las controla desplazamiento_m (debe0: se usa01).
4. Ciclo_s=0 para gestos no repetidos y poses mantenidas. Para caminar cerrar última fase igual que primera. Fracciones estrictamente crecientes0..1, última1. Al menos4fases por paso. Para gestos repetidos ciclo_s>0. Capa gesto preserva postura tras t1 hasta siguiente gesto, locomoción termina en t1.
5. Emite iniciales para TODOS los actores soportados, derivados del guion al tiempo0 (nunca poner de pie alguien que ya está caído/rodillas). Apoyos deben ser biomecánicamente plausibles. Las medidas provisionales NO se convierten en ADN aprobado.
6. Objetivos mirada con <id>.cabeza/pecho_c o punto de prop y tiempos fraccionales. Todas las cadenas id deben existir. No copiar IDs históricos. Personajes ausentes antes de aparecer pueden tener visibilidad de fuente (motor la respeta).
7. Anclas de props SÓLO con cita textual y host/lado explícitos de la FUENTE. No resolver conflictos; faltantes va en faltantes. Brazalete puede usar fórmula proxy existente brazalete_tecnologico; el motor lo marca proxy técnico, NO activo final aprobado.
8. Economía de salida: JSON COMPLETO es esencial. huesos=[] para cuerpo completo en lugar de repetir todos los huesos. Descripciones cortas; reutiliza poses/movimientos sin duplicarlos. Asigna TODAS las acciones antes de notas largas.
9. Poses angulos lista por hueso; raiz separada. No omitir articulaciones necesarias. Explica faltantes. No apruebes física: el revisor mide después.
'''+'\nCONVENCIÓN\n'+CONV+'\nLÍMITES\n'+json.dumps(EA.LIMITES)+'\nHUESOS POR ACTOR\n'+json.dumps({pid:[b['nombre'] for b in EA.huesos(s)] for pid,s in ctx['specs'].items()})+'\nFUENTE ACTUAL COMPLETA\n'+json.dumps(ev,ensure_ascii=False,separators=(',',':'))+'\nCATÁLOGO ACTUAL\n'+json.dumps(compact,ensure_ascii=False,separators=(',',':'))
 q=o/'prompt_2b.txt'
 if q.exists():
  import shutil,datetime
  shutil.copy2(q,str(q)+'.bak_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
 q.write_text(prompt);guardar(o/'esquema_2b.json',ESQ)
 guardar(o/'estado_2b.json',{'ready':False,'requires_explicit_argon_approval':True,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'free_preflight_can_build':ctx['can_build'] and setr['ready'],'errors':ctx['errors'],'warnings':ctx['warnings'],'no_paid_calls':True})
 return ctx

def ingresar(package,out,response,provisional=False):
 ctx=contrato(package,provisional)
 try:r=leer(response)
 except json.JSONDecodeError:
  from recuperar_2b import prefijo_completo
  r=prefijo_completo(Path(response).read_text())
  if not r.get('poses') or not r.get('movimientos') or not r.get('asignacion'):raise ValueError('Respuesta truncada sin programa utilizable; NO reintentar')
 from recuperar_2b import reutilizar_inequivoco,completar_catalogo_semantico
 reused=reutilizar_inequivoco(ctx,r)+completar_catalogo_semantico(ctx,r)
 cat=leer(AQUI/'catalogo_poses/catalogo_poses.json');issues=[]
 if r.get('_recovery'):issues.append({'recovery':r['_recovery'],'note':'respuesta incompleta; derivaciones sólo técnicas, nunca aprobación'})
 if reused:issues.append({'native_catalog_reuse':reused})
 for key in ['iniciales','anclas','faltantes']:r.setdefault(key,[])
 r.setdefault('notas','Respuesta truncada; sólo elementos completos recuperados por motor sin nueva llamada')
 for p in r['poses']:
  ang={a['hueso']:[a['flex'],a['abd'],a['giro']] for a in p['angulos']};ang['raiz']=p.get('raiz') or [0,0,0]
  if any(len(v)!=3 or not all(isinstance(z,(int,float)) and math.isfinite(z) for z in v) for v in ang.values()):raise ValueError('Ángulos inválidos: '+p['nombre'])
  cat['poses'][p['nombre']]={'angulos':ang,'apoyos':p.get('apoyos',[]),'descripcion':p['descripcion'],'origen':'motor2B Argon t923','validado':False}
 for m in r['movimientos']:
  fs=m['fases'];ts=[f['t_fin_frac'] for f in fs]
  if not ts or any(not(0<t<=1) for t in ts) or any(b<=a for a,b in zip(ts,ts[1:])) or abs(ts[-1]-1)>1e-5:raise ValueError('Fases fuera de contrato: '+m['nombre'])
  if any(f['pose'] not in cat['poses'] for f in fs):raise ValueError('Pose desconocida')
  cat['movimientos'][m['nombre']]={k:v for k,v in m.items() if k!='nombre'};cat['movimientos'][m['nombre']]['validado']=False
 acts={a['action_id']:a for a in ctx['actions']};supported=set(ctx['specs']);asig=[]
 for a in r['asignacion']:
  src=acts.get(a['accion_plan'])
  if not src or a['personaje']!=src['personaje'] or abs(a['t0']-src['t0'])>1e-6 or abs(a['t1']-src['t1'])>1e-6:raise ValueError('Asignación inventa sujeto/tiempo/action_id: '+str(a))
  if a['personaje'] not in supported:issues.append({'unsupported_assignment':a});continue
  if a['movimiento'] not in cat['movimientos']:raise ValueError('Movimiento desconocido')
  a['_source_kind']=src['source_kind'];asig.append(a)
 needed={a['action_id'] for a in ctx['actions'] if a['personaje'] in supported};got={a['accion_plan'] for a in asig};coverage={'needed':len(needed),'covered':len(needed&got),'missing':sorted(needed-got)}
 if coverage['missing']:issues.append({'coverage_incomplete':coverage['missing']})
 initial={a['personaje']:a['pose'] for a in r['iniciales'] if a['personaje'] in supported}
 if r.get('_recovery'):
  for pid in supported-set(initial):
   choices=sorted([a for a in asig if a['personaje']==pid],key=lambda a:a['t0'])
   if choices:
    n=cat['movimientos'][choices[0]['movimiento']]['fases'][0]['pose'];initial[pid]=n;issues.append({'PROVISIONAL_INITIAL_FROM_FIRST_2B_PHASE':{'id':pid,'pose':n,'source_action':choices[0]['accion_plan']},'not_source_approved':True})
 guardar(Path(out)/'respuesta_2b_ingresada.json',r)
 if set(initial)!=supported or any(n not in cat['poses'] for n in initial.values()):raise ValueError('Faltan poses iniciales válidas')
 guardar(Path(out)/'catalogo_poses_escena.json',cat);guardar(Path(out)/'asignacion_movimientos.json',asig);guardar(Path(out)/'programa_2b.json',{'iniciales':initial,'anclas':r['anclas'],'faltantes':r['faltantes'],'notas':r['notas'],'coverage':coverage,'issues':issues,'response_sha256':hashlib.sha256(Path(response).read_bytes()).hexdigest(),'producer':'motor/investigar_2b.py','physics_validated':False})
 return coverage
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--package',required=True);p.add_argument('--out',required=True);p.add_argument('--provisional',action='store_true');p.add_argument('--response');a=p.parse_args()
 print(ingresar(a.package,a.out,a.response,a.provisional) if a.response else {'free':True,'can_build':preparar(a.package,a.out,a.provisional)['can_build']})
