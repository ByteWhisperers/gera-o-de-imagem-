# Armadilhas do PhotoCraft 0.7.0

O que dá errado sem aviso (ou com uma mensagem que não diz o que fazer), achado nos testes de
11/10/2026. "**O acabar.py cuida**" = o script já recusa ou resolve; nos testes por sessão em
Python você mesmo tem de cuidar. Erro novo: acrescente aqui, com a mensagem exata e a saída.

## Gerais

1. **Filtro inteligente que some do PSD.** `doc.save` devolve em `warnings`:
   `layer "mascote": smart filter filter.sharpen.smartSharpen was not written to PSD: this filter has no PSD equivalent`.
   Vale para `smartSharpen`, `sharpen`, `sharpenMore`, `sharpenEdges`, `reduceNoise`,
   `dustAndScratches`, `lensBlur`, `blurGallery.irisBlur`/`tiltShift`/`fieldBlur`,
   `render.relight`, `render.lightingEffects`. Ao reabrir parece certo (pixels guardados), mas na
   primeira edição de outro filtro do objeto ele é refeito sem esse e o efeito some.
   **Saída:** `unsharpMask`, `highPass`, `median`, `gaussianBlur`, `cameraRaw` (todos voltam), ou o
   filtro numa cópia de pixels. **O acabar.py cuida** (para com o aviso).
2. **Converter em objeto inteligente troca o id da camada** (mesmo nome). **O acabar.py cuida**
   (mantém o nome, não prende, não renomeia). Na sessão em Python, pegue o id de novo pelo nome.
3. **Retoque não roda em objeto inteligente:**
   `command \`edit.contentAwareFill\` is not available right now: active layer is a Smart Object layer, not a pixel layer`
   (o mesmo para `paint.spotHealing`, `paint.remove`, `edit.fill`, `image.adjustments.matchColor`).
   **Saída:** retoque antes de converter, ou numa camada de pixels nova.
4. **Comandos que ignoram `"layer"` e agem na camada ativa:** `edit.fill`, `image.adjustments.*`,
   `paint.gradient`, `layer.layerMask.enabled`, `layer.layerMask.apply`. Sem erro: o `levels` "na
   cópia" escureceu a cena original. **Saída:** selecione a camada certa (`alvo` na receita).
   **O acabar.py cuida** (recusa `layer` diferente do selecionado).
5. **Modo de mesclagem só em inglês:** `unknown blend mode \`Luminosidade\`` / `\`Sobrepor\`` /
   `\`Add\``. Use `Luminosity`, `Overlay`, `Soft Light`, `Screen`, `Multiply`, `Linear Dodge (Add)`.
6. **Opacidade de 0 a 1** no `layer.setProps`: `{"opacity": 60}` não dá erro e vira 100%. Nos
   estilos de camada é de 0 a 100. **O acabar.py cuida** em `props` (recusa > 1).
7. **O comando que cria camada ignora `blend`, `opacity`, `name` e `clipped`** sem avisar
   (`vibrance {"vibrance": 10, "blend": "Luminosity"}` cria em Normal). **Saída:** `props`, `nome`
   e `prender` na receita.
8. **Valores fora da faixa passam calados** (curva `[[0,0],[300,255]]` vira identidade, `inBlack`
   maior que `inWhite` é aceito). Erros que aparecem: curva com 1 ponto (`points must be an array
   of 2..=19 [input, output] pairs in 0..255`), `midtones must be an array of 3 numbers`,
   `stops must be an array of 2..=64`, `unknown filter \`aquecimento\``,
   `amount must be a number in 1..500`, `radius must be a number in 0.1..1000`,
   `unknown parameter \`remove\`` (o `smartSharpen` só tem `amount`, `radius`, `reduceNoise`).
   **Saída:** confira o resultado (`pc.camadas()`: `adjustment`, `smartFilters`) depois de criar.
9. **`select.deselect` sem seleção dá erro:** `command \`select.deselect\` is not available right now: no selection`.
   Consomem a seleção: `layer.layerMask.hideSelection`, `select.refineEdge` com saída em máscara
   ou camada. **O acabar.py cuida** (pula o `deselect`).
10. **Seleção ativa vira máscara do próximo filtro ou ajuste.** Termine o bloco com
    `select.deselect`.
11. **Não existe `select.ellipse`**: use `select.rect` com `"ellipse": true`.
12. **Comandos de arquivo são desligados na automação:** `file.placeEmbedded`,
    `layer.smartObjects.updateModifiedContent` (`uses ambient filesystem paths and is disabled`).
    **Saída:** abrir o PNG como segundo documento (`doc.open`, depois `doc.select {"index": 0}`) e
    `select.loadSelection {"channel": "red", "document": 1}`; na receita, `selecao_do_grafo` e
    `mascara_do_grafo`. Depois do segundo `doc.open` o documento ativo é o novo.
13. **Ao reabrir, objeto inteligente aparece como `"smartSource": {"kind": "linked", ...}`.** Continua
    embutido no PSD. Nada a fazer.
14. **psd-tools imprime `Failed to read CurvesExtraMarker`** em todo PSD com Curvas. Os pontos são
    lidos; é só ruído.

## Pilha e medida

15. **O passo de depois fica embaixo.** Cada camada nova nasce logo acima da selecionada: a que
    for criada por último fica colada na parte e age primeiro. Remendo criado antes de uma luz
    presa fica **por cima** dela e sem a luz: use `alvo` com o remendo.
16. **Prender a camada de baixo de tudo** (`createClippingMask` na cena) não dá erro. Prenda só
    camada nova (`prender`).
17. **Nome repetido**: a receita, a sessão e a medida pegam a camada **visível de cima** com
    aquele nome. Se a receita parar no meio, podem sobrar duas.
18. **Receita com camada que a peça não tem** (passo em `frente` num PSD da ficha v1.1).
    **O acabar.py cuida** (recusa antes de medir).
19. **Medida de peça fora do lugar da referência**: a região de uma parte inclui o que está por
    cima dela na peça; o `acabar.py` tira as camadas da ficha que cobrem (frente, mascote, texto),
    mas confira olhando. Brilho externo cai fora do contorno e mexe no perfil da cena.
20. **Cor mexe na régua de nitidez.** Contraste sobe a nitidez medida; Níveis com preto de saída
    alto baixa. Faça a cor antes da nitidez e meça de novo.
21. **Juntar receitas boas sozinhas pode passar do ponto**: na B, Níveis do entorno + brilho
    interno + Filtro de Fotos deixaram as moedas chapadas (+28% de luz, -63% de contraste). Cada
    especialista mede **sobre o PSD do anterior**.

## Recorte

22. **Não dá para mirar a máscara com filtro:** `channel.target {"channel": "mask"}` ->
    `channel must be "composite", a colour channel name or an alpha channel`. Pior: um filtro
    "na máscara" depois de `fromTransparency` mexe nos pixels sem erro. **Saída:** carregar como
    seleção -> `select.saveSelection {"name": "recorte"}` -> `channel.target {"channel": "recorte"}`
    -> Níveis/filtro -> `channel.target {"channel": "composite"}` -> `select.loadSelection
    {"channel": "recorte"}` -> (`layer.layerMask.delete`) -> `layer.layerMask.revealSelection` ->
    `select.deselect` -> `channel.delete`.
23. **Revelar/Esconder seleção substituem a máscara** (não somam). Monte tudo no canal e revele uma vez.
24. **`refineEdge` com `decontaminate: true` ignora `"output": "layerMask"`**: cria "mascote copy" e
    esconde o original. **O acabar.py cuida** (recusa). Descontamine com
    `layer.matting.colorDecontaminate` à parte.
25. **Difusão/Densidade ao vivo e máscara vetorial** o PhotoCraft desenha, mas o psd-tools e a
    medida ignoram. **O acabar.py cuida** (recusa). Suavize a seleção e revele.
26. **`fromTransparency` + amaciar mostra o que estava escondido** (na A, a imagem gerada inteira:
    franja clara +6).
27. **Selecionar Assunto / Remover Fundo numa camada opaca pegam o retângulo todo** (IoU 0,38)
    sem erro. Só com fundo liso.
28. **`borda_opaca` engana**: parte que cobre a peça inteira dá 0, e 1 px de contração zera o
    número com o corte reto ainda lá. Olhe `quadro_%` e a imagem.
29. **ΔE não pega a frente que enche o quadro na peça do loop** (o fundo da img2img parece com a
    referência). Só `quadro_%` e a imagem mostram.
30. **Os cinzas do Intervalo de Cores também comem branco** (avião de papel, brilho). Baixe a
    tolerância para 50 ou tire `#a3acb3` da lista.
31. **As partes da A têm alfa 254**, não 255. Não aparece.
32. **`removeBlackMatte` / `removeWhiteMatte` pioram** a franja do rembg (não é fundo
    pré-multiplicado). Não use.

## Cor

33. **`casar_cor` em parte que não é a mesma coisa da referência dá degrau** (moedas soltas x ícone
    do Telegram: borda verde-azulada, contraste +29%). A inclinação agora fica entre 0,5 e 2; mesmo
    assim prefira Níveis em Luminosidade + Filtro de Fotos + Vibração, ou `forca` <= 0,5.
34. **Não rode `casar_cor` duas vezes na mesma parte**: empilha outra correção. Para afinar, mude a
    opacidade da camada "cor ... por medida".
35. **Contraste com Níveis/Curvas em Normal também satura.** Em Luminosidade não.
36. **Combinar Cor sem seleção na referência usa a imagem inteira** (mascote +15% de luz, -19% de
    saturação).

## Retoque

37. **Halo de nitidez.** Sem máscara de filtro, USM 150/2/4 deixou 6,6% da borda com contorno
    claro; 250/1,5/3 na peça mole: contorno branco no bico e nos óculos. **Saída:** máscara de filtro
    (seleção da parte encolhida 3 px, suavizada 1,5 px), raio curto (1,0-1,2) e `cameraRaw texture`
    em vez de força alta. Confira `estouro`.
38. **Passa-alta direto na parte deixa tudo cinza.** Use numa cópia em `Overlay` presa.
39. **Preenchimento sensível ao conteúdo com amostra automática pega o lugar errado** (cinza da asa,
    vermelho do short). Use `"sampling": "custom"` com `"area": [x, y, w, h]` só no tecido limpo.
40. **`"output": "new"` cria "Content-Aware Fill 1" solta.** Use `prender` e `nome`.
41. **Carimbo: `offset` é origem menos destino** (`[0, 70]` copia de 70 px abaixo).
42. **Coordenadas de retoque são da peça.** Receita de pseudo-texto não serve em outra peça.

## Luz

43. **Sombra interna ignora `angle`** se não vier `"useGlobalLight": false`.
44. **Reflexo de lente em camada vazia não faz nada**; em preenchimento dá `not a pixel layer`.
    Cor sólida preta -> `layer.rasterize.layer` -> `lensFlare` -> Tela.
45. **Gradiente vivo (`gradient.fill.create`) fora do centro sai em outro lugar no psd-tools.** Use
    `layer.newFillLayer.gradient` ou `paint.gradient` numa camada de pixels.
46. **Cetim, `relight` e vinheta nos valores padrão são fortes demais** (cetim ΔE +3,9; vinheta 70%
    ΔE do entorno +15). Comece com opacidade baixa.
47. **Desfocar a frente inteira piora** (a referência é mais nítida que a peça). Só a faixa mais perto.
48. **Brilho interno amacia** o que acende (nitidez do entorno 1,63 -> 1,25).
49. **O degradê de `layer.newFillLayer.gradient` cobre o documento inteiro, não a parte.** Com a
    parte fora do centro (o mascote da B fica à direita), ela cai quase toda do lado claro e o
    "volume" clareia a parte inteira (luz do mascote 35,7 -> 39,0 em Luz Suave 40%). **Saída:**
    camada nova presa + `paint.gradient` com `from`/`to` nos cantos da parte e `stops` claro /
    `#808080` / escuro, em Sobrepor (comandos testados). As coordenadas são da peça.
50. **O brilho externo de uma parte de baixo piora a franja da parte de cima.** A régua de recorte
    só esconde os estilos da própria parte. Na B, o brilho das moedas atrás do mascote, por baixo
    da beirada meio transparente dele, levou a franja do mascote de -2,73 para -3,29, sem contorno
    escuro visível (o brilho do próprio mascote cobre). Mudar o tamanho ou a opacidade do brilho
    quase não muda nada (-3,13). **Saída:** depois de pôr o brilho, meça a franja das partes de
    cima. O conserto de verdade é de recorte (a beirada escura do mascote); quem ilumina pode
    aliviar a camada presa à parte de cima que escurece a beirada (o volume com escuro
    `#505050` em vez de `#1e1e1e` deu -2,96).
