# Ficha ARARA v1.2: o que mudou e por quê

Feita e aprovada pelo dono em 10/10/2026. Substitui a v1.1, que fica guardada
como estava.

## De onde vem

Na fase 2 as 11 referências foram desconstruídas do mesmo jeito que a promo do
Telegram, cujo recorte o dono aprovou em 10/10/2026. Cada peça tem:

- a marcação `fichas/arara/grafos/<peca>.marcacao.yaml` (contornos, caixas e observações);
- o grafo `fichas/arara/grafos/<peca>.json` com as partes recortadas;
- a prancha `fichas/arara/grafos/<peca>/conferencia.jpg` (bordas encaixadas e recortes);
- as placas `sem-texto.webp` e `cena-limpa.webp`, feitas no ComfyUI.

`ferramentas/juntar_grafos.py` junta as medidas de todas em
`fichas/arara/grafos/medidas-dos-grafos.json`. As duas peças da árvore de
indicação (`home-convite-2` e `promo-convite-2`) têm outra composição: contam
para o logo e o texto, mas ficam fora das caixas do mascote, do entorno e da
frente.

## Mudanças em relação à v1.1

### 1. Camada nova: `frente`

Nas 11 peças há algo na frente do mascote, cobrindo parte dele: baús, moedas,
envelopes, folhas, a mesinha do VIP, as plaquinhas da árvore. Na v1.1 isso
ficava grudado no fundo, então um mascote novo ficava atrás de nada. A v1.2
cria a parte `frente` (gerada, transparente) e a camada `frente` entre o
mascote e o brilho. Cada tema diz o que vai nela.

| Peça | O que está na frente |
|---|---|
| home-convite-1, promo-convite-1 | baús abertos cheios de moedas |
| home-convite-2, promo-convite-2 | as três plaquinhas verdes de nível |
| home-instagram, promo-instagram | ícone de câmera, balão de coração e moeda com coroa, desfocados |
| promo-deposito | galho com musgo e moedas soltas |
| promo-envelopes | seis envelopes grandes e desfocados |
| promo-vip | mesinha de vidro com drinque e óculos, folha grande |
| promo-reembolso | duas moedas grandes e uma folha, desfocadas |
| promo-telegram | flor de hibisco e folhas embaixo (no recorte aprovado ficaram no fundo) |

### 2. Layout medido

As caixas da v1.1 eram estimativa a olho. Agora são a mediana das peças.

Caixas em fração da largura (x, w) e da altura (y, h) da peça. O entorno e a
frente vão até a borda direita, e a frente até a base.

| Formato | Camada | v1.1 (x, y, w, h) | v1.2 (x, y, w, h) | Peças medidas |
|---|---|---|---|---|
| home | logo | 0,030 0,060 0,140 | 0,030 0,078 0,138 | 3 |
| home | texto | 0,055 0,200 0,430 0,600 | 0,059 0,215 0,413 0,582 | 3 |
| home | mascote | 0,580 0 0,420 1 | 0,588 0 0,343 1 | 2 |
| home | entorno | 0,480 0 0,520 1 | 0,578 0 0,422 1 | 2 |
| home | frente | (não tinha) | 0,593 0,674 0,407 0,326 | 2 |
| promo | logo | 0,030 0,050 0,220 | 0,030 0,052 0,217 | 8 |
| promo | texto | 0,030 0,260 0,520 0,480 | 0,043 0,253 0,476 0,509 | 8 |
| promo | mascote | 0,500 0 0,500 1 | 0,534 0 0,456 1 | 7 |
| promo | entorno | 0,420 0 0,580 1 | 0,459 0 0,541 1 | 7 |
| promo | frente | (não tinha) | 0,577 0,663 0,423 0,337 | 6 |

Em palavras: o texto e o logo quase não mudam; o mascote fica mais estreito e
um pouco mais à direita, e o entorno começa mais à direita.

### 3. As mãos do mascote

Em todas as peças o mascote segura as coisas com uma mão escura de dedos na
ponta da asa, não com a ponta da asa. O prompt do mascote passa a pedir
"dark grey fingered hands at the wing tips" e o `segura` de cada tema diz
"in one dark fingered hand".

### 4. Figurino realeza

Corrigido pelo que se vê nas 5 peças de realeza: a coroa tem um penacho
vermelho, amarelo e azul (a v1.1 dizia penas verdes), o colar tem uma
esmeralda grande no peito e as pulseiras são largas, de ouro com esmeraldas.

### 5. Temas

| Tema | O que mudou | Evidência |
|---|---|---|
| convite | entorno: baús grandes abertos, transbordando moedas e esmeraldas (não há moedas soltas no ar); frente: um baú grande. Referências: só as duas peças dos baús | home-convite-1, promo-convite-1 |
| convite_rede (novo) | a árvore de indicação: mascote pequeno num medalhão no topo, fazendo positivo com uma luva azul; em volta, uma rede de medalhões com variantes da arara ligados por linhas douradas; plaquinhas de nível na frente | home-convite-2, promo-convite-2 |
| deposito | a moeda tem furo quadrado; há um baú aberto no canto; frente: moedas e galho com musgo | promo-deposito |
| instagram | o entorno também tem moedas com coroa; frente: ícones, balões de coração e moedas desfocados; a linha dourada do exemplo fica com peso 1,25 (era 1,45) | home-instagram, promo-instagram |
| telegram | frente: flor de hibisco e folhas | promo-telegram |
| envelopes | envelopes nítidos perto do mascote e desfocados longe; frente: envelopes grandes | promo-envelopes |
| vip | trono esculpido de ouro com veludo verde; no entorno, uma esfera de vidro com coroa num pedestal (o drinque saiu do entorno); frente: mesinha com drinque tropical, óculos e uma folha | promo-vip |
| reembolso | o caça-níquel tem setes, cerejas e coroas; frente: moedas grandes e uma folha | promo-reembolso |

### 6. Cores das letras

Medidas na letra inteira, mediana por terço da altura (no alto, no meio e
embaixo), nas 41 linhas que não misturam estilos. As letras das referências são bem mais chapadas que as
rampas da v1.1, que escureciam até cinza e laranja na base.

| Estilo | No alto | No meio | Na base | Diferença para a v1.1 (alto, meio, base) |
|---|---|---|---|---|
| branco (23 linhas) | `#fbfcfa` | `#f9f9f9` | `#e9e9e8` | 1,9 · 3,4 · 9,0 |
| dourado (18 linhas) | `#fce00e` | `#fcde06` | `#f2b004` | 8,4 · 7,2 · 8,5 |

A diferença é o ΔE CIEDE2000: acima de uns 5 já dá para ver a olho.

### Sem mudança

Paleta, cena, escurecimento (a curva medida nos grafos confirma a da v1.1),
contorno, sombra, vão entre linhas (0,14 do corpo da letra; nos grafos o vão
fica entre 0,17 e 0,23 da altura da letra, o que dá o mesmo) e o peso da linha
dourada do exemplo neutro (1,45: nas peças, a primeira linha dourada depois de
uma branca tem mediana de 1,43 vez a altura da primeira linha).

## O que a ficha ainda não resolve

São coisas que pedem código, não só ficha. Ficam para depois da aprovação.

1. **Linhas que misturam branco e dourado.** 5 das 46 linhas fazem isso (a
   última linha dos dois convites com baú, dos dois Instagram e dos
   envelopes). A ficha só prevê um estilo por linha; `motor/texto.py` teria
   de aceitar trechos com estilos diferentes na mesma linha.
2. **Bloco de texto em duas colunas.** No reembolso, embaixo das linhas
   empilhadas, uma frase de duas linhas fica ao lado de um número dourado
   enorme. A ficha só descreve uma pilha de linhas.
3. **Rótulos fora do bloco.** As três plaquinhas da árvore de indicação têm
   texto. Texto sai de código, então placa e rótulo devem sair juntos de
   código.
4. **Árvore de indicação.** A rede de medalhões e linhas douradas é um
   diagrama. O fluxo atual de IA não monta isso; o caminho mais firme é montar
   a rede por código e gerar só os retratos dos medalhões.
5. **Galho de apoio.** Em 4 peças (os dois convites com baú, depósito e
   envelopes) o mascote fica num galho grosso, que está no fundo. Um mascote
   novo em outra pose não encaixa no galho.
6. **Luz.** Raios dourados longos, riscos de luz verde neon e anéis de luz
   atrás do mascote aparecem em 5 peças. A camada brilho só tem poeira e raios
   finos.
7. **Medalhão do peito.** Muda por peça (ícone do Telegram, coroa no
   Instagram; no reembolso aparece o avião do Telegram). A ficha não diz o que
   vai nele em cada tema.
8. **Turista sem óculos.** Nos envelopes o mascote está sem óculos e com a
   camisa aberta. A v1.2 mantém os óculos no figurino turista.
9. **Rótulos das plaquinhas.** Na árvore, a IA refaz as plaquinhas da frente
   sem o texto (o texto sai de código e ainda não tem quem desenhe), por isso
   a frente dessas duas peças fica longe da referência (ΔE 22 a 24).

## Depois da aprovação (10/10/2026)

As 11 marcações apontam para a v1.2; as duas peças da árvore usam o tema
`convite_rede`. As placas de fundo limpo foram refeitas sem os objetos da
frente, e o loop rodou uma volta em cada peça (`fluxos/arara/tentativas.jsonl`,
denoise da melhor volta da fase 1: fundo 0,2, figura 0,3, objeto 0,3):

| Peça | ΔE da peça | cena | entorno | mascote | frente |
|---|---|---|---|---|---|
| promo-telegram | 10,8 | 9,7 | 8,5 | 11,7 | (vazia) |
| home-convite-1 | 9,4 | 9,1 | 11,4 | 10,0 | 10,7 |
| promo-convite-1 | 8,0 | 7,0 | 11,5 | 9,9 | 9,6 |
| home-convite-2 | 11,5 | 10,1 | 16,1 | 6,6 | 23,6 |
| promo-convite-2 | 11,2 | 9,0 | 17,1 | 6,4 | 22,5 |
| home-instagram | 10,6 | 11,0 | 10,7 | 10,5 | 8,0 |
| promo-instagram | 9,1 | 8,9 | 10,5 | 9,6 | 6,7 |
| promo-deposito | 7,8 | 5,5 | 10,6 | 9,3 | 9,3 |
| promo-envelopes | 9,2 | 9,3 | 10,0 | 9,0 | 10,0 |
| promo-vip | 10,5 | 8,5 | 6,1 | 10,8 | 14,6 |
| promo-reembolso | 10,4 | 8,9 | 12,4 | 11,7 | 9,8 |

O recorte aprovado do Telegram não tem frente: a camada entra vazia no PSD e a
flor continua no fundo. A tentativa 005 dele repete a 004 da fase 1 (ΔE 10,8).

## Limites dos recortes

- Fiapos finos de fundo entre as pontas das penas nos convites com baú.
- No reembolso, um pouco do brilho dourado em volta do número grande entra na
  máscara do texto. Não atrapalha: o texto é apagado do mesmo jeito.
- Moedas desfocadas da frente ficam com a borda serrilhada.
- O recorte aprovado do Telegram não marcou a flor da frente. A máscara do
  texto dele foi refeita com a letra inteira (a ferramenta melhorou) e, com
  isso, a do mascote mudou 705 pixels (0,14%). O workflow do Telegram agora tem
  sha256 `4dae6bef…` (a tentativa 001 usou `860e8d0e…`).
- As revisões independentes dos recortes foram curtas porque o limite de uso
  da conta cortou a sessão duas vezes; cada prancha foi conferida pelo
  marcador em close e por mim na folha de contato.
