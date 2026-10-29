"""Mede a acurácia de execução do text-to-SQL.

Para cada pergunta, compara o resultado do SQL gerado pelo modelo com o do SQL
de referência. Uma resposta é correta quando cada linha esperada aparece numa
linha do resultado (colunas extras e ordem diferente são aceitas).

Uso: python -m eval.avaliar
"""

import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from assistente import db  # noqa: E402
from assistente.agente import Assistente  # noqa: E402
from assistente.llm import ClienteOpenAICompativel  # noqa: E402
from assistente.seguranca import validar_sql  # noqa: E402


def _normalizar(valor):
    if isinstance(valor, float):
        return round(valor, 1)
    return valor


def resultados_equivalentes(esperado: list[tuple], obtido: list[tuple]) -> bool:
    if len(esperado) != len(obtido):
        return False
    restantes = [Counter(map(_normalizar, linha)) for linha in obtido]
    for linha in esperado:
        alvo = Counter(map(_normalizar, linha))
        achou = next((i for i, r in enumerate(restantes) if not alvo - r), None)
        if achou is None:
            return False
        restantes.pop(achou)
    return True


def avaliar(assistente: Assistente, casos: list[dict]) -> dict:
    acertos, detalhes = 0, []
    for caso in casos:
        _, esperado = db.executar(assistente.conexao, caso["sql"])
        inicio = time.perf_counter()
        try:
            sql = assistente.gerar_sql(caso["pergunta"])
            _, obtido = db.executar(assistente.conexao, validar_sql(sql))
            ok = resultados_equivalentes(esperado, obtido)
        except Exception as e:
            sql, ok = f"ERRO: {e}", False
        acertos += ok
        detalhes.append({"pergunta": caso["pergunta"], "ok": ok, "sql": sql,
                         "segundos": round(time.perf_counter() - inicio, 2)})
    return {"acertos": acertos, "total": len(casos), "acuracia": round(acertos / len(casos) * 100, 1), "detalhes": detalhes}


def main() -> None:
    casos = json.loads((Path(__file__).parent / "perguntas.json").read_text(encoding="utf-8"))
    cliente = ClienteOpenAICompativel()
    relatorio = avaliar(Assistente(cliente), casos)
    for d in relatorio["detalhes"]:
        print(f"[{'OK ' if d['ok'] else 'ERR'}] {d['pergunta']}")
        if not d["ok"]:
            print(f"      {d['sql']}")
    print(f"\nModelo: {cliente.modelo}")
    print(f"Acurácia de execução: {relatorio['acertos']}/{relatorio['total']} ({relatorio['acuracia']}%)")
    saida = Path(__file__).parent / "resultado.json"
    saida.write_text(json.dumps({"modelo": cliente.modelo, **relatorio}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Detalhes salvos em {saida}")


if __name__ == "__main__":
    main()
