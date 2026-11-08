// n8n Code node: SELLO ESTILO · 3a leer ADN
// disabled: False
function normalizarAdn(d,j){
 const a=d.adn_json || (d.adn_ako_texto && typeof d.adn_ako_texto==='object'?d.adn_ako_texto:null);
 if(!a) return String(d.adn_ako_texto||'');
 if(a.schema!=='ako_json/v1'||a.id!==String(j.id)||(j.clase&&a.clase!==j.clase)) throw new Error('JSON ADN: schema/identidad/clase');
 const blocks=[]; for(let i=1;i<=5;i++){const t=a['bloque_'+i];if(typeof t!=='string'||!new RegExp('^\\s*'+i+'[.)]').test(t))throw new Error('JSON ADN: bloque '+i);blocks.push(t);}
 return blocks.join('\n\n');
}
function b64u(o){const s=unescape(encodeURIComponent(JSON.stringify(o)));const T="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";let r="";for(let i=0;i<s.length;i+=3){const a=s.charCodeAt(i),b=s.charCodeAt(i+1),c=s.charCodeAt(i+2);const n=(a<<16)|((b||0)<<8)|(c||0);r+=T[(n>>18)&63]+T[(n>>12)&63]+(i+1<s.length?T[(n>>6)&63]:"")+(i+2<s.length?T[n&63]:"");}return r;}
const J=(x)=>{try{return JSON.parse(String(x.stdout||'').trim().split('\n').pop());}catch(e){return {ok:false,error:'no JSON: '+String(x.stderr||x.stdout||'').slice(0,200)};}};
const j=$('SELLO ESTILO · 3 preparar ADN · Maestro 05 (sello_pago)').first().json; const d=J($input.first().json);
if(j.en_disco) return [{json:j}];
if(!d.ok) throw new Error('sello_pago adn: '+(d.error||'sin respuesta')+' · llamadas hechas: '+(d.llamadas_hechas!=null?d.llamadas_hechas:'?')+' · peor caso US$'+(d.peor_caso!=null?d.peor_caso:'?'));
return [{json:{...j, adn_ako_texto:normalizarAdn(d,j), adn_json:d.adn_json||null, formato_adn:d.formato||'texto_ako', adn_salida:d.salida, adn_intentos:d.intentos||[]}}];