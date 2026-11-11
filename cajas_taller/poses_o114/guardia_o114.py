"""o114 (t312u/t313u) GUARDIA DEL CUERPO — cualquier esqueleto (humano VRM, animal, rig hecho en código). Se llama EN CADA CUADRO.
Reglas (si una falla, la escena se RECHAZA nombrando hueso y cuadro):
  1. largo de cada hueso = su largo de reposo (± TOL_LARGO) — un hueso estirado/aplastado = cuerpo roto;
  2. altura sobre el piso <= altura de pie (× TOL_ALTO) — nadie crece;
  3. contacto según la pose (solo cuadros con la pose QUIETA, no en transición): pies; rodillas al arrodillarse; torso acostado;
  4. cabeza por encima de la cadera salvo poses acostadas;
  5. ningún hueso por debajo del piso (± TOL_PISO).
Roles (pie, rodilla, torso, cabeza, cadera) salen de la biblioteca humana (partes) o del clasificador universal (por geometría)."""
import math
from mathutils import Vector
TOL_LARGO, TOL_ALTO, TOL_PISO = 0.10, 1.08, 0.05
TOL_CONTACTO, TOL_TORSO = 0.10, 0.25   # fracción de la altura de pie del propio cuerpo (vale igual para un gato que para un gigante)
CONTACTO = {'de_pie': 'pie', 'caminando': 'pie_uno', 'senalando': 'pie', 'sentado': 'pie', 'de_rodillas': 'rodilla',
            'acostado_boca_arriba': 'torso', 'acostado_boca_abajo': 'torso'}
ACOSTADO = ('acostado', 'boca_arriba', 'boca_abajo', 'enrollado')

def roles(A, LIB=None, R=None):
    """{'pie': [(hueso, 'tail'|'head')], 'rodilla': [...], 'torso': [...], 'cabeza': (h, extremo), 'cadera': (h, extremo)} o None."""
    B = A.data.bones
    if LIB and all(LIB['partes'].get(k) in B for k in ('pie_izq', 'pie_der', 'pierna_izq', 'pierna_der', 'torso')):
        P = LIB['partes']; cab = 'J_Bip_C_Head' if 'J_Bip_C_Head' in B else P['cuello']
        return {'pie': [(P['pie_izq'], 'head'), (P['pie_der'], 'head')], 'rodilla': [(P['pierna_izq'], 'head'), (P['pierna_der'], 'head')],
                'torso': [(P['torso'], 'head'), (P['cuello'], 'head')], 'cabeza': (cab, 'head'), 'cadera': (P['torso'], 'head')}
    if R:
        patas = [R[k] for k in R if isinstance(R[k], list) and (k.startswith('pata_') or k.startswith('pierna_')) and R[k]]
        col = R.get('columna') or []
        return {'pie': [(hs[-1], 'punta') for hs in patas], 'rodilla': [(hs[len(hs) // 2], 'head') for hs in patas],
                'torso': [(h, 'head') for h in col[:2]], 'cabeza': ((R.get('cabeza') or col)[-1], 'tail') if (R.get('cabeza') or col) else None,
                'cadera': (col[0], 'head') if col else None}
    return None

class Guardia:
    def __init__(self, A, actor, ROL, mallas=(), piso_z=0.0):
        self.A, self.actor, self.ROL = A, actor, ROL
        # solo huesos que mueven piel (los de control como 'Root' se quedan en el origen y no son cuerpo)
        vg = set()
        for m in mallas:
            if getattr(m, 'type', '') != 'MESH' or not m.vertex_groups: continue
            usados = {g.group for v in m.data.vertices for g in v.groups if g.weight > 0.01}
            vg |= {m.vertex_groups[i].name for i in usados if i < len(m.vertex_groups)}
        self.cuerpo = [pb for pb in A.pose.bones if pb.name in vg] or list(A.pose.bones)
        # referencia = el cuerpo YA armado y DE PIE (con sus proporciones reales: gordura, altura, escala del rig)
        self.largo = {pb.name: (pb.tail - pb.head).length for pb in self.cuerpo if (pb.tail - pb.head).length >= 0.02}
        P = [A.matrix_world @ p for pb in self.cuerpo for p in (pb.head, pb.tail)]
        self.alto_pie = max(p.z for p in P) - piso_z                     # altura de pie sobre el piso
        self.tam = max(max(p[i] for p in P) - min(p[i] for p in P) for i in range(3))   # tamaño del cuerpo (alto o largo)
        self.techo = max(self.alto_pie, self.tam)   # nada sube más que el propio cuerpo (gente: su altura; animal: su largo)
        # ¿cuerpo erguido (humano) u horizontal (animal)? decide qué regla de "derecho" se usa
        self.erguido = False
        if ROL and ROL.get('cabeza') and ROL.get('cadera') and len(ROL.get('pie') or []) == 2:   # (Argon o114) erguido = 2 patas y cabeza SOBRE la cadera
            hc, cc = self._p(*ROL['cabeza']), self._p(*ROL['cadera'])
            self.erguido = hc.z - cc.z > 0.3 * self.alto_pie and math.hypot(hc.x - cc.x, hc.y - cc.y) < 0.35 * self.alto_pie
        tz = min((self._p(*t).z - piso_z for t in (ROL or {}).get('torso') or []), default=self.alto_pie)
        # acostado = torso cerca del piso: humano <= 25% de su altura; animal con patas: más bajo que de pie (75%); sin patas: su propio grosor
        self.torso_max = TOL_TORSO * self.alto_pie if self.erguido else (0.75 * tz if (ROL or {}).get('pie') else 1.1 * tz + 0.02)
        self.fallas = []
    def _p(self, h, ext):
        pb = self.A.pose.bones[h]; W = self.A.matrix_world
        if ext == 'punta': return min(W @ pb.head, W @ pb.tail, key=lambda v: v.z)   # punta de la pata = su punto más bajo
        return W @ (pb.tail if ext == 'tail' else pb.head)
    def revisar(self, cuadro, pose, piso_z, quieta=True, elev=0.0):
        A = self.A; f = []; base = piso_z + elev
        for pb in self.cuerpo:
            L0 = self.largo.get(pb.name)
            if L0:
                r = (pb.tail - pb.head).length / L0
                if abs(r - 1) > TOL_LARGO: f.append(f'hueso {pb.name} con largo ×{r:.2f} (estirado/aplastado)')
        zs = [(A.matrix_world @ p).z for pb in self.cuerpo for p in (pb.head, pb.tail)]
        if max(zs) - base > self.techo * TOL_ALTO + 1e-3:
            top = max(self.cuerpo, key=lambda pb: max((A.matrix_world @ pb.head).z, (A.matrix_world @ pb.tail).z)).name
            f.append(f'altura {max(zs) - base:.2f} m > altura máxima del cuerpo {self.techo:.2f} m (hueso {top})')
        bajo = min(self.cuerpo, key=lambda pb: min((A.matrix_world @ pb.head).z, (A.matrix_world @ pb.tail).z))
        zb = min((A.matrix_world @ bajo.head).z, (A.matrix_world @ bajo.tail).z)
        if zb < base - TOL_PISO: f.append(f'hueso {bajo.name} {base - zb:.2f} m bajo el piso')
        R = self.ROL
        if R:
            acost = any(k in str(pose) for k in ACOSTADO)
            if self.erguido and not acost:
                hz, cz = self._p(*R['cabeza']).z, self._p(*R['cadera']).z
                if hz <= cz: f.append(f'cabeza ({R["cabeza"][0]}) por debajo de la cadera ({R["cadera"][0]}) sin estar acostado')
            elif not acost and R.get('pie') and R.get('torso'):   # animal: el lomo va por encima de las patas (si no, está patas arriba)
                lomo = sum(self._p(*t).z for t in R['torso']) / len(R['torso']); pata = max(self._p(*t).z for t in R['pie'])
                if lomo <= pata: f.append(f'lomo ({R["torso"][0][0]}) por debajo de las patas: cuerpo patas arriba sin estar acostado')
            c = CONTACTO.get(pose, 'torso' if acost else None)
            if quieta and c:
                k = 'pie' if c == 'pie_uno' else c
                if not R.get(k): c = k = 'torso'   # cuerpo sin patas (pez, serpiente): apoya el torso
                pts = [(h, self._p(h, e).z - base) for h, e in R.get(k) or []]
                if pts:
                    if c == 'pie_uno': ok = min(d for _, d in pts) <= TOL_CONTACTO * self.alto_pie; malo = min(pts, key=lambda x: x[1])
                    elif c == 'torso': ok = max(d for _, d in pts) <= self.torso_max; malo = max(pts, key=lambda x: x[1])   # (Argon o114) TODO el torso abajo, no solo la cadera
                    else: ok = max(d for _, d in pts) <= TOL_CONTACTO * self.alto_pie; malo = max(pts, key=lambda x: x[1])
                    if not ok: f.append(f'pose {pose}: {k} sin contacto con el piso (hueso {malo[0]} a {malo[1]:.2f} m)')
        for x in f: self.fallas.append({'actor': self.actor, 'cuadro': cuadro, 'falla': x})
        return f
