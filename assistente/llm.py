"""Cliente de LLM intercambiável.

Usa o formato de chat compatível com OpenAI, que funciona com:
- Ollama rodando localmente (padrão, gratuito): LLM_BASE_URL=http://localhost:11434/v1
- GitHub Models, Groq, OpenAI, OpenRouter e outros: basta trocar LLM_BASE_URL, LLM_API_KEY e LLM_MODEL.

A chamada é feita com a biblioteca padrão (urllib), sem SDK, para tratar
erros e limites de requisição de forma explícita.
"""

import json
import os
import time
import urllib.error
import urllib.request
from typing import Protocol

try:  # lê o arquivo .env da pasta do projeto, se existir
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


class ModeloDeLinguagem(Protocol):
    def completar(self, sistema: str, usuario: str) -> str: ...


class ErroLLM(RuntimeError):
    """A API do modelo respondeu com erro ou num formato inesperado."""


class ClienteOpenAICompativel:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, modelo: str | None = None,
                 tentativas: int = 5):
        self.modelo = modelo or os.getenv("LLM_MODEL", "qwen2.5:7b")
        self.base_url = (base_url or os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "ollama")
        self.timeout = float(os.getenv("LLM_TIMEOUT", "60"))
        self.tentativas = tentativas

    def completar(self, sistema: str, usuario: str) -> str:
        corpo = json.dumps({
            "model": self.modelo,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": sistema},
                {"role": "user", "content": usuario},
            ],
        }).encode("utf-8")
        requisicao = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=corpo,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                # Alguns provedores (ex.: Groq, via Cloudflare) bloqueiam o
                # User-Agent padrão "Python-urllib".
                "User-Agent": "assistente-chamados-ia/1.0",
            },
            method="POST",
        )

        for tentativa in range(1, self.tentativas + 1):
            try:
                with urllib.request.urlopen(requisicao, timeout=self.timeout) as resposta:
                    texto = resposta.read().decode("utf-8")
                break
            except urllib.error.HTTPError as e:
                detalhe = e.read().decode("utf-8", errors="replace")[:300]
                # 429 = limite de requisições; 5xx = instabilidade. Espera e tenta de novo.
                if e.code in (429, 500, 502, 503, 504) and tentativa < self.tentativas:
                    espera = float(e.headers.get("Retry-After") or 2 ** tentativa)
                    time.sleep(min(espera, 60))
                    continue
                raise ErroLLM(f"HTTP {e.code}: {detalhe}") from e
            except urllib.error.URLError as e:
                if tentativa < self.tentativas:
                    time.sleep(2 ** tentativa)
                    continue
                raise ErroLLM(f"Não foi possível conectar em {self.base_url}: {e.reason}") from e

        try:
            return json.loads(texto)["choices"][0]["message"]["content"] or ""
        except (ValueError, KeyError, IndexError, TypeError) as e:
            raise ErroLLM(f"Resposta inesperada da API: {texto[:300]}") from e
