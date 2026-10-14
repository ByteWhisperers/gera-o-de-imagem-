"""Roda a linha de produção para uma ficha: partes -> composição -> QA -> arquivos.

Uso:
    python pipeline.py fichas/arara/ficha-v1.2.yaml --tema instagram
    python pipeline.py fichas/arara/ficha-v1.2.yaml --tema telegram --provedor comfyui --formato promo
    python pipeline.py fichas/arara/ficha-v1.2.yaml --tema telegram --provedor comfyui --novo mascote   # variação
    python pipeline.py fichas/arara/ficha-v1.0.yaml --provedor registro --tema realeza   # v1.0: tema = figurino
    python pipeline.py fichas/arara/ficha-v1.2.yaml --tema telegram --provedor gateway --teto 0.05   # pago, com teto

O tema liga a mensagem ao mascote: escolhe o figurino, o que ele segura, os
elementos em volta e as linhas de texto de exemplo.

Saída em saida/<marca>/<formato>-<tema>-<provedor>.{psd,png,webp} e um
relatorio-<provedor>-<tema>.json com a proveniência de cada parte e o QA.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from motor import compositor as C
from motor import ficha as F
from motor import qa
from motor.portao import Portao

RAIZ = Path(__file__).resolve().parent


def rodar(caminho_ficha: str, formatos: list[str] | None, provedor: str, tema: str | None, saida: Path,
          novas: list[str] | None = None, teto_usd: float | None = None) -> dict:
    ficha = F.carregar(caminho_ficha)
    portao = Portao(provedor, novas=set(novas or []), teto_usd=teto_usd)
    t = F.resolver_tema(ficha, tema)
    nome_tema = t["nome"] or t["figurino"]
    linhas = F.linhas_de_texto(ficha, tema)
    geradas = [c["parte"] for c in ficha["camadas"] if c["tipo"] == "gerada"]
    relatorio = {"ficha": ficha["_caminho"], "versao": ficha["versao"], "provedor": provedor,
                 "tema": nome_tema, "figurino": t["figurino"], "pecas": []}
    for formato in formatos or list(ficha["formatos"]):
        partes = {p: portao.parte(ficha, p, formato, tema) for p in geradas}
        camadas = C.montar(ficha, formato, partes, linhas, portao.recorte)
        w, h = F.tamanho(ficha, formato)
        base = saida / ficha["marca"] / f"{formato}-{nome_tema}-{provedor}"
        caminhos = C.salvar(camadas, w, h, base)
        resultados = qa.conferir(ficha, formato, C.achatar(camadas, w, h), camadas)
        relatorio["pecas"].append({
            "formato": formato,
            "arquivos": {k: v.as_posix() for k, v in caminhos.items()},
            "camadas": [c.nome for c in camadas],
            "qa": resultados,
            "qa_ok": all(r["ok"] for r in resultados),
        })
    relatorio["partes"] = portao.log
    relatorio["gasto_usd"] = round(portao.gasto_usd, 4)
    relatorio["gasto_novo_usd"] = round(portao.gasto_novo_usd, 4)
    (saida / ficha["marca"] / f"relatorio-{provedor}-{nome_tema}.json").write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=1), encoding="utf-8")
    return relatorio


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ficha")
    ap.add_argument("--formato", nargs="*")
    ap.add_argument("--provedor", default="rascunho", choices=["rascunho", "registro", "comfyui", "gateway"])
    ap.add_argument("--tema")
    ap.add_argument("--saida", default=str(RAIZ / "saida"))
    ap.add_argument("--novo", nargs="*", default=[], metavar="PARTE",
                    help="com --provedor comfyui ou gateway: gera de novo estas partes em vez de reaproveitar da biblioteca")
    ap.add_argument("--teto", type=float, metavar="US$",
                    help="com --provedor gateway (obrigatório): quanto esta rodada pode gastar em partes novas")
    a = ap.parse_args()
    if a.provedor == "gateway" and a.teto is None:
        ap.error("--provedor gateway é pago: informe o teto de gasto com --teto (por exemplo --teto 0.05)")
    rel = rodar(a.ficha, a.formato, a.provedor, a.tema, Path(a.saida), a.novo, a.teto)
    for p in rel["pecas"]:
        falhas = [r["regra"] for r in p["qa"] if not r["ok"]]
        print(f"{p['formato']:6} {rel['tema']:10} QA {'ok' if p['qa_ok'] else 'FALHOU: ' + ', '.join(falhas)}  {p['arquivos']['png']}")
    for l in rel["partes"]:
        print(f"  {l['parte']:8} {'gerada agora' if l.get('gerada_agora') else 'da biblioteca':13} {l.get('arquivo', '')}")
    print(f"custo das partes usadas (pago só quando cada uma foi gerada): US${rel['gasto_usd']}")
    if rel["gasto_novo_usd"]:
        print(f"gasto desta rodada com partes novas: US${rel['gasto_novo_usd']}")


if __name__ == "__main__":
    main()
