"""kimodo_adaptador (prototipo, NO ejecuta Kimodo): convierte el camino del planificador MYIA
(mundo Blender Z-arriba, metros, 24 fps) en el JSON de restricciones de Kimodo (Y-arriba, plano XZ,
origen canónico en el cuadro 0, 30 fps) + la línea de comando. Ver docs/source/user_guide/constraints.md."""
import json, math
KIMODO_FPS = 30.0

def a_kimodo_xz(p, p0):
    # Blender (x, y, z-up) -> Kimodo (X, Y-up, Z) = (x, z, -y); luego restar el origen del cuadro 0
    return [round(p[0] - p0[0], 4), round(-(p[1] - p0[1]), 4)]

def camino_a_restricciones(tray_24fps, cada_s=0.5, rumbo=True):
    """tray_24fps: lista [(x,y), ...] por cuadro a 24 fps (salida del planificador). Devuelve (constraints, n_frames, heading0)."""
    n24 = len(tray_24fps); dur = (n24 - 1) / 24.0; n30 = int(round(dur * KIMODO_FPS)) + 1
    p0 = tray_24fps[0]; idx, xz, hd = [], [], []
    paso = max(1, int(cada_s * KIMODO_FPS))
    for f30 in list(range(0, n30, paso)) + ([n30 - 1] if (n30 - 1) % paso else []):
        t = f30 / KIMODO_FPS; i = min(n24 - 1, int(round(t * 24)))
        idx.append(f30); xz.append(a_kimodo_xz(tray_24fps[i], p0))
        j = min(n24 - 1, i + 2); k = max(0, i - 2)
        dx, dy = tray_24fps[j][0] - tray_24fps[k][0], tray_24fps[j][1] - tray_24fps[k][1]
        # rumbo en Kimodo: 0 rad = mirando a +Z. En Blender +Z_kimodo = -Y. (VERIFICAR signo con un ejemplo del demo)
        a = math.atan2(dx, -dy) if (dx or dy) else (hd and math.atan2(hd[-1][1], hd[-1][0]) or 0.0)
        hd.append([round(math.cos(a), 4), round(math.sin(a), 4)])
    c = {"type": "root2d", "frame_indices": idx, "smooth_root_2d": xz}
    if rumbo: c["global_root_heading"] = hd
    return [c], n30, math.atan2(hd[0][1], hd[0][0])

def comando(prompt, constraints_path, n30, salida, modelo="Kimodo-SOMA-RP-v1.2", seed=0):
    dur = round((n30 - 1) / KIMODO_FPS, 2)
    return (f'TEXT_ENCODER_DEVICE=cpu kimodo_gen "{prompt}" --model {modelo} --duration {dur} '
            f'--constraints {constraints_path} --num_samples 2 --seed {seed} --bvh --output {salida}')
