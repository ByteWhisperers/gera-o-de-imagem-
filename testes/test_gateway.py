import base64
import io
import json
import shutil
from pathlib import Path

import pytest
import yaml
from PIL import Image

from motor import ficha as F
from motor import gateway as G
from motor import portao as P

RAIZ = Path(__file__).resolve().parent.parent
FICHA = "fichas/arara/ficha-v1.2.yaml"


def _png(w, h, cor="red"):
    dados = io.BytesIO()
    Image.new("RGB", (w, h), cor).save(dados, "PNG")
    return dados.getvalue()


def test_tamanho_do_gateway_escolhe_a_proporcao_mais_parecida():
    assert G.tamanho_do_gateway(1024, 320) == (1280, 720)
    assert G.tamanho_do_gateway(512, 704) == (768, 1024)
    assert G.tamanho_do_gateway(768, 512) == (1024, 768)


def test_ajustar_corta_o_centro_sem_diminuir():
    im = G.ajustar(Image.new("RGB", (1280, 720)), 1024, 320)
    assert im.size == (1280, 400)
    im = G.ajustar(Image.new("RGB", (768, 1024)), 512, 704)
    assert im.size == (745, 1024)


def test_gerar_pede_espera_o_job_e_baixa_a_imagem():
    chamadas = []

    def abrir(pedido):
        url = pedido if isinstance(pedido, str) else pedido.full_url
        chamadas.append(url)
        if url.endswith("/v1/images"):
            assert pedido.headers["Authorization"] == "Bearer k"
            corpo = json.loads(pedido.data)
            assert corpo["size"] == "1280x720" and corpo["seed"] == 7 and corpo["model"] == "rapido"
            return io.BytesIO(json.dumps({"id": "img_1", "status": "running"}).encode())
        if url.endswith("/v1/jobs/img_1"):
            return io.BytesIO(json.dumps({"id": "img_1", "status": "succeeded", "cost_usd": 0.005,
                                          "images": ["https://cdn/x.png"]}).encode())
        return io.BytesIO(_png(1280, 720))

    im, custo = G.gerar("http://gw", "k", "rapido", "p", 1024, 320, 7, intervalo=0, abrir=abrir)
    assert im.size == (1280, 400) and custo == 0.005
    assert chamadas == ["http://gw/v1/images", "http://gw/v1/jobs/img_1", "https://cdn/x.png"]


def test_gerar_aceita_data_uri_e_avisa_falha():
    uri = "data:image/png;base64," + base64.b64encode(_png(1024, 768)).decode()
    pronto = {"id": "a", "status": "succeeded", "images": [uri]}
    im, custo = G.gerar("http://gw", "k", "rapido", "p", 768, 512, 1,
                        abrir=lambda pedido: io.BytesIO(json.dumps(pronto).encode()))
    assert im.size == (1024, 683) and custo is None
    falhou = {"id": "a", "status": "failed", "error": "sem crédito", "images": []}
    with pytest.raises(G.GatewayFalhou, match="sem crédito"):
        G.gerar("http://gw", "k", "rapido", "p", 768, 512, 1,
                abrir=lambda pedido: io.BytesIO(json.dumps(falhou).encode()))


def test_chave_vem_do_ambiente(monkeypatch):
    monkeypatch.delenv("GATEWAY_CHAVE", raising=False)
    with pytest.raises(G.GatewayFalhou, match="GATEWAY_CHAVE"):
        G.chave()


@pytest.fixture
def raiz(tmp_path, monkeypatch):
    shutil.copytree(RAIZ / "integracoes", tmp_path / "integracoes")
    (tmp_path / "partes" / "arara").mkdir(parents=True)
    monkeypatch.setattr(P, "RAIZ", tmp_path)
    monkeypatch.setenv("GATEWAY_CHAVE", "k")
    return tmp_path


def test_provedor_gateway_exige_teto(raiz):
    with pytest.raises(P.TetoDeGasto, match="--teto"):
        P.Portao("gateway").parte(F.carregar(FICHA), "mascote", "promo", "telegram")


def test_provedor_gateway_registra_a_parte_com_custo(raiz, monkeypatch):
    pedidos = []

    def gerar(url, chave, modelo, prompt, largura, altura, semente, espera_max):
        pedidos.append((url, modelo, largura, altura))
        return Image.new("RGB", (745, 1024)), 0.005

    monkeypatch.setattr(P, "gerar_no_gateway", gerar)
    f = F.carregar(FICHA)
    portao = P.Portao("gateway", teto_usd=0.01)
    im = portao.parte(f, "mascote", "promo", "telegram")
    assert im.size == (745, 1024) and pedidos == [("http://127.0.0.1:8000", "rapido", 512, 704)]
    entrada = yaml.safe_load((raiz / "partes/arara/registro.yaml").read_text())["entradas"][0]
    assert entrada["modelo"] == "gateway/rapido" and entrada["custo_usd"] == 0.005
    assert entrada["prompt"] == F.prompt_da_parte(f, "mascote", "telegram") and entrada["recorte"] == "modelo"
    assert portao.gasto_novo_usd == 0.005 and portao.gasto_usd == 0.005
    # a mesma receita sai da biblioteca, sem gastar de novo
    P.Portao("gateway", teto_usd=0.01).parte(f, "mascote", "promo", "telegram")
    assert len(pedidos) == 1


def test_provedor_gateway_para_no_teto(raiz, monkeypatch):
    monkeypatch.setattr(P, "gerar_no_gateway", lambda *a: (Image.new("RGB", (8, 8)), 0.005))
    f = F.carregar(FICHA)
    portao = P.Portao("gateway", teto_usd=0.005)
    portao.parte(f, "cena", "promo", "telegram")
    with pytest.raises(P.TetoDeGasto, match="teto"):
        portao.parte(f, "mascote", "promo", "telegram")
    assert portao.gasto_novo_usd == 0.005
