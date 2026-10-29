# Assistente de Chamados Públicos com LLM

Assistente que responde perguntas em português sobre chamados de serviços públicos. O LLM transforma a pergunta em SQL, o código valida e executa a consulta em modo somente leitura, e o LLM explica **apenas o resultado retornado**. Cada resposta mostra o SQL e a tabela usados, para que possa ser conferida.

A base vem do meu projeto [public-services-etl](https://github.com/ddecry/public-services-etl): 1.560 chamados de 6 cidades, carregados em SQLite.

> "Qual cidade tem o pior percentual de chamados dentro do SLA?"
> → gera o SQL → executa → "Curitiba tem o menor percentual de chamados resolvidos dentro do SLA: 62,4%."

## Como funciona

```
pergunta ──► LLM gera SQL ──► validação ──► SQLite (somente leitura) ──► LLM explica os dados
                 ▲                │ erro de execução
                 └────────────────┘ (uma tentativa de autocorreção)
```

1. **Geração de SQL:** o prompt traz o esquema da tabela com o significado de cada coluna e os valores válidos (cidades, categorias, status), além de dois exemplos (*few-shot*).
2. **Validação:** só aceita uma única instrução `SELECT`/`WITH`, bloqueia comandos de escrita e de sistema e aplica `LIMIT 200`.
3. **Execução segura:** a conexão é aberta com `mode=ro`. Mesmo que um SQL de escrita passasse pela validação, o SQLite recusaria.
4. **Autocorreção:** se a consulta falhar (ex.: coluna inexistente), o erro volta para o modelo, que tenta mais uma vez.
5. **Resposta fundamentada:** o modelo recebe só as linhas retornadas e é instruído a não inventar números. Se o modelo cair nessa etapa, o sistema devolve os dados brutos (*fallback*).
6. **Fora do escopo:** perguntas que a tabela não responde são recusadas em vez de inventadas.

O modelo é intercambiável. Qualquer API compatível com OpenAI funciona: **Ollama** local (gratuito), Groq, OpenAI ou OpenRouter.

## Avaliação

`eval/perguntas.json` tem 15 perguntas com o SQL de referência. O script `eval/avaliar.py` mede a **acurácia de execução**: o resultado do SQL gerado precisa conter o mesmo resultado do SQL de referência, aceitando ordem diferente e colunas extras.

```bash
python -m eval.avaliar
```

| Modelo | Acurácia de execução |
|--------|---------------------|
| _preencher após rodar_ | _x/15_ |

Os testes automatizados (`pytest`) usam um modelo simulado e cobrem a validação de SQL, a conexão somente leitura, a autocorreção, o fallback e o comparador da avaliação.

## Executar

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt

# Opção 1: Ollama local
ollama pull qwen2.5:7b
copy .env.example .env          # Linux/Mac: cp .env.example .env

streamlit run app.py            # interface web
python perguntar.py "Quantos chamados estão abertos por cidade?"   # terminal
pytest                          # testes
```

Para usar o Groq (gratuito), troque as três variáveis no `.env` conforme o exemplo comentado.

## Publicar no Hugging Face Spaces

1. Crie um Space do tipo **Streamlit**.
2. Envie os arquivos deste repositório, incluindo `data/servicos_publicos.db`.
3. Em *Settings → Variables and secrets*, cadastre `LLM_BASE_URL`, `LLM_MODEL` e o secret `LLM_API_KEY` (use Groq, já que o Space não roda Ollama).

## Estrutura

```
assistente/
  agente.py      # fluxo: gerar SQL, validar, executar, autocorrigir, explicar
  seguranca.py   # validação do SQL gerado
  db.py          # conexão somente leitura + descrição do esquema
  llm.py         # cliente compatível com OpenAI (Ollama, Groq, OpenAI)
app.py           # interface Streamlit
perguntar.py     # uso pelo terminal
eval/            # perguntas de referência e script de acurácia
tests/           # testes com modelo simulado
```

## Tecnologias

Python, LLM (text-to-SQL), engenharia de prompt, Ollama, API OpenAI-compatível, SQLite, Streamlit, pytest.
