import re
import unicodedata


def parse_confirmation(message: str) -> bool | None:
    normalized = "".join(
        character
        for character in unicodedata.normalize("NFD", message.casefold())
        if unicodedata.category(character) != "Mn"
    )
    normalized = " ".join(re.findall(r"[a-z0-9]+", normalized))

    if normalized in {
        "si",
        "si confirmo",
        "confirmo",
        "confirmar",
        "si autorizo",
        "de acuerdo",
        "acepto",
        "correcto",
    }:
        return True
    if normalized in {"no", "no gracias", "cancelo", "cancelar", "rechazo", "rechazar"}:
        return False
    return None