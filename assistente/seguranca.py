"""Validação do SQL gerado pelo modelo antes de qualquer execução.

Duas camadas de proteção:
1. esta validação textual (só uma instrução, começando com SELECT ou WITH,
   sem palavras de escrita);
2. a conexão SQLite aberta em modo somente leitura (ver db.py).
"""

import re

LIMITE_LINHAS = 200

PROIBIDAS = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum|reindex|trigger)\b",
    re.IGNORECASE,
)


class SQLInvalido(ValueError):
    """O SQL gerado não pode ser executado."""


def _remover_comentarios(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", " ", sql)


def validar_sql(sql: str) -> str:
    """Devolve o SQL limpo e com limite de linhas, ou levanta SQLInvalido."""
    limpo = _remover_comentarios(sql).strip().rstrip(";").strip()
    if not limpo:
        raise SQLInvalido("O modelo não gerou nenhuma consulta.")
    if ";" in limpo:
        raise SQLInvalido("Só é permitida uma consulta por vez.")
    if not re.match(r"^(select|with)\b", limpo, re.IGNORECASE):
        raise SQLInvalido("Só consultas de leitura (SELECT ou WITH) são permitidas.")
    if PROIBIDAS.search(limpo):
        raise SQLInvalido("A consulta contém um comando de escrita ou de sistema.")
    return f"SELECT * FROM ({limpo}) LIMIT {LIMITE_LINHAS}"
