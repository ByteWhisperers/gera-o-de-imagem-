# Memória do iluminador

Uma linha por aprendizado: data, peça, o que fez, números. O mais novo embaixo de cada seção.
A = promo-deposito-001 (tentativa do loop). B = promo-telegram-comfyui (gerada do zero, SD-Turbo).
B equipe = a B passando por recortista -> colorista -> retocador -> iluminador (PSD do retocador, ac001).

## Por tipo de peça

- 2026-10-11: nas duas referências a luz de contorno vem de cima e da direita e é dourada, com
  brilho em volta do mascote e das moedas.
- 2026-10-11, A: falta pouco (brilho em volta do mascote -3,2 x ref +0,3; luz de borda 10,1 x 12,1).
- 2026-10-11, B: falta tudo (brilho em volta -3,4 x ref +5,3; luz de borda 1,8 x 6,6; lado direito
  27 x 49). Moedas apagadas (luz do entorno 51 x 66).
- 2026-10-11: na referência quase tudo é mais nítido que as peças; só os objetos mais perto (faixa
  de baixo) são desfocados. Desfocar a frente inteira piora (ΔE +0,45).
- 2026-10-11, B equipe: chegou com moedas sem brilho (brilho em volta -1,7 x ref +11,2; luz de borda
  -8,8 x +0,4) e mascote com a luz do lado errado (esq 38,7 / dir 22,8 / cima 33,2 x ref 35,2 /
  49,2 / 56,8). A luz do mascote inteiro já batia (35,7): só contorno e direção.

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
- 2026-10-11, B equipe: moedas com brilho externo #ffb52e 20/62 + sombra interna #ffe08a em
  Sobrepor (ângulo 45, 4/6/100): brilho em volta -1,7 -> +11,2 (ref +11,2), luz de borda -8,8 -> -1,7
  (+0,4), contraste 21,2 -> 19,8 (21,8), nitidez 1,78 -> 1,72 (1,70); a cena ganha luz 30,6 -> 32,5 (32,5).
- 2026-10-11, B equipe: mascote com brilho 15/46 + luz #ffd27a Tela ângulo 30 (8/12/30) + sombra
  #2a1408 Multiplicação ângulo 210 (6/10/30) no mesmo `replace` + volume (`paint.gradient` numa camada
  presa acima das curvas, de (1584,200) a (1113,700), #ffe6b0/#808080/#505050, Sobrepor 60%): brilho
  em volta +4,4 (4,4), borda 8,0 (6,6), lados 38,5/38,8/42,9 (mesma ordem da ref), nitidez 3,20 ->
  3,70 (3,78), luz 35,7 -> 36,9. ΔE da peça 32,52 -> 32,16. Receita na pasta da equipe (iluminador-2).
- 2026-10-11, B equipe: varrer variantes por sessão (render + `B.contorno` + `A.perfis` + franja com
  `renders_sem_partes`, ~15 s cada) antes do `aplicar`: 2 tentativas bastaram.

## O que não funcionou

- 2026-10-11, A: cetim (ΔE do mascote +3,9), vinheta 70% (ΔE do entorno +15), chanfro e sombra
  interna escura (escurecem a borda, contra a referência), sombra projetada (a referência não tem).
- 2026-10-11, B: raios de luz pela cena (ΔE +0,5: a cena já é mais clara que a referência; escureça
  antes). `relight` direto destrói a parte (luz 40 -> 70).
- 2026-10-11, B: o gradiente de sombreado criado com o mascote selecionado ficou **abaixo** do
  remendo do pseudo-texto: a camisa remendada ficou sem sombra. Use `alvo` com o remendo.
- 2026-10-11, B: somado à cor quente do colorista, o brilho interno nas moedas passou do ponto
  (+28% de luz, -63% de contraste, moedas chapadas). Meça sobre o PSD do colorista.
- 2026-10-11, B equipe: `newFillLayer.gradient` cobre o documento todo; com o mascote à direita o
  volume clareou a parte inteira (luz 35,7 -> 39,0). Use `paint.gradient` com início e fim na parte.
- 2026-10-11, B equipe: volume em Luz Suave tira contraste do mascote (23,6 -> 23,1, passa de -10%);
  em Sobrepor sobe (24,2). Luz de borda das moedas em Tela tira contraste (19,3); em Sobrepor, 20,1.
- 2026-10-11, B equipe: o brilho das moedas atrás do mascote piorou a franja dele (-2,73 -> -3,29),
  porque a régua só tira o estilo do mascote. Mudar tamanho ou opacidade do brilho não resolve
  (-3,13). Resolveu aliviar o escuro do volume (#1e1e1e -> #505050): -2,96.
