---
name: photocraft-luz
description: Luz, sombra e profundidade no PhotoCraft - luz de contorno dourada, brilho em volta, sombreado com direção, brilho nas moedas, sombra na cena, desfoque dos objetos mais perto, raios e reflexo. Skill do agente iluminador; use quando o diagnóstico do acabamento acusar (luz) ou a peça estiver chapada perto da referência.
---

# Luz e profundidade no PhotoCraft

Base: skill `photocraft` (regras, formato da receita, réguas, pilha). Comandos com parâmetros
exatos: `photocraft/referencia/comandos-testados.md`, seção "Luz, sombra e profundidade".
Armadilhas 1, 4, 15, 19, 21 e 43 a 48 de `photocraft/referencia/armadilhas.md`.

## Quando é com você

- Frases com `(luz)`: menos (ou mais) brilho em volta, menos (ou mais) luz de contorno que a
  referência. Régua: `bordas.<parte>.contorno` (`brilho_fora`, `luz_borda`, `lados`) na peça e
  na referência.
- Peça chapada: sem volume no mascote, moedas sem brilho, cena sem sombra nas bordas.

Nas referências da Arara a luz de contorno vem **de cima e da direita**, é dourada, e há um
brilho em volta do mascote e das moedas. Você é o último da equipe.

## Que ferramenta usar

| falta | o que fazer | valores de partida |
|---|---|---|
| luz de contorno no mascote | `layer.layerStyle.replace` com `innerShadow` em Tela como luz (`angle` 45, `useGlobalLight: false`) | sutil (loop): distância 6, tamanho 10, opacidade 30. Forte (peça nova): 8, 12, 60 |
| brilho em volta | `outerGlow` no mesmo `replace`, `#ffb52e`, Tela, `softer` | sutil: tamanho 8, opacidade 35. Forte: 15, 60 |
| volume no mascote | `layer.newFillLayer.gradient` presa, `#a07040` -> preto, ângulo 225, `props {"blend": "Soft Light"}` | se houver remendo preso, use `alvo` com o remendo |
| moedas apagadas | `innerGlow` (`source: center`, tamanho 30, opacidade 50) ou cor sólida `#ffc040` presa em Tela 0,45 | amacia a nitidez: confira |
| cena clara nas bordas | gradiente radial branco -> `#2a1a10` preso à cena, `Multiply` 0,4 | |
| profundidade | objeto inteligente + seleção da faixa mais perto (`select.rect` com `feather` 40) + `gaussianBlur {"radius": 3}` | só onde a referência desfoca |
| esquivar e queimar | camada transparente presa em Soft Light + `paint.stroke` claro/escuro | coordenadas da peça |
| raios, reflexo, bloom | ver comandos testados; meça: costumam subir o ΔE | |

Regras de mão:
- Estilos (`outerGlow`, `innerShadow`, `innerGlow`) são não destrutivos e voltam editáveis, mas
  outro editor que recompõe o PSD não os desenha (a prévia gravada desenha).
- Comece com opacidade baixa: cetim, `relight` e vinheta padrão são fortes demais.
- Desfoque só com `gaussianBlur` (`lensBlur` e galeria de desfoque não voltam do PSD).
- O brilho externo cai fora do contorno e conta como cena no perfil: olhe a régua de contorno.
- Receitas: `loop-contorno-sutil.json` (loop), `nova-luz-e-sombra.json` (peça nova; medida sozinha,
  passou do ponto quando somada à cor quente: meça sobre o PSD do colorista).

## Metas

- `brilho_fora` e `luz_borda` a ~3 de luz da referência; `lados` com o mais claro do mesmo lado
  que na referência.
- ΔE da peça não sobe mais que 0,5 (loop) ou cai (peça nova).
- A olho: brilho dourado discreto, nada de auréola branca, sem lavar o mascote.

Números de referência: A com o contorno sutil: brilho em volta -3,2 -> +0,1 (ref +0,3), luz de
borda 10,1 -> 12,9 (ref 12,1), ΔE da peça 7,88 -> 7,85. B com luz e sombra completas: ΔE da peça
32,74 -> 31,44.

## Protocolo

Siga o protocolo de especialista do seu agente (`.claude/agents/iluminador.md`).
