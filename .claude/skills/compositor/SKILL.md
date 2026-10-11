---
name: compositor
description: Monta as partes em camadas na ordem da ficha e entrega PSD editável mais PNG/WebP. Use depois que as partes estiverem registradas.
---

# Compositor

## Protocolo

1. Rode `python pipeline.py <ficha> --provedor registro|comfyui --tema <tema> [--formato ...]`. Na ficha v1.0 o tema é o nome do figurino.
2. Para conferir o PSD no PhotoCraft, rode `integracoes/photocraft/conferir_psd.py`. Confira que o PSD tem as camadas com os nomes e na ordem de `camadas` da ficha.
3. Acabamento (cor, nitidez, bordas, luz) é da skill `acabamento`, no PhotoCraft, por receita. Ajuste de posição ou de camada que precise valer sempre vira proposta de mudança na ficha, não só no arquivo.
4. Entregue o PNG para aprovação e o PSD para edição.

## Regras

- Posições vêm do `layout` da ficha, em frações da peça. Não mova à mão sem registrar.
- Texto sempre por `motor/texto.py`.
- Na tentativa a partir do grafo (`tentativa.py`), texto e logo vão para as caixas medidas na referência
  e os efeitos que já vêm no fundo da referência (escurecimento, brilho) entram no PSD desligados.
