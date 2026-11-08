// n8n Code node: SELLO ESTILO · 3 preparar ADN · Maestro 05 (sello_pago)
// disabled: False
function b64u(o){const s=unescape(encodeURIComponent(JSON.stringify(o)));const T="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";let r="";for(let i=0;i<s.length;i+=3){const a=s.charCodeAt(i),b=s.charCodeAt(i+1),c=s.charCodeAt(i+2);const n=(a<<16)|((b||0)<<8)|(c||0);r+=T[(n>>18)&63]+T[(n>>12)&63]+(i+1<s.length?T[(n>>6)&63]:"")+(i+2<s.length?T[n&63]:"");}return r;}
const J=(x)=>{try{return JSON.parse(String(x.stdout||'').trim().split('\n').pop());}catch(e){return {ok:false,error:'no JSON: '+String(x.stderr||x.stdout||'').slice(0,200)};}};
const Q=s=>String(s||'').replace(/[^A-Za-z0-9._-]/g,'-').replace(/^-+/,'').slice(0,60)||'sin-ok';
const j=$input.first().json; const e=$('SELLO ESTILO · 1c armar pedido (gratis)').first().json;
const ok=Number(j.tope_usd||0).toFixed(4);
if(j.en_disco) return [{json:{...j, pago_cmd:'estado'}}];
const img=String(e.imagen_ref||(e.sello_estilo||{}).imagen||''); if(!img) throw new Error('Falta la imagen de estilo (imagen_ref o sello 1a)');
const ped={id:String(j.id),canal:String(j.canal),clase:'estilo',imagenes:[img]};
// JSON es opt-in explícito; pedidos antiguos sin formato conservan la vía original.
if(e.formato_adn==='ako_json/v1') ped.formato='ako_json/v1';
return [{json:{...j, pago_cmd:'adn b64.'+b64u(ped)+' --ok '+ok+' --aprobado '+Q(e.ok_ricardo)}}];