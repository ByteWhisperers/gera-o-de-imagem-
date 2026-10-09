import numpy as np
from PIL import Image, ImageDraw

from motor.recorte import recortar_conteudo, remover_fundo_liso


def test_fundo_cinza_sai_e_cinza_interno_fica():
    im = Image.new("RGB", (200, 200), (205, 205, 205))
    d = ImageDraw.Draw(im)
    d.ellipse((40, 40, 160, 160), fill=(210, 30, 20))
    d.rectangle((90, 90, 110, 110), fill=(200, 200, 200))  # "bico" cinza dentro do corpo
    a = np.asarray(remover_fundo_liso(im, suavizar=0).getchannel("A"))
    assert a[5, 5] == 0          # fundo
    assert a[100, 100] == 255    # cinza interno, longe da borda
    assert a[60, 100] == 255     # corpo


def test_recorta_as_margens():
    im = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle((20, 30, 59, 79), fill=(255, 0, 0, 255))
    assert recortar_conteudo(im).size == (40, 50)
