"""Lista os modelos disponíveis para a chave e escolhe o melhor da lista de preferência.

Uso: python scripts/escolher_modelo.py  -> imprime o id do modelo escolhido
"""

import json
import os
import sys
import urllib.request

PREFERENCIA = [
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-20b",
    "llama-3.1-8b-instant",
]


def main() -> None:
    base = os.environ["LLM_BASE_URL"].rstrip("/")
    req = urllib.request.Request(
        f"{base}/models",
        headers={"Authorization": f"Bearer {os.environ['LLM_API_KEY']}", "User-Agent": "assistente-chamados-ia/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        ids = sorted(m["id"] for m in json.load(r)["data"])
    print("Modelos disponíveis: " + ", ".join(ids), file=sys.stderr)
    escolhido = next((m for m in PREFERENCIA if m in ids), None)
    if not escolhido:
        sys.exit("Nenhum modelo da lista de preferência está disponível.")
    print(escolhido)


if __name__ == "__main__":
    main()
