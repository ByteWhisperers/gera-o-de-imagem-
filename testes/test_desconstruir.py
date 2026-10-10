import numpy as np
import pytest

pytest.importorskip("skimage")

from ferramentas import desconstruir as D  # noqa: E402


def test_contorno_aproximado_encaixa_na_borda_real():
    yy, xx = np.mgrid[:200, :300]
    disco = ((xx - 150) ** 2 + (yy - 100) ** 2) < 60 ** 2
    rgb = np.where(disco[..., None], [220, 40, 20], [20, 60, 30]).astype(np.float32)
    rgb += np.random.default_rng(1).normal(0, 6, rgb.shape)
    # contorno do agente: 4 px maior que o disco, como um contorno feito a olho
    aproximada = D.mascara_elipse([86 / 300, 36 / 200, 128 / 300, 128 / 200], 300, 200)
    encaixada = D.encaixar_na_borda(rgb.clip(0, 255), aproximada)
    iou = (encaixada & disco).sum() / (encaixada | disco).sum()
    assert iou > 0.95
    assert (aproximada & disco).sum() / (aproximada | disco).sum() < iou


def test_buraco_e_preenchido_com_as_cores_de_volta():
    rgb = np.zeros((80, 120, 3), np.float32)
    rgb[:] = [30, 90, 40]
    rgb[30:50, 40:80] = [255, 255, 255]                                     # "texto" branco
    buraco = np.zeros((80, 120), bool)
    buraco[28:52, 38:82] = True
    cheio = D.preencher_buraco(rgb, buraco, reducao=2)
    assert np.abs(cheio[buraco] - [30, 90, 40]).max() < 12
    assert (cheio[~buraco] == rgb[~buraco]).all()
