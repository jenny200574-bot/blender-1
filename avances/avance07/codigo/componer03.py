import json,sys,copy
from pathlib import Path
B=Path('/opt/myia-motor-v9/avance07_20261107/entrega');sys.path.insert(0,str(B/'codigo'));from generar_schema import standard
import jsonschema
read=lambda p:json.loads(p.read_text());a=read(B/'evidencias/av07_adn_compuesto02/respuesta.json');v=read(B/'evidencias/av07_visor03/respuesta.json');rain=read(B/'evidencias/av07_rainbow03/respuesta.json')
assert len(v['updates'])==len({(x['id'],x['field']) for x in v['updates']})
visor=next(o for o in a['objects'] if o['id']=='obj-visor-spark')
for patch in v['updates']:next(p for p in visor['parts'] if p['id']==patch['id'])[patch['field']]=patch['value']
window=next(o for o in a['objects'] if o['id']=='Ventana con vista al arcoíris');window['parts']=[p for p in window['parts'] if not p['id'].startswith('av07.window.rainbow.')]
assert len(rain['bands'])==7 and {b['id'] for b in rain['bands']}=={'av07.window.rainbow.'+c for c in ['red','orange','yellow','green','blue','indigo','violet']}
for band in rain['bands']:
 assert len(band['points_xz'])>=13 and band['y']+band['radius_m']<=.075
 # Fixed coordinate embedding and unused schema fields are structural transport, not artistic edits.
 original_window=next(o for o in read(B/'evidencias/av07_adn01/respuesta.json')['objects'] if o['id']=='Ventana con vista al arcoíris')
 part=copy.deepcopy(next(p for p in original_window['parts'] if p['id']==band['id']))
 part.update(role='rainbow',shape='POINT_TUBE',px=0,py=band['y'],pz=0,rx=0,ry=0,rz=0,r=band['rgba'][0],g=band['rgba'][1],b=band['rgba'][2],a=band['rgba'][3],resolution=band['resolution'],radius_m=band['radius_m'],plane_normal=[0,1,0],points=[dict(x=p['x'],y=0,z=p['z']) for p in band['points_xz']]);window['parts'].append(part)
jsonschema.validate(a,standard(read(B/'config/adn.schema.json')));p=B/'evidencias/av07_adn_compuesto03';p.mkdir();(p/'respuesta.json').write_text(json.dumps(a,ensure_ascii=False,indent=2));(p/'schema_validacion.json').write_text(json.dumps({'passed':True,'scope':'Lossless ADN01 book/rug + ADN02 visor/frame + visor03 scalar patches + rainbow03 model points','network_calls':0,'artistic_numeric_edits_by_consumer':0,'rainbow_transport_constants':'Coordinate embedding XZ plane, Y offset from model; materials other than new RGB/A retained verbatim from same-ID ADN01 model part; no new artistic numeric defaults'}));print('composed03')
