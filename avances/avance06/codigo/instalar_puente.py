from pathlib import Path
import shutil,subprocess,os,json,hashlib
B=Path('/opt/myia-motor-v9/avance06_20261107');E=B/'entrega';bridge=Path('/opt/myia-taller-n8n/cajas/entrada_ssh.sh');sudo=Path('/etc/sudoers.d/myia-taller-n8n');sello=Path('/opt/myia-taller-n8n/cajas/sello_pago.py');wrapper=E/'codigo/puente_json.sh'
wrapper.chmod(0o755)
for n in ['generador.off','pago_adn_json.off']:(B/n).write_text('Guardia AVANCE06; red sólo con aprobación y ledger\n')
old=bridge.read_text();block='''# AVANCE06 Ricardo 2026-11-07 21:30 Bogota: sólo generador JSON acotado y sus argumentos.
if [[ "$CMD" =~ ^generador_json\\ (estado|ejecutar\\ [A-Za-z0-9][A-Za-z0-9_-]{0,79})$ ]] || [[ "$CMD" =~ ^generador_json\\ adn\\ b64\\.[A-Za-z0-9_-]+\\ --ok\\ [0-9]+(\\.[0-9]+)?\\ --aprobado\\ [A-Za-z0-9_-]+$ ]]; then
  read -r -a ARGS <<< "$CMD"
  exec sudo -n /opt/myia-motor-v9/avance06_20261107/entrega/codigo/puente_json.sh "${ARGS[@]:1}"
fi
'''
new=old.replace('# VER pre-gasto',block+'# VER pre-gasto',1);assert new!=old
stage=E/'codigo/entrada_ssh_nueva.sh';stage.write_text(new);subprocess.run(['/bin/bash','-n',str(stage)],check=True)
sudotext=sudo.read_text()+'\n# AVANCE06: no intérprete arbitrario, sólo wrapper root-owned con validación estricta\nn8ntaller ALL=(root) NOPASSWD: '+str(wrapper)+' *\n';ss=E/'codigo/sudoers_nuevo';ss.write_text(sudotext);ss.chmod(0o440);subprocess.run(['/usr/sbin/visudo','-cf',str(ss)],check=True)
# New mode opts in; all old requests follow exact original code.
src=sello.read_text();needle="    d = b64(a.pedido or '')\n";insert=needle+"    if a.op == 'adn' and d.get('formato') == 'ako_json/v1':\n        os.execv('/opt/myia-motor-v9/avance06_20261107/entrega/codigo/puente_json.sh', ['puente_json.sh'] + sys.argv[1:])\n";assert src.count(needle)==1;src=src.replace(needle,insert);compile(src,str(sello),'exec')
for p,text in [(bridge,new),(sudo,sudotext),(sello,src)]:
 tmp=p.with_name(p.name+'.av06_stage');tmp.write_text(text);tmp.chmod(p.stat().st_mode&0o777);os.replace(tmp,p)
subprocess.run(['/usr/sbin/visudo','-c'],check=True)
tests=[]
for cmd in ['generador_json estado','generador_json ejecutar missing_job','generador_json ejecutar ../../etc/passwd','generador_json estado;id']:
 r=subprocess.run(['runuser','-u','n8ntaller','--','env','SSH_ORIGINAL_COMMAND='+cmd,'/bin/bash',str(bridge)],capture_output=True,text=True);tests.append({'command':cmd,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
(E/'evidencias/puente_pruebas.json').write_text(json.dumps(tests,indent=2,ensure_ascii=False))
print(json.dumps({'backup':str(B/'respaldos'),'visudo':'PASS','tests':tests},ensure_ascii=False))
