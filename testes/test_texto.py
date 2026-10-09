import numpy as np

from motor import ficha as F
from motor import texto as T


def test_bloco_cabe_na_caixa():
    f = F.carregar("fichas/arara/ficha-v1.0.yaml")
    im, folga = T.bloco(f, f["texto"]["exemplo"], 600, 300)
    assert im.size == (600 + 2 * folga, 300 + 2 * folga)
    letras = np.asarray(im.getchannel("A")) > 250
    ys, xs = np.nonzero(letras)
    # letras e contorno ficam dentro da caixa; só o contorno pode passar um pouco
    tol = folga // 2
    assert xs.min() >= folga - tol and xs.max() <= folga + 600 + tol
    assert ys.min() >= folga - tol and ys.max() <= folga + 300 + tol


def test_rampa_vai_do_topo_a_base():
    r = T._rampa(10, [[0.0, "#ffffff"], [1.0, "#000000"]])
    assert tuple(r[0]) == (255, 255, 255) and tuple(r[-1]) == (0, 0, 0)
