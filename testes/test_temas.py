import pytest
import yaml

from motor import ficha as F

FICHA = "fichas/arara/ficha-v1.1.yaml"


def test_tema_muda_figurino_o_que_segura_e_o_entorno():
    f = F.carregar(FICHA)
    insta = F.prompt_da_parte(f, "mascote", "instagram")
    convite = F.prompt_da_parte(f, "mascote", "convite")
    assert "straw hat" in insta and "smartphone" in insta
    assert "crown" in convite and "smartphone" not in convite
    assert "paper plane" in F.prompt_da_parte(f, "entorno", "telegram")
    assert "{" not in insta


def test_sem_tema_usa_o_tema_padrao():
    f = F.carregar(FICHA)
    assert F.resolver_tema(f)["nome"] == f["tema_padrao"]


def test_tema_desconhecido_e_recusado():
    with pytest.raises(F.FichaInvalida, match="tema"):
        F.resolver_tema(F.carregar(FICHA), "tiktok")


def test_tema_com_figurino_inexistente_e_recusado(tmp_path):
    dados = yaml.safe_load(open(FICHA, encoding="utf-8"))
    dados["temas"]["convite"]["figurino"] = "pirata"
    caminho = tmp_path / "ficha.yaml"
    caminho.write_text(yaml.safe_dump(dados, allow_unicode=True), encoding="utf-8")
    with pytest.raises(F.FichaInvalida, match="pirata"):
        F.carregar(caminho)


def test_linhas_de_texto_do_tema_ou_neutras():
    f = F.carregar(FICHA)
    assert [l["texto"] for l in F.linhas_de_texto(f, "instagram")][1] == "INSTAGRAM"
    assert F.linhas_de_texto(f, "convite") == f["texto"]["exemplo"]
