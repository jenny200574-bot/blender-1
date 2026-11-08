// n8n Code node: SELLO ESTILO · 4 validar (5 bloques + párrafo)
// disabled: False
const j=$input.first().json; const f=[];
const a=j.adn_ako||{}; const t=String(j.adn_ako_texto||a.texto||'');
if(!t) f.push('sin ADN (Fase 2 no corrió)');
for(let n=1;n<=5;n++) if(t&&!new RegExp('^[ \\t>#*_\\-]*'+n+'[.)]','m').test(t)) f.push('falta bloque '+n+' del Maestro 05');
if(/\[GAP/.test(t)) f.push('GAP en ADN');
if(j.en_disco&&a.status&&a.status!=='PASS_SELLABLE') f.push('ADN en disco no pasa: '+(a.fails||[]).join(','));
function b64u(o){const s=unescape(encodeURIComponent(JSON.stringify(o)));const T="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";let r="";for(let i=0;i<s.length;i+=3){const a=s.charCodeAt(i),b=s.charCodeAt(i+1),c=s.charCodeAt(i+2);const n=(a<<16)|((b||0)<<8)|(c||0);r+=T[(n>>18)&63]+T[(n>>12)&63]+(i+1<s.length?T[(n>>6)&63]:"")+(i+2<s.length?T[n&63]:"");}return r;}
const J=(x)=>{try{return JSON.parse(String(x.stdout||'').trim().split('\n').pop());}catch(e){return {ok:false,error:'no JSON: '+String(x.stderr||x.stdout||'').slice(0,200)};}};
const sel={id:j.id,clase:'estilo',canal:j.canal}; if(j.adn_ako_texto) sel.adn_ako_texto=j.adn_ako_texto;
return [{json:{...j, ok:f.length===0, fails:f, sellar_b64:'b64.'+b64u(sel)}}];