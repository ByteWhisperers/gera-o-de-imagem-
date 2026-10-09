---
name: compositor
description: Monta as partes em camadas na ordem da ficha e entrega PSD editável mais PNG/WebP. Use depois que as partes estiverem registradas.
---

# Compositor

## Protocolo

1. Rode `python pipeline.py <ficha> --provedor registro [--formato ...] [--figurino ...]`.
2. Confira que o PSD tem as camadas com os nomes e na ordem de `camadas` da ficha.
3. Se precisar de ajuste manual, abra o PSD num editor de camadas (PhotoCraft via MCP, Photopea, GIMP) e registre o ajuste como proposta de mudança na ficha, não só no arquivo.
4. Entregue o PNG para aprovação e o PSD para edição.

## Regras

- Posições vêm do `layout` da ficha, em frações da peça. Não mova à mão sem registrar.
- Texto sempre por `motor/texto.py`.
