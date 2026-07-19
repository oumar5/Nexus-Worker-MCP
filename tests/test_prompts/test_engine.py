"""Tests pour le moteur de prompts."""


import pytest

from nexus_worker.prompts.engine import PromptEngine


@pytest.fixture
def temp_templates_dir(tmp_path):
    """Cree un repertoire temporaire avec des templates de test."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    # Template valide
    (templates_dir / "test_valid.md").write_text(
        "Template for {language}:\nContext: {context}"
    )

    return templates_dir


def test_engine_initialization(temp_templates_dir):
    """Test l_initialisation avec un repertoire personnalise."""
    engine = PromptEngine(templates_dir=temp_templates_dir)
    assert engine.templates_dir == temp_templates_dir


def test_get_system_prompt_success(temp_templates_dir):
    """Test le chargement et le rendu d_un template."""
    engine = PromptEngine(templates_dir=temp_templates_dir)

    prompt = engine.get_system_prompt(
        "test_valid",
        language="Python",
        context="Tests"
    )

    assert "Template for Python:" in prompt
    assert "Context: Tests" in prompt


def test_get_system_prompt_cache(temp_templates_dir):
    """Test que le template est bien mis en cache apres le premier chargement."""
    engine = PromptEngine(templates_dir=temp_templates_dir)

    # Premier appel : chargement depuis le disque
    engine.get_system_prompt("test_valid", language="A", context="B")
    assert "test_valid" in engine._cache

    # Modification du fichier sur le disque
    (temp_templates_dir / "test_valid.md").write_text("Modified template")

    # Deuxieme appel : utilise le cache, ignore la modification
    prompt = engine.get_system_prompt("test_valid", language="A", context="B")
    assert "Modified template" not in prompt
    assert "Template for A:" in prompt


def test_get_system_prompt_missing(temp_templates_dir):
    """Test le comportement quand un template n_existe pas."""
    engine = PromptEngine(templates_dir=temp_templates_dir)

    with pytest.raises(FileNotFoundError, match="Template introuvable"):
        engine.get_system_prompt("does_not_exist")


def test_list_templates(temp_templates_dir):
    """Test le listage des templates disponibles."""
    (temp_templates_dir / "another.md").write_text("test")
    (temp_templates_dir / "not_a_template.txt").write_text("test")

    engine = PromptEngine(templates_dir=temp_templates_dir)
    templates = engine.list_templates()

    assert "test_valid" in templates
    assert "another" in templates
    assert "not_a_template" not in templates
