// n8n Code node: 02 · resultado T317
// disabled: False
const r=JSON.parse(String($input.first().json.stdout||'').trim().split('\n').pop());if(r.ok!==true)throw new Error('T317: '+String(r.error||r.estado||'no terminó'));return [{json:r}];