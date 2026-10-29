"""Fluxo do assistente: pergunta -> SQL -> validação -> execução -> resposta fundamentada.

O modelo nunca acessa o banco diretamente. Ele só escreve o SQL e depois
explica o resultado que o código executou, o que reduz alucinação e deixa
cada resposta verificável (a interface mostra o SQL e a tabela usados).
"""

import json
import re
import sqlite3
from dataclasses import dataclass, field

from . import db
from .llm import ModeloDeLinguagem
from .seguranca import SQLInvalido, validar_sql

PROMPT_SQL = f"""Você converte perguntas em português em UMA consulta SQLite de leitura.

{db.ESQUEMA}

Regras:
- Responda só com a consulta dentro de um bloco ```sql ... ```, sem explicações.
- Use apenas SELECT ou WITH. Nunca altere dados.
- Use os valores exatamente como estão no esquema (acentos e maiúsculas).
- Para meses use strftime('%m', opened_at); para percentuais use ROUND(AVG(...) * 100, 1).
- Taxas de SLA e tempo de resolução consideram só chamados resolvidos (coluna não nula).
- Dê nomes claros em português às colunas calculadas.
- Se a pergunta não puder ser respondida com esta tabela, responda exatamente: FORA_DO_ESCOPO

Exemplos:
Pergunta: Quantos chamados existem por canal?
```sql
SELECT channel AS canal, COUNT(*) AS chamados FROM service_tickets GROUP BY channel ORDER BY chamados DESC
```
Pergunta: Qual cidade tem o pior percentual dentro do SLA?
```sql
SELECT city AS cidade, ROUND(AVG(within_sla) * 100, 1) AS pct_dentro_sla
FROM service_tickets WHERE within_sla IS NOT NULL
GROUP BY city ORDER BY pct_dentro_sla ASC LIMIT 1
```"""

PROMPT_RESPOSTA = """Você é um analista de dados que explica resultados para gestores públicos.
Responda em português, em no máximo 4 frases, usando SOMENTE os dados fornecidos.
Cite os números. Não invente valores, causas ou recomendações que os dados não mostram.
Se o resultado estiver vazio, diga que não há registros para essa pergunta."""

MAX_LINHAS_NO_PROMPT = 50


@dataclass
class Resposta:
    pergunta: str
    texto: str
    sql: str | None = None
    colunas: list[str] = field(default_factory=list)
    linhas: list[tuple] = field(default_factory=list)
    erro: str | None = None
    tentativas: int = 0


def extrair_sql(texto: str) -> str:
    bloco = re.search(r"```(?:sql)?\s*(.*?)```", texto, re.DOTALL | re.IGNORECASE)
    return (bloco.group(1) if bloco else texto).strip()


class Assistente:
    def __init__(self, modelo: ModeloDeLinguagem, conexao: sqlite3.Connection | None = None, max_tentativas: int = 2):
        self.modelo = modelo
        self.conexao = conexao or db.conectar()
        self.max_tentativas = max_tentativas

    def gerar_sql(self, pergunta: str, erro_anterior: str | None = None, sql_anterior: str | None = None) -> str:
        mensagem = f"Pergunta: {pergunta}"
        if erro_anterior:
            # Autocorreção: devolve ao modelo o SQL que falhou e o erro.
            mensagem += f"\n\nA consulta anterior falhou.\nSQL: {sql_anterior}\nErro: {erro_anterior}\nCorrija a consulta."
        return extrair_sql(self.modelo.completar(PROMPT_SQL, mensagem))

    def perguntar(self, pergunta: str) -> Resposta:
        pergunta = pergunta.strip()
        if not pergunta:
            return Resposta(pergunta, "Digite uma pergunta sobre os chamados.")

        sql, erro = None, None
        for tentativa in range(1, self.max_tentativas + 1):
            sql = self.gerar_sql(pergunta, erro, sql)
            if "FORA_DO_ESCOPO" in sql.upper():
                return Resposta(pergunta, "Essa pergunta não pode ser respondida com a base de chamados.", tentativas=tentativa)
            try:
                colunas, linhas = db.executar(self.conexao, validar_sql(sql))
            except SQLInvalido as e:
                # Tentativa de escrita não ganha segunda chance.
                return Resposta(pergunta, "Não executei a consulta gerada por segurança.", sql=sql, erro=str(e), tentativas=tentativa)
            except sqlite3.Error as e:
                erro = str(e)
                continue
            texto = self.explicar(pergunta, sql, colunas, linhas)
            return Resposta(pergunta, texto, sql, colunas, linhas, tentativas=tentativa)

        return Resposta(pergunta, "Não consegui montar uma consulta válida para essa pergunta.", sql=sql, erro=erro, tentativas=self.max_tentativas)

    def explicar(self, pergunta: str, sql: str, colunas: list[str], linhas: list[tuple]) -> str:
        dados = [dict(zip(colunas, l)) for l in linhas[:MAX_LINHAS_NO_PROMPT]]
        mensagem = (
            f"Pergunta: {pergunta}\nSQL executado: {sql}\n"
            f"Resultado ({len(linhas)} linhas, mostrando até {MAX_LINHAS_NO_PROMPT}):\n"
            f"{json.dumps(dados, ensure_ascii=False, default=str)}"
        )
        try:
            return self.modelo.completar(PROMPT_RESPOSTA, mensagem).strip()
        except Exception:
            # Fallback: sem modelo disponível, ainda devolve o dado em texto.
            return f"Resultado da consulta ({len(linhas)} linhas): {json.dumps(dados[:5], ensure_ascii=False, default=str)}"
