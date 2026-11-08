// n8n Code node: SELLO PJ · 2c leer hoja
// disabled: False
function b64u(o){const s=unescape(encodeURIComponent(JSON.stringify(o)));const T="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";let r="";for(let i=0;i<s.length;i+=3){const a=s.charCodeAt(i),b=s.charCodeAt(i+1),c=s.charCodeAt(i+2);const n=(a<<16)|((b||0)<<8)|(c||0);r+=T[(n>>18)&63]+T[(n>>12)&63]+(i+1<s.length?T[(n>>6)&63]:"")+(i+2<s.length?T[n&63]:"");}return r;}
const J=(x)=>{try{return JSON.parse(String(x.stdout||'').trim().split('\n').pop());}catch(e){return {ok:false,error:'no JSON: '+String(x.stderr||x.stdout||'').slice(0,200)};}};
const j=$('SELLO PJ · 2b preparar hoja Fase 1 · Maestro 02 (sello_pago)').first().json; const d=J($input.first().json);
if(j.en_disco) return [{json:{...j, hoja:null}}];
if(!d.ok) throw new Error('sello_pago hoja: '+(d.error||'sin respuesta')+' · llamadas hechas: '+(d.llamadas_hechas!=null?d.llamadas_hechas:'?')+' · peor caso US$'+(d.peor_caso!=null?d.peor_caso:'?'));
return [{json:{...j, hoja:d.hoja, hoja_usd:d.usd, hoja_intentos:d.intentos||[]}}];