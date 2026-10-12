# Produção de imagem: guia para o agente coordenador

O dono escreve em português e tem pouca base de design: responda em português simples, mostre imagens em vez de descrever, e peça aprovação antes de mudar uma ficha ou gastar.

## A linha de produção

1. **Referência**: exemplos em `referencias/<marca>/`.
2. **Desconstrução**: skill `analista-referencia` escreve `fichas/<marca>/ficha-vX.Y.yaml` e, por peça, o grafo `fichas/<marca>/grafos/<peca>.json` com as partes isoladas.
3. **Criação**: skill `operador-geracao` gera as partes e registra em `partes/<marca>/registro.yaml`.
4. **Composição**: skill `compositor` roda `pipeline.py` e entrega PSD + PNG/WebP.
5. **Acabamento**: skill `acabamento` (diretor) e os agentes `recortista`, `colorista`, `retocador` e `iluminador` (nessa ordem) editam o PSD no PhotoCraft; `integracoes/photocraft/acabar.py` aplica a receita, mede contra a referência e anota em `fluxos/<marca>/acabamentos.jsonl`.
6. **Revisão**: skill `revisor-qa` lê o relatório do QA e olha as imagens.
7. **Loop**: `tentativa.py` monta o workflow a partir do grafo, roda, compara cada parte com a referência e anota em `fluxos/<marca>/tentativas.jsonl`.

A ficha é o contrato. Só a desconstrução escreve nela; as outras etapas só leem. Ficha aprovada não se edita: crie a versão seguinte.

## Regras

- Texto, logo e avisos saem de código (`motor/texto.py`), nunca da IA.
- Toda parte gerada entra pelo portão (`motor/portao.py`). Parte sem receita registrada não entra.
- As tentativas do loop ficam no diário `fluxos/<marca>/tentativas.jsonl`, com o workflow guardado pelo sha256. Só viram parte da biblioteca depois que o dono aprova.
- O acabamento no PhotoCraft não toca no texto nem no logo e não põe camada acima deles. A receita de acabamento só vira padrão depois que o dono aprova.
- Gasto com IA só com autorização do dono e registrado com custo no `registro.yaml`.
- Mudou a mensagem, muda o tema: figurino, o que o mascote segura e os objetos em volta vêm do tema da ficha.
- Testes usam textos neutros (`texto.exemplo` da ficha), nunca textos de oferta.

## Comandos

Primeira vez numa máquina nova: siga o `INSTALAR.md` (quatro níveis, do rascunho ao PhotoCraft).

```bash
pip install -r requirements-dev.txt
python -m pytest -q
python pipeline.py fichas/arara/ficha-v1.2.yaml --tema telegram                      # rascunho, custo zero
python pipeline.py fichas/arara/ficha-v1.2.yaml --tema telegram --provedor comfyui   # ComfyUI local, grátis
python pipeline.py fichas/arara/ficha-v1.0.yaml --tema turista --provedor registro   # partes do teste 1 (fal)
python pipeline.py fichas/arara/ficha-v1.2.yaml --tema telegram --provedor gateway --teto 0.05   # gateway de imagem, PAGO: só com autorização do dono
python integracoes/comfyui/rodar_fluxo.py --tema telegram --formato promo            # fluxo completo no ComfyUI
python ferramentas/medir.py referencias/arara > fichas/arara/medidas.json
pip install -r requirements-desconstrucao.txt
python ferramentas/desconstruir.py fichas/arara/grafos/promo-telegram.marcacao.yaml --placas   # grafo + partes isoladas
python tentativa.py fichas/arara/grafos/promo-telegram.json                                    # uma volta do loop, grátis
python integracoes/photocraft/acabar.py medir saida/arara/tentativas/promo-telegram-005/peca.psd   # diagnóstico contra a referência
python integracoes/photocraft/acabar.py aplicar <psd> --receita integracoes/photocraft/receitas/arara/<r>.json --mudanca "..."   # acabamento, grátis
```
