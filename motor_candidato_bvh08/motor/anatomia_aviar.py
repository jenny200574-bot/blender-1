"""Anatomía aviar genérica, sin usar solver ni proporciones humanoides."""
from geometria import rig_declarativo

def construir(pid,spec):
    # Posiciones/proporciones y límites los entrega ADN/esqueleto, en metros.
    required={'root','neck','head','beak','tail','wing.L','wing.R','leg.L','leg.R','foot.L','foot.R'}
    required|={f'toe.{side}.{n}' for side in ('L','R') for n in ('front1','front2','front3','back')}
    roles={b['role'] for b in spec['bones']}
    if not required.issubset(roles):raise ValueError('ADN/rig aviar: faltan roles '+','.join(sorted(required-roles)))
    return rig_declarativo(pid,spec)
