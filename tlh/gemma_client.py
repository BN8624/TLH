# Gemma live 호출을 env 기반으로 감싸는 얇은 adapter를 제공한다.

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from typing import Callable, Mapping

from .schemas import TaskCard


DEFAULT_MODEL = "gemma-3-27b-it"


class GemmaUnavailable(RuntimeError):
    pass


@dataclass
class GemmaConfig:
    api_key: str
    model: str = DEFAULT_MODEL
    timeout_seconds: float = 60.0
    max_output_tokens: int = 4096


@dataclass
class GemmaResponse:
    success: bool
    text: str = ""
    error: str = ""
    model: str = ""


def load_config(env: Mapping[str, str] | None = None) -> GemmaConfig:
    env = env or os.environ
    api_key = env.get("TLH_GEMMA_API_KEY", "").strip()
    if not api_key:
        raise GemmaUnavailable("TLH_GEMMA_API_KEY is not configured.")
    return GemmaConfig(
        api_key=api_key,
        model=env.get("TLH_GEMMA_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        timeout_seconds=_float_env(env, "TLH_GEMMA_TIMEOUT_SECONDS", 60.0),
        max_output_tokens=_int_env(env, "TLH_GEMMA_MAX_OUTPUT_TOKENS", 4096),
    )


def is_configured(env: Mapping[str, str] | None = None) -> bool:
    env = env or os.environ
    return bool(env.get("TLH_GEMMA_API_KEY", "").strip())


def build_worker_prompt(card: TaskCard) -> str:
    return "\n".join(
        [
            "You are a TLH worker processing exactly one TaskCard.",
            "Do not write files. Do not run shell commands. Do not produce the final answer.",
            "Return only a concise JSON object. Do not wrap it in a markdown code fence.",
            "Use summary, findings, risks, assumptions, open_questions, and attach_notes fields.",
            "",
            "TaskCard.",
            f"- task_id: {card.task_id}",
            f"- title: {card.title}",
            f"- goal: {card.goal}",
            f"- worker_role: {card.worker_role}",
            f"- expected_output: {card.expected_output}",
            f"- attach_point: {card.attach_point}",
            f"- merge_key: {card.merge_key}",
            "",
            "Input context.",
            "\n\n".join(card.input_context),
        ]
    )


def generate(
    prompt: str,
    config: GemmaConfig | None = None,
    client_factory: Callable[[GemmaConfig], Callable[[str], str]] | None = None,
) -> GemmaResponse:
    try:
        config = config or load_config()
    except GemmaUnavailable as exc:
        return GemmaResponse(success=False, error=str(exc), model="")

    def call() -> str:
        if client_factory:
            return client_factory(config)(prompt)
        return _generate_with_optional_sdk(prompt, config)

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(call)
    try:
        text = future.result(timeout=config.timeout_seconds)
    except TimeoutError:
        executor.shutdown(wait=False, cancel_futures=True)
        return GemmaResponse(
            success=False,
            error=f"Gemma call timed out after {config.timeout_seconds:g} seconds.",
            model=config.model,
        )
    except Exception as exc:  # noqa: BLE001 - adapter boundary must convert all SDK errors.
        executor.shutdown(wait=False, cancel_futures=True)
        return GemmaResponse(success=False, error=sanitize_error(str(exc), config), model=config.model)
    executor.shutdown(wait=True)
    return GemmaResponse(success=True, text=str(text or ""), model=config.model)


def sanitize_error(error: str, config: GemmaConfig | None = None) -> str:
    if not config or not config.api_key:
        return error
    return error.replace(config.api_key, "[REDACTED]")


def _generate_with_optional_sdk(prompt: str, config: GemmaConfig) -> str:
    try:
        from google import genai  # type: ignore

        client = genai.Client(api_key=config.api_key)
        response = client.models.generate_content(
            model=config.model,
            contents=prompt,
            config={"max_output_tokens": config.max_output_tokens},
        )
        return getattr(response, "text", "") or str(response)
    except ImportError:
        pass

    try:
        import google.generativeai as genai_legacy  # type: ignore

        genai_legacy.configure(api_key=config.api_key)
        model = genai_legacy.GenerativeModel(config.model)
        response = model.generate_content(prompt, generation_config={"max_output_tokens": config.max_output_tokens})
        return getattr(response, "text", "") or str(response)
    except ImportError as exc:
        raise GemmaUnavailable("No supported Google GenAI SDK is installed.") from exc


def _float_env(env: Mapping[str, str], key: str, default: float) -> float:
    try:
        return float(env.get(key, default))
    except (TypeError, ValueError):
        return default


def _int_env(env: Mapping[str, str], key: str, default: int) -> int:
    try:
        return int(env.get(key, default))
    except (TypeError, ValueError):
        return default
