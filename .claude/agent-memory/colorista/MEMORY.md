# Memória do colorista

Uma linha por aprendizado: data, peça, o que fez, números. O mais novo embaixo de cada seção.
A = promo-deposito-001 (tentativa do loop). B = promo-telegram-comfyui (gerada do zero, SD-Turbo).

## Por tipo de peça

- 2026-10-11, A: a cor já vem certa da img2img (luz -1%, saturação -1% no mascote); só o contraste
  cai (mascote -11%, entorno -7%, frente -7%). `casar_cor` devolve o contraste mas sobe o ΔE do
  mascote +0,4: na peça do loop use a curva de luz (`casar_luz`), ΔE +0,05.
- 2026-10-11, B: tudo lavado: saturação -20 a -24%, cena +12% de luz, entorno -22% de luz e +18% de
  contraste (parte disso era sombra cinza do recorte: peça a peça, meça depois do recortista).

## O que funcionou

- 2026-10-11, A: Curvas de luz por quantis presa ao mascote em Luminosidade: contraste -11% -> -4%,
  luz e saturação iguais, ΔE da peça 7,88 -> 7,89. Nas três partes (entorno, mascote, frente): ΔE da
  peça igual, entorno ΔE -0,21.
- 2026-10-11, B: `casar_cor` na cena e no mascote (força 1): cena +2/-4/-2%, mascote +4/-8/+8%
  (luz/contraste/saturação). Mascote ΔE -1,6.
- 2026-10-11, B entorno (moedas): Níveis gama 1,5 e preto de saída 40 em Luminosidade + Filtro de
  Fotos warming85 50% + Vibração 50/25: -22/+18/-24% -> -9/+10/-7%, ΔE do entorno 41,9 -> 37,7. O
  filtro quente é o que aproxima o ouro das moedas.
- 2026-10-11: opacidade da camada = força do ajuste (casar_cor 1 a 60% = força 0,6). Para afinar,
  baixe a opacidade.

## O que não funcionou

- 2026-10-11, B entorno: `casar_cor` sem limite fez degrau no azul (moedas com borda
  verde-azulada, contraste +29%, ΔE +0,6): as moedas soltas não são o ícone do Telegram da
  referência. Agora a inclinação é limitada, mas prefira Níveis + Filtro de Fotos + Vibração.
- 2026-10-11, A: Exposição +0,3 forte demais (ΔE +0,54); Níveis 12/240 em Normal satura +6%.
- 2026-10-11, B: Níveis do entorno somado ao brilho interno do iluminador deixou as moedas chapadas
  (+28% de luz, -63% de contraste). Ajuste a luz do entorno junto com o iluminador, não cada um no
  máximo.
- 2026-10-11, B: Combinar Cor com seleção empata com casar_cor no mascote, mas é destrutivo e não
  cabe em receita. Não vale.
