# Ficha ARARA v1.0: evidência

Estado: **proposta** (falta a aprovação do dono). Feita em 09/10/2026 a partir das 12 referências em `referencias/arara/` e das medidas em `medidas.json`.

## O que se repete em todas as peças

| Lente | O que se vê | Base |
|---|---|---|
| Cena | Vale de rio com torres cársticas e selva, sol se pondo em contraluz entre as torres | 11 de 11 peças |
| Personagem | Arara-vermelha 3D de animação, meio-corpo, rindo, bico preto, à direita | 10 de 11 (o promo da pirâmide só tem ícones) |
| Figurinos | **turista**: chapéu de palha com flor, óculos escuros, camisa havaiana verde. **realeza**: coroa com esmeraldas, colar e pulseiras de ouro | turista em 5 promos e no banner3; realeza em 2 promos e no banner1 |
| Layout | Logo no canto superior esquerdo; texto à esquerda numa zona escura; mascote ocupa a direita, encostado embaixo | 11 de 11 (posições na ficha são estimativa) |
| Brilho | A faixa esquerda (0–35% W) é sempre mais escura que o centro | 11 de 11; medianas de L: esquerda 39–71, centro 51–105 |
| Cores | Verde quase preto domina; dourado `#fbd448` aparece entre as 4 cores principais em 5 peças | medidas.json |
| Tipografia | Caixa alta muito pesada, branco cromado e dourado metálico, contorno marrom escuro e sombra | 11 de 11 |
| Efeitos | Poeira dourada, raios finos, moedas e objetos dourados voando | 11 de 11 |
| Ordem das camadas | cena, escurecimento, mascote, brilho, texto, logo | leitura das sobreposições |

## O que varia entre peças

Os objetos que o mascote segura (baú, moedas, celular, envelope, cartão VIP), o figurino e o texto. Esses objetos ainda não estão na ficha: ficam para a v1.1.

## Limites desta versão

- Posições do layout foram lidas a olho, sem medição de pixel.
- O `ponto_claro_centro` de `medidas.json` muitas vezes cai no texto branco, não no sol.
- Não há regra de QA para o figurino nem para o bico preto: hoje isso é olhado pelo revisor.

## Conferência com o trabalho anterior

Bate com `gerador-imagens/constante-visual.md` (repo modelo2cs): texto começando em ~5,5% W, terminando antes de 50% W no banner e 55% no card, mascote a partir de ~57–61% W no banner e ~50–54% no card.
