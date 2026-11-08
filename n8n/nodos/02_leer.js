// n8n Code node: 02 · leer
// disabled: False
// PISTA INMI (2026-10-29): orden 74 — lee la respuesta (una línea JSON) del cubo 02. GRATIS: el cubo nunca llama a un servicio pago.
const out = [];
for (const it of $input.all()) {
  const txt = String(it.json.stdout || '').trim().split('\n').pop();
  let r;
  try { r = JSON.parse(txt); } catch (e) { throw new Error('El cubo 02 no devolvió JSON. stdout: ' + String(it.json.stdout || '').slice(0, 300) + ' | stderr: ' + String(it.json.stderr || '').slice(0, 300)); }
  if (!r.ok) throw new Error('Cubo 02: ' + r.error);
  if (r.llamadas_pagas || r.usd_gastado) throw new Error('Cubo 02: no debía llamar a un servicio pago');
  out.push({ json: { cubo: '02', resumen: r.resumen, faltan: r.faltan || [], ...r } });
}
return out;
