"""LLM providers.

- fake: deterministic, offline, free. Builds an "answer" by quoting the first
        sentence of the top evidence passages with their [E#] labels. It only
        exists so the pipeline and tests run without a model; it is NOT a baseline.
- openai_compatible: any server implementing POST /chat/completions:
        OpenAI, Groq, OpenRouter, Together, or a local Ollama
        (LLM_BASE_URL=http://localhost:11434/v1, no API key needed).

Every call reports token usage and latency so cost can be measured per run.
"""

import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlparse

import httpx

from app.core.config import Settings, get_settings
from app.core.errors import ConfigurationError, ExternalServiceError
from app.rag.chunking import approx_tokens

logger = logging.getLogger(__name__)

_THINK_BLOCK = re.compile(r"<think>.*?</think>\s*", re.DOTALL)


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    usage_estimated: bool = False  # True if the provider did not report token counts


class LLMProvider(ABC):
    model: str

    @abstractmethod
    def complete(
        self, messages: list[ChatMessage], *, temperature: float, max_tokens: int
    ) -> LLMResponse: ...


class FakeLLM(LLMProvider):
    model = "fake-extractive"
    _EVIDENCE = re.compile(r"^\[(E\d+)\][^\n]*\n(.+?)(?=\n\[E\d+\]|\n</evidence>|\Z)", re.M | re.S)

    def complete(self, messages, *, temperature, max_tokens):
        started = time.perf_counter()
        prompt = "\n".join(m.content for m in messages)
        evidence = self._EVIDENCE.findall(prompt.split("<evidence>", 1)[-1])
        if not evidence:
            text = "INSUFFICIENT_EVIDENCE: No evidence was provided."
        else:
            sentences = []
            for label, body in evidence[:2]:
                first = re.split(r"(?<=[.!?])\s", body.strip(), maxsplit=1)[0].rstrip(".")
                sentences.append(f"{first} [{label}].")
            text = " ".join(sentences)
        return LLMResponse(
            text=text,
            model=self.model,
            prompt_tokens=approx_tokens(prompt),
            completion_tokens=approx_tokens(text),
            latency_ms=round((time.perf_counter() - started) * 1000),
            usage_estimated=True,
        )


class OpenAICompatibleLLM(LLMProvider):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 120.0,
        reasoning_effort: str = "",
    ):
        host = urlparse(base_url).hostname or ""
        if not api_key and host not in ("localhost", "127.0.0.1", "host.docker.internal"):
            raise ConfigurationError("LLM_API_KEY is required for a remote LLM provider.")
        self.model = model
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._timeout = timeout
        self._reasoning_effort = reasoning_effort

    def complete(self, messages, *, temperature, max_tokens):
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if self._reasoning_effort:
            payload["reasoning_effort"] = self._reasoning_effort
        started = time.perf_counter()
        error = "unknown error"
        for attempt in range(3):
            try:
                response = httpx.post(
                    self._url, json=payload, headers=self._headers, timeout=self._timeout
                )
            except httpx.TimeoutException:
                error = "timeout"
                break  # a timed-out generation is unlikely to succeed on immediate retry
            except httpx.HTTPError as exc:
                error = type(exc).__name__
            else:
                if response.status_code == 200:
                    return self._parse(response.json(), messages, started)
                error = f"HTTP {response.status_code}"
                if response.status_code not in (429, 500, 502, 503, 504):
                    break
            time.sleep(2**attempt)
        logger.error("LLM call failed: %s", error)
        message = (
            "The language model took too long to respond."
            if error == "timeout"
            else "The language model service is unavailable. Please try again."
        )
        raise ExternalServiceError(message)

    def _parse(self, body: dict, messages: list[ChatMessage], started: float) -> LLMResponse:
        try:
            text = body["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise ExternalServiceError("The language model returned a malformed reply.") from exc
        text = _THINK_BLOCK.sub("", text).strip()  # reasoning models (e.g. Qwen3) "think" first
        usage = body.get("usage") or {}
        estimated = not usage
        return LLMResponse(
            text=text,
            model=body.get("model", self.model),
            prompt_tokens=usage.get("prompt_tokens")
            or approx_tokens(" ".join(m.content for m in messages)),
            completion_tokens=usage.get("completion_tokens") or approx_tokens(text),
            latency_ms=round((time.perf_counter() - started) * 1000),
            usage_estimated=estimated,
        )


def estimate_cost_usd(response: LLMResponse, settings: Settings) -> float:
    return (
        response.prompt_tokens * settings.llm_price_input_per_1m
        + response.completion_tokens * settings.llm_price_output_per_1m
    ) / 1_000_000


def build_llm(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "openai_compatible":
        return OpenAICompatibleLLM(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key.get_secret_value(),
            model=settings.llm_model,
            timeout=settings.llm_timeout_seconds,
            reasoning_effort=settings.llm_reasoning_effort,
        )
    return FakeLLM()


@lru_cache
def get_llm() -> LLMProvider:
    return build_llm(get_settings())
