import json,sys
from pathlib import Path
import jsonschema
B=Path('/opt/myia-motor-v9/avance07_20261107/entrega');sys.path.insert(0,str(B/'codigo'));from generar_schema import standard
read=lambda p:json.loads(p.read_text());a=read(B/'evidencias/av07_adn01/respuesta.json');b=read(B/'evidencias/av07_adn02/respuesta.json');assert {x['id'] for x in b['objects']}=={'obj-visor-spark','Ventana con vista al arcoíris'}
a['objects']=[x for x in a['objects'] if x['id'] not in {y['id'] for y in b['objects']}]+b['objects'];a['axes']=b['axes'];a['identity_notes']+=b['identity_notes'];a['physical_missing']=sorted(set(a['physical_missing']+b['physical_missing']))
jsonschema.validate(a,standard(read(B/'config/adn.schema.json')))
p=B/'evidencias/av07_adn_compuesto02';p.mkdir();(p/'respuesta.json').write_text(json.dumps(a,ensure_ascii=False,indent=2));(p/'schema_validacion.json').write_text(json.dumps({'passed':True,'scope':'Lossless composition of model responses ADN01(book/rug)+ADN02(visor/window/axes)','network_calls':0,'numeric_edits_by_consumer':0}));print('composed')
