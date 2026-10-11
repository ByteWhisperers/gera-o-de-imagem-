"""Curvas que levam as cores de uma parte para as da referência.

Para cada canal (vermelho, verde, azul), compara os quantis da parte gerada com
os da mesma parte na referência e devolve os pontos de uma camada de ajuste
Curvas do PhotoCraft (0 a 255). É o "Combinar Cor" feito por medida, mas sem
mexer nos pixels: a curva fica numa camada de ajuste presa à parte, que o dono
ou um agente pode afinar ou desligar.

A posição não precisa bater: só a distribuição de cores conta, então serve
também para um mascote novo, gerado do zero.

A inclinação de cada trecho da curva fica entre 0,5 e 2 (ajustável): quando a parte
e a referência mostram coisas diferentes (moedas soltas contra um ícone), a curva sem
limite dá degrau e pinta borda de outra cor.

`curva_de_luz` faz o mesmo só com a luz (um canal, para uma Curvas em modo
Luminosidade): acerta claro e escuro sem mexer na cor nem na saturação.
"""

from __future__ import annotations

import numpy as np

QUANTIS = (0.02, 0.15, 0.35, 0.5, 0.65, 0.85, 0.98)
QUANTIS_LUZ = (0.05, 0.25, 0.5, 0.75, 0.95)
CANAIS = ("red", "green", "blue")
INCLINACAO = (0.5, 2.0)


def curvas_para_casar(atual: np.ndarray, m_atual: np.ndarray, ref: np.ndarray, m_ref: np.ndarray,
                      quantis: tuple[float, ...] = QUANTIS, forca: float = 1.0,
                      inclinacao: tuple[float, float] = INCLINACAO) -> dict[str, list[list[int]]]:
    """Pontos [entrada, saída] por canal. `forca` 0 deixa como está, 1 casa por inteiro."""
    if not m_atual.any() or not m_ref.any():
        raise ValueError("a parte ou a referência não tem pixels na máscara")
    forca = float(np.clip(forca, 0.0, 1.0))
    curvas = {}
    for c, nome in enumerate(CANAIS):
        de = np.quantile(atual[..., c][m_atual].astype(np.float64), quantis)
        para = np.quantile(ref[..., c][m_ref].astype(np.float64), quantis)
        para = de + forca * (para - de)
        curvas[nome] = _pontos(de, para, inclinacao)
    return curvas


def luminancia(rgb: np.ndarray) -> np.ndarray:
    rgb = rgb.astype(np.float64)
    return 0.30 * rgb[..., 0] + 0.59 * rgb[..., 1] + 0.11 * rgb[..., 2]


def curva_de_luz(atual: np.ndarray, m_atual: np.ndarray, ref: np.ndarray, m_ref: np.ndarray,
                 quantis: tuple[float, ...] = QUANTIS_LUZ, forca: float = 1.0,
                 inclinacao: tuple[float, float] = INCLINACAO) -> list[list[int]]:
    """Pontos [entrada, saída] da curva de luz (canal composto, para usar em Luminosidade)."""
    if not m_atual.any() or not m_ref.any():
        raise ValueError("a parte ou a referência não tem pixels na máscara")
    forca = float(np.clip(forca, 0.0, 1.0))
    de = np.quantile(luminancia(atual)[m_atual], quantis)
    para = np.quantile(luminancia(ref)[m_ref], quantis)
    return _pontos(de, de + forca * (para - de), inclinacao)


def _pontos(de: np.ndarray, para: np.ndarray, inclinacao: tuple[float, float] = INCLINACAO) -> list[list[int]]:
    """Curva monótona de 0 a 255, com entradas a pelo menos 4 níveis umas das outras.

    As pontas seguem os quantis extremos com inclinação 1, para a curva não dar um salto
    entre o último quantil e o branco (ou entre o preto e o primeiro quantil). Cada trecho
    fica com inclinação entre `inclinacao[0]` e `inclinacao[1]`.
    """
    lo, hi = float(inclinacao[0]), float(inclinacao[1])
    if not 0 <= lo <= 1 <= hi:
        raise ValueError(f"inclinação {inclinacao}: o mínimo vai de 0 a 1 e o máximo é 1 ou mais")
    brutos = []
    for i, o in zip(np.round(de).astype(int), np.round(para).astype(int)):
        i, o = int(np.clip(i, 0, 255)), int(np.clip(o, 0, 255))
        if i - (brutos[-1][0] if brutos else 0) < 4 or 255 - i < 4:
            continue
        brutos.append([i, o])
    if not brutos:
        return [[0, 0], [255, 255]]
    i0, o0 = brutos[0]
    pontos = [[0, int(np.clip(o0 - i0, 0, 255))]]
    for i, o in brutos:
        pi, po = pontos[-1]
        dx = i - pi
        o = int(np.clip(o, np.ceil(po + lo * dx), np.floor(po + hi * dx)))
        pontos.append([i, int(np.clip(o, po, 255))])
    pi, po = pontos[-1]
    dx = 255 - pi
    fim = int(np.clip(po + dx, np.ceil(po + lo * dx), np.floor(po + hi * dx)))
    pontos.append([255, int(np.clip(fim, po, 255))])
    return pontos


def aplicar(rgb: np.ndarray, curvas: dict[str, list[list[int]]]) -> np.ndarray:
    """Aplica as curvas por interpolação linear (só para estimar antes de mandar ao PhotoCraft)."""
    saida = rgb.astype(np.float64).copy()
    for c, nome in enumerate(CANAIS):
        p = np.array(curvas[nome], np.float64)
        saida[..., c] = np.interp(saida[..., c], p[:, 0], p[:, 1])
    return np.clip(np.round(saida), 0, 255).astype(np.uint8)
