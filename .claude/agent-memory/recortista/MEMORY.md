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
- 2026-10-11, B (2ª rodada): receita testada `recortista-3` = casa no mascote com Descontaminar 30/2 +
  entorno com Níveis 104-152 e degradê no corte reto. Tudo na meta: mascote franja -2,1, névoa 2,1%,
  ilhas 5, área -0,8%, ΔE +0,04; entorno franja +2,8, névoa 2,9%, ilhas 0, `borda_opaca` 0, ΔE -2,0.
- 2026-10-11, B: o corte reto visível do entorno são só 3 pedaços (meia moeda em x 1689-1793 e caco em
  x 1076-1133 na linha y=722; moeda cortada em x=784, y 191-245). Os outros cortes em y=722 ficam
  atrás do mascote (x 1134-1524) mas contam na `borda_opaca` (0,10 se não esmaecer).

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
- 2026-10-11, B entorno: Níveis 104-152 no canal (no lugar de 64-192): franja +3,7 -> +1,8, névoa
  4,1 -> 1,6%, `borda_suave_%` 63 -> 42 (ainda sem serrilhado a olho). 96-160: +2,2 / 2,4%; 112-160:
  +1,6 / 2,1%; 80-176: +3,0 / 3,3%. A franja clara que sobra é o antisserrilhado da moeda clara sobre
  cena escura, espalhado por tudo (não é resto de sombra): só borda mais dura baixa.
- 2026-10-11, B entorno: degradê do corte reto com `stops` [[0,#000000],[0.25,#a0a0a0],[1,#ffffff]] em
  24 px (rápido até 63%, depois devagar), largura toda em y=722 + retângulo x 784-844, y 150-300 na
  esquerda: custa franja +1,0 e névoa +1,3 (sobre Níveis 104-152) e zera `borda_opaca`. A olho a meia
  moeda some no escuro da cena: fica bom. `paint.gradient` no canal respeita a seleção (`select.rect`).
- 2026-10-11, B mascote: Descontaminar 30/2 no lugar de 50/2 tira o falso "nitidez estourou" do
  diagnóstico (estouro da borda 1,59% -> 0,36%; quem clareava a beirada era o Descontaminar), halo_fora
  8,9 -> 7,9, franja -1,6 -> -2,1. Raio 1 dá o mesmo que raio 2.
- 2026-10-11, B: banco de ensaio por sessão (aplica os passos, salva, mede só `bordas`, ~17 s, sem
  diário) bate número a número com o `aplicar`. Bom para varrer parâmetro antes de gastar tentativa.

## O que não funcionou

- 2026-10-11, B: `removeBlackMatte` (névoa vira névoa colorida, halo_fora 20,7 -> 35,5) e
  `removeWhiteMatte` (franja clara vira escura). `defringe` 1-3: quase nada.
- 2026-10-11, B: Descontaminar 100/4 antes de apertar a névoa pinta a névoa de vermelho (halo_fora
  20,7 -> 33,1). Sempre depois do aperto.
- 2026-10-11: `refineEdge` com `decontaminate` cria cópia e esconde o original (o acabar.py recusa).
- 2026-10-11, B entorno: degradê linear de 20 px no corte reto: franja +1,8 e névoa +1,3 só nos cortes
  visíveis (moeda clara meio transparente sobre cena escura conta como franja clara); na largura toda
  a névoa sobe mais 1,0 (a parte atrás do mascote conta na névoa, não na franja). Mínimo 1 no canal
  zera a `borda_opaca` sem esmaecer nada (armadilha 28) e quase não mexe na franja (+3,7 -> +3,7).
- 2026-10-11, B entorno: Descontaminar 50/2 no entorno (no lugar de 100/2) piora a franja (+2,2 -> +2,4).
