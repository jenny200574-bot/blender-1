"""ADN/SELLO→IR citado→superficies y detalles del contrato único.
No confunde prosa presente con ADN ausente. No inventa cotas ni marca final
si hay una exigencia sin vincular a geometría. Los fallos de cobertura siguen A.
"""
import re,hashlib,copy
from seguridad import error,numero
from superficies_adn import loft

def hechos(text):
    section=None;out=[]
    for line_no,line in enumerate(text.splitlines(),1):
        clean=re.sub(r'[*]','',line).strip()
        heading=re.match(r'^(\d+)\.\s',clean)
        if heading:section=int(heading[1]);continue
        if section not in [1,2,3,4,5] or not clean:continue
        clean=clean.lstrip('- ').strip();out.append({'id':hashlib.sha256((str(section)+':'+clean).encode()).hexdigest(),'section':{1:'anthropometry',2:'face',3:'expressions',4:'clothes',5:'rotation_rules'}[section],'line':line_no,'text':clean,'hex_colors':re.findall(r'#[0-9a-fA-F]{6}\b',clean),'explicit_cm':[float(v.replace(',','.')) for v in re.findall(r'(\d+(?:[.,]\d+)?)\s*cm\b',clean)]})
    return out

def superficie(entity,record,role,source):
    for field in ['id','position_m','rotation_deg','material','surface','source']:
        if field not in record:raise ValueError('Patrón sin '+field)
    vertices,faces=loft(record['surface']);part={k:copy.deepcopy(record[k]) for k in ['id','position_m','rotation_deg','material','source']};part.update(shape='MESH',vertices_m=vertices,faces=faces,normals='SMOOTH',role=record.get('role',role))
    for key in ['bone','bevel']:
        if key in record:part[key]=copy.deepcopy(record[key])
    return part

def traducir(entity):
    dna=(entity.get('dna_record') or {});data=dna.get('source_data') or {};text=data.get('text','');facts=hechos(text);source=dna.get('source');model=data.get('construction_3d');base='entities/'+entity['id']+'/dna';receipt={'entity':entity['id'],'source':source,'source_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'facts':facts,'applied':[],'state':'PENDIENTE'};errors=[]
    if not facts:
        errors.append(error(base+'/text','ADN/SELLO PJ','Faltan secciones de fisonomía y vestuario del ADN real; no se genera identidad genérica'));return None,receipt,errors
    if not isinstance(model,dict):
        for field,message in [('face_measurements','No hay cotas 3D/profundidad/calibración de vistas de cara para construir un perfil sin inventar medidas'),('garment_measurements','No hay cotas espaciales de capas, cobertura corporal y aberturas para un perfil medido; el ADN y las imágenes están presentes, pero no determinan toda la profundidad oculta')]:
            errors.append(error(base+'/'+field,'ADN Maestro 03/04 / SELLO PJ',message,'ADN_COTA_NO_DEFINIDA',fuente=source))
        receipt['state']='BLOQUEADO_DATOS_Y_COBERTURA_NO_RESUELTA';return None,receipt,errors
    parts=[]
    try:
        if not isinstance(model.get('fact_bindings'),dict) or any(not isinstance(v,list) or any(not isinstance(x,str) for x in v) for v in model['fact_bindings'].values()):raise ValueError('Vínculos de hechos deben ser listas de IDs')
        if not isinstance(model.get('required_roles'),list) or any(not isinstance(v,str) or not v for v in model['required_roles']):raise ValueError('Roles requeridos deben ser lista explícita')
        for record in model.get('face_surfaces',[]):parts.append(superficie(entity,record,'face',source))
        for record in model.get('garments',[]):parts.append(superficie(entity,record,'clothes',source))
        parts+=copy.deepcopy(model.get('details',[]));ids={p['id'] for p in parts}
        if 'required_roles' not in model or 'source' not in model:raise ValueError('Faltan roles requeridos o procedencia del patrón')
        for part in parts:
            if not isinstance(part.get('id'),str) or not part['id'] or ('role' in part and (not isinstance(part['role'],str) or not part['role'])):raise ValueError('ID o rol de pieza inválido')
            mat=part['material']
            if not isinstance(mat,dict) or not {'rgba','metallic','roughness'}<=set(mat):raise ValueError('Faltan parámetros de material por pieza')
            if not isinstance(mat['rgba'],list) or len(mat['rgba'])!=4 or any(not numero(x) or not 0<=x<=1 for x in mat['rgba']) or any(not numero(mat[k]) or not 0<=mat[k]<=1 for k in ['metallic','roughness']):raise ValueError('Color/material fuera de rango o no numérico')
    except (ValueError,KeyError,TypeError) as exc:
        errors.append(error(base+'/construction_3d','ADN Maestro 03/04 / SELLO PJ','Cota/patrón/material incompleto o inválido: '+str(exc),'ADN_COTA_NO_DEFINIDA',fuente=source));receipt['state']='BLOQUEADO_DATOS';return None,receipt,errors
    if len(ids)!=len(parts):
        errors.append(error(base+'/construction_3d/parts','ADN/SELLO PJ','IDs de pieza duplicados','CONFLICTO',tipo='conflicto',fuente=source));receipt['state']='BLOQUEADO_DATOS';return None,receipt,errors
    for fact in facts:
        linked=model.get('fact_bindings',{}).get(fact['id'],[])
        if not linked or not set(linked)<=ids:errors.append(error(base+'/facts/'+fact['id'],'motor/traductor ADN→3D','Exigencia real del ADN aún sin geometría vinculada: '+fact['text'],'ADN_RASGO_SIN_CONSTRUIR',tipo='crear capacidad',fuente={'document':source,'line':fact['line']}))
        else:receipt['applied'].append({'fact_id':fact['id'],'parts':linked})
    if not model.get('face_surfaces') or not model.get('garments'):errors.append(error(base+'/construction_3d','ADN/SELLO PJ','Faltan cotas de superficie de cara o de vestuario','ADN_COTA_NO_DEFINIDA',fuente=source))
    if errors:receipt['state']='BLOQUEADO';return None,receipt,errors
    receipt['state']='COMPILADO_POR_DATOS';receipt['part_ids']=sorted(ids)
    return {'parts':parts,'required_roles':model['required_roles'],'source':source,'final_appearance_ref':{'dna_sha256':receipt['source_text_sha256'],'construction_source':model['source'],'scope':'DERIVADO_DEL_ADN; NO FIRMA DE APROBACION HUMANA'}},receipt,[]

def compilar(d,prueba_cpu=False):
    if not prueba_cpu and any(e.get("type")=="CHARACTER" and not (e.get("appearance") or {}).get("geometry") for e in d.get("entities",[])):
        from seguridad import exigir
        exigir("traductor_adn")
    receipts=[];errors=[]
    for entity in d.get('entities',[]):
        if entity.get('type')!='CHARACTER' or (entity.get('appearance') or {}).get('geometry'):continue
        if not (entity.get('dna_record') or {}).get('source_data',{}).get('construction_3d') and not (__import__('pathlib').Path(__file__).resolve().parents[1]/'config/apariencia_base_cpu.off').exists():
            from apariencia_base_cpu import construir as construir_base
            geometry,receipt,found=construir_base(entity)
            if geometry:
                for field in ['face_measurements','garment_measurements']:d.setdefault('warnings',[]).append({'codigo':'ADN_FIDELIDAD_BIBLIOTECA','severidad':'AVISO','campo':'entities/'+entity['id']+'/dna/'+field,'modulo':'ADN + biblioteca base CPU','mensaje':'Cotas de biblioteca t314, no cotas medidas del ADN; aproximación autorizada','fuente':receipt.get('source')})
        else:geometry,receipt,found=traducir(entity)
        receipts.append(receipt);errors+=found
        if geometry:
            app=entity.setdefault('appearance',{});app['geometry']=geometry
            for field in ['rostros_finales','ropa_final']:app[field]={'asset':'entrada_escena.json#/entities/'+entity['id']+'/appearance/geometry','source':receipt['source']}
    from malla_cabeza import validar_cabeza, error_malla_vacia
    from compatibilidad_artefacto import ESQUEMA
    revisadas=[]
    for entity in d.get('entities',[]):
        if entity.get('type')!='CHARACTER':
            continue
        revisadas.append(entity.get('id'))
        geometry=(entity.get('appearance') or {}).get('geometry')
        if not geometry:
            continue
        vacia=next((error_malla_vacia(part) for part in geometry.get('parts') or [] if error_malla_vacia(part)), None)
        if vacia:
            errors.append(error('entities/'+entity['id']+'/appearance/geometry','traductor ADN',vacia,'MALLA_VACIA'))
            continue
        falta=validar_cabeza(entity)
        if falta:
            errors.append(error('entities/'+entity['id']+'/rig/cabeza','traductor ADN + ensamblado',falta,'CABEZA_NO_ASIGNADA'))
    d['_cabeza_compilada']={'esquema':ESQUEMA,'entidades':revisadas}
    return receipts,errors
