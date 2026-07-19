"""Tests pour les utilitaires de fichiers."""


import pytest

from nexus_worker.utils.files import chunk_file, is_path_allowed, read_file_safe, write_file_safe


def test_is_path_allowed(tmp_path):
    """Test la verification des chemins autorises."""
    allowed = [tmp_path / "src"]

    # Chemin exact
    assert is_path_allowed(tmp_path / "src", allowed) is True
    # Sous-chemin
    assert is_path_allowed(tmp_path / "src" / "main.py", allowed) is True
    # Chemin hors autorisation
    assert is_path_allowed(tmp_path / "tests", allowed) is False
    # Navigation relative qui sort
    assert is_path_allowed(tmp_path / "src" / ".." / "tests", allowed) is False


def test_read_file_safe(tmp_path):
    """Test la lecture de fichier securisee."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Ligne 1\nLigne 2\nLigne 3")

    # Lecture normale sans restriction
    content, lines = read_file_safe(test_file)
    assert lines == 3
    assert "Ligne 2" in content

    # Lecture avec restriction (chemin non autorise)
    with pytest.raises(PermissionError):
        read_file_safe(test_file, allowed_paths=[tmp_path / "other"])

    # Lecture avec restriction (chemin autorise)
    content, lines = read_file_safe(test_file, allowed_paths=[tmp_path])
    assert lines == 3

    # Lecture avec filtre de lignes
    content, lines = read_file_safe(test_file, focus_lines="2-3")
    assert lines == 3  # Toujours le total original
    assert "Ligne 1" not in content
    assert "Ligne 2" in content
    assert "Ligne 3" in content


def test_write_file_safe(tmp_path):
    """Test l_ecriture de fichier securisee."""
    test_file = tmp_path / "output.py"
    content = "def test():\n    pass\n"

    # Ecriture avec chemin non autorise
    with pytest.raises(PermissionError):
        write_file_safe(test_file, content, allowed_paths=[tmp_path / "other"])

    # Ecriture reussie avec creation de dossier
    target_file = tmp_path / "src" / "new_dir" / "output.py"
    lines_written = write_file_safe(target_file, content, allowed_paths=[tmp_path])

    assert lines_written == 2
    assert target_file.exists()
    assert target_file.read_text() == content


def test_chunk_file():
    """Test le decoupage d_un fichier."""
    content = "Ligne 1\nLigne 2\nLigne 3\ndef test():\n    pass\nLigne 6"

    # Pas de decoupage necessaire
    chunks = chunk_file(content, max_lines_per_chunk=10)
    assert len(chunks) == 1
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 6

    # Decoupage avec frontiere naturelle
    chunks = chunk_file(content, max_lines_per_chunk=3)
    assert len(chunks) == 2
    assert chunks[0].end_line == 4
    assert chunks[1].start_line == 5
    assert chunks[1].end_line == 6
    assert chunks[1].content.startswith("    pass")
