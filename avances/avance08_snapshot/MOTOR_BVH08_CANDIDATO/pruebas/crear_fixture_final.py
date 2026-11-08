"""DATOS SINTÉTICOS DECLARADOS para probar APIs, NO diseño Guardianes ni ADN aprobado."""
import sys,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'motor'));from seguridad import guardar,sha
pk=R/'paquetes'/'fixture_aviar_integracion';pk.mkdir(exist_ok=False)
source='fixture_sintetico.json';bones=[]
def bone(id,head,tail,parent,role):bones.append({'id':id,'head':head,'tail':tail,'parent':parent,'role':role,'limits_deg':[[-90,90]]*3})
bone('root',[0,0,.4],[0,0,.55],None,'root');bone('neck',[0,0,.55],[0,0,.78],'root','neck');bone('head',[0,0,.78],[0,0,1.0],'neck','head');bone('beak',[0,-.10,.9],[0,-.25,.9],'head','beak');bone('tail',[0,.12,.5],[0,.4,.55],'root','tail')
for side,sign in [('L',-1),('R',1)]:
 bone('wing.'+side,[sign*.12,0,.65],[sign*.4,0,.55],'root','wing.'+side)
 bone('leg.'+side,[sign*.12,0,.4],[sign*.12,0,.14],'root','leg.'+side)
 bone('foot.'+side,[sign*.12,0,.14],[sign*.12,.15,.08],'leg.'+side,'foot.'+side)
 for n,delta in [('front1',[-.06,.12,0]),('front2',[0,.14,0]),('front3',[.06,.12,0]),('back',[0,-.12,0])]:
  base=[sign*.12,.15,.08];bone('toe.'+side+'.'+n,base,[base[i]+delta[i] for i in range(3)],'foot.'+side,'toe.'+side+'.'+n)
mat={'rgba':[.95,.7,.05,1],'metallic':0,'roughness':.45}
def part(id,shape,dim,pos,role='geometry',color=None):return {'id':id,'shape':shape,'dimensions_m':dim,'position_m':pos,'rotation_deg':[0,0,0],'resolution':12,'material':dict(mat,rgba=color or mat['rgba']),'source':source,'role':role}
parts=[part('bird_body','ELLIPSOID',[.4,.35,.55],[0,0,.53],'body'),part('bird_head','ELLIPSOID',[.35,.35,.35],[0,0,.9],'head'),part('eye_l','ELLIPSOID',[.08,.045,.08],[-.09,-.155,.94],'eye',[1,1,1,1]),part('eye_r','ELLIPSOID',[.08,.045,.08],[.09,-.155,.94],'eye',[1,1,1,1]),part('pupil_l','ELLIPSOID',[.035,.025,.035],[-.09,-.18,.94],'pupil',[.03,.015,.01,1]),part('pupil_r','ELLIPSOID',[.035,.025,.035],[.09,-.18,.94],'pupil',[.03,.015,.01,1]),part('scarf','TORUS',[1,1,1],[0,0,.75],'clothes',[.5,.02,.05,1])]
parts[-1].update(major_radius_m=.16,minor_radius_m=.025)
for side,sign in [('L',-1),('R',1)]:
 p=part('wingmesh_'+side,'ELLIPSOID',[.12,.1,.35],[0,-.15,0],'wing');p['bone']='wing.'+side;parts.append(p)
parts.append(dict(part('bill','CONE',[.12,.12,.20],[0,-.2,.9],'beak',[1,.2,.02,1]),tip_ratio=0,rotation_deg=[90,0,0]))
points=[{'id':id,'position_m':pos,'rotation_deg':[0,0,0],'source':source} for id,pos in [('centre',[0,0,.6]),('ground_l',[-.12,.15,.08]),('ground_r',[.12,.15,.08]),('support_a',[-.3,-.2,0]),('support_b',[.3,-.2,0]),('support_c',[.3,.35,0]),('support_d',[-.3,.35,0])]]
geometry={'parts':parts,'required_roles':['body','head','eye','pupil','clothes','beak','wing'],'source':source,'final_appearance_ref':'SOLO_FIXTURE_SINTETICO_NO_APROBACION_ARTISTICA'}
e={'id':'bird_fixture','type':'CHARACTER','anatomy':'avian','rig':{'bones':bones},'appearance':{'geometry':geometry,'rostros_finales':{'asset':source,'source':source},'ropa_final':{'asset':source,'source':source}},'points':points,'physics':{'bone_mass_kg':{b['id']:1 for b in bones},'balance_margin_m':.04,'support_intervals':[{'t0':0,'t1':2,'mode':'supported','support_points':['bird_fixture.support_a','bird_fixture.support_b','bird_fixture.support_c','bird_fixture.support_d']}]}}
shots=[]
for id,a,b,mode,tr in [('shot_A',0,1,'STATIC','CORTE'),('shot_B',1,2,'PAN',{'type':'FUNDIDO','duration_s':.25})]:
 s={'id':id,'t0':a,'t1':b,'transition':tr,'trajectory':{'mode':mode,'position':[0,-4,1.8],'target':[0,0,.6],'lens_mm':28},'sensor_width_mm':36,'clip_start_m':.01,'clip_end_m':100,'smoothing':0,'roll_deg':0,'handheld_amount':0,'check_points':['bird_fixture.centre'],'ndc_margin':.03,'ray_epsilon_m':.001,'occlusion_allowed_objects':[p['id'] for p in parts],'min_clearance_m':.05,'axis180':None}
 if mode=='PAN':s['trajectory']['degrees']=15
 shots.append(s)
floor=part('floor','BOX',[5,5,.1],[0,0,-.05],color=[.25,.3,.35,1])
requests={'entity':'bird_fixture','action':'wing_open','anatomy':'avian','emotion':'neutral','load':'none','support':'feet','context':'flat'}
candidate=dict(requests,id='authored_wing',provider='argon',license_ref='CREACION_SINTETICA_DE_PRUEBA_NO_BIBLIOTECA',approval_ref='SOLO_PRUEBA_CPU',tracks=[{'bone':'wing.L','keys':[{'t':0,'value':[0,0,0],'curve':'SMOOTH'},{'t':1,'value':[15,0,0],'curve':'SMOOTH'},{'t':2,'value':[0,0,0],'curve':'SMOOTH'}]}])
p={'id':'prop_fixture','position_m':[1.1,0,0],'geometry':[part('prop_base','BOX',[.5,.3,.3],[0,0,.15]),part('prop_lid','BOX',[.5,.3,.04],[0,0,.32])],'points':[{'id':'hinge','position_m':[0,.15,.3],'rotation_deg':[0,0,0],'source':source}],'hinges':[{'id':'lid_hinge','pivot_m':[0,.15,.3],'axis':[1,0,0],'parts':['prop_lid'],'min_deg':0,'max_deg':60,'keys':[{'t':0,'c':0},{'t':2,'c':1}]}]}
d={'schema_version':'1.0','job_id':'FIXTURE_NO_GUARDIANES','scene':'synthetic_cpu','clock':{'fps':8,'duration_s':2,'rounding':'half_up'},'coordinates':{'unit':'m','up':'Z','forward':'-Y','origin':[0,0,0],'source':source},'entities':[e],'requirements':{'entity_ids':['bird_fixture'],'object_refs':[]},'environment':{'mode':'geometry','geometry':[floor],'events':[],'live_data':{'status':'complete','changes':[]}},'props':[p],'contacts':[],'fx_events':[],'motion':{'status':'complete','catalog':source,'assignments':'asignaciones.json','requests':[requests],'candidates':[candidate]},'camera':{'shots':shots},'lighting':{'base':[{'id':'key_light','type':'AREA','position_m':[0,-2,4],'rotation_deg':[25,0,0],'energy':400,'color':[1,1,1]}],'exposure':0,'view_transform':'Standard','events':[],'source':source},'rules':{'bone_length_error_m':.00001,'root_speed_max_m_s':5,'root_accel_max_m_s2':20,'com_accel_max_m_s2':20,'joint_speed_max_deg_s':900,'slip_max_m_per_frame':.05,'colliders':['bird_body','floor','prop_base'],'allowed_collision_pairs':[],'penetration_tolerance_m':.001,'reject_surface_intersections':True},'actions':[{'id':'dialog_1','accion':'hablar','actor':'bird_fixture','t':[.5,1.5],'cita':'Texto sintético para comprobar el archivo de tiempos. No se genera voz.'}],'segments':[],'render':{'engine':'BLENDER_EEVEE_NEXT','resolution':[128,128],'samples':1,'seed':42},'required_capabilities':['rostros_finales','ropa_final'],'libraries':[],'fixture_only':True}
guardar(pk/source,{'fixture':'sintético explícito; dimensiones no pertenecen a un personaje real','no_artistic_approval':True});guardar(pk/'asignaciones.json',[{'accion_plan':'dialog_1'}]);d['assets']=[{'path':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in pk.iterdir() if p.is_file()];d['sources']=[{'module':'fixture_autogenerado_NO_MODULO_REAL','path':source,'sha256':sha(pk/source)}];d=__import__('json').loads((R/'pruebas/datos/fixture_aviar_canonico.json').read_text());guardar(pk/'entrada_escena.json',d);print(pk)
