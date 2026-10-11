---
name: photocraft-cor
description: Cor e tom no PhotoCraft - casar luz, contraste, saturação e tom de cada parte com a referência por camadas de ajuste presas (curvas por medida, Níveis, Vibração, Filtro de Fotos). Skill do agente colorista; use quando o diagnóstico do acabamento acusar (cor).
---

# Cor no PhotoCraft

Base: skill `photocraft` (regras, formato da receita, réguas, pilha). Comandos com parâmetros
exatos: `photocraft/referencia/comandos-testados.md`, seção "Cor". Armadilhas 5 a 8, 15, 20,
21 e 33 a 36 de `photocraft/referencia/armadilhas.md`.

## Quando é com você

Frases do diagnóstico com `(cor)`: parte mais clara ou mais escura, com mais ou menos contraste,
mais ou menos saturada que a referência (10% ou mais). Você trabalha depois do recortista e
antes do retocador.

## Que ferramenta usar

Tudo é **camada de ajuste presa à parte** (`prender: true`), nunca nos pixels.

| situação | o que fazer |
|---|---|
| peça do loop: só contraste ou luz fora (cor já certa) | `{"casar_luz": {"forca": 1.0}}` na parte. Muda luz e contraste sem mexer na cor (ΔE +0,05). Receita `loop-luz-por-medida.json` |
| peça nova: luz e saturação fora, a parte é a mesma coisa da referência (cena, mascote) | `{"casar_cor": {"forca": 1.0}}` (curvas por canal, inclinação limitada) |
| a parte não é a mesma coisa da referência (moedas soltas x ícone) | Níveis em Luminosidade (`{"gamma": 1.5, "outBlack": 40}`, `props {"blend": "Luminosity"}`) + Filtro de Fotos `warming85` + Vibração. Receita `nova-cor-quente.json` |
| só saturação baixa | Vibração `{"vibrance": 25..50, "saturation": 0..25}`; Matiz/Saturação para uma faixa de cor |
| só contraste, sem mexer na cor | Curvas ou Níveis com `props {"blend": "Luminosity"}` |
| cor geral da peça | ajuste com `camada` = `brilho` (logo abaixo do texto), sem prender. Prefira por parte |
| afinar um ajuste que já existe | `layer.setProps {"layer": "<nome>", "opacity": 0.8}` ou `layer.setAdjustment {"layer": "<nome>", ...}` |

Regras de mão:
- **Opacidade é força**: comece forte e baixe a opacidade até a medida casar.
- Contraste em modo Normal também satura; use Luminosidade para não mexer na cor.
- Não rode `casar_cor` duas vezes na mesma parte.
- O último ajuste criado fica colado na parte e age primeiro (armadilha 15).
- Mais de uma mudança na mesma parte soma: meça o conjunto, não cada um sozinho (armadilha 21).

## Metas

- Luz, contraste e saturação de cada parte a ~10% da referência.
- ΔE da peça: não sobe mais que 0,5 (loop); cai (peça nova).
- A olho: sem borda de outra cor, sem moeda chapada, sem cor suja. Detalhe não pode sumir:
  se a `nitidez` da parte despencar depois do seu ajuste, você achatou o contraste.

Números de referência: A mascote contraste -11% -> -4% com `casar_luz` (ΔE +0,05). B com a
receita quente: cena +12/+4/-23% -> +2/-5/-2%, entorno -22/+18/-24% -> -9/+10/-7%,
mascote +14/-9/-20% -> +4/-8/+8% (luz/contraste/saturação), ΔE da peça igual.

## Protocolo

Siga o protocolo de especialista do seu agente (`.claude/agents/colorista.md`).
