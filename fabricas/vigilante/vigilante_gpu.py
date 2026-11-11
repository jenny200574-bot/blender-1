#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vigilante GPU — cron cada 30 min en el 213 (Ricardo t541u/t542u).

Lista los pods de RunPod y termina SOLO los que:
  - se llaman myia-fabricas-motor-* (lista blanca estricta), y
  - no están en uso por un trabajo del motor, y
  - llevan más de 20 minutos en ese estado (RUNNING o EXITED).

Nunca toca el pod de Star 32soe7oh2f1gtf ni ningún pod de otro nombre.
Nunca imprime ni guarda la clave: la lee del mismo archivo que el motor
(config gpu.runpod_env → secretos/runpod.env).

Si hay duda (candado tomado y no se identifica el pod, proceso del motor
vivo sin pod claro, error de API), solo registra y no termina nada.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import socket
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

# IPv4: en el 213 RunPod por IPv6 no responde (mismo truco que gpu_pod).
try:
    import urllib3.util.connection as _uc
    _uc.allowed_gai_family = lambda: socket.AF_INET
except Exception:
    pass

BOGOTA = ZoneInfo("America/Bogota")
STAR_ID = "32soe7oh2f1gtf"
PREFIJO = "myia-fabricas-motor-"
GRACIA_MIN_DEF = 20

FABRICAS = Path("/opt/myia-fabricas")
CONFIG_FABRICAS = FABRICAS / "config" / "config.json"
LOCK_FABRICAS = FABRICAS / "gpu.lock"
LEDGER_FABRICAS = FABRICAS / "ledger_gpu.json"
MOTORES_ROOT = Path("/opt/myia-motor-unificado")

LOG_PATH = FABRICAS / "logs" / "vigilante_gpu.log"
ALERTAS_DIR = FABRICAS / "alertas"
ESTADO_PATH = FABRICAS / "vigilante" / "estado.json"
LOCK_VIGILANTE = FABRICAS / "vigilante" / "vigilante.lock"

PROC_RE = re.compile(
    r"(correr_escena|entrada_motor|entrada_n8n|entrada_ssh|"
    r"gpu_pod|motor_blender|sb3d_argon)",
    re.I,
)
POD_ID_RE = re.compile(r"\b([a-z0-9]{11,16})\b")
IGNORAR_LEDGER_DIR = re.compile(r"(respaldo|backup|\.bak)", re.I)


def ahora_bogota() -> datetime:
    return datetime.now(BOGOTA)


def fmt_ts(dt: datetime | None = None) -> str:
    d = dt or ahora_bogota()
    return d.strftime("%Y-%m-%d %H:%M:%S") + " America/Bogota"


def iso_bogota(dt: datetime | None = None) -> str:
    return (dt or ahora_bogota()).isoformat(timespec="seconds")


def log(msg: str, fh=None) -> None:
    line = f"{fmt_ts()} | {msg}"
    print(line, flush=True)
    if fh is not None:
        fh.write(line + "\n")
        fh.flush()


def cargar_config() -> dict:
    if not CONFIG_FABRICAS.is_file():
        return {}
    try:
        return json.loads(CONFIG_FABRICAS.read_text())
    except Exception:
        return {}


def leer_clave(env_file: Path) -> str:
    if not env_file.is_file():
        raise RuntimeError(f"no existe el archivo de clave: {env_file}")
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:]
        if line.startswith("RUNPOD_API_KEY="):
            k = line.split("=", 1)[1].strip().strip('"').strip("'")
            if k:
                return k
    raise RuntimeError("falta RUNPOD_API_KEY en el archivo de clave del servicio")


def clave_desde_config(cfg: dict) -> str:
    g = cfg.get("gpu") or {}
    env = Path(g.get("runpod_env") or str(FABRICAS / "secretos" / "runpod.env"))
    return leer_clave(env)


def forcemos_ipv4_requests():
    return None


def api_myself(key: str) -> dict:
    import requests
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    q = (
        "{ myself { currentSpendPerHr clientBalance "
        "pods { id name desiredStatus costPerHr lastStatusChange "
        "machine { gpuDisplayName } runtime { uptimeInSeconds } } } }"
    )
    r = requests.post(
        "https://api.runpod.io/graphql",
        headers=headers,
        json={"query": q},
        timeout=90,
    )
    r.raise_for_status()
    j = r.json()
    if j.get("errors"):
        raise RuntimeError("RunPod GraphQL: " + str(j["errors"])[:200])
    return j["data"]["myself"]


def api_terminar(key: str, pod_id: str) -> str:
    import requests
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    r = requests.delete(
        f"https://rest.runpod.io/v1/pods/{pod_id}",
        headers=headers,
        timeout=90,
    )
    if r.status_code in (200, 204):
        return f"DELETE {r.status_code}"
    # respaldo GraphQL, igual que el motor
    r2 = requests.post(
        "https://api.runpod.io/graphql",
        headers=headers,
        json={
            "query": "mutation($id:String!){ podTerminate(input:{podId:$id}) }",
            "variables": {"id": pod_id},
        },
        timeout=90,
    )
    try:
        j = r2.json()
    except Exception:
        j = {"text": (r2.text or "")[:120]}
    if r2.status_code >= 400 or (isinstance(j, dict) and j.get("errors")):
        raise RuntimeError(f"no se pudo terminar: REST {r.status_code}, GQL {r2.status_code}")
    return f"GQL {r2.status_code} (REST {r.status_code})"


# ---------- detección de trabajo activo ----------

def _leer_json(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def candados_configurados(cfg: dict) -> list[Path]:
    out = []
    g = cfg.get("gpu") or {}
    for raw in (g.get("lock"), str(LOCK_FABRICAS)):
        if raw:
            p = Path(raw)
            if p not in out:
                out.append(p)
    if MOTORES_ROOT.is_dir():
        for conf in sorted(MOTORES_ROOT.glob("*/config_motor.json")):
            if IGNORAR_LEDGER_DIR.search(str(conf)):
                continue
            d = _leer_json(conf)
            if not isinstance(d, dict):
                continue
            lock = (d.get("gpu") or {}).get("lock")
            if lock:
                p = Path(lock)
                if p not in out:
                    out.append(p)
    return out


def ledgers_conocidos(cfg: dict) -> list[Path]:
    out = []
    g = cfg.get("gpu") or {}
    for raw in (g.get("ledger"), str(LEDGER_FABRICAS)):
        if raw:
            p = Path(raw)
            if p.is_file() and p not in out:
                out.append(p)
    if MOTORES_ROOT.is_dir():
        for p in sorted(MOTORES_ROOT.glob("*/ledger_gpu_motor.json")):
            if IGNORAR_LEDGER_DIR.search(str(p)):
                continue
            if p.is_file() and p not in out:
                out.append(p)
    return out


def motor_root_de(path: Path) -> Path | None:
    try:
        path = path.resolve()
    except Exception:
        return None
    parts = path.parts
    if "myia-motor-unificado" not in parts:
        return None
    i = parts.index("myia-motor-unificado")
    if i + 1 < len(parts):
        return Path(*parts[: i + 2])
    return None


def titular_candado(lock: Path) -> tuple[bool, list[int]]:
    """True si el candado gpu.lock está tomado. Nunca deja el candado cogido."""
    if not lock.exists():
        return False, []
    pids = pids_con_archivo(lock)
    ocupado = False
    try:
        # r+ no trunca (el motor abre en 'w'; nosotros no debemos vaciarlo).
        fd = open(lock, "r+")
    except PermissionError:
        try:
            fd = open(lock, "r")
        except Exception:
            return bool(pids), pids
    except Exception:
        return bool(pids), pids
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
        ocupado = False
    except BlockingIOError:
        ocupado = True
    except Exception:
        ocupado = bool(pids)
    finally:
        try:
            fd.close()
        except Exception:
            pass
    return ocupado, pids


def pids_con_archivo(path: Path) -> list[int]:
    pids = []
    try:
        objetivo = path.resolve()
    except Exception:
        objetivo = path
    proc = Path("/proc")
    if not proc.is_dir():
        return pids
    for d in proc.iterdir():
        if not d.name.isdigit():
            continue
        fd_dir = d / "fd"
        try:
            for link in fd_dir.iterdir():
                try:
                    dest = Path(os.readlink(link))
                except Exception:
                    continue
                if dest == objetivo or str(dest) == str(objetivo):
                    pids.append(int(d.name))
                    break
        except Exception:
            continue
    return sorted(set(pids))


def cmdline_de(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\x00", b" ")
        return raw.decode("utf-8", "replace").strip()
    except Exception:
        return ""


def cwd_de(pid: int) -> Path | None:
    try:
        return Path(os.readlink(f"/proc/{pid}/cwd"))
    except Exception:
        return None


def procesos_motor() -> list[dict]:
    """Procesos del motor / GPU en este servidor."""
    out = []
    proc = Path("/proc")
    if not proc.is_dir():
        return out
    for d in proc.iterdir():
        if not d.name.isdigit():
            continue
        pid = int(d.name)
        cmd = cmdline_de(pid)
        if not cmd or not PROC_RE.search(cmd):
            continue
        # no contar al propio vigilante
        if "vigilante_gpu" in cmd:
            continue
        cwd = cwd_de(pid)
        root = motor_root_de(cwd) if cwd else None
        if root is None and "/opt/myia-motor-unificado/" in cmd:
            m = re.search(r"/opt/myia-motor-unificado/([^/\s]+)", cmd)
            if m:
                root = MOTORES_ROOT / m.group(1)
        out.append({"pid": pid, "cmd": cmd[:400], "cwd": str(cwd) if cwd else "", "motor": str(root) if root else ""})
    return out


def extraer_ids_de_texto(texto: str, candidatos: set[str] | None = None) -> set[str]:
    hallados = set(POD_ID_RE.findall(texto or ""))
    if candidatos is not None:
        return {x for x in hallados if x in candidatos}
    return hallados


def pods_en_ledger(path: Path, solo_en_curso: bool = True) -> list[dict]:
    d = _leer_json(path)
    if not isinstance(d, dict):
        return []
    out = []
    for e in d.get("entradas") or []:
        if not isinstance(e, dict):
            continue
        if solo_en_curso and e.get("estado") != "en_curso":
            continue
        pid = e.get("pod_id")
        if pid:
            out.append({
                "pod_id": str(pid),
                "ledger": str(path),
                "etiqueta": e.get("etiqueta"),
                "inicio": e.get("inicio"),
                "estado": e.get("estado"),
                "n": e.get("n"),
            })
    return out


def pod_terminado_en_estado(motor: Path, pod_id: str) -> bool | None:
    """True si algún estado.json de una corrida marca ese pod como ya terminado
    y no hay otra mención en_curso. None si no hay dato."""
    visto = None
    corridas = motor / "corridas"
    if not corridas.is_dir():
        return None
    try:
        directorios = list(corridas.iterdir())
    except Exception:
        return None
    for d in directorios:
        if not d.is_dir():
            continue
        est = _leer_json(d / "estado.json")
        if not isinstance(est, dict):
            continue
        def walk(o):
            nonlocal visto
            if isinstance(o, dict):
                if str(o.get("pod_id") or "") == pod_id:
                    term = o.get("pod_terminado")
                    if term is True:
                        visto = True if visto is None else visto
                    elif term is False:
                        visto = False
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(est)
    return visto


def logs_recientes_mencionan(motor: Path, pod_id: str, max_s: int = 45 * 60) -> bool:
    corridas = motor / "corridas"
    if not corridas.is_dir():
        return False
    ahora = time.time()
    try:
        rutas = list(corridas.glob("*/*.log")) + list(corridas.glob("*.log"))
        rutas += list(corridas.glob("*/estado.json"))
        rutas += list(corridas.glob("*/reporte_motor.json"))
    except Exception:
        return False
    for p in rutas:
        try:
            if ahora - p.stat().st_mtime > max_s:
                continue
            txt = p.read_text(errors="replace")[-80000:]
        except Exception:
            continue
        if pod_id in txt:
            # si el mismo archivo dice que ese pod ya se terminó y no hay 'en_curso'
            # posterior, no cuenta como activo por el log solo.
            if f"pod {pod_id}" in txt or pod_id in txt:
                return True
    return False


def construir_contexto(cfg: dict, pods_ids: set[str]) -> dict:
    procs = procesos_motor()
    candados = []
    pids_candado = set()
    duda_candado = False
    for lock in candados_configurados(cfg):
        ocupado, pids = titular_candado(lock)
        candados.append({"path": str(lock), "ocupado": ocupado, "pids": pids})
        if ocupado:
            pids_candado.update(pids)
            if not pids:
                duda_candado = True

    # unir procesos titulares del candado aunque no coincidan con PROC_RE
    pids_proc = {p["pid"] for p in procs}
    for pid in pids_candado:
        if pid not in pids_proc:
            cmd = cmdline_de(pid)
            cwd = cwd_de(pid)
            root = motor_root_de(cwd) if cwd else None
            procs.append({"pid": pid, "cmd": cmd[:400], "cwd": str(cwd) if cwd else "", "motor": str(root) if root else "", "via": "candado"})
            pids_proc.add(pid)

    ledgers = []
    for lp in ledgers_conocidos(cfg):
        ledgers.extend(pods_en_ledger(lp, solo_en_curso=True))

    # pods referenciados por procesos vivos
    activos: dict[str, list[str]] = {}

    def marca(pod_id: str, razon: str):
        if not pod_id or pod_id == STAR_ID:
            return
        activos.setdefault(pod_id, []).append(razon)

    motores_con_proceso = set()
    for p in procs:
        if p.get("motor"):
            motores_con_proceso.add(p["motor"])
        txt = " ".join([p.get("cmd") or "", p.get("cwd") or ""])
        for pid in extraer_ids_de_texto(txt, pods_ids or None):
            if not pods_ids or pid in pods_ids:
                marca(pid, f"cmdline/cwd del proceso {p['pid']}")

    # ledgers en_curso solo cuentan si hay proceso vivo en ese árbol del motor,
    # o si el titular del candado vive en ese árbol. Un en_curso huérfano
    # (prueba caída) NO protege el pod para siempre.
    for e in ledgers:
        pod_id = e["pod_id"]
        root = motor_root_de(Path(e["ledger"]))
        root_s = str(root) if root else ""
        if root_s and root_s in motores_con_proceso:
            # si el estado ya marcó ese pod como terminado, el ledger puede
            # haberse quedado a medias: no proteger por ledger solo.
            term = pod_terminado_en_estado(root, pod_id) if root else None
            if term is True:
                continue
            marca(pod_id, f"ledger en_curso {e['ledger']} (proceso vivo en {root_s})")
        elif not root_s:
            # ledger de fábricas: proteger solo si hay proceso o candado
            if procs or any(c["ocupado"] for c in candados):
                marca(pod_id, f"ledger fábricas en_curso {e['ledger']}")

    # logs / estado recientes de un motor con proceso vivo
    for root_s in motores_con_proceso:
        root = Path(root_s)
        for pod_id in pods_ids:
            if pod_id in activos:
                continue
            term = pod_terminado_en_estado(root, pod_id)
            if term is True:
                continue
            if logs_recientes_mencionan(root, pod_id):
                marca(pod_id, f"mencionado en logs/estado recientes de {root_s}")

    hay_proceso_motor = bool(procs)
    hay_candado = any(c["ocupado"] for c in candados)
    # duda: candado ocupado y no logramos saber de qué pod se trata
    if hay_candado and not activos:
        duda_candado = True
    # proceso correr_escena vivo, candado libre (hueco entre fases GPU) y
    # todavía no hay pod asociado: no terminar NINGÚN pod motor.
    duda_proceso = False
    if hay_proceso_motor and not activos:
        # si el proceso está claramente en un motor, proteger todos
        duda_proceso = True

    return {
        "procesos": procs,
        "candados": candados,
        "ledgers_en_curso": ledgers,
        "activos": activos,
        "duda": duda_candado or duda_proceso,
        "duda_razon": (
            "candado ocupado sin pod identificado" if duda_candado else
            "proceso del motor vivo sin pod identificado (posible hueco entre fases)" if duda_proceso else
            ""
        ),
        "hay_proceso_motor": hay_proceso_motor,
        "hay_candado": hay_candado,
    }


def permitido_terminar(pod: dict, star_ids: set[str], prefijo: str) -> tuple[bool, str]:
    pid = str(pod.get("id") or "")
    nom = str(pod.get("name") or "")
    if not pid:
        return False, "sin id"
    if pid in star_ids:
        return False, "lista negra Star"
    if not nom.startswith(prefijo):
        return False, "fuera de la lista blanca de nombre"
    return True, "ok"


def cargar_estado() -> dict:
    d = _leer_json(ESTADO_PATH)
    if not isinstance(d, dict):
        return {"schema": "vigilante_gpu_v1", "idle": {}}
    d.setdefault("schema", "vigilante_gpu_v1")
    d.setdefault("idle", {})
    return d


def guardar_estado(d: dict) -> None:
    ESTADO_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = ESTADO_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
    os.replace(tmp, ESTADO_PATH)


def escribir_alerta(pod: dict, idle_min: float, ahorro: float, dry: bool) -> Path | None:
    if dry:
        return None
    ALERTAS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = ahora_bogota().strftime("%Y%m%d_%H%M")
    path = ALERTAS_DIR / f"GPU_APAGADA_{stamp}.txt"
    if path.exists():
        path = ALERTAS_DIR / f"GPU_APAGADA_{stamp}_{str(pod.get('id') or '')[:8]}.txt"
    rate = float(pod.get("costPerHr") or 0)
    cuerpo = (
        f"Fecha (America/Bogota): {fmt_ts()}\n"
        f"El vigilante GPU apagó un pod del motor que llevaba más de 20 minutos\n"
        f"sin un trabajo activo en el 213.\n\n"
        f"pod_id: {pod.get('id')}\n"
        f"nombre: {pod.get('name')}\n"
        f"estado: {pod.get('desiredStatus')}\n"
        f"costo_hora_usd: {rate:.4f}\n"
        f"minutos_sin_trabajo: {idle_min:.1f}\n"
        f"ahorro_estimado_usd (media hora de tarifa): {ahorro:.4f}\n"
        f"Star 32soe7oh2f1gtf: no tocado\n"
        f"dry_run: no\n"
    )
    path.write_text(cuerpo)
    return path


def resumen_candados(ctx: dict) -> str:
    parts = []
    for c in ctx["candados"]:
        if c["ocupado"]:
            pids = ",".join(str(x) for x in c["pids"]) or "?"
            parts.append(f"ocupado(pid={pids})")
        else:
            parts.append("libre")
    return "; ".join(parts) if parts else "sin candado"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Vigilante de pods GPU huérfanos del motor")
    ap.add_argument("--dry-run", action="store_true", help="solo muestra qué haría, no termina nada")
    ap.add_argument("--gracia-min", type=int, default=GRACIA_MIN_DEF)
    ap.add_argument("--prefijo", default=PREFIJO)
    ap.add_argument("--star", default=STAR_ID, help="id de Star, nunca se toca")
    args = ap.parse_args(argv)

    cfg = cargar_config()
    star_ids = {STAR_ID, args.star}
    star_cfg = ((cfg.get("gpu") or {}).get("star_no_tocar") or "").strip()
    if star_cfg:
        star_ids.add(star_cfg)
    prefijo = args.prefijo
    gracia = max(1, int(args.gracia_min))
    dry = bool(args.dry_run)

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ALERTAS_DIR.mkdir(parents=True, exist_ok=True)
    ESTADO_PATH.parent.mkdir(parents=True, exist_ok=True)

    # candado propio, no el gpu.lock del motor
    lk = open(LOCK_VIGILANTE, "a")
    try:
        fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        # otra instancia del vigilante: no hacer nada
        print(f"{fmt_ts()} | SKIP | otra instancia del vigilante está corriendo", flush=True)
        return 0

    modo = "DRY-RUN" if dry else "REAL"
    try:
        key =[REDACTED]
    except Exception as e:
        log(f"ERROR | no se pudo leer la clave del servicio ({e}). No se toca ningún pod.")
        return 2

    try:
        me = api_myself(key)
    except Exception as e:
        log(f"ERROR | no se pudo listar pods en RunPod ({type(e).__name__}). No se termina nada.")
        return 3

    pods = list(me.get("pods") or [])
    ids = {str(p.get("id") or "") for p in pods if p.get("id")}
    ctx = construir_contexto(cfg, ids)

    motor_pods = [p for p in pods if str(p.get("name") or "").startswith(prefijo)]
    star_pods = [p for p in pods if str(p.get("id") or "") in star_ids]
    otros = [p for p in pods if p not in motor_pods and p not in star_pods]

    log(
        f"CHECK | modo={modo} pods={len(pods)} motor={len(motor_pods)} "
        f"star={len(star_pods)} otros={len(otros)} "
        f"candado={resumen_candados(ctx)} procesos_motor={len(ctx['procesos'])} "
        f"gracia_min={gracia}"
    )
    if ctx["duda"]:
        log(f"DUDA | {ctx['duda_razon']}: no se termina ningún pod en esta pasada")
    for p in ctx["procesos"]:
        log(f"PROC | pid={p['pid']} motor={p.get('motor') or '-'} cmd={p['cmd'][:180]}")
    for e in ctx["ledgers_en_curso"]:
        vivo = "con_proceso" if any(
            Path(e["ledger"]).is_relative_to(Path(pr["motor"])) if pr.get("motor") else False
            for pr in ctx["procesos"]
        ) else "sin_proceso (no protege por sí solo)"
        # is_relative_to may fail on 3.12 it's ok; fallback:
        try:
            _ = vivo
        except Exception:
            vivo = "?"
        log(f"LEDGER | n={e.get('n')} estado={e.get('estado')} pod={e['pod_id']} etiqueta={e.get('etiqueta')} archivo={e['ledger']} {vivo}")

    estado = cargar_estado()
    idle = dict(estado.get("idle") or {})
    vistos_ahora = set()
    terminados = []
    ahorro_total = 0.0
    ahora = ahora_bogota()

    # Star siempre se declara excluido
    for p in star_pods:
        log(
            f"STAR | id={p.get('id')} nombre={p.get('name')} "
            f"estado={p.get('desiredStatus')} EXCLUIDO (lista negra, no se toca)"
        )
    for p in otros:
        log(
            f"OTRO | id={p.get('id')} nombre={p.get('name')} "
            f"estado={p.get('desiredStatus')} IGNORADO (fuera de lista blanca {prefijo})"
        )

    for p in motor_pods:
        pod_id = str(p.get("id") or "")
        nom = str(p.get("name") or "")
        status = str(p.get("desiredStatus") or "")
        try:
            rate = float(p.get("costPerHr") or 0)
        except (TypeError, ValueError):
            rate = 0.0
        up = ((p.get("runtime") or {}) or {}).get("uptimeInSeconds")
        ok_term, por_que = permitido_terminar(p, star_ids, prefijo)
        if not ok_term:
            log(f"POD | id={pod_id} nombre={nom} estado={status} NO-ACCION ({por_que})")
            continue

        razones = list(ctx["activos"].get(pod_id) or [])
        activo = bool(razones) or ctx["duda"]
        if ctx["duda"] and not razones:
            razones = [f"duda: {ctx['duda_razon']}"]

        if activo:
            idle.pop(pod_id, None)
            log(
                f"POD | id={pod_id} nombre={nom} estado={status} "
                f"tarifa_usd_h={rate:.4f} ACTIVO razon={'; '.join(razones)}"
            )
            continue

        # idle
        vistos_ahora.add(pod_id)
        prev = idle.get(pod_id) if isinstance(idle.get(pod_id), dict) else None
        if not prev or prev.get("nombre") != nom:
            idle[pod_id] = {
                "nombre": nom,
                "idle_desde": iso_bogota(ahora),
                "estado": status,
                "tarifa_usd_h": rate,
            }
            log(
                f"POD | id={pod_id} nombre={nom} estado={status} "
                f"tarifa_usd_h={rate:.4f} IDLE desde=ahora "
                f"(gracia {gracia} min, no se toca en esta pasada)"
            )
            continue

        try:
            desde = datetime.fromisoformat(prev["idle_desde"])
            if desde.tzinfo is None:
                desde = desde.replace(tzinfo=BOGOTA)
        except Exception:
            idle[pod_id]["idle_desde"] = iso_bogota(ahora)
            log(
                f"POD | id={pod_id} nombre={nom} estado={status} "
                f"IDLE (reloj de gracia reiniciado por fecha ilegible, no se toca)"
            )
            continue

        minutos = (ahora - desde).total_seconds() / 60.0
        ahorro = round(rate * (gracia / 60.0), 4)  # lo que se evitaria en una ventana de gracia
        if minutos < gracia:
            log(
                f"POD | id={pod_id} nombre={nom} estado={status} "
                f"tarifa_usd_h={rate:.4f} IDLE hace={minutos:.1f} min "
                f"(gracia {gracia} min, no se toca todavía)"
            )
            continue

        # Segunda comprobación justo antes de terminar
        ok_term, por_que = permitido_terminar(p, star_ids, prefijo)
        if not ok_term:
            log(f"POD | id={pod_id} nombre={nom} REHUSO última comprobación ({por_que})")
            continue
        # re-detectar procesos por si el trabajo arrancó durante la pasada
        ctx2 = construir_contexto(cfg, {pod_id})
        if ctx2["duda"] or pod_id in ctx2["activos"]:
            log(
                f"POD | id={pod_id} nombre={nom} REHUSO: apareció trabajo activo "
                f"o duda justo antes de terminar"
            )
            idle.pop(pod_id, None)
            continue

        accion = "TERMINAR_SECO" if dry else "TERMINAR"
        detalle = "no se llama a RunPod (dry-run)" if dry else ""
        alerta = None
        if not dry:
            try:
                detalle = api_terminar(key, pod_id)
                alerta = escribir_alerta(p, minutos, ahorro, dry=False)
            except Exception as e:
                log(
                    f"ERROR | al terminar id={pod_id} nombre={nom}: {type(e).__name__}. "
                    f"Se deja el pod y se reintenta en la próxima pasada."
                )
                continue
        else:
            # en seco no se escribe alerta real
            detalle = "dry-run: no se termina ni se escribe alerta"

        idle.pop(pod_id, None)
        terminados.append(pod_id)
        ahorro_total += ahorro
        log(
            f"{accion} | id={pod_id} nombre={nom} estado={status} "
            f"tarifa_usd_h={rate:.4f} idle_min={minutos:.1f} "
            f"ahorro_estimado_usd={ahorro:.4f} detalle={detalle}"
            + (f" alerta={alerta}" if alerta else "")
        )

    # limpia del estado pods que ya no existen
    for pid in list(idle.keys()):
        if pid not in vistos_ahora and pid not in ctx["activos"]:
            # si sigue en la lista de motor y está activo, ya se sacó; si desapareció, limpiar
            if pid not in {str(p.get("id") or "") for p in motor_pods}:
                idle.pop(pid, None)

    estado["idle"] = idle
    estado["ultima_pasada"] = iso_bogota(ahora)
    estado["ultima_modo"] = modo
    guardar_estado(estado)

    log(
        f"FIN | modo={modo} terminados={len(terminados)} "
        f"ahorro_estimado_usd={ahorro_total:.4f} "
        f"star_tocado=no"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print(f"{fmt_ts()} | ERROR | no controlado; no se termina ningún pod", flush=True)
        traceback.print_exc()
        sys.exit(1)
