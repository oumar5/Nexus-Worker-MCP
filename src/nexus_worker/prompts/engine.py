"""Moteur de sélection et de formatage des prompts système.

Charge les templates Markdown depuis le répertoire templates/,
les met en cache, et injecte les variables dynamiques.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Répertoire par défaut des templates (à côté de ce fichier)
_DEFAULT_TEMPLATES_DIR = Path(__file__).parent / "templates"


class PromptEngine:
    """Charge et formate les templates de prompts système.

    Les templates sont des fichiers Markdown stockés dans le répertoire
    templates/. Le nom du fichier correspond au nom de l'outil
    (ex: generate.md pour worker_generate_code).

    Attributes:
        templates_dir: Répertoire contenant les templates Markdown.
    """

    def __init__(self, templates_dir: Path | None = None) -> None:
        """Initialise le moteur de prompts.

        Args:
            templates_dir: Répertoire des templates. Si None, utilise
                          le répertoire par défaut (templates/ à côté de ce fichier).
        """
        self.templates_dir = templates_dir or _DEFAULT_TEMPLATES_DIR
        self._cache: dict[str, str] = {}

    def get_system_prompt(self, tool_name: str, **variables: Any) -> str:
        """Retourne le prompt système pour un outil donné.

        Charge le template depuis le cache ou le disque, puis injecte
        les variables dynamiques.

        Args:
            tool_name: Nom de l'outil (ex: "generate", "analyze").
            **variables: Variables à injecter dans le template
                        (ex: context="...", language="python").

        Returns:
            Le prompt système formaté prêt à envoyer au Worker.
        """
        template = self._load_template(tool_name)

        # Injecter les variables avec un fallback pour les variables non fournies
        try:
            return template.format_map(_SafeFormatDict(variables))
        except (KeyError, ValueError):
            # Si le formatage échoue, retourner le template brut
            return template

    def list_templates(self) -> list[str]:
        """Liste les templates disponibles.

        Returns:
            Liste des noms de templates (sans l'extension .md).
        """
        if not self.templates_dir.is_dir():
            return []
        return sorted(p.stem for p in self.templates_dir.glob("*.md"))

    def reload(self) -> None:
        """Vide le cache pour forcer le rechargement des templates."""
        self._cache.clear()

    def _load_template(self, tool_name: str) -> str:
        """Charge un template depuis le disque avec mise en cache.

        Args:
            tool_name: Nom de l'outil (correspond au nom du fichier .md).

        Returns:
            Contenu brut du template.

        Raises:
            FileNotFoundError: Si le template n'existe pas.
        """
        if tool_name not in self._cache:
            path = self.templates_dir / f"{tool_name}.md"
            if not path.is_file():
                raise FileNotFoundError(
                    f"Template introuvable: {path}. Templates disponibles: {self.list_templates()}"
                )
            self._cache[tool_name] = path.read_text(encoding="utf-8")
        return self._cache[tool_name]


class _SafeFormatDict(dict):
    """Dict qui retourne la clé elle-même pour les variables manquantes.

    Permet d'utiliser str.format_map() sans lever de KeyError
    si certaines variables ne sont pas fournies.
    """

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"
