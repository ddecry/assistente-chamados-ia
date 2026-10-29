import json
import sqlite3
from pathlib import Path

import pytest

from assistente import Assistente, db
from assistente.seguranca import SQLInvalido, validar_sql
from eval.avaliar import resultados_equivalentes


class ModeloFalso:
    """Simula o LLM devolvendo respostas pré-definidas, em ordem."""

    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.chamadas = []

    def completar(self, sistema, usuario):
        self.chamadas.append(usuario)
        r = self.respostas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


@pytest.fixture
def conexao():
    return db.conectar()


# ---------- segurança ----------

@pytest.mark.parametrize("sql", [
    "DELETE FROM service_tickets",
    "DROP TABLE service_tickets",
    "SELECT 1; DELETE FROM service_tickets",
    "UPDATE service_tickets SET status = 'x'",
    "PRAGMA table_info(service_tickets)",
    "ATTACH DATABASE 'x.db' AS x",
    "",
])
def test_bloqueia_sql_perigoso(sql):
    with pytest.raises(SQLInvalido):
        validar_sql(sql)


def test_aceita_select_e_aplica_limite():
    assert validar_sql("SELECT city FROM service_tickets;").endswith("LIMIT 200")
    assert validar_sql("WITH t AS (SELECT 1 AS a) SELECT a FROM t")


def test_conexao_e_somente_leitura(conexao):
    with pytest.raises(sqlite3.OperationalError):
        conexao.execute("DELETE FROM service_tickets")


# ---------- fluxo do assistente ----------

def test_fluxo_completo(conexao):
    modelo = ModeloFalso(
        "```sql\nSELECT COUNT(*) AS total FROM service_tickets\n```",
        "Existem 1.560 chamados na base.",
    )
    r = Assistente(modelo, conexao).perguntar("Quantos chamados existem?")
    assert r.linhas == [(1560,)]
    assert r.texto == "Existem 1.560 chamados na base."
    assert '"total": 1560' in modelo.chamadas[1]  # a explicação recebe o dado real


def test_autocorrige_sql_com_erro(conexao):
    modelo = ModeloFalso(
        "SELECT cidade FROM service_tickets",          # coluna inexistente
        "SELECT DISTINCT city FROM service_tickets",   # corrigido
        "Há 6 cidades.",
    )
    r = Assistente(modelo, conexao).perguntar("Quais cidades existem?")
    assert r.tentativas == 2 and len(r.linhas) == 6
    assert "no such column" in modelo.chamadas[1]


def test_nao_executa_escrita(conexao):
    r = Assistente(ModeloFalso("DELETE FROM service_tickets"), conexao).perguntar("apague tudo")
    assert r.erro and not r.linhas
    assert conexao.execute("SELECT COUNT(*) FROM service_tickets").fetchone()[0] == 1560


def test_fora_do_escopo(conexao):
    r = Assistente(ModeloFalso("FORA_DO_ESCOPO"), conexao).perguntar("Qual a capital da França?")
    assert "não pode ser respondida" in r.texto and r.sql is None


def test_fallback_quando_modelo_falha_na_explicacao(conexao):
    modelo = ModeloFalso("SELECT COUNT(*) AS total FROM service_tickets", TimeoutError("sem modelo"))
    r = Assistente(modelo, conexao).perguntar("Quantos chamados?")
    assert "1560" in r.texto


# ---------- avaliação ----------

def test_comparador_de_resultados():
    assert resultados_equivalentes([("Recife",)], [("Recife", 61.2)])
    assert resultados_equivalentes([("A", 1), ("B", 2)], [("B", 2), ("A", 1)])
    assert resultados_equivalentes([(65.34,)], [(65.3,)])
    assert not resultados_equivalentes([("Recife",)], [("Curitiba",)])


def test_sql_de_referencia_executa(conexao):
    casos = json.loads((Path(__file__).parent.parent / "eval" / "perguntas.json").read_text(encoding="utf-8"))
    for caso in casos:
        _, linhas = db.executar(conexao, validar_sql(caso["sql"]))
        assert linhas, caso["pergunta"]
