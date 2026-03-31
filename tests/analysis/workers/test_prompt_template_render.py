import pytest
from jinja2 import Environment

def test_render():
    env = Environment(autoescape=False)
    template = env.from_string("Input:\n{{ some_input }}")
    assert template.render(some_input="hello world") == "Input:\nhello world"
    assert template.render(some_input=["line1", "line2", "line3"]) == "Input:\n['line1', 'line2', 'line3']"

@pytest.mark.parametrize(
    "as_str, as_list",
    [
        ("hello world", ["hello world"]),
        ("line1\nline2\nline3", ["line1", "line2", "line3"]),
        ("single", ["single"]),
    ],
)
def test_str_and_list_render_equally(as_str: str, as_list: list[str]) -> None:
    def render(some_input: str | list[str]) -> str:
        env = Environment(autoescape=False)
        template = env.from_string("Input:\n{{ some_input if some_input is string else some_input | join('\n') }}")
        return template.render(some_input=some_input)
    assert render(as_str) == render(as_list)
