# Ficha CAPIVARA362 v1.0: o padrão visual da 9pmbet com a nossa capivara

Estado: **proposta** (falta o dono aprovar).

## De onde veio

- 13 banners da 9pmbet, da pasta "IMAGENS CONCORRÊNTES/9pmbet" no Drive do dono:
  5 da home (1020x300) e 8 de promoção (710x320). A pasta da logo deles foi ignorada.
- Copiados em `referencias/9pmbet/home/` e `referencias/9pmbet/promo/`, com o tema no nome.
- `medidas.json` saiu de `ferramentas/medir.py`. Os grafos de 3 peças (home-telegram,
  home-envelopes, promo-vip) foram juntados em `grafos/medidas-dos-grafos.json`.
- Do concorrente só entra o estilo. O logo é o nosso (`referencias/capivara362/logo/logo.webp`),
  e os personagens deles (touro, pandas, mago, tigre, chacal, coelho, rainha, pirata)
  viram a capivara com o figurino do tema.

## As 8 lentes

1. **Cena.** Fogo laranja, vermelho e dourado, com uma explosão de luz atrás do mascote,
   raios brancos finos, brasas, bokeh e moedas voando desfocadas. As exceções são o convite
   (roxo e rosa) e as redes sociais (azul-noite com raios roxos).
2. **Personagem.** Um mascote 3D de jogo mobile, cabeçudo, de olho grande e boca aberta,
   inclinado para a câmera. Ele muda a cada tema: no Telegram é um mago, no VIP um faraó,
   nos envelopes uma roupa chinesa vermelha. Aparece em meio corpo, cortado pela base.
3. **Layout.**
   - Logo pequeno no topo esquerdo, com x 0,041 nas 3 peças medidas.
   - Bloco de texto alinhado à esquerda, entre x 0,05 e 0,07 e y de 0,30 a 0,80.
   - Mascote de ~0,42 até ~0,95 da largura.
   - Objetos em volta do mascote e, em 6 de 13 peças, uma pilha na frente, no pé da peça
     (envelopes, moedas, notas).
4. **Cores.**
   - A esquerda é quase preta: L mediana por décimo da largura, nas 13 peças, é
     5 13 21 47 86 123 135 145 161 131.
   - A esquerda é mais escura que o centro em 13 de 13.
   - L mediana da peça entre 46,8 e 146,0.
5. **Tipografia.**
   - Sem serifa geométrica, larga e muito pesada, em caixa alta.
   - Só duas cores, chapadas: branco #fffefb e amarelo-limão #fef510, medidas na letra
     inteira; os três terços da letra têm a mesma cor.
   - Sem contorno e com sombra mínima.
   - A palavra-chave fica em amarelo e enorme. No promo-vip, "VIP" tem 4 vezes a altura das
     linhas brancas; nas outras peças é 2 a 3 vezes, a olho.
   - Vão entre linhas de 0,44 a 0,50 da altura da letra.
6. **Efeitos.** Faíscas e brasas por toda a peça, raios, e rastros de fogo nas moedas e nos
   envelopes.
7. **Ordem das camadas.** Cena, escurecimento, entorno, mascote, frente, brilho, texto e logo.
8. **Fixo e variável.**
   - Fixo: o preto da esquerda, as duas cores de letra, a posição do logo e do texto, e o
     mascote à direita.
   - Varia com o tema: o personagem (para nós, o figurino), o que ele segura, os objetos em
     volta e a cor do fogo.

## Temas (um por mensagem das referências)

| tema | referências | figurino | ligação |
|---|---|---|---|
| resgate | home, promo | sorte (roupa chinesa) | média |
| convite | home, promo | rua (boné e jaqueta) | média |
| telegram | home | mago | forte |
| envelopes | home, promo | sorte | forte |
| vip | home, promo | faraó | forte |
| rebate | promo | rua | média |
| apostas | promo | sorte | média |
| login | promo | faraó | média |
| redes | promo | pirata | forte |

## O que o revisor cético derrubou ou corrigiu

- **Contorno.** "Texto com contorno escuro" não se sustenta: `contorno_escuro_frac` alto só
  aparece porque o fundo atrás é preto. A desconstrução precisou do modo
  `texto_sem_contorno`, porque sem ele as letras sobre o fogo amarelo eram cortadas.
- **Degradê.** "O dourado tem degradê como o da Arara" é falso: as letras são chapadas.
- **Escurecimento.** O gradiente da Arara não deixava o preto chapado até ~30%. Entrou
  `cheio_ate` no escurecimento (opcional; as fichas antigas não mudam).
- **Tamanho.** As referências são pequenas. A peça final sai no dobro (2040x600 e
  1420x640), e o loop compara no tamanho da referência.

## O que fica para a v1.1

- **Layout medido em poucas peças.** Hoje são 3 grafos (2 home, 1 promo). Marcar mais peças
  para medir mascote, entorno e frente no promo.
- **Fonte.** A Montserrat Black é mais estreita que a letra deles; vale testar uma
  sem serifa larga e pesada (OFL).
- **Luz atrás do mascote.** A cena gerada tem menos clarão dourado atrás do mascote que a
  referência.
- **Objetos estranhos.** No tema envelopes, o entorno gerou um boneco vermelho. A ideia é
  pedir só envelopes no prompt ou gerar mais de uma opção.
