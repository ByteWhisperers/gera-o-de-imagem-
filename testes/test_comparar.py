from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from motor import comparar as CMP
from motor import grafo as G

RAIZ = Path(__file__).resolve().parent.parent
GRAFO = G.carregar(RAIZ / "fichas/arara/grafos/promo-telegram.json")


@pytest.mark.parametrize("lab1, lab2, esperado", [      # pares de teste de Sharma, Wu e Dalal (2005)
    ([50, 2.6772, -79.7751], [50, 0, -82.7485], 2.0425),
    ([50, 2.5, 0], [50, 0, -2.5], 4.3065),
    ([50, 2.5, 0], [73, 25, -18], 27.1492),
    ([60.2574, -34.0099, 36.2677], [60.4626, -34.1751, 39.4387], 1.2644),
])
def test_ciede2000_bate_com_a_tabela_de_referencia(lab1, lab2, esperado):
    assert CMP.de2000(np.array(lab1), np.array(lab2)) == pytest.approx(esperado, abs=1e-4)


def _camadas_da_referencia(ref):
    saida = {}
    for camada in G.camadas_geradas(GRAFO):
        if camada == "cena":
            saida[camada] = (np.dstack([ref, np.full(ref.shape[:2], 255, np.uint8)]), 0, 0)
        else:
            m = G.mascara_camada(GRAFO, camada)
            saida[camada] = (np.dstack([ref, (m * 255).astype(np.uint8)]), 0, 0)
    return saida


def test_referencia_contra_ela_mesma_da_nota_perfeita():
    ref = np.asarray(Image.open(RAIZ / GRAFO["referencia"]).convert("RGB"))
    notas = CMP.medir(GRAFO, Image.fromarray(ref), _camadas_da_referencia(ref))
    assert notas["peca"]["dE00"] < 0.01 and notas["peca"]["ssim"] > 0.999
    for camada in ("entorno", "mascote"):
        assert notas[camada]["dE00"] < 0.01 and notas[camada]["cobertura"] == 1.0
        assert notas[camada]["leitura"] == "igual a olho nu"


def test_elipse_vermelha_no_lugar_da_arara_reprova():
    ref = np.asarray(Image.open(RAIZ / GRAFO["referencia"]).convert("RGB"))
    W, H = GRAFO["tamanho_px"]
    camadas = _camadas_da_referencia(ref)
    elipse = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(elipse).ellipse((W * 0.62, H * 0.2, W * 0.85, H), fill=(212, 28, 9, 255))
    camadas["mascote"] = (np.asarray(elipse), 0, 0)
    final = Image.fromarray(ref).convert("RGBA")
    final.alpha_composite(elipse)
    notas = CMP.medir(GRAFO, final, camadas)
    assert notas["mascote"]["dE00"] > 20 and notas["mascote"]["cobertura"] < 0.6
    assert notas["mascote"]["leitura"] == "muito diferente"
    assert notas["peca"]["dE00"] > notas["entorno"]["dE00"]


def test_borda_opaca_acusa_corte_reto_mas_nao_a_borda_da_peca():
    quadrado = np.zeros((40, 40, 4), np.uint8)
    quadrado[..., 3] = 255
    assert CMP.borda_opaca(quadrado, 100, 100, 400, 300) == 1.0          # solto no meio: corte reto
    redondo = np.zeros((40, 40, 4), np.uint8)
    yy, xx = np.mgrid[:40, :40]
    redondo[..., 3] = (((xx - 19.5) ** 2 + (yy - 19.5) ** 2) < 18 ** 2) * 255
    assert CMP.borda_opaca(redondo, 100, 100, 400, 300) == 0.0
    meio = redondo[:30]                                                  # cortado pela base da peça
    assert (meio[-1, :, 3] > 0).any()
    assert CMP.borda_opaca(meio, 100, 270, 400, 300) == 0.0
