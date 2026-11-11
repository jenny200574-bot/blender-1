#!/usr/bin/env python3
"""MYIA · Taller n8n · Paso 00 · RAMAS 4a (escenarios), 4b (objetos de la historia), 4c (objetos del lugar).
Staging 213 SOLAMENTE. Lo llama paso00_cadena.py:  paso00_cadena.py ramas <caja> --canal C --capitulo N [--corrida ID]

TODO GRATIS: no llama a Argon ni a Nano Banana, no usa red. Toma la SALIDA DE ARGON que dejó la caja 4p
(respuestas/escenarios.json = 2a, respuestas/objetos.json = 2b) y la BASE de la caja 4 (respuestas/base.json).
- 4a / 4b / 4c       → fichas (escenarios / objetos tipo «historia» / objetos tipo «lugar» agrupados por escenario).
- 4a1 / 4b1 / 4c1    → (orden 58, t385u) son LLAMADAS REALES A ARGON, pero NO corren aquí: las corre paso00_cadena.py
                         (cotizar/correr investigar_escenarios | investigar_objetos_historia | investigar_objetos_lugar).
                         Aquí solo se muestra su estado (gratis). Dejan respuestas/inv_escenarios.json, inv_obj_historia.json, inv_obj_lugar.json.
- Todas las cajas siguientes usan la INVESTIGACIÓN (4a1/4b1/4c1) cuando existe; si no, la salida de 4p (2a/2b).
- 4a2                → (orden 60) arma la entrada y BLENDER (headless, gratis) construye el molde 3D de cada escenario con molde:
                         ramas/moldes/<id>/{molde.blend, planta.png, cam_NN_escX.png, luz_escX.png, molde.json} + ramas/moldes/<id>.png (vista principal).
                         Script genérico: cajas/blender_molde.py. Si la receta no cambió, reutiliza el molde (no vuelve a renderizar).
- (orden 61) ambiente_vivo de 4a1 = zona AMBIENTE (ids amb-…, origen «ambiente»): va a Blender (4a2), a la galería y al plan de 4a5;
                         si un elemento coincide con un objeto de la historia (catálogo, 4b1/4c1) se marca ascender_a_oficial y conserva sus datos.
- 4a4                → estado de los prompts de escenario (los hace paso00_cadena «prompts_escenarios», Argon pago; orden 59).
- 4a5 / 4b2 / 4c2    → cotizan las imágenes de Nano Banana (precio por imagen de precios_myia.json de la app). NO llaman.
- 4a3 / 4a6 / 4b3 / 4c3 → galería grande (orden 51): HTML en <carpeta>/ramas/galerias/.
Salida: un dict (paso00_cadena.py lo imprime como una línea JSON).
"""
import os, json, math, time, argparse, html, shutil, subprocess, hashlib, fcntl
from pathlib import Path

B = Path('/opt/myia-staging-arreglos-20261026'); REPO = B / 'repo'
TRABAJO = Path('/opt/myia-taller-n8n/trabajo/paso00_cadena')
TOPE_LLAMADA = 0.75
BLENDERS = ['/opt/myia-herramientas/blender-4.2.3-linux-x64/blender', '/opt/blender/actual/blender']   # 4.2.3 LTS (ya instalado en 213; solo se ejecuta)
SCRIPT_MOLDE = Path(__file__).resolve().parent / 'blender_molde.py'
CAJAS = ['4a', '4a1', '4a2', '4a3', '4a4', '4a5', '4a6', '4b', '4b1', '4b2', '4b3', '4c', '4c1', '4c2', '4c3']

def ahora(): return time.strftime('%Y-%m-%dT%H:%M:%S%z')

def carpeta(canal, capitulo):
    base = TRABAJO / canal
    ds = sorted(base.glob(f'cap{int(capitulo):02d}_*')) if str(capitulo).isdigit() else sorted(base.glob(f'cap*_{capitulo}'))
    return ds[0] if ds else None

def archivo_resp(D, nombre):
    """t353u: misma regla que paso00_cadena.archivo_resp. Reparada si resultados dice «reparado»; y la resolución del 4r
    (<paso>.resuelto.json) SOLO si se hizo sobre ese mismo archivo (sha). La original nunca se pisa."""
    f = D / 'respuestas' / f'{nombre}.json'; fr = D / 'respuestas' / f'{nombre}.reparado.json'
    try: r = json.loads((D / 'resultados' / f'{nombre}.json').read_text()) if (D / 'resultados' / f'{nombre}.json').is_file() else {}
    except Exception: r = {}
    f0 = fr if (r.get('estado') == 'reparado' or (r.get('estado') == 'incompleto' and r.get('reparacion'))) and fr.is_file() else f
    fz = D / 'respuestas' / f'{nombre}.resuelto.json'
    if fz.is_file() and f0.is_file():
        try:
            z = json.loads(fz.read_text(encoding='utf-8')).get('_resolucion') or {}
            if z.get('fuente_archivo') == f0.name and z.get('fuente_sha') == hashlib.sha256(f0.read_bytes()).hexdigest(): return fz
        except Exception: pass
    return f0

def leer(D, nombre):
    f = D / 'respuestas' / f'{nombre}.json' if nombre.endswith(('.reparado', '.resuelto')) else archivo_resp(D, nombre)
    if not f.is_file(): return None
    t = f.read_text(encoding='utf-8').strip()
    if t.startswith('```'): t = t.strip('`'); t = t[t.find('{'):]
    try: return json.loads(t[t.find('{'):t.rfind('}') + 1])
    except Exception: return None

REF_4A5 = 3   # t310u: peor caso de imágenes de entrada por pedido de pintura (molde + estilo + base de la edición)

def precio_imagen(canal=None, n_img=1, chars=0):
    """t310u (Ricardo, 2-nov-2026) — GENÉRICO: precio por imagen del MODELO Y TALLA DEL CANAL (channels.data.imagen_modelo / imagen_talla),
    con el MISMO cálculo que el motor que paga (paso00_pintar.precio_llamada: lista + referencia_extra por imagen extra, y tramo por
    tokens si está vigente). Antes 4a5/4a6/4b3/4c3 tomaban el modelo por defecto del servidor (VS_NB_MODELS, p. ej. gemini-3-pro-image
    a 0,134) a 2K fijo, aunque el canal pinte con otro modelo o talla → la cotización no cuadraba con lo cobrado.
    Sin canal, o si el canal no tiene modelo/talla/precio, queda el cálculo viejo y el nombre del modelo lo dice."""
    if canal:
        try:
            import estilo_taller as ET_, paso00_pintar as PNT
            I = ET_.imagen_canal(ET_.canal_datos(canal))
            return float(PNT.precio_llamada(I, PNT.tramo(I['modelo'], I['talla']), chars, n_img)), f"{I['modelo']} {I['talla']} (canal)"
        except Exception as exc:
            u, m = precio_imagen_servidor()
            return u, f"{m} 2K (modelo del servidor: el canal no sirve para cotizar: {str(exc)[:120]})"
    return precio_imagen_servidor()

def precio_imagen_servidor():
    """Precio de UNA imagen de Nano Banana según la app de staging (precios_myia.json). Solo lee el NOMBRE del modelo del servidor."""
    import sys
    sys.path.insert(0, str(REPO))
    try:
        for p in os.listdir('/proc'):
            if p.isdigit():
                try:
                    if b'servidor_real.py' in open(f'/proc/{p}/cmdline', 'rb').read():
                        for x in open(f'/proc/{p}/environ', 'rb').read().split(b'\0'):
                            if x.startswith(b'VS_NB_MODELS='): os.environ['VS_NB_MODELS'] = x.split(b'=', 1)[1].decode()
                        break
                except Exception: pass
    except Exception: pass
    import precios_myia as PR
    m = PR.modelo_imagen()
    return float(PR.usd_imagen(m, '2K')), m

def est_argon(chars):   # misma fórmula que myia_argon.estimar (peor caso: entrada ×2/M por token aprox. + 65536 de salida ×10/M)
    return round(math.ceil(chars / 3) * 2 / 1e6 + 65536 * 10 / 1e6, 4)

# ---------- fichas ----------
def datos(D):
    base, e2a, e2b = leer(D, 'base'), leer(D, 'escenarios'), leer(D, 'objetos')
    return base, e2a, e2b

def inv(D, nombre):
    """Investigación 4a1/4b1/4c1 ya unida (solo si su resultado quedó ok). Devuelve {id: registro} y la info del taller."""
    f = D / 'resultados' / f'{nombre}.json'
    try: est = json.loads(f.read_text()).get('estado') if f.is_file() else None
    except Exception: est = None
    ok = est in ('ok', 'reparado')   # PISTA INMI (2026-10-29): orden 72 — «reparado» (arreglo local aplicado con OK) también sirve: se lee su .reparado.json
    j = (leer(D, f'{nombre}.reparado') if est == 'reparado' else None) or (leer(D, nombre) if ok else None)
    if not isinstance(j, dict): return None, None
    clave, idk = ('escenarios', 'escenario_id') if nombre in ('inv_escenarios', 'prompts_escenarios') else ('objetos', 'objeto_id')
    return {x.get(idk): x for x in j.get(clave, []) if isinstance(x, dict)}, j

def nombres_inv(caja): return {'4a': 'inv_escenarios', '4b': 'inv_obj_historia', '4c': 'inv_obj_lugar'}[caja[:2]]

def fichas_escenarios(base, e2a, iv=None):
    cat = {x['id']: x for x in (base or {}).get('catalogo_oficial', {}).get('escenarios', [])}
    esc_base = (base or {}).get('escenas', [])
    out = []
    for x in e2a.get('escenarios', []):
        i = x.get('escenario_id'); c = cat.get(i, {})
        mis = [s for s in esc_base if s.get('escenario_id') == i]
        val = lambda s, k: (s.get(k) or {}).get('valor') if isinstance(s.get(k), dict) else s.get(k)
        out.append({'id': i, 'nombre': c.get('nombre', i), 'int_ext': c.get('int_ext'), 'escenas': c.get('escenas') or [s.get('numero') for s in mis],
                    'horas': sorted({str(val(s, 'hora')) for s in mis if val(s, 'hora')}), 'climas': sorted({str(val(s, 'clima')) for s in mis if val(s, 'clima')}),
                    'solo_recuerdo_o_pantalla': x.get('solo_recuerdo_o_pantalla'), 'elementos': x.get('elementos', []),
                    'variantes_estado': x.get('variantes_estado', []), 'estado_por_escena': x.get('estado_por_escena', []),
                    'fuente': '4a1' if (iv or {}).get(i) else '4p', 'investigacion': (iv or {}).get(i)})
    return out

def fichas_objetos(base, e2b, tipo, iv=None):
    cat = {x['id']: x for x in (base or {}).get('catalogo_oficial', {}).get('objetos', [])}
    cesc = {x['id']: x.get('nombre', x['id']) for x in (base or {}).get('catalogo_oficial', {}).get('escenarios', [])}
    out = []
    for x in e2b.get('objetos', []):
        cl_ = (x.get('clase') or '').strip()   # t453u: catálogo de 3 clases (personaje/escenario/utileria) — igual que 4b2/4c2 (paso00_pintar)
        if not ((cl_ == 'personaje' and tipo == 'historia') or (cl_ == 'escenario' and tipo == 'lugar') or (not cl_ and x.get('tipo') == tipo)): continue
        i = x.get('objeto_id'); c = cat.get(i, {})
        f = {k: x.get(k) for k in ('objeto_id', 'tipo', 'dueno_id', 'escenario_id', 'escenas', 'origen', 'forma', 'medidas', 'material', 'cita', 'justificacion', 'prompt_imagen', 'estado_por_escena')}
        f['clase'] = cl_ or None; f['nombre'] = c.get('nombre', i); f['en_canal'] = c.get('en_canal'); f['escenario_nombre'] = cesc.get(x.get('escenario_id'), x.get('escenario_id') or '')
        v = (iv or {}).get(i)
        f['fuente'] = '4p'; f['investigacion'] = v
        if v:   # la investigación (4b1/4c1) manda sobre 4p para lo que trae
            f['fuente'] = '4b1' if tipo == 'historia' else '4c1'
            if (v.get('prompt_imagen') or '').strip(): f['prompt_imagen'] = v['prompt_imagen']
            fo_ = v.get('forma') or {}
            if fo_.get('tipo'): f['forma'] = fo_['tipo']
            t = v.get('tamano') or {}
            if any(t.get(k) is not None for k in ('ancho_cm', 'fondo_cm', 'alto_cm')):
                f['medidas'] = ' x '.join('?' if t.get(k) is None else f"{t[k]:g}" for k in ('ancho_cm', 'fondo_cm', 'alto_cm')) + ' cm'
            m = [f"{q.get('parte')}: {q.get('material')}" for q in (v.get('materiales') or []) if q.get('material')]
            if m: f['material'] = '; '.join(m)
            f['prompts_por_estado'] = v.get('prompts_por_estado') or []
        out.append(f)
    return out

def guardar(D, nombre, obj):
    d = D / 'ramas'; d.mkdir(parents=True, exist_ok=True)
    f = d / nombre; f.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding='utf-8'); return str(f)

# ---------- galería (orden 51) ----------
GAL = r'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITULO__</title><style>
*{box-sizing:border-box}body{margin:0;font:14px system-ui,sans-serif;background:#111;color:#eee}
header{position:sticky;top:0;background:#1b1b1b;padding:10px 14px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;z-index:2;border-bottom:1px solid #333}
h1{font-size:16px;margin:0 12px 0 0}select,input,button{background:#262626;color:#eee;border:1px solid #444;border-radius:6px;padding:5px 8px;font:inherit}
button{cursor:pointer}button:hover{background:#333}.muted{color:#999}
#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;padding:14px}
.card{background:#1c1c1c;border:1px solid #333;border-radius:10px;overflow:hidden;cursor:pointer;display:flex;flex-direction:column}
.card:hover{border-color:#777}.img{aspect-ratio:16/9;background:#222;display:flex;align-items:center;justify-content:center;color:#666;text-align:center;padding:8px}
.img img{width:100%;height:100%;object-fit:cover}.cb{padding:8px 10px}.cb b{display:block;margin-bottom:3px}
.tag{display:inline-block;font-size:11px;padding:1px 6px;border-radius:9px;margin:2px 2px 0 0;background:#333}
.aprobado{background:#1f6f3a}.revisar{background:#6b5a12}.repetir{background:#7a2323}
#pag{display:flex;gap:6px;justify-content:center;padding:0 0 20px}
#lb{position:fixed;inset:0;background:#000e;display:none;z-index:9;grid-template-columns:1fr 380px}
#lb.on{display:grid}#vis{overflow:hidden;position:relative;display:flex;align-items:center;justify-content:center;cursor:grab}
#vis img{max-width:100%;max-height:100%;transform-origin:center;user-select:none}#ph{color:#777;font-size:18px;padding:30px;text-align:center}
#lado{background:#181818;overflow:auto;padding:14px;border-left:1px solid #333}#lado pre{white-space:pre-wrap;background:#222;padding:8px;border-radius:6px;font-size:12px}
.nav{position:absolute;top:50%;font-size:28px;background:#0008;border:0}#ant{left:8px}#sig{right:8px}#zoomc{position:absolute;bottom:10px;left:10px;display:flex;gap:6px}
</style></head><body>
<header><h1>__TITULO__</h1><span class="muted" id="cuenta"></span>
<input id="q" placeholder="buscar…" size="14">
<select id="fe"><option value="">todos los estados</option><option value="aprobado">aprobado</option><option value="revisar">por revisar</option><option value="repetir">repetir</option></select>
<select id="fs"><option value="">todas las escenas</option></select>
<select id="fg"><option value="">__GRUPO__: todos</option></select>
<select id="pp"><option>24</option><option>48</option><option>96</option><option value="100000">todos</option></select>
<button id="exp" title="descargar decisiones (JSON)">⬇ decisiones</button></header>
<div id="grid"></div><div id="pag"></div>
<div id="lb"><div id="vis"><img id="big" alt=""><div id="ph"></div><button class="nav" id="ant">‹</button><button class="nav" id="sig">›</button>
<div id="zoomc"><button id="zm">−</button><button id="z0">1:1</button><button id="zp">+</button><button id="fsb">⛶ pantalla completa</button><button id="cer">✕ cerrar (Esc)</button></div></div>
<div id="lado"></div></div>
<script>
const D=__DATOS__, K='myia_gal_'+D.clave, E=JSON.parse(localStorage.getItem(K)||'{}');
const $=s=>document.querySelector(s), esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const est=i=>E[i.id]||'revisar', nom={aprobado:'aprobado',revisar:'por revisar',repetir:'repetir'};
let L=[],pag=0,cur=-1,z=1,tx=0,ty=0;
[...new Set(D.items.flatMap(i=>i.escenas||[]))].sort((a,b)=>(+a||0)-(+b||0)).forEach(s=>$('#fs').insertAdjacentHTML('beforeend',`<option value="${esc(s)}">escena ${esc(s)}</option>`));
[...new Set(D.items.map(i=>i.grupo).filter(Boolean))].sort().forEach(g=>$('#fg').insertAdjacentHTML('beforeend',`<option>${esc(g)}</option>`));
function filtra(){const q=$('#q').value.toLowerCase(),fe=$('#fe').value,fs=$('#fs').value,fg=$('#fg').value;
 L=D.items.filter(i=>(!fe||est(i)==fe)&&(!fs||(i.escenas||[]).map(String).includes(fs))&&(!fg||i.grupo==fg)&&(!q||JSON.stringify(i).toLowerCase().includes(q)));pinta();}
function imgHTML(i){return i.img?`<img src="${esc(i.img)}" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('span'),{textContent:'(sin imagen todavía)'}))">`:'<span>(sin imagen todavía)</span>';}
function pinta(){const pp=+$('#pp').value,np=Math.max(1,Math.ceil(L.length/pp));pag=Math.min(pag,np-1);
 $('#cuenta').textContent=`${L.length} de ${D.items.length} · ${D.nota}`;
 $('#grid').innerHTML=L.slice(pag*pp,pag*pp+pp).map((i,k)=>`<div class="card" data-k="${pag*pp+k}"><div class="img">${imgHTML(i)}</div><div class="cb"><b>${esc(i.titulo)}</b>
 <span class="tag ${est(i)}">${nom[est(i)]}</span>${i.grupo?`<span class="tag">${esc(i.grupo)}</span>`:''}<span class="tag">escenas ${esc((i.escenas||[]).join(', '))}</span>${i.usd!=null?`<span class="tag">US$${(+i.usd).toFixed(3)}</span>`:''}
 <div class="muted">${esc((i.desc||'').slice(0,160))}</div></div></div>`).join('');
 $('#pag').innerHTML=np>1?Array.from({length:np},(_,p)=>`<button ${p==pag?'style="background:#555"':''} data-p="${p}">${p+1}</button>`).join(''):'';}
function abre(k){cur=k;const i=L[k];if(!i)return;z=1;tx=ty=0;ap();$('#lb').classList.add('on');
 const b=$('#big');if(i.img){b.style.display='';$('#ph').style.display='none';b.src=i.img;b.onerror=()=>{b.style.display='none';$('#ph').style.display='';$('#ph').textContent='(sin imagen todavía)';};}else{b.style.display='none';$('#ph').style.display='';$('#ph').textContent='(sin imagen todavía)';}
 $('#lado').innerHTML=`<h3>${esc(i.titulo)}</h3><div class="muted">${esc(i.id)}${i.grupo?' · '+esc(i.grupo):''} · escenas ${esc((i.escenas||[]).join(', '))}</div>
 <p>${['aprobado','revisar','repetir'].map(s=>`<button data-e="${s}" class="${est(i)==s?s:''}">${nom[s]}</button>`).join(' ')}</p>
 <p><b>Costo:</b> ${i.usd!=null?'US$'+(+i.usd).toFixed(3)+(i.usd_nota?' ('+esc(i.usd_nota)+')':''):'—'}</p>
 <p><b>Descripción</b></p><pre>${esc(i.desc||'—')}</pre><p><b>Prompt</b></p><pre>${esc(i.prompt||'(todavía no hay prompt)')}</pre>
 ${i.extra?`<p><b>Datos</b></p><pre>${esc(i.extra)}</pre>`:''}`;}
function ap(){$('#big').style.transform=`translate(${tx}px,${ty}px) scale(${z})`;}
$('#grid').onclick=e=>{const c=e.target.closest('.card');if(c)abre(+c.dataset.k);};
$('#pag').onclick=e=>{if(e.target.dataset.p){pag=+e.target.dataset.p;pinta();scrollTo(0,0);}};
['#q','#fe','#fs','#fg','#pp'].forEach(s=>$(s).oninput=()=>{pag=0;filtra();});
$('#lado').onclick=e=>{const s=e.target.dataset.e;if(!s)return;E[L[cur].id]=s;localStorage.setItem(K,JSON.stringify(E));abre(cur);pinta();};
$('#ant').onclick=()=>abre((cur-1+L.length)%L.length);$('#sig').onclick=()=>abre((cur+1)%L.length);
$('#zp').onclick=()=>{z*=1.25;ap()};$('#zm').onclick=()=>{z/=1.25;ap()};$('#z0').onclick=()=>{z=1;tx=ty=0;ap()};
$('#cer').onclick=()=>{$('#lb').classList.remove('on');if(document.fullscreenElement)document.exitFullscreen();};
$('#fsb').onclick=()=>document.fullscreenElement?document.exitFullscreen():$('#lb').requestFullscreen();
$('#vis').onwheel=e=>{e.preventDefault();z*=e.deltaY<0?1.15:1/1.15;z=Math.min(12,Math.max(.2,z));ap();};
let arr=null;$('#vis').onmousedown=e=>{if(e.target.id=='big'){arr=[e.clientX-tx,e.clientY-ty];e.preventDefault();}};
onmousemove=e=>{if(arr){tx=e.clientX-arr[0];ty=e.clientY-arr[1];ap();}};onmouseup=()=>arr=null;
onkeydown=[REDACTED]
$('#exp').onclick=()=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify({galeria:D.clave,decisiones:D.items.map(i=>({id:i.id,estado:est(i)}))},null,1)],{type:'application/json'}));a.download=D.clave+'_decisiones.json';a.click();};
filtra();
</script></body></html>'''

def galeria(D, caja, titulo, grupo, items, nota):
    d = D / 'ramas' / 'galerias'; d.mkdir(parents=True, exist_ok=True)
    datos_ = {'clave': f"{D.name}_{caja}", 'nota': nota, 'items': items}
    t = (GAL.replace('__TITULO__', html.escape(titulo)).replace('__GRUPO__', html.escape(grupo))
         .replace('__DATOS__', json.dumps(datos_, ensure_ascii=False).replace('</', '<\\/')))
    f = d / f'{caja}.html'; f.write_text(t, encoding='utf-8')
    return str(f), sum(1 for i in items if i.get('img') and (d / i['img']).is_file())

def items_escenarios(fe, carpeta_img, usd=None, usd_nota=None, prompts=None):
    r = []
    for x in fe:
        el = '\n'.join(f"• {e.get('nombre')} (escenas {', '.join(map(str, e.get('escenas', [])))})" for e in x['elementos'])
        va = '\n'.join(f"• {v.get('variante')} (escenas {', '.join(map(str, v.get('escenas', [])))})" for v in x['variantes_estado'])
        v = x.get('investigacion') or {}; me = v.get('medidas') or {}
        inv_txt = (f"\n[4a1] medidas ≈ {me.get('ancho_m')} × {me.get('fondo_m')} × {me.get('alto_m')} m · {(v.get('planta') or {}).get('descripcion', '')}"
                   f"\nAtmósfera: {(v.get('para_pintar') or {}).get('atmosfera', '')}") if v else '\n[4p] (sin investigación 4a1 todavía)'
        am = (v.get('ambiente_vivo') or {}) if v else {}
        if am:   # orden 61: resumen de la zona ambiente
            c = AMB.conteo(am)
            pr = am.get('perfil_real') if isinstance(am.get('perfil_real'), dict) else {}   # orden 61b
            inv_txt += (f"\nAmbiente vivo: {c['utileria_ambiente']} elementos, {c['superficies']} superficies, {c['senales_uso']} señales de uso, {c['extras_fondo']} grupos de vida de fondo, {c['vista_por_aberturas']} vistas, {c['fondo_lejano']} de fondo lejano"
                        + (f"\n  perfil real: {pr.get('que_es')}" if pr.get('que_es') else '')
                        + (f"\n  paleta: {', '.join(map(str, pr.get('paleta_de_colores') or []))}" if pr.get('paleta_de_colores') else '')
                        + (f"\n  NO hay: {', '.join(map(str, pr.get('lo_que_no_hay') or []))}" if pr.get('lo_que_no_hay') else '')
                        + f"\n  ej.: {', '.join(str(q.get('nombre')) for q in (am.get('utileria_ambiente') or [])[:8])}"
                        + (f"\n  a lo lejos: {', '.join(str(q.get('que_es')) for q in (am.get('fondo_lejano') or [])[:5])}" if am.get('fondo_lejano') else ''))
        r.append({'id': x['id'], 'titulo': x['nombre'], 'grupo': x.get('int_ext') or '', 'escenas': [str(s) for s in x['escenas']],
                  'extra': json.dumps(v, ensure_ascii=False, indent=1)[:6000] if v else None,
                  'desc': f"{x.get('int_ext') or ''} · hora: {'; '.join(x['horas']) or '—'} · clima: {'; '.join(x['climas']) or '—'}" + (' · solo recuerdo/pantalla' if x.get('solo_recuerdo_o_pantalla') else '') + f"\nElementos:\n{el}\nVariantes de estado:\n{va}" + inv_txt,
                  'prompt': (prompts or {}).get(x['id']), 'img': f"../{carpeta_img}/{x['id']}.png", 'usd': usd, 'usd_nota': usd_nota})
    return r

def items_objetos(fo, carpeta_img, usd, usd_nota, grupo_de):
    return [{'id': x['objeto_id'], 'titulo': x['nombre'], 'grupo': grupo_de(x), 'escenas': [str(s) for s in (x.get('escenas') or [])],
             'desc': f"[{x.get('fuente', '4p')}] forma: {x.get('forma')} · medidas: {x.get('medidas')} · material: {x.get('material')}\n«{x.get('cita') or ''}»" + (f"\nubicación: {json.dumps(((x.get('investigacion') or {}).get('ubicacion') or {}), ensure_ascii=False)}" if (x.get('investigacion') or {}).get('ubicacion') else ''),
             'prompt': x.get('prompt_imagen'), 'img': f"../{carpeta_img}/{x['objeto_id']}.png", 'usd': usd, 'usd_nota': usd_nota,
             'extra': '\n'.join(f"escena {s.get('escena')}: {s.get('inicio')} → {s.get('fin')}" for s in (x.get('estado_por_escena') or []))} for x in fo]

def muestra(lst, k='nombre', n=4): return [x.get(k) for x in lst[:n]]

def para_sello(D, items, clase):
    """inmi 2-nov-2026 (orden Ricardo 17:33 Bogotá): lo pintado en 4a5/4b2/4c2 pasa a la cadena SELLO OBJ (ADN Maestro 03/04 + sello fijo).
    Solo lista lo que YA tiene imagen en disco; no llama a nada."""
    g = D / 'ramas' / 'galerias'; r = []
    for i in items:
        if not i.get('img'): continue
        f = (g / i['img']).resolve()
        if f.is_file(): r.append({'id': str(i.get('id')), 'clase': clase, 'imagen_ref': str(f), 'nombre': i.get('titulo')})
    return r

# ---------- orden 61: zona AMBIENTE (ids amb-…, origen «ambiente») y ASCENSO a oficial ----------
import ambiente as AMB

def objetos_historia(D, base):
    """Objetos que la historia usa: catálogo oficial (caja 4) + los investigados en 4b1/4c1. Para el ascenso automático."""
    objs = [{'id': o.get('id'), 'nombre': o.get('nombre')} for o in (base or {}).get('catalogo_oficial', {}).get('objetos', [])]
    for n in ('inv_obj_historia', 'inv_obj_lugar'):
        iv_, _ = inv(D, n)
        objs += [{'id': i, 'nombre': (o or {}).get('nombre')} for i, o in (iv_ or {}).items()]
    return objs

def ambiente_de(x, objs):
    """ambiente_vivo de la investigación 4a1, normalizado, con ascensos marcados (conserva los datos)."""
    v = x.get('investigacion') or {}
    am, _ = AMB.normalizar(x['id'], v.get('ambiente_vivo'))
    asc = AMB.marcar_ascenso(am, objs, '4b/4c y catálogo oficial')
    return am, asc

# ---------- Blender (orden 60): molde 3D por escenario ----------
def sha(b): return hashlib.sha256(b).hexdigest()

def moldes_blender(D, ent, bl, solo=None):
    """Corre blender_molde.py por escenario. t358u: varios escenarios A LA VEZ (llamadas_config.json «paralelo.max_a_la_vez.blender»;
    1 = uno a la vez como antes); los hilos de render de cada Blender = núcleos / ese número. Un candado impide dos armados del mismo
    capítulo. Reutiliza el molde si la receta y el script no cambiaron. Cada escenario escribe solo en su carpeta."""
    import paralelo_cadena as PC
    MD = D / 'ramas' / 'moldes'; MD.mkdir(parents=True, exist_ok=True)
    sh_script = sha(SCRIPT_MOLDE.read_bytes())[:16]
    lista = [e for e in ent if not solo or e['id'] in solo.split(',')]
    if solo and not lista: return {'ok': False, 'error': f'--solo {solo}: ese escenario no está en la entrada de Blender'}
    n = PC.max_a_la_vez('blender') if PC.activo() else 1
    hilos = str(3 if n <= 1 else max(1, (os.cpu_count() or 4) // n))
    t0 = time.time()

    def uno(e):
        d = MD / e['id']; d.mkdir(exist_ok=True)
        receta = json.dumps(e, ensure_ascii=False, sort_keys=True).encode('utf-8'); huella = sha(receta)[:16] + '-' + sh_script
        mj = d / 'molde.json'
        try: prev = json.loads(mj.read_text(encoding='utf-8')) if mj.is_file() else {}
        except Exception: prev = {}
        # orden 62: molde copiado de la biblioteca del canal (de_biblioteca) = ya aprobado; no se rehace aunque cambie la receta del capítulo
        if prev.get('ok') and (prev.get('huella') == huella or prev.get('de_biblioteca')) and all((d / x).is_file() for x in prev.get('renders', [])):
            return {'id': e['id'], 'reutilizado': True, 'segundos': prev.get('segundos'), 'renders': len(prev.get('renders', [])), 'avisos': len(prev.get('avisos', [])),
                    **({'de_biblioteca': prev['de_biblioteca']} if prev.get('de_biblioteca') else {})}
        (d / 'escenario.json').write_bytes(receta)
        for x in d.glob('*.png'): x.unlink()
        ti = time.time()
        try:
            p = subprocess.run(['nice', '-n', '10', bl, '-b', '--factory-startup', '-noaudio', '--python', str(SCRIPT_MOLDE), '--', str(d / 'escenario.json'), str(d)],
                               capture_output=True, text=True, timeout=900, env=dict(os.environ, MOLDE_HILOS=hilos))
            (d / 'blender.log').write_text((p.stdout or '')[-20000:] + '\n--- stderr ---\n' + (p.stderr or '')[-5000:], encoding='utf-8')
            ok = p.returncode == 0 and 'MOLDE_OK' in (p.stdout or '') and mj.is_file()
        except subprocess.TimeoutExpired:
            ok = False; (d / 'blender.log').write_text('tiempo agotado (900 s)', encoding='utf-8')
        seg = round(time.time() - ti, 1)
        if not ok:
            return {'id': e['id'], 'ok': False, 'segundos': seg, 'error': 'Blender falló: ver ' + str(d / 'blender.log')}
        m = json.loads(mj.read_text(encoding='utf-8')); m['huella'] = huella; m['segundos_total'] = seg
        mj.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding='utf-8')
        principal = next((x for x in m['renders'] if x.startswith('cam_')), 'planta.png')
        shutil.copyfile(d / principal, MD / f"{e['id']}.png")
        return {'id': e['id'], 'reutilizado': False, 'segundos': seg, 'renders': len(m['renders']), 'camaras': m.get('camaras'),
                'escenas_con_luz': len(m.get('escenas_con_luz', [])), 'avisos': len(m.get('avisos', []))}

    with open(MD / '.candado', 'w') as cand:
        try: fcntl.flock(cand, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: return {'ok': False, 'error': 'ya hay un armado de Blender corriendo para este capítulo'}
        out = [r for _, r, _, _ in PC.correr_paralelo(lista, uno, n)]
    malos = [x['id'] for x in out if x.get('ok') is False]
    hechos = [x for x in out if x.get('ok') is not False]
    return {'ok': not malos, 'moldes': out, 'carpeta_moldes': str(MD), 'segundos_total': round(time.time() - t0, 1), 'fallaron': malos, 'blender_a_la_vez': n, 'hilos_por_blender': int(hilos),
            'error': (f"Blender falló en: {', '.join(malos)}" if malos else None),
            'resumen': f"Blender armó {len(hechos)}/{len(lista)} moldes ({sum(x.get('renders', 0) for x in hechos)} renders, "
                       f"{sum(1 for x in hechos if x.get('reutilizado'))} reutilizados, {n} a la vez) en {round(time.time() - t0)} s" + (f"; fallaron: {', '.join(malos)}" if malos else '')}

def items_moldes(D, fe):
    """Galería 4a3: un cuadro por render real (planta, cada cámara, la luz de cada escena) agrupado por escenario."""
    base = {i['id']: i for i in items_escenarios(fe, 'moldes')}; out, n = [], 0
    for x in fe:
        b = base[x['id']]; d = D / 'ramas' / 'moldes' / x['id']
        try: m = json.loads((d / 'molde.json').read_text(encoding='utf-8'))
        except Exception: m = None
        if not m:
            motivo = 'sin molde: solo recuerdo o pantalla' if x.get('solo_recuerdo_o_pantalla') else 'todavía sin molde (corre 4a2)'
            out.append(dict(b, img=None, grupo=x['nombre'], titulo=f"{x['nombre']} · {motivo}")); continue
        n += 1; cams = {f"cam_{k + 1:02d}": c for k, c in enumerate((x.get('investigacion') or {}).get('camaras_sugeridas') or [])}
        for rnd in m.get('renders', []):
            k = rnd[:-4]
            if k == 'planta': t, esc = 'planta cenital (rejilla 1 m)', []
            elif k.startswith('luz_esc'): t, esc = f"luz escena {k[7:]} (Cycles)", [k[7:]]
            else:
                c = cams.get(k[:6]) or {}; esc = [str(c.get('escena'))] if c.get('escena') else []
                t = f"cámara {int(k[4:6])} · escena {c.get('escena', '?')} · {c.get('lente_mm', '?')} mm"
            ex = f"{'; '.join(m.get('armado', []))}\n\nAVISOS:\n" + ('\n'.join(m.get('avisos', [])) or '—')
            out.append(dict(b, id=f"{x['id']}__{k}", titulo=f"{x['nombre']} · {t}", grupo=x['nombre'], escenas=esc or b['escenas'],
                            img=f"../moldes/{x['id']}/{rnd}", extra=ex[:6000], usd=0, usd_nota='Blender, gratis'))
    return out, n

# ---------- cajas ----------
def correr(caja, canal, capitulo, solo=None):
    D = carpeta(canal, capitulo)
    if D is None: return {'ok': True, 'caja': caja, 'espera_4p': True, 'gratis': True, 'mensaje': 'todavía no hay carpeta del capítulo: corre primero 4 y 4p'}
    base, e2a, e2b = datos(D)
    r = {'ok': True, 'caja': caja, 'gratis': True, 'carpeta': str(D), 'hora': ahora(), 'llama_a_pago': False}
    rama = caja[:2]
    iv, ivj = inv(D, nombres_inv(caja))
    r['fuente_investigacion'] = ({'4a': '4a1', '4b': '4b1', '4c': '4c1'}[rama] + ' (Argon)') if iv else '4p (todavía no hay investigación)'
    if rama == '4a' and not e2a: return dict(r, espera_4p=True, mensaje='falta respuestas/escenarios.json (2a de la caja 4p): corre 4p en modo pagar')
    if rama in ('4b', '4c') and not e2b: return dict(r, espera_4p=True, mensaje='falta respuestas/objetos.json (2b de la caja 4p): corre 4p en modo pagar')
    if not base: return dict(r, espera_4p=True, mensaje='falta respuestas/base.json (caja 4)')

    if caja in ('4a1', '4b1', '4c1'):
        t = (ivj or {}).get('_taller', {})
        if not iv: return dict(r, pendiente=True, resumen=f"{caja}: todavía no hay investigación; la corre paso00_cadena (Argon, pago)")
        return dict(r, registros=len(iv), usd_real=t.get('usd_real'), grupos=t.get('grupos'), ids_inventados=t.get('ids_inventados'),
                    ids_sin_respuesta=t.get('ids_sin_respuesta'), dudas=len(ivj.get('dudas', [])), contradicciones=len(ivj.get('contradicciones', [])),
                    resumen=f"{caja}: {len(iv)} registros investigados por Argon (US${t.get('usd_real')})")
    if rama == '4a':
        fe = fichas_escenarios(base, e2a, iv)
        if caja == '4a':
            f = guardar(D, '4a_escenarios.json', fe)
            return dict(r, escenarios=len(fe), variantes=sum(len(x['variantes_estado']) for x in fe), elementos=sum(len(x['elementos']) for x in fe),
                        solo_recuerdo_o_pantalla=sum(1 for x in fe if x.get('solo_recuerdo_o_pantalla')), ejemplos=muestra(fe), archivo=f,
                        resumen=f"{len(fe)} escenarios desde la salida de Argon (2a de 4p)")
        if caja == '4a2':
            # t356u: tamaños y forma de TODOS los objetos investigados: los de la historia (4b1) y los del lugar (4c1); si un id está en los dos, manda 4c1
            tam = {}
            for n_inv in ('inv_obj_historia', 'inv_obj_lugar'):
                ivo, _ = inv(D, n_inv)
                tam.update({i: {'nombre': i, 'forma': (o.get('forma') or {}).get('tipo'), 'tamano': o.get('tamano'), 'fuente_tamano': n_inv} for i, o in (ivo or {}).items()})
            ent = []; objs = objetos_historia(D, base)
            for x in fe:
                if x.get('solo_recuerdo_o_pantalla'): continue
                v = x.get('investigacion') or {}
                e = {'id': x['id'], 'nombre': x['nombre'], 'int_ext': x['int_ext'], 'horas': x['horas'], 'fuente': x['fuente'],
                     'elementos': [e.get('nombre') for e in x['elementos']], 'variantes': [q.get('variante') for q in x['variantes_estado']],
                     **{k: v.get(k) for k in ('medidas', 'planta', 'aberturas', 'elementos_blender', 'objetos_del_lugar_posicion', 'materiales_texturas',
                                             'luz_por_escena', 'camaras_sugeridas') if v}}
                e['objetos_tamano'] = {o.get('objeto_id'): tam[o.get('objeto_id')] for o in (e.get('objetos_del_lugar_posicion') or []) if o.get('objeto_id') in tam}
                if v: e['ambiente_vivo'], e['ambiente_ascensos'] = ambiente_de(x, objs)   # orden 61
                ent.append(e)
            f = guardar(D, '4a2_entrada_blender.json', ent)
            con = sum(1 for e in ent if e['fuente'] == '4a1')
            bl = next((b for b in BLENDERS if os.access(b, os.X_OK)), None) or shutil.which('blender')
            r.update(escenarios_para_blender=len(ent), con_investigacion_4a1=con, archivo=f, blender=bl, blender_instalado=bool(bl))
            r['ambiente_por_escenario'] = {e['id']: AMB.conteo(e.get('ambiente_vivo')) for e in ent}
            r['ambiente_vacios'] = [e['id'] for e in ent if not sum(AMB.conteo(e.get('ambiente_vivo')).values())]
            r['ambiente_ascensos'] = [dict(q, escenario_id=e['id']) for e in ent for q in (e.get('ambiente_ascensos') or [])]
            if not bl or not SCRIPT_MOLDE.is_file():
                return dict(r, pendiente=True, resumen=f"entrada de Blender lista para {len(ent)} escenarios; Blender o el script no están en este servidor")
            mb = moldes_blender(D, ent, bl, solo)
            try:   # t440 (Ricardo): 4a2 entrega glosario de formas + fondo de exteriores para 4a1b. GRATIS
                import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import entregas_origen as EO
                mb['entrega_origen'] = EO.entregar_4a2(D, (set(solo.split(',')) if isinstance(solo, str) else set(solo)) if solo else None)
            except Exception as exc_eo:
                mb['entrega_origen'] = {'ok': False, 'error': f'{type(exc_eo).__name__}: {str(exc_eo)[:300]}'}
            return dict(r, **mb)
        if caja == '4a3':
            it, n_moldes = items_moldes(D, fe[:20])
            f, con = galeria(D, '4a3', 'Moldes de escenarios (4a3)', 'escenario', it, 'renders de Blender (4a2): planta cenital, una vista por cámara sugerida y la luz de cada escena · descripción de Argon (hasta 20 escenarios)')
            sin = [x['id'] for x in fe[:20] if not (D / 'ramas' / 'moldes' / x['id'] / 'molde.json').is_file()]
            return dict(r, galeria=f, cuadros=len(it), con_imagen=con, escenarios_con_molde=n_moldes, sin_molde=sin,
                        resumen=f"galería de moldes: {n_moldes} escenarios con molde, {con} renders" + (f"; sin molde: {', '.join(sin)}" if sin else ''))
        if caja in ('4a4', '4a5'):   # orden 59 (t399u/t400u): 1 imagen BASE por escenario (con molde de Blender) + 1 EDICIÓN de la base por variante
            pv, pj = inv(D, 'prompts_escenarios')
            if pv:
                bases = [{'escenario_id': i, 'con_molde': bool(x.get('tiene_molde_blender')), 'sin_molde_motivo': x.get('sin_molde_motivo') or '',
                          'cubre_variante_id': (x.get('base') or {}).get('cubre_variante_id'), 'ediciones': [q.get('variante_id') for q in x.get('variantes', [])]} for i, x in pv.items()]
                fuente = '4a4 (Argon)'
            else:
                bases = [{'escenario_id': x['id'], 'con_molde': not x.get('solo_recuerdo_o_pantalla'), 'sin_molde_motivo': 'solo recuerdo o pantalla (según 4p)' if x.get('solo_recuerdo_o_pantalla') else '',
                          'cubre_variante_id': f"{x['id']}__v1", 'ediciones': [f"{x['id']}__v{k}" for k in range(2, len(x['variantes_estado']) + 1)]} for x in fe]
                fuente = '4p (estimado: la base cubre la 1.ª variante; 4a4 aún no corre)'
            nb = len(bases); ne = sum(len(x['ediciones']) for x in bases); sm = [x['escenario_id'] for x in bases if not x['con_molde']]
            if caja == '4a4':
                t = (pj or {}).get('_taller', {})
                if not pv: return dict(r, pendiente=True, plan=bases, sin_molde=sm,
                                       resumen=f"4a4: todavía no hay prompts; la corre paso00_cadena (Argon, pago). Plan estimado: {nb} bases + {ne} ediciones")
                return dict(r, plan=bases, sin_molde=sm, usd_real=t.get('usd_real'), ids_inventados=t.get('ids_inventados'), variantes_sin_prompt=pj.get('_variantes_sin_prompt'),
                            resumen=f"4a4: {nb} prompts base + {ne} prompts de edición (Argon, US${t.get('usd_real')}); sin molde: {len(sm)}")
            usd, modelo = precio_imagen(canal, REF_4A5, 6000)
            objs = objetos_historia(D, base); fx = {x['id']: x for x in fe}
            for b in bases:   # orden 61/61b: el plan de pintura usa TODO el ambiente (perfil_real, superficies, utilería, señales de uso, extras, clima/hora, vistas, fondo lejano)
                x = fx.get(b['escenario_id'])
                am, asc = ambiente_de(x, objs) if x else ({}, [])
                b['ambiente_conteo'] = AMB.conteo(am); b['ambiente_ascensos'] = asc
                b['ambiente'] = {'superficies': [f"{q.get('superficie')}: {q.get('acabado')}; desgaste: {q.get('desgaste')}" for q in am.get('superficies', [])],
                                 'utileria': [f"{q.get('nombre')} ({q.get('material') or ''} {q.get('color') or ''}".strip() + ')' + (f" → oficial {q['ascender_a_oficial']['objeto_id']}" if q.get('ascender_a_oficial') else '') for q in am.get('utileria_ambiente', [])],
                                 'senales_uso': [q.get('descripcion') for q in am.get('senales_uso', [])],
                                 'extras_fondo': [f"{q.get('cantidad')} · {q.get('que_hacen')} · {q.get('donde')} (escenas {', '.join(map(str, q.get('escenas') or []))})" for q in am.get('extras_fondo', [])],
                                 'por_escena': am.get('ambiente_por_escena', []), 'vistas': [f"{q.get('abertura')}: {q.get('que_se_ve')}" for q in am.get('vista_por_aberturas', [])],
                                 'perfil_real': AMB.perfil_corto(am),   # orden 61b: paleta real y lo que NO debe aparecer
                                 'fondo_lejano': [f"{q.get('que_es')} · {q.get('direccion')} · ~{q.get('distancia_aprox_m')} m · {q.get('tamano_aparente')} · {q.get('color')} (escenas {', '.join(map(str, q.get('escenas') or []))})" for q in am.get('fondo_lejano', [])]}
            f = guardar(D, '4a5_plan_pintura.json', {'fuente': fuente, 'bases': bases})
            r['ambiente_por_escenario'] = {b['escenario_id']: sum(b['ambiente_conteo'].values()) for b in bases}
            return dict(r, cotizacion=True, modelo=modelo, usd_por_imagen=usd, imagenes_base=nb, ediciones=ne, imagenes=nb + ne,
                        total_usd=round((nb + ne) * usd, 3), sin_molde=sm, plan=f, fuente_plan=fuente,
                        nota='primero las bases (guiadas por el molde de Blender de 4a2; las «sin molde» van solo con su prompt), después cada variante editando su base (la base va como imagen de referencia con «no cambiar lo demás"). Necesita prompts de 4a4 y moldes de 4a2.',
                        resumen=f"{nb} bases + {ne} ediciones = {nb + ne} imágenes × US${usd} = US${round((nb + ne) * usd, 3)}" + (f" · sin molde: {', '.join(sm)}" if sm else ''))
        if caja == '4a6':
            usd, _ = precio_imagen(canal, REF_4A5, 6000)
            it = items_escenarios(fe, 'imagenes/4a5', usd, 'Nano Banana, 1 imagen')
            f, con = galeria(D, '4a6', 'Escenarios pintados (4a6)', 'interior/exterior', it, 'resultado de Nano Banana; recorte automático al formato del canal (4a6)')
            try:   # t445 (Ricardo): recorte AUTOMÁTICO al formato del canal, centrado, sin IA (cajas/recorte_4a6.py)
                import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import recorte_4a6 as RC
                rec = RC.recortar(D, canal)
            except Exception as exc_rc:
                rec = {'ok': False, 'error': f'{type(exc_rc).__name__}: {str(exc_rc)[:300]}'}
            return dict(r, galeria=f, cuadros=len(it), con_imagen=con, recorte=rec, para_sello=para_sello(D, it, 'escenario'),
                        resumen=f"galería de escenarios: {len(it)} cuadros, {con} con imagen · recorte: " + (f"{rec.get('recortes')} imágenes a {rec['formato']['aspect']} ({rec.get('nuevos')} nuevas)" if rec.get('ok') else f"ERROR {rec.get('error')}"))

    tipo = 'historia' if rama == '4b' else 'lugar'
    fo = fichas_objetos(base, e2b, tipo, iv)
    if rama == '4b': grupo_de, gnom = (lambda x: x.get('dueno_id') or 'sin dueño'), 'dueño'
    else: grupo_de, gnom = (lambda x: x.get('escenario_nombre') or 'sin escenario'), 'escenario'
    if caja in ('4b', '4c'):
        f = guardar(D, f"{caja}_objetos_{tipo}.json", fo)
        extra = {}
        if caja == '4c':
            g = {}
            for x in fo: g.setdefault(x.get('escenario_nombre') or 'sin escenario', []).append(x['nombre'])
            extra = {'por_escenario': {k: len(v) for k, v in g.items()}}
        return dict(r, objetos=len(fo), ejemplos=muestra(fo), archivo=f, **extra,
                    resumen=f"{len(fo)} objetos {'de la historia' if tipo == 'historia' else 'del lugar'} desde la salida de Argon (2b de 4p)")
    if caja in ('4b2', '4c2'):   # PISTA INMI (2026-10-29): orden 72 — la cotización la hace el MISMO motor seguro de 4a5 (paso00_pintar --caja)
        try:
            import paso00_pintar as PNT, estilo_taller as ET_
            cd = ET_.canal_datos(canal)
            c = PNT.cotizar(D, cd, None, None, caja) if cd is not None else {'ok': False, 'error': f'el canal {canal} no está en la base del estudio'}
            c = c[0] if isinstance(c, tuple) else c
        except Exception as exc:
            c = {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:300]}'}
        if c.get('ok'):
            pt = c.get('por_tipo') or {}; nb, ne = pt.get('base', 0), pt.get('estado', 0); ns = c.get('no_se_pinta') or []
            return dict(r, cotizacion=True, modelo=c['modelo'], talla=c.get('talla'), usd_por_imagen=c['usd_por_imagen'], imagenes=nb, imagenes_por_estado_extra=ne,
                        total_usd=round(sum(q['peor_caso_usd'] for q in c['pedidos'] if q['tipo'] == 'base' and not q['saltar']), 4),
                        total_con_estados_usd=c['total_peor_caso_usd'], no_se_pinta=ns, pintar=c,
                        nota=(f"no llama: solo cotiza. Pintar = paso00_cadena pintar correr --caja {caja} --ok USD --aprobado QUIEN, cerrado sin cajas/{c.get('guarda')}"
                              " (una imagen a la vez, 12 s entre imágenes, 429 con espera, ledger por intento, --solo-fallidos)."),
                        resumen=f"{nb} bases + {ne} estados = {nb + ne} imágenes · peor caso US${c['total_peor_caso_usd']} ({c['modelo']} {c.get('talla')})"
                                + (f" · no se pintan {len(ns)} (falta {'4b1' if caja == '4b2' else '4c1'} válida)" if ns else ''))
        return dict(r, ok=False, cotizacion=True, error=c.get('error'), resumen=f"no se puede cotizar {caja}: {c.get('error')}")
    if caja in ('4b3', '4c3'):
        usd, _ = precio_imagen(canal, REF_4A5, 6000)
        it = items_objetos(fo, f"imagenes/{caja[:2]}2", usd, 'Nano Banana, 1 imagen', grupo_de)
        tit = 'Objetos de la historia (4b3)' if caja == '4b3' else 'Objetos del lugar (4c3)'
        f, con = galeria(D, caja, tit, gnom, it, 'imagen de Nano Banana + descripción y prompt de Argon')
        return dict(r, galeria=f, cuadros=len(it), con_imagen=con, para_sello=para_sello(D, it, 'objeto'), resumen=f"galería: {len(it)} objetos, {con} con imagen")
    return {'ok': False, 'error': f'caja desconocida {caja}'}

def main(argv):
    ap = argparse.ArgumentParser(prog='paso00_cadena.py ramas')
    ap.add_argument('caja', choices=CAJAS)
    ap.add_argument('--canal', default='cn-gnesis-digital-el-de-ed178619')
    ap.add_argument('--capitulo', default='1')
    ap.add_argument('--corrida', default=None)
    ap.add_argument('--solo', default=None, help='4a2: solo estos escenarios (ids separados por coma)')
    a = ap.parse_args(argv)
    r = correr(a.caja, a.canal, a.capitulo, a.solo)
    D = carpeta(a.canal, a.capitulo)
    if D is not None and r.get('ok'):
        try: guardar(D, f'resultado_{a.caja}.json', r)
        except Exception: pass
    return r
