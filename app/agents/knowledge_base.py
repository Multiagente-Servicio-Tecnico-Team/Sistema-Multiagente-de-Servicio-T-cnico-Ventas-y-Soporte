from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from pathlib import Path


KNOWLEDGE_DIRECTORY = Path(__file__).parent / "knowledge"
TOKEN_PATTERN = re.compile(r"[a-záéíóúüñ0-9]+", re.IGNORECASE)
STOP_WORDS = {
    "a", "al", "algun", "alguna", "algunas", "algunos", "como", "con", "cuando",
    "de", "del", "desde", "el", "ella", "en", "es", "esta", "este", "la", "las",
    "lo", "los", "mi", "mis", "no", "o", "para", "pero", "por", "que", "se", "sin", "su",
    "sus", "un", "una", "unas", "uno", "unos", "y",
}


def _tokens(text: str) -> list[str]:
    normalized = "".join(
        character
        for character in unicodedata.normalize("NFD", text.casefold())
        if unicodedata.category(character) != "Mn"
    )
    return [
        token
        for token in TOKEN_PATTERN.findall(normalized)
        if token not in STOP_WORDS
    ]


def _load_sections() -> list[tuple[str, str, list[str]]]:
    sections: list[tuple[str, str, list[str]]] = []
    for path in sorted(KNOWLEDGE_DIRECTORY.glob("*.md")):
        title = ""
        content: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "):
                if title:
                    body = "\n".join(content).strip()
                    sections.append((title, body, _tokens(f"{title}\n{body}")))
                title = line[3:].strip()
                content = []
            elif title:
                content.append(line)
        if title:
            body = "\n".join(content).strip()
            sections.append((title, body, _tokens(f"{title}\n{body}")))
    return sections


def retrieve_technical_knowledge(query: str, limit: int = 3) -> list[str]:
    query_tokens = set(_tokens(query))
    if not query_tokens or limit <= 0:
        return []

    sections = _load_sections()
    if not sections:
        return []

    document_frequencies = Counter(
        token
        for _, _, tokens in sections
        for token in set(tokens)
    )
    average_length = sum(len(tokens) for _, _, tokens in sections) / len(sections)
    ranked: list[tuple[float, str, str]] = []
    for title, body, tokens in sections:
        frequencies = Counter(tokens)
        score = 0.0
        for token in query_tokens:
            frequency = frequencies[token]
            if frequency == 0:
                continue
            document_frequency = document_frequencies[token]
            inverse_frequency = math.log(
                1 + (len(sections) - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            length_normalizer = 1.5 * (
                1 - 0.75 + 0.75 * len(tokens) / max(average_length, 1)
            )
            score += inverse_frequency * frequency * 2.5 / (frequency + length_normalizer)
        if score > 0:
            ranked.append((score, title, body))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [f"## {title}\n{body}" for _, title, body in ranked[:limit]]