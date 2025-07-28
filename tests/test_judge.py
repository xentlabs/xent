import pytest

from xega.common.x_string import XString
from xega.runtime.judge import Judge


@pytest.fixture
def judge():
    """Create a test XegaRuntime instance."""
    judge = Judge("Qwen/Qwen3-0.6B-Base")
    return judge


def test_first_n_tokens(judge):
    string = XString("This is a test string for the Xega framework.")

    assert judge.first_n_tokens(string, 5) == "This is a test string"
    assert judge.first_n_tokens(str(string), 5) == "This is a test string"
    assert judge.first_n_tokens("", 5) == ""
    assert judge.first_n_tokens("   ", 5) == "   "
    assert judge.first_n_tokens("\n", 5) == "\n"


@pytest.mark.parametrize(
    "statement, expected_truthfulness",
    [
        # Cases that should be True
        ("Water boils at 100 degrees Celsius at sea level", True),
        ("Grass is green", True),
        # Cases that should be False
        ("The sun is smaller than the earth", False),
        (
            "There are no emoji in the following string: 'hello 🌎'",
            False,
        ),
    ],
)
def test_truthfulness(judge, statement, expected_truthfulness):
    """Tests the is_true method with various statements."""
    assert judge.is_true(statement) == expected_truthfulness
