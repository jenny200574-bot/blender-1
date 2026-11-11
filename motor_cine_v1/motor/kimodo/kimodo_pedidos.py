"""kimodo_pedidos (213, CPU, gratis): del plan A*+RVO2 -> pedidos de Kimodo por tramo de movimiento (caminar/girar) de cada personaje humano.
Mismo método del lab aprobado (lab/kimodo_prueba_20261109, Ricardo t995u): restricción root2d cada 0.5 s + global_root_heading,
Kimodo-SOMA-RP-v1.2 ('--model soma'), seed 7, 1 muestra, --no-postprocess, BVH con T-pose estándar, texto en CPU.
Escala: Kimodo genera en tamaño SOMA (1.765 m); el molde mide altura_m -> el camino se pide x (1.765/altura) para que, al
retargetear con Mwni (que escala por altura), el personaje recorra EXACTAMENTE el camino del plan.
Uso: python3 kimodo_pedidos.py --corrida DIR"""
import json, math, argparse, os
SOMA_ALTURA_M = 1.765      # span del esqueleto SOMA77 en reposo (medido en Blender 5.2.3 sobre el BVH del lab)
KIMODO_FPS = 30.0; CADA_S = 0.5; PAD = 12  # 0.5 s de pie antes y después de cada tramo
CORRER_M_S = 2.0           # velocidad (escala SOMA) desde la que se pide correr

def pedidos(E, M, PL):
    fps = E['fps']; N = PL['N']; out = []
    alt = {p['id']: float(p.get('altura_m') or 1.0) for p in E['personajes']}
    suj = {p['id']: p.get('sujeto_kimodo') or 'A person' for p in E['personajes']}   # del ADN (m1_preparar); ya no fijo «A child»
    for pid, fr in PL['personajes'].items():
        P = M['personajes'].get(pid, {})
        if P.get('acople'): continue
        # (el motor en Blender decide si el molde es humano; uno no humano ignora su pedido)
        s = SOMA_ALTURA_M / alt[pid]; f = 1; k = 0
        while f <= N:
            if fr[f - 1][4] in ('caminar', 'girar'):
                g = f
                while g < N and fr[g][4] in ('caminar', 'girar'): g += 1
                a = max(1, f - PAD, P.get('visible_desde', 1)); b = min(N, g + PAD)
                tipo = 'caminar' if any(fr[i - 1][4] == 'caminar' for i in range(f, g + 1)) else 'girar'
                dist = fr[g - 1][3] - fr[f - 1][3]; v = dist * s / max(1e-6, (g - f + 1) / fps)
                dr = (fr[g - 1][2] - fr[f - 1][2] + 180) % 360 - 180
                if tipo == 'girar':
                    lado = 'right' if dr < 0 else 'left'; grados = int(round(abs(dr) / 45.0) * 45) or 45
                    num = {45: 'forty-five', 90: 'ninety', 135: 'one hundred thirty-five', 180: 'one hundred eighty'}.get(grados, 'ninety')
                    prompt = f"{suj[pid]} stands, turns {num} degrees to the {lado} in place, then stands still"
                elif v > CORRER_M_S:
                    prompt = f"{suj[pid]} runs forward to a point and stops"
                else:
                    prompt = f"{suj[pid]} walks forward to a point and stops"
                x0, y0 = fr[a - 1][0], fr[a - 1][1]
                n30 = int(round((b - a) / fps * KIMODO_FPS)) + 1; paso = int(CADA_S * KIMODO_FPS)
                idx = list(range(0, n30, paso)) + ([n30 - 1] if (n30 - 1) % paso else [])
                xz, hd = [], []
                for j in idx:
                    i = min(b, a + int(round(j / KIMODO_FPS * fps)))
                    x, y, r = fr[i - 1][0], fr[i - 1][1], math.radians(fr[i - 1][2])
                    xz.append([round((x - x0) * s, 4), round(-(y - y0) * s, 4)])          # Blender (x, y) -> Kimodo (X, Z) = (x, -y)
                    ang = math.atan2(math.cos(r), -math.sin(r)); hd.append([round(math.cos(ang), 4), round(math.sin(ang), 4)])
                nombre = f"{pid}_{k:02d}"
                out.append({"nombre": nombre, "personaje": pid, "f0": a, "f1": b, "tramo": [f, g], "tipo": tipo, "prompt": prompt,
                            "duracion_s": round((n30 - 1) / KIMODO_FPS, 2), "n30": n30, "escala_soma": round(s, 5), "p0": [x0, y0],
                            "vel_soma_m_s": round(v, 3), "vel_plan_m_s": round(dist / max(1e-6, (g - f + 1) / fps), 3),
                            "constraints": [{"type": "root2d", "frame_indices": idx, "smooth_root_2d": xz, "global_root_heading": hd}]})
                k += 1; f = g + 1
            else: f += 1
    return out

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--corrida', required=True); a = ap.parse_args(); C = a.corrida
    E = json.load(open(f'{C}/entrada_motor.json')); M = json.load(open(f'{C}/movimiento.json')); PL = json.load(open(f'{C}/plan.json'))
    ped = pedidos(E, M, PL); os.makedirs(f'{C}/kimodo', exist_ok=True)
    for p in ped: json.dump(p['constraints'], open(f"{C}/kimodo/{p['nombre']}.json", 'w'))
    json.dump({"contrato": "kimodo_pedidos_v1", "modelo": "soma (Kimodo-SOMA-RP-v1.2)", "seed": 7, "num_samples": 1, "no_postprocess": True,
               "bvh_standard_tpose": True, "text_encoder_device": "cpu", "soma_altura_m": SOMA_ALTURA_M, "pedidos": [{k: v for k, v in p.items() if k != 'constraints'} for p in ped]},
              open(f'{C}/kimodo/pedidos.json', 'w'), indent=1, ensure_ascii=False)
    print('RESULT_KIMODO_PEDIDOS', json.dumps({"pedidos": len(ped), "personajes": sorted({p['personaje'] for p in ped}), "segundos_total": round(sum(p['duracion_s'] for p in ped), 1)}))
