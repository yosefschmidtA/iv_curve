#!/usr/bin/env python3
"""Le a curva IV gravada pelo coleta_no_step_*.pro (IDL) e mostra os dados.

Uso:
    python3 le_curva_idl.py arquivo.txt                  tabela e resumo na tela
    python3 le_curva_idl.py arquivo.txt --grafico        abre o grafico (precisa de matplotlib)
    python3 le_curva_idl.py arquivo.txt --csv saida.csv  grava em CSV (abre no Excel/Origin)

Formato do IDL: 1a linha = nome do experimento; 2a = "Valor de normalizacao= <max>";
3a = cabecalho; depois, por linha: energia, intensidade, intensidade suavizada.
Atencao: esse programa do IDL nao grava a ultima energia da varredura.
"""
import argparse
import csv
import sys


def le_curva_idl(caminho):
    """Devolve (experimento, valor_normalizacao, energias, intensidades, suavizadas)."""
    with open(caminho, "rb") as f:
        bruto = f.read()
    # O acento de "normalizacao" sai em UTF-8 ou Latin-1 conforme a maquina que rodou o IDL.
    try:
        texto = bruto.decode("utf-8")
    except UnicodeDecodeError:
        texto = bruto.decode("latin-1")
    linhas = texto.splitlines()
    if len(linhas) < 4:
        raise ValueError(f"{caminho}: curto demais para ser uma curva do IDL ({len(linhas)} linhas)")

    experimento = linhas[0].strip()
    try:
        normalizacao = float(linhas[1].split("=")[-1])
    except ValueError:
        raise ValueError(f"{caminho}: 2a linha nao tem o valor de normalizacao: {linhas[1]!r}")

    energias, intensidades, suavizadas = [], [], []
    for n, linha in enumerate(linhas[3:], start=4):
        campos = linha.split()
        if not campos:
            continue
        if len(campos) != 3:
            raise ValueError(f"{caminho}, linha {n}: esperava 3 numeros, achei {linha!r}")
        try:
            e, i, s = (float(c) for c in campos)
        except ValueError:
            raise ValueError(f"{caminho}, linha {n}: valor nao numerico em {linha!r}")
        energias.append(e)
        intensidades.append(i)
        suavizadas.append(s)
    if not energias:
        raise ValueError(f"{caminho}: nenhuma linha de dados")
    return experimento, normalizacao, energias, intensidades, suavizadas


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("arquivo")
    ap.add_argument("--grafico", action="store_true", help="mostra intensidade x energia")
    ap.add_argument("--csv", metavar="SAIDA", help="grava os dados num CSV")
    ap.add_argument("--sem-tabela", action="store_true", help="so o resumo, sem listar as linhas")
    args = ap.parse_args()

    try:
        exp, norm, E, I, S = le_curva_idl(args.arquivo)
    except (OSError, ValueError) as erro:
        sys.exit(f"erro: {erro}")

    passos = sorted({round(b - a, 6) for a, b in zip(E, E[1:])})
    k_max = max(range(len(I)), key=I.__getitem__)
    print(f"experimento:            {exp}")
    print(f"valor de normalizacao:  {norm:g}")
    print(f"pontos:                 {len(E)}  ({E[0]:g} a {E[-1]:g} eV, passo {', '.join(f'{p:g}' for p in passos)} eV)")
    print(f"intensidade maxima:     {I[k_max]:g} em {E[k_max]:g} eV")
    if max(I) != norm:
        # Normal: o IDL calcula o maximo com a ultima energia, que ele nao grava.
        print(f"  (o maximo gravado difere do valor de normalizacao; o maximo esta na energia que o IDL nao gravou)")

    if not args.sem_tabela:
        print()
        print(f"{'energia':>8} {'intensidade':>12} {'suavizada':>12} {'normalizada':>12}")
        for e, i, s in zip(E, I, S):
            print(f"{e:8g} {i:12.1f} {s:12.2f} {i / norm:12.5f}")

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["energia_eV", "intensidade", "suavizada", "normalizada"])
            for e, i, s in zip(E, I, S):
                w.writerow([e, i, s, i / norm])
        print(f"\nCSV gravado: {args.csv}")

    if args.grafico:
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            sys.exit("para o grafico instale o matplotlib:  pip install matplotlib")
        plt.plot(E, [i / norm for i in I], ".", color="gray", ms=4, label="intensidade")
        plt.plot(E, [s / norm for s in S], "-", color="black", lw=1.2, label="suavizada")
        plt.xlabel("Energia (eV)")
        plt.ylabel("Intensidade normalizada")
        plt.title(exp)
        plt.legend()
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    main()
