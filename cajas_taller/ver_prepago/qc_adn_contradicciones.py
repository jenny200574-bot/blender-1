#!/usr/bin/env python3
"""QC ADN sin IA: busca contradicciones por elemento (Jenny H2-H6, dictamen §53). Uso: qc_adn_contradicciones.py DIR [--json]"""
import re,sys,json,pathlib
NEG=re.compile(r"\b(no|sin|nunca|prohibid\w*|not|never|without|evitar)\b",re.I)
REGLAS=[
 ("ANILLO_vs_MANILLA",r"\banillo\b|\bring\b|en un dedo|finger",None),
 ("BRAZALETE_ANCHO",r"brazalete ancho",None),
 ("AURORAS",r"aurora",None),
 ("PROHIBE_LUZ_CIUDAD",r"(sin|no)\s+(luz|luces) de (la )?ciudad",'raw'),
 ("LOW_POLY_EN_ADN",r"low[- ]?poly|bajo poligonaje",None),
 ("MANIQUI",r"maniqu[ií]|mannequin",None),
 ("MOCHILA",r"mochila|backpack",None),
 ("EDAD",r"\bjoven\b|\b\d{1,2}\s*(años|years)|adolescente|teen|niñ[ao]\b",None),
 ("LANZA_ROSA",r"vara vertical rosa|lanza rosa",None),
 ("TEXTO_EN_IMAGEN",r"\bImi\.\.\.",None),
]
def scan(p):
    hits=[]
    for i,l in enumerate(p.read_text(errors="ignore").splitlines(),1):
        for n,rx,mode in REGLAS:
            m=re.search(rx,l,re.I)
            if not m: continue
            pre=l[:m.start()]
            if mode!='raw' and NEG.search(pre): continue  # mención negada = regla, no ADN
            hits.append((n,i,l.strip()[:140]))
    return hits
d=pathlib.Path(sys.argv[1]); out={}
for p in sorted(d.glob("*.txt"))+sorted(d.glob("*.md")):
    h=scan(p); out[p.name]={"estado":"FAIL" if h else "PASS","hallazgos":h}
# contradicción cruzada: pulsera definida de >1 forma
tipos=set()
for p in d.glob("*.txt"):
    t=p.read_text(errors="ignore").lower()
    for k in ["anillo","brazalete ancho","manilla","punto cian"]:
        if k in t: tipos.add(k)
if "--json" in sys.argv: print(json.dumps(out,ensure_ascii=False,indent=1)); sys.exit()
for f,v in out.items():
    print(f"{v['estado']:4} {f} ({len(v['hallazgos'])})")
    for n,i,l in v["hallazgos"][:8]: print(f"     L{i} {n}: {l}")
print("Definiciones de pulsera en carpeta:",sorted(tipos))
sys.exit(1 if any(v["estado"]=="FAIL" for v in out.values()) else 0)
