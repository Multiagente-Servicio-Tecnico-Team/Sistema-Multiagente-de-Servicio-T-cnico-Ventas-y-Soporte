import unicodedata


def interpret_confirmation(message: str) -> str:
    text = (message or "").strip().casefold()
    if text in {"s�", "s?", "s�", "s?"}:
        return "yes"
    if "�" in text:
        text = text.replace("�", "i")
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    yes = {"si", "acepto", "confirmo", "de acuerdo", "ok", "dale", "perfecto, acepto"}
    no = {"no", "rechazo", "no acepto", "cancelar", "cancelo"}
    if text in yes or text.startswith(("si, acept", "si confirm", "acepto ", "confirmo ")):
        return "yes"
    if text in no or text.startswith(("no, ", "no gracia", "rechazo", "cancel")):
        return "no"
    return "ambiguous"


def parse_confirmation(message: str):
    decision = interpret_confirmation(message)
    return True if decision == "yes" else False if decision == "no" else None
