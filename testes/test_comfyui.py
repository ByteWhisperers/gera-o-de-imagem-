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
