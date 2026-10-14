import base64
import io
import json
import shutil
from pathlib import Path

import numpy as np
import pytest
import yaml
from PIL import Image

import tentativa as T
from motor import ficha as F
from motor import gateway as G
from motor import grafo as GR
from motor import portao as P

RAIZ = Path(__file__).resolve().parent.parent
FICHA = "fichas/arara/ficha-v1.2.yaml"
GRAFO = "fichas/arara/grafos/promo-telegram.json"


def _png(w, h, cor="red"):
    dados = io.BytesIO()
    Image.new("RGB", (w, h), cor).save(dados, "PNG")
    return dados.getvalue()


def test_tamanho_aceito_fica_entre_256_e_1536_na_mesma_proporcao():
    assert G.tamanho_aceito(1024, 448) == (1024, 448)
    assert G.tamanho_aceito(3072, 960) == (1536, 480)
    assert G.tamanho_aceito(200, 400) == (256, 512)


def test_gerar_pede_espera_o_job_e_baixa_a_imagem():
    chamadas = []

    def abrir(pedido):
        url = pedido if isinstance(pedido, str) else pedido.full_url
        chamadas.append(url)
        if url.endswith("/v1/images"):
            assert pedido.headers["Authorization"] == "Bearer k"
            corpo = json.loads(pedido.data)
            assert corpo == {"model": "rapido", "prompt": "p", "size": "1024x448", "seed": 7, "wait": True}
            return io.BytesIO(json.dumps({"id": "img_1", "status": "running"}).encode())
        if url.endswith("/v1/jobs/img_1"):
            return io.BytesIO(json.dumps({"id": "img_1", "status": "succeeded", "cost_usd": 0.005,
                                          "images": ["https://cdn/x.png"]}).encode())
        return io.BytesIO(_png(1024, 448))

    im, custo = G.gerar("http://gw", "k", "rapido", "p", 1024, 448, 7, intervalo=0, abrir=abrir)
    assert im.size == (1024, 448) and custo == 0.005
    assert chamadas == ["http://gw/v1/images", "http://gw/v1/jobs/img_1", "https://cdn/x.png"]


def test_gerar_com_imagem_de_entrada_manda_data_uri_e_forca():
    pedidos = []
    pronto = {"id": "a", "status": "succeeded", "images": ["data:image/png;base64,"
                                                           + base64.b64encode(_png(512, 704)).decode()]}

    def abrir(pedido):
        pedidos.append(json.loads(pedido.data))
        return io.BytesIO(json.dumps(pronto).encode())

    im, custo = G.gerar("http://gw", "k", "rapido", "p", 512, 704, 1, imagem=Image.new("RGB", (100, 80)),
                        forca=0.4, abrir=abrir)
    assert im.size == (512, 704) and custo is None
    assert pedidos[0]["strength"] == 0.4 and pedidos[0]["image"].startswith("data:image/png;base64,")
    entrada = Image.open(io.BytesIO(base64.b64decode(pedidos[0]["image"].split(",", 1)[1])))
    assert entrada.size == (512, 704)          # a entrada sobe no tamanho de geração


def test_gerar_avisa_falha():
    falhou = {"id": "a", "status": "failed", "error": "sem crédito", "images": []}
    with pytest.raises(G.GatewayFalhou, match="sem crédito"):
        G.gerar("http://gw", "k", "rapido", "p", 768, 512, 1,
                abrir=lambda pedido: io.BytesIO(json.dumps(falhou).encode()))


def test_chave_vem_do_ambiente(monkeypatch):
    monkeypatch.delenv("GATEWAY_CHAVE", raising=False)
    with pytest.raises(G.GatewayFalhou, match="GATEWAY_CHAVE"):
        G.chave()


def test_caixa_para_antes_de_passar_do_teto():
    caixa = G.Caixa(teto_usd=0.01, preco_usd=0.005)
    for _ in range(2):
        caixa.conferir("x")
        caixa.pagar("x", None)
    with pytest.raises(G.TetoDeGasto):
        caixa.conferir("x")
    assert caixa.gasto_usd == pytest.approx(0.01)


# ------------------------------------------------------------- portão


@pytest.fixture
def raiz(tmp_path, monkeypatch):
    shutil.copytree(RAIZ / "integracoes", tmp_path / "integracoes")
    (tmp_path / "partes" / "arara").mkdir(parents=True)
    monkeypatch.setattr(P, "RAIZ", tmp_path)
    monkeypatch.setenv("GATEWAY_CHAVE", "k")
    monkeypatch.delenv("GATEWAY_URL", raising=False)
    return tmp_path


def test_provedor_gateway_exige_teto(raiz):
    with pytest.raises(P.TetoDeGasto, match="--teto"):
        P.Portao("gateway").parte(F.carregar(FICHA), "mascote", "promo", "telegram")


def test_provedor_gateway_registra_a_parte_com_custo(raiz, monkeypatch):
    pedidos = []

    def gerar(url, chave, modelo, prompt, largura, altura, semente, espera_max):
        pedidos.append((url, modelo, largura, altura))
        return Image.new("RGB", (largura, altura)), 0.005

    monkeypatch.setattr(P, "gerar_no_gateway", gerar)
    f = F.carregar(FICHA)
    portao = P.Portao("gateway", teto_usd=0.01)
    im = portao.parte(f, "mascote", "promo", "telegram")
    assert im.size == (768, 1056) and pedidos == [("http://127.0.0.1:8000", "rapido", 768, 1056)]
    entrada = yaml.safe_load((raiz / "partes/arara/registro.yaml").read_text())["entradas"][0]
    assert entrada["modelo"] == "gateway/rapido" and entrada["custo_usd"] == 0.005
    assert entrada["prompt"] == F.prompt_da_parte(f, "mascote", "telegram") and entrada["recorte"] == "modelo"
    assert portao.gasto_novo_usd == 0.005 and portao.gasto_usd == 0.005
    # a mesma receita sai da biblioteca, sem gastar de novo
    P.Portao("gateway", teto_usd=0.01).parte(f, "mascote", "promo", "telegram")
    assert len(pedidos) == 1
    # e a parte do ComfyUI com a mesma receita não serve para o gateway
    monkeypatch.setattr(P, "executar_comfyui", lambda url, grafo: Image.new("RGB", (64, 64)))
    P.Portao("comfyui", novas={"entorno"}).parte(f, "entorno", "promo", "telegram")
    P.Portao("gateway", teto_usd=0.01).parte(f, "entorno", "promo", "telegram")
    assert len(pedidos) == 2


def test_provedor_gateway_para_no_teto(raiz, monkeypatch):
    monkeypatch.setattr(P, "gerar_no_gateway", lambda *a: (Image.new("RGB", (8, 8)), 0.005))
    f = F.carregar(FICHA)
    portao = P.Portao("gateway", teto_usd=0.005)
    portao.parte(f, "cena", "promo", "telegram")
    with pytest.raises(P.TetoDeGasto, match="teto"):
        portao.parte(f, "mascote", "promo", "telegram")
    assert portao.gasto_novo_usd == 0.005


# ------------------------------------------------------------- loop e placas


def _gateway_falso(pedidos):
    """Devolve a própria imagem de entrada: o ramo tem de voltar igual à placa."""
    def gerar(url, chave, modelo, prompt, largura, altura, semente, imagem=None, forca=None, espera_max=300):
        pedidos.append({"prompt": prompt, "tamanho": (largura, altura), "forca": forca, "entrada": imagem.size})
        return imagem.resize((largura, altura)), 0.005
    return gerar


def test_refazer_ramos_corta_a_placa_e_aplica_a_mascara(monkeypatch):
    from motor import compilador as C

    monkeypatch.setenv("GATEWAY_CHAVE", "k")
    grafo = GR.carregar(RAIZ / GRAFO)
    ficha = F.carregar(RAIZ / grafo["ficha"])
    comp = C.compilar(grafo, ficha, C.ler_config())
    pedidos = []
    caixa = G.Caixa(1.0, 0.005)
    saidas = G.refazer_ramos(comp, grafo, G.ler_config(), caixa, gerar_=_gateway_falso(pedidos))
    assert set(saidas) == set(comp.saidas) and caixa.gasto_usd == pytest.approx(0.005 * len(saidas))
    for camada, (im, x, y) in saidas.items():
        s = comp.saidas[camada]
        assert (x, y, im.size) == (s["x"], s["y"], (s["w"], s["h"]))
        if s["classe"] != "fundo":
            assert im.mode == "RGBA"
            alfa = np.asarray(im)[..., 3] > 127
            assert (alfa == GR.mascara_camada(grafo, camada)[y:y + s["h"], x:x + s["w"]]).mean() > 0.99
    assert {p["forca"] for p in pedidos} == {s["denoise"] for s in comp.saidas.values()}
    assert all(max(p["tamanho"]) <= 1536 for p in pedidos)


def test_placa_so_troca_o_buraco(monkeypatch):
    preenchida = Image.new("RGB", (400, 200), (10, 20, 30))
    mascara = Image.new("L", (400, 200), 0)
    mascara.paste(255, (100, 50, 200, 150))

    def gerar(url, chave, modelo, prompt, largura, altura, semente, imagem=None, forca=None, espera_max=300):
        return Image.new("RGB", (largura, altura), (200, 200, 200)), None

    monkeypatch.setenv("GATEWAY_CHAVE", "k")
    caixa = G.Caixa(0.01, 0.005)
    im = G.placa(preenchida, mascara, "p", 0.8, 7, {"url": "u", "modelo": "rapido"}, caixa, lado=512, gerar_=gerar)
    assert im.getpixel((10, 10)) == (10, 20, 30) and im.getpixel((150, 100)) == (200, 200, 200)
    assert caixa.gasto_usd == 0.005


def test_tentativa_pelo_gateway_anota_custo_e_motor(tmp_path, monkeypatch):
    monkeypatch.setenv("GATEWAY_CHAVE", "k")
    pedidos = []
    monkeypatch.setattr(G, "gerar", _gateway_falso(pedidos))
    with pytest.raises(G.TetoDeGasto):
        T.rodar(GRAFO, saida=tmp_path / "saida", fluxos=tmp_path / "fluxos", motor="gateway")
    linha = T.rodar(GRAFO, saida=tmp_path / "saida", fluxos=tmp_path / "fluxos", motor="gateway", teto_usd=0.05)
    assert linha["custo_usd"] == pytest.approx(0.005 * len(pedidos)) and linha["motor"]["motor"] == "gateway"
    # devolvendo a própria placa, mascote e entorno ficam iguais aos da referência
    for camada in ("entorno", "mascote"):
        assert linha["notas"][camada]["dE00"] < 3
    with pytest.raises(G.TetoDeGasto):
        T.rodar(GRAFO, saida=tmp_path / "saida", fluxos=tmp_path / "fluxos", motor="gateway", teto_usd=0.005)
