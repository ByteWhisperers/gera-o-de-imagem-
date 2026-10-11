# Memória do iluminador

Uma linha por aprendizado: data, peça, o que fez, números. O mais novo embaixo de cada seção.
A = promo-deposito-001 (tentativa do loop). B = promo-telegram-comfyui (gerada do zero, SD-Turbo).

## Por tipo de peça

- 2026-10-11: nas duas referências a luz de contorno vem de cima e da direita e é dourada, com
  brilho em volta do mascote e das moedas.
- 2026-10-11, A: falta pouco (brilho em volta do mascote -3,2 x ref +0,3; luz de borda 10,1 x 12,1).
- 2026-10-11, B: falta tudo (brilho em volta -3,4 x ref +5,3; luz de borda 1,8 x 6,6; lado direito
  27 x 49). Moedas apagadas (luz do entorno 51 x 66).
- 2026-10-11: na referência quase tudo é mais nítido que as peças; só os objetos mais perto (faixa
  de baixo) são desfocados. Desfocar a frente inteira piora (ΔE +0,45).

## O que funcionou

- 2026-10-11, A: `layer.layerStyle.replace` no mascote com brilho externo #ffb52e (tamanho 8,
  opacidade 35) + sombra interna em Tela como luz (#ffd27a, ângulo 45, `useGlobalLight: false`,
  distância 6, tamanho 10, opacidade 30): brilho em volta +0,1, luz de borda 12,9, ΔE da peça
  7,88 -> 7,85.
- 2026-10-11, A: frente em objeto inteligente, seleção y 760-880 com borda 40, gaussiano 3: ΔE da
  frente -0,03. Junto com o contorno sutil, ΔE da peça 7,84.
- 2026-10-11, B: contorno forte (brilho 15/60, sombra interna 8/12/60) + gradiente #a07040 -> preto
  ângulo 225 em Luz Suave preso ao mascote + brilho interno nas moedas + gradiente radial
  Multiplicação 40% na cena: ΔE da peça 32,74 -> 31,44, mascote 41,2 -> 38,4, entorno 41,9 -> 36,1.

## O que não funcionou

- 2026-10-11, A: cetim (ΔE do mascote +3,9), vinheta 70% (ΔE do entorno +15), chanfro e sombra
  interna escura (escurecem a borda, contra a referência), sombra projetada (a referência não tem).
- 2026-10-11, B: raios de luz pela cena (ΔE +0,5: a cena já é mais clara que a referência; escureça
  antes). `relight` direto destrói a parte (luz 40 -> 70).
- 2026-10-11, B: o gradiente de sombreado criado com o mascote selecionado ficou **abaixo** do
  remendo do pseudo-texto: a camisa remendada ficou sem sombra. Use `alvo` com o remendo.
- 2026-10-11, B: somado à cor quente do colorista, o brilho interno nas moedas passou do ponto
  (+28% de luz, -63% de contraste, moedas chapadas). Meça sobre o PSD do colorista.
