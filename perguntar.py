"""Uso pelo terminal: python perguntar.py "Qual cidade tem mais chamados abertos?" """

import sys

from assistente import Assistente
from assistente.llm import ClienteOpenAICompativel


def main() -> None:
    if len(sys.argv) < 2:
        print('Uso: python perguntar.py "sua pergunta"')
        sys.exit(1)
    r = Assistente(ClienteOpenAICompativel()).perguntar(" ".join(sys.argv[1:]))
    if r.sql:
        print(f"SQL:\n{r.sql}\n")
    if r.erro:
        print(f"Aviso: {r.erro}\n")
    print(r.texto)


if __name__ == "__main__":
    main()
