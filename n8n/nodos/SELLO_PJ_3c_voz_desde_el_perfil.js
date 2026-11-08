// n8n Code node: SELLO PJ · 3c voz desde el perfil
// disabled: False
function b64u(o){const s=unescape(encodeURIComponent(JSON.stringify(o)));const T="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";let r="";for(let i=0;i<s.length;i+=3){const a=s.charCodeAt(i),b=s.charCodeAt(i+1),c=s.charCodeAt(i+2);const n=(a<<16)|((b||0)<<8)|(c||0);r+=T[(n>>18)&63]+T[(n>>12)&63]+(i+1<s.length?T[(n>>6)&63]:"")+(i+2<s.length?T[n&63]:"");}return r;}
const J=(x)=>{try{return JSON.parse(String(x.stdout||'').trim().split('\n').pop());}catch(e){return {ok:false,error:'no JSON: '+String(x.stderr||x.stdout||'').slice(0,200)};}};
const j=$('SELLO PJ · 3a leer ADN').first().json; const c=J($input.first().json);
const pj=((c.cubo||{}).personajes||[]).find(x=>x.id===j.id||(x.ids_canal||[]).includes(j.id));
return [{json:{...j, voz_adn:pj?pj.voz_adn||null:null, nombre:pj?pj.nombre:null}}];