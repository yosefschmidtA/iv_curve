"""Calculo das curvas IV de LEED: leitura das imagens, rastreio do spot e intensidade.

A intensidade e o refinamento de posicao reproduzem o coleta_no_step_*.pro do IDL
exatamente (conferido: 139/139 energias identicas na curva 10.txt).
"""
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

EXTENSOES = (".jpg", ".jpeg", ".tif", ".tiff")


def div_idl(a, b):
    # Divisao inteira do IDL trunca em direcao a zero; o // do Python arredonda para baixo.
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


def round_idl(v):
    # ROUND do IDL arredonda .5 para longe do zero; o round() do Python arredonda para o par.
    return int(np.floor(v + 0.5)) if v >= 0 else -int(np.floor(-v + 0.5))


def lista_imagens(pasta):
    """{energia: caminho} para os arquivos cujo nome e so o numero da energia."""
    achadas = {}
    for p in Path(pasta).iterdir():
        if p.suffix.lower() in EXTENSOES and re.fullmatch(r"\d+", p.stem):
            achadas.setdefault(int(p.stem), p)
    return dict(sorted(achadas.items()))


@lru_cache(maxsize=None)
def carrega_cinza(caminho):
    """Imagem 2D uint8 com img[linha, coluna]; mesma convencao do read_jpeg, order=1 do IDL."""
    im = Image.open(caminho)
    if im.mode in ("L", "P", "I;16", "I"):
        a = np.asarray(im.convert("L"))
    else:
        rgb = np.asarray(im.convert("RGB")).astype(np.float32)
        # Media de R,G,B, e nao a luminancia ponderada do PIL: a camera e Bayer e o
        # fosforo e verde; a media nao privilegia canal e preserva a soma relativa.
        a = np.clip(np.round(rgb.mean(axis=2)), 0, 255).astype(np.uint8)
    a.setflags(write=False)
    return a


def le_xml(caminho):
    """BeamCurrent (uA) e Energy (eV) do .xml do software do LEED, ou None."""
    p = Path(caminho)
    if not p.exists():
        return {"BeamCurrent": None, "Energy": None}
    # Gravado em UTF-16; lido como UTF-8 o regex nao acha nada.
    texto = p.read_bytes().decode("utf-16", errors="replace")
    valores = {}
    for tag in ("BeamCurrent", "Energy"):
        m = re.search(rf"<{tag}>\s*([-\d.eE+]+)\s*</{tag}>", texto)
        valores[tag] = float(m.group(1)) if m else None
    return valores


def _janela(img, c, l, meio):
    ny, nx = img.shape
    rc, rl = round_idl(c), round_idl(l)
    return (max(rc - meio, 0), min(rc + meio, nx - 1),
            max(rl - meio, 0), min(rl + meio, ny - 1))


def refina(img, c_poly, l_poly, largura=15, raio=3):
    """Move a posicao prevista para o maximo da janela, se ele estiver a ate `raio` px.

    Com raio=3 e o laco do IDL, inclusive a ordem (x por fora, y por dentro) e o fato de
    c_poly mudar dentro do laco, o que altera as comparacoes seguintes.
    """
    meio = max(largura, 2 * raio + 1) // 2
    col1, col2, lin1, lin2 = _janela(img, c_poly, l_poly, meio)
    bloco = img[lin1:lin2 + 1, col1:col2 + 1]
    maximo = bloco.max()
    ys, xs = np.nonzero(bloco >= maximo)
    # np.nonzero percorre linha a linha; o IDL percorre coluna a coluna.
    ordem = np.lexsort((ys, xs))
    for x, y in zip(xs[ordem] + col1, ys[ordem] + lin1):
        if c_poly - raio <= x <= c_poly + raio:
            c_poly = int(x)
        if l_poly - raio <= y <= l_poly + raio:
            l_poly = int(y)
    return c_poly, l_poly


def intensidade(img, c, l, modo="c", largura=15):
    """Soma do spot menos o fundo linear, em janela largura x largura centrada em (c, l)."""
    col1, col2, lin1, lin2 = _janela(img, c, l, largura // 2)
    spot = img[lin1:lin2 + 1, col1:col2 + 1].astype(np.int64)
    n_somados = spot.shape[1]  # img_size(0) do IDL: numero de colunas do recorte
    if modo == "l":
        spot = spot.T  # por linha e o mesmo calculo com os eixos trocados
    ny_s, nx_s = spot.shape
    n = ny_s - 1
    soma = np.zeros(ny_s, dtype=np.int64)
    for x in range(nx_s):
        col = spot[:, x]
        ini, fim = 0, n
        for yy in range(ny_s):
            if col[yy] < col[ini] and yy <= n // 4:
                ini = yy
            if col[yy] < col[fim] and yy > (n * 3) // 4:
                fim = yy
        a, b = int(col[ini]), int(col[fim])
        fita = np.array([div_idl((b - a) * yy, n) + a for yy in range(ny_s)])
        soma += col - fita
    # O IDL soma so os primeiros img_size(0) elementos de soma; com janela quadrada e tudo.
    return int(soma[:n_somados].sum())


def suaviza3(v):
    """smooth(v, 3, /EDGE_TRUNCATE) do IDL."""
    v = np.asarray(v, dtype=float)
    if len(v) < 3:
        return v.copy()
    pad = np.concatenate([v[:1], v, v[-1:]])
    return (pad[:-2] + pad[1:-1] + pad[2:]) / 3


def ajusta_fisico(ancoras, centro=None):
    """Posicao do spot = centro + K/sqrt(E), por eixo.

    A distancia ao centro do padrao cai com 1/sqrt(E) (comprimento de onda do eletron).
    Medido nos 5 pontos da curva 10: residuo <= 2 px, contra ate 24 px de um ajuste linear.
    Com 2+ ancoras ajusta centro e K; com 1 ancora precisa do centro conhecido.
    Devolve (centro_col, K_col, centro_lin, K_lin).
    """
    es = np.array(sorted(ancoras), dtype=float)
    cols = np.array([ancoras[e][0] for e in sorted(ancoras)], dtype=float)
    lins = np.array([ancoras[e][1] for e in sorted(ancoras)], dtype=float)
    u = 1 / np.sqrt(es)
    if len(es) >= 2 and np.ptp(es) > 0:
        A = np.c_[np.ones_like(u), u]
        (cc, kc), *_ = np.linalg.lstsq(A, cols, rcond=None)
        (cl, kl), *_ = np.linalg.lstsq(A, lins, rcond=None)
        return cc, kc, cl, kl
    if centro is None:
        raise ValueError("com 1 ponto marcado e preciso conhecer o centro do padrao")
    cc, cl = centro
    return cc, float(np.mean((cols - cc) / u)), cl, float(np.mean((lins - cl) / u))


def pico_local(img, c, l, raio=4, snr_min=4.0):
    """Maximo da imagem suavizada 3x3 a ate `raio` px de (c, l).

    Se o pico nao se destaca do entorno (spot apagado nessa energia), devolve a propria
    previsao: seguir ruido faz a janela pular para outro lugar e contaminar as seguintes.
    """
    ny, nx = img.shape
    borda = raio + 6
    rc, rl = round_idl(c), round_idl(l)
    x0, x1 = max(rc - borda, 1), min(rc + borda, nx - 2)
    y0, y1 = max(rl - borda, 1), min(rl + borda, ny - 2)
    if x1 <= x0 or y1 <= y0:
        return c, l, 0.0
    bloco = img[y0 - 1:y1 + 2, x0 - 1:x1 + 2].astype(np.float32)
    suave = sum(bloco[dy:dy + y1 - y0 + 1, dx:dx + x1 - x0 + 1] for dy in range(3) for dx in range(3)) / 9
    yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
    perto = (xx - c) ** 2 + (yy - l) ** 2 <= raio ** 2
    if not perto.any():
        return c, l, 0.0
    fundo = np.median(suave[~perto]) if (~perto).any() else np.median(suave)
    ruido = 1.4826 * np.median(np.abs(suave[~perto] - fundo)) + 0.5 if (~perto).any() else 1.0
    k = np.argmax(np.where(perto, suave, -np.inf))
    snr = float((suave.flat[k] - fundo) / ruido)
    if snr < snr_min:
        return c, l, snr
    return int(xx.flat[k]), int(yy.flat[k]), snr


def trajetoria(imagens, ancoras, metodo="fisico", largura=15, raio=None, centro=None):
    """Posicao do spot em cada energia.

    imagens: {energia: caminho}; ancoras: {energia: (coluna, linha)} marcadas a mao.
    metodo "polinomio": ajuste cubico pelas ancoras e refinamento +-3 px, como o IDL
        (exige 4 ancoras ou mais).
    metodo "fisico": previsao centro + K/sqrt(E) ajustada nas ancoras, e busca do pico
        a ate `raio` px. Fora da amostra (curva 10) acerta pontos nao usados a 1-4 px com
        2 ancoras. Um "seguir" energia a energia foi testado e perdeu o spot acima de
        210 eV (erro de 35 px), quando ele fica no nivel do ruido.
    """
    energias = list(imagens)
    if not ancoras:
        return {}
    if metodo == "fisico":
        raio = 4 if raio is None else raio
        cc, kc, cl, kl = ajusta_fisico(ancoras, centro)
        pos = {}
        for e in energias:
            if e in ancoras:
                # O clique manda: e o jeito de o usuario corrigir uma energia ruim.
                pos[e] = tuple(float(v) for v in ancoras[e])
                continue
            u = 1 / np.sqrt(e)
            c, l, _ = pico_local(carrega_cinza(imagens[e]), cc + kc * u, cl + kl * u, raio)
            pos[e] = (float(c), float(l))
        return pos
    if metodo == "polinomio":
        if len(ancoras) < 4:
            raise ValueError("o metodo polinomio precisa de pelo menos 4 pontos marcados")
        raio = 3 if raio is None else raio
        e_a = np.array(sorted(ancoras), dtype=float)
        pc = np.polyfit(e_a, [ancoras[e][0] for e in sorted(ancoras)], 3)
        pl = np.polyfit(e_a, [ancoras[e][1] for e in sorted(ancoras)], 3)
        return {e: refina(carrega_cinza(imagens[e]), float(np.polyval(pc, e)),
                          float(np.polyval(pl, e)), largura, raio) for e in energias}

    raise ValueError(f"metodo desconhecido: {metodo}")


def curva(imagens, posicoes, modo="c", largura=15):
    return {e: intensidade(carrega_cinza(imagens[e]), *posicoes[e], modo=modo, largura=largura)
            for e in posicoes}
