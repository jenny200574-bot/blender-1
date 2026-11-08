"""ADN textual a bases CPU autorizadas; cotas de biblioteca explícitas, no cotas imaginadas del ADN."""
import re,copy,unicodedata,math
from pathlib import Path
from seguridad import leer,sha,error
from superficies_adn import loft

def norm(s):return unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
def color(text,palette,fallback):
 s=norm(text);hexes=re.findall(r'#[0-9a-f]{6}',s)
 if hexes:return [int(hexes[0][j:j+2],16)/255 for j in [1,3,5]]+[1]
 candidates=[(m.start(),v) for k,v in palette.items() for m in re.finditer(r'\b'+re.escape(norm(k)[:-1])+r'[oa]s?\b' if norm(k).endswith('o') else re.escape(norm(k)),s)]
 return copy.deepcopy(min(candidates,key=lambda x:x[0])[1] if candidates else fallback)
def construir(entity,library=None):
 path=Path(__file__).resolve().parents[1]/'bibliotecas/apariencia_base_cpu.json';lib=library or leer(path);dna=entity.get('dna_record') or {};data=dna.get('source_data') or {};text=data.get('text','');anatomy=entity.get('anatomy');profile=lib['profiles'].get(anatomy)
 if not text or profile is None:return None,{},[error('appearance/base','ADN/SELLO','ADN textual o perfil base ausente')]
 h=data.get('height_m') or (entity.get('legacy') or {}).get('spec',{}).get('altura_m')
 if not isinstance(h,(float,int)) or h<=0:return None,{},[error('appearance/base/height','ADN Maestro','Falta altura declarada para ajustar la base')]
 heads=data.get('heads') or (entity.get('legacy') or {}).get('spec',{}).get('cabezas') or (2 if anatomy=='avian' else 6)
 hh=h/heads;cz=h-hh/2;parts=[];source=dna.get('source');palette=lib['palette'];normalized=norm(text);lines=text.splitlines();selected=[]
 def sentence(*words):return next((line for line in lines if not re.match(r'^\s*\d+[.]',line) and any(norm(w) in norm(line) for w in words)),'')
 skin=color(sentence('piel','plumaje'),palette,palette['piel']);hair=color(sentence('cabello','pelo'),palette,palette['castaño']);outfit=color(sentence('prenda exterior','prenda interior','vestuario'),palette,palette['azul'])
 def add(name,role,center,size,rgba,bone_role=None,kind='loft',style=None):
  ident=entity['id']+'.base.'+name;mat={'rgba':rgba,'metallic':0,'roughness':.55,'source':'ADN:'+str(source)+'; paleta:'+lib['source']}
  spec={'id':ident,'shape':'MESH','position_m':center,'rotation_deg':[0,0,0],'material':mat,'source':'de biblioteca: '+lib['source'],'role':role,'normals':'SMOOTH','library_dimensions':{'status':'de biblioteca','dimensions_m':size,'library_sha256':sha(path),'generator_sha256':sha(Path(__file__)),'position_m':center,'rotation_deg':[0,0,0],'fit_height_m':h,'ADN_source':source},'bind_role':bone_role}
  if kind=='loft':
   width,depth,height=size;sections=[[-height*.5,0,0,width*.28,depth*.3],[-height*.35,0,0,width*.46,depth*.46],[height*.05,0,0,width*.5,depth*.5],[height*.35,0,0,width*.38,depth*.4],[height*.5,0,0,width*.12,depth*.15]]
   if style=='triangle':sections[1][3]*=.65;sections[3][3]*=1.2
   v,f=loft({'sections_m':sections,'radial_segments':lib['resolution'],'thickness_m':0,'cap_bottom':True,'cap_top':True});spec.update(vertices_m=v,faces=f)
  else:spec.update(shape='ELLIPSOID',dimensions_m=size,resolution=lib['resolution'])
  parts.append(spec);return spec
 headw=hh*profile['head_width'];headd=hh*profile['head_depth'];face_line=sentence('rostro','forma del rostro','pico');add('face','face',[0,0,cz],[headw,headd,hh],skin,'head',style='triangle' if 'triangular' in norm(face_line) else None)
 for side in [-1,1]:
  x=side*hh*profile['eye_spacing'];eye=hh*profile['eye_size'];add('eye_'+str(side),'eyes',[x,headd*.45,cz+hh*.05],[eye,eye*.4,eye*.9],palette['blanco'],'head','ellipsoid');add('iris_'+str(side),'eyes',[x,headd*.52,cz+hh*.05],[eye*.55,eye*.15,eye*.65],color(sentence('iris'),palette,palette['marron']),'head','ellipsoid');add('pupil_'+str(side),'eyes',[x,headd*.54,cz+hh*.05],[eye*.25,eye*.1,eye*.4],palette['negro'],'head','ellipsoid');add('brow_'+str(side),'face',[x,headd*.47,cz+hh*.2],[eye*1.1,eye*.3,eye*.2],hair,'head')
 ns=hh*profile['nose_size']*(1.5 if 'grande' in norm(face_line) else 1);add('nose','face',[0,headd*.53,cz-hh*.1],[ns,ns*1.2,ns],color(face_line,palette,skin),'head','ellipsoid');add('mouth','face',[0,headd*.48,cz-hh*.28],[hh*profile['mouth_width'],hh*.025,hh*.035],color(sentence('labios'),palette,palette['rosa']),'head')
 if anatomy=='avian':
  plum=color(sentence('plumaje'),palette,palette['amarillo']);add('body','body_cover',[0,0,h*.36],[h*profile['torso_width'],h*profile['torso_depth'],h*.52],plum,'root')
  add('beak','face',[0,headd*.62,cz-hh*.15],[hh*.4,hh*.38,hh*.17],color(sentence('pico'),palette,palette['naranja']),'head')
  for side in [-1,1]:add('wing_'+str(side),'plumage',[side*h*.26,0,h*.4],[h*.15,h*.32,h*.38],plum,'wing.L' if side<0 else 'wing.R')
 else:
  add('body','body_cover',[0,0,h*.53],[h*profile['torso_width'],h*profile['torso_depth'],max(h*.25,h-hh-h*.4)],skin,'torso')
  for side in [-1,1]:
   suffix='left' if side<0 else 'right'
   for name,role,size in [('thigh','thigh_', [h*.09,h*.11,h*.22]),('shin','shin_', [h*.075,h*.09,h*.22]),('upper_arm','upper_arm_', [h*.075,h*.09,h*.18]),('forearm','forearm_', [h*.06,h*.07,h*.15]),('hand','hand_', [h*.065,h*.04,h*.1])]:
    part=add(name+str(side),'body_cover',[0,0,0],size,skin,role+suffix);part['fit_to_bone']=True
  clothing_text='\n'.join(x for x in lines if any(w in norm(x) for w in ['prenda','vestido','traje','pantalon','capa ','camisa','armadura','calzado']))
  for garment in lib['garments']:
   matches=[x for x in clothing_text.splitlines() if any(w in norm(x) for w in garment['words']) and not re.search(r'sin (?:capas?|'+garment['kind']+')',norm(x))]
   if not matches:continue
   selected.append({'template':garment['id'],'ADN_lines':matches});rgba=color(matches[0],palette,outfit);kind=garment['kind']
   if kind=='trousers':
    for side in [-1,1]:
     for segment in ['thigh','shin']:
      part=add(garment['id']+segment+str(side),'clothes',[0,0,0],[h*.105,h*.125,h*.22],rgba,segment+('_left' if side<0 else '_right'));part['fit_to_bone']=True
   else:
    center=[0,-h*.09 if kind=='cape' else 0,h*(.51 if kind in ['skirt','cape'] else .53)];layer=len(selected)*.012;size=[h*(.32 if kind=='cape' else .29+layer),h*(.025 if kind=='cape' else .18+layer),h*(.5 if kind=='cape' else .44)];add(garment['id'],'clothes',center,size,rgba,'torso')
    if kind in ['suit','jacket','shirt','armor']:
     segments=['upper_arm']+(['forearm'] if kind!='shirt' else [])+(['thigh','shin','hand'] if kind=='suit' else [])
     for side in ['left','right']:
      for segment in segments:
       part=add(garment['id']+'_'+segment+'_'+side,'clothes',[0,0,0],[h*(.115+layer),h*(.13+layer),h*.22],rgba,segment+'_'+side);part['fit_to_bone']=True
  if not selected:add('garment_base','clothes',[0,0,h*.53],[h*.29,h*.18,h*.44],outfit,'torso');selected.append({'template':'garment_base','reason':'Tipo no reconocido: aproximación de biblioteca, no identidad exacta'})
  for side in [-1,1]:add('shoe_'+str(side),'clothes',[side*h*.07,h*.025,h*.035],[h*.11,h*.18,h*.07],color(sentence('calzado','botas','zapatillas'),palette,palette['negro']),'foot_left' if side<0 else 'foot_right')
 hairline=sentence('cabello','pelo','cresta')
 if hairline:
  add('hair','hair',[0,-headd*.08,cz+hh*.32],[headw*1.08,headd*.95,hh*.42],hair,'head')
  if any(w in norm(hairline) for w in ['largo','espalda','ondas']):add('hair_long','hair',[0,-headd*.45,cz-hh*.38],[headw*.95,headd*.35,hh*1.5],hair,'head')
 for word,kind in [('casco','helmet'),('gafas','glasses'),('visor','glasses'),('boina','hat')]:
  ls=[s for s in lines if word in norm(s) and not re.search(r'sin\s+(?:gafas|visor|casco)',norm(s))]
  if not ls:continue
  if kind=='glasses':
   for side in [-1,1]:
    p=add(kind+word+str(side),'accessory',[side*hh*profile['eye_spacing'],headd*.57,cz+hh*.05],[hh*.36,hh*.04,hh*.25],color(ls[0],palette,palette['cian']),'head','ellipsoid');p['material'].update(alpha=.35,transmission=.8,ior=1.45)
  else:add(kind,'accessory',[0,-headd*.05,cz+hh*.36],[headw*1.18,headd*1.13,hh*.4],color(ls[0],palette,outfit),'head')
 covered={p.get('bind_role') for p in parts if p['role']=='clothes' and p.get('bind_role')}
 for p in parts:
  if p['role']=='body_cover' and p.get('bind_role') in covered:p['hidden_under_garment']=True
 roles=sorted({p['role'] for p in parts});geometry={'parts':parts,'required_roles':roles,'source':source,'final_appearance_ref':{'scope':'BASE_CPU_AJUSTADA_ADN_T314; fidelidad aproximada, no reconstrucción de imagen','library_sha256':sha(path),'gpu_adapter_slot':lib['gpu_slot'],'dna_text_sha256':__import__('hashlib').sha256(text.encode()).hexdigest()}}
 receipt={'entity':entity['id'],'state':'BASE_CPU_COMPILADA','source':source,'library_sha256':sha(path),'part_count':len(parts),'selected_garments':selected,'dimensions_status':'de biblioteca; escala/altura del ADN','unsupported_fidelity':'Detalles/expresiones/ornamentos no resueltos por bases son AVISO de fidelidad; no se declaran exactos','parts':[p['id'] for p in parts]}
 return geometry,receipt,[]

def ligar(spec,rig,entity):
 """Convierte marco rest de la base al marco local de cola del hueso Blender."""
 if not spec.get('bind_role'):return spec
 from mathutils import Matrix,Euler,Vector
 lib=leer(Path(__file__).resolve().parents[1]/'bibliotecas/apariencia_base_cpu.json');roles={b.get('role'):b['id'] for b in (entity.get('rig') or {}).get('bones',[])};roles.update((entity.get('rig') or {}).get('roles') or {});name=roles.get(spec['bind_role']) or lib['body_bones'].get(entity['anatomy'],{}).get(spec['bind_role'])
 if not name or name not in rig.data.bones:
  from malla_cabeza import error_hueso_cabeza
  raise ValueError(error_hueso_cabeza(entity.get('id'), spec.get('bind_role'), name, [b.name for b in rig.data.bones]))
 b=rig.data.bones[name];spec=copy.deepcopy(spec)
 if spec.get('fit_to_bone'):
  dims=spec['library_dimensions']['dimensions_m'];ratio=b.length/dims[2]
  if spec['shape']=='MESH':
   for vertex in spec['vertices_m']:vertex[2]*=ratio
  else:spec['dimensions_m'][2]=b.length
  fitted=b.matrix_local@Matrix.Translation((0,b.length/2,0))@Euler((-math.pi/2,0,0)).to_matrix().to_4x4();spec['position_m']=list(fitted.translation);spec['rotation_deg']=[math.degrees(x) for x in fitted.to_euler()];spec['library_dimensions']['fit_from_rig']={'bone':name,'length_m':b.length,'source':'esqueleto de entrada; sin cambiarlo'}
 parent=b.matrix_local@Matrix.Translation((0,b.length,0));m=parent.inverted()@Matrix.LocRotScale(Vector(spec['position_m']),Euler([math.radians(x) for x in spec['rotation_deg']]).to_quaternion(),Vector((1,1,1)));out=copy.deepcopy(spec);out.update(position_m=list(m.translation),rotation_deg=[math.degrees(x) for x in m.to_euler()],bone=name);return out
