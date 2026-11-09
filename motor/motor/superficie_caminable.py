"""Superficies caminables (alfombra/tapete sobre piso). Universal por nombre, sin canal fijo."""
import re

_PATRON_CAMINABLE = re.compile(r'(rug|alfombra|tapete|carpet|\.rug\.)', re.I)
_PATRON_PISO = re.compile(r'^(piso|suelo|floor|param_piso)', re.I)


def es_superficie_caminable(nombre):
    return bool(nombre and _PATRON_CAMINABLE.search(nombre))


def es_piso_base(nombre):
    return bool(nombre and _PATRON_PISO.search(nombre))


def z_superior_estimada(verts):
    if not verts:
        return None
    zs = []
    for v in verts:
        zs.append(v.z if hasattr(v, 'z') else v[2])
    return max(zs)


def elegir_apoyo_xy(xy, candidatos):
    """
    candidatos: lista de {nombre, z_top, caminable}
    Devuelve el collider de apoyo con mayor z_top en la misma zona (alfombra sobre piso).
    """
    x, y = float(xy[0]), float(xy[1])
    mejor = None
    for c in candidatos:
        if c.get('z_top') is None:
            continue
        if mejor is None or c['z_top'] > mejor['z_top'] + 1e-6:
            mejor = c
        elif abs(c['z_top'] - mejor['z_top']) < 1e-4 and c.get('caminable') and not mejor.get('caminable'):
            mejor = c
    return mejor
