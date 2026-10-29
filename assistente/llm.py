"""Cliente de LLM intercambiável.

Usa a API compatível com OpenAI, que funciona com:
- Ollama rodando localmente (padrão, gratuito): LLM_BASE_URL=http://localhost:11434/v1
- Groq, OpenAI, OpenRouter e outros: basta trocar LLM_BASE_URL, LLM_API_KEY e LLM_MODEL.
"""

import os
from typing import Protocol

try:  # lê o arquivo .env da pasta do projeto, se existir
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


class ModeloDeLinguagem(Protocol):
    def completar(self, sistema: str, usuario: str) -> str: ...


class ClienteOpenAICompativel:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, modelo: str | None = None):
        from openai import OpenAI

        self.modelo = modelo or os.getenv("LLM_MODEL", "qwen2.5:7b")
        self._cliente = OpenAI(
            base_url=base_url or os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
            api_key=api_key or os.getenv("LLM_API_KEY", "ollama"),
            timeout=float(os.getenv("LLM_TIMEOUT", "60")),
        )

    def completar(self, sistema: str, usuario: str) -> str:
        resposta = self._cliente.chat.completions.create(
            model=self.modelo,
            temperature=0,
            messages=[
                {"role": "system", "content": sistema},
                {"role": "user", "content": usuario},
            ],
        )
        return resposta.choices[0].message.content or ""
