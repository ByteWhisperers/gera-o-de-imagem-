# Memória do diretor de acabamento

Uma linha por aprendizado, com data. O que o dono decidiu sobre acabamento vem primeiro.

## Decisões do dono

- 2026-10-11: o dono pediu agentes que dominem o PhotoCraft para subir a qualidade do que sai do
  ComfyUI ("testei na mão na minha máquina e o resultado é impressionante").

## O que já se sabe

- 2026-10-11: nas tentativas do loop (img2img a partir da referência) a cor já vem certa; casar a
  cor por curvas não baixa o ΔE (a diferença é de detalhe, não de tom). O que falta é nitidez:
  mascote e entorno saem uns 40% menos nítidos que a referência (promo-deposito-001).
- 2026-10-11: na peça gerada do zero (promo-telegram-comfyui, SD-Turbo) tudo sai lavado: 20 a 24%
  menos saturado e mais de 50% menos nítido que a referência.
- 2026-10-11: a ordem que funciona é recortista -> colorista -> retocador -> iluminador. Na B, o
  sombreado do mascote criado depois do remendo do pseudo-texto ficou embaixo dele (camisa sem
  sombra): a camada nova nasce logo acima da selecionada; use `alvo` com o remendo.
- 2026-10-11: receitas boas sozinhas passam do ponto quando somadas. Na B, cor quente + luz e
  sombra deixaram as moedas chapadas (entorno +28% de luz, -63% de contraste). Por isso cada
  especialista trabalha sobre o PSD do anterior.
- 2026-10-11: na A, luz por medida + nitidez com máscara + contorno sutil juntas deixaram o
  diagnóstico limpo (só "menos brilho em volta" na frente e no entorno), ΔE da peça +0,1.
- 2026-10-11: na B, a equipe em cadeia (recortista-3, colorista-1, retocador-1, iluminador-2, cada
  um sobre o PSD do anterior) juntada numa receita só (`promo-telegram-comfyui-1`) deu o mesmo
  número da cadeia: diagnóstico 19 achados -> 1 (cena -28% de nitidez), ΔE da peça 32,7 -> 32,2.
  Juntar no fim funciona; testar junto antes (pasta sua) confirma.
- 2026-10-11: na B, o `casar_cor` no mascote inteiro puxou o bico e as lentes cinza para rosado
  (a arara da referência é quente). A régua não pega: olhe a imagem. Partes neutras pedem máscara
  ou casar só a luz.
- 2026-10-11: corrigido com a `colorista-2` (máscara de neutros + cópia só de luz nos cinzas):
  bico, lentes e garganta voltam ao cinza (R-B 76 -> 9), ΔE da peça igual (32,2). Receita
  `promo-telegram-comfyui-2` substitui a -1.
