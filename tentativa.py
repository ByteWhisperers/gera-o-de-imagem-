"""Uma volta do loop: grafo -> workflow do ComfyUI -> PSD -> notas contra a referência.

Uso:
    python tentativa.py fichas/arara/grafos/promo-telegram.json
    python tentativa.py fichas/arara/grafos/promo-telegram.json --denoise personagem=0.4 --mudanca "mascote mais fiel"
    python tentativa.py fichas/arara/grafos/promo-telegram.json --so-compilar      # só monta e confere o workflow
    python tentativa.py fichas/arara/grafos/promo-telegram.json --controles saida/arara/promo-telegram-comfyui.psd
    python tentativa.py fichas/arara/grafos/promo-telegram.json --motor gateway --teto 0.05   # pago, Z-Image Turbo

Cada tentativa:
  1. compila o workflow a partir do grafo (motor/compilador.py) e guarda em
     fluxos/<marca>/workflows/<sha256 curto>.json;
  2. confere o workflow contra o /object_info do ComfyUI (nós, entradas,
     modelos instalados, nenhum nó pago); o /prompt confere de novo;
  3. sobe as placas e as máscaras, roda e baixa as camadas geradas;
  4. monta o PSD com texto e logo de código, no lugar medido na referência;
  5. mede cada parte contra a referência (motor/comparar.py) e faz a prancha;
  6. acrescenta uma linha em fluxos/<marca>/tentativas.jsonl (nada é apagado).

Com --motor comfyui (padrão) o custo é zero: roda no ComfyUI local. Com
--motor gateway os mesmos ramos (mesma caixa, prompt e força) vão como
image-to-image para o gateway de imagem; é pago e exige teto (--teto). O
workflow compilado continua guardado como receita. Quem decide se vale é o
dono; a linha nasce com "decisao": null.
"""

from __future__ import annotations

import argparse
import copy
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

from motor import comfyui as CU
from motor import gateway as GW
from motor import comparar as CMP
from motor import compilador as C
from motor import compositor as M
from motor import ficha as F
from motor import grafo as G
from motor import qa

RAIZ = Path(__file__).resolve().parent


def _rel(caminho: Path) -> str:
    caminho = caminho.resolve()
    return caminho.relative_to(RAIZ).as_posix() if caminho.is_relative_to(RAIZ) else caminho.as_posix()


def ficha_no_lugar(ficha: dict, grafo: dict) -> dict:
    """A ficha com as caixas medidas no grafo (texto e logo) no lugar das estimativas,
    e no tamanho da referência: as partes vêm em pixels dela (a ficha pode pedir a
    peça final maior, como o dobro das referências pequenas da 9pmbet).

    Só vale para esta tentativa, em memória: a ficha aprovada não muda.
    """
    efetiva = copy.deepcopy(ficha)
    efetiva["layout"][grafo["formato_peca"]].update(G.layout_medido(grafo))
    largura, altura = grafo["tamanho_px"]
    efetiva["formatos"][grafo["formato_peca"]] = {"largura": largura, "altura": altura}
    return efetiva


def camadas_ocultas(grafo: dict) -> set[str]:
    """Efeitos que já vêm embutidos no fundo da referência entram no PSD desligados."""
    return {n["camada_psd"] for n in grafo["nos"]
            if n["tipo"] == "efeito" and str(n.get("na_referencia", "")).startswith("embutido")}


def camadas_vazias(ficha: dict, posicionadas: dict) -> set[str]:
    """Camadas geradas da ficha que o grafo desta peça não tem (ex.: frente no Telegram)."""
    return {c["id"] for c in ficha["camadas"] if c["tipo"] == "gerada" and c["id"] not in posicionadas}


def proximo_id(diario: Path, peca: str) -> str:
    n = 0
    if diario.exists():
        n = sum(1 for l in diario.read_text(encoding="utf-8").splitlines() if l.strip()
                and json.loads(l).get("peca") == peca)
    return f"{peca}-{n + 1:03d}"


def notas_de_psd(grafo: dict, psd: Path, so: list[str] | None = None) -> tuple[Image.Image, dict]:
    png = psd.with_suffix(".png")
    if png.exists():
        final = Image.open(png)
    else:
        from psd_tools import PSDImage

        final = PSDImage.open(psd).composite()
    return final, CMP.medir(grafo, final, CMP.camadas_do_psd(psd), so)


def rodar(caminho_grafo: str, tema: str | None = None, semente: int = 519, denoise: dict | None = None,
          saida: Path = RAIZ / "saida", controles: list[str] | None = None, mudanca: str = "", pai: str | None = None,
          so_compilar: bool = False, fluxos: Path = RAIZ / "fluxos", motor: str = "comfyui",
          teto_usd: float | None = None) -> dict:
    if motor == "gateway" and teto_usd is None:
        raise GW.TetoDeGasto("o motor gateway é pago: defina o teto de gasto (--teto)")
    tempos: dict[str, float] = {}
    t0 = time.perf_counter()
    grafo = G.carregar(caminho_grafo)
    ficha = F.carregar(RAIZ / grafo["ficha"])
    cfg = C.ler_config()
    comp = C.compilar(grafo, ficha, cfg, tema, semente, denoise)
    pasta_fluxos = fluxos / grafo["marca"]
    sha = comp.sha256()
    arquivo_wf = pasta_fluxos / "workflows" / f"{sha[:16]}.json"
    arquivo_wf.parent.mkdir(parents=True, exist_ok=True)
    arquivo_wf.write_text(comp.json(), encoding="utf-8")
    tempos["compilar"] = round(time.perf_counter() - t0, 1)

    t = time.perf_counter()
    if motor == "comfyui":
        info = CU.object_info(cfg["url"])
        problemas = C.conferir(comp.workflow, info)
        if problemas:
            raise CU.WorkflowRecusado("o workflow não passou na conferência", {"problemas": problemas})
    tempos["conferir"] = round(time.perf_counter() - t, 1)
    if so_compilar:
        return {"workflow": _rel(arquivo_wf), "sha256": sha, "nos": len(comp.workflow),
                "conferencia": "ok", "camadas": list(comp.saidas),
                "camadas_fora_da_ficha": comp.parametros["camadas_fora_da_ficha"]}

    t = time.perf_counter()
    custo = 0.0
    if motor == "gateway":
        cfg_gw = GW.ler_config()
        caixa = GW.Caixa(teto_usd, cfg_gw["preco_por_imagem_usd"])
        posicionadas = GW.refazer_ramos(comp, grafo, cfg_gw, caixa)
        custo = round(caixa.gasto_usd, 4)
        versao = {"motor": "gateway", "url": cfg_gw["url"], "modelo": cfg_gw["modelo"]}
    else:
        for nome, imagem in comp.entradas.items():
            CU.enviar_imagem(cfg["url"], nome, imagem)
        resultado = CU.executar(cfg["url"], comp.workflow)
        posicionadas = {camada: (resultado[s["no"]][0], s["x"], s["y"]) for camada, s in comp.saidas.items()}
        versao = CU.versao(cfg["url"])
    tempos[motor] = round(time.perf_counter() - t, 1)

    t = time.perf_counter()
    efetiva = ficha_no_lugar(ficha, grafo)
    formato = grafo["formato_peca"]
    linhas = F.linhas_de_texto(efetiva, comp.parametros["tema"])
    camadas = M.montar(efetiva, formato, {}, linhas, posicionadas=posicionadas, ocultas=camadas_ocultas(grafo),
                       vazias=camadas_vazias(efetiva, posicionadas))
    w, h = F.tamanho(efetiva, formato)
    diario = pasta_fluxos / "tentativas.jsonl"
    id_ = proximo_id(diario, grafo["peca"])
    destino = saida / grafo["marca"] / "tentativas" / id_
    caminhos = M.salvar(camadas, w, h, destino / "peca")
    final = M.achatar(camadas, w, h)
    tempos["compor"] = round(time.perf_counter() - t, 1)

    t = time.perf_counter()
    notas = CMP.medir(grafo, final, {c.nome: (np.asarray(c.imagem), c.x, c.y) for c in camadas}, list(comp.saidas))
    pecas, todas = {id_: final}, {id_: notas}
    for ctrl in controles or []:
        p = Path(ctrl)
        im_c, n_c = notas_de_psd(grafo, p, list(comp.saidas))
        pecas[p.stem], todas[p.stem] = im_c, n_c
    CMP.prancha(grafo, pecas, todas).save(destino / "prancha.jpg", quality=88)
    antigo = qa.conferir(efetiva, formato, final, camadas)
    tempos["comparar"] = round(time.perf_counter() - t, 1)
    tempos["total"] = round(time.perf_counter() - t0, 1)

    linha = {
        "id": id_, "peca": grafo["peca"], "pai": pai, "quando": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "grafo": {"arquivo": _rel(Path(grafo["_caminho"])), "sha256": grafo["_sha256"], "estado": grafo.get("estado")},
        "ficha": ficha["versao"], "workflow": {"arquivo": _rel(arquivo_wf), "sha256": sha},
        "comfyui" if motor == "comfyui" else "motor": versao, "parametros": comp.parametros, "mudanca": mudanca,
        "custo_usd": custo,
        "tempos_s": tempos, "notas": notas, "qa_antigo_ok": all(r["ok"] for r in antigo),
        "controles": {k: v for k, v in todas.items() if k != id_},
        "arquivos": {k: _rel(v) for k, v in {**caminhos, "prancha": destino / "prancha.jpg"}.items()},
        "decisao": None,
    }
    with diario.open("a", encoding="utf-8") as f:
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")
    return linha


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("grafo")
    ap.add_argument("--tema")
    ap.add_argument("--semente", type=int, default=519)
    ap.add_argument("--denoise", nargs="*", default=[], metavar="TIPO=VALOR",
                    help="muda quanto cada tipo de parte pode mudar, ex.: personagem=0.4 fundo=0.3")
    ap.add_argument("--controles", nargs="*", default=[], metavar="PSD", help="outras peças para pôr na prancha")
    ap.add_argument("--mudanca", default="", help="o que mudou em relação à tentativa anterior")
    ap.add_argument("--pai", help="id da tentativa da qual esta deriva")
    ap.add_argument("--saida", default=str(RAIZ / "saida"))
    ap.add_argument("--so-compilar", action="store_true")
    ap.add_argument("--motor", default="comfyui", choices=["comfyui", "gateway"],
                    help="onde gerar: ComfyUI local (grátis) ou gateway de imagem (pago, exige --teto)")
    ap.add_argument("--teto", type=float, metavar="US$", help="com --motor gateway: quanto esta volta pode gastar")
    a = ap.parse_args()
    if a.motor == "gateway" and a.teto is None:
        ap.error("--motor gateway é pago: informe o teto de gasto com --teto (por exemplo --teto 0.05)")
    denoise = {k: float(v) for k, v in (x.split("=") for x in a.denoise)}
    r = rodar(a.grafo, a.tema, a.semente, denoise, Path(a.saida), a.controles, a.mudanca, a.pai, a.so_compilar,
              motor=a.motor, teto_usd=a.teto)
    if a.so_compilar:
        print(json.dumps(r, ensure_ascii=False))
        return
    print(f"tentativa {r['id']}  workflow {r['workflow']['arquivo']}  tempo total {r['tempos_s']['total']}s"
          f"  custo US${r['custo_usd']}")
    for parte, n in r["notas"].items():
        if n.get("falta"):
            print(f"  {parte:8} não veio")
            continue
        extra = f"  cobertura {n['cobertura']}" if "cobertura" in n else ""
        print(f"  {parte:8} ΔE {n['dE00']:>6}  ssim {n['ssim']}  paleta ΔE {n['paleta_dE']}{extra}  ({n['leitura']})")
    print(f"  prancha: {r['arquivos']['prancha']}")


if __name__ == "__main__":
    main()
