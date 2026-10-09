import io
import json
import shutil
from pathlib import Path

import yaml
from PIL import Image

from motor import ficha as F
from motor import portao as P

RAIZ = Path(__file__).resolve().parent.parent
FICHA = "fichas/arara/ficha-v1.1.yaml"


def test_preencher_troca_os_marcadores_mantendo_o_tipo():
    g = {"3": {"inputs": {"seed": "{{semente}}", "text": "{{prompt}}", "fixo": "x"}}, "l": ["{{largura}}"]}
    assert P.preencher(g, {"semente": 7, "prompt": "p", "largura": 512}) == {
        "3": {"inputs": {"seed": 7, "text": "p", "fixo": "x"}}, "l": [512]}


def test_executar_comfyui_segue_prompt_historico_e_view():
    png = io.BytesIO()
    Image.new("RGB", (8, 4), "red").save(png, "PNG")
    chamadas = []

    def abrir(pedido):
        url = pedido if isinstance(pedido, str) else pedido.full_url
        chamadas.append(url.split("?")[0].rsplit("/", 2)[-2:])
        if url.endswith("/prompt"):
            return io.BytesIO(json.dumps({"prompt_id": "abc"}).encode())
        if "/history/" in url:
            hist = {"abc": {"status": {"completed": True},
                            "outputs": {"9": {"images": [{"filename": "a.png", "subfolder": "", "type": "output"}]}}}}
            return io.BytesIO(json.dumps(hist).encode())
        return io.BytesIO(png.getvalue())

    im = P.executar_comfyui("http://x", {"1": {}}, abrir=abrir)
    assert im.size == (8, 4)
    assert [c[-1] for c in chamadas] == ["prompt", "abc", "view"]


def test_provedor_comfyui_registra_a_parte_com_a_receita(tmp_path, monkeypatch):
    shutil.copytree(RAIZ / "integracoes", tmp_path / "integracoes")
    (tmp_path / "partes" / "arara").mkdir(parents=True)
    monkeypatch.setattr(P, "RAIZ", tmp_path)
    monkeypatch.setattr(P, "executar_comfyui", lambda url, grafo: Image.new("RGB", (64, 64), (150, 150, 160)))
    f = F.carregar(FICHA)
    portao = P.Portao("comfyui")
    im = portao.parte(f, "mascote", "promo", "telegram")
    assert im.size == (64, 64)
    entrada = yaml.safe_load((tmp_path / "partes/arara/registro.yaml").read_text())["entradas"][0]
    assert entrada["prompt"] == F.prompt_da_parte(f, "mascote", "telegram")
    assert entrada["custo_usd"] == 0 and entrada["recorte"] == "modelo"
    assert portao.recorte["mascote"] == "modelo" and portao.gasto_usd == 0


def test_biblioteca_reaproveita_e_so_gera_o_que_falta_ou_foi_pedido(tmp_path, monkeypatch):
    shutil.copytree(RAIZ / "integracoes", tmp_path / "integracoes")
    (tmp_path / "partes" / "arara").mkdir(parents=True)
    monkeypatch.setattr(P, "RAIZ", tmp_path)
    geradas = []

    def gerar(url, grafo):
        geradas.append(1)
        return Image.new("RGB", (64, 64), (len(geradas) * 40, 0, 0))

    monkeypatch.setattr(P, "executar_comfyui", gerar)
    f = F.carregar(FICHA)
    P.Portao("comfyui").parte(f, "cena", "promo", "telegram")
    im = P.Portao("comfyui").parte(f, "cena", "promo", "instagram")   # o fundo não depende do tema
    assert len(geradas) == 1 and im.getpixel((0, 0))[0] == 40
    P.Portao("comfyui").parte(f, "mascote", "promo", "instagram")       # mascote de tema novo: gera
    assert len(geradas) == 2
    portao = P.Portao("comfyui", novas={"cena"})
    im = portao.parte(f, "cena", "promo", "telegram")                  # variação pedida: gera e passa a valer
    assert len(geradas) == 3 and im.getpixel((0, 0))[0] == 120
    assert portao.log[-1]["gerada_agora"]


def test_registro_mantem_cabecalho_e_entradas_antigas(tmp_path, monkeypatch):
    shutil.copytree(RAIZ / "integracoes", tmp_path / "integracoes")
    (tmp_path / "partes" / "arara").mkdir(parents=True)
    (tmp_path / "partes/arara/registro.yaml").write_text(
        "# cabeçalho que cita a ficha: e entradas: no meio\n\nficha: x.yaml\nentradas: []\n", encoding="utf-8")
    monkeypatch.setattr(P, "RAIZ", tmp_path)
    monkeypatch.setattr(P, "executar_comfyui", lambda url, grafo: Image.new("RGB", (8, 8)))
    P.Portao("comfyui").parte(F.carregar(FICHA), "mascote", "promo", "vip")
    texto = (tmp_path / "partes/arara/registro.yaml").read_text(encoding="utf-8")
    assert texto.startswith("# cabeçalho que cita a ficha: e entradas: no meio\n")
    dados = yaml.safe_load(texto)
    assert dados["ficha"] == "x.yaml" and len(dados["entradas"]) == 1
