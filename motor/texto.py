"""Desenha o bloco de texto da ficha: caixa alta, degradê metálico, contorno e sombra.

O texto nunca vem da IA. Sai daqui, a partir das linhas e dos estilos da
ficha, para estar sempre escrito certo.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont

RAIZ = Path(__file__).resolve().parent.parent


def _rampa(altura: int, paradas: list) -> np.ndarray:
    """Degradê vertical (altura x 3) a partir de [[posição, cor], ...]."""
    pos = np.array([p for p, _ in paradas], dtype=np.float32)
    cores = np.array([ImageColor.getrgb(c) for _, c in paradas], dtype=np.float32)
    t = np.linspace(0, 1, max(altura, 1), dtype=np.float32)
    return np.stack([np.interp(t, pos, cores[:, k]) for k in range(3)], axis=1)


def _linha(texto: str, fonte: ImageFont.FreeTypeFont, estilo: dict, cfg: dict) -> tuple[Image.Image, int, int]:
    """Uma linha pronta. Devolve a imagem, a margem em volta das letras e a altura das letras."""
    corpo = fonte.size
    contorno = max(1, round(cfg["contorno"]["espessura"] * corpo))
    sombra = cfg["sombra"]
    dx, dy = (round(v * corpo) for v in sombra["desvio"])
    margem = contorno + abs(dy) + round(sombra["desfoque"] * corpo) * 2 + 4
    x0, y0, x1, y1 = fonte.getbbox(texto)
    w, h = x1 - x0 + 2 * margem, y1 - y0 + 2 * margem
    origem = (margem - x0, margem - y0)

    mascara = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mascara).text(origem, texto, font=fonte, fill=255)
    borda = Image.new("L", (w, h), 0)
    ImageDraw.Draw(borda).text(origem, texto, font=fonte, fill=255, stroke_width=contorno, stroke_fill=255)

    camada = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    # sombra
    s = borda.filter(ImageFilter.GaussianBlur(max(1, sombra["desfoque"] * corpo)))
    s = s.point(lambda a: int(a * sombra["opacidade"]))
    cor_sombra = Image.new("RGBA", (w, h), ImageColor.getrgb(sombra["cor"]) + (255,))
    cor_sombra.putalpha(s)
    camada.alpha_composite(cor_sombra, (dx, dy))
    # contorno
    cor_borda = Image.new("RGBA", (w, h), ImageColor.getrgb(cfg["contorno"]["cor"]) + (255,))
    cor_borda.putalpha(borda)
    camada.alpha_composite(cor_borda)
    # preenchimento com a rampa entre o topo e a base das letras
    rampa = _rampa(y1 - y0, estilo["rampa"])
    cheia = np.zeros((h, w, 3), dtype=np.float32)
    cheia[:] = rampa[0]
    cheia[margem : margem + (y1 - y0)] = rampa[:, None, :]
    cheia[margem + (y1 - y0) :] = rampa[-1]
    preenchimento = Image.fromarray(cheia.astype(np.uint8), "RGB").convert("RGBA")
    preenchimento.putalpha(mascara)
    camada.alpha_composite(preenchimento)
    return camada, margem, y1 - y0


def bloco(ficha: dict, linhas: list[dict], largura: int, altura: int) -> tuple[Image.Image, int]:
    """Bloco de texto alinhado à esquerda, do maior corpo cujas letras cabem em largura x altura.

    Devolve a imagem e a folga P em volta da caixa: contorno e sombra podem
    passar da caixa, então a imagem tem P a mais de cada lado e deve ser
    colada em (x - P, y - P).
    """
    cfg = ficha["texto"]
    caminho_fonte = RAIZ / cfg["fonte"]
    pesos = [l.get("peso", 1.0) for l in linhas]
    vao = cfg.get("vao_entre_linhas", 0.14)   # fração do corpo

    def montar(corpo: int) -> list[tuple[Image.Image, int, int]]:
        saida = []
        for l, p in zip(linhas, pesos):
            texto = l["texto"].upper() if cfg.get("caixa_alta") else l["texto"]
            fonte = ImageFont.truetype(str(caminho_fonte), max(8, round(corpo * p)))
            saida.append(_linha(texto, fonte, cfg["estilos"][l["estilo"]], cfg))
        return saida

    def medidas(corpo: int, partes) -> tuple[int, int]:
        larg = max(img.width - 2 * m for img, m, _ in partes)
        alt = sum(a for _, _, a in partes) + round(vao * corpo) * (len(partes) - 1)
        return larg, alt

    lo, hi = 8, altura
    while lo < hi:  # busca binária do maior corpo que cabe
        meio = (lo + hi + 1) // 2
        w, h = medidas(meio, montar(meio))
        if w <= largura and h <= altura:
            lo = meio
        else:
            hi = meio - 1
    corpo = lo
    partes = montar(corpo)
    _, alt_total = medidas(corpo, partes)
    folga = max(m for _, m, _ in partes)
    saida = Image.new("RGBA", (largura + 2 * folga, altura + 2 * folga), (0, 0, 0, 0))
    y = (altura - alt_total) // 2
    for img, m, a in partes:
        saida.alpha_composite(img, (folga - m, folga + y - m))
        y += a + round(vao * corpo)
    return saida, folga
