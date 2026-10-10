import copy
import json
from pathlib import Path

import pytest

from motor import grafo as G

RAIZ = Path(__file__).resolve().parent.parent
TELEGRAM = RAIZ / "fichas/arara/grafos/promo-telegram.json"


def test_grafo_do_telegram_carrega_com_partes_isoladas_e_relacoes():
    g = G.carregar(TELEGRAM)
    assert g["estado"] in ("proposta", "aprovada")
    tipos = {n["tipo"] for n in g["nos"]}
    assert {"fundo", "personagem", "objeto", "texto", "logo", "efeito"} <= tipos
    rels = {a["rel"] for a in g["arestas"]}
    assert {"segura", "tema_liga", "contraste", "fica_sobre"} <= rels
    for n in g["nos"]:
        if "mascara" in n:
            assert (G.pasta(g) / n["mascara"]).exists(), n["id"]
    assert G.camadas_geradas(g) == ["cena", "entorno", "mascote"]       # de baixo para cima


def test_texto_da_referencia_nao_e_copiado_para_o_grafo():
    g = G.carregar(TELEGRAM)
    textos = [n for n in g["nos"] if n["tipo"] == "texto"]
    assert textos and all("não copiado" in n["conteudo"] for n in textos)


def test_mascaras_das_camadas_nao_se_sobrepoem():
    g = G.carregar(TELEGRAM)
    mascote, entorno = G.mascara_camada(g, "mascote"), G.mascara_camada(g, "entorno")
    assert mascote.mean() > 0.15 and entorno.mean() > 0.01
    assert not (mascote & entorno).any()


def test_layout_medido_traz_texto_e_logo():
    lay = G.layout_medido(G.carregar(TELEGRAM))
    assert set(lay) == {"texto", "logo"}
    assert 0 < lay["texto"]["x"] < 0.1 and lay["texto"]["w"] > 0.3


@pytest.mark.parametrize("estrago, erro", [
    (lambda g: g["arestas"].append({"de": "mascote", "rel": "segura", "para": "nada"}), "não existe"),
    (lambda g: g["arestas"].append({"de": "mascote", "rel": "abraça", "para": "cena"}), "desconhecida"),
    (lambda g: g["nos"][0].update(caixa=[0.5, 0.5, 0.9, 0.2]) or g["nos"][0].update(caixa=[1.2, 0, 0.1, 0.1]), "fora"),
    (lambda g: g["nos"].append(dict(g["nos"][0])), "repetidos"),
])
def test_grafo_estragado_e_recusado(estrago, erro):
    g = json.loads(TELEGRAM.read_text(encoding="utf-8"))
    estrago(g)
    with pytest.raises(G.GrafoInvalido, match=erro):
        G.conferir(copy.deepcopy(g))


def test_rotulo_solto_nao_estica_o_bloco_de_texto():
    g = copy.deepcopy(G.carregar(TELEGRAM))
    antes = G.layout_medido(g)["texto"]
    g["nos"].append({"id": "rotulo_nivel2", "tipo": "texto", "papel": "rotulo", "z": 6, "camada_psd": "texto",
                     "caixa": [0.7, 0.9, 0.05, 0.03]})
    assert G.layout_medido(g)["texto"] == antes


def test_camada_que_a_ficha_nao_conhece_fica_de_fora_quando_pedido():
    g = copy.deepcopy(G.carregar(TELEGRAM))
    moedas = G.no(g, "moedas")
    g["nos"].append({**moedas, "id": "folhagem", "camada_psd": "frente", "z": 5})
    assert G.camadas_geradas(g) == ["cena", "entorno", "mascote", "frente"]
    assert G.camadas_geradas(g, ["cena", "mascote", "entorno"]) == ["cena", "entorno", "mascote"]
