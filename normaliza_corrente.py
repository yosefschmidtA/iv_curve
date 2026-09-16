#!/usr/bin/env python3
"""Divide a intensidade de uma curva IV do IDL pela corrente do feixe de cada imagem.

Uso:
    python3 normaliza_corrente.py dados/curva_IV_idl_10.txt dados/xml
    python3 normaliza_corrente.py dados/curva_IV_idl_10.txt dados/xml -o saida.txt
"""
import argparse
import re
import sys
from pathlib import Path


def le_curva_idl(caminho):
    energias, intensidades = [], []
    for linha in Path(caminho).read_text(encoding="latin-1").splitlines():
        campos = linha.split()
        # As 3 linhas de cabecalho do IDL nao comecam com numero.
        if len(campos) >= 2 and re.fullmatch(r"-?\d+", campos[0]):
            energias.append(int(campos[0]))
            intensidades.append(float(campos[1]))
    return energias, intensidades


def le_xml(caminho):
    # O software do LEED grava em UTF-16; lido como UTF-8 o regex nao acha nada.
    texto = Path(caminho).read_text(encoding="utf-16")
    valores = {}
    for tag in ("BeamCurrent", "Energy"):
        m = re.search(rf"<{tag}>\s*([-\d.eE+]+)\s*</{tag}>", texto)
        valores[tag] = float(m.group(1)) if m else None
    return valores


def suaviza3(v):
    # Mesma regra do IDL: smooth(x, 3, /EDGE_TRUNCATE), que repete o valor da borda.
    n = len(v)
    return [(v[max(i - 1, 0)] + v[i] + v[min(i + 1, n - 1)]) / 3 for i in range(n)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("curva", help="arquivo .txt gravado pelo coleta_no_step_*.pro")
    ap.add_argument("dir_xml", help="pasta com os <energia>.xml")
    ap.add_argument("-o", "--saida", help="padrao: <curva>_norm_corrente.txt")
    args = ap.parse_args()

    energias, intensidades = le_curva_idl(args.curva)
    if not energias:
        sys.exit(f"nenhuma linha de dados em {args.curva}")

    correntes, energias_reais, faltando = [], [], []
    for e in energias:
        xml = Path(args.dir_xml) / f"{e}.xml"
        if not xml.exists():
            faltando.append(f"{e}: sem {xml.name}")
            continue
        v = le_xml(xml)
        if not v["BeamCurrent"]:
            # Corrente zero ou ausente faria a divisao explodir ou mentir; melhor parar.
            faltando.append(f"{e}: BeamCurrent ausente ou zero")
            continue
        correntes.append(v["BeamCurrent"])
        energias_reais.append(v["Energy"])
    if faltando:
        sys.exit("nao normalizei nada, faltam dados:\n  " + "\n  ".join(faltando))

    por_corrente = [i / c for i, c in zip(intensidades, correntes)]
    maximo = max(por_corrente)
    normalizada = [x / maximo for x in por_corrente]
    suavizada = suaviza3(normalizada)

    saida = Path(args.saida) if args.saida else Path(args.curva).with_name(Path(args.curva).stem + "_norm_corrente.txt")
    with open(saida, "w", encoding="utf-8") as f:
        f.write(f"# origem: {args.curva}  |  corrente: {args.dir_xml}/<energia>.xml (BeamCurrent, uA)\n")
        f.write(f"# intensidade_por_uA = intensidade / BeamCurrent ; normalizada = intensidade_por_uA / {maximo:.4f}\n")
        f.write("# suavizada = media de 3 pontos da normalizada (igual ao smooth do IDL)\n")
        f.write("# energia_nominal energia_xml BeamCurrent_uA intensidade intensidade_por_uA normalizada suavizada\n")
        for linha in zip(energias, energias_reais, correntes, intensidades, por_corrente, normalizada, suavizada):
            e, er, c, i, p, n, s = linha
            er_txt = f"{er:.1f}" if er is not None else "nan"
            f.write(f"{e:6d} {er_txt:>7} {c:6.2f} {i:12.1f} {p:14.2f} {n:10.5f} {s:10.5f}\n")

    print(f"{len(energias)} energias ({energias[0]} a {energias[-1]} eV), corrente de {min(correntes)} a {max(correntes)} uA")
    print(f"gravado: {saida}")


if __name__ == "__main__":
    main()
