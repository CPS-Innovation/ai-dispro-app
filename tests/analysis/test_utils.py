import pytest

from src.analysis.utils import deduplicate_case_outlines, is_valid_subset

@pytest.mark.unit
@pytest.mark.parametrize(
    "source, extracted, expected",
    [
        (
            "The defendant was arrested and later interviewed "
            "at the police station.",
            "The defendant was arrested",
            True,
        ),
        (
            "I was staying around her friend [REDACTED]'s house.",
            "I was staying around her friend [REDACTED]'s house "
            "at [REDACTED], [REDACTED]. She was back in "
            "[REDACTED] staying at a woman's refuge as she "
            "wanted to see her children.",
            False,
        ),
        (
            "She said 'hello'",
            'She said "hello"',
            True,
        ),
        (
            "The defendant was arrested.",
            "The   defendant    was arrested.",
            True,
        ),
        (
            "The defendant was arrested and later interviewed "
            "at the police station.",
            "...The defendant was arrested and later interviewed "
            "at the police station.",
            True,
        ),
    ],
)
def test_is_valid_subset(source, extracted, expected):
    assert is_valid_subset(source, extracted) == expected

@pytest.mark.unit
def test_deduplicate_case_outlines_removes_near_duplicates():
    narratives = [
        "The defendant John Smith attended the property and assaulted the victim.",
        "The defendant [REDACTED] attended the property and assaulted the victim.",
        "The defendant was later arrested and interviewed.",
    ]

    result = deduplicate_case_outlines(narratives)

    assert len(result) == 2


@pytest.mark.unit
def test_deduplicate_case_outlines_keeps_different_outlines():
    narratives = [
        "The defendant assaulted the victim.",
        "The defendant later admitted the offence during interview.",
        "The defendant was released on bail.",
    ]

    result = deduplicate_case_outlines(narratives)

    assert len(result) == 3


@pytest.mark.unit
def test_deduplicate_case_outlines_removes_exact_duplicates():
    narratives = [
        "Same outline",
        "Same outline",
        "Different outline",
    ]

    result = deduplicate_case_outlines(narratives)

    assert result == [
        "Same outline",
        "Different outline",
    ]