"""camara_calculada: prototipo MYIA (código propio, licencia nuestra).
Ideas estudiadas (no copiadas): espacio tórico (Lino & Christie 2012/2015, ToricCam GPL) y
encuadre de grupo / composer (Phantom Camera MIT, Cinemachine). Solo mathutils de Blender.

camera_toric(A, B, sA, sB, side, beta_deg, phi_deg, lens, sensor, aspect)
  A, B   : puntos 3D (p.ej. cabezas) de los dos sujetos
  sA, sB : posición deseada en pantalla, coordenadas normalizadas [-1,1] (x derecha, y arriba)
  side   : +1 / -1  lado del eje de acción (línea A-B) donde va la cámara -> respeta el eje de 180°
  beta   : ángulo en A entre la prolongación B->A y A->C  (beta un poco mayor que alpha = cámara detrás de A = sobre el hombro;
           ~90 = plano lateral; >90 = cámara del lado de B)
  phi    : elevación del plano de la cámara alrededor del eje A-B (0 = misma altura)
  -> (posición, matriz de rotación 3x3) que pone A en sA y B en sB EXACTO (salvo roll)."""
import math
from mathutils import Vector, Matrix

def _dir_cam(s, lens, sensor, aspect):
    tx = (sensor / 2) / lens; ty = tx / aspect
    return Vector((s[0] * tx, s[1] * ty, -1.0)).normalized()

def camera_toric(A, B, sA, sB, side=+1, beta_deg=30.0, phi_deg=10.0, lens=35.0, sensor=36.0, aspect=16/9, up=Vector((0, 0, 1))):
    A = Vector(A); B = Vector(B)
    dA = _dir_cam(sA, lens, sensor, aspect); dB = _dir_cam(sB, lens, sensor, aspect)
    alpha = math.acos(max(-1, min(1, dA.dot(dB))))            # ángulo que deben subtender A y B
    AB = B - A; L = AB.length; ab = AB / L
    side0 = ab.cross(up).normalized() * side                  # perpendicular horizontal al eje, del lado elegido
    u0 = side0.cross(ab).normalized()
    if u0.dot(up) < 0: u0 = -u0
    phi = math.radians(phi_deg); w = (side0 * math.cos(phi) + u0 * math.sin(phi)).normalized()
    beta = math.pi - math.radians(beta_deg)                   # ángulo interno en A
    if beta >= math.pi - alpha or beta <= 0: raise ValueError(f"beta debe estar entre {math.degrees(alpha):.1f} y 180 para este encuadre")
    AC = L * math.sin(math.pi - alpha - beta) / math.sin(alpha)   # ley de senos (ángulo inscrito = alpha)
    C = A + (ab * math.cos(beta) + w * math.sin(beta)) * AC
    vA = (A - C).normalized(); vB = (B - C).normalized()
    def frame(a, b):
        e1 = a; e2 = (b - a * a.dot(b)).normalized(); return Matrix((e1, e2, e1.cross(e2))).transposed()
    Rm = frame(vA, vB) @ frame(dA, dB).transposed()            # rota cámara->mundo
    return C, Rm, {"alpha_deg": math.degrees(alpha), "dist_A": AC}

def mirar_sin_roll(C, T, up=Vector((0, 0, 1))):
    fwd = (Vector(T) - C).normalized(); right = fwd.cross(up).normalized(); upc = right.cross(fwd)
    return Matrix((right, upc, -fwd)).transposed()

def quitar_roll(C, Rm, A, B, sA, sB, lens, sensor, aspect, up=Vector((0, 0, 1)), it=8):
    """Horizonte recto (roll 0): conserva la posición C y ajusta yaw/pitch para que el punto medio de A y B
    caiga en el punto medio de sA y sB. Devuelve Rm sin roll; el error residual se mide aparte."""
    M = (Vector(A) + Vector(B)) / 2; tgt = ((sA[0] + sB[0]) / 2, (sA[1] + sB[1]) / 2)
    T = M.copy(); Rn = mirar_sin_roll(C, T, up)
    for _ in range(it):
        p = proyectar(C, Rn, M, lens, sensor, aspect)
        if p is None: break
        ex, ey = tgt[0] - p[0], tgt[1] - p[1]
        right = Rn @ Vector((1, 0, 0)); upc = Rn @ Vector((0, 1, 0)); d = (T - C).length
        tx = (sensor / 2) / lens; ty = tx / aspect
        T = T - right * ex * tx * d - upc * ey * ty * d
        Rn = mirar_sin_roll(C, T, up)
    return Rn

def proyectar(C, Rm, P, lens, sensor, aspect):
    p = Rm.transposed() @ (Vector(P) - C)
    if p.z >= 0: return None
    tx = (sensor / 2) / lens; ty = tx / aspect
    return (p.x / -p.z / tx, p.y / -p.z / ty)

def encuadre_grupo(C, Rm, puntos, lens, sensor, aspect, margen=0.08):
    """Phantom/Cinemachine 'group framing': retrocede/avanza por el eje óptico para que TODOS los puntos
    (p.ej. esquinas de las cajas: cabeza y pies) entren con margen. Devuelve nueva C."""
    fwd = -(Rm @ Vector((0, 0, 1))); right = Rm @ Vector((1, 0, 0)); upc = Rm @ Vector((0, 1, 0))
    tx = (sensor / 2) / lens * (1 - margen); ty = (sensor / 2) / lens / aspect * (1 - margen)
    cen = sum((Vector(p) for p in puntos), Vector()) / len(puntos)
    # centrar lateralmente sobre el grupo y calcular distancia mínima
    D = 0.0
    for p in puntos:
        d = Vector(p) - cen; x, y, z = d.dot(right), d.dot(upc), d.dot(fwd)
        D = max(D, abs(x) / tx - z, abs(y) / ty - z)
    return cen - fwd * D

def lado_del_eje(C, A, B, up=Vector((0, 0, 1))):
    ab = (Vector(B) - Vector(A)); n = ab.cross(up)
    return 1 if (Vector(C) - Vector(A)).dot(n) > 0 else -1

def roll_de(Rm, up=Vector((0, 0, 1))):
    return math.degrees(math.asin(max(-1, min(1, (Rm @ Vector((1, 0, 0))).dot(up)))))

def camera_toric_sin_roll(A, B, sA, sB, side=+1, beta_deg=30.0, phi_rango=(-25, 45), lens=35.0, sensor=36.0, aspect=16/9, up=Vector((0, 0, 1)), min_dist=0.45):
    """Busca la elevación phi en la que la solución tórica EXACTA tiene roll ~0 (horizonte recto).
    Así A y B quedan exactamente donde se pidió y la cámara no se ladea."""
    best = None
    phi = phi_rango[0]
    while phi <= phi_rango[1]:
        try:
            C, Rm, info = camera_toric(A, B, sA, sB, side, beta_deg, phi, lens, sensor, aspect, up)
            fwd = -(Rm @ Vector((0, 0, 1)))
            r = abs(roll_de(Rm, up))
            lejos = (C - Vector(A)).length >= min_dist and (C - Vector(B)).length >= min_dist
            if lejos and fwd.dot(up) > -0.95 and (best is None or r < best[0]): best = (r, phi, C, Rm, info)
        except ValueError:
            pass
        phi += 0.25
    if best is None: raise ValueError("sin solución")
    r, phi, C, Rm, info = best
    info["phi_deg"] = phi; info["roll_residual_deg"] = r
    return C, Rm, info
