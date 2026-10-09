"""Teste rápido de um servidor MCP por stdio: inicia, lista as ferramentas e, se pedido, chama uma.

Uso:
    python integracoes/testar_mcp.py -- comfy-mcp
    python integracoes/testar_mcp.py --chamar server_info -- comfy-mcp
    python integracoes/testar_mcp.py --chamar doc_inspect --args '{"path": "saida/arara/x.psd"}' -- photocraft-cli mcp --automation-read-root .
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys


def conversar(comando: list[str], chamar: str | None, args: dict) -> dict:
    proc = subprocess.Popen(comando, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

    def enviar(msg: dict) -> None:
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()

    def receber(id_: int) -> dict:
        for linha in proc.stdout:
            linha = linha.strip()
            if not linha:
                continue
            msg = json.loads(linha)
            if msg.get("id") == id_:
                return msg
        raise RuntimeError("o servidor fechou sem responder")

    enviar({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {},
        "clientInfo": {"name": "testar_mcp", "version": "0.1"}}})
    inicio = receber(1)
    enviar({"jsonrpc": "2.0", "method": "notifications/initialized"})
    enviar({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    ferramentas = [t["name"] for t in receber(2)["result"]["tools"]]
    resultado = {"servidor": inicio["result"].get("serverInfo"), "ferramentas": ferramentas}
    if chamar:
        enviar({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": chamar, "arguments": args}})
        resultado["chamada"] = receber(3).get("result")
    proc.stdin.close()
    proc.terminate()
    return resultado


def main() -> None:
    if "--" not in sys.argv:
        sys.exit(__doc__)
    i = sys.argv.index("--")
    ap = argparse.ArgumentParser()
    ap.add_argument("--chamar")
    ap.add_argument("--args", default="{}")
    a = ap.parse_args(sys.argv[1:i])
    print(json.dumps(conversar(sys.argv[i + 1:], a.chamar, json.loads(a.args)), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
