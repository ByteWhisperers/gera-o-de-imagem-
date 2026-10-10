from pathlib import Path

from ferramentas import juntar_grafos as J  # noqa: E402
from motor import ficha as F  # noqa: E402
from motor import grafo as G  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
TELEGRAM = G.carregar(RAIZ / "fichas/arara/grafos/promo-telegram.json")
FICHA = F.carregar(RAIZ / "fichas/arara/ficha-v1.1.yaml")


def test_junta_medidas_por_formato_com_a_origem_de_cada_numero():
    r = J.juntar([TELEGRAM], FICHA)
    promo = r["por_formato"]["promo"]
    assert promo["pecas"] == 1 and promo["linhas_por_peca"]["mediana"] == 4
    assert promo["texto"]["pecas"] == ["promo-telegram"]
    assert 0 < promo["logo"]["x"]["mediana"] < 0.1
    assert len(promo["L_fundo_por_decimo_de_W"]) == 10
    assert set(r["cores_do_texto"]) == {"branco", "dourado"}
    assert len(r["cores_do_texto"]["dourado"]["dE00_ficha_x_medido"]) == 3
