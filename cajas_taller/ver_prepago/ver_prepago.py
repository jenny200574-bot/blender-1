#!/usr/bin/env python3
"""VER · pre-gasto (SECO, nunca llama APIs ni paga). Plan R1-R5 + addendum Jenny.
Uso: ver_prepago.py MANIFIESTO.json [--ledger ledger.json] [--guarda cajas/HABILITAR_PAGO_X]
Manifiesto (envío T1 / FC):
{"canal":"..","escena":"11","ledger_id":"..",
 "pj":[{"id":"kael","adn":"ruta.txt","sha256":"..","sellado":true}],
 "entorno":{"adn":"env_v2.json|txt","sha256":"..","sellado":true},
 "imagenes":[{"rol":"bg|molde|hoja|objeto|estilo","path":"..","sha256":"..","pj":"kael"}],
 "texto":"prompt variable"}
Salida JSON {ok, checks:[{id,ok,detalle}]}; exit 1 si algún FAIL (para stopAndError en n8n)."""
import json,sys,hashlib,pathlib,re,subprocess,argparse
A=pathlib.Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def chk(L,i,ok,d=""): L.append({"id":i,"ok":bool(ok),"detalle":d})
def qc_texto(p):
    import importlib.util
    s=importlib.util.spec_from_file_location("qc",A/"qc_adn_contradicciones.py")
    src=(A/"qc_adn_contradicciones.py").read_text().split("d=pathlib.Path(sys.argv[1])")[0]
    g={};exec(src,g);return g["scan"](pathlib.Path(p))
FIJO=re.compile(r"cabello|pelo|ojos|sudadera|cárdigan|hex|#[0-9a-f]{6}|auroras?|skyline",re.I)
# ARGON TEXTO (inmi 2-nov-2026, orden Ricardo t523u): VER seco para los pasos Argon de texto del paso 00 (4, 4p, 5, 4a1/4b1/4c1).
# El manifiesto lo escribe «paso00_cadena cotizar» (prepago_<caja>_<canal>_capNN.json). Revisa: compuerta HABILITAR_PAGO_00 (monto, desde,
# pasos, canal, capítulo), ledger legible, lo ya gastado desde «desde», y que la cotización (fresca, mismo canal/capítulo, todo cabe por
# llamada) quepa en lo que queda del tope. Nunca paga.
def argon_texto_r(M):
    import csv,datetime as dt
    L=[];G=pathlib.Path(M.get("guarda") or "");kv={}
    if G.is_file(): kv=dict(re.findall(r"^\s*([a-z_]+)\s*=\s*(\S+)\s*$",G.read_text(errors="replace"),re.M))
    chk(L,"guarda_pago_presente",G.is_file(),str(G) if G.is_file() else f"falta {G} → pago cerrado")
    monto=desde=None
    try: monto=float(kv["monto"]);desde=dt.datetime.fromisoformat(kv["desde"])
    except Exception: pass
    chk(L,"guarda_monto_desde",monto is not None and desde is not None and desde.tzinfo is not None,f"monto={kv.get('monto')} desde={kv.get('desde')}")
    pasos=[x.strip().lower() for x in kv.get("pasos","").split(",") if x.strip()]
    chk(L,"guarda_paso",str(M.get("paso")) in pasos,f"paso {M.get('paso')} en {pasos}")
    chk(L,"guarda_canal_capitulo",(not kv.get("canal") or kv["canal"]==M.get("canal")) and (not kv.get("capitulo") or str(kv["capitulo"])==str(M.get("capitulo"))),
        f"guarda canal={kv.get('canal')} cap={kv.get('capitulo')} · manifiesto canal={M.get('canal')} cap={M.get('capitulo')}")
    led=pathlib.Path(M.get("ledger") or "");g=0.0;okl=False
    try:
        with open(led,encoding="utf-8",newline="") as f:
            R=csv.DictReader(f);okl={"id","fecha","costo_estimado_usd","estado"}<=set(R.fieldnames or [])
            for r in R:
                if not desde or not str(r.get("id","")).startswith("taller00-") or r.get("estado")=="no_cobrado": continue
                try: fe=dt.datetime.fromisoformat(r["fecha"])
                except Exception: continue
                if fe.tzinfo and fe>=desde: g+=float(r.get("costo_estimado_usd") or 0)
    except Exception as e: okl=False
    chk(L,"ledger_legible",okl,f"{led} (cada llamada se escribe en el ledger ANTES de llamar: myia_argon.llamar)")
    C=pathlib.Path(M.get("cotizacion") or "");c={}
    try: c=json.loads(C.read_text())
    except Exception: pass
    chk(L,"cotizacion_ok",c.get("ok") is True and c.get("caja")==M.get("caja") and c.get("canal")==M.get("canal") and str(c.get("capitulo"))==str(M.get("capitulo")),str(C))
    fresca=False
    try: fresca=(dt.datetime.now(dt.timezone.utc)-dt.datetime.strptime(c["hora"],"%Y-%m-%dT%H:%M:%S%z")).total_seconds()<3*3600
    except Exception: pass
    chk(L,"cotizacion_fresca",fresca,f"hora {c.get('hora')} (máx 3 h)")
    chk(L,"cabe_por_llamada",c.get("todo_cabe") is True,f"tope por llamada {c.get('tope_por_llamada_usd')}")
    pend=round(sum(float(p.get("peor_caso_usd") or 0) for p in c.get("pasos") or [] if not p.get("ya_hecho")),4)
    resto=round((monto or 0)-g,4)
    chk(L,"cabe_en_tope_total",monto is not None and pend<=resto+1e-9,f"peor caso {pend} · tope {monto} · ya gastado {round(g,4)} · queda {resto}")
    crit=[x for x in L if not x["ok"]]
    return {"ok":not crit,"seco":True,"tipo":"argon_texto","caja":M.get("caja"),"paso":M.get("paso"),"llamadas_pagas":0,"usd_gastado":0,"fallas":len(crit),"peor_caso_usd":pend,"queda_usd":resto,"checks":L}
def argon_texto(M):
    r=argon_texto_r(M);print(json.dumps(r,ensure_ascii=False,indent=1));sys.exit(0 if r["ok"] else 1)
def main():
    ap=argparse.ArgumentParser();ap.add_argument("m");ap.add_argument("--ledger");ap.add_argument("--guarda")
    a=ap.parse_args();M=json.load(open(a.m));base=pathlib.Path(a.m).parent;L=[]
    if M.get("tipo")=="argon_texto": return argon_texto(M)
    R=lambda p:(base/p) if not pathlib.Path(p).is_absolute() else pathlib.Path(p)
    # 1 canal sellado: cada PJ con ADN sellado, sha coincide, QC texto PASS
    for pj in M.get("pj",[]):
        f=R(pj["adn"]);ex=f.is_file()
        chk(L,f"canal_sellado:{pj['id']}",ex and pj.get("sellado") and pj.get("sha256")==(sha(f) if ex else None),
            "falta archivo" if not ex else ("no sellado" if not pj.get("sellado") else ("sha distinto" if pj.get("sha256")!=sha(f) else "ok")))
        if ex:
            h=qc_texto(f);chk(L,f"qc_adn:{pj['id']}",not h,"; ".join(f"L{i} {n}" for n,i,_ in h[:5]))
    # 2 entorno: sellado + sha + sin auroras (H6)
    e=M.get("entorno")
    if not e: chk(L,"entorno_sellado",False,"sin entorno en manifiesto")
    else:
        f=R(e["adn"]);ex=f.is_file()
        chk(L,"sha_entorno",ex and e.get("sellado") and e.get("sha256")==(sha(f) if ex else None),"ok" if ex else "falta archivo")
        if ex: h=qc_texto(f);chk(L,"qc_entorno",not h,"; ".join(f"L{i} {n}" for n,i,_ in h[:5]))
    # 3 orden T1: 1 bg, 2 molde, 3..N hoja/objeto, última estilo
    roles=[i["rol"] for i in M.get("imagenes",[])]
    okord=len(roles)>=3 and roles[0]=="bg" and roles[1]=="molde" and roles[-1]=="estilo" and all(r in("hoja","objeto") for r in roles[2:-1])
    chk(L,"orden_T1",okord," > ".join(roles))
    for i in M.get("imagenes",[]):
        f=R(i["path"]);chk(L,f"sha_img:{f.name}",f.is_file() and (not i.get("sha256") or i["sha256"]==sha(f)),"ok" if f.is_file() else "falta")
    # 4 conteo PJ = hojas
    hojas={i.get("pj") for i in M.get("imagenes",[]) if i["rol"]=="hoja"}; pjs={p["id"] for p in M.get("pj",[])}
    chk(L,"conteo_PJ_eq_hojas",hojas==pjs,f"pj={sorted(pjs)} hojas={sorted(x for x in hojas if x)}")
    # 5 texto solo VARIABLE (R3)
    t=M.get("texto","");hit=FIJO.findall(t);chk(L,"sin_FIJO_en_texto",not hit,",".join(sorted(set(hit)))[:200])
    # 6 ledger antes de pagar (stub): ledger_id debe existir y estar en estado registrado/pendiente, sin cobro
    lid=M.get("ledger_id")
    if a.ledger and lid:
        lj=json.load(open(a.ledger));ent=lj.get(lid) if isinstance(lj,dict) else next((x for x in lj if x.get("id")==lid),None)
        chk(L,"ledger_antes_de_pago",bool(ent),"registrado" if ent else f"{lid} no está en ledger")
    else: chk(L,"ledger_antes_de_pago",False,"falta --ledger o ledger_id")
    # 7 guarda de pago (solo informa; en seco nunca se paga)
    g=pathlib.Path(a.guarda) if a.guarda else None
    chk(L,"guarda_pago_presente",bool(g and g.is_file()),"guarda ausente → pago cerrado (correcto en seco)")
    crit=[c for c in L if not c["ok"] and c["id"]!="guarda_pago_presente"]
    print(json.dumps({"ok":not crit,"seco":True,"llamadas_pagas":0,"usd_gastado":0,"fallas":len(crit),"checks":L},ensure_ascii=False,indent=1))
    sys.exit(1 if crit else 0)
if __name__=="__main__": main()
