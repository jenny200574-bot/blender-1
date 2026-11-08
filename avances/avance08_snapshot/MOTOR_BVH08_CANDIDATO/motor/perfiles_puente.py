"""Conserva el modelo físico del núcleo bueno; no inventa kilogramos ni apoyos."""
import importlib.util,math
from pathlib import Path
from seguridad import sha
ROOT=Path(__file__).resolve().parent
def adaptar(d):
    p=ROOT/'heredado/esqueleto_adn.py';sp=importlib.util.spec_from_file_location('EA_puente',p);ea=importlib.util.module_from_spec(sp);sp.loader.exec_module(ea)
    for e in d.get('entities',[]):
        if e.get('type')!='CHARACTER' or e.get('physics') or not e.get('legacy'):continue
        old=e['legacy'];bones=ea.huesos(old['spec']);weights={b['nombre']:b['radio']**2*max(.02,math.dist(b['cabeza'],b['cola']))*(3 if b['nombre']=='cabeza' else 1) for b in bones}
        e['physics']={'bone_mass_weights':weights,'mass_model':'MN.centro_masa del núcleo bueno; pesos relativos, NO kg medidos','support_method':'legacy_solver','radii_m':{b['nombre']:b['radio'] for b in bones},'balance_margin_m':old['profile']['margen_equilibrio_m'],'source':{'path':'motor/heredado/movimiento_natural.py','sha256':sha(ROOT/'heredado/movimiento_natural.py'),'profile':'entrada.json#/actors/profile'}}
    return d
