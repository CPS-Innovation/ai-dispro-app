import pytest

from jinja2 import Environment

from src.repositories import (
    PromptTemplateRepository,
)

@pytest.mark.integration
def test_prompt_template_repository(db_session):
    """Test PromptTemplate repository create."""
    repo = PromptTemplateRepository(db_session)
    for pt in repo.get_all():
        try:
            template = Environment(autoescape=True).from_string(source=pt.template)
            assert template is not None
        except Exception as e:
            pytest.fail(f"Template id={pt.id} failed: {e}")
        

@pytest.mark.unit
@pytest.mark.parametrize("template", [
    "This is a template with a input: {{ variable_name }}",
])
def test_prompt_template_syntax(template):
    """Test PromptTemplate repository create."""
    template = Environment(autoescape=True).from_string(source=template)
    assert template is not None
