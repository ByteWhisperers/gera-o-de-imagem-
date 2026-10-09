# Produção de imagem: guia para o agente coordenador

O dono escreve em português e tem pouca base de design: responda em português simples, mostre imagens em vez de descrever, e peça aprovação antes de mudar uma ficha ou gastar.

## A linha de produção

1. **Referência**: exemplos em `referencias/<marca>/`.
2. **Desconstrução**: skill `analista-referencia` escreve `fichas/<marca>/ficha-vX.Y.yaml`.
3. **Criação**: skill `operador-geracao` gera as partes e registra em `partes/<marca>/registro.yaml`.
4. **Composição**: skill `compositor` roda `pipeline.py` e entrega PSD + PNG/WebP.
5. **Revisão**: skill `revisor-qa` lê o relatório do QA e olha as imagens.

A ficha é o contrato. Só a desconstrução escreve nela; as outras etapas só leem. Ficha aprovada não se edita: crie a versão seguinte.

## Regras

- Texto, logo e avisos saem de código (`motor/texto.py`), nunca da IA.
- Toda parte gerada entra pelo portão (`motor/portao.py`). Parte sem receita registrada não entra.
- Gasto com IA só com autorização do dono e registrado com custo no `registro.yaml`.
- Mudou a mensagem, muda o tema: figurino, o que o mascote segura e os objetos em volta vêm do tema da ficha.
- Testes usam textos neutros (`texto.exemplo` da ficha), nunca textos de oferta.

## Comandos

```bash
pip install -r requirements-dev.txt
python -m pytest -q
python pipeline.py fichas/arara/ficha-v1.1.yaml --tema telegram                      # rascunho, custo zero
python pipeline.py fichas/arara/ficha-v1.1.yaml --tema telegram --provedor comfyui   # ComfyUI local, grátis
python pipeline.py fichas/arara/ficha-v1.0.yaml --tema turista --provedor registro   # partes do teste 1 (fal)
python integracoes/comfyui/rodar_fluxo.py --tema telegram --formato promo            # fluxo completo no ComfyUI
python ferramentas/medir.py referencias/arara > fichas/arara/medidas.json
```
