"""Roda a linha de produção para uma ficha: partes -> composição -> QA -> arquivos.

Uso:
    python pipeline.py fichas/arara/ficha-v1.0.yaml --formato home promo
    python pipeline.py fichas/arara/ficha-v1.0.yaml --provedor registro --figurino turista

Saída em saida/<marca>/<formato>-<figurino>-<provedor>.{psd,png,webp} e um
relatorio.json com a proveniência de cada parte e o resultado do QA.
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


def rodar(caminho_ficha: str, formatos: list[str] | None, provedor: str, figurino: str | None, saida: Path) -> dict:
    ficha = F.carregar(caminho_ficha)
    portao = Portao(provedor)
    figurino = figurino or ficha["partes"]["mascote"].get("figurino_padrao")
    relatorio = {"ficha": ficha["_caminho"], "versao": ficha["versao"], "provedor": provedor, "pecas": []}
    for formato in formatos or list(ficha["formatos"]):
        partes = {
            "cena": portao.parte(ficha, "cena", formato),
            "mascote": portao.parte(ficha, "mascote", formato, figurino),
        }
        camadas = C.montar(ficha, formato, partes, ficha["texto"]["exemplo"])
        w, h = F.tamanho(ficha, formato)
        base = saida / ficha["marca"] / f"{formato}-{figurino}-{provedor}"
        caminhos = C.salvar(camadas, w, h, base)
        final = C.achatar(camadas, w, h)
        resultados = qa.conferir(ficha, formato, final, camadas)
        relatorio["pecas"].append({
            "formato": formato,
            "figurino": figurino,
            "arquivos": {k: v.relative_to(saida.parent).as_posix() if v.is_relative_to(saida.parent) else str(v)
                         for k, v in caminhos.items()},
            "camadas": [c.nome for c in camadas],
            "qa": resultados,
            "qa_ok": all(r["ok"] for r in resultados),
        })
    relatorio["partes"] = portao.log
    relatorio["gasto_usd"] = round(portao.gasto_usd, 4)
    (saida / ficha["marca"]).mkdir(parents=True, exist_ok=True)
    (saida / ficha["marca"] / f"relatorio-{provedor}-{figurino}.json").write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=1), encoding="utf-8")
    return relatorio


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ficha")
    ap.add_argument("--formato", nargs="*")
    ap.add_argument("--provedor", default="rascunho", choices=["rascunho", "registro"])
    ap.add_argument("--figurino")
    ap.add_argument("--saida", default=str(RAIZ / "saida"))
    a = ap.parse_args()
    rel = rodar(a.ficha, a.formato, a.provedor, a.figurino, Path(a.saida))
    for p in rel["pecas"]:
        falhas = [r["regra"] for r in p["qa"] if not r["ok"]]
        print(f"{p['formato']:6} {p['figurino']:8} QA {'ok' if p['qa_ok'] else 'FALHOU: ' + ', '.join(falhas)}  {p['arquivos']['png']}")
    print(f"gasto registrado: US${rel['gasto_usd']}")


if __name__ == "__main__":
    main()
