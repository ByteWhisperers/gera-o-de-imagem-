"""Curvas que levam as cores de uma parte para as da referência.

Para cada canal (vermelho, verde, azul), compara os quantis da parte gerada com
os da mesma parte na referência e devolve os pontos de uma camada de ajuste
Curvas do PhotoCraft (0 a 255). É o "Combinar Cor" feito por medida, mas sem
mexer nos pixels: a curva fica numa camada de ajuste presa à parte, que o dono
ou um agente pode afinar ou desligar.

A posição não precisa bater: só a distribuição de cores conta, então serve
também para um mascote novo, gerado do zero.
"""

from __future__ import annotations

import numpy as np

QUANTIS = (0.02, 0.15, 0.35, 0.5, 0.65, 0.85, 0.98)
CANAIS = ("red", "green", "blue")


def curvas_para_casar(atual: np.ndarray, m_atual: np.ndarray, ref: np.ndarray, m_ref: np.ndarray,
                      quantis: tuple[float, ...] = QUANTIS, forca: float = 1.0) -> dict[str, list[list[int]]]:
    """Pontos [entrada, saída] por canal. `forca` 0 deixa como está, 1 casa por inteiro."""
    if not m_atual.any() or not m_ref.any():
        raise ValueError("a parte ou a referência não tem pixels na máscara")
    forca = float(np.clip(forca, 0.0, 1.0))
    curvas = {}
    for c, nome in enumerate(CANAIS):
        de = np.quantile(atual[..., c][m_atual].astype(np.float64), quantis)
        para = np.quantile(ref[..., c][m_ref].astype(np.float64), quantis)
        para = de + forca * (para - de)
        curvas[nome] = _pontos(de, para)
    return curvas


def _pontos(de: np.ndarray, para: np.ndarray) -> list[list[int]]:
    """Curva monótona de 0 a 255, com entradas a pelo menos 4 níveis umas das outras.

    As pontas seguem os quantis extremos com inclinação 1, para a curva não dar um salto
    entre o último quantil e o branco (ou entre o preto e o primeiro quantil).
    """
    meio = []
    for i, o in zip(np.round(de).astype(int), np.round(para).astype(int)):
        i, o = int(np.clip(i, 0, 255)), int(np.clip(o, 0, 255))
        anterior = meio[-1] if meio else [0, 0]
        if i - anterior[0] < 4 or 255 - i < 4:
            continue
        meio.append([i, max(o, anterior[1])])
    if not meio:
        return [[0, 0], [255, 255]]
    inicio = [0, int(np.clip(meio[0][1] - meio[0][0], 0, meio[0][1]))]
    fim = [255, int(np.clip(meio[-1][1] + 255 - meio[-1][0], meio[-1][1], 255))]
    return [inicio, *meio, fim]


def aplicar(rgb: np.ndarray, curvas: dict[str, list[list[int]]]) -> np.ndarray:
    """Aplica as curvas por interpolação linear (só para estimar antes de mandar ao PhotoCraft)."""
    saida = rgb.astype(np.float64).copy()
    for c, nome in enumerate(CANAIS):
        p = np.array(curvas[nome], np.float64)
        saida[..., c] = np.interp(saida[..., c], p[:, 0], p[:, 1])
    return np.clip(np.round(saida), 0, 255).astype(np.uint8)
