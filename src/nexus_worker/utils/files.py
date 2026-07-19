"""Utilitaires de lecture et écriture de fichiers sécurisée.

Vérifie les chemins autorisés, gère les encodages,
et découpe les fichiers volumineux en chunks.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileChunk:
    """Un morceau de fichier avec ses métadonnées de position.

    Attributes:
        content: Le contenu textuel du chunk.
        start_line: Numéro de la première ligne (1-indexed).
        end_line: Numéro de la dernière ligne (1-indexed).
    """

    content: str
    start_line: int
    end_line: int


def is_path_allowed(file_path: Path, allowed_paths: list[Path]) -> bool:
    """Vérifie qu'un chemin de fichier est dans les répertoires autorisés.

    Args:
        file_path: Chemin à vérifier (sera résolu en absolu).
        allowed_paths: Liste des répertoires autorisés.

    Returns:
        True si le fichier est dans un répertoire autorisé.
    """
    resolved = file_path.resolve()
    return any(resolved == allowed or allowed in resolved.parents for allowed in allowed_paths)


def read_file_safe(
    file_path: str | Path,
    allowed_paths: list[Path] | None = None,
    focus_lines: str | None = None,
) -> tuple[str, int]:
    """Lit un fichier de manière sécurisée avec vérification des permissions.

    Args:
        file_path: Chemin du fichier à lire.
        allowed_paths: Répertoires autorisés. Si None, pas de restriction.
        focus_lines: Plage de lignes optionnelle (ex: "100-200").

    Returns:
        Tuple (contenu, nombre_total_de_lignes).

    Raises:
        FileNotFoundError: Si le fichier n'existe pas.
        PermissionError: Si le fichier est hors des chemins autorisés.
        ValueError: Si le format focus_lines est invalide.
    """
    path = Path(file_path).resolve()

    if not path.is_file():
        raise FileNotFoundError(f"Fichier introuvable: {path}")

    if allowed_paths and not is_path_allowed(path, allowed_paths):
        raise PermissionError(
            f"Accès refusé: {path} est hors des répertoires autorisés "
            f"(ALLOWED_PATHS). Répertoires autorisés: {[str(p) for p in allowed_paths]}"
        )

    # Tenter plusieurs encodages
    content = _read_with_fallback_encoding(path)
    lines = content.splitlines()
    total_lines = len(lines)

    # Extraire la plage de lignes si demandée
    if focus_lines:
        start, end = _parse_line_range(focus_lines, total_lines)
        selected = lines[start - 1 : end]
        content = "\n".join(selected)

    return content, total_lines


def write_file_safe(
    file_path: str | Path,
    content: str,
    allowed_paths: list[Path] | None = None,
) -> int:
    """Écrit dans un fichier de manière sécurisée avec vérification des permissions.

    Crée les répertoires parents si nécessaire.

    Args:
        file_path: Chemin du fichier à écrire.
        content: Contenu à écrire.
        allowed_paths: Répertoires autorisés. Si None, pas de restriction.

    Returns:
        Nombre de lignes écrites.

    Raises:
        PermissionError: Si le fichier est hors des chemins autorisés.
    """
    path = Path(file_path).resolve()

    if allowed_paths and not is_path_allowed(path, allowed_paths):
        raise PermissionError(
            f"Accès refusé: {path} est hors des répertoires autorisés "
            f"(ALLOWED_PATHS). Répertoires autorisés: {[str(p) for p in allowed_paths]}"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    return len(content.splitlines())


def chunk_file(
    content: str,
    max_lines_per_chunk: int = 500,
) -> list[FileChunk]:
    """Découpe un contenu de fichier en morceaux digestibles.

    Essaie de découper aux frontières naturelles du code
    (définitions de fonctions, de classes, ou commentaires séparateurs).

    Args:
        content: Contenu textuel complet du fichier.
        max_lines_per_chunk: Nombre maximum de lignes par chunk.

    Returns:
        Liste de FileChunk avec positions.
    """
    lines = content.splitlines()

    if len(lines) <= max_lines_per_chunk:
        return [FileChunk(content=content, start_line=1, end_line=len(lines))]

    chunks: list[FileChunk] = []
    current_lines: list[str] = []
    current_start = 1

    for i, line in enumerate(lines, 1):
        current_lines.append(line)

        # Chercher une frontière naturelle après avoir atteint la taille min
        is_boundary = (
            line.startswith("def ")
            or line.startswith("class ")
            or line.startswith("# ---")
            or line.startswith("// ---")
            or line.startswith("function ")
            or line.startswith("export ")
        )

        if len(current_lines) >= max_lines_per_chunk and is_boundary:
            chunks.append(
                FileChunk(
                    content="\n".join(current_lines),
                    start_line=current_start,
                    end_line=i,
                )
            )
            current_lines = []
            current_start = i + 1

    # Dernier chunk
    if current_lines:
        chunks.append(
            FileChunk(
                content="\n".join(current_lines),
                start_line=current_start,
                end_line=len(lines),
            )
        )

    return chunks


def _read_with_fallback_encoding(path: Path) -> str:
    """Lit un fichier en essayant plusieurs encodages.

    Args:
        path: Chemin du fichier.

    Returns:
        Contenu du fichier.

    Raises:
        ValueError: Si aucun encodage ne fonctionne.
    """
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except (UnicodeDecodeError, ValueError):
            continue

    raise ValueError(
        f"Impossible de lire {path}: aucun encodage supporté ne fonctionne. "
        f"Encodages testés: {encodings}"
    )


def _parse_line_range(focus_lines: str, total_lines: int) -> tuple[int, int]:
    """Parse une plage de lignes au format "start-end".

    Args:
        focus_lines: Plage au format "100-200".
        total_lines: Nombre total de lignes du fichier.

    Returns:
        Tuple (start, end) en 1-indexed, borné au fichier.

    Raises:
        ValueError: Si le format est invalide.
    """
    try:
        parts = focus_lines.strip().split("-")
        start = max(1, int(parts[0]))
        end = min(total_lines, int(parts[1])) if len(parts) > 1 else total_lines
        return start, end
    except (ValueError, IndexError) as e:
        raise ValueError(
            f"Format de plage invalide: '{focus_lines}'. "
            f"Format attendu: 'start-end' (ex: '100-200')"
        ) from e
