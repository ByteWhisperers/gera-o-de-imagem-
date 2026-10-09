import pytest
import yaml

from motor import ficha as F

FICHA = "fichas/arara/ficha-v1.0.yaml"


def test_ficha_da_arara_carrega():
    f = F.carregar(FICHA)
    assert f["marca"] == "arara"
    assert F.tamanho(f, "home") == (2048, 682)


def test_prompt_troca_o_figurino():
    f = F.carregar(FICHA)
    turista = F.prompt_da_parte(f, "mascote", "turista")
    realeza = F.prompt_da_parte(f, "mascote", "realeza")
    assert "straw hat" in turista and "crown" not in turista
    assert "crown" in realeza
    assert "{figurino}" not in turista


def test_ficha_sem_layout_para_um_formato_e_recusada(tmp_path):
    dados = yaml.safe_load(open(FICHA, encoding="utf-8"))
    dados["formatos"]["story"] = {"largura": 1080, "altura": 1920}
    caminho = tmp_path / "ficha.yaml"
    caminho.write_text(yaml.safe_dump(dados, allow_unicode=True), encoding="utf-8")
    with pytest.raises(F.FichaInvalida, match="story"):
        F.carregar(caminho)
