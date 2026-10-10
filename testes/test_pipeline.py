import json

import pytest
import yaml
from psd_tools import PSDImage

import pipeline
from motor import ficha as F
from motor.portao import ParteRecusada, Portao

FICHA = "fichas/arara/ficha-v1.0.yaml"


def test_rascunho_gera_psd_com_as_camadas_da_ficha(tmp_path):
    rel = pipeline.rodar(FICHA, ["promo"], "rascunho", None, tmp_path)
    peca = rel["pecas"][0]
    assert peca["qa_ok"], peca["qa"]
    assert rel["gasto_usd"] == 0
    psd = PSDImage.open(tmp_path / "arara" / "promo-turista-rascunho.psd")
    ordem = [c["id"] for c in F.carregar(FICHA)["camadas"]]
    assert [l.name for l in psd] == ordem
    assert psd.size == (1867, 842)
    assert json.loads((tmp_path / "arara" / "relatorio-rascunho-turista.json").read_text())["versao"] == "1.0"


def test_registro_usa_as_partes_escolhidas(tmp_path):
    rel = pipeline.rodar(FICHA, ["promo"], "registro", "turista", tmp_path)
    usados = {l["arquivo"] for l in rel["partes"]}
    assert usados == {"cena-promo-bruto.png", "mascote-turista-v2-bruto.png"}
    assert rel["pecas"][0]["qa_ok"], rel["pecas"][0]["qa"]


def test_registro_recusa_parte_de_outra_receita(tmp_path):
    f = F.carregar(FICHA)
    f["partes"]["cena"]["prompt"] = "a completely different scene"
    with pytest.raises(ParteRecusada, match="prompt"):
        Portao("registro").parte(f, "cena", "promo")


def test_ficha_com_temas_poe_o_entorno_no_psd(tmp_path):
    rel = pipeline.rodar("fichas/arara/ficha-v1.1.yaml", ["home"], "rascunho", "telegram", tmp_path)
    assert rel["tema"] == "telegram" and rel["figurino"] == "turista"
    assert rel["pecas"][0]["qa_ok"], rel["pecas"][0]["qa"]
    psd = PSDImage.open(tmp_path / "arara" / "home-telegram-rascunho.psd")
    assert [l.name for l in psd][:4] == ["cena", "escurecimento", "entorno", "mascote"]


def test_proposta_v12_poe_a_frente_por_cima_do_mascote(tmp_path):
    rel = pipeline.rodar("fichas/arara/ficha-v1.2.yaml", ["promo"], "rascunho", "reembolso", tmp_path)
    assert rel["pecas"][0]["qa_ok"], rel["pecas"][0]["qa"]
    psd = PSDImage.open(tmp_path / "arara" / "promo-reembolso-rascunho.psd")
    nomes = [l.name for l in psd]
    assert nomes.index("frente") == nomes.index("mascote") + 1
