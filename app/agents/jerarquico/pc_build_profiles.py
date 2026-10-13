"""Curated PC configurations sourced from the local Markdown knowledge base."""

import re
from dataclasses import dataclass
from pathlib import Path


PROFILE_FILE = Path(__file__).parent / "knowledge_base" / "pc_build_profiles.md"
_PROFILE_PATTERN = re.compile(r"(?ms)^## ([a-z0-9_-]+)\s*\n(.*?)(?=^## |\Z)")
_COMPONENT_PATTERN = re.compile(r"(?m)^-\s*([^:]+):\s*`([^`]+)`\s*$")


@dataclass(frozen=True)
class PCBuildProfile:
    identifier: str
    title: str
    uses: tuple[str, ...]
    components: tuple[tuple[str, str], ...]
    compatibility_notes: str


def load_pc_build_profiles() -> tuple[PCBuildProfile, ...]:
    content = PROFILE_FILE.read_text(encoding="utf-8")
    profiles: list[PCBuildProfile] = []
    for match in _PROFILE_PATTERN.finditer(content):
        identifier, body = match.groups()
        title_match = re.search(r"(?m)^\*\*Nombre\*\*:\s*(.+)$", body)
        uses_match = re.search(r"(?m)^\*\*Uso\*\*:\s*(.+)$", body)
        notes_match = re.search(r"(?m)^\*\*Compatibilidad\*\*:\s*(.+)$", body)
        components = tuple(_COMPONENT_PATTERN.findall(body))
        if not title_match or not uses_match or not notes_match or not components:
            raise ValueError(
                f"El perfil {identifier} requiere Nombre, Uso, Compatibilidad "
                "y al menos un componente con código de catálogo."
            )
        profiles.append(
            PCBuildProfile(
                identifier=identifier,
                title=title_match.group(1).strip(),
                uses=tuple(
                    use.strip().casefold()
                    for use in re.split(r"[,;]", uses_match.group(1))
                    if use.strip()
                ),
                components=components,
                compatibility_notes=notes_match.group(1).strip(),
            )
        )
    if not profiles:
        raise ValueError(f"No se encontraron perfiles en {PROFILE_FILE}.")
    return tuple(profiles)


def choose_pc_build_profile(
    intended_use: str,
    profiles: tuple[PCBuildProfile, ...] | None = None,
) -> PCBuildProfile:
    available = profiles or load_pc_build_profiles()
    normalized_use = intended_use.casefold()
    ranked = sorted(
        available,
        key=lambda profile: (
            not any(use in normalized_use for use in profile.uses),
            profile.identifier,
        ),
    )
    return ranked[0]
