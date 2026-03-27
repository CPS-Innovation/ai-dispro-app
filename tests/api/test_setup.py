import pytest

from src.api.setup import setup, validate_create_view_ddl
from sqlalchemy import text


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.parametrize("views", [
    None,
    [
        "CREATE OR REPLACE VIEW test_view AS SELECT 1 AS value;",
    ]
])
async def test_setup_with_views(views):
    """Setup returns success when schema verification passes."""
    result = await setup(views=views)
    if views is not None:
        assert "views" in result
        assert result["views"]["upserted"] == len(views)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.parametrize("views", [
    None,
    [
        "CREATE OR REPLACE VIEW test_view AS SELECT 1 AS value;",
    ]
])
async def test_setup_defend_db(views):
    """Setup returns success when schema verification passes."""
    await setup(views=views)
    with pytest.raises(ValueError):
        await setup(views=['DROP TABLE IF EXISTS test_view;'])


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.parametrize("prompt_templates", [
    None,
    [
        {
            "template": "Classify the last word in the following text based on language:\n {{ contextText }}\n Return a JSON with {\n \"analysis_results\": [{\n \"content\": string of the word,\n \"justification\": string, why this language was selected,\n \"categories\": [list of selected languages],\n \"self_confidence\": float (0.0-1.0)\n }]",
            "name": "mockup",
            "agent": "critic",
            "theme": "tst-theme-01",
            "pattern": "tst-pattern-02",
            "version": 0.2
        }
    ]
])
async def test_setup_with_prompt_templates(prompt_templates):
    """Setup returns success when schema verification passes and prompt templates are uploaded."""
    result = await setup(prompt_templates=prompt_templates)
    if prompt_templates is not None:
        assert "prompt_templates" in result
        assert len(result["prompt_templates"]["upserted"]) == len(prompt_templates)


@pytest.mark.unit
@pytest.mark.parametrize("ddl, should_pass", [
    ("CREATE VIEW test_view AS SELECT 1;", True),
    ("CREATE OR REPLACE VIEW test_view AS SELECT 1;", True),
    ("-- Comment\nCREATE OR REPLACE VIEW test_view AS SELECT 1;", True),
    ("/* Multi-line\nComment */\nCREATE OR REPLACE VIEW test_view AS SELECT 1;", True),
    ("CREATE OR REPLACE VIEW test_view AS SELECT 1; -- Inline comment", True),
    ("CREATE TABLE test_table (id INT);", False),
    ("DROP VIEW test_view;", False),
])
def test_validate_create_view_ddl(ddl, should_pass, db_session):
    """Test that validate_create_view_ddl correctly validates DDL statements."""
    if should_pass:
        # Should not raise an exception
        validate_create_view_ddl(ddl)
        db_session.execute(text('DROP VIEW IF EXISTS test_view;'))
    else:
        with pytest.raises(ValueError):
            validate_create_view_ddl(ddl)
