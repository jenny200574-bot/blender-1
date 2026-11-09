"""Oclusión y reparación por storyboard (R14): rayos sujeto-cámara, universal."""
import math


def sujetos_protegidos(S, objetivo_vineta, act_ids):
    """Entidades que no se ocultan con visible_camera (sujetos SB + hombro OTS)."""
    prot = set()
    if objetivo_vineta and objetivo_vineta in act_ids:
        prot.add(objetivo_vineta)
    for sid in S.get('sujetos') or []:
        if sid in act_ids:
            prot.add(sid)
    if S.get('ots'):
        esc = S['ots'][0]
        if esc in act_ids:
            prot.add(esc)
    if S.get('pov') and S['pov'] in act_ids:
        prot.add(S['pov'])
    return prot


def entidad_de_objeto(nombre, act_ids):
    if not nombre:
        return None
    for pid in sorted(act_ids, key=len, reverse=True):
        if nombre == pid or nombre.startswith(pid + '.') or nombre.startswith(pid + '_'):
            return pid
    return None


def puede_ocultar_obstaculo(nombre_obj, sujetos_prot, act_ids):
    """True si el obstáculo no es sujeto protegido (personaje/objeto en cuadro por composición OTS)."""
    ent = entidad_de_objeto(nombre_obj, act_ids)
    if ent is None:
        return True
    return ent not in sujetos_prot


def cuadros_reparacion(malos, f0, f1, max_cuadros=6):
    fs = sorted({int(m[0]) for m in (malos or []) if m and m[0] is not None})
    if not fs:
        return [int(f0), int((f0 + f1) // 2)]
    extra = [int(f0), int(f1)]
    for e in extra:
        if e not in fs:
            fs.append(e)
    return sorted(fs)[:max_cuadros]


def contar_bloqueadores_rayos(loc, puntos, env_bvh, oth_bvh, eps=0.01):
    """Objeto → votos de bloqueo en rayos sujeto-cámara."""
    counts = {}
    if loc is None or not puntos:
        return counts

    def _ray(bv):
        if bv is None:
            return
        for p in puntos:
            d = p - loc
            dist = d.length
            if dist < eps:
                continue
            h = bv.ray_cast(loc, d / dist, max(0.0, dist - eps))
            if h[0] is not None:
                who = bv.quien(h[2])
                if who:
                    counts[who] = counts.get(who, 0) + 1
                break

    _ray(env_bvh)
    _ray(oth_bvh)
    return counts


def elegir_a_ocultar(counts, sujetos_prot, act_ids, min_votos=1, max_objs=24):
    salida = []
    for name, v in sorted(counts.items(), key=lambda x: -x[1]):
        if v < min_votos:
            continue
        if not puede_ocultar_obstaculo(name, sujetos_prot, act_ids):
            continue
        salida.append(name)
        if len(salida) >= max_objs:
            break
    return salida


def reflejar_xy_sobre_eje(p, a, b):
    """Refleja p (x,y) respecto a la recta AB en el plano horizontal."""
    if hasattr(p, 'x'):
        px, py, pz = float(p.x), float(p.y), float(p.z)
    else:
        px, py, pz = float(p[0]), float(p[1]), float(p[2])
    ax, ay = float(a.x if hasattr(a, 'x') else a[0]), float(a.y if hasattr(a, 'y') else a[1])
    bx, by = float(b.x if hasattr(b, 'x') else b[0]), float(b.y if hasattr(b, 'y') else b[1])
    abx, aby = bx - ax, by - ay
    ln2 = abx * abx + aby * aby
    if ln2 < 1e-12:
        return p
    t = ((px - ax) * abx + (py - ay) * aby) / ln2
    projx, projy = ax + t * abx, ay + t * aby
    nx, ny = px + 2 * (projx - px), py + 2 * (projy - py)
    if hasattr(p, 'x'):
        try:
            from mathutils import Vector
            return Vector((nx, ny, pz))
        except ImportError:
            p.x, p.y, p.z = nx, ny, pz
            return p
    return (nx, ny, pz)


def motivos_reparables(malos):
    m = {row[1] if len(row) > 1 else '' for row in (malos or [])}
    hay_eje = any('180' in x for x in m)
    hay_holg = any('pegada' in x or 'dentro de geometría' in x for x in m)
    hay_tap = any('tapado' in x for x in m)
    hay_enc = any('fuera de cuadro' in x for x in m)
    return hay_eje, hay_holg, hay_tap, hay_enc


def nombres_obstaculo_en_malos(malos):
    """Extrae nombres de objeto de mensajes de validación (tapado, pegada, dentro)."""
    import re
    out = {}
    for row in malos or []:
        msg = row[1] if len(row) > 1 else ''
        if not any(k in msg for k in ('tapado', 'pegada', 'dentro de geometría', 'escenario', 'personaje')):
            continue
        for m in re.finditer(r'\(([^)]+)\)', msg):
            raw = m.group(1).strip()
            if ':' in raw:
                raw = raw.split(':', 1)[1].strip()
            if raw:
                out[raw] = out.get(raw, 0) + 4
    return out


def espejar_tray_camara_eje(tray, centro_a, centro_b):
    """Refleja la posición de la cámara al otro lado del eje 180° (plano XY)."""
    salida = []
    for x in tray or []:
        y = dict(x)
        loc = x.get('loc')
        if loc is not None:
            y['loc'] = reflejar_xy_sobre_eje(loc, centro_a, centro_b)
        salida.append(y)
    return salida


def fusionar_conteos_bloqueo(*dicts):
    total = {}
    for d in dicts:
        for k, v in (d or {}).items():
            total[k] = total.get(k, 0) + int(v)
    return total
