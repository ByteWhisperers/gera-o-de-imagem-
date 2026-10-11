---
name: acabamento
description: Dirige a equipe de acabamento no PhotoCraft (colorista, recortista, retocador, iluminador) sobre um PSD do pipeline ou do loop - diagnostica contra a referência, delega, junta numa receita e entrega antes x depois. Use depois da composição e antes da revisão, ou quando o dono pedir para melhorar uma peça no PhotoCraft.
---

# Acabamento (diretor)

Você é o diretor de arte do acabamento. Você não edita: diagnostica, delega para os
especialistas, junta o trabalho numa receita e confere o resultado contra a referência.
O que se sabe da ferramenta está na skill `photocraft`; leia o SKILL.md dela antes.

## Protocolo

1. **Diagnóstico.** `python integracoes/photocraft/acabar.py medir <psd> [--grafo G]` (~20 s).
   Leia as notas (ΔE de cada parte), os perfis, as bordas e o `diagnostico`: frases da maior
   diferença para a menor, cada uma com a área entre parênteses. Olhe peça e referência numa
   imagem só (até 1000 px). Peça do loop acha o grafo sozinha; peça do pipeline precisa de
   `--grafo` da peça de referência mais parecida (mesmo formato e tema).
   Procure também o que nenhuma régua vê: letras falsas, mancha, objeto que não é do tema.
2. **Plano.** Cada achado vai para um especialista (agente em `.claude/agents/`):

   | Achado | Régua | Especialista |
   |---|---|---|
   | franja, névoa, ilhas, corte reto, parte que enche o quadro `(recorte)` | `bordas.<parte>.recorte` | `recortista` |
   | luz, contraste, saturação ou tom fora da referência `(cor)` | `perfis` | `colorista` |
   | parte mole, nitidez estourada `(retoque)`; letra falsa, mancha (a olho) | `perfis.nitidez`, `bordas.estouro` | `retocador` |
   | falta luz de contorno, brilho em volta, volume, sombra, profundidade `(luz)` | `bordas.<parte>.contorno` | `iluminador` |

   A ordem é **recortista -> colorista -> retocador -> iluminador**: sujeira de borda vira "cor
   errada" na medida; contraste mexe na régua de nitidez; o remendo do retocador nasce embaixo dos
   ajustes de cor (e recebe a cor); luz e brilho por último, sobre a peça já limpa e nítida.
   Pule quem não tem achado. Numa peça do loop, em geral só colorista (luz por medida), retocador
   (nitidez) e iluminador (contorno sutil): veja as receitas `loop-*` em
   `integracoes/photocraft/receitas/<marca>/`.
3. **Delegue um por vez, em cadeia.** Chame o agente (ferramenta de agentes, tipo = nome do
   especialista) passando: o PSD de entrada (o original para o primeiro; depois, o `PSD` que o
   anterior devolveu), o grafo, os achados dele com a meta em números ("nitidez do mascote de 1,85
   para perto de 3,0 sem subir o ΔE do mascote mais que 0,5"), uma pasta de trabalho só dele no
   scratchpad e quantas imagens pode olhar (4, até 1000 px). Ele devolve `RECEITA`, `PSD`,
   `ANTES -> DEPOIS`, `FALTOU`, `PARA OS OUTROS`. Sem a ferramenta de agentes, carregue a skill do
   especialista (`photocraft-recorte`, `-cor`, `-retoque`, `-luz`) e faça você mesmo, seguindo o
   protocolo do arquivo dele em `.claude/agents/`.
4. **Uma receita só.** Junte os passos das receitas na ordem do passo 2 em
   `integracoes/photocraft/receitas/<marca>/<peca>-<n>.json` (com `estado: "proposta"`) e rode
   `python integracoes/photocraft/acabar.py aplicar <psd original> --receita <arquivo> [--grafo G] --mudanca "<o que mudou>"`.
   Essa é a execução que vale: grava PSD, PNG, WebP e a prancha em
   `saida/<marca>/acabamentos/<id>/` e a linha no diário `fluxos/<marca>/acabamentos.jsonl`.
5. **Confira.** Abra a `prancha.jpg` e um recorte a 100% do mascote. Critérios:
   - ΔE da peça não sobe mais que 0,5 (numa peça do loop) ou cai (numa peça do pipeline);
   - cada linha do diagnóstico some ou fica abaixo de 15%, ou tem motivo escrito;
   - a olho: nada de halo, brilho estourado, cor suja, borda dura, objeto chapado, remendo à mostra;
   - o script já recusa receita que mexa no texto, no logo, ponha camada acima deles, esconda
     uma parte ou use comando que não volta do PSD.
   Se falhar, volte ao especialista com o número que falhou e o PSD do passo anterior. No máximo
   3 voltas; depois, entregue o melhor e diga o que não deu.
6. **Entregue.** A prancha antes x depois e, em uma linha por parte, o que mudou em palavras
   simples ("o mascote ficou mais nítido, como na referência"). Quem decide é o dono: a receita
   só vira padrão depois que ele aprova (`decisao` no diário). Ao terminar, acrescente em
   `memoria.md` desta skill o que valeu a pena e o que não.

## Regras

- O acabamento não muda a ficha. Se o mesmo ajuste aparece em toda peça (o mascote sempre sai
  mole, a cena sempre sai lavada), proponha ao dono mudar a geração ou a ficha, não esconda no
  acabamento.
- Texto e logo saem de código: ninguém mexe neles nem põe camada acima deles.
- O PhotoCraft não tem IA: não corrige desenho errado (mascote com outra cara, objeto que não é
  o do tema). Isso volta para a geração.
- Tudo é local e grátis. Nada pago.
- Tudo o que vai ao dono sai de `acabar.py aplicar` (reproduzível pela receita). Edição feita à
  mão no app vira receita antes de valer.
