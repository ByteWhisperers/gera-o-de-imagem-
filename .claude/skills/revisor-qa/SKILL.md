---
name: revisor-qa
description: Confere cada peça contra a ficha (relatório automático + olhar a imagem) e decide aprovar ou mandar refazer. Use depois de cada rodada do pipeline.
---

# Revisor (QA)

## Protocolo

1. Leia `saida/<marca>/relatorio-<provedor>-<tema>.json`: cada regra com valor e esperado.
2. Abra o PNG e compare lado a lado com 2 referências do mesmo formato.
3. Para cada falha, diga qual etapa refaz: parte (operador), posição (ficha) ou regra de QA errada (analista).
4. Uma regra que deixou passar um defeito visível vira regra nova em `motor/qa.py`.
5. Tentativa a partir do grafo: leia a última linha de `fluxos/<marca>/tentativas.jsonl` e abra a
   `prancha.jpg` dela. Cada parte tem ΔE (cor), ssim (forma), paleta e cobertura contra a mesma parte
   isolada na referência. Os limites ainda não estão calibrados (fase 3): por enquanto, compare com a
   tentativa anterior e com os controles da prancha. Quem marca `decisao` é o dono.

## Memória

- 2026-10-09: o QA aprovou um mascote sem recorte (fundo cinza inteiro). Nasceu a regra `mascote_recortado`.
- 2026-10-10: o QA aprovou um rascunho com uma elipse vermelha no lugar da arara, porque só conferia
  faixas da ficha. Nasceu o comparador por parte contra a referência (`motor/comparar.py`).
