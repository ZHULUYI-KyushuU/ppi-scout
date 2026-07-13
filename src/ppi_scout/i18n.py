"""Small, dependency-free internationalisation helpers for the CLI."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("zh-CN", "en", "ja")

_ALIASES = {
    "1": "zh-CN",
    "zh": "zh-CN",
    "zh-cn": "zh-CN",
    "cn": "zh-CN",
    "chinese": "zh-CN",
    "中文": "zh-CN",
    "2": "en",
    "en": "en",
    "english": "en",
    "英文": "en",
    "英語": "en",
    "3": "ja",
    "ja": "ja",
    "jp": "ja",
    "japanese": "ja",
    "日本語": "ja",
    "日文": "ja",
}

# These strings keep error reporting usable even if an installed locale file is
# accidentally missing. Full CLI text lives in locales/*.json.
_BUILTIN_EN = {
    "language_prompt": (
        "Choose a language / 请选择语言 / 言語を選択してください "
        "[1 中文, 2 English, 3 日本語]: "
    ),
    "invalid_language": "Please enter 1, 2, 3, zh-CN, en, or ja.",
    "error_prefix": "Error",
}


def normalize_language(value: str | None, default: str = DEFAULT_LANGUAGE) -> str:
    """Return a supported language code from a user-facing alias."""

    if value is None or not str(value).strip():
        return default
    raw = str(value).strip()
    if raw in SUPPORTED_LANGUAGES:
        return raw
    return _ALIASES.get(raw.casefold(), default)


def _locale_candidates(language: str) -> list[Path]:
    filename = f"{language}.json"
    candidates: list[Path] = []
    if configured := os.environ.get("PPI_SCOUT_LOCALES"):
        candidates.append(Path(configured).expanduser() / filename)

    # Editable/source checkout: <repo>/src/ppi_scout/i18n.py -> <repo>/locales
    candidates.append(Path(__file__).resolve().parents[2] / "locales" / filename)
    # ``pip install --target DIR`` places data files under DIR/share while the
    # package itself lives under DIR/ppi_scout; sys.prefix does not point there.
    candidates.append(
        Path(__file__).resolve().parents[1] / "share" / "ppi-scout" / "locales" / filename
    )
    # Wheel installation via tool.setuptools.data-files.
    candidates.append(Path(sys.prefix) / "share" / "ppi-scout" / "locales" / filename)
    return candidates


def load_messages(language: str) -> dict[str, str]:
    """Load a locale, falling back key-by-key to English."""

    language = normalize_language(language)

    def load_one(code: str) -> dict[str, str]:
        for path in _locale_candidates(code):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (FileNotFoundError, OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                return {str(key): str(value) for key, value in payload.items()}
        return {}

    english = {**_BUILTIN_EN, **load_one("en")}
    if language == "en":
        return english
    return {**english, **load_one(language)}


@dataclass(frozen=True)
class Translator:
    """Translate message keys and safely apply named format fields."""

    language: str
    messages: Mapping[str, str]

    @classmethod
    def for_language(cls, language: str | None) -> "Translator":
        code = normalize_language(language)
        return cls(code, load_messages(code))

    def t(self, key: str, **values: object) -> str:
        template = self.messages.get(key, key)
        try:
            return template.format(**values)
        except (KeyError, ValueError):
            return template


def choose_language(
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> str:
    """Ask for Chinese, English, or Japanese until a valid choice is made."""

    prompt = _BUILTIN_EN["language_prompt"]
    while True:
        answer = input_fn(prompt).strip()
        if answer in SUPPORTED_LANGUAGES or answer.casefold() in _ALIASES:
            return normalize_language(answer)
        output_fn(_BUILTIN_EN["invalid_language"])
