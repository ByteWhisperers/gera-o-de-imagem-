# Memória do colorista

Uma linha por aprendizado: data, peça, o que fez, números. O mais novo embaixo de cada seção.
A = promo-deposito-001 (tentativa do loop). B = promo-telegram-comfyui (gerada do zero, SD-Turbo).
B2 = a mesma B depois do recortista (ac003, franja e sombra cinza já limpas).

## Por tipo de peça

- 2026-10-11, A: a cor já vem certa da img2img (luz -1%, saturação -1% no mascote); só o contraste
  cai (mascote -11%, entorno -7%, frente -7%). `casar_cor` devolve o contraste mas sobe o ΔE do
  mascote +0,4: na peça do loop use a curva de luz (`casar_luz`), ΔE +0,05.
- 2026-10-11, B: tudo lavado: saturação -20 a -24%, cena +12% de luz, entorno -22% de luz e +18% de
  contraste (parte disso era sombra cinza do recorte: peça a peça, meça depois do recortista).
- 2026-10-11, B2: limpo o recorte, o entorno já vinha com luz e saturação certas (-1%) e só
  contraste -21%; cena só saturação -33%; mascote luz +14%, saturação -19%. A receita quente
  (Níveis + warming) não serve mais no entorno: clareia e esquenta o que já está certo.

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
- 2026-10-11, B2: casar_cor na cena e no mascote + casar_luz no entorno (força 1, inclinação
  padrão): cena +0/+6/-33% -> -6/-9/-8% (ΔE 26,07 -> 24,78), mascote +14/-9/-19% -> +5/-10/+3%
  (ΔE 41,22 -> 39,68), entorno -1/-21/-1% -> -5/-5/-5% (ΔE igual 39,88), peça 32,71 -> 32,55.
  casar_luz é o certo quando só falta contraste: moedas com mais relevo, sem degrau de cor.
- 2026-10-11: testar variantes numa Sessao (A.aplicar_passos + A.medir + A.perfis, sem diário)
  dá os mesmos números do `aplicar` em ~12 s por variante (contra ~50 s). Cuidado: sem `docs`,
  casar_* olha os pixels originais; só vale com o casar_* como primeiro passo da parte.

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
- 2026-10-11, B2 cena: Vibração 50/20 sobe a saturação (-33 -> -6%) mas o ΔE sobe (+0,6);
  casar_cor acerta o matiz e baixa o ΔE (-1,3). Na cena prefira casar_cor.
- 2026-10-11, B2 mascote: Níveis gama 0,8 em Luminosidade + Vibração 40/15 acertam os números
  (-1/-7/-9%) mas ΔE 41,09 contra 39,68 do casar_cor. Brilho/Contraste 20 em Luminosidade depois
  do casar_cor: contraste -10 -> -6%, ΔE +0,47. Não vale.
- 2026-10-11, B2: inclinação (0,4; 2,5) na cena piora o ΔE (+0,34); (0,6; 1,7) baixa 0,1 a 0,2
  mas a saturação cai para -10 a -13%. Fique na padrão. Níveis gama 1,1 Lum. no entorno devolve
  a luz (-5 -> -1%) mas o contraste cai para -8%, ΔE igual: deixe a luz para o iluminador.
- 2026-10-11, B2: escurecer a cena em volta subiu o halo_fora do mascote (7,9 -> 11,2) e a
  franja (-2,1 -> -2,7, ainda dentro de ±3). Avise o recortista quando a cena escurecer.
