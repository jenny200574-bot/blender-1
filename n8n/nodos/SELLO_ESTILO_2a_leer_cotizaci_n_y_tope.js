// n8n Code node: SELLO ESTILO · 2a leer cotización y tope
// disabled: False
function b64u(o){const s=unescape(encodeURIComponent(JSON.stringify(o)));const T="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";let r="";for(let i=0;i<s.length;i+=3){const a=s.charCodeAt(i),b=s.charCodeAt(i+1),c=s.charCodeAt(i+2);const n=(a<<16)|((b||0)<<8)|(c||0);r+=T[(n>>18)&63]+T[(n>>12)&63]+(i+1<s.length?T[(n>>6)&63]:"")+(i+2<s.length?T[n&63]:"");}return r;}
const J=(x)=>{try{return JSON.parse(String(x.stdout||'').trim().split('\n').pop());}catch(e){return {ok:false,error:'no JSON: '+String(x.stderr||x.stdout||'').slice(0,200)};}};
const e=$('SELLO ESTILO · 1 entrada imagen de referencia').first().json; const d=J($input.first().json);
if(d.error) throw new Error('extraer: '+d.error);
const ped=d.pedidos||[]; const cot=Number(d.cotizado_usd||0);
const en_disco=!!(d.ok&&d.adn_ako);
const sin_img=(d.avisos||[]).some(a=>/sin imagen/.test(a));
const pago_abierto=e.habilitar_pago===true&&String(e.ok_ricardo||'').trim()!==''&&Number(e.tope_usd||0)>=cot&&!sin_img;
return [{json:{id:d.id||e.id, canal:e.canal, clase:'estilo', en_disco, adn_ako:d.adn_ako||null, pago_abierto, seguir:en_disco||pago_abierto,
  cotizacion:ped.map(p=>({fase:p.fase,que:p.que,endpoint:p.endpoint,usd:p.usd!=null?p.usd:p.usd_estimado,entrada:p.entrada_imagenes})), cotizado_usd:cot,
  maestro:d.maestro||null, maestro_sha256:d.maestro_sha256||null, avisos:d.avisos||[], prompt_maestro:d.prompt||null, tope_usd:Number(e.tope_usd||0)}}];