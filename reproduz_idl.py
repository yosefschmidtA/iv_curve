#!/usr/bin/env python3
"""Reproduz em Python a coleta de intensidade do coleta_no_step_*.pro (IDL).

Recebe os 5 pontos marcados a mao e refaz, energia por energia: ajuste cubico da
posicao do spot, refinamento de +-3 px no maximo, recorte 15x15, subtracao de fundo
por (c)oluna ou (l)inha e soma. Compara com o .txt gravado pelo IDL.

Uso:
    python3 reproduz_idl.py --modo c
    python3 reproduz_idl.py --modo l --energia-final 308
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def div_idl(a, b):
    # Divisao inteira do IDL trunca em direcao a zero; o // do Python arredonda para baixo.
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


def round_idl(v):
    # ROUND do IDL arredonda .5 para longe do zero; o round() do Python arredonda para o par.
    return int(np.floor(v + 0.5)) if v >= 0 else -int(np.floor(-v + 0.5))


def le_pontos(caminho):
    dados = np.loadtxt(caminho, comments="#")
    return dados[:, 0], dados[:, 1], dados[:, 2]


def le_curva_idl(caminho):
    linhas = Path(caminho).read_text(encoding="latin-1").splitlines()[3:]
    tab = np.array([[float(c) for c in l.split()] for l in linhas if l.strip()])
    return tab[:, 0].astype(int), tab[:, 1], tab[:, 2]


def carrega(dir_jpg, energia, inverte_y):
    img = np.asarray(Image.open(Path(dir_jpg) / f"{energia}.jpg").convert("L"))
    # read_jpeg, order=1 guarda a linha de cima do arquivo em y=0, que e a ordem do numpy.
    return img[::-1] if inverte_y else img


def intensidade(img, c_poly, l_poly, modo, largura=15):
    ny, nx = img.shape
    meio = largura // 2
    pix = lambda x, y: int(img[y, x])

    def janela(c, l):
        rc, rl = round_idl(c), round_idl(l)
        return (max(rc - meio, 0), min(rc + meio, nx - 1),
                max(rl - meio, 0), min(rl + meio, ny - 1))

    col1, col2, lin1, lin2 = janela(c_poly, l_poly)
    maximo = img[lin1:lin2 + 1, col1:col2 + 1].max()
    # Mesma ordem do laco do IDL (x por fora, y por dentro): c_poly muda dentro do laco
    # e as comparacoes seguintes ja usam o valor novo.
    for x in range(col1, col2 + 1):
        for y in range(lin1, lin2 + 1):
            if pix(x, y) >= maximo:
                if c_poly - 3 <= x <= c_poly + 3:
                    c_poly = x
                if l_poly - 3 <= y <= l_poly + 3:
                    l_poly = y
    col1, col2, lin1, lin2 = janela(c_poly, l_poly)
    spot = img[lin1:lin2 + 1, col1:col2 + 1].astype(np.int64)  # spot[y, x]
    ny_s, nx_s = spot.shape

    soma = np.zeros(ny_s if modo == "c" else nx_s, dtype=np.int64)
    if modo == "c":
        n = ny_s - 1
        for x in range(nx_s):
            ini, fim = 0, n
            for yy in range(ny_s):
                if spot[yy, x] < spot[ini, x] and yy <= n // 4:
                    ini = yy
                if spot[yy, x] < spot[fim, x] and yy > (n * 3) // 4:
                    fim = yy
            a, b = int(spot[ini, x]), int(spot[fim, x])
            fita = np.array([div_idl((b - a) * yy, n) + a for yy in range(ny_s)])
            soma += spot[:, x] - fita
    else:
        n = nx_s - 1
        for y in range(ny_s):
            ini, fim = 0, n
            for xx in range(nx_s):
                if spot[y, xx] < spot[y, ini] and xx <= n // 4:
                    ini = xx
                if spot[y, xx] < spot[y, fim] and xx > (n * 3) // 4:
                    fim = xx
            a, b = int(spot[y, ini]), int(spot[y, fim])
            fita = np.array([div_idl((b - a) * xx, n) + a for xx in range(nx_s)])
            soma += spot[y, :] - fita
    # O IDL soma so os primeiros img_size(0) elementos; com spot quadrado e o vetor todo.
    return int(soma[:nx_s].sum()), c_poly, l_poly


def grava_curva(args, energias, intensidades):
    inten = np.array(intensidades, dtype=float)
    # smooth(Intensity, 3, /EDGE_TRUNCATE) do IDL, sobre o vetor inteiro (inclusive a ultima energia).
    pad = np.concatenate([inten[:1], inten, inten[-1:]])
    suave = (pad[:-2] + pad[1:-1] + pad[2:]) / 3
    n = len(energias) - 1 if args.como_idl else len(energias)
    experimento = Path(args.curva).read_text(encoding="utf-8").splitlines()[0]
    # Mesmo layout do printf livre do IDL (inteiro em 22 colunas, double em 16 com 8 algarismos significativos),
    # para que um diff contra o .txt do IDL mostre so diferenca de valor.
    with open(args.saida, "w", encoding="utf-8") as f:
        f.write(f"{experimento}\n")
        f.write(f"Valor de normalização={inten.max():#16.8g}\n")
        f.write("energia  intensidade intensidade - smoothing\n")
        for e, i, s in zip(energias[:n], inten[:n], suave[:n]):
            f.write(f"{e:22d}{i:#16.8g}{s:#16.8g}\n")
    print(f"gravado: {args.saida} ({n} energias, {energias[0]} a {energias[n - 1]} eV)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modo", choices=["c", "l"], required=True)
    ap.add_argument("--jpg", default="dados/jpg")
    ap.add_argument("--pontos", default="dados/pontos_marcados_10.txt")
    ap.add_argument("--curva", default="dados/curva_IV_idl_10.txt")
    ap.add_argument("--energia-final", type=int, default=308)
    ap.add_argument("--inverte-y", action="store_true", help="testa a outra convencao de eixo y")
    ap.add_argument("--float32", action="store_true", help="ajuste em precisao simples, como o POLY_FIT sem /DOUBLE")
    ap.add_argument("--saida", default="dados/curva_IV_python_10.txt")
    ap.add_argument("--como-idl", action="store_true",
                    help="omite a ultima energia, repetindo o bug do IDL, para dar diff limpo")
    args = ap.parse_args()

    e_pts, col_pts, lin_pts = le_pontos(args.pontos)
    tipo = np.float32 if args.float32 else np.float64
    pc = np.polyfit(e_pts.astype(tipo), col_pts.astype(tipo), 3)
    pl = np.polyfit(e_pts.astype(tipo), lin_pts.astype(tipo), 3)

    e_idl, i_idl, s_idl = le_curva_idl(args.curva)
    energias = [e for e in range(int(e_idl[0]), args.energia_final + 1)
                if (Path(args.jpg) / f"{e}.jpg").exists()]

    resultados = {}
    for e in energias:
        img = carrega(args.jpg, e, args.inverte_y)
        resultados[e] = intensidade(img, float(np.polyval(pc, e)), float(np.polyval(pl, e)), args.modo)

    grava_curva(args, energias, [resultados[e][0] for e in energias])

    iguais, difs = 0, []
    for e, i_ref in zip(e_idl, i_idl):
        i_py = resultados[e][0]
        if i_py == int(i_ref):
            iguais += 1
        else:
            difs.append((e, int(i_ref), i_py))
    print(f"modo={args.modo} inverte_y={args.inverte_y} float32={args.float32}")
    print(f"energias identicas ao IDL: {iguais} de {len(e_idl)}")
    for e, ref, py in difs[:15]:
        c, l = resultados[e][1], resultados[e][2]
        print(f"  {e:4d} eV  IDL={ref:7d}  Python={py:7d}  dif={py - ref:+6d}  spot=({c}, {l})")
    if len(difs) > 15:
        print(f"  ... mais {len(difs) - 15}")
    ultimo = args.energia_final
    if ultimo in resultados and ultimo not in set(e_idl):
        esperado = 3 * s_idl[-1] - i_idl[-2] - i_idl[-1]
        print(f"{ultimo} eV (nao gravado pelo IDL): Python={resultados[ultimo][0]}  deduzido da coluna suavizada={esperado:.0f}")


if __name__ == "__main__":
    main()
