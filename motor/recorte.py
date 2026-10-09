"""Tira o fundo liso de estúdio de uma parte gerada (sem custo, sem IA).

O prompt das partes transparentes pede "plain light grey studio background".
Aqui o fundo é tudo o que for claro, pouco saturado e ligado à borda da
imagem. O que é cinza mas fica dentro do personagem (um bico cinza, por
exemplo) não encosta na borda e por isso fica.

Quando o recorte local não bastar, o operador pode trocar por um modelo de
recorte (BiRefNet, por exemplo) pelo portão de geração.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter


def _dilatar(m: np.ndarray) -> np.ndarray:
    d = m.copy()
    d[1:, :] |= m[:-1, :]
    d[:-1, :] |= m[1:, :]
    d[:, 1:] |= m[:, :-1]
    d[:, :-1] |= m[:, 1:]
    return d


def mascara_de_fundo(im: Image.Image, brilho_min: float = 150, saturacao_max: float = 0.14) -> np.ndarray:
    rgb = np.asarray(im.convert("RGB"), dtype=np.float32)
    mx, mn = rgb.max(axis=2), rgb.min(axis=2)
    saturacao = (mx - mn) / np.maximum(mx, 1)
    candidato = (mx >= brilho_min) & (saturacao <= saturacao_max)
    regiao = np.zeros_like(candidato)
    regiao[0, :], regiao[-1, :], regiao[:, 0], regiao[:, -1] = (
        candidato[0, :], candidato[-1, :], candidato[:, 0], candidato[:, -1])
    while True:
        nova = _dilatar(regiao) & candidato
        if np.array_equal(nova, regiao):
            return regiao
        regiao = nova


def remover_fundo_liso(im: Image.Image, suavizar: float = 1.2) -> Image.Image:
    fundo = mascara_de_fundo(im)
    alfa = Image.fromarray(np.where(fundo, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(suavizar))
    saida = im.convert("RGBA")
    saida.putalpha(alfa)
    return saida


def recortar_conteudo(im: Image.Image) -> Image.Image:
    """Corta as margens transparentes em volta do personagem."""
    caixa = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    return im.crop(caixa) if caixa else im
