#!/usr/bin/env python3
"""01: revisar respuestas YA pagadas y guardar las validas. Sin IA ni compuertas.
Uso: paso00_cadena revisar_guardar01 --canal cn-ID --capitulo N|ep-ID
     [--escenas 1,2,4] [--seco]. Escenas omitidas = todas las del mapa.
"""
import argparse, hashlib, json, re, shutil, socket, sys

from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

def _id(s):
    if len(s)>160 or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*',s):
        raise argparse.ArgumentTypeError('ID no valido: use letras, numeros, guion o guion bajo')
    return s

def _escenas(s):
    if not re.fullmatch(r'[1-9][0-9]{0,5}(,[1-9][0-9]{0,5}){0,999}',s):
        raise argparse.ArgumentTypeError('escenas: lista de numeros positivos separados por coma')
    return set(s.split(','))

def _sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def _manifest(root):
    return {str(p.relative_to(root)):_sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
def _no_pagar(*a,**k): raise RuntimeError('01 revisar y guardar: IA y red prohibidas')

def main(argv):
    ap=argparse.ArgumentParser(prog='paso00_cadena revisar_guardar01')
    ap.add_argument('--canal',required=True,type=_id)
    ap.add_argument('--capitulo',required=True,type=_id)
    ap.add_argument('--escenas',type=_escenas,default=None)
    ap.add_argument('--seco',action='store_true',help='valida sin escribir en cubos ni biblioteca; Blender usa temporales')
    a=ap.parse_args(argv)
    socket.socket.connect=_no_pagar
    import paso01_cubos as K, cubo01_accion as A, paso01_pago as PG
    PG.app=PG.correr=_no_pagar
    D=K.carpeta(a.canal,a.capitulo)
    if not D: return {'ok':False,'error':'no existe canal/capitulo','llamadas_pagas':0,'usd_gastado':0}
    D=D.resolve(); root=(K.TRABAJO/a.canal).resolve()
    if root not in D.parents: raise ValueError('capitulo fuera del canal')
    S=D/'cubos'/'01'
    if not S.is_dir(): return {'ok':False,'error':'no existen respuestas del 01','llamadas_pagas':0,'usd_gastado':0}
    all_e=K.escenas(D,set())
    nums={str(e['numero']) for e in all_e}
    if a.escenas and a.escenas-nums:
        return {'ok':False,'error':'escenas no existentes: '+','.join(sorted(a.escenas-nums)),'llamadas_pagas':0,'usd_gastado':0}
    if any(not re.fullmatch(r'[1-9][0-9]{0,5}',str(e['numero'])) for e in all_e if not a.escenas or str(e['numero']) in a.escenas):
        return {'ok':False,'error':'el mapa tiene numeros de escena no admitidos','llamadas_pagas':0,'usd_gastado':0}
    # Serializa solo este nuevo comando; no modifica otros comandos ni permisos.
    import fcntl
    lockdir=D/'respaldos'
    if not a.seco: lockdir.mkdir(parents=True,exist_ok=True)
    lock=None
    if not a.seco:
        lock=open(lockdir/'revisar_guardar01.lock','a')
        fcntl.flock(lock,fcntl.LOCK_EX)
    try:
        before=_manifest(S)
        cd=K.canal(a.canal); PC=K.personajes_canal(a.canal); G=K._guion(D)
        a.solo=a.escenas or set(); a.correr=False
        rows=[]; pending=[]
        for e in all_e:
            n=str(e['numero'])
            if a.escenas and n not in a.escenas: continue
            f=S/'respuestas'/('esc_'+n+'.txt')
            if not f.is_file() or not f.stat().st_size:
                rows.append({'escena':n,'estado':'omitida_sin_respuesta','guardada':False}); continue
            try:
                txt=f.read_text(encoding='utf-8'); obj=json.loads(txt[txt.find('{'):txt.rfind('}')+1])
                P,err=A.pedido(K,D,a,e,cd,PC,G,[])
                if err: raise ValueError(str(err))
                C,errs=A.validar(K,obj,e,P)
                if errs:
                    rows.append({'escena':n,'estado':'rechazada','guardada':False,'errores':errs}); continue
                row={'escena':n,'estado':'validada_seco' if a.seco else 'pendiente','guardada':False,
                     'fps':C.get('fps'),'duracion_s':C.get('duracion_s'),'avisos':C.get('avisos_codigo') or []}
                rows.append(row); pending.append((e,P,f,row))
            except Exception as ex:
                rows.append({'escena':n,'estado':'error','guardada':False,'error':str(ex)[:600]})
        backup=None
        if pending and not a.seco:
            tag=datetime.now(ZoneInfo('America/Bogota')).strftime('%Y%m%d_%H%M%S_%f')
            backup=lockdir/('antes_revisar_guardar01_'+tag+'_bogota')
            backup.mkdir(exist_ok=False)
            shutil.copytree(S,backup/'01')
            assert before==_manifest(backup/'01'),'respaldo no coincide'
            (backup/'SHA256SUMS').write_text(''.join(h+'  01/'+n+'\n' for n,h in before.items()),encoding='utf-8')
            for e,P,f,row in pending:
                n=row['escena']
                try:
                    r=A.revalidar(K,D,n,e,P,str(f),escribir=True)
                    row.update(estado='guardada' if r.get('ok') else 'error',guardada=bool(r.get('ok')),resultado=r)
                    if r.get('ok'): row['sha256']=_sha(S/('esc_'+n+'.json'))
                except Exception as ex: row.update(estado='error',error=str(ex)[:600])
        ok=not any(r['estado'] in ('error','rechazada') for r in rows)
        if a.seco: assert before==_manifest(S),'el modo seco modifico cubos/01'
        return {'ok':ok,'gratis':True,'seco':a.seco,'llamadas_pagas':0,'usd_gastado':0,
                'resumen':'01: '+str(sum(r['guardada'] for r in rows))+' guardadas; '+str(sum(r['estado']=='omitida_sin_respuesta' for r in rows))+' sin respuesta (no se generan)',
                'respaldo':str(backup) if backup else None,'escenas':rows}
    finally:
        if lock: lock.close()

if __name__=='__main__': print(json.dumps(main(sys.argv[1:]),ensure_ascii=False))
