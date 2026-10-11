# Memória do retocador

Uma linha por aprendizado: data, peça, o que fez, números. O mais novo embaixo de cada seção.
A = promo-deposito-001 (tentativa do loop). B = promo-telegram-comfyui (gerada do zero, SD-Turbo).
C = promo-telegram-ac001 (a mesma B depois do recortista e do colorista; ensaio por sessão ~18 s por variante).

## Por tipo de peça

- 2026-10-11, A: as partes saem ~40% menos nítidas que a referência (mascote 1,85 x 3,04, entorno
  2,66 x 4,44, frente 2,24 x 3,06, cena 0,91 x 1,12).
- 2026-10-11, B: mais de 50% menos nítida (mascote 1,66 x 3,78, cena 0,92 x 2,55) e mole, não
  ruidosa (Reduzir Ruído baixou a nitidez 24% e não melhorou nada). A IA escreveu letras falsas
  amarelas na camisa do mascote (x 1300-1490, y 728-806) e dois risquinhos brancos (x 1350-1390,
  y 707-726).
- 2026-10-11, C: depois da cor, mascote 1,75 x 3,78, entorno 0,96 x 1,70, cena 1,0 x 2,55. O estouro
  do miolo do mascote vem quase todo do cabelo crespo (y 0-180), não do bico nem dos óculos; as
  letras escondidas embaixo do remendo também contam (estão nos pixels do mascote).

## O que funcionou

- 2026-10-11, A: USM como filtro inteligente com máscara de filtro (seleção da parte encolhida 3 px
  e suavizada 1,5 px): mascote e entorno 100/1,5/3, frente 60/1,5/3, cena 50/1,5/3 sem máscara.
  Tudo a -1 a -3% da referência, ΔE da peça +0,09, halo na borda 0,05-0,22% (sem máscara: 2-7%).
- 2026-10-11, B: Preenchimento sensível ao conteúdo com amostra só do verde
  (`"area": [1285, 690, 240, 135]`, `colorAdaptation high`, `output new`, preso): letras somem
  (amarelo 5279 -> 26 px), ΔE do mascote -0,49.
- 2026-10-11, B mascote: USM 120/1,0/2 + Camera Raw textura 40, com máscara de filtro: 1,66 -> 2,65
  (ref 3,78). Cena USM 200/1,5/4: 0,92 -> 1,88.
- 2026-10-11, A: passa-alta raio 3 numa cópia em Overlay presa funciona (mascote 1,85 -> 2,82), mas
  sobe o ΔE o dobro do USM.
- 2026-10-11, C: coordenadas do pseudo-texto da B ainda servem depois do recortista e do colorista
  (amarelo 5570 -> 26 px, tirando a ponta da estrela; o laço come 3 px da ponta, não se vê).
- 2026-10-11, C mascote: USM 120/1,0/2 + textura 40 + **2º USM 200/0,8/2 com
  `layer.smartFilter.blendingOptions {"blend": "darken"}`** (só escurece): 1,75 -> 3,20 (ref 3,78),
  estouro 0,11/2,55%, ΔE -0,25, luz 37,4 -> 35,7. O Escurecer volta do PSD (reaberto e refeito: igual).
  Máscara do filtro = mascote encolhido menos a área remendada (`select.lasso` `mode subtract`).
- 2026-10-11, C: entorno USM 160/1,2/3 + textura 40: 0,96 -> 1,78 (ref 1,70), estouro 0/0,69%, sem
  contorno nas moedas. Cena USM 250/1,5/6 (limiar 6): 1,0 -> 1,85, limpa a 100%.

## O que não funcionou

- 2026-10-11, B mascote: USM 250/1,5/3 (3,28) e 180/1,2/3 + textura 40 (3,16) deixam contorno branco
  no bico e nos óculos (halo 4,7-5,4%). Com limiar 2 na cena o mato escuro fica áspero.
- 2026-10-11: `smartSharpen`, `reduceNoise`, `dustAndScratches` e os Sharpen simples não voltam do
  PSD como filtro inteligente (o efeito some na próxima edição).
- 2026-10-11, B: `contentAwareFill` com amostra automática e `edit.fill contentAware` pegaram cinza
  da asa e vermelho do short. `spotHealing` em grade deixa borrões em texto grande.
- 2026-10-11, C mascote: passe Escurecer forte (250/1,0/2 = 3,42; 300/1,0/2 = 3,65, estouro 3,11%)
  faz linha escura grossa nos óculos e cabelo crocante. Escurecer acima de 200/0,8 não vale.
- 2026-10-11, C cena: 300/1,5/4 + textura 40 (2,47) e 320/1,5/4 (2,21) batem o número mas deixam a
  folhagem pontilhada e o contorno do morro serrilhado a 100%. Textura na cena: não.
