import pytest

from xega.common.x_string import XString
from xega.runtime.judge import Judge


@pytest.fixture
def judge():
    """Create a test XegaRuntime instance."""
    judge = Judge("gpt2")
    return judge


def test_first_n_tokens(judge):
    string = XString("This is a test string for the Xega framework.")

    assert judge.first_n_tokens(string, 5) == "This is a test string"
    assert judge.first_n_tokens(str(string), 5) == "This is a test string"
    assert judge.first_n_tokens("", 5) == ""
    assert judge.first_n_tokens("   ", 5) == "   "
    assert judge.first_n_tokens("\n", 5) == "\n"
