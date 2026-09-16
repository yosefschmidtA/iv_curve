#!/usr/bin/env python3
"""Confere o leed_iv_core contra a curva que o IDL gravou (dados/curva_IV_idl_10.txt).

    python3 testa_core.py
"""
import sys

import numpy as np

import leed_iv_core as core
from reproduz_idl import le_curva_idl, le_pontos

falhas = 0


def confere(nome, ok, detalhe=""):
    global falhas
    print(f"[{'ok' if ok else 'FALHOU'}] {nome} {detalhe}")
    falhas += not ok


imagens = {e: p for e, p in core.lista_imagens("dados/jpg").items() if 30 <= e <= 308}
e_pts, c_pts, l_pts = le_pontos("dados/pontos_marcados_10.txt")
ancoras = {int(e): (float(c), float(l)) for e, c, l in zip(e_pts, c_pts, l_pts)}
e_idl, i_idl, s_idl = le_curva_idl("dados/curva_IV_idl_10.txt")

# 1. Metodo polinomio com os 5 pontos = IDL.
pos = core.trajetoria(imagens, ancoras, metodo="polinomio")
cur = core.curva(imagens, pos, modo="c")
iguais = sum(cur[e] == int(i) for e, i in zip(e_idl, i_idl))
confere("polinomio + fundo c reproduz o IDL", iguais == len(e_idl), f"({iguais}/{len(e_idl)})")
confere("308 eV igual ao deduzido do IDL", cur[308] == round(3 * s_idl[-1] - i_idl[-2] - i_idl[-1]), f"({cur[308]})")

# 2. Controle: fundo l tem de dar diferente, senao o teste acima nao distingue nada.
cur_l = core.curva(imagens, pos, modo="l")
iguais_l = sum(cur_l[e] == int(i) for e, i in zip(e_idl, i_idl))
confere("controle: fundo l NAO reproduz", iguais_l < len(e_idl) // 2, f"({iguais_l}/{len(e_idl)})")

# 3. Suavizacao igual a coluna 3 do IDL (calculada sobre o vetor com 308 eV).
suave = core.suaviza3([cur[e] for e in imagens])
confere("suavizacao igual ao IDL", np.allclose(suave[:-1], s_idl, atol=1e-3))

# 4. Fisico: ajustado com 2 pontos acerta os 3 que nao viu (a precisao do clique e ~2 px).
for usados in ((30, 160), (30, 290), (80, 260)):
    pos_f = core.trajetoria(imagens, {e: ancoras[e] for e in usados}, metodo="fisico")
    erros = {e: float(np.hypot(pos_f[e][0] - c, pos_f[e][1] - l)) for e, (c, l) in ancoras.items() if e not in usados}
    confere(f"fisico com {usados} acerta os outros (< 5 px)", max(erros.values()) < 5,
            " ".join(f"{e}eV:{d:.1f}px" for e, d in erros.items()))

# 5. Fisico com 1 clique e centro conhecido.
cc, _, cl, _ = core.ajusta_fisico({30: ancoras[30], 290: ancoras[290]})
pos_1 = core.trajetoria(imagens, {160: ancoras[160]}, metodo="fisico", centro=(cc, cl))
erros = {e: float(np.hypot(pos_1[e][0] - c, pos_1[e][1] - l)) for e, (c, l) in ancoras.items() if e != 160}
confere("fisico com 1 clique + centro acerta os outros (< 5 px)", max(erros.values()) < 5,
        " ".join(f"{e}eV:{d:.1f}px" for e, d in erros.items()))

sys.exit(1 if falhas else 0)
