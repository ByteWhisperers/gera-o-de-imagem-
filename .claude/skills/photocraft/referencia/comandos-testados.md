# Comandos testados no PhotoCraft 0.7.0

Tudo rodou neste projeto em 11/10/2026, pelo `photocraft-cli serve` (via
`integracoes/photocraft/sessao.py`), nas peças A = `saida/arara/tentativas/promo-deposito-001/peca.psd`
(tentativa do loop, partes no lugar da referência) e B = `saida/arara/promo-telegram-comfyui.psd`
(gerada do zero no SD-Turbo, recortada por rembg; grafo `fichas/arara/grafos/promo-telegram.json`).
Peça de 1867 x 842 px. "PSD ok" = salvo, reaberto no PhotoCraft, editável e com o mesmo render.
"psd-tools" = se a recomposição camada a camada do psd-tools desenha (outros editores como o GIMP
fazem igual). Na receita do `acabar.py`, `"layer"` vai pelo **nome**; aqui aparece como `<id>`.

Os números "x -> y" são a régua do `acabar.py` (perfil ou bordas) naquela peça. Comando que não
está aqui: procure em `catalogo.md` e teste antes numa pasta sua.

## Apoio (camadas, seleção, canais)

| comando | parâmetros | nota |
|---|---|---|
| `layer.select` | `{"layer": <id>}` | o `acabar.py` faz em todo passo |
| `layer.setProps` | `{"layer": <id>, "name": "...", "blend": "Luminosity", "opacity": 0.6, "visible": true}` | modo em inglês (`Luminosity`, `Soft Light`, `Screen`, `Multiply`, `Overlay`, `Linear Dodge (Add)`, `Color Dodge`, `Lighten`; minúsculas e camelCase valem). Opacidade de 0 a 1 |
| `layer.createClippingMask` | `{"layer": <id>}` | prende à camada de baixo (`prender` faz isso) |
| `layer.duplicate` | `{"layer": <id>}` | cria "<nome> copy" acima e a deixa selecionada |
| `layer.delete` | `{"layer": <id>}` | |
| `layer.new.layer` | `{"name": "..."}` | camada de pixels vazia acima da selecionada |
| `layer.rasterize.layer` / `.smartObject` | `{"layer": <id>}` | preenchimento ou objeto vira pixels (mesmo id); filtros inteligentes viram pixels |
| `layer.smartObjects.convertToSmartObject` | `{}` ou `{"layer": <id>}` | **id novo, mesmo nome**; leva a máscara para dentro; o que está preso fica preso. 0,2-0,5 s |
| `layer.smartObjects.editContents` | `{"layer": <id>}` | abre o conteúdo como outro documento |
| `select.loadSelection` | `{"channel": "transparency", "layer": <id>}` / `{"channel": "mask", "layer": <id>}` / `{"channel": "recorte"}` / `{"channel": "red", "document": 1}` | da forma da camada, da máscara, de um canal alfa salvo, ou do canal de outro documento aberto. `"operation": "intersect"`/`"add"`/`"subtract"` |
| `select.saveSelection` | `{"name": "recorte"}` / `{"channel": "recorte", "operation": "intersect"}` | guarda num canal alfa (use o nome: o PSD já traz "Alpha 1") |
| `select.rect` | `{"x": 0, "y": 760, "width": 1867, "height": 120, "feather": 40}`; `"ellipse": true` para elipse; `"mode": "add"` | não existe `select.ellipse` |
| `select.lasso` | `{"points": [[x,y],...], "mode": "replace", "feather": 0}` | laço por pontos |
| `select.modify.contract` / `expand` / `feather` / `smooth` / `border` | `{"radius": 3}` | encolher, alargar, suavizar, arredondar, só a faixa |
| `select.inverse`, `select.all`, `select.deselect` | `{}` | `deselect` sem seleção dá erro (o `acabar.py` pula) |
| `channel.target` | `{"channel": "recorte"}` / `{"channel": "composite"}` | para Níveis, filtro e pintura agirem num canal alfa |
| `channel.delete` | `{"channel": "recorte"}` | |
| `doc.open` + `doc.select {"index": 0}` | | segundo documento (PNG de máscara) dentro da raiz de leitura. É o que `selecao_do_grafo` faz |

## Recorte e máscara (recortista)

| comando | parâmetros | o que fez | PSD |
|---|---|---|---|
| `layer.layerMask.revealSelection` | `{"layer": <id>}` | máscara = seleção atual; **substitui** a que existir | ok, psd-tools ok |
| `layer.layerMask.hideSelection` | `{"layer": <id>}` | máscara = inverso; substitui e **consome a seleção** | ok |
| `layer.layerMask.delete` / `revealAll` / `linked` | `{"layer": <id>}` | | ok |
| `layer.layerMask.enabled` / `apply` | `{"layer": <id>, "enabled": false}` | olham a camada **ativa** | ok |
| `layer.layerMask.fromTransparency` | `{"layer": <id>}` | alfa vai para a máscara e os pixels ficam opacos: aparece o que estava escondido (na A a imagem gerada inteira) | ok, mas evite |
| Níveis no canal | `channel.target {"channel": "recorte"}` + `image.adjustments.levels {"inBlack": 64, "inWhite": 192}` | aperta a máscara: alfa < 25% some, > 75% fica cheio. B mascote: névoa 13,4% -> 2,1% | pixels do canal |
| `filter.other.minimum` no canal | `{"radius": 1}` | contrai a máscara 1 px (tira o contorno escuro fino) | |
| `filter.noise.median` no canal | `{"radius": 2}` | tira pontinhos soltos da máscara | |
| `filter.blur.gaussianBlur` no canal | `{"radius": 0.7}` | amacia a borda da máscara | |
| `paint.gradient` no canal | `{"from": [0, 722], "to": [0, 692], "colors": ["#000000", "#ffffff"], "mode": "multiply"}` | esmaece a máscara até um corte reto (coordenadas da peça) | |
| `select.colorRange` | `{"colors": ["#0a0b0d", ..., "#a3acb3"], "fuzziness": 90, "invert": true, "sampleAllLayers": false}` | seleciona o que não é cinza: tira a sombra de estúdio que o rembg levou (B entorno: 94% do cinza sai, 99% do colorido fica) | |
| `select.colorRange` (fundo liso) | `{"color": "#bcbcb8", "fuzziness": 30, "invert": true}` | objeto sobre fundo liso: IoU 1,0 | |
| `layer.removeBackground` | `{"layer": <id>}` | objeto sobre fundo **liso**: IoU 1,0 em 0,3 s. Com cena atrás pega o retângulo todo (0,38) | ok |
| `select.subject` / `select.object {"rect": [x,y,w,h]}` / `select.magicWand` / `select.quick` / `select.focusArea` | | fundo liso: 0,999-1,0. Cena atrás: 0,04-0,46 (não servem) | |
| máscara do grafo | passo `{"mascara_do_grafo": {}}` | peça do loop com parte enchendo o quadro: IoU 1,0 | ok |
| `layer.matting.colorDecontaminate` | `{"amount": 50, "radius": 2}` (mascote), `{"amount": 100, "radius": 2}` (entorno) | tira a cor do fundo antigo da beirada. **Só depois** de apertar a névoa (sozinho pinta a névoa) | pixels |
| `select.refineEdge` | `{"radius": 2, "smooth": 10, "contrast": 30, "shiftEdge": -20, "output": "layerMask"}` | B mascote: halo_fora 20,7 -> 8,9, névoa 13,4% -> 2,0%, área -2,6%. Consome a seleção | ok |
| `layer.matting.defringe` | `{"width": 1..3}` | quase nada | pixels |
| `layer.matting.removeBlackMatte` / `removeWhiteMatte` | `{}` | **não use**: troca a franja por névoa colorida ou por franja do outro tom | pixels |

## Cor (colorista)

Todos com a parte selecionada, presos (`prender`), medidos no mascote da A (antes: ΔE 9,33;
luz -1%, contraste -11%, saturação -1%).

| comando | parâmetros | o que fez | psd-tools |
|---|---|---|---|
| `casar_luz` (passo medido) | `{"forca": 1.0}` | Curvas de luz por quantis em Luminosidade: contraste -11% -> -4%, cor igual, ΔE +0,05. **O melhor para peça do loop** | não |
| `casar_cor` (passo medido) | `{"forca": 1.0}` | B cena e mascote ótimos (dentro de 8%); B entorno pior (moedas x ícone); A: ΔE +0,4 | não |
| `layer.newAdjustmentLayer.curves` | `{"points": [[0,0],[64,56],[192,200],[255,255]]}`; por canal `{"red": [...], "blue": [...]}` | S de contraste; esquentar | não |
| `layer.newAdjustmentLayer.levels` | `{"inBlack": 12, "gamma": 1.0, "inWhite": 240}`; `{"gamma": 1.5, "outBlack": 40}`; por canal `{"red": {"inBlack":0,"gamma":1.1,"inWhite":255,"outBlack":0,"outWhite":255}}` | em Normal o contraste também satura (+6%); em Luminosidade não | sim |
| `layer.newAdjustmentLayer.hueSaturation` | `{"saturation": 10, "reds": {"hue": 0, "saturation": 15, "lightness": 0, "range": [315,345,15,45]}}` | saturação +6% | sim |
| `layer.newAdjustmentLayer.vibrance` | `{"vibrance": 50, "saturation": 25}` | sobe a saturação do que está apagado; quase nada no que já é saturado | não |
| `layer.newAdjustmentLayer.photoFilter` | `{"filter": "warming85", "density": 50, "preserveLuminosity": true}` | ouro mais quente (moedas da B) | não |
| `layer.newAdjustmentLayer.colorBalance` | `{"shadows": [0,0,-5], "midtones": [5,0,-5], "highlights": [0,0,5], "preserveLuminosity": true}` | esquenta os meios-tons | não |
| `layer.newAdjustmentLayer.selectiveColor` | `{"method": "relative", "reds": [-10,5,5,0], "yellows": [0,0,10,0], "blacks": [0,0,0,10]}` | vermelhos quentes, pretos fundos | não |
| `layer.newAdjustmentLayer.gradientMap` + `props {"blend": "Soft Light", "opacity": 0.2}` | `{"stops": [[0,"#1b0b33"],[1,"#fff1c4"]]}` | "look" com corpo | não |
| `layer.newAdjustmentLayer.brightnessContrast` | `{"brightness": 0, "contrast": 25}` | contraste -11% -> -7% | sim |
| `layer.newAdjustmentLayer.exposure` | `{"exposure": 0.3, "offset": 0, "gamma": 1.0}` | forte demais (ΔE +0,54) | sim |
| `layer.setAdjustment` | `{"layer": <id>, "vibrance": 35}` | edita um ajuste que já existe; só os campos passados mudam | — |
| `image.adjustments.matchColor` | `{"source": 1, "luminance": 100, "intensity": 100, "fade": 0, "useSelectionInSource": true}` | Combinar Cor com a referência aberta como documento 1. **Destrutivo**, não aceita objeto inteligente, não cabe em receita; `casar_cor` é o padrão | — |

Opacidade = força: `casar_cor` força 1 com opacidade 0,6 dá o mesmo que força 0,6. Para afinar
depois, mude a opacidade da camada.

## Retoque e nitidez (retocador)

Filtros como **filtro inteligente**: a parte vira objeto inteligente e o filtro fica editável.
Nitidez medida no mascote da A (1,85; ref 3,04).

| comando | parâmetros | o que fez | volta do PSD |
|---|---|---|---|
| `filter.sharpen.unsharpMask` | `{"amount": 100, "radius": 1.5, "threshold": 3}` com máscara de filtro | 1,85 -> 3,02, halo na borda 0,05% | **sim**, editável |
| `filter.other.highPass` | `{"radius": 3}` numa cópia em `Overlay` presa | 1,85 -> 2,82; sobe o ΔE o dobro do USM | sim |
| `filter.cameraRaw` | `{"texture": 40}`; `{"sharpenAmount": 60, "sharpenRadius": 1, "sharpenDetail": 25, "sharpenMasking": 20}`; ruído `{"noiseLuminance": 30, "noiseLuminanceDetail": 50, "noiseColor": 25}` | textura = detalhe médio sem contorno forte (bom em parte mole) | sim |
| `filter.noise.median` | `{"radius": 2}` | alisa | sim |
| máscara de filtro | `select.loadSelection {"channel": "transparency", "layer": <parte>}` + `select.modify.contract {"radius": 3}` + `select.modify.feather {"radius": 1.5}` antes do filtro, `select.deselect` depois | a seleção ativa vira a máscara do filtro: borda sem halo (7,5 -> 0,9 de luz na faixa de 3 px) | sim (não aparece no `doc.inspect`) |
| `layer.smartFilter.setParams` | `{"layer": <id>, "index": 0, "params": {"amount": 100}}` | edita o filtro (index 0 = o primeiro aplicado) | — |
| `layer.smartFilter.setVisible` / `blendingOptions` / `move` / `delete` / `disableFilterMask` / `disableSmartFilters` | `{"layer": <id>, "index": 0, "visible": false}`, `{"opacity": 0.5}` | | — |
| `layer.smartFilter.blendingOptions` | `{"layer": "mascote", "blend": "darken"}` logo depois de um 2º USM 200/0,8/2 (sem `index` = o filtro de cima) | nitidez que só escurece: sem contorno claro. Mascote da B 1,75 -> 3,20 com USM 120/1,0/2 + textura 40 antes, estouro 0,11/2,55%. Acima de 200/0,8 faz linha escura grossa | **sim** (reaberto e refeito: igual) |
| `filter.sharpen.smartSharpen`, `sharpen`, `sharpenMore`, `sharpenEdges`, `filter.noise.reduceNoise`, `dustAndScratches` | | **não voltam do PSD** como filtro inteligente (o `acabar.py` para). Equivalentes: Sharpen = USM 60/0,5/0, More = 150/0,6/0, Edges = 100/0,8/6 | não |
| `edit.contentAwareFill` | `{"sampling": "custom", "area": [x, y, w, h], "colorAdaptation": "high", "output": "new"}` com seleção | **o melhor** para pseudo-texto: remendo numa camada nova (use `prender` e `nome`). Amostra automática pega o lugar errado | sim |
| `paint.remove` | `{"points": [[x,y],...], "size": 30, "hardness": 80, "closeLoops": true}`; numa camada nova com `"layer": <nova>, "sampleAllLayers": true` | bom; na camada nova é não destrutivo | sim |
| `paint.spotHealing` | `{"points": [[x,y]], "size": 20, "type": "proximityMatch"}` | pinta pequena; ruim para texto grande | sim |
| `paint.cloneStamp` | `{"points": [[x,y]], "size": 20, "hardness": 50, "source": [x, y]}` (ou `"offset": [dx, dy]` = origem menos destino) | precisa de área limpa para copiar | sim |
| `paint.healingBrush` / `paint.patch` | `{"points": [...], "size": 20, "source": [x, y]}` / `{"offset": [0, -60], "mode": "source", "contentAware": true}` | aceitos | sim |
| `paint.sharpen` | `{"points": [...], "size": 120, "strength": 50}` | pincel de nitidez local, destrutivo | sim |

Retoque (`contentAwareFill`, `paint.*`, `edit.fill`) só funciona em camada de pixels: faça antes de
converter em objeto inteligente, ou numa camada nova.

## Luz, sombra e profundidade (iluminador)

Estilos de camada (não mexem nos pixels; vão ao PSD e voltam editáveis; o psd-tools **não**
desenha):

| comando | parâmetros | o que fez |
|---|---|---|
| `layer.layerStyle.replace` | `{"layer": <id>, "effects": [{"kind": "outerGlow", "params": {...}}, {"kind": "innerShadow", "params": {...}}]}` | troca a lista inteira de efeitos (é o jeito de editar) |
| `layer.layerStyle.outerGlow` | `{"color": "#ffb52e", "opacity": 35, "blend": "screen", "technique": "softer", "spread": 0, "size": 8, "range": 50}` | brilho dourado em volta. A: brilho em volta -3,2 -> +0,1 (ref +0,3). B (tamanho 15, opacidade 60): -3,4 -> +6,1 (ref +5,3) |
| `layer.layerStyle.innerShadow` como luz | `{"color": "#ffd27a", "opacity": 30, "blend": "screen", "angle": 45, "useGlobalLight": false, "distance": 6, "choke": 0, "size": 10}` | **luz de contorno com direção** (de cima e da direita, como nas referências). Sem `useGlobalLight: false` o ângulo é ignorado |
| `layer.layerStyle.innerGlow` | `{"color": "#ffc040", "opacity": 50, "blend": "screen", "technique": "softer", "source": "center", "choke": 0, "size": 30}` | moedas acesas por dentro (B entorno: luz 51 -> 63, ΔE -5,7), mas amacia a nitidez |
| `innerShadow` como luz em **Sobrepor** | `{"color": "#ffe08a", "opacity": 100, "blend": "overlay", "angle": 45, "useGlobalLight": false, "distance": 4, "choke": 0, "size": 6}` | acende a beirada das moedas sem tirar o contraste. B pela equipe (com brilho externo 20/62): luz de borda do entorno -8,8 -> -1,7 (ref +0,4), contraste 21,2 -> 19,8; em Tela o mesmo dá 19,3 (-11%) |
| dois `innerShadow` no mesmo `replace` | luz `{"color": "#ffd27a", "blend": "screen", "angle": 30, "distance": 8, "size": 12, "opacity": 30}` + sombra `{"color": "#2a1408", "blend": "multiply", "angle": 210, "distance": 6, "size": 10, "opacity": 30}`, os dois com `"useGlobalLight": false` | luz de um lado e sombra fraca do outro: os lados do mascote ficam na ordem da referência (B: esq 38,7 / dir 22,8 / cima 33,2 -> 38,5 / 38,8 / 42,9). Os dois voltam do PSD |
| `layer.layerStyle.dropShadow` | `{"color": "#000000", "opacity": 50, "blend": "multiply", "angle": 120, "useGlobalLight": true, "distance": 12, "size": 20}` | sombra atrás; a referência não tem |
| `layer.layerStyle.gradientOverlay` | `{"from": "#ffe08a", "to": "#000000", "style": "radial", "angle": 90, "scale": 120, "opacity": 30, "blend": "softLight"}` | único estilo que o psd-tools desenha |
| `layer.layerStyle.globalLight` | `{"angle": 45, "altitude": 30}` | luz global do documento inteiro |
| `layer.layerStyle.clear` / `layer.setEffectsVisible` | `{"layer": <id>}` / `{"layer": <id>, "visible": false}` | tira ou esconde os efeitos |
| `satin`, `bevelEmboss`, `innerShadow` escuro | | pioraram (lava ou escurece a borda) |

Camadas de luz (não destrutivas, o psd-tools desenha):

| comando | parâmetros | o que fez |
|---|---|---|
| `layer.newFillLayer.gradient` presa + `props {"blend": "Soft Light"}` | `{"from": "#a07040", "to": "#000000", "angle": 225, "style": "linear", "reverse": false}` | sombreado com direção: B mascote ΔE 41,2 -> 38,4, saturação 35 -> 40 |
| `layer.newFillLayer.gradient` presa à cena + `props {"blend": "Multiply", "opacity": 0.4}` | `{"from": "#ffffff", "to": "#2a1a10", "angle": 0, "style": "radial"}` | escurece a cena pelas bordas |
| `layer.newFillLayer.solidColor` presa + `props {"blend": "Screen", "opacity": 0.45}` | `{"color": "#ffc040"}` | moedas mais claras e douradas (B entorno ΔE -5,3) |
| volume só na parte: `layer.new.layer` presa (`alvo` = a camada de cima do grupo da parte, `props {"blend": "Overlay", "opacity": 0.6}`) + `paint.gradient` com `alvo` nela | `{"from": [1584, 200], "to": [1113, 700], "style": "linear", "stops": [[0, "#ffe6b0"], [0.5, "#808080"], [1, "#505050"]]}` (coordenadas da peça: canto de cima à direita e de baixo à esquerda do mascote) | cinza no meio = neutro, então a luz da parte quase não muda. B pela equipe: nitidez do mascote 3,20 -> 3,70, contraste 23,6 -> 23,9, luz 35,7 -> 36,9, ΔE do mascote -0,7. Em Luz Suave o contraste cai (23,1). Volta do PSD; o psd-tools desenha |
| camada transparente em Luz Suave + `paint.stroke` | `{"layer": <id>, "points": [...], "size": 90, "hardness": 0, "opacity": 0.6, "flow": 0.5, "color": "#ffe6a0"}` e preto do lado da sombra | esquivar e queimar sem cinza 50%; coordenadas da peça |
| `paint.dodge` / `paint.burn` | `{"layer": <id>, "points": [...], "size": 120, "range": "midtones", "exposure": 40}` | |
| bloom | `layer.duplicate` + (com `alvo` na cópia) `image.adjustments.levels {"inBlack": 150}` + `filter.blur.gaussianBlur {"radius": 6}` + `props {"blend": "Linear Dodge (Add)", "opacity": 0.6}` | partes claras brilham; B entorno ΔE +2,1 |
| `filter.render.lensFlare` | numa camada preta rasterizada em Tela 0,5: `{"layer": <id>, "brightness": 60, "centerX": 0.308, "centerY": 0.589, "lens": "prime105"}` | reflexo no sol; neutro no ΔE |
| `filter.blur.radialBlur` | numa cópia da cena com Níveis `inBlack` 170, em Tela: `{"amount": 80, "method": "zoom", "quality": "good", "centerX": 0.308, "centerY": 0.589}` | raios de sol; bonito, mas ΔE +0,5 se a cena já é clara. 3 s |

Profundidade (objeto inteligente + filtro inteligente):

| comando | parâmetros | o que fez | volta do PSD |
|---|---|---|---|
| `filter.blur.gaussianBlur` com seleção antes | `select.rect {"x": 0, "y": 760, "width": 1867, "height": 120, "feather": 40}` + `{"radius": 3}` | só os objetos de baixo desfocam (A frente ΔE -0,03) | **sim** |
| `filter.blur.lensBlur`, `blurGallery.irisBlur`/`tiltShift`/`fieldBlur`, `filter.render.relight`, `lightingEffects` | | | **não** (só numa cópia de pixels) |

Na referência quase tudo é **mais nítido** que as peças: só desfoque o que a referência desfoca
(os objetos mais perto, embaixo).

## Tempos

Abrir PSD 0,2-0,4 s; comando quase sempre < 0,1 s; render cheio 0,3-0,7 s; salvar PSD 0,3-0,8 s;
`radialBlur` 3 s; `acabar.py medir` ~20 s; `aplicar` 45-60 s.
