"""tomas_desde_sb (python puro, sin Blender): arma el contrato toma.json que lee ocultar_estorbos.py
a partir de lo que YA decidió el storyboard (sb_scene.json -> director_imagen) y de la pose de cámara
ya resuelta (camara_v2.json -> frame_ini/fin, objetivo). No elige plano, lente, ángulo ni posición."""
import json, sys, os, re

def toma_desde_sb(sb_scene, camara_v2, vineta, camara_obj="camera_4g_master"):
    v = next(x for x in sb_scene["vinetas"] if x.get("id") == vineta)
    t = next(x for x in camara_v2["tomas"] if x["vineta"] == vineta)
    di = v.get("director_imagen", {})
    en_cuadro = [e["id"] for e in di.get("en_cuadro", []) if e.get("id")]
    objetos_sb = [o["nombre"] for o in di.get("objetos", []) if o.get("nombre")]
    return {
        "contrato": "toma_ocultar_v1",
        "toma_id": t["id"], "vineta": vineta,
        "frame_ini": t["frame_ini"], "frame_fin": t["frame_fin"],
        "camara": camara_obj,                       # la cámara ya animada con la pose del SB (no se mueve)
        "objetivo": t["objetivo"],                  # sujeto principal del SB
        "en_cuadro": en_cuadro,                     # protegidos (SB director_imagen.en_cuadro)
        "debe_verse": v.get("debe_verse", []),      # protegidos explícitos (campo nuevo, opcional)
        "objetos_sb": objetos_sb,                   # objetos que el SB pide ver -> protegidos si existen en la escena
        "plano": di.get("plano"), "lente_mm": di.get("lente_mm"), "angulo": di.get("angulo"),
        "movimiento_sb": v.get("director_camara", {}).get("dsl_movimiento"),
        "paso_frames": 1,
    }

if __name__ == "__main__":
    sb, cv, out = sys.argv[1], sys.argv[2], sys.argv[3]
    S = json.load(open(sb)); C = json.load(open(cv))
    for vin in sys.argv[4:]:
        d = toma_desde_sb(S, C, vin)
        json.dump(d, open(os.path.join(out, f"toma_{vin}.json"), "w"), indent=1, ensure_ascii=False)
        print(vin, d["frame_ini"], d["frame_fin"], d["objetivo"], d["en_cuadro"], d["objetos_sb"])
