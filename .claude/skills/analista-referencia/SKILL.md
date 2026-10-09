---
name: analista-referencia
description: Desconstrói referências visuais em uma ficha de estilo (fichas/<marca>/ficha-vX.Y.yaml). Use quando chegarem referências novas ou quando a ficha precisar de nova versão.
---

# Analista de referência

Você transforma imagens de referência em informação que o código lê.

## Protocolo

1. Copie as referências para `referencias/<marca>/` (WebP q90) e anote em `/mnt/project-files/.notes/inputs.md`.
2. Rode `python ferramentas/medir.py referencias/<marca> > fichas/<marca>/medidas.json`.
3. Olhe cada peça e responda as 8 lentes: cena, personagem, layout, cores, tipografia, efeitos, ordem das camadas, o que é fixo e o que varia.
4. Escreva a ficha no formato de `fichas/arara/ficha-v1.0.yaml`. Todo número tem origem: `medidas.json` ou `(estimativa)`.
5. Revisor cético: reabra as peças e tente derrubar cada afirmação. O que não se sustenta sai ou é corrigido.
6. Escreva `ficha-vX.Y.md` com a evidência e deixe `estado: proposta`. O dono aprova.

## Regras

- Nunca edite uma ficha `aprovada`: crie a próxima versão.
- Para cada mensagem das referências, registre um tema: figurino, o que o mascote segura, o entorno e a força da ligação com o texto.
- Estilo pode ser descrito; marca, logo e personagem de terceiros não entram como coisa a copiar.
- Leia `memoria.md` antes de começar e acrescente o que aprendeu ao terminar.
