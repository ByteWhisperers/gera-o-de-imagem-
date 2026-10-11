---
name: photocraft-recorte
description: Recorte, máscaras e bordas no PhotoCraft - tirar franja, névoa e sombra de fundo que o rembg deixou, esmaecer corte reto, refazer a máscara de parte que veio enchendo o quadro. Skill do agente recortista; use quando o diagnóstico do acabamento acusar (recorte).
---

# Recorte no PhotoCraft

Base: skill `photocraft` (regras, formato da receita, réguas, pilha). Comandos com parâmetros
exatos: `photocraft/referencia/comandos-testados.md`, seção "Recorte e máscara". Armadilhas
22 a 32 de `photocraft/referencia/armadilhas.md`.

## Quando é com você

| no diagnóstico ou nas `bordas.<parte>.recorte` | o que é |
|---|---|
| `franja` abaixo de -3 | névoa ou franja escura do fundo antigo em volta da parte |
| `franja` acima de +3 | franja clara: sombra cinza do fundo de estúdio levada junto |
| `semi_%` acima de 3 | pixels meio transparentes (névoa, fiapo) |
| `ilhas` acima de 5 | pedacinhos soltos em volta |
| `borda_opaca` acima de 0,05 | a parte foi cortada reta pela borda da imagem gerada |
| `quadro_%` de 90 ou mais (fora a cena) | a parte trouxe o fundo da imagem gerada junto |
| `anel` muito acima de `anel_ref` | cor do fundo antigo presa na beirada de dentro |

Recorte é o primeiro da equipe: sujeira de borda vira "cor errada" na medida (na B, metade do
"entorno escuro e sem cor" era sombra cinza do recorte).

## Que ferramenta usar

1. **Peça do loop (partes no lugar da referência): quase nunca mexa.** A borda já é a do grafo,
   pixel a pixel; suavizar, contrair ou limpar só sobe o `dE_borda` (0,2 a 3,5). Os "bolsões
   escuros" entre as penas são fiéis à referência.
   - Exceção: parte que enche o quadro (`quadro_%` alto) -> `{"camada": "frente", "mascara_do_grafo": {}}`.
2. **Peça nova com franja escura e névoa (rembg)**: aperto da máscara no canal (Níveis 64-192)
   e depois `colorDecontaminate` (50/2 no mascote). Receita `nova-recorte-rembg.json`, primeira metade.
3. **Peça nova com sombra cinza de estúdio no entorno**: o mesmo, cruzando antes com
   `select.colorRange` dos cinzas (invertido) e Mediana 2 no canal. Receita `nova-recorte-rembg.json`.
   Cuidado com objeto branco ou cinza na parte (armadilha 30).
4. **Corte reto** (`borda_opaca`): degradê em multiplicar no canal até a linha do corte (coordenadas
   da peça), refazer a máscara. Decisão de gosto: diga ao diretor.
5. **Objeto sobre fundo liso**: `layer.removeBackground` ou `select.colorRange` do fundo + revelar.
   Com cena atrás, nenhuma seleção clássica serve: máscara do grafo (peça do loop) ou volta à geração.
6. Borda serrilhada sobre fundo diferente: `select.loadSelection` transparência ->
   `select.modify.feather {"radius": 0.7}` -> `layer.layerMask.revealSelection`. Não na peça do loop.

Máscara sempre **pela seleção** (carregar, mexer no canal, revelar). Nunca difusão ao vivo, nunca
vetorial, nunca `refineEdge` com `decontaminate` (o `acabar.py` recusa).

## Metas

- `franja` entre -3 e +3, `semi_%` até 3, `ilhas` até 5; `anel` perto de `anel_ref`.
- A área da parte não cai mais que ~3% (exceto quando o que sai é fundo, como a sombra cinza).
- ΔE da parte não sobe mais que 0,5; numa peça nova, costuma cair.
- A olho, ampliado na borda: sem contorno escuro fino, sem buraco no objeto.

Números de referência: B mascote franja -14,0 -> -1,6, névoa 13,4% -> 2,1%, ilhas 36 -> 5;
B entorno franja +14,3 -> +3,7, ΔE 41,9 -> 39,9.

## Protocolo

Siga o protocolo de especialista do seu agente (`.claude/agents/recortista.md`). Para ver a
borda de perto sem gastar imagem grande, recorte só a região da parte (≤ 1000 px).
