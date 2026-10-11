"""Gera a lista de comandos do PhotoCraft que os agentes consultam.

Lê o registro de comandos do `photocraft-cli` instalado e escreve
`.claude/skills/photocraft/referencia/catalogo.md`: um comando por linha,
agrupado pelo começo do id (filter, layer, select…), com o rótulo, o caminho no
menu e os parâmetros que o próprio PhotoCraft documenta.

Rode de novo quando atualizar o PhotoCraft:
    python integracoes/photocraft/catalogo.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from integracoes.photocraft.sessao import achar_cli, versao  # noqa: E402

DESTINO = RAIZ / ".claude" / "skills" / "photocraft" / "referencia" / "catalogo.md"


def comandos(cli: str) -> list[dict]:
    saida = subprocess.run([cli, "commands", "--json"], check=True, capture_output=True, text=True).stdout
    return json.loads(saida)


def _uma_linha(texto) -> str:
    if texto is None:
        return ""
    if not isinstance(texto, str):
        texto = json.dumps(texto, ensure_ascii=False)
    return " ".join(texto.split()).replace("|", "\\|")


def markdown(lista: list[dict], ver: str) -> str:
    grupos: dict[str, list[dict]] = defaultdict(list)
    for c in lista:
        grupos[c["id"].split(".")[0]].append(c)
    linhas = [
        f"# Comandos do PhotoCraft {ver}",
        "",
        f"Gerado por `integracoes/photocraft/catalogo.py` a partir de `photocraft-cli commands --json` "
        f"({len(lista)} comandos). Não edite à mão: rode o script de novo.",
        "",
        "Para achar um comando: `grep -i 'blur' .claude/skills/photocraft/referencia/catalogo.md`.",
        "Os parâmetros abaixo são os que o PhotoCraft documenta; os testados neste projeto estão em",
        "[comandos-testados.md](comandos-testados.md).",
        "",
        "Grupos: " + ", ".join(f"`{g}` ({len(v)})" for g, v in sorted(grupos.items())),
        "",
    ]
    for g in sorted(grupos):
        linhas += [f"## {g}", "", "| id | rótulo | menu | parâmetros |", "|---|---|---|---|"]
        for c in sorted(grupos[g], key=lambda c: c["id"]):
            menu = " › ".join(c.get("menu") or [])
            params = c.get("params") or c.get("paramsDoc") or c.get("params_doc") or ""
            linhas.append(f"| `{c['id']}` | {_uma_linha(c.get('label'))} | {_uma_linha(menu)} | {_uma_linha(params)} |")
        linhas.append("")
    return "\n".join(linhas)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cli", default=None)
    ap.add_argument("--saida", type=Path, default=DESTINO)
    a = ap.parse_args()
    cli = a.cli or achar_cli()
    lista = comandos(cli)
    a.saida.parent.mkdir(parents=True, exist_ok=True)
    a.saida.write_text(markdown(lista, versao(cli)), encoding="utf-8")
    print(f"{len(lista)} comandos em {a.saida.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
