"""Acesso somente leitura à base de chamados gerada pelo projeto public-services-etl."""

import sqlite3
from pathlib import Path

CAMINHO_PADRAO = Path(__file__).resolve().parent.parent / "data" / "servicos_publicos.db"

# Descrição que vai no prompt: o modelo precisa saber o significado de cada coluna,
# não só o nome, para não inventar valores.
ESQUEMA = """
Tabela service_tickets (um registro por chamado de serviço público):
- id INTEGER: identificador do chamado
- city TEXT: cidade. Valores: 'Belo Horizonte', 'Curitiba', 'Goiânia', 'Recife', 'Rio de Janeiro', 'São Paulo'
- category TEXT: categoria. Valores: 'Buraco na via', 'Coleta de lixo', 'Drenagem', 'Iluminação', 'Árvore'
- channel TEXT: canal de abertura. Valores: 'App', 'Portal', 'Telefone', 'WhatsApp'
- opened_at TEXT: data/hora de abertura no formato ISO 'AAAA-MM-DDTHH:MM:SS' (ano de 2026)
- closed_at TEXT: data/hora de fechamento (NULL se não foi fechado)
- status TEXT: 'Aberto', 'Em andamento' ou 'Resolvido'
- sla_hours INTEGER: prazo de atendimento previsto, em horas
- resolution_hours REAL: horas até a resolução (NULL se não resolvido)
- citizen_rating INTEGER: nota do cidadão de 1 a 5 (NULL se não avaliou)
- within_sla INTEGER: 1 se resolvido dentro do SLA, 0 se fora, NULL se não resolvido
""".strip()


def conectar(caminho: Path | str = CAMINHO_PADRAO) -> sqlite3.Connection:
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(f"Base não encontrada: {caminho}")
    # mode=ro: mesmo que um SQL de escrita passe pela validação, o SQLite recusa.
    return sqlite3.connect(f"file:{caminho.as_posix()}?mode=ro", uri=True, check_same_thread=False)


def executar(conexao: sqlite3.Connection, sql: str) -> tuple[list[str], list[tuple]]:
    cursor = conexao.execute(sql)
    colunas = [d[0] for d in cursor.description]
    return colunas, cursor.fetchall()
