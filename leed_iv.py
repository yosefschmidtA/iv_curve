#!/usr/bin/env python3
"""Coleta de curvas IV de LEED com o mouse.

    python3 leed_iv.py dados/jpg --xml dados/xml
    python3 leed_iv.py /pasta/com/tiffs              (xml na mesma pasta)

Na janela:
  clique esquerdo na imagem   marca o centro do spot nesta energia
  clique direito na imagem    apaga o ponto marcado nesta energia
  <- / ->  (ou roda do mouse) muda de energia
  clique no grafico da curva  pula para aquela energia
  Salvar spot                 grava spot_N.txt, spot_N_pontos.txt e spot_N.png
  Novo spot                   limpa os pontos; o centro do padrao fica, e 1 clique basta

Com o metodo "fisico" bastam 2 cliques em energias bem separadas (ex.: uma baixa e uma
alta). Depois do primeiro spot salvo, o centro do padrao ja e conhecido e 1 clique basta.
Use "polinomio" com 4+ pontos para calcular exatamente como o coleta_no_step do IDL.
"""
import argparse
from pathlib import Path

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.widgets import Button, CheckButtons, RadioButtons, Slider

import leed_iv_core as core

CORES_SPOTS = ["tab:orange", "tab:purple", "tab:brown", "tab:pink", "tab:olive", "tab:cyan"]


class Coleta:
    def __init__(self, pasta, pasta_xml=None, saida=None, emin=None, emax=None, largura=None):
        self.imagens = {e: p for e, p in core.lista_imagens(pasta).items()
                        if (emin is None or e >= emin) and (emax is None or e <= emax)}
        if not self.imagens:
            raise SystemExit(f"nenhuma imagem com nome <energia>.jpg/.tif em {pasta}")
        self.energias = list(self.imagens)
        self.saida = Path(saida) if saida else Path(pasta)
        pasta_xml = Path(pasta_xml) if pasta_xml else Path(pasta)
        self.xml = {e: core.le_xml(pasta_xml / f"{e}.xml") for e in self.energias}
        self.tem_corrente = all(v["BeamCurrent"] for v in self.xml.values())

        ny, nx = core.carrega_cinza(self.imagens[self.energias[0]]).shape
        # 15 px era o padrao do IDL para imagens de 640 px; escala junto com a resolucao.
        self.largura = largura or (int(round(15 * nx / 640)) | 1)
        self.forma = (ny, nx)

        self.ancoras = {}
        self.metodo = "fisico"
        self.fundo = "c"
        self.normalizar = self.tem_corrente
        self.centro = None
        self.pos, self.inten = {}, {}
        self.salvos = []  # (nome, energias, curva normalizada) dos spots ja gravados
        self.mensagem = ""
        self.i = 0

        self._monta_janela()
        self.recalcula()
        self.desenha()

    # ---------------------------------------------------------------- calculo
    def recalcula(self):
        self.pos, self.inten = {}, {}
        if not self.ancoras:
            self.mensagem = "Clique no centro do spot que quer medir."
            return
        if self.metodo == "polinomio" and len(self.ancoras) < 4:
            self.mensagem = f"Polinomio (como o IDL) precisa de 4 pontos ou mais; ha {len(self.ancoras)}."
            return
        if self.metodo == "fisico" and len(self.ancoras) == 1 and self.centro is None:
            self.mensagem = "Marque o mesmo spot em outra energia, bem distante desta."
            return
        try:
            self.pos = core.trajetoria(self.imagens, self.ancoras, self.metodo, self.largura,
                                       centro=self.centro)
        except ValueError as erro:
            self.mensagem = str(erro)
            return
        self.inten = core.curva(self.imagens, self.pos, self.fundo, self.largura)
        self.mensagem = (f"{len(self.ancoras)} ponto(s) marcado(s). Confira o quadrado verde "
                         "percorrendo as energias; se escapar do spot, clique nele ali.")

    def curva_plot(self):
        es = np.array(self.energias)
        y = np.array([self.inten[e] for e in es], dtype=float)
        if self.normalizar and self.tem_corrente:
            y = y / np.array([self.xml[e]["BeamCurrent"] for e in es])
        return es, y

    # ---------------------------------------------------------------- janela
    def _monta_janela(self):
        self.fig = plt.figure(figsize=(14, 8))
        try:
            self.fig.canvas.manager.set_window_title("Curvas IV - LEED")
        except AttributeError:
            pass
        self.ax_img = self.fig.add_axes([0.02, 0.20, 0.50, 0.74])
        self.ax_zoom = self.fig.add_axes([0.56, 0.60, 0.17, 0.34])
        self.ax_info = self.fig.add_axes([0.75, 0.60, 0.24, 0.34])
        self.ax_curva = self.fig.add_axes([0.58, 0.20, 0.40, 0.33])
        self.ax_info.axis("off")

        img0 = core.carrega_cinza(self.imagens[self.energias[0]])
        self.h_img = self.ax_img.imshow(img0, cmap="gray", interpolation="nearest")
        self.ax_img.set_xticks([]), self.ax_img.set_yticks([])
        self.h_traj, = self.ax_img.plot([], [], "-", color="cyan", lw=0.8, alpha=0.6)
        self.h_anc, = self.ax_img.plot([], [], "x", color="yellow", ms=8, mew=2)
        self.h_quad = Rectangle((0, 0), 1, 1, fill=False, color="lime", lw=1.5, visible=False)
        self.ax_img.add_patch(self.h_quad)

        self.h_zoom = self.ax_zoom.imshow(np.zeros((41, 41)), cmap="gray", interpolation="nearest")
        self.ax_zoom.set_xticks([]), self.ax_zoom.set_yticks([])
        self.ax_zoom.set_title("zoom", fontsize=9)
        self.h_zquad = Rectangle((0, 0), 1, 1, fill=False, color="lime", lw=1.5, visible=False)
        self.ax_zoom.add_patch(self.h_zquad)
        self.h_info = self.ax_info.text(0, 1, "", va="top", family="monospace", fontsize=9)

        e = self.energias
        self.sl = Slider(self.fig.add_axes([0.08, 0.12, 0.40, 0.03]), "Energia (eV)",
                         e[0], e[-1], valinit=e[0], valstep=np.array(e))
        self.sl.on_changed(self._slider)

        self.fig.text(0.575, 0.145, "fundo", fontsize=9)
        self.rb_fundo = RadioButtons(self.fig.add_axes([0.575, 0.02, 0.09, 0.12]),
                                     ["c (coluna)", "l (linha)"])
        self.rb_fundo.on_clicked(self._fundo)
        self.fig.text(0.675, 0.145, "posicao do spot", fontsize=9)
        self.rb_metodo = RadioButtons(self.fig.add_axes([0.675, 0.02, 0.12, 0.12]),
                                      ["fisico (1-2 cliques)", "polinomio (IDL)"])
        self.rb_metodo.on_clicked(self._metodo)
        self.ck = CheckButtons(self.fig.add_axes([0.08, 0.02, 0.20, 0.06]),
                               ["dividir pela corrente do feixe"], [self.normalizar])
        self.ck.on_clicked(self._normaliza)
        if not self.tem_corrente:
            self.ck.ax.set_visible(False)

        self.bt_limpa = Button(self.fig.add_axes([0.81, 0.10, 0.08, 0.05]), "Limpar pontos")
        self.bt_limpa.on_clicked(lambda _: self._limpa())
        self.bt_novo = Button(self.fig.add_axes([0.90, 0.10, 0.08, 0.05]), "Novo spot")
        self.bt_novo.on_clicked(lambda _: self._novo())
        self.bt_salva = Button(self.fig.add_axes([0.81, 0.03, 0.17, 0.05]), "Salvar spot",
                               color="#b8e0b8", hovercolor="#8fd18f")
        self.bt_salva.on_clicked(lambda _: self.salva())

        self.fig.canvas.mpl_connect("button_press_event", self._clique)
        self.fig.canvas.mpl_connect("key_press_event", self._tecla)
        self.fig.canvas.mpl_connect("scroll_event", self._roda)

    def desenha(self):
        e = self.energias[self.i]
        img = core.carrega_cinza(self.imagens[e])
        self.h_img.set_data(img)
        # Contraste so da tela (como o tvscl): nao mexe nos numeros da curva.
        self.h_img.set_clim(np.percentile(img, 1), max(np.percentile(img, 99.8), 1))
        self.ax_img.set_title(f"{e} eV", fontsize=12)

        if self.ancoras:
            ea = [a for a in self.ancoras if a == e]
            self.h_anc.set_data([self.ancoras[a][0] for a in ea], [self.ancoras[a][1] for a in ea])
        else:
            self.h_anc.set_data([], [])
        if self.pos:
            self.h_traj.set_data([self.pos[k][0] for k in self.energias], [self.pos[k][1] for k in self.energias])
        else:
            self.h_traj.set_data([], [])

        meio = self.largura / 2
        centro = self.pos.get(e) or self.ancoras.get(e)
        if centro:
            c, l = core.round_idl(centro[0]), core.round_idl(centro[1])
            self.h_quad.set_xy((c - meio, l - meio))
            self.h_quad.set_width(self.largura), self.h_quad.set_height(self.largura)
            self.h_quad.set_visible(True)
            z = 20 + self.largura // 2
            pad = np.pad(img, z, mode="constant")
            crop = pad[l:l + 2 * z + 1, c:c + 2 * z + 1]
            self.h_zoom.set_data(crop)
            self.h_zoom.set_extent((-0.5, crop.shape[1] - 0.5, crop.shape[0] - 0.5, -0.5))
            self.h_zoom.set_clim(crop.min(), max(crop.max(), crop.min() + 1))
            self.h_zquad.set_xy((z - meio, z - meio))
            self.h_zquad.set_width(self.largura), self.h_zquad.set_height(self.largura)
            self.h_zquad.set_visible(True)
        else:
            self.h_quad.set_visible(False), self.h_zquad.set_visible(False)

        x = self.xml[e]
        linhas = [f"energia     {e} eV" + (f"  (xml {x['Energy']})" if x["Energy"] else "")]
        if x["BeamCurrent"]:
            linhas.append(f"corrente    {x['BeamCurrent']} uA")
        if centro:
            linhas.append(f"posicao     col {core.round_idl(centro[0])}  lin {core.round_idl(centro[1])}")
        if e in self.inten:
            linhas.append(f"intensidade {self.inten[e]}")
        linhas += ["", f"pontos marcados: {len(self.ancoras)}"]
        linhas += [f"  {a} eV: ({self.ancoras[a][0]:.0f}, {self.ancoras[a][1]:.0f})" for a in sorted(self.ancoras)]
        linhas += ["", f"janela {self.largura}x{self.largura} px"]
        if self.centro is not None:
            linhas.append(f"centro do padrao ({self.centro[0]:.0f}, {self.centro[1]:.0f})")
        linhas += ["", *self._quebra(self.mensagem, 38)]
        self.h_info.set_text("\n".join(linhas))

        ax = self.ax_curva
        ax.clear()
        for k, (nome, es_s, y_s) in enumerate(self.salvos):
            ax.plot(es_s, y_s / y_s.max(), color=CORES_SPOTS[k % len(CORES_SPOTS)], lw=1, alpha=0.5, label=nome)
        if self.inten:
            es, y = self.curva_plot()
            ax.plot(es, y / y.max(), color="black", lw=1.2, label="spot atual")
            ax.plot([a for a in self.ancoras], [y[self.energias.index(a)] / y.max() for a in self.ancoras],
                    "x", color="goldenrod", mew=2)
        ax.axvline(e, color="red", lw=0.8)
        ax.set_xlabel("energia (eV)")
        ax.set_ylabel("intensidade" + (" / corrente" if self.normalizar and self.tem_corrente else "") + " (norm.)")
        ax.set_xlim(self.energias[0], self.energias[-1])
        if self.salvos or self.inten:
            ax.legend(fontsize=8, loc="upper right")
        self.fig.canvas.draw_idle()

    @staticmethod
    def _quebra(texto, n):
        linhas, atual = [], ""
        for palavra in texto.split():
            if len(atual) + len(palavra) + 1 > n:
                linhas.append(atual)
                atual = palavra
            else:
                atual = f"{atual} {palavra}".strip()
        return linhas + ([atual] if atual else [])

    # ---------------------------------------------------------------- eventos
    def vai_para(self, i):
        self.i = int(np.clip(i, 0, len(self.energias) - 1))
        if self.sl.val != self.energias[self.i]:
            self.sl.set_val(self.energias[self.i])  # chama _slider, que desenha
        else:
            self.desenha()

    def _slider(self, val):
        self.i = self.energias.index(int(round(val)))
        self.desenha()

    def _clique(self, ev):
        if ev.inaxes is self.ax_img and ev.xdata is not None:
            e = self.energias[self.i]
            if ev.button == 1:
                img = core.carrega_cinza(self.imagens[e])
                # O clique a mao erra 1-2 px; puxa para o pico mais proximo se houver um claro.
                c, l, _ = core.pico_local(img, ev.xdata, ev.ydata, raio=3)
                self.ancoras[e] = (float(core.round_idl(c)), float(core.round_idl(l)))
            elif ev.button == 3:
                self.ancoras.pop(e, None)
            self.recalcula()
            self.desenha()
        elif ev.inaxes is self.ax_curva and ev.xdata is not None:
            self.vai_para(int(np.argmin(np.abs(np.array(self.energias) - ev.xdata))))

    def _tecla(self, ev):
        if ev.key in ("right", "up"):
            self.vai_para(self.i + 1)
        elif ev.key in ("left", "down"):
            self.vai_para(self.i - 1)
        elif ev.key in ("delete", "backspace"):
            self.ancoras.pop(self.energias[self.i], None)
            self.recalcula(), self.desenha()

    def _roda(self, ev):
        if ev.inaxes in (self.ax_img, self.ax_zoom, self.ax_curva):
            self.vai_para(self.i + (1 if ev.button == "up" else -1))

    def _fundo(self, rotulo):
        self.fundo = rotulo[0]
        self.recalcula(), self.desenha()

    def _metodo(self, rotulo):
        self.metodo = "fisico" if rotulo.startswith("fisico") else "polinomio"
        self.recalcula(), self.desenha()

    def _normaliza(self, _):
        self.normalizar = self.ck.get_status()[0]
        self.desenha()

    def _limpa(self):
        self.ancoras = {}
        self.recalcula(), self.desenha()

    def _novo(self):
        self.ancoras = {}
        self.recalcula()
        if self.centro is not None:
            self.mensagem = "Novo spot: com o centro do padrao ja conhecido, 1 clique basta."
        self.desenha()

    # ---------------------------------------------------------------- gravacao
    def salva(self):
        if not self.inten:
            self.mensagem = "Nada para salvar: marque o spot primeiro."
            self.desenha()
            return None
        n = 1
        while (self.saida / f"spot_{n}.txt").exists():
            n += 1
        nome = f"spot_{n}"
        self.saida.mkdir(parents=True, exist_ok=True)

        es = self.energias
        inten = np.array([self.inten[e] for e in es], dtype=float)
        suave = core.suaviza3(inten)
        corr = np.array([self.xml[e]["BeamCurrent"] or np.nan for e in es], dtype=float)
        por_corr = inten / corr
        norm = por_corr / np.nanmax(por_corr) if self.tem_corrente else inten / inten.max()
        norm_suave = core.suaviza3(norm)

        with open(self.saida / f"{nome}.txt", "w", encoding="utf-8") as f:
            f.write(f"# curva IV LEED - {nome}\n")
            f.write(f"# imagens: {Path(self.imagens[es[0]]).parent.resolve()}\n")
            f.write(f"# metodo de posicao: {self.metodo} | fundo: {self.fundo} | janela: {self.largura} px\n")
            f.write("# pontos marcados (energia: coluna, linha): "
                    + "; ".join(f"{a}: {self.ancoras[a][0]:.0f}, {self.ancoras[a][1]:.0f}" for a in sorted(self.ancoras)) + "\n")
            f.write("# intensidade e suavizada: mesmo calculo do coleta_no_step (IDL), sem perder a ultima energia\n")
            f.write("# normalizada = intensidade / corrente, dividida pelo maximo; normalizada_suave = media de 3 pontos\n")
            f.write("# energia energia_xml coluna linha intensidade suavizada corrente_uA intensidade_por_uA normalizada normalizada_suave\n")
            for k, e in enumerate(es):
                ex = self.xml[e]["Energy"]
                f.write(f"{e:5d} {ex if ex is not None else float('nan'):7.1f} {self.pos[e][0]:6.0f} {self.pos[e][1]:6.0f} "
                        f"{inten[k]:10.0f} {suave[k]:12.4f} {corr[k]:6.2f} {por_corr[k]:12.2f} "
                        f"{norm[k]:10.5f} {norm_suave[k]:10.5f}\n")
        with open(self.saida / f"{nome}_pontos.txt", "w", encoding="utf-8") as f:
            f.write("# pontos marcados no leed_iv.py; mesmo formato de pontos_marcados_10.txt\n")
            f.write("# energia_eV  coluna  linha\n")
            for a in sorted(self.ancoras):
                f.write(f"{a} {self.ancoras[a][0]:.0f} {self.ancoras[a][1]:.0f}\n")
        self._figura_resumo(nome, norm)

        if self.metodo == "fisico" and len(self.ancoras) >= 2:
            cc, _, cl, _ = core.ajusta_fisico(self.ancoras)
            self.centro = (cc, cl)
        self.salvos.append((nome, np.array(es), norm))
        self.mensagem = f"Gravado {nome}.txt em {self.saida}. 'Novo spot' para medir outro."
        self.desenha()
        return self.saida / f"{nome}.txt"

    def _figura_resumo(self, nome, norm):
        fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.5))
        e0 = min(self.ancoras)
        a1.imshow(core.carrega_cinza(self.imagens[e0]), cmap="gray")
        a1.plot([self.pos[e][0] for e in self.energias], [self.pos[e][1] for e in self.energias], "c-", lw=1)
        a1.plot([self.ancoras[a][0] for a in self.ancoras], [self.ancoras[a][1] for a in self.ancoras], "yx", mew=2)
        a1.set_title(f"{nome}: trajetoria sobre {e0} eV"), a1.set_xticks([]), a1.set_yticks([])
        a2.plot(self.energias, norm, "k-", lw=1)
        a2.set_xlabel("energia (eV)"), a2.set_ylabel("intensidade normalizada")
        a2.set_title(f"metodo {self.metodo}, fundo {self.fundo}")
        fig.tight_layout()
        fig.savefig(self.saida / f"{nome}.png", dpi=120)
        plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pasta", help="pasta com as imagens <energia>.jpg ou <energia>.tiff")
    ap.add_argument("--xml", help="pasta com os <energia>.xml (padrao: a mesma das imagens)")
    ap.add_argument("--saida", help="onde gravar os spots (padrao: a pasta das imagens)")
    ap.add_argument("--emin", type=int), ap.add_argument("--emax", type=int)
    ap.add_argument("--largura", type=int, help="lado da janela do spot em px (padrao: 15 para 640 px)")
    ap.add_argument("--pontos", help="arquivo de pontos (energia coluna linha) para ja abrir marcado")
    args = ap.parse_args()

    app = Coleta(args.pasta, args.xml, args.saida, args.emin, args.emax, args.largura)
    if args.pontos:
        dados = np.atleast_2d(np.loadtxt(args.pontos, comments="#"))
        app.ancoras = {int(e): (float(c), float(l)) for e, c, l in dados if int(e) in app.imagens}
        app.recalcula(), app.desenha()
    plt.show()


if __name__ == "__main__":
    main()
