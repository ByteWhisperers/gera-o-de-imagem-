# Ficha ARARA v1.1: o que mudou e por quê

Aprovada pelo dono em 09/10/2026, junto com uma regra nova:

> Existe uma correlação do texto com o figurino do mascote. Ela é mais forte
> em peças como Instagram/Telegram, onde o mascote fica envolto em ícones, e
> menor em peças genéricas como "convide 1 pessoa e ganhe". Quando a mensagem
> do texto mudar, o estilo do mascote e seus elementos devem mudar junto.

## Mudanças em relação à v1.0

- **Temas.** Cada mensagem vira um tema com `figurino`, `segura` (o que o
  mascote tem nas mãos), `entorno` (objetos em volta) e a força da `ligacao`
  (forte, media, fraca). O prompt do mascote e do entorno sai do tema.
- **Camada `entorno`**, entre o escurecimento e o mascote, ocupando a metade
  direita da peça. É onde ficam os ícones e objetos do tema.
- O mascote deixa de ter "one wing raised" fixo: o que ele faz com as asas
  depende do que segura.

## De onde vieram os temas

| Tema | Ligação | Figurino | Referências |
|---|---|---|---|
| convite | fraca | realeza | `home/banner1`, `home/banner2`, `promo/promo-1790980982-3c38ef02`, `promo/promo-1790981047-26876e08` |
| deposito | media | realeza | `promo/promo-1790980959-9639e055` |
| instagram | forte | turista | `home/banner3`, `promo/promo-1790981412-117f1d73` |
| telegram | forte | turista | `promo/promo-1790981127-d91c22ef` |
| envelopes | forte | turista | `promo/promo-1790980998-e0741671` |
| vip | forte | turista | `promo/promo-1790981066-c225f1b5` |
| reembolso | forte | turista | `promo/promo-1790981102-82ba1db4` |

As referências ficam em `referencias/arara/`.

Os textos de exemplo continuam neutros. Só o tema instagram tem linhas
próprias ("SIGA NOSSO / INSTAGRAM / E FIQUE POR DENTRO"); os outros usam as
linhas neutras da ficha.
