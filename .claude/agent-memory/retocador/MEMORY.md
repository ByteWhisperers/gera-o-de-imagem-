# Memória do retocador

Uma linha por aprendizado: data, peça, o que fez, números. O mais novo embaixo de cada seção.
A = promo-deposito-001 (tentativa do loop). B = promo-telegram-comfyui (gerada do zero, SD-Turbo).

## Por tipo de peça

- 2026-10-11, A: as partes saem ~40% menos nítidas que a referência (mascote 1,85 x 3,04, entorno
  2,66 x 4,44, frente 2,24 x 3,06, cena 0,91 x 1,12).
- 2026-10-11, B: mais de 50% menos nítida (mascote 1,66 x 3,78, cena 0,92 x 2,55) e mole, não
  ruidosa (Reduzir Ruído baixou a nitidez 24% e não melhorou nada). A IA escreveu letras falsas
  amarelas na camisa do mascote (x 1300-1490, y 728-806) e dois risquinhos brancos (x 1350-1390,
  y 707-726).

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

## O que não funcionou

- 2026-10-11, B mascote: USM 250/1,5/3 (3,28) e 180/1,2/3 + textura 40 (3,16) deixam contorno branco
  no bico e nos óculos (halo 4,7-5,4%). Com limiar 2 na cena o mato escuro fica áspero.
- 2026-10-11: `smartSharpen`, `reduceNoise`, `dustAndScratches` e os Sharpen simples não voltam do
  PSD como filtro inteligente (o efeito some na próxima edição).
- 2026-10-11, B: `contentAwareFill` com amostra automática e `edit.fill contentAware` pegaram cinza
  da asa e vermelho do short. `spotHealing` em grade deixa borrões em texto grande.
