"""02T canonical manifest adapter, free and fail-closed; never guesses raw 01→engine fields."""
import copy,hashlib,json,shutil,sys
from pathlib import Path

def unwrap(d):
 for _ in range(8):
  if isinstance(d,str):d=json.loads(d)
  elif isinstance(d,list) and len(d)==1:d=d[0]
  elif isinstance(d,dict) and set(d)=={'json'}:d=d['json']
  elif isinstance(d,dict) and 'stdout' in d and set(d)<= {'stdout','stderr','exitCode'}:
   if d.get('exitCode',0):raise ValueError('Producer failed')
   d=d['stdout']
  else:return d
 raise ValueError('Too many wrappers')
def safe(base,name):
 if not isinstance(name,str) or not name or '\\' in name or '..' in Path(name).parts or Path(name).is_absolute():raise ValueError('Invalid relative asset path')
 base=Path(base).resolve();p=(base/name).resolve()
 if not p.is_relative_to(base) or any(x.lower() in {'privado','.secrets','claves_privadas'} for x in Path(name).parts):raise ValueError('Forbidden asset')
 return p

def check(d):
 if not isinstance(d,dict):raise ValueError('Canonical object required')
 required=['schema_version','scene','clock','entities','environment','motion','camera','sources','assets','requirements','lighting','coordinates','libraries','required_capabilities']
 missing=[k for k in required if k not in d]
 if missing:raise ValueError('FALTA_ADAPTADOR_PRODUCTOR: missing canonical fields '+','.join(missing))
 ids=[e['id'] for e in d['entities']]
 if len(ids)!=len(set(ids)):raise ValueError('Duplicate entity IDs')
 paths=[a['path'] for a in d['assets']]
 if len(paths)!=len(set(paths)):raise ValueError('Duplicate asset paths')
 return d

def pointer(d,ptr):
 if ptr=='':return d
 if not ptr.startswith('/'):raise ValueError('JSON pointer required')
 for token in ptr[1:].split('/'):
  token=token.replace('~1','/').replace('~0','~');d=d[int(token)] if isinstance(d,list) else d[token]
 return d

def equivalences(rows,base):
 seen={};reverse={}
 for row in rows:
  # Each mapping is explicit and backed by the SAME source record, not fuzzy text.
  if not {'spatial_id','dna_id','source','spatial_pointer','dna_pointer'}<=set(row):raise ValueError('Equivalence missing evidence')
  a,b=row['spatial_id'],row['dna_id'];src=json.loads(safe(base,row['source']).read_text())
  if pointer(src,row['spatial_pointer'])!=a or pointer(src,row['dna_pointer'])!=b:raise ValueError('Equivalence evidence mismatch')
  if (a in seen and seen[a]!=b) or (b in reverse and reverse[b]!=a):raise ValueError('Ambiguous equivalence')
  seen[a]=b;reverse[b]=a
 return seen

def build(source,dest):
 source=Path(source).resolve();dest=Path(dest)
 if dest.exists():raise ValueError('Destination must be new')
 d=check(copy.deepcopy(unwrap(json.loads(source.read_text()))));base=source.parent
 if (base/'traductor_02t.off').exists():raise ValueError('02T off')
 mapping=equivalences(d.get('explicit_equivalences',[]),base)
 verified=[]
 for asset in d['assets']:
  p=safe(base,asset['path'])
  if p.suffix.lower() not in {'.json','.blend','.png','.jpg','.jpeg','.wav','.bvh','.mp3'}:raise ValueError('Unsupported asset type')
  if not p.is_file() or p.stat().st_size!=asset['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=asset['sha256']:raise ValueError('Asset hash/bytes mismatch: '+asset['path'])
  verified.append((asset,p))
 dest.mkdir(parents=True)
 for asset,p in verified:
  target=safe(dest,asset['path']);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
 # Nothing physical or artistic is inferred. Contract validates the explicit upstream values.
 receipt={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'assets_verified':len(verified),'explicit_equivalences':mapping,'paid_requests':0,'inferred_values':0,'adapter':'canonical_manifest_only','production_approved':False}
 (dest/'entrada_escena.json').write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False))
 (dest/'recibo_02t.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2));return receipt
if __name__=='__main__':
 try:print(json.dumps(build(sys.argv[1],sys.argv[2]),ensure_ascii=False))
 except (ValueError,OSError,KeyError,TypeError) as e:print(json.dumps({'ok':False,'error':str(e),'paid_requests':0}));sys.exit(2)
