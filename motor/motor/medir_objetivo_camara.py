"""Puntos medidos del objetivo de cámara. No inventa posiciones ni el sensor."""
import math

SENSOR_ANCHO_MM_APROBADO = 36

def _xyz(p):
    if isinstance(p, bool) or isinstance(p, (str, bytes)):
        return None
    try:
        x, y, z = float(p[0]), float(p[1]), float(p[2])
    except (TypeError, ValueError, IndexError):
        return None
    if not all(math.isfinite(v) for v in (x, y, z)):
        return None
    return (x, y, z)

def _con_extension(pts):
    if len(pts) < 2:
        return False
    a = pts[0]
    return any(any(abs(p[i] - a[i]) > 1e-9 for i in range(3)) for p in pts[1:])

def puntos_de_objetivo(nombre, toma, propios, hijos, bbox):
    """Vértices propios, si no los de los hijos, si no la caja del mundo con extensión real."""
    pts = [q for q in (_xyz(p) for p in (propios or [])) if q]
    if not pts:
        for grupo in hijos or []:
            pts.extend(q for q in (_xyz(p) for p in (grupo or [])) if q)
    if not pts:
        caja = [q for q in (_xyz(p) for p in (bbox or [])) if q]
        if _con_extension(caja):
            pts = caja
    if not pts:
        raise ValueError(
            f"Objetivo '{nombre}' de la toma '{toma or 'desconocida'}' no tiene vértices "
            "(malla propia, hijos evaluados ni bounding box del mundo). No se inventa su posición."
        )
    return pts

def sensor_ancho_mm(camera):
    """Lee camera.sensor_width_mm. El valor aprobado por Ricardo es 36 mm."""
    w = None
    if isinstance(camera, dict):
        w = camera.get('sensor_width_mm')
        if w is None:
            for shot in camera.get('shots') or []:
                if isinstance(shot, dict) and shot.get('sensor_width_mm') is not None:
                    w = shot['sensor_width_mm']
                    break
    if isinstance(w, bool) or not isinstance(w, (int, float)) or not math.isfinite(w) or w <= 0:
        raise ValueError('Falta camera.sensor_width_mm; no se inventa el ancho del sensor')
    if float(w) != SENSOR_ANCHO_MM_APROBADO:
        raise ValueError(f'camera.sensor_width_mm={w} no es el valor aprobado ({SENSOR_ANCHO_MM_APROBADO} mm)')
    return float(SENSOR_ANCHO_MM_APROBADO)
