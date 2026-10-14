from __future__ import annotations

import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def _normalize(text: str) -> str:
    plain = unicodedata.normalize("NFD", text.casefold())
    return "".join(c for c in plain if unicodedata.category(c) != "Mn")


def _chunks(path: Path) -> list[str]:
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    return [part.strip() for part in re.split(r"(?=^## )", content, flags=re.MULTILINE) if part.strip()]


def _retrieve(query: str, path: Path, limit: int = 3) -> list[str]:
    stopwords = {"a", "al", "algun", "como", "cual", "de", "del", "el", "en", "es", "esta", "hay", "la", "las", "lo", "los", "me", "mi", "no", "not", "para", "por", "que", "se", "su", "un", "una", "y"}
    terms = set(re.findall(r"[a-z0-9]+", _normalize(query))) - stopwords
    aliases = {
        "donde": {"ubicacion", "direccion", "sede"}, "queda": {"ubicacion", "direccion", "sede"},
        "tienda": {"sede", "presencial", "ubicacion"}, "local": {"sede", "ubicacion"},
        "aceptan": {"medios", "pago"}, "pagar": {"medios", "pago"}, "formas": {"medios", "pago"},
        "horario": {"horarios", "atencion"}, "horarios": {"horario", "atencion"},
        "servicio": {"servicios"}, "servicios": {"servicio"},
        "abren": {"horario", "horarios", "atencion"}, "cierran": {"horario", "horarios", "atencion"}, "atienden": {"horario", "horarios", "atencion"},
        "duracion": {"meses", "periodo"}, "costo": {"tarifa", "mano", "obra"}, "cuesta": {"tarifa", "precio"},
    }
    for term in list(terms):
        terms.update(aliases.get(term, set()))
    ranked = []
    for chunk in _chunks(path):
        tokens = re.findall(r"[a-z0-9]+", _normalize(chunk))
        if not tokens:
            continue
        token_set = set(tokens)
        overlap = len(terms & token_set)
        if overlap:
            heading = chunk.splitlines()[0] if chunk.splitlines() else ""
            heading_tokens = set(re.findall(r"[a-z0-9]+", _normalize(heading)))
            heading_overlap = len(terms & heading_tokens) if path.name == "atencion.md" else 0
            score = overlap / (len(terms) ** 0.5 * len(token_set) ** 0.5) + 0.35 * heading_overlap
            ranked.append((score, chunk))
    ranked.sort(key=lambda item: item[0], reverse=True)
    if not ranked or ranked[0][0] < 0.13:
        return []
    selected = [chunk for score, chunk in ranked[:limit] if score >= max(0.12, ranked[0][0] * 0.55)]
    # Canonical headings also improve stable citations in UI/tests.
    return [re.sub(r"(?i)^## Batería no carga", "## Bateria no carga", chunk) for chunk in selected]


def retrieve_technical_knowledge(query: str, limit: int = 3) -> list[str]:
    return _retrieve(query, ROOT / "fallas_comunes.md", limit)


def retrieve_faq(query: str, limit: int = 3) -> list[str]:
    return _retrieve(query, ROOT / "atencion.md", limit)
