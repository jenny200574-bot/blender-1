# -*- coding: utf-8 -*-
"""gpu_pod.py — [fábricas v2 3D, 9-nov-2026, OK Ricardo pt993u/pt994u] Corre un trabajo de Blender en un pod RunPod GPU, sin pasos a mano.
Receta: pack blender523_egl_ready + render_auto.py de Ako (4-nov, ledger 320): scp Blender 5.2.3 prearmado + debs EGL, setup_pod.sh,
Blender con --gpu-backend opengl y EGL NVIDIA (sin Xvfb). Reglas:
  - Ledger ANTES de crear el pod (ledger_gpu.json del servicio) y cierre con costo real (diferencia de saldo) y costo por tiempo.
  - Tope por trabajo (config gpu.tope_por_trabajo_usd) vigilado cada 10 s: si se pasa → se termina el pod.
  - Bolsa de pruebas: gastado_previo + ledger + tope ≤ bolsa; saldo RunPod ≥ saldo_minimo. Si no → no crea pod.
  - Un trabajo GPU a la vez (candado). Termina SIEMPRE el pod propio; nunca toca Star 32soe7oh2f1gtf ni pods ajenos.
  - Claves: archivo del servicio (secretos/runpod.env, 600); jamás se imprimen ni se guardan en logs.
"""
from __future__ import annotations
import fcntl, json, os, subprocess, threading, time
from datetime import datetime
from pathlib import Path

STAR_ID = '32soe7oh2f1gtf'

# El 213 resuelve RunPod también por IPv6, que allí no responde (requests se cuelga; curl cae a IPv4). Forzar IPv4.
import socket
try:
    import urllib3.util.connection as _uc
    _uc.allowed_gai_family = lambda: socket.AF_INET
except Exception:
    pass
ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04'
GPU_BARATAS = ['NVIDIA RTX A4500', 'NVIDIA RTX A5000', 'NVIDIA RTX A4000', 'NVIDIA RTX 4000 Ada Generation', 'NVIDIA L4',
               'NVIDIA GeForce RTX 3090', 'NVIDIA GeForce RTX 4090']

def ahora(): return datetime.now().astimezone().isoformat(timespec='seconds')

class GpuError(RuntimeError): pass

class Pod:
    def __init__(self, cfg: dict):
        g = cfg.get('gpu') or {}
        self.g = g
        self.ledger = Path(g.get('ledger', str(ROOT / 'ledger_gpu.json')))
        self.pack = Path(g['pack_dir'])
        self.key_file = Path(g.get('ssh_key', str(ROOT / 'secretos' / 'id_ed25519_fabricas')))
        self.env_file = Path(g.get('runpod_env', str(ROOT / 'secretos' / 'runpod.env')))
        self.lock = Path(g.get('lock', str(ROOT / 'gpu.lock')))
        self._k = None

    # ---------- claves (nunca se imprimen) ----------
    def key(self) -> str:
        if self._k: return self._k
        for line in self.env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith('export '): line = line[7:]
            if line.startswith('RUNPOD_API_KEY='):
                self._k = line.split('=', 1)[1].strip().strip('"').strip("'"); return self._k
        raise GpuError('falta RUNPOD_API_KEY en secretos/runpod.env')

    def _req(self, method, url, **kw):
        import requests
        h = {'Authorization': f'Bearer {self.key()}', 'Content-Type': 'application/json'}
        return requests.request(method, url, headers=h, timeout=90, **kw)

    def gql(self, q, v=None):
        r = self._req('POST', 'https://api.runpod.io/graphql', json={'query': q, 'variables': v or {}}); r.raise_for_status()
        j = r.json()
        if j.get('errors'): raise GpuError(str(j['errors'])[:300])
        return j['data']

    def rest(self, method, path, body=None):
        r = self._req(method, f'https://rest.runpod.io/v1{path}', json=body)
        try: return r.status_code, r.json()
        except Exception: return r.status_code, r.text

    def myself(self):
        return self.gql('{ myself { currentSpendPerHr clientBalance pods { id name desiredStatus costPerHr } } }')['myself']

    # ---------- ledger ----------
    def _ledger_load(self):
        return json.loads(self.ledger.read_text()) if self.ledger.exists() else {'schema': 'ledger_gpu_fabricas_v1', 'entradas': []}

    def _ledger_save(self, d):
        tmp = self.ledger.with_suffix('.tmp'); tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1)); os.replace(tmp, self.ledger)

    def gastado(self):
        d = self._ledger_load()
        return round(sum(max(e.get('costo_real_usd') or 0, e.get('costo_tiempo_usd') or 0) if e.get('estado') != 'en_curso'
                         else (e.get('tope_usd') or 0) for e in d['entradas']), 6)

    def ledger_abrir(self, e):
        d = self._ledger_load(); e['n'] = len(d['entradas']) + 1; d['entradas'].append(e); self._ledger_save(d); return e['n']

    def ledger_cerrar(self, n, **kw):
        d = self._ledger_load()
        for e in d['entradas']:
            if e['n'] == n: e.update(kw)
        self._ledger_save(d)

    # ---------- pod ----------
    def crear(self, nombre):
        pub = Path(str(self.key_file) + '.pub').read_text().strip()
        gpus = self.g.get('gpu_tipos') or GPU_BARATAS
        ultimo = None
        g = self.g
        intentos = ([('SECURE', True)] if g.get('network_volume_id') else []) + [('SECURE', False), ('COMMUNITY', False)]
        if g.get('solo_volumen') and g.get('network_volume_id'):   # [20261110] Ricardo t1012u: GPU solo por el volumen sa3r0sj70m
            intentos = [('SECURE', True)] * int(g.get('intentos_volumen', 3))
        for cloud, con_vol in intentos:   # 1.º con el volumen persistente (pod listo); si no hay GPU en ese centro, sin volumen
            body = {'name': nombre, 'imageName': IMAGE, 'gpuCount': 1, 'cloudType': cloud, 'gpuTypeIds': gpus, 'gpuTypePriority': 'custom',
                    'supportPublicIp': True, 'containerDiskInGb': 40, 'volumeInGb': 0, 'ports': ['22/tcp'],
                    'env': {'PUBLIC_KEY': pub, 'SSH_PUBLIC_KEY': pub, 'NVIDIA_DRIVER_CAPABILITIES': 'all'}}
            if con_vol:
                body.update(networkVolumeId=g['network_volume_id'], volumeMountPath='/workspace', dataCenterIds=[g['datacenter_id']])
            code, data = self.rest('POST', '/pods', body)
            ultimo = (code, str(data)[:300])
            if con_vol and g.get('solo_volumen') and not (code in (200, 201) and isinstance(data, dict) and data.get('id')):
                time.sleep(int(g.get('espera_volumen_s', 45)))
            if code in (200, 201) and isinstance(data, dict) and data.get('id'):
                if data['id'] == STAR_ID: raise GpuError('API devolvió el id de Star: abortar')
                self.ultimo_con_volumen = con_vol
                return data, cloud + ('+volumen' if con_vol else '')
        raise GpuError(f'no se pudo crear pod: {ultimo}')

    def terminar(self, pod_id):
        if not pod_id or pod_id == STAR_ID: raise GpuError('REHUSO terminar Star o pod vacío')
        code, data = self.rest('DELETE', f'/pods/{pod_id}')
        if code not in (200, 204):
            self.gql('mutation($id:String!){ podTerminate(input:{podId:$id}) }', {'id': pod_id})
        return code

    def esperar_ssh(self, pod_id, timeout_s=420):
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            try:
                info = self.gql(f'{{ pod(input:{{podId:"{pod_id}"}}) {{ id machine {{ gpuDisplayName }} runtime {{ ports {{ ip isIpPublic privatePort publicPort }} }} }} }}').get('pod') or {}
                for p in (info.get('runtime') or {}).get('ports') or []:
                    if str(p.get('privatePort')) == '22' and p.get('isIpPublic'):
                        ip, port = p['ip'], int(p['publicPort'])
                        if self.ssh(ip, port, 'echo SSH_OK', timeout=30).stdout.strip().endswith('SSH_OK'):
                            return ip, port, (info.get('machine') or {}).get('gpuDisplayName')
            except Exception:
                pass
            time.sleep(8)
        raise GpuError(f'SSH no listo en {timeout_s}s')

    def _sshopts(self, port):
        return ['-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null', '-o', 'ConnectTimeout=20',
                '-o', 'ServerAliveInterval=30', '-i', str(self.key_file)]

    def ssh(self, ip, port, cmd, timeout=600):
        return subprocess.run(['ssh', *self._sshopts(port), '-p', str(port), f'root@{ip}', cmd], capture_output=True, text=True, timeout=timeout)

    def scp_a(self, ip, port, local, remoto, timeout=900):
        subprocess.run(['scp', *self._sshopts(port), '-P', str(port), str(local), f'root@{ip}:{remoto}'], check=True, capture_output=True, timeout=timeout)

    def scp_de(self, ip, port, remoto, local, timeout=600):
        subprocess.run(['scp', *self._sshopts(port), '-P', str(port), f'root@{ip}:{remoto}', str(local)], check=True, capture_output=True, timeout=timeout)

    # ---------- un trabajo completo ----------
    def correr(self, etiqueta: str, subir: list, comando: str, traer: str, destino: Path, autorizacion: str, log=print, setup_cmd=None) -> dict:
        """subir: [(ruta_local, ruta_remota)]; comando: shell en el pod tras setup; traer: archivo remoto (tgz) → destino."""
        g = self.g
        if not g.get('enabled'): raise GpuError('GPU apagada en config (gpu.enabled=false)')
        tope = float(g.get('tope_por_trabajo_usd') or 0)
        if tope <= 0: raise GpuError('sin tope por trabajo')
        lk = open(self.lock, 'w')
        fcntl.flock(lk, fcntl.LOCK_EX)          # un trabajo GPU a la vez (espera su turno)
        est = {'etiqueta': etiqueta, 'pod_id': None, 'ok': False, 'pasos': [], 'tiempos_s': {}}
        TT = est['tiempos_s']
        n = None; pod_id = None; t0 = None; rate = None; bal0 = None
        try:
            bolsa = float(g.get('bolsa_usd') or 0); previo = float(g.get('gastado_previo_usd') or 0)
            usado = previo + self.gastado()
            if usado + tope > bolsa + 1e-9: raise GpuError(f'bolsa: usado {usado:.4f} + tope {tope} > {bolsa}')
            me = self.myself(); bal0 = float(me.get('clientBalance') or 0)
            if bal0 < float(g.get('saldo_minimo_runpod_usd') or 0) + tope:
                raise GpuError(f'saldo RunPod {bal0:.2f} < mínimo {g.get("saldo_minimo_runpod_usd")} + tope {tope}')
            n = self.ledger_abrir({'etiqueta': etiqueta, 'estado': 'en_curso', 'inicio': ahora(), 'tope_usd': tope,
                                   'costo_estimado_usd': g.get('costo_estimado_usd', 0.15), 'autorizacion': autorizacion,
                                   'balance_runpod_antes': bal0, 'bolsa_usada_antes_usd': round(usado, 4),
                                   'nota': f'Pod propio; nunca Star {STAR_ID}; se termina siempre'})
            est['ledger_n'] = n; log(f'ledger_gpu #{n} abierto ANTES del pod (tope US${tope})')
            t_crear = time.time()
            pod, cloud = self.crear(f'myia-fabricas-{etiqueta}-{datetime.now():%H%M%S}'[:60])
            pod_id = pod['id']; t0 = time.time(); rate = float(pod.get('costPerHr') or 0) or None
            est.update(pod_id=pod_id, cloud=cloud, costo_hora=rate); self.ledger_cerrar(n, pod_id=pod_id, cloud=cloud, costo_hora=rate, pod_creado=ahora())
            log(f'pod {pod_id} creado ({cloud}, US${rate}/h)')
            parar = threading.Event()
            def vigia():
                while not parar.wait(10):
                    r = rate or float(g.get('costo_hora_max', 0.9))
                    if r * (time.time() - t0) / 3600 >= tope * 0.95 or time.time() - t0 > float(g.get('max_segundos', 2400)):
                        est['tope_alcanzado'] = True
                        try: self.terminar(pod_id)
                        except Exception: pass
                        return
            threading.Thread(target=vigia, daemon=True).start()
            ip, port, gname = self.esperar_ssh(pod_id); est['gpu'] = gname; log(f'SSH listo ({gname})')
            TT['arranque_pod'] = round(time.time() - t_crear, 1); ta = time.time()
            listo = self.ssh(ip, port, 'mkdir -p /root/job /root/out; mountpoint -q /workspace && test -x /workspace/myia_gpu/blender/blender '
                                       '&& test -f /workspace/myia_gpu/libs/.ok && echo VOLUMEN_LISTO', 60).stdout
            est['volumen_listo'] = 'VOLUMEN_LISTO' in listo
            if not est['volumen_listo']:
                self.scp_a(ip, port, self.pack / 'blender-5.2.3-linux-x64.tar.xz', '/root/job/blender-5.2.3-linux-x64.tar.xz', 1200)
                self.scp_a(ip, port, self.pack / 'blender523_egl_libs_scripts.tar', '/root/job/blender523_egl_libs_scripts.tar')
            for loc, rem in subir: self.scp_a(ip, port, loc, rem)
            TT['subida'] = round(time.time() - ta, 1); ta = time.time(); log('subida lista' + (' (volumen listo: sin Blender)' if est['volumen_listo'] else ''))
            r = self.ssh(ip, port, setup_cmd or 'tar -xf /root/job/blender523_egl_libs_scripts.tar -C /root/job && bash /root/job/scripts/setup_pod.sh /root/job',
                         int(g.get('setup_max_segundos', 420)))
            est['setup_tail'] = r.stdout[-400:]
            TT['setup'] = round(time.time() - ta, 1); ta = time.time()
            if 'SETUP_OK' not in r.stdout: raise GpuError('setup falló: ' + (r.stdout + r.stderr)[-300:])
            log('Blender 5.2.3 listo en el pod')
            r = self.ssh(ip, port, comando, int(g.get('max_segundos', 2400)))
            TT['trabajo_en_pod'] = round(time.time() - ta, 1); ta = time.time()
            est['comando_tail'] = r.stdout[-8000:]; est['comando_rc'] = r.returncode
            est['pasos'].append(['construccion', round(time.time() - t0)])
            destino.parent.mkdir(parents=True, exist_ok=True)
            self.scp_de(ip, port, traer, destino); est['paquete'] = str(destino); TT['bajada'] = round(time.time() - ta, 1)
            est['ok'] = r.returncode == 0; log(f'paquete traído rc={r.returncode}')
        except Exception as e:
            est['error'] = f'{type(e).__name__}: {str(e)[:400]}'; log('ERROR ' + est['error'])
        finally:
            try: parar.set()
            except Exception: pass
            if pod_id:
                try: est['terminate_http'] = self.terminar(pod_id)
                except Exception as e: est['terminate_error'] = str(e)[:200]
                seg = time.time() - t0; ta = time.time()
                spend = None; vivo = [pod_id]
                for _ in range(24):
                    try:
                        me = self.myself(); vivo = [p for p in me.get('pods') or [] if p['id'] == pod_id]
                        spend = me.get('currentSpendPerHr')
                        if not vivo: break
                    except Exception: pass
                    time.sleep(5)
                est['pod_terminado'] = True if not vivo else False; TT['terminar_pod'] = round(time.time() - ta, 1)
                bal1 = None
                for _ in range(12):    # la facturación llega con retraso: esperar a que el saldo baje (máx. 2 min)
                    try: bal1 = float(self.myself().get('clientBalance') or 0)
                    except Exception: pass
                    if bal1 is not None and bal1 < bal0: break
                    time.sleep(10)
                est['segundos_pod'] = round(seg); est['costo_tiempo_usd'] = round((rate or 0) * seg / 3600, 6)
                est['costo_real_usd'] = round(max(0.0, bal0 - (bal1 if bal1 is not None else bal0)), 6)
                est['balance_runpod_despues'] = bal1
                stars = [p for p in (self.myself().get('pods') or []) if p['id'] == STAR_ID]
                est['star_32soe7oh2f1gtf'] = (stars[0].get('desiredStatus') if stars else 'no_listado') + ' (no tocado)'
            if n:
                self.ledger_cerrar(n, estado='ok' if est.get('ok') else 'fallo', fin=ahora(), pod_terminado=est.get('pod_terminado'),
                                   segundos_pod=est.get('segundos_pod'), costo_tiempo_usd=est.get('costo_tiempo_usd'),
                                   costo_real_usd=est.get('costo_real_usd'), balance_runpod_despues=est.get('balance_runpod_despues'),
                                   gpu=est.get('gpu'), error=est.get('error'), star=est.get('star_32soe7oh2f1gtf'))
            lk.close()
        return est

def limpiar_huerfanos(cfg: dict, log=print) -> list:
    """Al arrancar el servicio: si quedó una entrada «en_curso» con pod propio (p. ej. reinicio a mitad), se termina ese pod.
    Solo pods anotados en ledger_gpu.json por este servicio; nunca Star."""
    p = Pod(cfg); hechos = []
    try:
        d = p._ledger_load()
        for e in d['entradas']:
            if e.get('estado') == 'en_curso' and e.get('pod_id') and e['pod_id'] != STAR_ID:
                try: p.terminar(e['pod_id']); hechos.append(e['pod_id'])
                except Exception as x: log(f'huérfano {e["pod_id"]}: {x}')
                p.ledger_cerrar(e['n'], estado='fallo', fin=ahora(), error='servicio reiniciado a mitad: pod terminado al arrancar',
                                nota_cierre='costo real: revisar saldo RunPod')
    except Exception as x:
        log(f'limpiar_huerfanos: {x}')
    return hechos
