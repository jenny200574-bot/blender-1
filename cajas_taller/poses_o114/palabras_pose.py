"""o110 (t298u): lista de palabras de pose para el validador del cubo 01 y el cubo 02c. Fuente: poses_basicas.json (humanos, probadas en Blender)
+ universal.py (poses por tipo de cuerpo, por rol). Palabra desconocida = FALTA (nunca se inventa)."""
import json, unicodedata
from pathlib import Path
AQUI = Path(__file__).resolve().parent
def _n(s): return ''.join(c for c in unicodedata.normalize('NFKD', str(s).lower()) if not unicodedata.combining(c)).replace(' ', '_')
def biblioteca(): return json.loads((AQUI / 'poses_basicas.json').read_text(encoding='utf-8'))
def palabras():
    """{palabra_normalizada: id_de_pose} con ids y alias de la biblioteca humana."""
    L = biblioteca(); out = {}
    for pid, p in L['poses'].items():
        for a in [pid] + list(p.get('alias') or []): out[_n(a)] = pid
    return out
def lista(): return sorted(biblioteca()['poses'])
def validar_toma(q, cid, x):
    """x = palabras.por_personaje[i]. 'pose' y 'espejo' son OPCIONALES (sin pose = de_pie). Devuelve lista de errores."""
    err = []
    if x.get('pose') not in (None, ''):
        if _n(x['pose']) not in palabras(): err.append(f"{q}.{cid}.pose: «{x['pose']}» no está en la biblioteca de poses {lista()} (FALTA, no se inventa)")
    if 'espejo' in x and not isinstance(x['espejo'], bool): err.append(f'{q}.{cid}.espejo: debe ser verdadero/falso')
    return err
