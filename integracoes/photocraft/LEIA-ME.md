# PhotoCraft no projeto

O PSD é o contrato da composição: qualquer editor que abre PSD serve. O
PhotoCraft (https://github.com/storytold/photocraft, editor livre do tipo
Photoshop) é o que testamos, porque tem linha de comando e MCP.

O ArtCraft, do mesmo time, não tem MCP; o MCP é do PhotoCraft.

## Instalar (testado com a 0.5.0)

```bash
git clone https://github.com/storytold/photocraft
cd photocraft && cargo build --release -p photocraft-cli    # gera target/release/photocraft-cli
```

## Conferir um PSD nosso

```bash
python integracoes/photocraft/conferir_psd.py saida/arara/promo-telegram-comfyui.psd \
    --ficha fichas/arara/ficha-v1.1.yaml --cli caminho/para/photocraft-cli
```

Confere que as camadas lidas pelo PhotoCraft têm os nomes e a ordem da ficha e
que o render dele bate com o nosso PNG (diferença média de 2 a 5 em 255 nos testes).

## MCP

`photocraft-cli mcp --automation-read-root <repo> --automation-write-root <repo>/saida`
abre um servidor MCP com ferramentas como `doc_open`, `doc_inspect`,
`command_run` e `render_preview`. Teste rápido:

```bash
python integracoes/testar_mcp.py -- photocraft-cli mcp --automation-read-root .
```
