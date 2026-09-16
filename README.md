# iv_curve

Extração de curvas IV de LEED a partir das imagens da câmera: em Python e com o mouse.
Substitui o `coleta_no_step_*.pro` (IDL) e reproduz o cálculo dele exatamente.

## Programas

| arquivo | para quê |
|---|---|
| `leed_iv.py` | interface: marque o spot com 1 ou 2 cliques e salve a curva |
| `leed_iv_core.py` | cálculo: leitura das imagens, posição do spot, intensidade |
| `le_curva_idl.py` | lê o `.txt` gravado pelo IDL (tabela, CSV, gráfico); só biblioteca padrão |
| `normaliza_corrente.py` | divide uma curva do IDL pela corrente do feixe (`BeamCurrent` do `.xml`) |
| `reproduz_idl.py` | refaz em Python uma coleta do IDL a partir dos 5 pontos marcados |
| `testa_core.py` | confere o cálculo contra a curva do IDL em `dados/` |

Requisitos: `numpy`, `Pillow` e `matplotlib` com Tk. O `le_curva_idl.py` não precisa de nada.

## Uso

```bash
python3 leed_iv.py dados/jpg --xml dados/xml --emin 30 --emax 308
```

- Clique esquerdo no spot marca o centro naquela energia; clique direito apaga.
- Setas ou roda do mouse mudam a energia; clicar na curva pula para aquela energia.
- **Salvar spot** grava `spot_N.txt` (curva), `spot_N_pontos.txt` (cliques) e `spot_N.png`.
- **Novo spot** limpa os cliques e guarda o centro do padrão: a partir daí 1 clique basta.

As imagens precisam se chamar `<energia>.jpg` ou `<energia>.tiff`; o `.xml` de mesmo nome
dá a corrente do feixe.

## Como a posição do spot é achada

- **físico** (padrão): posição = centro + K/√E em cada eixo, ajustada nos cliques, e busca do
  pico a até 4 px. Nos 5 pontos marcados à mão da curva 10 o resíduo é ≤ 2 px (um ajuste
  linear erra até 24 px). Ajustado com 2 pontos, acerta os 3 que não viu a 1–4 px.
- **polinômio (IDL)**: ajuste cúbico por 4+ pontos e refinamento de ±3 px, como o
  `coleta_no_step`. Com os mesmos pontos, dá as mesmas 139 intensidades do IDL.

A intensidade é a do IDL nos dois casos: janela 15×15 (para imagens de 640 px), fundo linear
por coluna (`c`) ou por linha (`l`), soma.

## Validação (16/09/2026, curva `dados/curva_IV_idl_10.txt`)

- `reproduz_idl.py --modo c --como-idl` gera arquivo **idêntico byte a byte** ao do IDL.
  Controles: fundo `l` ou eixo y invertido dão 0/139.
- Rode `python3 testa_core.py` depois de mexer no cálculo.

## O que se descobriu sobre o programa do IDL

- **Não grava a última energia** (`for n=0, z-1`). Confirmado: a coluna suavizada do `.txt`
  implica I(308 eV) = 1055, e o Python calcula 1055.
- **Entre ~34 e 78 eV a janela cortou o spot pela metade**: o polinômio cúbico por 5 pontos
  não segue a trajetória 1/√E em energia baixa. Em 36 eV o IDL dá 9171; com a janela
  centrada, 12348. Curvas antigas do IDL subestimam essa faixa.
- Rodado como `idl arquivo.pro` (modo batch) trava no primeiro `while`; use `.r` e o nome.
- As TIFF da câmera (RGBA 1440×1080) aparecem pretas no IDL; ele espera cinza 640×480.

## Dados

`dados/jpg` são as TIFF de `Ag_poslimpeza_IV` convertidas para cinza 640×480 (média de RGB,
redução por área, JPEG qualidade 95); `dados/xml` são os parâmetros de cada imagem.
`idl/` guarda as versões do `coleta_no_step` com a correção das respostas s/n.
