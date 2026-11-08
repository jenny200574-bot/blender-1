// n8n Code node: V · Argon video prompt (stub)
// disabled: False
const CAM = { 'static':'static shot, locked-off camera','push in':'slow push in','pull out':'slow pull out','pan left':'pan left','pan right':'pan right','tilt up':'tilt up','tilt down':'tilt down','orbit left':'orbit left around subject','orbit right':'orbit right around subject','dolly in':'dolly in','dolly out':'dolly out','truck left':'truck left','truck right':'truck right','crane up':'crane up','crane down':'crane down','tracking':'tracking shot following subject','handheld':'subtle handheld' };
const VOZ = { ako: 'young adult female voice, warm and soft timbre, medium-high pitch, gentle Colombian Spanish accent, calm unhurried pace' }; // stub: luego sale de ADN · Voz sellada
return $input.all().map(it => { const t = it.json; const fallas = [];
  const cam = CAM[t.cmd]; if (!cam) fallas.push('cmd cámara fuera de vocabulario: ' + t.cmd);
  let p = `${t.accion}. Camera: ${cam || '??'}. Keep identity and style from first frame.`;
  if (t.dialogo) { if (!VOZ[t.pj]) fallas.push('sin ADN · Voz para ' + t.pj); p += ` ${t.pj} says in Spanish, lips synced: "${t.dialogo}" — voice: ${VOZ[t.pj]}. Native audio, no music, no subtitles.`; }
  else p += ' Ambient sound only, no dialogue, no music.';
  return { json: { ...t, veo_prompt_en: p, motor: 'veo3 (NO se llama)', fallas } }; });
