"""Junta as medidas dos grafos de todas as peças: a evidência para a próxima versão da ficha.

Uso:
    python ferramentas/juntar_grafos.py fichas/arara/grafos -o fichas/arara/grafos/medidas-dos-grafos.json
    python ferramentas/juntar_grafos.py fichas/arara/grafos --folha saida/arara/fase2-pranchas.jpg

Para cada formato (home, promo): onde ficam o logo, o bloco de texto, o mascote
e o entorno (mediana, mínimo e máximo das peças), quantas linhas de texto, a
altura e o vão das linhas, as cores de cada estilo de letra, as linhas que
misturam branco e dourado, o contraste do texto com o fundo e a curva de
escurecimento. E o que não cabe na ficha atual: camadas que ela não tem,
rótulos fora do bloco de texto, observações das marcações. Cada número diz de
quais peças veio. O conteúdo do texto nunca é lido.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from motor import grafo as G  # noqa: E402
from motor.comparar import _fonte, de2000, rgb_para_lab  # noqa: E402


def _hex(c) -> str:
    return "#%02x%02x%02x" % tuple(int(round(v)) for v in c)


def _rgb(h: str) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[i : i + 2], 16) for i in (0, 2, 4)], np.float64)


def resumo(valores: list[float], casas: int = 3) -> dict:
    v = np.asarray(valores, np.float64)
    return {"mediana": round(float(np.median(v)), casas), "min": round(float(v.min()), casas),
            "max": round(float(v.max()), casas), "n": int(len(v))}


def caixa_resumo(caixas: dict[str, list[float]]) -> dict:
    if not caixas:
        return {}
    saida = {k: resumo([c[i] for c in caixas.values()]) for i, k in enumerate("xywh")}
    saida["pecas"] = sorted(caixas)
    return saida


def rampa_da_ficha(rampa: list, t: float) -> np.ndarray:
    for (t0, c0), (t1, c1) in zip(rampa, rampa[1:]):
        if t0 <= t <= t1:
            k = (t - t0) / (t1 - t0) if t1 > t0 else 0
            return (1 - k) * _rgb(c0) + k * _rgb(c1)
    return _rgb(rampa[-1][1])


def ler(pasta: Path) -> list[dict]:
    grafos = []
    for arq in sorted(pasta.glob("*.json")):
        try:
            g = G.carregar(arq)
        except Exception:                                   # noqa: BLE001 - outros JSON na pasta
            continue
        grafos.append(g)
    return grafos


def juntar(grafos: list[dict], ficha: dict | None = None) -> dict:
    pecas, por_formato = [], {}
    fora, rotulos, observacoes, temas = {}, {}, {}, {}
    estilos: dict[str, list[list[str]]] = {}
    for g in grafos:
        W, H = g["tamanho_px"]
        fmt = g["formato_peca"]
        f = por_formato.setdefault(fmt, {"logo": {}, "texto": {}, "mascote": {}, "entorno": {}, "linhas": [],
                                         "altura_linha": [], "vao": [], "contraste": [], "contorno": [],
                                         "escurecimento": [], "mistas": [], "delta_logo_texto": []})
        lay = G.layout_medido(g)
        if "logo" in lay:
            f["logo"][g["peca"]] = [lay["logo"]["x"], lay["logo"]["y"], lay["logo"]["w"], 0]
        if "texto" in lay:
            t = lay["texto"]
            f["texto"][g["peca"]] = [t["x"], t["y"], t["w"], t["h"]]
        for camada in ("mascote", "entorno"):
            m = G.mascara_camada(g, camada)
            c = G.caixa_px(m)
            if c is not None:
                f[camada][g["peca"]] = G.caixa_frac(c, W, H)
        linhas = [n for n in g["nos"] if n["tipo"] == "texto" and n.get("papel") != "rotulo"]
        f["linhas"].append(len(linhas))
        detalhes = []
        for n in linhas:
            est = n.get("estilo", {})
            f["altura_linha"].append(est.get("altura_px", 0) / H)
            f["contorno"].append(est.get("contorno_escuro_frac", 0))
            dourada = est.get("fracao_dourada", 1.0 if est.get("estilo_ficha") == "dourado" else 0.0)
            detalhes.append({"id": n["id"], "estilo": est.get("estilo_ficha"),
                             "altura_frac_H": round(est.get("altura_px", 0) / H, 4), "peso_rel": est.get("peso_rel"),
                             "fracao_dourada": dourada, "rampa_tercos": est.get("rampa_tercos")})
            if 0.15 < dourada < 0.85:
                f["mistas"].append(f"{g['peca']}:{n['id']}")
            elif est.get("rampa_tercos"):
                estilos.setdefault(est.get("estilo_ficha"), []).append(est["rampa_tercos"])
        for a in g["arestas"]:
            if a["rel"] == "empilhado_acima":
                f["vao"].append(a["vao_rel_altura"])
            if a["rel"] == "contraste":
                f["contraste"].append(a["wcag"])
            if a["rel"] == "alinhado_com" and a.get("para") == "logo":
                f["delta_logo_texto"].append(a["delta_x"])
        esc = next((n for n in g["nos"] if n["id"] == "escurecimento"), None)
        if esc:
            f["escurecimento"].append(esc["estilo"]["L_fundo_por_decimo_de_W"])
        for c in g.get("camadas_fora_da_ficha", []):
            fora.setdefault(c, []).append(g["peca"])
        rs = [n["id"] for n in g["nos"] if n.get("papel") == "rotulo"]
        if rs:
            rotulos[g["peca"]] = rs
        if g.get("observacoes"):
            observacoes[g["peca"]] = g["observacoes"]
        mascote = next((n for n in g["nos"] if n["tipo"] == "personagem"), {})
        tm = temas.setdefault(g.get("tema"), {"pecas": [], "figurinos": []})
        tm["pecas"].append(g["peca"])
        tm["figurinos"].append(mascote.get("figurino"))
        pecas.append({"peca": g["peca"], "formato": fmt, "tema": g.get("tema"), "estado": g.get("estado"),
                      "linhas": detalhes, "rotulos": rs, "camadas_fora_da_ficha": g.get("camadas_fora_da_ficha", []),
                      "quantidades": {n["id"]: n["quantidade"] for n in g["nos"] if "quantidade" in n}})

    saida_fmt = {}
    for fmt, f in por_formato.items():
        curvas = [c for c in f["escurecimento"] if c and all(v is not None for v in c)]
        saida_fmt[fmt] = {
            "pecas": len(f["linhas"]),
            "logo": {k: v for k, v in caixa_resumo(f["logo"]).items() if k != "h"},
            "texto": caixa_resumo(f["texto"]),
            "mascote": caixa_resumo(f["mascote"]),
            "entorno": caixa_resumo(f["entorno"]),
            "linhas_por_peca": resumo(f["linhas"], 1),
            "altura_linha_frac_H": resumo(f["altura_linha"]),
            "vao_entre_linhas_rel_altura": resumo(f["vao"], 2) if f["vao"] else {},
            "contraste_wcag": resumo(f["contraste"], 1) if f["contraste"] else {},
            "contorno_escuro_frac": resumo(f["contorno"], 2),
            "texto_x_menos_logo_x": resumo(f["delta_logo_texto"]) if f["delta_logo_texto"] else {},
            "linhas_mistas": f["mistas"],
            "L_fundo_por_decimo_de_W": [round(float(np.median([c[i] for c in curvas])), 1) for i in range(10)]
            if curvas else [],
        }
    cores = {}
    for est, rampas in estilos.items():
        tercos = []
        for i in range(3):
            vals = [_rgb(r[i]) for r in rampas if r[i]]
            tercos.append(_hex(np.median(vals, axis=0)))
        cores[est] = {"rampa_tercos": tercos, "linhas": len(rampas)}
        if ficha and est in ficha["texto"]["estilos"]:
            rampa = ficha["texto"]["estilos"][est]["rampa"]
            da_ficha = [rampa_da_ficha(rampa, t) for t in (1 / 6, 1 / 2, 5 / 6)]
            de = [float(de2000(rgb_para_lab(_rgb(m)[None]), rgb_para_lab(c[None]))[0])
                  for m, c in zip(tercos, da_ficha)]
            cores[est]["ficha_nos_tercos"] = [_hex(c) for c in da_ficha]
            cores[est]["dE00_ficha_x_medido"] = [round(v, 1) for v in de]
    return {"formato": "medidas-dos-grafos/0.1", "pecas": pecas, "por_formato": saida_fmt, "cores_do_texto": cores,
            "camadas_fora_da_ficha": fora, "rotulos_fora_do_bloco": rotulos, "temas": temas,
            "observacoes": observacoes,
            "convencao": "caixas em fração de W e H; mediana, mínimo e máximo das peças de cada formato"}


def folha(grafos: list[dict], largura: int = 2400) -> Image.Image:
    """As pranchas de conferência de todas as peças, duas por linha, com o nome em cima."""
    col = 2
    lado = (largura - 30) // col
    fonte = _fonte(26)
    blocos = []
    for g in grafos:
        arq = G.pasta(g) / "conferencia.jpg"
        if not arq.exists():
            continue
        im = Image.open(arq).convert("RGB")
        im = im.resize((lado, round(im.height * lado / im.width)))
        b = Image.new("RGB", (lado, im.height + 40), (20, 20, 20))
        b.paste(im, (0, 40))
        ImageDraw.Draw(b).text((8, 6), f"{g['peca']}  ({g.get('estado')})", font=fonte, fill=(240, 240, 240))
        blocos.append(b)
    linhas = [blocos[i : i + col] for i in range(0, len(blocos), col)]
    alturas = [max(b.height for b in ln) + 10 for ln in linhas]
    total = Image.new("RGB", (largura, sum(alturas) + 10), (20, 20, 20))
    y = 10
    for ln, a in zip(linhas, alturas):
        for i, b in enumerate(ln):
            total.paste(b, (10 + i * (lado + 10), y))
        y += a
    return total


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pasta", help="pasta com os grafos (<peca>.json)")
    ap.add_argument("-o", "--saida", help="arquivo JSON (padrão: imprime)")
    ap.add_argument("--ficha", help="ficha para comparar as cores do texto (padrão: a do primeiro grafo)")
    ap.add_argument("--folha", help="também salva a folha com as pranchas de conferência de todas as peças")
    a = ap.parse_args()
    grafos = ler(Path(a.pasta))
    from motor import ficha as F

    ficha = F.carregar(RAIZ / (a.ficha or grafos[0]["ficha"])) if grafos else None
    r = juntar(grafos, ficha)
    texto = json.dumps(r, ensure_ascii=False, indent=1) + "\n"
    if a.saida:
        Path(a.saida).write_text(texto, encoding="utf-8")
    else:
        print(texto, end="")
    if a.folha:
        Path(a.folha).parent.mkdir(parents=True, exist_ok=True)
        folha(grafos).save(a.folha, quality=86)


if __name__ == "__main__":
    main()
