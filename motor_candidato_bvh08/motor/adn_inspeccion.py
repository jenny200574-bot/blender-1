"""Traducción conservadora de estructura: no elige proporciones ni rellena adjetivos."""
import re,copy

def enriquecer(d):
    for e in d.get('entities',[]):
        if e.get('type')!='CHARACTER' or e.get('anatomy') is not None:continue
        old=e.get('legacy') or {};source=(e.get('dna_record') or {}).get('source_data') or {};text=source.get('text','')
        # Compatibilidad con un backend ya identificado por su formato, NO inferencia por ID.
        if all(k in old for k in ['spec','profile','colors','initial_pose_id','solver_policy']) and all(k in old['spec'] for k in ['altura_m','cabezas','complexion']):
            e['anatomy']='humanoid';e['anatomy_source']={'method':'backend_legacy_rig_format','source':'entrada.json#/actors','note':'Clasificación del esqueleto humanoide existente; no afirma que la especie sea humana.'}
        elif re.search(r'\bave\b|\baviares?\b|\bpajarito\b|\bpájaro\b',text,re.I):
            e['anatomy']='avian';e['anatomy_source']={'method':'anatomia_explicita_en_ADN','source':(e.get('dna_record') or {}).get('source'),'citations':re.findall(r'.{0,25}(?:ave|aviar|pajarito|pájaro).{0,45}',text,re.I)}
    known={e['id']:e for e in d.get('entities',[])};keep=[]
    for note in d.get('provisional',[]):
        entity=known.get(note.get('campo'))
        if entity and entity.get('anatomy') and 'excluid' in note.get('mensaje','').lower():
            d.setdefault('normalization_history',[]).append({'resolved_note':note,'reason':'Entidad conservada en el contrato; backend anatómico ya existe. El rig/apariencia específicos se validan por separado y NO se declaran terminados.'})
        else:keep.append(note)
    d['provisional']=keep
    return d

def inventario(d):
    out=[]
    for e in d.get('entities',[]):
        source=(e.get('dna_record') or {}).get('source_data') or {};text=source.get('text','');features=[]
        for i,line in enumerate(text.splitlines(),1):
            if re.match(r'^\s*[-*]',line):features.append({'source_line':i,'description':line.strip(),'geometry_applied':False})
        out.append({'entity':e['id'],'anatomy':e.get('anatomy'),'height_m':source.get('height_m'),'heads':source.get('heads'),'explicit_hex_colors':sorted(set(re.findall(r'#[0-9a-fA-F]{6}\b',text))),'features':features,'note':'Inventario conservado, NO malla final. Un atributo sólo pasa a aplicado cuando exista vínculo geométrico trazable.'})
    return out
