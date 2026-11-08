// n8n Code node: SELLO PJ · 2b preparar hoja Fase 1 · Maestro 02 (sello_pago)
// disabled: False
function b64u(o){const s=unescape(encodeURIComponent(JSON.stringify(o)));const T="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";let r="";for(let i=0;i<s.length;i+=3){const a=s.charCodeAt(i),b=s.charCodeAt(i+1),c=s.charCodeAt(i+2);const n=(a<<16)|((b||0)<<8)|(c||0);r+=T[(n>>18)&63]+T[(n>>12)&63]+(i+1<s.length?T[(n>>6)&63]:"")+(i+2<s.length?T[n&63]:"");}return r;}
const J=(x)=>{try{return JSON.parse(String(x.stdout||'').trim().split('\n').pop());}catch(e){return {ok:false,error:'no JSON: '+String(x.stderr||x.stdout||'').slice(0,200)};}};
const Q=s=>String(s||'').replace(/[^A-Za-z0-9._-]/g,'-').replace(/^-+/,'').slice(0,60)||'sin-ok';
const j=$('SELLO PJ · 2a leer cotización y tope').first().json; const e=$('SELLO PJ · 1 entrada imagen de referencia').first().json; const c=J($input.first().json);
const ok=Number(j.tope_usd||0).toFixed(4);
if(j.en_disco) return [{json:{...j, pago_cmd:'estado', paso_hoja:'ADN ya en disco: no se genera hoja (gratis)'}}];
if(!e.imagen_ref) throw new Error('Falta imagen_ref (foto del cliente) para la hoja Fase 1');
const est=((c.cubo||{}).estilo||[]).find(x=>x.canal===j.canal||(x.ids_canal||[]).includes(j.canal));
const ei=est&&(est.imagen_ref||est.hoja_ref); if(!ei) throw new Error('El canal no tiene imagen de estilo sellada: correr SELLO ESTILO primero');
const ped={id:String(j.id),canal:String(j.canal),refs:[String(e.imagen_ref)],estilo_img:String(ei)}; if(e.extra) ped.extra=String(e.extra);
return [{json:{...j, estilo_img:ei, pago_cmd:'hoja b64.'+b64u(ped)+' --ok '+ok+' --aprobado '+Q(e.ok_ricardo)}}];