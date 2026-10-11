# Memória do recortista

Uma linha por aprendizado: data, peça, o que fez, números. O mais novo embaixo de cada seção.
A = promo-deposito-001 (tentativa do loop). B = promo-telegram-comfyui (gerada do zero, rembg).

## Por tipo de peça

- 2026-10-11, A: a borda já é a do grafo (camada = máscara do grafo, pixel a pixel), alfa só 0 ou
  254, franja 0, névoa 0. Suavizar 0,7 px subiu o `dE_borda` (mascote 18,8 -> 19,1); contrair 1 px
  -> 22,2. Na peça do loop não mexa no recorte.
- 2026-10-11, A: os "bolsões escuros" entre as penas do penacho são fiéis à referência (L 15 na
  peça, 18 na referência). Não limpar.
- 2026-10-11, B: o rembg deixa névoa escura no mascote (franja -14,0, névoa 13,4%, 36 ilhas) e
  sombra cinza-azulada do estúdio colada nas moedas do entorno (franja +14,3, névoa 10,5%) e
  moedas cortadas retas pela borda da imagem gerada (y=722, x=784; `borda_opaca` 0,30).

## O que funcionou

- 2026-10-11, B mascote: transparência -> canal -> Níveis 64-192 -> revelar -> Descontaminar 50/2.
  Franja -14,0 -> -1,6, névoa 13,4% -> 2,1%, ilhas 36 -> 5, área -0,8%. ΔE quase igual.
- 2026-10-11, B entorno: o mesmo com Intervalo de Cores de 9 cinzas (tolerância 90, invertido)
  cruzado no canal e Mediana 2, Descontaminar 100/2. Franja +14,3 -> +3,7, ΔE 41,9 -> 39,9, área
  -24% (era sombra). Corrigiu metade do "entorno escuro e sem cor" do diagnóstico.
- 2026-10-11, B entorno: Mínimo 1 no canal depois da Mediana tira o contorno escuro fino embaixo
  das moedas (anel -16,9 -> -9,8 de luz) ao custo de mais 5% da área. Não entrou na receita.
- 2026-10-11, frente que enche o quadro sobre fundo liso: `layer.removeBackground` (IoU 1,0, ΔE
  da peça 45,7 -> 7,9). Com cena atrás: máscara do grafo (IoU 1,0); seleções clássicas 0,04-0,46.
- 2026-10-11, B: degradê no canal até a linha do corte zera a `borda_opaca` (0,23 -> 0) mas sobe a
  névoa (4,1 -> 8,0%). Coordenadas da peça; é decisão de gosto.

## O que não funcionou

- 2026-10-11, B: `removeBlackMatte` (névoa vira névoa colorida, halo_fora 20,7 -> 35,5) e
  `removeWhiteMatte` (franja clara vira escura). `defringe` 1-3: quase nada.
- 2026-10-11, B: Descontaminar 100/4 antes de apertar a névoa pinta a névoa de vermelho (halo_fora
  20,7 -> 33,1). Sempre depois do aperto.
- 2026-10-11: `refineEdge` com `decontaminate` cria cópia e esconde o original (o acabar.py recusa).
