# Gemma 연동의 향후 위치를 남기고 MVP에서는 stub 사용을 명시한다.

from __future__ import annotations


class GemmaUnavailable(RuntimeError):
    pass


def is_configured() -> bool:
    return False


def generate(_prompt: str) -> str:
    raise GemmaUnavailable("Live Gemma is not configured in the MVP skeleton.")
