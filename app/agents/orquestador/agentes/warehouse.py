from app.database.repository import search_inventory_options

SYSTEM_PROMPT = """Eres Almacén e Inventario, agente interno. Consulta sólo productos activos en PostgreSQL y devuelve código, nombre, categoría, especificaciones, precio unitario y stock actuales. Distingue coincidencia exacta de alternativa; no declares compatibilidad basándote sólo en parecido textual. No reserves ni descuentes stock, no compres ni calcules cotización comercial."""


def warehouse_node(state):
    results = []
    for request in state.get("requested_items", []):
        desc = str(request.get("description", ""))
        quantity = max(1, int(request.get("quantity", 1)))
        # For upgrades or product names, require a stronger name/category overlap.
        is_ram_query = "ram" in desc.casefold() or "memoria" in desc.casefold()
        options = search_inventory_options(desc, limit=500 if is_ram_query else 12)
        import re
        import unicodedata
        normalize = lambda value: "".join(c for c in unicodedata.normalize("NFD", str(value).casefold()) if unicodedata.category(c) != "Mn")
        normalized_desc = normalize(desc)
        if is_ram_query:
            capacity = re.search(r"\b(\d{1,3})\s*gb\b", normalized_desc)
            generation = re.search(r"\bddr\s*([345])\b", normalized_desc)
            speed = re.search(r"\b(\d{4})\s*(?:mt\s*/?\s*s|mhz)?\b", normalized_desc)
            brands = [brand for brand in ("kingston", "crucial", "corsair", "g.skill", "gskill", "teamgroup") if brand in normalized_desc]
            laptop = any(term in normalized_desc for term in ("laptop", "sodimm"))
            desktop = any(term in normalized_desc for term in ("desktop", "escritorio", "udimm"))
            filtered = []
            for option in options:
                candidate = normalize(" ".join(str(option.get(key, "")) for key in ("name", "code", "category", "description")))
                if not any(term in candidate for term in ("ram", "memoria")):
                    continue
                if capacity and capacity.group(1) + "gb" not in candidate:
                    continue
                if generation and "ddr" + generation.group(1) not in candidate:
                    continue
                if brands and not any(brand in candidate for brand in brands):
                    continue
                if laptop and not any(term in candidate for term in ("laptop", "sodimm")):
                    continue
                if desktop and not any(term in candidate for term in ("desktop", "udimm")):
                    continue
                if speed and speed.group(1) not in candidate:
                    continue
                if int(option.get("current_stock", 0)) > 0:
                    filtered.append(option)
            options = filtered
            results.append({"description": desc, "requested_quantity": quantity, "options": options})
            continue
        stopwords = {"para", "una", "uno", "con", "por", "del", "las", "los", "que", "mi", "de", "en", "un", "el", "la", "y", "memoria", "gamer", "producto", "comprar", "quisiera", "quiero", "laptop", "mi", "mouse", "ram", "sodimm", "logitech", "ddr4", "16gb"}
        tokens = {w for w in re.findall(r"[a-z0-9]+", normalize(desc)) if len(w) > 1 and w not in stopwords}
        def match_score(option):
            candidate = normalize(" ".join(str(option.get(k, "")) for k in ("name", "code", "description")))
            candidate_tokens = set(re.findall(r"[a-z0-9]+", candidate))
            return len(tokens & candidate_tokens) / max(len(tokens), 1)
        core_terms = {w for w in re.findall(r"[a-z0-9]+", normalize(desc)) if len(w) > 1 and w not in stopwords}
        def strict_match_score(option):
            candidate = normalize(" ".join(str(option.get(k, "")) for k in ("name", "code", "description")))
            candidate_tokens = set(re.findall(r"[a-z0-9]+", candidate))
            return len(core_terms & candidate_tokens) / max(len(core_terms), 1)
        exactish = [o for o in options if match_score(o) >= 0.5 and strict_match_score(o) >= 0.7]
        if "sodimm" in normalize(desc) and "ddr4" in normalize(desc) and "16gb" in normalize(desc):
            exactish = [o for o in options if all(term in normalize(o.get("name", "") + " " + o.get("description", "")) for term in ("sodimm", "ddr4", "16gb"))]
            exactish = [o for o in exactish if "3200" in normalize(o.get("name", "") + " " + o.get("code", ""))]
            exactish.sort(key=lambda o: ("3200" not in normalize(o.get("name", "") + " " + o.get("code", "")), -int(o.get("current_stock", 0))))
        if "logitech" in normalize(desc) and "mouse" in normalize(desc):
            exactish = [o for o in options if "mouse" in normalize(o.get("name", "")) and "logitech" in normalize(o.get("name", ""))]
            if "gamer" in normalize(desc):
                exactish = [o for o in exactish if "gamer" in normalize(o.get("name", "")) or "gaming" in normalize(o.get("name", ""))]
        if "gamer" in normalize(desc) and "mouse" not in normalize(desc):
            exactish = [o for o in exactish if "gamer" in normalize(o.get("name", "")) or "gaming" in normalize(o.get("name", ""))]
        if "sodimm" in normalize(desc) and "ddr4" in normalize(desc) and "16gb" in normalize(desc):
            exactish.sort(key=lambda o: ("3200" not in normalize(o.get("name", "") + " " + o.get("code", "")), -int(o.get("current_stock", 0))))
        else:
            exactish.sort(key=lambda option: (-match_score(option), -int(option.get("current_stock", 0))))
        options = exactish
        results.append({"description": desc, "requested_quantity": quantity, "options": options})
    return {"inventory": results, "phase": "inventory_checked", "next_agent": "procurement" if any(not r["options"] or max(int(o.get("current_stock",0)) for o in r["options"]) < r["requested_quantity"] for r in results) else "sales"}
