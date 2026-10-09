"""Tira o fundo liso de estúdio de uma parte gerada (sem custo, sem IA).

O prompt das partes transparentes pede "plain light grey studio background".
Aqui o fundo é tudo o que for claro, pouco saturado e ligado à borda da
imagem. O que é cinza mas fica dentro do personagem (um bico cinza, por
exemplo) não encosta na borda e por isso fica.

Há três métodos, escolhidos por parte (a receita da parte diz qual):

- liso: o fundo claro e cinza ligado à borda (bom para FLUX, que obedece ao
  "plain light grey studio background").
- cor_da_borda: tudo o que tem a cor mediana da borda e encosta nela. Serve
  para fundos em degradê, como os do SD-Turbo, quando os objetos são soltos.
- modelo: um modelo de recorte local e gratuito (rembg, isnet-general-use).
  Serve para personagens sobre fundo texturizado. Precisa de `pip install
  rembg[cpu]`; sem ele, cai em cor_da_borda.
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
    return _ligado_a_borda((mx >= brilho_min) & (saturacao <= saturacao_max))


def mascara_cor_da_borda(im: Image.Image, tolerancia: float = 80, saturacao_max: float = 0.3) -> np.ndarray:
    rgb = np.asarray(im.convert("RGB").filter(ImageFilter.GaussianBlur(2)), dtype=np.float32)
    cor = np.median(np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]]), axis=0)
    mx, mn = rgb.max(axis=2), rgb.min(axis=2)
    saturacao = (mx - mn) / np.maximum(mx, 1)
    candidato = (np.sqrt(((rgb - cor) ** 2).sum(axis=2)) <= tolerancia) & (saturacao <= saturacao_max)
    return _ligado_a_borda(candidato)


def _ligado_a_borda(candidato: np.ndarray) -> np.ndarray:
    regiao = np.zeros_like(candidato)
    regiao[0, :], regiao[-1, :], regiao[:, 0], regiao[:, -1] = (
        candidato[0, :], candidato[-1, :], candidato[:, 0], candidato[:, -1])
    while True:
        nova = _dilatar(regiao) & candidato
        if np.array_equal(nova, regiao):
            return regiao
        regiao = nova


def _com_alfa(im: Image.Image, fundo: np.ndarray, suavizar: float) -> Image.Image:
    alfa = Image.fromarray(np.where(fundo, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(suavizar))
    saida = im.convert("RGBA")
    saida.putalpha(alfa)
    return saida


def remover_fundo_liso(im: Image.Image, suavizar: float = 1.2) -> Image.Image:
    return _com_alfa(im, mascara_de_fundo(im), suavizar)


_sessoes: dict = {}


def remover_fundo(im: Image.Image, metodo: str = "liso") -> Image.Image:
    """Tira o fundo pelo método da receita da parte."""
    if metodo == "liso":
        return remover_fundo_liso(im)
    if metodo == "cor_da_borda":
        return _com_alfa(im, mascara_cor_da_borda(im), 1.2)
    if metodo == "modelo":
        try:
            from rembg import new_session, remove
        except ImportError:
            return remover_fundo(im, "cor_da_borda")
        if "isnet" not in _sessoes:
            _sessoes["isnet"] = new_session("isnet-general-use")
        return remove(im.convert("RGB"), session=_sessoes["isnet"])
    raise ValueError(f"método de recorte desconhecido: {metodo}")


def recortar_conteudo(im: Image.Image) -> Image.Image:
    """Corta as margens transparentes em volta do personagem."""
    caixa = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    return im.crop(caixa) if caixa else im
