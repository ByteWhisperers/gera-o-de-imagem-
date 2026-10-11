---
name: photocraft-retoque
description: Retoque e nitidez no PhotoCraft - devolver o detalhe de parte mole com Máscara de Nitidez como filtro inteligente sem halo, tirar pseudo-texto, manchas e ruído que a IA deixou. Skill do agente retocador; use quando o diagnóstico do acabamento acusar (retoque) ou houver letra falsa ou mancha na peça.
---

# Retoque e nitidez no PhotoCraft

Base: skill `photocraft` (regras, formato da receita, réguas, pilha). Comandos com parâmetros
exatos: `photocraft/referencia/comandos-testados.md`, seção "Retoque e nitidez". Armadilhas 1 a
3, 10, 15, 20 e 37 a 42 de `photocraft/referencia/armadilhas.md`.

## Quando é com você

- Frases com `(retoque)`: parte menos nítida (ou mais) que a referência; a nitidez estourou.
- O que só se vê olhando: letras falsas que a IA desenhou (camisa, placa), risquinhos, manchas.
  Nenhuma régua acha isso: olhe a peça e diga ao diretor.

Você trabalha depois do colorista (contraste mexe na régua de nitidez) e antes do iluminador.

## Nitidez

O padrão é **Máscara de Nitidez como filtro inteligente com máscara de filtro**, por parte:

```json
{"camada": "mascote", "comando": "layer.smartObjects.convertToSmartObject", "params": {}},
{"camada": "mascote", "comando": "select.loadSelection", "params": {"channel": "transparency", "layer": "mascote"}},
{"camada": "mascote", "comando": "select.modify.contract", "params": {"radius": 3}},
{"camada": "mascote", "comando": "select.modify.feather", "params": {"radius": 1.5}},
{"camada": "mascote", "comando": "filter.sharpen.unsharpMask", "params": {"amount": 100, "radius": 1.5, "threshold": 3}},
{"camada": "mascote", "comando": "select.deselect", "params": {}}
```

A seleção encolhida vira a máscara do filtro: a borda não ganha halo. A cena enche o quadro:
sem máscara.

| peça | valores de partida | resultado |
|---|---|---|
| loop (nitidez ~40% abaixo) | mascote e entorno 100/1,5/3, frente 60/1,5/3, cena 50/1,5/3. Receita `loop-nitidez.json` | A: mascote 1,85 -> 3,02 (ref 3,04), entorno 2,66 -> 4,40 (4,44), ΔE da peça +0,09, estouro 0,05% |
| nova e mole (SD-Turbo, ~50% abaixo) | mascote 120/1,0/2 + `filter.cameraRaw {"texture": 40}`, entorno 100/1,2/3, cena 200/1,5/4. Receita `nova-nitidez.json` | B: mascote 1,66 -> 2,65 (ref 3,78). Mais que isso faz contorno branco no bico e nos óculos |

- Raio curto (1,0 a 1,5) e limiar 2 a 4. Para parte muito mole, `cameraRaw texture` dá detalhe
  médio sem contorno; força alta dá halo.
- Só filtros que voltam do PSD: `unsharpMask`, `highPass` (cópia em Overlay), `cameraRaw`,
  `median`. Nada de `smartSharpen`, `reduceNoise` (o `acabar.py` para).
- Passa-alta: duplicar com `nome`, converter a cópia, `highPass {"radius": 3}` com `alvo` na
  cópia, `props {"blend": "Overlay"}`, presa. Fácil de dosar pela opacidade, mas sobe o ΔE o dobro.
- Se toda peça do mesmo gerador sai tão mole, diga ao diretor: é caso de mudar a geração.

## Pseudo-texto, manchas, ruído

Retoque só roda em **camada de pixels**: faça antes de converter a parte em objeto inteligente.

| caso | o que fazer |
|---|---|
| letras falsas, risco, mancha média | seleção (`select.lasso` por pontos, `select.rect`), `select.modify.expand {"radius": 3}`, `edit.contentAwareFill {"sampling": "custom", "area": [x, y, w, h] só sobre o tecido limpo, "colorAdaptation": "high", "output": "new"}` com `prender` e `nome`. Exemplo: `promo-telegram-comfyui-pseudotexto.json` |
| sem área limpa ao lado | `layer.new.layer` + `paint.remove` com `"layer": "<camada nova>", "sampleAllLayers": true` |
| pinta pequena | `paint.spotHealing {"type": "proximityMatch"}` |
| ruído | `filter.cameraRaw {"noiseLuminance": 30, "noiseColor": 25}` ou `median` como filtro inteligente |

O remendo nasce logo acima da parte, abaixo dos ajustes de cor que já estão presos: a cor vale
para ele também. Coordenadas são da peça: medir os pontos olhando a peça.

## Metas

- Nitidez de cada parte a ~10% da referência (peça mole: o que der sem estourar).
- `estouro` da parte: borda até 1%, miolo até 3%. Acima disso, olhe bico, olhos, moedas a 100%.
- ΔE da parte não sobe mais que 0,5 (o detalhe novo não cai no pixel do detalhe da referência).
- Remendo: a letra some e o tecido continua o mesmo a olho.

## Protocolo

Siga o protocolo de especialista do seu agente (`.claude/agents/retocador.md`).
