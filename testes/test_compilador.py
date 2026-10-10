from pathlib import Path

from motor import compilador as C
from motor import ficha as F
from motor import grafo as G

RAIZ = Path(__file__).resolve().parent.parent
GRAFO = G.carregar(RAIZ / "fichas/arara/grafos/promo-telegram.json")
FICHA = F.carregar(RAIZ / "fichas/arara/ficha-v1.1.yaml")
CFG = C.ler_config()


def _por_classe(wf, classe):
    return [n for n in wf.values() if n["class_type"] == classe]


def test_mesmo_grafo_da_sempre_o_mesmo_workflow():
    a, b = C.compilar(GRAFO, FICHA, CFG), C.compilar(GRAFO, FICHA, CFG)
    assert a.sha256() == b.sha256()
    assert C.compilar(GRAFO, FICHA, CFG, semente=520).sha256() != a.sha256()


def test_uma_saida_por_camada_gerada_e_nenhuma_para_texto_ou_logo():
    comp = C.compilar(GRAFO, FICHA, CFG)
    assert list(comp.saidas) == ["cena", "entorno", "mascote"]
    prefixos = sorted(n["inputs"]["filename_prefix"] for n in _por_classe(comp.workflow, "SaveImage"))
    assert prefixos == sorted(f"gera/promo-telegram/{c}" for c in ("cena", "entorno", "mascote"))
    assert not any("texto" in p or "logo" in p for p in prefixos)


def test_cada_parte_trabalha_na_sua_regiao_e_sai_recortada():
    comp = C.compilar(GRAFO, FICHA, CFG)
    W, H = GRAFO["tamanho_px"]
    for camada, s in comp.saidas.items():
        assert 0 <= s["x"] and 0 <= s["y"] and s["x"] + s["w"] <= W and s["y"] + s["h"] <= H
        assert s["geracao"][0] % 64 == 0 and s["geracao"][1] % 64 == 0
    assert len(_por_classe(comp.workflow, "ImageCrop")) == 2            # entorno e mascote
    assert len(_por_classe(comp.workflow, "JoinImageWithAlpha")) == 2
    assert comp.saidas["cena"]["w"] == W                               # o fundo é a peça inteira
    # tudo o que o workflow carrega está nas entradas a subir
    carregadas = {n["inputs"]["image"] for n in comp.workflow.values() if n["class_type"].startswith("LoadImage")}
    assert carregadas == set(comp.entradas)


def test_prompt_vem_da_ficha_com_o_tema_e_sem_fundo_de_estudio():
    comp = C.compilar(GRAFO, FICHA, CFG, tema="telegram")
    assert "blue paper plane" in comp.saidas["mascote"]["prompt"]
    assert "straw hat" in comp.saidas["mascote"]["prompt"]
    assert "studio background" not in comp.saidas["mascote"]["prompt"]
    outro = C.compilar(GRAFO, FICHA, CFG, tema="instagram")
    assert "camera app icon" in outro.saidas["mascote"]["prompt"]


def test_denoise_por_tipo_de_parte_e_ajustavel():
    comp = C.compilar(GRAFO, FICHA, CFG, denoise={"personagem": 0.3})
    assert comp.saidas["mascote"]["denoise"] == 0.3
    assert comp.saidas["cena"]["denoise"] == CFG["compilador"]["denoise"]["fundo"]
    valores = sorted(n["inputs"]["denoise"] for n in _por_classe(comp.workflow, "KSampler"))
    assert 0.3 in valores


def test_conferir_acha_no_inexistente_entrada_faltando_modelo_ausente_e_no_pago():
    info = {
        "CheckpointLoaderSimple": {"input": {"required": {"ckpt_name": [["sd_turbo.safetensors"]]}}},
        "Pago": {"api_node": True, "input": {"required": {}}},
        "KSampler": {"input": {"required": {"seed": ["INT"], "model": ["MODEL"]}}},
    }
    wf = {"1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "outro.safetensors"}},
          "2": {"class_type": "Pago", "inputs": {}},
          "3": {"class_type": "KSampler", "inputs": {"model": ["9", 0]}},
          "4": {"class_type": "IPAdapterApply", "inputs": {}}}
    problemas = " | ".join(C.conferir(wf, info))
    assert "não está entre as opções" in problemas
    assert "é pago" in problemas
    assert "falta a entrada 'seed'" in problemas
    assert "nó que não existe (9)" in problemas
    assert "'IPAdapterApply' não existe" in problemas


def test_placa_apaga_so_o_buraco():
    from PIL import Image

    W, H = GRAFO["tamanho_px"]
    comp = C.compilar_placa(FICHA, GRAFO, CFG, Image.new("RGB", (W, H)), Image.new("L", (W, H)))
    classes = [n["class_type"] for n in comp.workflow.values()]
    assert "SetLatentNoiseMask" in classes and "ImageCompositeMasked" in classes
    assert comp.saidas["placa"]["no"] in comp.workflow


def test_camada_fora_da_ficha_nao_vira_ramo_e_fica_anotada():
    import copy

    g = copy.deepcopy(GRAFO)
    moedas = G.no(g, "moedas")
    g["nos"].append({**moedas, "id": "folhagem", "camada_psd": "frente", "z": 5})
    comp = C.compilar(g, FICHA, CFG)
    assert list(comp.saidas) == ["cena", "entorno", "mascote"]
    assert comp.parametros["camadas_fora_da_ficha"] == ["frente"]
    assert comp.sha256() == C.compilar(GRAFO, FICHA, CFG).sha256()       # o workflow não muda


def test_todos_os_grafos_compilam_com_a_ficha_deles_e_a_frente_vira_ramo():
    for marcacao in sorted((RAIZ / "fichas/arara/grafos").glob("*.marcacao.yaml")):
        g = G.carregar(marcacao.with_name(marcacao.name.replace(".marcacao.yaml", ".json")))
        comp = C.compilar(g, F.carregar(RAIZ / g["ficha"]), CFG)
        assert comp.parametros["camadas_fora_da_ficha"] == [], g["peca"]
        tem_frente = any(n.get("camada_psd") == "frente" and "mascara" in n for n in g["nos"])
        assert ("frente" in comp.saidas) == tem_frente, g["peca"]
