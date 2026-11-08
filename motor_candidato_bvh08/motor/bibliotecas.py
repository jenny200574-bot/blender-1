"""Registro local por hash y permiso, sin confundir índice con clip ni copia con pose nueva."""
from seguridad import *

def indexar(files,root):
 records=[];by_hash={}
 for f in files:
  p=Path(f['path']);h=sha(p);record={'path':str(p.relative_to(root)),'sha256':h,'bytes':p.stat().st_size,'role':f['role'],'approval_status':f.get('approval_status','SIN_VERIFICAR'),'license_status':f.get('license_status','SIN_VERIFICAR')}
  if h in by_hash:record['duplicate_of']=by_hash[h]
  else:by_hash[h]=record['path']
  record['runtime_enabled']=record['approval_status']=='VERIFICADA';records.append(record)
 return records

def cargar(root,reference):
 p=ruta(root,reference['path'])
 if sha(p)!=reference['sha256']:raise ValueError('Biblioteca cambió')
 if reference.get('technical_restricted') or reference.get('restricted_reason')=='technical':raise ValueError('Biblioteca sin autorización técnica: no habilitar por una plantilla')
 if reference.get('restricted') or reference.get('license_status')!='VERIFICADA':reference.setdefault('warnings',[]).append('LICENCIA_INFORMATIVA: uso personal t291, sin filtro legal; calidad técnica obligatoria')
 return leer(p)

def resolver_id(query,records):
 matches=[r for r in records if query==r.get('id') or query in r.get('exact_aliases',[])]
 if len(matches)!=1:raise ValueError('ID/alias '+str(query)+' ambiguo o ausente; no se aproxima')
 return matches[0]['id']
