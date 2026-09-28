#!/usr/bin/env python3
"""Media de curvas IV gravadas pelo coleta_no_step_*.pro (IDL), no mesmo formato do IDL.

Uso:
    python3 media_curvas_idl.py arquivo1.txt arquivo2.txt saida.txt
    python3 media_curvas_idl.py a.txt b.txt c.txt saida.txt      (aceita mais de dois)

Para cada energia: intensidade = media das intensidades; suavizada = media das suavizadas.
As curvas precisam ter exatamente as mesmas energias; se nao tiverem, nada e gravado.
A saida pode ser lida pelo le_curva_idl.py como qualquer arquivo do IDL.
"""
import sys


def le_curva_idl(caminho):
    with open(caminho, "rb") as f:
        bruto = f.read()
    try:
        texto = bruto.decode("utf-8")
    except UnicodeDecodeError:
        texto = bruto.decode("latin-1")
    linhas = texto.splitlines()
    if len(linhas) < 4:
        raise ValueError(f"{caminho}: curto demais para ser uma curva do IDL")
    try:
        normalizacao = float(linhas[1].split("=")[-1])
    except ValueError:
        raise ValueError(f"{caminho}: 2a linha nao tem o valor de normalizacao: {linhas[1]!r}")
    dados = []
    for n, linha in enumerate(linhas[3:], start=4):
        campos = linha.split()
        if not campos:
            continue
        if len(campos) != 3:
            raise ValueError(f"{caminho}, linha {n}: esperava 3 numeros, achei {linha!r}")
        try:
            dados.append(tuple(float(c) for c in campos))
        except ValueError:
            raise ValueError(f"{caminho}, linha {n}: valor nao numerico em {linha!r}")
    if not dados:
        raise ValueError(f"{caminho}: nenhuma linha de dados")
    return linhas[0].strip(), normalizacao, dados


def main():
    if len(sys.argv) < 4 or sys.argv[1] in ("-h", "--help"):
        sys.exit(__doc__)
    entradas, saida = sys.argv[1:-1], sys.argv[-1]
    if saida in entradas:
        sys.exit(f"erro: a saida {saida} e tambem um dos arquivos de entrada; escolha outro nome")

    curvas = []
    for caminho in entradas:
        try:
            curvas.append((caminho, *le_curva_idl(caminho)))
        except (OSError, ValueError) as erro:
            sys.exit(f"erro: {erro}")

    ref_nome, _, _, ref_dados = curvas[0]
    ref_energias = [d[0] for d in ref_dados]
    for nome, _, _, dados in curvas[1:]:
        energias = [d[0] for d in dados]
        if energias != ref_energias:
            so_ref = sorted(set(ref_energias) - set(energias))
            so_este = sorted(set(energias) - set(ref_energias))
            sys.exit(f"erro: {nome} nao tem as mesmas energias de {ref_nome}; nada foi gravado\n"
                     f"  so em {ref_nome}: {so_ref[:10] or '-'}\n  so em {nome}: {so_este[:10] or '-'}"
                     + ("\n  (mesmas energias, ordem diferente)" if not so_ref and not so_este else ""))

    n = len(curvas)
    media = []
    for k, e in enumerate(ref_energias):
        # Media das suavizadas, e nao suavizar a media: da o mesmo resultado no meio da curva,
        # mas na ultima linha a suavizada do IDL inclui a energia que ele nao grava, e so a
        # media preserva essa informacao.
        media.append((e, sum(c[3][k][1] for c in curvas) / n, sum(c[3][k][2] for c in curvas) / n))

    # O IDL normaliza pelo maximo incluindo a energia seguinte, que ele nao grava. Ela sai da
    # ultima suavizada: s_ult = (I_penult + I_ult + I_seguinte) / 3.
    if len(media) >= 2:
        seguinte = 3 * media[-1][2] - media[-2][1] - media[-1][1]
        normalizacao = max(max(m[1] for m in media), seguinte)
    else:
        normalizacao = max(m[1] for m in media)

    experimentos = []
    for c in curvas:
        if c[1] not in experimentos:
            experimentos.append(c[1])
    with open(saida, "w", encoding="utf-8") as f:
        f.write(" + ".join(experimentos) + f" (media de {n})\n")
        # Mesmo layout do printf do IDL: energia em 22 colunas, numeros com 8 algarismos significativos.
        f.write(f"Valor de normalização={normalizacao:#16.8g}\n")
        f.write("energia  intensidade intensidade - smoothing\n")
        for e, i, s in media:
            f.write(f"{int(e) if e == int(e) else e:22}{i:#16.8g}{s:#16.8g}\n")

    print(f"media de {n} curvas, {len(media)} energias ({ref_energias[0]:g} a {ref_energias[-1]:g} eV)")
    for c in curvas:
        print(f"  {c[0]}  (normalizacao {c[2]:g})")
    print(f"gravado: {saida}  (normalizacao {normalizacao:g})")


if __name__ == "__main__":
    main()
