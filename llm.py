"""Тонкий слой над провайдером. Сменить провайдера: LLM_PROVIDER в .env (anthropic | openai | ollama)."""
import json
import os
import urllib.error
import urllib.request

DEFAULT_MODELS = {"anthropic": "claude-sonnet-5-5", "openai": "gpt-4o-mini",
                  "ollama": "qwen2.5:7b-instruct"}


class LLMError(RuntimeError):
    pass


def get_settings() -> tuple[str, str]:
    provider = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
    if provider not in DEFAULT_MODELS:
        raise LLMError(f"Неизвестный LLM_PROVIDER='{provider}'. Допустимо: anthropic, openai, ollama.")
    return provider, os.getenv("LLM_MODEL") or DEFAULT_MODELS[provider]


def _ollama(system: str, user: str, model: str) -> str:
    """Локальная модель через Ollama (http://localhost:11434). Только стандартная библиотека."""
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    body = json.dumps({
        "model": model, "stream": False, "format": "json",
        "options": {"temperature": 0.2, "num_ctx": 4096},
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
    }).encode("utf-8")
    req = urllib.request.Request(f"{host}/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=int(os.getenv("LLM_TIMEOUT", "600"))) as r:
            return json.loads(r.read().decode("utf-8"))["message"]["content"]
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        hint = f" Модель не скачана? Выполните: ollama pull {model}" if e.code == 404 else ""
        raise LLMError(f"Ollama вернул HTTP {e.code}: {detail}.{hint}") from e
    except urllib.error.URLError as e:
        raise LLMError(f"Не удалось подключиться к Ollama ({host}). "
                       f"Запущен ли он? ({e.reason})") from e


def generate(system: str, user: str, provider: str, model: str) -> str:
    """Возвращает сырой текст ответа модели. Любые сбои API превращаются в LLMError."""
    try:
        if provider == "ollama":
            return _ollama(system, user, model)

        if provider == "anthropic":
            key = os.getenv("ANTHROPIC_API_KEY")
            if not key:
                raise LLMError("Не задан ANTHROPIC_API_KEY (см. .env.example).")
            import anthropic
            client = anthropic.Anthropic(api_key=key, max_retries=3, timeout=60)
            resp = client.messages.create(
                model=model, max_tokens=2000, temperature=0.2,
                system=system, messages=[{"role": "user", "content": user}],
            )
            return "".join(b.text for b in resp.content if b.type == "text")

        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise LLMError("Не задан OPENAI_API_KEY (см. .env.example).")
        from openai import OpenAI
        client = OpenAI(api_key=key, max_retries=3, timeout=60)
        resp = client.chat.completions.create(
            model=model, temperature=0.2,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
        )
        return resp.choices[0].message.content or ""
    except LLMError:
        raise
    except Exception as e:  # ошибки сети, лимиты, авторизация и т. д.
        raise LLMError(f"Ошибка API ({provider}): {type(e).__name__}: {e}") from e
